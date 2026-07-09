# -*- coding: utf-8 -*-
"""
해외(미국) 주식 데이터 수집 모듈
- yfinance: PER/PBR/등락률/거래량/섹터(테마 근사치) (야후 파이낸스, 지연 시세)
- indicators: RSI, MACD
- news: yfinance 뉴스 헤드라인 기반 호재/악재 참고 지표
"""
import datetime
import logging
from zoneinfo import ZoneInfo

import pandas as pd

import indicators
import news as news_mod

logger = logging.getLogger(__name__)


def _us_trading_progress():
    """
    지금이 미국 정규장 중(09:30~16:00 ET)이면 경과 비율(0~1)을 반환.
    장 마감 후/장 시작 전이면 1.0(보정 불필요). 장 시작 직후 노이즈 완화를 위해 최소 0.15로 clamp.
    (공휴일/조기폐장 등은 반영하지 않은 단순 근사치)
    """
    now = datetime.datetime.now(ZoneInfo("America/New_York"))
    open_t = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if now.weekday() >= 5 or now <= open_t or now >= close_t:
        return 1.0
    elapsed = (now - open_t).total_seconds()
    total = (close_t - open_t).total_seconds()
    return min(max(elapsed / total, 0.15), 1.0)


def _get_sp500_tickers(limit):
    """위키피디아 S&P500 목록을 시도, 실패하면 None 반환."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        symbols = tables[0]["Symbol"].tolist()
        symbols = [s.replace(".", "-") for s in symbols]  # BRK.B -> BRK-B 형식 통일
        return symbols[:limit]
    except Exception as e:
        logger.warning("S&P500 목록을 가져오지 못했습니다, fallback 리스트 사용: %s", e)
        return None


def fetch_us_stocks(
    fallback_tickers,
    universe_size,
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    history_period="9mo",
    fetch_news=True,
    news_max_items=5,
):
    """
    해외 주식 데이터를 수집해 DataFrame으로 반환.
    columns: market, ticker, name, sector, price, change_pct, volume, rel_volume,
             rsi, macd, macd_signal_line, macd_hist, macd_golden_cross, macd_dead_cross,
             news_score, news_tag, news_headline, per, pbr, marketcap
    """
    import yfinance as yf

    tickers = _get_sp500_tickers(universe_size) or fallback_tickers
    n_total = len(tickers)

    trading_progress = _us_trading_progress()
    if trading_progress < 1.0:
        logger.info(
            "미국 장중 감지 (경과 약 %.0f%%) - 상대거래량을 예상 하루 거래량 기준으로 보정합니다.",
            trading_progress * 100,
        )

    rows = []
    for i, symbol in enumerate(tickers, start=1):
        if i % 25 == 0:
            logger.info("해외 종목 상세 지표 수집 중... (%d/%d)", i, n_total)
        try:
            t = yf.Ticker(symbol)
            info = t.info
            hist = t.history(period=history_period)

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev_close = info.get("previousClose")
            change_pct = (
                ((price - prev_close) / prev_close * 100)
                if price and prev_close
                else None
            )
            volume = info.get("volume") or info.get("regularMarketVolume")
            avg_volume = info.get("averageVolume")
            volume_adjusted = (volume / trading_progress) if volume else None
            rel_volume = (volume_adjusted / avg_volume) if volume_adjusted and avg_volume else None

            close = hist["Close"] if hist is not None and not hist.empty else None
            rsi = indicators.rsi(close, period=rsi_period)
            m = indicators.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)

            if fetch_news:
                try:
                    n = news_mod.analyze_us_ticker_news(t, max_items=news_max_items)
                except Exception as e:
                    logger.debug("종목 %s 뉴스 수집 실패: %s", symbol, e)
                    n = {"news_score": 0, "news_tag": "중립", "news_headline": None}
            else:
                n = {"news_score": 0, "news_tag": "중립", "news_headline": None}

            rows.append(
                {
                    "market": "US",
                    "ticker": symbol,
                    "name": info.get("shortName", symbol),
                    "sector": info.get("sector", "기타"),
                    "price": price,
                    "change_pct": change_pct,
                    "volume": volume,
                    "rel_volume": rel_volume,
                    "rsi": rsi,
                    "macd": m["macd"],
                    "macd_signal_line": m["macd_signal"],
                    "macd_hist": m["macd_hist"],
                    "macd_golden_cross": m["golden_cross"],
                    "macd_dead_cross": m["dead_cross"],
                    "news_score": n["news_score"],
                    "news_tag": n["news_tag"],
                    "news_headline": n["news_headline"],
                    "per": info.get("trailingPE"),
                    "pbr": info.get("priceToBook"),
                    "marketcap": info.get("marketCap"),
                }
            )
        except Exception as e:
            logger.warning("종목 %s 데이터 수집 실패: %s", symbol, e)
            continue

    return pd.DataFrame(rows)
