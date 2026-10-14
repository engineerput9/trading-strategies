# Trading Strategies

Research, backtests and live-signal code for intraday strategies (MCX commodities, Indian indices/F&O).

> **This repository is PUBLIC.** It contains no credentials. All secrets (Fyers app id, secret, client id, PIN, TOTP key, access tokens) live **only in environment variables** on your own machine. Never commit `.env`, `.token`, logs or raw data — `.gitignore` blocks them.

## Layout
```
common/fyers/            Fyers login helper (reads env vars) + .env.example
common/telegram.py       Telegram sender (env vars)
scripts/                 run_crude_alerts.py (one check), session_loop.py (bar-close loop), load/save_state.sh
.github/workflows/       crude-session.yml (live), crude-alerts.yml (manual/test)
indicators/              Pine Script indicators (TradingView)
strategies/
  crude_5m_range_filter/ Finalised MCX crude 5m strategy
    STRATEGY.md          The rules
    live/live_check.py   Live signal check (run every 5 min in session)
    backtest/            Minimal pipeline to reproduce the final plan (see its README)
    results/             Final trade logs (dynamic_trades, rvol08_trades, monthly)
  crude_5m_agent_indicator_original/  Original Agent Indicator (baseline) on crude 5m
  _template/             Copy this to start a new strategy
docs/GETTING_STARTED.md  Step-by-step setup guide
```

## Strategies
| Strategy | Market | TF | Status |
|---|---|---|---|
| crude_5m_range_filter ("Updated Indicator") | MCX Crude (front month) | 5m | Final; live alerts |
| crude_5m_agent_indicator_original ("Agent Indicator") | MCX Crude (front month) | 5m | Baseline; live alerts |

## Live alerts (Telegram via GitHub Actions)
- `.github/workflows/crude-session.yml` is the main workflow. It's a session-long job that checks 15 s after every 5m bar close, so alerts arrive within about 30 s. cron-job.org starts it daily, and a GitHub schedule is the backup.
- `.github/workflows/crude-alerts.yml` runs a single manual check or a Telegram test.
- `scripts/run_crude_alerts.py` does one Fyers pull, runs both strategies, and sends to Telegram with the `Agent Indicator:` or `Updated Indicator:` prefix.
- State and logs are kept on the `state` branch, which prevents repeat alerts.

Setup is in `docs/GETTING_STARTED.md` §11.

## Add a new strategy
1. Copy `strategies/_template` to `strategies/<market>_<tf>_<idea>`.
2. Write the rules in `STRATEGY.md`, implement `backtest.py`.
3. Use an in-sample / out-of-sample split; save summaries to `results/`.
4. Open a Pull Request. See `docs/GETTING_STARTED.md`.

Not investment advice.
