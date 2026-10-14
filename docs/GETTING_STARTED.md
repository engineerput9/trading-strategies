# Getting Started (step by step, Windows-friendly)

## 1. See the repo online
Open https://github.com/engineerput9/trading-strategies and sign in. Click folders to browse; click any `.md` file to read it nicely formatted. CSVs in `results/` show as tables.

## 2. Install the tools (one time)
1. **Git**: https://git-scm.com/download/win and accept defaults.
2. **Python 3.11+**: https://www.python.org/downloads/ and **tick "Add Python to PATH"**.
3. **VS Code**: https://code.visualstudio.com/ (add the "Python" extension). *Or* **GitHub Desktop**: https://desktop.github.com/ if you prefer buttons over commands.

## 3. Get the code on your PC
- GitHub Desktop: File > Clone repository > pick `engineerput9/trading-strategies`.
- Or in a terminal (VS Code: Terminal > New Terminal):
```
git clone https://github.com/engineerput9/trading-strategies.git
cd trading-strategies
```

## 4. Python environment
```
python -m venv venv
venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

## 5. Fyers credentials (stay on YOUR PC only)
This repo is public, so secrets go in environment variables, never in files you commit.
1. Copy `common/fyers/.env.example` to `common/fyers/.env` (git-ignored).
2. Fill in the values from your Fyers API dashboard.
3. Load them in PowerShell before running scripts:
```
Get-Content common\fyers\.env | ? { $_ -match '^[A-Z_]+=' } | % { $k,$v = $_ -split '=',2; Set-Item "env:$k" $v }
```
The login token is cached in `common/fyers/.token` (git-ignored) and refreshes daily.

## 6. Run a backtest
```
cd strategies\crude_5m_range_filter\backtest
python fetch.py       (download 5m crude data, once)
python dynamic.py     (final plan)
python rvol08.py      (final plan + 0.8x volume skip)
```
Results are written as CSVs. Open them in Excel or VS Code.

## 7. Run the live check
```
cd strategies\crude_5m_range_filter\live
python live_check.py
```
Run every 5 minutes during MCX hours (Task Scheduler on Windows). It keeps `live_state.json` / `live_log.csv` locally (git-ignored).

## 8. Add a new strategy
1. Copy `strategies/_template` to e.g. `strategies/gold_15m_breakout`.
2. Write the rules in `STRATEGY.md`, then the code in `backtest.py`.
3. Run it and save summaries to `results/`.

## 9. Branch, commit, Pull Request
```
git checkout -b gold-15m-breakout      (new branch for your idea)
git add .
git commit -m "Add gold 15m breakout backtest"
git push -u origin gold-15m-breakout
```
On GitHub, click **Compare & pull request**, review the changes, then **Merge**. Then `git checkout main` and `git pull`.
GitHub Desktop: Current branch > New branch, then Commit, Push, and Create Pull Request.

**Before every commit:** make sure no `.env`, `.token`, or file containing keys is staged (`git status`).

## 10. Asking the Crude bot to work on it
Just message it in chat, e.g.:
- "Add a gold 15m strategy from the template and backtest it, open a PR."
- "Change the crude stop to 1.2x ATR on a branch and compare results."
- "Update results/ with this week's live trades."
The bot works on a branch, pushes, and sends you the PR link to review and merge.
