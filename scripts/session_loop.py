#!/usr/bin/env python3
"""Run the crude alerts once per 5m bar close (+DELAY s) until --until HH:MM IST.
State is saved to the state branch after every iteration (scripts/save_state.sh), so a
restarted/duplicate job never re-sends an alert (each strategy's state marks what was sent).
Sends a once-per-day heartbeat 'Crude alerts live'."""
import argparse, datetime as dt, json, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'common'))
import telegram
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DELAY = int(os.environ.get('BAR_DELAY_SEC', '15'))
STATE = os.environ.get('CRUDE_LIVE_DIR', os.path.join(ROOT, 'state'))


def save():
    subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'save_state.sh')], check=False)


def heartbeat(now):
    p = os.path.join(STATE, 'heartbeat.json')
    hb = json.load(open(p)) if os.path.exists(p) else {}
    if hb.get('date') != str(now.date()):
        if telegram.send(f"Crude alerts live for {now:%a %d %b} (Agent Indicator + Updated Indicator)."):
            json.dump({'date': str(now.date())}, open(p, 'w')); save()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--until', default='23:40'); a = ap.parse_args()
    hh, mm = map(int, a.until.split(':'))
    os.makedirs(STATE, exist_ok=True)
    while True:
        now = dt.datetime.now(IST)
        end = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now >= end:
            break
        if now.hour >= 9 or (now.hour == 8 and now.minute >= 55):
            heartbeat(now)
        # next bar close + DELAY
        nxt = now.replace(second=0, microsecond=0) + dt.timedelta(minutes=5 - now.minute % 5)
        nxt += dt.timedelta(seconds=DELAY)
        if nxt - dt.timedelta(minutes=5) > now:  # still within DELAY of the bar that just closed
            nxt -= dt.timedelta(minutes=5)
        if nxt >= end + dt.timedelta(minutes=1):
            break
        time.sleep(max(0, (nxt - dt.datetime.now(IST)).total_seconds()))
        if dt.datetime.now(IST).hour < 9:
            continue
        subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'run_crude_alerts.py')], check=False)
        save()


if __name__ == '__main__':
    main()
