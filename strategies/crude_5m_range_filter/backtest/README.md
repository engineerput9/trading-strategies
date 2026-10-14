# Crude 5m final plan: backtest pipeline

Run everything from this folder: `cd strategies/crude_5m_range_filter/backtest`

| Step | Command | Needs | Produces |
|---|---|---|---|
| 1 | `python fetch.py` | Fyers env vars | `raw.json` (5m MCX crude cache) |
| 2 | `python optreal.py` | Fyers env vars, `../results/dynamic_trades.csv` | `optraw.json` (real option quotes, where available) |
| 3 | `python base.py` | raw.json | `_add.pkl` (base 5m/15m signals) |
| 4 | `python dynamic.py` | raw.json | `dynamic.csv` (dynamic stop: tight vs locked study) |
| 5 | `python options.py` | _add.pkl, optraw.json | `options_pnl.csv` (Black-76 option P&L) |
| 6 | `python rvol08.py` | raw.json, options_pnl.csv | `rvol08_trades.csv`, `rvol08_monthly.csv`: **final plan** |
| 7 | `python costs.py` | raw.json | `costs.csv` (brokerage/slippage breakeven) |

Steps 1 and 2 are the only ones that call Fyers. Run them outside 09:15 to 09:30 IST. Steps 3 to 7 run offline.

Engine files (don't run directly): `add5m.py` (Range Filter + signal engine), `_ss_head.py`, `_rv_base.py` (final-plan trade builder + volume features), `robust.py` (parameterised engine used by costs.py).

Expected step 6 result: 142 base trades, 110 kept after the volume skip, **+7,310 pts gross**.
Outputs land here and are git-ignored; copy final ones to `../results/` if you want them published.
