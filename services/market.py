from __future__ import annotations
import time
from typing import Dict, Any, Iterable, List, Tuple

import pandas as pd
import yfinance as yf

from services.indicators import compute_all_indicators
from utils.cache import cache


def _normalize_symbol(symbol: str) -> str:
    return (symbol or '').strip().upper()


def _fetch_hist_once(symbol: str, period: str, interval: str) -> pd.DataFrame:
    t = yf.Ticker(symbol)
    df = t.history(period=period, interval=interval, actions=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={c: c.title() for c in df.columns})
    return df.reset_index().rename(columns={"Date": "date"})


def fetch_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Tries multiple symbol candidates and (period, interval) combinations to reduce yfinance 'empty' cases.
    """
    symbol = _normalize_symbol(symbol)
    key = f"hist:{symbol}:{period}:{interval}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    candidates = [symbol] if '.' in symbol else [symbol, f"{symbol}.NS", f"{symbol}.BO"]
    # Try some reasonable combinations if the provided one fails
    combos: List[Tuple[str, str]] = [
        (period, interval),
        ("6mo", "1d"),
        ("3mo", "1d"),
        ("1mo", "1d"),
        ("1y", "1wk"),
        ("max", "1wk"),
    ]

    tried = []
    for cand in candidates:
        for p, iv in combos:
            tried.append(f"{cand}({p},{iv})")
            df = _fetch_hist_once(cand, p, iv)
            if not df.empty:
                cache.set(key, df)
                return df

    raise ValueError(f"No price history found for symbol: {symbol}. Tried: {', '.join(tried)}")


def fetch_info(symbol: str) -> Dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    key = f"info:{symbol}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    info: Dict[str, Any] = {}
    candidates = [symbol] if '.' in symbol else [symbol, f"{symbol}.NS", f"{symbol}.BO"]
    for candidate in candidates:
        try:
            t = yf.Ticker(candidate)
            fi = t.fast_info or {}
            info.update(fi or {})
            try:
                full = t.info
                if isinstance(full, dict):
                    info.update(full)
            except Exception:
                pass
            if info:
                break
        except Exception:
            continue

    if not info:
        raise ValueError(f"Could not fetch fundamentals for symbol: {symbol}")
    cache.set(key, info)
    return info


def technicals(symbol: str, period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
    df = fetch_history(symbol, period, interval)
    return compute_all_indicators(df)


def fundamentals(symbol: str) -> Dict[str, Any]:
    info = fetch_info(symbol)
    keys = [
        "trailingPe",
        "forwardPe",
        "returnOnEquity",
        "debtToEquity",
        "marketCap",
        "epsTrailingTwelveMonths",
    ]
    return {k: info.get(k) for k in keys}


def rule_based_summary(symbol: str) -> Dict[str, Any]:
    ind = technicals(symbol)
    f = fundamentals(symbol)

    score = 0
    reasons = []

    # RSI
    rsi_latest = ind.get("rsi", {}).get("latest")
    if rsi_latest is not None:
        if 45 <= rsi_latest <= 60:
            score += 1; reasons.append("RSI in neutral-to-positive zone")
        elif rsi_latest < 35:
            score -= 1; reasons.append("RSI indicates oversold (bearish risk)")
        elif rsi_latest > 70:
            score -= 1; reasons.append("RSI indicates overbought (pullback risk)")

    # MACD histogram
    macd_hist = ind.get("macd", {}).get("hist_latest")
    if macd_hist is not None and macd_hist > 0:
        score += 1; reasons.append("MACD histogram positive (bullish momentum)")

    # Fundamentals
    pe = f.get("trailingPe")
    if pe and pe > 0 and pe < 35:
        score += 1; reasons.append("Reasonable P/E valuation")

    roe = f.get("returnOnEquity")
    if roe and roe > 0.12:
        score += 1; reasons.append("Healthy ROE (>12%)")

    de = f.get("debtToEquity")
    if de is not None and de < 100:
        score += 1; reasons.append("Manageable debt (D/E < 100)")

    if score >= 4:
        signal = "Strong Buy"
    elif score == 3:
        signal = "Buy"
    elif score == 2:
        signal = "Hold"
    elif score == 1:
        signal = "Weak Hold"
    else:
        signal = "Sell"

    return {
        "score": score,
        "signal": signal,
        "reasons": reasons,
        "technicals": ind,
        "fundamentals": f,
    }


# --------------------------
# Batch quotes (with tuning)
# --------------------------

def _chunks(seq: Iterable[str], size: int) -> Iterable[list[str]]:
    buf: list[str] = []
    for s in seq:
        buf.append(s)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def fetch_quotes(symbols: List[str], chunk_size: int = 25, sleep_ms: int = 200) -> list[dict]:
    """
    Fetch latest 'live-ish' quotes for many symbols.
    Tries fast_info; falls back to last close via history.
    Chunked to avoid rate limits.
    Returns: list of dicts with
      symbol, price, currency, previous_close, change, change_pct, market_cap, ts
    """
    out: list[dict] = []
    now = int(time.time())
    symbols = [_normalize_symbol(s) for s in symbols if s]

    for batch in _chunks(symbols, chunk_size):
        for sym in batch:
            item = {
                "symbol": sym,
                "price": None,
                "currency": None,
                "previous_close": None,
                "change": None,
                "change_pct": None,
                "market_cap": None,
                "ts": now,
            }
            candidates = [sym] if '.' in sym else [sym, f"{sym}.NS", f"{sym}.BO"]
            for c in candidates:
                try:
                    t = yf.Ticker(c)
                    fi = t.fast_info or {}

                    price = fi.get("last_price") or fi.get("lastPrice") or fi.get("last_trade") or fi.get("regularMarketPrice")
                    prev = fi.get("previous_close") or fi.get("previousClose") or fi.get("regularMarketPreviousClose")
                    curr = fi.get("currency")
                    mcap = fi.get("market_cap") or fi.get("marketCap")

                    if not price:
                        h = t.history(period="5d", interval="1d", actions=False)
                        if h is not None and not h.empty:
                            price = float(h["Close"].iloc[-1])
                            prev = float(h["Close"].iloc[-2]) if len(h) > 1 else None

                    if price is not None:
                        item["price"] = float(price)
                    if prev is not None:
                        item["previous_close"] = float(prev)
                    if item["price"] is not None and item["previous_close"] is not None and item["previous_close"]:
                        item["change"] = round(item["price"] - item["previous_close"], 4)
                        item["change_pct"] = round(100.0 * item["change"] / item["previous_close"], 3)
                    if curr:
                        item["currency"] = curr
                    if mcap:
                        try:
                            item["market_cap"] = int(mcap)
                        except Exception:
                            pass
                    break
                except Exception:
                    continue

            out.append(item)

        # small delay per chunk to avoid rate limits
        time.sleep(max(0, sleep_ms) / 1000.0)

    return out
