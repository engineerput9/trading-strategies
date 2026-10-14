#!/usr/bin/env python3
"""Run ONLY the Agent Indicator (original) live check. The logic lives in the shared
crude live script (run_original) so both strategies use one Fyers pull in production."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'crude_5m_range_filter', 'live'))
import live_check as lc

if __name__ == '__main__':
    now = lc._now()
    if os.environ.get('CRUDE_REPLAY_FILE'):
        fy = None; d, sym = lc.pull_history(None, days_back=21, now=now)
    else:
        fy = lc.get_fyers(); d, sym = lc.pull_history(fy, days_back=21, now=now)
    alerts, meta, st = lc.run_original(now, d, sym, fy)
    print(json.dumps({'alerts': alerts, 'state': st}, default=str))
