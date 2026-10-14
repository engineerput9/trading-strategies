#!/usr/bin/env python3
"""One-shot live check for Crude 5m final strategy. Prints JSON alert or {}."""
import json, os, sys, time, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(os.environ.get('CRUDE_LIVE_DIR', str(Path(__file__).resolve().parent)))
STATE = Path(os.environ.get('CRUDE_LIVE_STATE', str(ROOT / 'live_state.json')))
LOG = Path(os.environ.get('CRUDE_LIVE_LOG', str(ROOT / 'live_log.csv')))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common' / 'fyers'))
from fyers_login import get_fyers, scrub

def _looks_like_auth(err: str) -> bool:
    """True for Fyers token/auth failures (e.g. code -15/-16)."""
    e = (err or '').lower()
    return (
        'token is invalid' in e or 'token is expired' in e
        or 'token is invalid or expired' in e
        or 'could not authenticate' in e
        or ('token' in e and 'expired' in e)
        or 'code": -15' in e or "code': -15" in e or 'code":-15' in e or "code':-15" in e
        or 'code": -16' in e or "code': -16" in e or 'code":-16' in e or "code':-16" in e
        or ' -15' in e or ' -16' in e
        or 'login' in e
        or ('auth' in e and ('token' in e or 'fail' in e or 'could not' in e))
    )

# --- Range Filter / feats (from add5m.py) ---
def ema(a, t):
    al = 2 / (t + 1); o = np.full(len(a), np.nan); s = np.nan; buf = []
    for i, v in enumerate(a):
        if np.isnan(v): continue
        if np.isnan(s):
            buf.append(v)
            if len(buf) == t: s = np.mean(buf)
        else:
            s = al * v + (1 - al) * s
        o[i] = s
    return o

def build(d, per=100, mult=3):
    x = d.c.values.astype(float); n = len(x)
    H = d.h.values.astype(float); L = d.l.values.astype(float); O = d.o.values.astype(float)
    dif = np.r_[np.nan, np.abs(np.diff(x))]
    r = ema(ema(dif, per), 2 * per - 1) * mult
    rf = np.zeros(n); rf[0] = x[0]
    for i in range(1, n):
        p = rf[i - 1]; R = r[i]
        if np.isnan(R): rf[i] = x[i]; continue
        rf[i] = (p if x[i] - R < p else x[i] - R) if x[i] > p else (p if x[i] + R > p else x[i] + R)
    up = np.zeros(n); dn = np.zeros(n)
    for i in range(1, n):
        up[i] = up[i - 1] + 1 if rf[i] > rf[i - 1] else (0 if rf[i] < rf[i - 1] else up[i - 1])
        dn[i] = dn[i - 1] + 1 if rf[i] < rf[i - 1] else (0 if rf[i] > rf[i - 1] else dn[i - 1])
    ch = np.r_[False, x[1:] != x[:-1]]
    lc = (x > rf) & (up > 0) & ch; sc = (x < rf) & (dn > 0) & ch
    ci = np.zeros(n)
    for i in range(1, n):
        ci[i] = 1 if lc[i] else (-1 if sc[i] else ci[i - 1])
    flip = np.zeros(n, int)
    flip[1:] = np.where((lc[1:] & (ci[:-1] == -1)), 1, np.where(sc[1:] & (ci[:-1] == 1), -1, 0))
    tr = np.maximum(H - L, np.maximum(abs(H - np.r_[np.nan, x[:-1]]), abs(L - np.r_[np.nan, x[:-1]])))
    tr[0] = H[0] - L[0]
    atr = np.full(n, np.nan); atr[13] = tr[:14].mean()
    for i in range(14, n):
        atr[i] = (atr[i - 1] * 13 + tr[i]) / 14
    day = d.dt.dt.date.values; first = {}; last = {}
    for k, dd in enumerate(day):
        first.setdefault(dd, k); last[dd] = k
    days = sorted(first); pos = {dd: q for q, dd in enumerate(days)}
    return dict(d=d, x=x, H=H, L=L, O=O, rf=rf, r=r, ci=ci, flip=flip, atr=atr,
                day=day, first=first, last=last, days=days, pos=pos, n=n, start=3 * per * 2, dt=d.dt)

def feats(B, i, s):
    x, H, L, O, atr = B['x'], B['H'], B['L'], B['O'], B['atr']
    dd = B['day'][i]; q = B['pos'][dd]; f0 = B['first'][dd]
    if q == 0: return None
    p = B['days'][q - 1]; pc = x[B['last'][p]]; gap = O[f0] - pc
    lo = L[f0:i + 1].min(); hi = H[f0:i + 1].max()
    gf = bool(lo <= pc) if gap > 0 else (bool(hi >= pc) if gap < 0 else True)
    pl = L[B['first'][p]:B['last'][p] + 1].min()
    ph = H[B['first'][p]:B['last'][p] + 1].max()
    return dict(gap_atr=gap / atr[f0], gap_filled=gf, pdl_atr=(x[i] - pl) / atr[i], pdr=ph - pl)

def stopof(B, i, s):
    e = B['x'][i]; a = B['atr'][i]
    if s > 0:
        raw = B['L'][i - 10:i].min(); sl = e - a if e - raw < a else raw
    else:
        raw = B['H'][i - 10:i].max(); sl = e + a if raw - e < a else raw
    return sl

def er20(x, i, lb=20):
    if i < lb: return np.nan
    num = abs(x[i] - x[i - lb])
    den = np.abs(np.diff(x[i - lb:i + 1])).sum()
    return num / max(den, 1e-9)

RVOL_TH = 0.8
RVOL_N = 10

def rvol_tod(B, d, i, N=RVOL_N):
    """Signal-bar volume / mean volume of the same time-of-day bar over the prior N
    trading days in the data (matches rvol08.py: needs >= max(3, N//2) such bars, else NaN)."""
    V = d.v.values.astype(float)
    tod = B['dt'].iloc[i].strftime('%H%M'); dd = B['day'][i]; q = B['pos'][dd]
    vals = []
    for pd_ in B['days'][max(0, q - N):q]:
        for k in range(B['first'][pd_], B['last'][pd_] + 1):
            if B['dt'].iloc[k].strftime('%H%M') == tod:
                vals.append(V[k]); break
    if len(vals) < max(3, N // 2): return float('nan')
    m = float(np.nanmean(vals))
    return float(V[i] / m) if m > 0 else float('nan')

def bd_back(x, n):
    while x.weekday() > 4: x -= dt.timedelta(1)
    for _ in range(n):
        x -= dt.timedelta(1)
        while x.weekday() > 4: x -= dt.timedelta(1)
    return x

def optexp(y, m):
    return bd_back(dt.date(y, m, 19), 2)

def nearest_opt_exp(day):
    y, m = day.year, day.month
    e = optexp(y, m)
    if day > e:
        m += 1
        if m > 12: y += 1; m = 1
        e = optexp(y, m)
    return e

def month_code(d):
    return {1:'JAN',2:'FEB',3:'MAR',4:'APR',5:'MAY',6:'JUN',
            7:'JUL',8:'AUG',9:'SEP',10:'OCT',11:'NOV',12:'DEC'}[d.month]

def load_state():
    if STATE.exists():
        return json.load(open(STATE))
    return {}

def save_state(st):
    tmp = STATE.with_suffix('.tmp')
    json.dump(st, open(tmp, 'w'), indent=2, default=str)
    tmp.replace(STATE)

LOG_COLS = ['ts','event','date','direction','signal_time','signal_price','reason','entry',
            'stop','target','mode','er','exit','pts','option','rvol']

def append_log(row):
    row = {c: row.get(c, '') for c in LOG_COLS}
    if LOG.exists():
        old = pd.read_csv(LOG, dtype=str, keep_default_na=False)
        if list(old.columns) != LOG_COLS:  # migrate header once
            old = old.reindex(columns=LOG_COLS, fill_value='')
            old.to_csv(LOG, index=False)
    df = pd.DataFrame([row], columns=LOG_COLS)
    if LOG.exists():
        df.to_csv(LOG, mode='a', header=False, index=False)
    else:
        df.to_csv(LOG, index=False)

def pull_history(fyers, days_back=12):
    today = dt.datetime.now(IST).date()
    fr = (today - dt.timedelta(days=days_back)).isoformat()
    to = today.isoformat()
    sym = 'MCX:CRUDEOIL26OCTFUT'
    r = fyers.history({
        'symbol': sym, 'resolution': '5', 'date_format': '1',
        'range_from': fr, 'range_to': to, 'cont_flag': '1'
    })
    if r.get('s') != 'ok':
        raise RuntimeError('history_fail:' + scrub(str(r))[:200])
    candles = r.get('candles') or []
    if not candles:
        raise RuntimeError('no_candles')
    d = pd.DataFrame(candles, columns=list('toh lcv'.replace(' ', '')))
    # columns: t o h l c v
    d = pd.DataFrame(candles, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    d = d.drop_duplicates('t').sort_values('t').reset_index(drop=True)
    d['dt'] = pd.to_datetime(d.t, unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
    return d, sym

def quotes(fyers, symbols):
    try:
        r = fyers.quotes({'symbols': ','.join(symbols)})
        if r.get('s') != 'ok':
            return {}
        out = {}
        for row in r.get('d') or []:
            v = row.get('v') or {}
            sym = v.get('symbol') or row.get('n')
            lp = v.get('lp')
            if sym is not None and lp is not None:
                out[sym] = float(lp)
        return out
    except Exception:
        return {}

def main():
    now = dt.datetime.now(IST)
    today = now.date()
    alerts = []  # list of user-facing messages
    meta = {'now': now.isoformat(), 'today': str(today)}

    st = load_state()
    # reset day if new calendar day
    if st.get('date') != str(today):
        st = {
            'date': str(today),
            'signal_used': False,
            'signal': None,
            'filtered': None,
            'heads_up_sent': False,
            'entry_sent': False,
            'trade': None,
            'exit_sent': False,
            'session_end_sent': False,
            'fyers_auth_alerted': st.get('fyers_auth_alerted_date') == str(today),
            'fyers_auth_alerted_date': st.get('fyers_auth_alerted_date'),
        }

    # Friday skip — quiet
    if today.weekday() == 4:
        st['filtered'] = {'reason': 'friday'}
        save_state(st)
        print(json.dumps({'alerts': [], 'meta': meta, 'note': 'friday_skip'}))
        return

    try:
        fyers = get_fyers()
        # Cached same-day token can still be invalid/expired; validate via history.
        try:
            d, fut_sym = pull_history(fyers, days_back=21)
        except Exception as e1:
            err1 = scrub(str(e1))
            if not _looks_like_auth(err1):
                raise
            # One forced re-login, then retry history before alerting.
            fyers = get_fyers(force=True)
            d, fut_sym = pull_history(fyers, days_back=21)
    except Exception as e:
        err = scrub(str(e))
        already = st.get('fyers_auth_alerted_date') == str(today)
        if not already and (_looks_like_auth(err) or 'history_fail' in err
                            or 'Access' in err or 'LOGIN' in err.upper()):
            msg = 'Fyers login needs refreshing for Crude 5m signal alerts (token/auth failed).'
            st['fyers_auth_alerted_date'] = str(today)
            save_state(st)
            print(json.dumps({'alerts': [msg], 'meta': meta, 'error': err[:200]}))
            return
        # other errors: quiet
        save_state(st)
        print(json.dumps({'alerts': [], 'meta': meta, 'error': err[:200]}))
        return

    B = build(d, per=100, mult=3)
    x, H, L, day, flip, ci, atr = B['x'], B['H'], B['L'], B['day'], B['flip'], B['ci'], B['atr']
    n = B['n']
    if today not in B['first']:
        save_state(st)
        print(json.dumps({'alerts': [], 'meta': {**meta, 'note': 'no_bars_today', 'last': str(B['dt'].iloc[-1])}}))
        return

    f0 = B['first'][today]
    last_i = B['last'][today]
    last_dt = B['dt'].iloc[last_i]
    last_px = float(x[last_i])
    meta.update({
        'bars_today': int(last_i - f0 + 1),
        'last_bar': last_dt.strftime('%Y-%m-%d %H:%M'),
        'last_px': last_px,
        'total_bars': int(n),
    })

    # Session end roughly 23:30 IST (last bar starts 23:25 typically for 5m)
    session_over = (now.hour > 23) or (now.hour == 23 and now.minute >= 30) or (
        last_dt.hour == 23 and last_dt.minute >= 25 and (now - last_dt).total_seconds() > 240
    )

    ERTH = 0.294737
    WAIT = 2

    # Find first flip today after warm-up
    sig_i = None
    sig_s = 0
    for i in range(max(f0, B['start']), last_i + 1):
        if flip[i] != 0:
            sig_i = i; sig_s = int(flip[i]); break

    # --- Process signal / filters ---
    if sig_i is not None and not st.get('signal_used') and st.get('filtered') is None:
        f = feats(B, sig_i, sig_s)
        dt_sig = B['dt'].iloc[sig_i]
        reason = None
        if f is None:
            reason = 'no_prior_day'
        elif f['gap_filled'] and abs(f['gap_atr']) > 0.5:
            reason = f"gap_filled gap_atr={f['gap_atr']:.2f}"
        elif f['pdl_atr'] < 4:
            reason = f"pdl_atr={f['pdl_atr']:.2f}<4"
        if reason:
            st['filtered'] = {
                'reason': reason,
                'signal_time': dt_sig.strftime('%Y-%m-%d %H:%M'),
                'direction': 'long' if sig_s > 0 else 'short',
                'price': float(x[sig_i]),
            }
            st['signal_used'] = True  # day consumed by filtered flip
            append_log({
                'ts': now.isoformat(), 'event': 'filtered', 'date': str(today),
                'direction': 'long' if sig_s > 0 else 'short',
                'signal_time': dt_sig.strftime('%Y-%m-%d %H:%M'),
                'signal_price': float(x[sig_i]), 'reason': reason,
                'entry': '', 'stop': '', 'target': '', 'mode': '', 'er': '',
                'exit': '', 'pts': '', 'option': '',
            })
            # quiet — no user alert
        else:
            st['signal_used'] = True
            st['signal'] = {
                'i': int(sig_i),
                'direction': 'long' if sig_s > 0 else 'short',
                's': sig_s,
                'time': dt_sig.strftime('%Y-%m-%d %H:%M'),
                'price': float(x[sig_i]),
                'sl0': float(stopof(B, sig_i, sig_s)),
                'R0': float(abs(x[sig_i] - stopof(B, sig_i, sig_s))),
                'pdl_atr': float(f['pdl_atr']),
                'gap_atr': float(f['gap_atr']),
            }
            if not st.get('heads_up_sent'):
                direction = st['signal']['direction']
                alerts.append(
                    f"Crude 5m heads-up: {direction.upper()} signal at {st['signal']['time']} "
                    f"@ {st['signal']['price']:.0f}. Entry after 2 confirming candles "
                    f"(a choppy/locked entry is skipped if signal-bar RVOL < 0.8)."
                )
                st['heads_up_sent'] = True
                append_log({
                    'ts': now.isoformat(), 'event': 'heads_up', 'date': str(today),
                    'direction': direction,
                    'signal_time': st['signal']['time'],
                    'signal_price': st['signal']['price'], 'reason': '',
                    'entry': '', 'stop': '', 'target': '', 'mode': '', 'er': '',
                    'exit': '', 'pts': '', 'option': '',
                })

    # --- Entry confirmation ---
    sig = st.get('signal')
    if sig and not st.get('entry_sent') and st.get('trade') is None:
        i = None
        # locate signal bar by time
        tmatch = pd.Timestamp(sig['time']).tz_localize('Asia/Kolkata') if pd.Timestamp(sig['time']).tzinfo is None else pd.Timestamp(sig['time'])
        # rebuild index from state time
        for k in range(f0, last_i + 1):
            if B['dt'].iloc[k].strftime('%Y-%m-%d %H:%M') == sig['time']:
                i = k; break
        if i is None:
            i = int(sig.get('i', -1))
        s = int(sig['s'])
        j = i + WAIT
        if i >= 0 and j <= last_i and day[j] == today:
            sl0 = float(sig['sl0']); e_sig = float(sig['price']); R0 = float(sig['R0'])
            ok_dir = (ci[i:j + 1] == s).all()
            hit_stop = bool((L[i + 1:j + 1] <= sl0).any() if s > 0 else (H[i + 1:j + 1] >= sl0).any())
            if ok_dir and not hit_stop:
                ie = j; ee = float(x[ie])
                a = float(atr[ie]); er = float(er20(x, ie))
                tight = er > ERTH
                # RVOL at the signal bar (complete by now, no lookahead)
                rv = rvol_tod(B, d, i)
                rv_txt = 'n/a' if np.isnan(rv) else f'{rv:.2f}'
                if (not tight) and (not np.isnan(rv)) and rv < RVOL_TH:
                    st['trade'] = {'status': 'filtered', 'reason': 'rvol<0.8', 'rvol': round(rv, 3), 'er': round(er, 4)}
                    st['entry_sent'] = True
                    st['filtered'] = {'reason': 'rvol<0.8', 'rvol': round(rv, 3), 'signal_time': sig['time'],
                                      'direction': sig['direction'], 'price': e_sig}
                    append_log({
                        'ts': now.isoformat(), 'event': 'filtered', 'date': str(today),
                        'direction': sig['direction'], 'signal_time': sig['time'],
                        'signal_price': e_sig, 'reason': 'rvol<0.8',
                        'entry': '', 'stop': '', 'target': '', 'mode': 'locked', 'er': er,
                        'exit': '', 'pts': '', 'option': '', 'rvol': rv,
                    })
                    if st.get('heads_up_sent') and not st.get('rvol_skip_sent'):
                        alerts.append(f"Crude 5m: no entry today, low volume (RVOL {rv:.2f} < {RVOL_TH}) on choppy setup.")
                        st['rvol_skip_sent'] = True
                    tight = None
            if ok_dir and not hit_stop and tight is not None:
                if tight:
                    sl = ee - s * 2 * a
                    tp = e_sig + s * 2.5 * R0
                    mode = 'tight'
                else:
                    sl = e_sig - s * 1.5 * R0
                    tp = e_sig + s * 1.5 * R0
                    mode = 'locked'
                stop_dist = abs(ee - sl); tgt_dist = abs(tp - ee)
                # ATM option
                K = int(round(ee / 50) * 50)
                exp = nearest_opt_exp(today)
                mcode = month_code(exp)
                yy = str(exp.year)[-2:]
                cp = 'CE' if s > 0 else 'PE'
                opt_sym = f'MCX:CRUDEOIL{yy}{mcode}{K}{cp}'
                q = quotes(fyers, [fut_sym, opt_sym])
                prem = q.get(opt_sym)
                opt_txt = f"{opt_sym}" + (f" @ {prem:.0f}" if prem is not None else " (premium unavailable)")
                trade = {
                    'direction': 'long' if s > 0 else 'short',
                    's': s,
                    'entry_time': B['dt'].iloc[ie].strftime('%Y-%m-%d %H:%M'),
                    'entry': ee,
                    'mode': mode,
                    'er': round(er, 4),
                    'rvol': None if np.isnan(rv) else round(rv, 3),
                    'stop': float(sl),
                    'target': float(tp),
                    'stop_dist': float(stop_dist),
                    'target_dist': float(tgt_dist),
                    'option': opt_sym,
                    'option_premium': prem,
                    'status': 'open',
                }
                st['trade'] = trade
                st['entry_sent'] = True
                alerts.append(
                    f"Crude 5m ENTRY: {trade['direction'].upper()} @ {ee:.0f} "
                    f"({mode}, ER={er:.3f}, RVOL={rv_txt}). Stop {sl:.0f} ({stop_dist:.0f} pts), "
                    f"target {tp:.0f} ({tgt_dist:.0f} pts). ATM option: {opt_txt}."
                )
                append_log({
                    'ts': now.isoformat(), 'event': 'entry', 'date': str(today),
                    'direction': trade['direction'],
                    'signal_time': sig['time'], 'signal_price': e_sig, 'reason': '',
                    'entry': ee, 'stop': sl, 'target': tp, 'mode': mode, 'er': er,
                    'exit': '', 'pts': '', 'option': opt_txt, 'rvol': rv,
                })
            elif not ok_dir or hit_stop:
                st['trade'] = {'status': 'aborted', 'reason': 'dir_flip' if not ok_dir else 'stop_before_entry'}
                st['entry_sent'] = True  # don't keep retrying
                append_log({
                    'ts': now.isoformat(), 'event': 'entry_aborted', 'date': str(today),
                    'direction': sig['direction'], 'signal_time': sig['time'],
                    'signal_price': sig['price'], 'reason': st['trade']['reason'],
                    'entry': '', 'stop': '', 'target': '', 'mode': '', 'er': '',
                    'exit': '', 'pts': '', 'option': '',
                })

    # --- Manage open trade ---
    trade = st.get('trade')
    if trade and trade.get('status') == 'open' and not st.get('exit_sent'):
        s = int(trade['s']); ee = float(trade['entry'])
        sl = float(trade['stop']); tp = float(trade['target'])
        # find entry index
        ie = None
        for k in range(f0, last_i + 1):
            if B['dt'].iloc[k].strftime('%Y-%m-%d %H:%M') == trade['entry_time']:
                ie = k; break
        if ie is None:
            ie = f0
        why = None; pts = None; exit_px = None; exit_time = None
        for k in range(ie + 1, last_i + 1):
            if (L[k] <= sl) if s > 0 else (H[k] >= sl):
                why = 'stop'; pts = s * (sl - ee); exit_px = sl
                exit_time = B['dt'].iloc[k].strftime('%Y-%m-%d %H:%M'); break
            if (H[k] >= tp) if s > 0 else (L[k] <= tp):
                why = 'target'; pts = s * (tp - ee); exit_px = tp
                exit_time = B['dt'].iloc[k].strftime('%Y-%m-%d %H:%M'); break
        if why is None and session_over:
            why = 'session_end'
            exit_px = float(x[last_i])
            pts = s * (exit_px - ee)
            exit_time = B['dt'].iloc[last_i].strftime('%Y-%m-%d %H:%M')
        if why is not None:
            trade['status'] = 'closed'
            trade['exit'] = float(exit_px)
            trade['exit_time'] = exit_time
            trade['pts'] = float(pts)
            trade['why'] = why
            st['trade'] = trade
            st['exit_sent'] = True
            if why == 'session_end':
                st['session_end_sent'] = True
            sign = '+' if pts >= 0 else ''
            alerts.append(
                f"Crude 5m EXIT ({why}): {trade['direction'].upper()} "
                f"{trade['entry']:.0f} → {exit_px:.0f} = {sign}{pts:.0f} pts "
                f"at {exit_time}."
            )
            append_log({
                'ts': now.isoformat(), 'event': f'exit_{why}', 'date': str(today),
                'direction': trade['direction'],
                'signal_time': (st.get('signal') or {}).get('time', ''),
                'signal_price': (st.get('signal') or {}).get('price', ''),
                'reason': why, 'entry': trade['entry'], 'stop': trade['stop'],
                'target': trade['target'], 'mode': trade.get('mode', ''),
                'er': trade.get('er', ''), 'exit': exit_px, 'pts': pts,
                'option': trade.get('option', ''), 'rvol': trade.get('rvol', ''),
            })

    # Session end with no open trade / already exited: nothing extra
    # If heads-up was for earlier today but we somehow missed — already handled

    save_state(st)
    print(json.dumps({
        'alerts': alerts,
        'meta': meta,
        'state_summary': {
            'signal_used': st.get('signal_used'),
            'filtered': st.get('filtered'),
            'heads_up_sent': st.get('heads_up_sent'),
            'entry_sent': st.get('entry_sent'),
            'trade_status': (st.get('trade') or {}).get('status'),
            'exit_sent': st.get('exit_sent'),
            'signal': st.get('signal'),
            'trade': st.get('trade'),
        }
    }, default=str))

if __name__ == '__main__':
    main()
