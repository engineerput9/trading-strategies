# Agent Indicator (original) on MCX Crude 5m

Source indicator: `indicators/original-agent-indicator.pine`. Alerts are prefixed **"Agent Indicator:"**.

## Rules (exactly as backtested in `backtest/bt.py` → `results/trades.csv`)
- **Data:** MCX crude front-month continuous 5m (Fyers `cont_flag=1`), IST session 09:00 to 23:30.
- **Signal:** Range Filter, period 100, multiplier 3. A long flip happens when close > filter, the filter is rising, close changed, and the previous state was short. A short flip is the mirror.
- **One trade per day:** the first flip of the day only. No other filters (no gap, ATR-distance or volume filter, and Fridays are traded).
- **Entry:** close of the signal candle.
- **Stop:** the wider of the 10-bar swing (low for longs, high for shorts) or entry ∓ ATR14×1. Risk R = |entry − stop|.
- **Targets:** TP1 = 1R (book half), TP2 = 1.5R (book the rest). The stop is never moved.
- **Order of checks within a bar:** stop first (conservative).
- **Session end:** anything still open exits at the last 5m close of the day. No overnight holds.
- **Option suggestion:** ATM (strike rounded to 50) CE for longs, PE for shorts, nearest MCX option expiry.

## Baseline (Jun 2025 to Oct 2026, every day's first signal, no filters)
| Trades | Win % | Net pts | Avg win | Avg loss | Max DD |
|---|---|---|---|---|---|
| 340 | 45.9% | +2,509 | +86.7 | −59.8 | 1,290 |

`orig_pts` in `results/trades.csv` is each trade's points (the average of both halves).

## Files
- `backtest/bt.py`: produces `trades.csv`. Run it from a folder containing `raw.json`, which `crude_5m_range_filter/backtest/fetch.py` creates.
- `live/live_check_original.py`: runs only this strategy. In production both strategies run from `strategies/crude_5m_range_filter/live/live_check.py` using one Fyers pull (`run_original`).
