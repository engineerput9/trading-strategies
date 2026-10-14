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
        ok = telegram.send('Test: crude alerts workflow can reach Telegram.')
        sys.exit(0 if ok else 1)
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
