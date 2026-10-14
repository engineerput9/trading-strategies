"""Template backtest. Copy the folder, then fill in signals() and the exit logic."""
import os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common", "fyers"))
RESULTS = os.path.join(HERE, "results")


def load_data() -> pd.DataFrame:
    """Return OHLCV with a datetime index. Cache raw pulls under data/ (git-ignored)."""
    raise NotImplementedError


def signals(df: pd.DataFrame) -> pd.Series:
    """+1 long, -1 short, 0 none per bar."""
    raise NotImplementedError


def backtest(df, sig):
    trades = []  # dicts: date, side, entry, stop, target, exit, pts
    return pd.DataFrame(trades)


if __name__ == "__main__":
    os.makedirs(RESULTS, exist_ok=True)
    df = load_data()
    t = backtest(df, signals(df))
    t.to_csv(os.path.join(RESULTS, "trades.csv"), index=False)
    if len(t):
        print(f"trades={len(t)} win%={(t.pts>0).mean()*100:.1f} net={t.pts.sum():.0f}")
