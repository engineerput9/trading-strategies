# Trading Strategies

Research, backtests and live-signal code for intraday strategies (MCX commodities, Indian indices/F&O).

> **This repository is PUBLIC.** It contains no credentials. All secrets (Fyers app id, secret, client id, PIN, TOTP key, access tokens) live **only in environment variables** on your own machine. Never commit `.env`, `.token`, logs or raw data — `.gitignore` blocks them.

## Layout
```
common/fyers/            Fyers login helper (reads env vars) + .env.example
indicators/              Pine Script indicators (TradingView)
strategies/
  crude_5m_range_filter/ Finalised MCX crude 5m strategy
    STRATEGY.md          The rules
    live/live_check.py   Live signal check (run every 5 min in session)
    backtest/            Backtest scripts (robust.py = core engine)
    results/             Summary CSVs / trade logs
  _template/             Copy this to start a new strategy
docs/GETTING_STARTED.md  Step-by-step setup guide
```

## Strategies
| Strategy | Market | TF | Status |
|---|---|---|---|
| crude_5m_range_filter | MCX Crude (front month) | 5m | Final; live alerts (paused) |

## Add a new strategy
1. Copy `strategies/_template` to `strategies/<market>_<tf>_<idea>`.
2. Write the rules in `STRATEGY.md`, implement `backtest.py`.
3. Use an in-sample / out-of-sample split; save summaries to `results/`.
4. Open a Pull Request. See `docs/GETTING_STARTED.md`.

Not investment advice.
