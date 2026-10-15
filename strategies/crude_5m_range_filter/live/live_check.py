#!/usr/bin/env python3
"""One-shot live check for Crude 5m final strategy. Prints JSON alert or {}."""
import json, os, sys, time, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(os.environ.get('CRUDE_LIVE_DIR', str(Path(__file__).resolve().parent / 'state')))
ROOT.mkdir(parents=True, exist_ok=True)
STATE = Path(os.environ.get('CRUDE_LIVE_STATE', str(ROOT / 'live_state.json')))
LOG = Path(os.environ.get('CRUDE_LIVE_LOG', str(ROOT / 'live_log.csv')))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
sys.path.insert(0, os.environ.get('FYERS_LIB_DIR', str(Path(__file__).resolve().parents[3] / 'common' / 'fyers')))
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

# ---- Contract resolution from Fyers' public MCX symbol master (cached per day) ----
MASTER_URL = 'https://public.fyers.in/sym_details/MCX_COM.csv'
ROLL_DAYS = 2  # roll futures to next month this many calendar days before expiry

def _master_rows(day):
    import csv, io, urllib.request
    cache = ROOT / f'mcx_master_{day.isoformat()}.csv'
    if not cache.exists():
        ROOT.mkdir(parents=True, exist_ok=True)
        for old in ROOT.glob('mcx_master_*.csv'):
            try: old.unlink()
            except Exception: pass
        data = urllib.request.urlopen(MASTER_URL, timeout=20).read().decode('utf-8', 'replace')
        cache.write_text(data)
    rows = []
    for r in csv.reader(io.StringIO(cache.read_text())):
        if len(r) > 13 and r[13] == 'CRUDEOIL' and r[9].startswith('MCX:CRUDEOIL'):
            rows.append(r)
    return rows

def _exp_date(r):
    return dt.datetime.fromtimestamp(int(r[8]), IST).date()

def resolve_contracts(day):
    """Return (futures_symbol, option_prefix, option_expiry_date) for `day`.
    Futures: earliest CRUDEOIL FUT whose expiry is more than ROLL_DAYS days away.
    Options: earliest CRUDEOIL option expiry not yet passed (expiry day counts)."""
    try:
        rows = _master_rows(day)
        futs = sorted((_exp_date(r), r[9]) for r in rows if r[9].endswith('FUT'))
        fut = next(s for e, s in futs if (e - day).days > ROLL_DAYS)
        opts = sorted({(_exp_date(r), r[9][len('MCX:CRUDEOIL'):len('MCX:CRUDEOIL') + 5])
                       for r in rows if r[9][-2:] in ('CE', 'PE')})
        oexp, ocode = next((e, c) for e, c in opts if e >= day)
        return fut, 'MCX:CRUDEOIL' + ocode, oexp
    except Exception:
        # fallback: date rules (fut expiry ~19th, options 2 business days earlier)
        e = nearest_opt_exp(day)
        y, m = day.year, day.month
        if (dt.date(y, m, 19) - day).days <= ROLL_DAYS:
            m += 1
            if m > 12: y += 1; m = 1
        f = dt.date(y, m, 1)
        return (f'MCX:CRUDEOIL{str(y)[-2:]}{month_code(f)}FUT',
                f'MCX:CRUDEOIL{str(e.year)[-2:]}{month_code(e)}', e)

def option_symbol(day, K, s):
    return f"{resolve_contracts(day)[1]}{K}{'CE' if s > 0 else 'PE'}"

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

def pull_history(fyers, days_back=12, now=None):
    now = now or dt.datetime.now(IST)
    if os.environ.get('CRUDE_REPLAY_FILE'):
        return replay_history(now, days_back)
    today = now.date()
    fr = (today - dt.timedelta(days=days_back)).isoformat()
    to = today.isoformat()
    sym = resolve_contracts(today)[0]
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
    d = d[d.t + 300 <= now.timestamp() + 5].reset_index(drop=True)  # completed bars only
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

def replay_history(now, days_back):
    """Offline replay: candles from a cached raw.json-like file, only bars completed by `now`."""
    raw = json.load(open(os.environ['CRUDE_REPLAY_FILE']))
    raw = raw.get('cont', raw) if isinstance(raw, dict) else raw
    d = pd.DataFrame(raw, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    d = d.drop_duplicates('t').sort_values('t').reset_index(drop=True)
    lo = (now - dt.timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    d = d[(d.t >= lo) & (d.t + 300 <= now.timestamp())].reset_index(drop=True)
    d['dt'] = pd.to_datetime(d.t, unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
    return d, 'REPLAY'

def run_updated(now, d, fut_sym, fyers):
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
        meta['note'] = 'friday_skip'
        return alerts, meta, {}

    B = build(d, per=100, mult=3)
    x, H, L, day, flip, ci, atr = B['x'], B['H'], B['L'], B['day'], B['flip'], B['ci'], B['atr']
    n = B['n']
    if today not in B['first']:
        save_state(st)
        meta.update({'note': 'no_bars_today', 'last': str(B['dt'].iloc[-1])})
        return alerts, meta, {}

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
                opt_sym = option_symbol(today, K, s)
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
    return alerts, meta, {
            'signal_used': st.get('signal_used'),
            'filtered': st.get('filtered'),
            'heads_up_sent': st.get('heads_up_sent'),
            'entry_sent': st.get('entry_sent'),
            'trade_status': (st.get('trade') or {}).get('status'),
            'exit_sent': st.get('exit_sent'),
            'signal': st.get('signal'),
            'trade': st.get('trade'),
        }


# ======================= Agent Indicator (original) =======================
STATE_O = Path(os.environ.get('CRUDE_ORIG_STATE', str(ROOT / 'live_state_original.json')))
LOG_O = Path(os.environ.get('CRUDE_ORIG_LOG', str(ROOT / 'live_log_original.csv')))
LOG_O_COLS = ['ts', 'event', 'date', 'direction', 'signal_time', 'entry', 'stop', 'tp1', 'tp2',
              'risk', 'exit', 'exit_time', 'pts', 'option']


def _append_log_o(row):
    row = {c: row.get(c, '') for c in LOG_O_COLS}
    pd.DataFrame([row], columns=LOG_O_COLS).to_csv(LOG_O, mode='a', header=not LOG_O.exists(), index=False)


def run_original(now, d, fut_sym, fyers):
    """Original Agent Indicator, matching bt.py/trades.csv: first RF(100,3) flip of the day
    (no filters, Fridays included), entry at signal close, stop = wider of 10-bar swing or ATR14x1,
    half off at TP1 (1R), rest at TP2 (1.5R); stop never moved; stop checked first in a bar; else session close."""
    today = now.date(); alerts = []; meta = {}
    st = json.load(open(STATE_O)) if STATE_O.exists() else {}
    if st.get('date') != str(today):
        st = {'date': str(today), 'trade': None}
    B = build(d, per=100, mult=3)
    x, H, L, flip, atr = B['x'], B['H'], B['L'], B['flip'], B['atr']
    if today not in B['first']:
        return alerts, {'note': 'no_bars_today'}, st
    f0, last_i = B['first'][today], B['last'][today]
    last_dt = B['dt'].iloc[last_i]
    session_over = (now.hour > 23) or (now.hour == 23 and now.minute >= 30) or (
        last_dt.hour == 23 and last_dt.minute >= 25 and (now - last_dt).total_seconds() > 240)
    tstr = lambda k: B['dt'].iloc[k].strftime('%Y-%m-%d %H:%M')

    if st.get('trade') is None:
        sig = next((i for i in range(max(f0, B['start']), last_i + 1) if flip[i] != 0), None)
        if sig is not None:
            s = int(flip[sig]); e = float(x[sig]); sl = float(stopof(B, sig, s)); R = abs(e - sl)
            tp1, tp2 = e + s * R, e + s * 1.5 * R
            K = int(round(e / 50) * 50)
            opt_sym = option_symbol(today, K, s)
            prem = quotes(fyers, [opt_sym]).get(opt_sym) if fyers is not None else None
            opt_txt = opt_sym + (f" @ {prem:.0f}" if prem is not None else " (premium unavailable)")
            side = 'BUY' if s > 0 else 'SELL'
            st['trade'] = dict(s=s, dir=side, signal_time=tstr(sig), entry=e, stop=sl, tp1=tp1, tp2=tp2,
                               risk=R, option=opt_sym, tp1_hit=False, status='open')
            alerts.append(f"Agent Indicator: Crude 5m {side} signal at {tstr(sig)}, entry {e:.0f}. "
                          f"Stop {sl:.0f} ({R:.0f} pts), TP1 {tp1:.0f} (1R, book half), TP2 {tp2:.0f} (1.5R). "
                          f"ATM option: {opt_txt}.")
            _append_log_o(dict(ts=now.isoformat(), event='entry', date=str(today), direction=side,
                               signal_time=tstr(sig), entry=e, stop=sl, tp1=tp1, tp2=tp2, risk=R, option=opt_txt))

    t = st.get('trade')
    if t and t.get('status') == 'open':
        s, e, sl, R = t['s'], t['entry'], t['stop'], t['risk']
        k0 = next((k for k in range(f0, last_i + 1) if tstr(k) == t['signal_time']), None)
        start = (k0 + 1) if k0 is not None else f0
        why = None; tp1_hit = False
        for k in range(start, last_i + 1):
            adv = s * (e - (L[k] if s > 0 else H[k])); fav = s * ((H[k] if s > 0 else L[k]) - e)
            if adv >= R:
                why, px = 'stop', sl; break
            if fav >= R: tp1_hit = True
            if tp1_hit and not t['tp1_hit']:
                t['tp1_hit'] = True; t['tp1_time'] = tstr(k)
                alerts.append(f"Agent Indicator: Crude 5m TP1 hit at {tstr(k)} ({t['tp1']:.0f}, +{R:.0f} pts). "
                              f"Book half; rest rides to TP2 {t['tp2']:.0f}, stop stays {sl:.0f}.")
                _append_log_o(dict(ts=now.isoformat(), event='tp1', date=str(today), direction=t['dir'],
                                   signal_time=t['signal_time'], entry=e, tp1=t['tp1'], exit_time=tstr(k)))
            if fav >= 1.5 * R:
                why, px = 'TP2', t['tp2']; break
        if why is None and session_over:
            why, px, k = 'session end', float(x[last_i]), last_i
        if why:
            half1 = R if t['tp1_hit'] else s * (px - e)
            pts = (half1 + s * (px - e)) / 2
            t.update(status='closed', exit=px, exit_time=tstr(k), why=why, pts=pts)
            sign = '+' if pts >= 0 else ''
            alerts.append(f"Agent Indicator: Crude 5m EXIT ({why}): {t['dir']} {e:.0f} → {px:.0f} at {tstr(k)}. "
                          f"Trade result {sign}{pts:.0f} pts (avg of both halves"
                          f"{', TP1 booked' if t['tp1_hit'] else ''}).")
            _append_log_o(dict(ts=now.isoformat(), event=f'exit_{why}', date=str(today), direction=t['dir'],
                               signal_time=t['signal_time'], entry=e, stop=sl, tp1=t['tp1'], tp2=t['tp2'],
                               risk=R, exit=px, exit_time=tstr(k), pts=pts, option=t['option']))
    tmp = STATE_O.with_suffix('.tmp'); json.dump(st, open(tmp, 'w'), indent=2, default=str); tmp.replace(STATE_O)
    return alerts, meta, st.get('trade')


def _now():
    fake = os.environ.get('CRUDE_FAKE_NOW')
    return pd.Timestamp(fake).tz_localize('Asia/Kolkata').to_pydatetime() if fake else dt.datetime.now(IST)


def main():
    now = _now(); today = now.date()
    out = {'alerts': [], 'meta': {'now': now.isoformat(), 'today': str(today)}}
    fyers = None
    try:
        if os.environ.get('CRUDE_REPLAY_FILE'):
            d, fut_sym = pull_history(None, days_back=21, now=now)
        else:
            fyers = get_fyers()
            try:
                d, fut_sym = pull_history(fyers, days_back=21, now=now)
            except Exception as e1:
                if not _looks_like_auth(scrub(str(e1))):
                    raise
                fyers = get_fyers(force=True)  # one forced re-login, then retry
                d, fut_sym = pull_history(fyers, days_back=21, now=now)
    except Exception as e:
        err = scrub(str(e)); st = load_state()
        if st.get('fyers_auth_alerted_date') != str(today) and (
                _looks_like_auth(err) or 'history_fail' in err or 'Access' in err or 'LOGIN' in err.upper()):
            st['fyers_auth_alerted_date'] = str(today); save_state(st)
            out['alerts'].append('Crude 5m alerts (Agent Indicator + Updated Indicator): Fyers login needs refreshing (token/auth failed).')
        out['error'] = err[:200]
        print(json.dumps(out)); return
    for name, fn in (('Updated Indicator', run_updated), ('Agent Indicator', run_original)):
        try:
            a, m, summ = fn(now, d, fut_sym, fyers)
        except Exception as e:
            a, m, summ = [], {'error': scrub(str(e))[:200]}, None
        if name == 'Updated Indicator':
            a = [x if x.startswith('Updated Indicator:') else f'Updated Indicator: {x}' for x in a]
        out['alerts'] += a
        out[name] = {'meta': m, 'state': summ}
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
