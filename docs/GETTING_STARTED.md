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
python fetch.py       (download 5m crude data from Fyers, once)
python optreal.py     (download real option quotes, once)
python base.py
python dynamic.py
python options.py
python rvol08.py      (FINAL plan: expect 110 trades, +7,310 pts)
python costs.py
```
The full table is in `strategies/crude_5m_range_filter/backtest/README.md`. Outputs are CSVs; open them in Excel.

## 7. Run the live check (both strategies)
```
python scripts\run_crude_alerts.py --dry-run
```
This runs the Agent Indicator and the Updated Indicator with one Fyers pull and prints the alerts. Drop `--dry-run` to also send them to Telegram, which needs the `TELEGRAM_*` env vars.
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

## 11. Telegram alerts from GitHub Actions (no PC needed)

### How it works
- **`crude-session` workflow (main):** one job per trading day stays running and checks crude about **15 seconds after every 5m candle closes**, so a 09:00 signal reaches Telegram at about 09:05:20. GitHub stops any job after 6 hours, so the day is split into 3 jobs that run one after another (to 14:30, to 19:55, and to 23:40 IST). Fyers logs in once per job.
- **Why not a run every 5 min?** A fresh run takes about 1–2 minutes to start, and GitHub's own scheduler often runs 5–15+ minutes late. Keeping one job running avoids both delays. Public repos get Actions minutes free.
- **Starting it:** cron-job.org (free, punctual) starts the session at 08:40 IST. A GitHub schedule at 08:30 IST is a backup.
- **No double alerts:** after every check, what was sent is saved on the `state` branch. A second start just waits in the queue (only one runs at a time), then reloads the saved state and stays quiet about anything already sent.
- **Messages:** a heartbeat "Crude alerts live…" once a day at the start, then each alert prefixed `Agent Indicator:` or `Updated Indicator:`. You get one warning a day if the Fyers login fails.
- **`crude-alerts` workflow:** a manual single check, plus a Telegram **test** button.

### Step 1: Telegram bot
1. In Telegram, message **@BotFather**, send `/newbot`, follow the prompts, and copy the **bot token**.
2. Send any message to your new bot. Then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy the number in `"chat":{"id": ...}`. That's your **chat id**.

### Step 2: Repo secrets
On GitHub, open the repo and go to **Settings > Secrets and variables > Actions > New repository secret**. Add each of these:
`FYERS_APP_ID`, `FYERS_SECRET_ID`, `FYERS_CLIENT_ID`, `FYERS_PIN`, `FYERS_TOTP_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (and optionally `FYERS_REDIRECT_URI`).
Secrets are encrypted and never visible to visitors, even though the repo is public.

### Step 3: Test Telegram
Go to **Actions > crude-alerts > Run workflow**, tick **test**, and click **Run workflow**. You should get "Test: crude alerts workflow can reach Telegram."

### Step 4: Personal access token for the pinger
1. Go to GitHub, then your avatar > **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**.
2. **Name:** `cron-job crude`. **Expiration:** up to 1 year (set a reminder to renew it).
3. **Repository access:** *Only select repositories* > `trading-strategies`.
4. **Permissions > Repository permissions > Actions: Read and write.** Leave everything else as is.
5. Click Generate and copy the token (it starts with `github_pat_`). Keep it only in cron-job.org.

### Step 5: cron-job.org
1. Sign up at https://cron-job.org (free), then click **Create cronjob**.
2. **Title:** `crude-session start`
3. **URL:** `https://api.github.com/repos/engineerput9/trading-strategies/actions/workflows/crude-session.yml/dispatches`
4. **Schedule:** Custom. Days of week Mon–Fri, hours `8`, minutes `40`. **Time zone: Asia/Kolkata.**
5. **Advanced:**
   - **Request method:** `POST`
   - **Headers:**
     - `Authorization: Bearer github_pat_...` (your token)
     - `Accept: application/vnd.github+json`
     - `X-GitHub-Api-Version: 2022-11-28`
     - `Content-Type: application/json`
   - **Request body:** `{"ref":"main"}`
6. Save, then click **Test run**. GitHub replies **204 No Content** when it works, and a `crude-session` run appears under Actions.
7. **Optional safety net:** create a second cronjob with the same settings at **12:00, 16:00 and 20:00 IST**. If the session ever crashed, this restarts it. While it's running, the extra start just waits and then exits.

### Daily use
- Watch it under **Actions > crude-session**. Trade logs are on the `state` branch: `live_log.csv` (Updated) and `live_log_original.csv` (Agent).
- **To pause:** go to **Actions > crude-session > ⋯ > Disable workflow**, and pause the cronjob.
- Don't also run the Crude bot's own alerts, or you'll get duplicate messages.
