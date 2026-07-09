# -*- coding: utf-8 -*-
"""공통 기술적 지표 계산 함수 (RSI, MACD). data_kr.py / data_us.py에서 공유."""


def rsi(close_series, period=14):
    """14일 RSI. 데이터 부족 시 None."""
    if close_series is None or len(close_series) < period + 1:
        return None
    delta = close_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return round(100 - (100 / (1 + rs)), 1)


def macd(close_series, fast=12, slow=26, signal=9):
    """
    MACD 계산.
    반환: dict(macd, macd_signal, macd_hist, golden_cross, dead_cross)
    - golden_cross: 히스토그램이 직전 <=0 에서 최근 >0 으로 전환 (통상 매수 신호로 해석)
    - dead_cross: 반대로 >=0 에서 <0 으로 전환 (통상 매도 신호로 해석)
    """
    empty = {
        "macd": None, "macd_signal": None, "macd_hist": None,
        "golden_cross": False, "dead_cross": False,
    }
    if close_series is None or len(close_series) < slow + signal:
        return empty

    ema_fast = close_series.ewm(span=fast, adjust=False).mean()
    ema_slow = close_series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    if len(hist) < 2:
        return empty

    golden = hist.iloc[-2] <= 0 and hist.iloc[-1] > 0
    dead = hist.iloc[-2] >= 0 and hist.iloc[-1] < 0

    return {
        "macd": round(float(macd_line.iloc[-1]), 2),
        "macd_signal": round(float(signal_line.iloc[-1]), 2),
        "macd_hist": round(float(hist.iloc[-1]), 2),
        "golden_cross": bool(golden),
        "dead_cross": bool(dead),
    }
