# MCX Crude Oil 5m Strategy (Final, updated 12 Oct 2026: RVOL filter on locked trades)

## Instrument and timeframe
MCX CRUDEOIL front-month futures, 5-minute chart, MCX session 09:00-23:30 IST.

## Signal
- Original Agent Indicator: Range Filter flip, period 100, multiplier 3.
- Max ONE signal per day (first valid flip).

## Skip the day/signal if
- It is Friday.
- Opening gap > 0.5 ATR and the gap filled before the signal.
- Price is less than 4 ATR above the prior-day low.

## RVOL filter (choppy/locked trades only)
- RVOL = signal-bar volume / average volume of the same time-of-day 5m bar over the prior 10 trading days (needs at least 5 such bars).
- If the trade would be in locked (choppy) mode and RVOL < 0.8, skip it. Tight (smooth) trades are never filtered. If RVOL can't be calculated, take the trade.

## Entry
- At the close 2 candles after the signal, only if the Range Filter still points the same way and the stop has not been touched.

## Stop and target (dynamic)
- Smooth move (20-bar efficiency ratio > 0.295): stop = 2 x 5m ATR from entry; target = signal price +/- 2.5 x original indicator risk.
- Choppy move (ER <= 0.295): stop = 1.5 x indicator stop (wider of 10-bar swing or ATR14 x 1); target = signal price +/- 1.5 x original risk, full exit.
- Efficiency ratio = |close - close 20 bars ago| / sum of |bar-to-bar close changes| over 20 bars.

## Exit
- Stop or target, otherwise session end. No overnight hold, no breakeven, no early exit.

## Backtest (Fyers continuous 5m, Jun 2025 - 12 Oct 2026)
| Case | Trades | Win | Net pts | Rs/lot | Max DD | Losing streak |
|---|---|---|---|---|---|---|
| Futures, gross (with RVOL filter) | 110 | 45.5% | +7,310 | 7.31 L | 277 (11 Jun-14 Jul 2026) | 6 |
| Futures, charges + 3 pt slippage | 110 | 45.5% | +6,793 | 6.79 L | - | 6 |
| ATM options (modelled), after costs | 110 | 43.6% | +3,975 | 3.98 L | 159 | - |
| Previous plan, no RVOL filter (gross) | 142 | 46.5% | +7,597 | 7.60 L | 495 | 9 |

- Jun 2025-Mar 2026: +3,510 | Apr-Oct 2026: +3,800 (futures gross); after costs +3,209 / +3,584.
- Tight 69 trades +3,647; locked 41 trades +3,663. Avg win +189 / avg loss -36 pts.
- The filter skipped 32 locked trades (16 wins / 16 losses, +286.5 pts in total). It gives up about 4% of futures points and cuts drawdown by 44%. Negative months went from 3 to 1. On options it was better in both periods.
- Thresholds either side: below 0.7 gave +7,198 with a 426 drawdown; below 0.9 gave +6,978 with a 277 drawdown.

## Caveats
- The RVOL filter (0.8) was the best Jun-Mar setting but did not beat the plan on futures points in both periods; it was adopted to cut drawdown. Volume around contract rolls in the continuous series is distorted.
- Continuous series is not roll-adjusted; stops assumed filled at stop price.
- Several settings are near peak (RF multiplier, 2-bar wait, targets): expect live results 15-25% lower.
- Recent locked-mode stops are 110-230 pts: size positions on actual stop distance.
- Options: 137 of 142 trades priced with Black-76 model (expired option data unavailable).
- Paper-trade a few weeks before going live.
