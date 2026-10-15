#!/usr/bin/env python3
"""Run both crude 5m strategies (Agent Indicator + Updated Indicator) once and push every
alert to Telegram. Usage:
  python scripts/run_crude_alerts.py            # live run
  python scripts/run_crude_alerts.py --test     # send a Telegram test message only
  python scripts/run_crude_alerts.py --dry-run  # print alerts, don't send
State/logs go to $CRUDE_LIVE_DIR (default strategies/crude_5m_range_filter/live/state)."""
import io, json, os, sys, contextlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'common'))
sys.path.insert(0, os.path.join(ROOT, 'strategies', 'crude_5m_range_filter', 'live'))
import telegram


def main():
    if '--test' in sys.argv:
        sys.path.insert(0, os.path.join(ROOT, 'common', 'fyers'))
        try:
            import fyers_login
            sys.path.insert(0, os.path.join(ROOT, 'strategies', 'crude_5m_range_filter', 'live'))
            import live_check
            fy = fyers_login.get_fyers(force=True)
            fut_sym = live_check.resolve_contracts(__import__('datetime').date.today())[0]
            r = fy.history({'symbol': fut_sym, 'resolution': '5', 'date_format': '1',
                            'range_from': __import__('datetime').date.today().isoformat(),
                            'range_to': __import__('datetime').date.today().isoformat(), 'cont_flag': '1'})
            fmsg = f"Fyers login OK from GitHub ({fut_sym}: {len(r.get('candles') or [])} bars today)" if r.get('s') == 'ok' else 'Fyers data FAILED: ' + fyers_login.scrub(r)[:150]
        except BaseException as e:
            fmsg = 'Fyers login FAILED from GitHub: ' + type(e).__name__
            try: fmsg += ' ' + fyers_login.scrub(str(e))[:150]
            except Exception: pass
        print(fmsg)
        ok = telegram.send('Test: crude alerts workflow can reach Telegram. ' + fmsg)
        sys.exit(0 if ok and 'OK' in fmsg else 1)
    import live_check
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        live_check.main()
    out = json.loads(buf.getvalue().strip().splitlines()[-1])
    alerts = out.get('alerts', [])
    print(json.dumps({'n_alerts': len(alerts), 'error': out.get('error')}))
    for a in alerts:
        print('ALERT:', a)
        if '--dry-run' not in sys.argv:
            telegram.send(a)


if __name__ == '__main__':
    main()
