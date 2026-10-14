# Crude backtests
Run from this folder (`cd strategies/crude_5m_range_filter/backtest`).
1. `python fetch.py` pulls 5m MCX crude from Fyers into local cache files (git-ignored; needs env vars).
2. `python robust.py` core parameterised engine; `dynamic.py` final dynamic-stop plan; `rvol08.py` adds the 0.8x volume skip; `costs.py`, `options.py` costs and option P&L.
Other scripts are research experiments (filters, losers, 15m, targets, small SL, overnight, rr fix).
Outputs CSVs here; copy small summaries into `../results/`.
