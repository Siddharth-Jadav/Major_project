import pandas as pd
import numpy as np

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = (delta.clip(lower=0)).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / (loss.replace(0, np.nan))
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger(close: pd.Series, window: int = 20, num_std: float = 2.0):
    ma = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return ma, upper, lower

def compute_all_indicators(df: pd.DataFrame):
    close = df['Close'] if 'Close' in df else df['close']
    out = {}

    r = rsi(close).round(2)
    m_line, m_sig, m_hist = macd(close)
    bb_ma, bb_u, bb_l = bollinger(close)

    r_clean = r.dropna()
    out['rsi'] = {
        'series': r_clean.tolist(),
        'latest': float(r_clean.iloc[-1]) if r_clean.size else None
    }
    out['macd'] = {
        'line': m_line.dropna().tolist(),
        'signal': m_sig.dropna().tolist(),
        'hist': m_hist.dropna().tolist(),
        'hist_latest': float(m_hist.dropna().iloc[-1]) if m_hist.dropna().size else None
    }
    out['moving_averages'] = {
        'sma_50': close.rolling(50).mean().dropna().tolist(),
        'sma_200': close.rolling(200).mean().dropna().tolist(),
    }
    out['bollinger_bands'] = {
        'ma': bb_ma.dropna().tolist(),
        'upper': bb_u.dropna().tolist(),
        'lower': bb_l.dropna().tolist(),
    }
    return out
