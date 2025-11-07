from __future__ import annotations
import os
import pandas as pd
from typing import List

CSV_DEFAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "yfinance_supported_tickers.csv"))
POSSIBLE_COLS = ["symbol", "ticker", "Ticker", "SYMBOL"]

def load_supported_tickers(csv_path: str | None = None) -> List[str]:
    """
    Load tickers from CSV. Accepts flexible column names.
    Returns a de-duplicated, upper-cased list (preserves suffixes like .NS, .BO).
    """
    path = os.path.abspath(csv_path or CSV_DEFAULT)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Tickers CSV not found at: {path}")

    df = pd.read_csv(path)
    col = next((c for c in POSSIBLE_COLS if c in df.columns), None)
    if not col:
        raise ValueError(f"No ticker column found in CSV. Expected one of {POSSIBLE_COLS}")

    tickers = (
        df[col]
        .dropna()
        .astype(str)
        .map(str.strip)
        .map(str.upper)
        .tolist()
    )

    # de-duplicate while preserving order
    seen = set()
    unique = []
    for t in tickers:
        if t and t not in seen:
            seen.add(t)
            unique.append(t)
    return unique
