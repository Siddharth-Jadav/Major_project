from __future__ import annotations
import os, csv
from typing import Dict, Any, List

_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "stock_static_100.csv"))
_cache_rows: List[Dict[str, Any]] | None = None

# fields that should be numeric (we'll try to convert)
_NUMERIC_FIELDS = {
    "price": float,
    "previous_close": float,
    "change": float,
    "change_pct": float,
    "market_cap": int,
    "pe": float,
    "roe": float,
    "debt_to_equity": float,
    "eps": float,
    "rsi": float,
    "macd_hist": float,
    "sma_50": float,
    "sma_200": float,
    "bb_ma": float,
    "bb_upper": float,
    "bb_lower": float,
    "recommendation_score": int,
}

def _convert(v: str, typ):
    if v is None or v == "":
        return None
    try:
        return typ(v)
    except Exception:
        try:
            return typ(str(v).replace(',', ''))
        except Exception:
            return None

def _load_rows() -> List[Dict[str, Any]]:
    global _cache_rows
    if _cache_rows is not None:
        return _cache_rows
    if not os.path.exists(_CSV_PATH):
        raise FileNotFoundError(f"Static CSV not found at: {_CSV_PATH}")

    rows: List[Dict[str, Any]] = []
    with open(_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in reader.fieldnames or []]
        if "symbol" not in headers:
            raise ValueError("CSV must contain a 'symbol' column")
        for r in reader:
            clean = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
            # numeric conversions
            for key, typ in _NUMERIC_FIELDS.items():
                if key in clean:
                    clean[key] = _convert(clean[key], typ)
            rows.append(clean)

    _cache_rows = rows
    return _cache_rows

def list_symbols(q: str = "", limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    rows = _load_rows()
    symbols = [str(r.get("symbol", "")).strip() for r in rows if r.get("symbol")]
    if q:
        q_up = q.strip().upper()
        symbols = [s for s in symbols if q_up in s.upper()]
    total = len(symbols)
    page = symbols[offset: offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "data": page}

def _find_row(symbol: str) -> Dict[str, Any] | None:
    s = (symbol or "").strip().upper()
    rows = _load_rows()
    # exact match
    for r in rows:
        sym = str(r.get("symbol", "")).upper()
        if sym == s:
            return r
    # loose match (without suffix)
    base = s.split(".")[0]
    for r in rows:
        sym = str(r.get("symbol", "")).upper()
        if sym.split(".")[0] == base:
            return r
    return None

def quote_for_symbol(symbol: str) -> Dict[str, Any]:
    row = _find_row(symbol)
    if not row:
        raise ValueError(f"Symbol not found in static dataset: {symbol}")
    return {
        "symbol": row.get("symbol"),
        "price": row.get("price"),
        "currency": row.get("currency", "INR"),
        "previous_close": row.get("previous_close"),
        "change": row.get("change"),
        "change_pct": row.get("change_pct"),
        "market_cap": row.get("market_cap"),
        "ts": row.get("updated_at"),
        "status": "ok",
    }

def quotes_all(limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    rows = _load_rows()
    total = len(rows)
    page = rows[offset: offset + limit]
    data = []
    for r in page:
        data.append({
            "symbol": r.get("symbol"),
            "price": r.get("price"),
            "currency": r.get("currency", "INR"),
            "previous_close": r.get("previous_close"),
            "change": r.get("change"),
            "change_pct": r.get("change_pct"),
            "market_cap": r.get("market_cap"),
            "ts": r.get("updated_at"),
            "status": "ok",
        })
    return {"total": total, "limit": limit, "offset": offset, "data": data}

def fundamentals_for_symbol(symbol: str) -> Dict[str, Any]:
    row = _find_row(symbol)
    if not row:
        raise ValueError(f"Symbol not found in static dataset: {symbol}")
    return {
        "trailingPe": row.get("pe"),
        "returnOnEquity": row.get("roe"),
        "debtToEquity": row.get("debt_to_equity"),
        "marketCap": row.get("market_cap"),
        "epsTrailingTwelveMonths": row.get("eps"),
    }

def technicals_for_symbol(symbol: str) -> Dict[str, Any]:
    row = _find_row(symbol)
    if not row:
        raise ValueError(f"Symbol not found in static dataset: {symbol}")
    return {
        "rsi": { "series": [], "latest": row.get("rsi") },
        "macd": { "line": [], "signal": [], "hist": [], "hist_latest": row.get("macd_hist") },
        "moving_averages": {
            "sma_50": [], "sma_200": [],
            "sma50_latest": row.get("sma_50"),
            "sma200_latest": row.get("sma_200"),
        },
        "bollinger_bands": {
            "ma": [], "upper": [], "lower": [],
            "ma_latest": row.get("bb_ma"),
            "upper_latest": row.get("bb_upper"),
            "lower_latest": row.get("bb_lower"),
        },
    }

def summary_for_symbol(symbol: str) -> Dict[str, Any]:
    row = _find_row(symbol)
    if not row:
        raise ValueError(f"Symbol not found in static dataset: {symbol}")
    score_val = row.get("recommendation_score")
    try:
        score = int(score_val) if score_val is not None else 0
    except Exception:
        score = 0
    signal = row.get("recommendation") or "Hold"

    reasons = []
    rsi = row.get("rsi"); macd_hist = row.get("macd_hist")
    pe = row.get("pe"); roe = row.get("roe"); de = row.get("debt_to_equity")
    if rsi is not None and 45 <= float(rsi) <= 60: reasons.append("RSI in neutral-to-positive zone")
    if macd_hist is not None and float(macd_hist) > 0: reasons.append("MACD histogram positive (bullish momentum)")
    if pe is not None and 0 < float(pe) < 35: reasons.append("Reasonable P/E valuation")
    if roe is not None and float(roe) > 0.12: reasons.append("Healthy ROE (>12%)")
    if de is not None and float(de) < 1.0: reasons.append("Low debt")

    return {
        "score": score,
        "signal": signal,
        "reasons": reasons,
        "technicals": technicals_for_symbol(symbol),
        "fundamentals": fundamentals_for_symbol(symbol),
    }
