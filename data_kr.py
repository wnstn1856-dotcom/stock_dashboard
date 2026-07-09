# -*- coding: utf-8 -*-
"""
국내 주식 데이터 수집 모듈
- pykrx: PER/PBR/거래량/등락률 등 시세·펀더멘털 (한국거래소 원천, 지연 시세)
- FinanceDataReader: 업종(테마 근사치) 정보
- indicators: RSI, MACD
- news: 네이버 금융 뉴스 헤드라인 기반 호재/악재 참고 지표
"""
import datetime
import logging

import pandas as pd

import indicators
import news as news_mod

logger = logging.getLogger(__name__)


def _latest_business_day():
    """
    pykrx는 휴장일/장중(당일 미확정)에 빈 데이터나 예외를 던질 수 있으므로,
    최근 영업일을 찾을 때까지 하루씩 이전으로 내려가며 재시도한다.
    """
    from pykrx import stock

    day = datetime.date.today()
    last_error = None
    for _ in range(15):
        ds = day.strftime("%Y%m%d")
        try:
            df = stock.get_market_cap(ds, market="KOSPI")
            if df is not None and not df.empty:
                return ds
        except Exception as e:
            last_error = e
            logger.debug("날짜 %s 데이터 조회 실패, 이전 영업일로 재시도: %s", ds, e)
        day -= datetime.timedelta(days=1)
    raise RuntimeError(f"최근 영업일 데이터를 찾을 수 없습니다. (마지막 오류: {last_error})")


def _load_sector_map():
    """FinanceDataReader로 종목별 업종(테마 근사치) 매핑을 가져온다. 미설치/실패 시 빈 dict."""
    try:
        import FinanceDataReader as fdr

        df = fdr.StockListing("KRX-DESC")
        code_col = "Symbol" if "Symbol" in df.columns else "Code"
        sector_col = None
        for cand in ("Sector", "업종", "Industry"):
            if cand in df.columns:
                sector_col = cand
                break
        if sector_col is None:
            return {}
        return dict(zip(df[code_col], df[sector_col].fillna("기타")))
    except Exception as e:
        logger.warning("업종 정보를 가져오지 못했습니다 (기타로 표기): %s", e)
        return {}


def fetch_kr_stocks(
    markets,
    top_n_by_marketcap,
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    history_days=150,
    fetch_news=True,
    news_max_items=5,
    news_sleep_sec=0.15,
):
    """
    국내 시장 데이터를 수집해 DataFrame으로 반환.
    columns: market, ticker, name, sector, price, change_pct, volume, rel_volume,
             rsi, macd, macd_signal_line, macd_hist, macd_golden_cross, macd_dead_cross,
             news_score, news_tag, news_headline, per, pbr, marketcap
    """
    from pykrx import stock

    date = _latest_business_day()
    sector_map = _load_sector_map()

    frames = []
    for market in markets:
        cap = stock.get_market_cap(date, market=market)
        fundamental = stock.get_market_fundamental(date, market=market)
        ohlcv = stock.get_market_ohlcv(date, market=market)

        df = cap.join(fundamental, how="left").join(
            ohlcv[["등락률"]], how="left"
        )
        df = df.sort_values("시가총액", ascending=False).head(top_n_by_marketcap)
        df["market"] = market
        frames.append(df)

    merged = pd.concat(frames)
    merged.index.name = "ticker"
    merged = merged.reset_index()

    n_total = len(merged)
    rel_vols, rsis = {}, {}
    macds, macd_signals, macd_hists, goldens, deads = {}, {}, {}, {}, {}
    news_scores, news_tags, news_heads = {}, {}, {}

    end = date
    start = (
        datetime.datetime.strptime(date, "%Y%m%d") - datetime.timedelta(days=history_days)
    ).strftime("%Y%m%d")

    for i, ticker in enumerate(merged["ticker"], start=1):
        if i % 50 == 0:
            logger.info("국내 종목 상세 지표 수집 중... (%d/%d)", i, n_total)
        try:
            hist = stock.get_market_ohlcv(start, end, ticker)
            if len(hist) >= 5:
                avg20 = hist["거래량"].iloc[-21:-1].mean() if len(hist) > 1 else hist["거래량"].mean()
                today_vol = hist["거래량"].iloc[-1]
                rel_vols[ticker] = (today_vol / avg20) if avg20 else 1.0
            else:
                rel_vols[ticker] = 1.0

            close = hist["종가"]
            rsis[ticker] = indicators.rsi(close, period=rsi_period)
            m = indicators.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
            macds[ticker] = m["macd"]
            macd_signals[ticker] = m["macd_signal"]
            macd_hists[ticker] = m["macd_hist"]
            goldens[ticker] = m["golden_cross"]
            deads[ticker] = m["dead_cross"]
        except Exception as e:
            logger.debug("종목 %s 시세 지표 계산 실패: %s", ticker, e)
            rel_vols[ticker] = 1.0
            rsis[ticker] = None
            macds[ticker] = macd_signals[ticker] = macd_hists[ticker] = None
            goldens[ticker] = deads[ticker] = False

        if fetch_news:
            try:
                n = news_mod.analyze_kr_ticker_news(
                    ticker, max_items=news_max_items, sleep_sec=news_sleep_sec
                )
                news_scores[ticker] = n["news_score"]
                news_tags[ticker] = n["news_tag"]
                news_heads[ticker] = n["news_headline"]
            except Exception as e:
                logger.debug("종목 %s 뉴스 수집 실패: %s", ticker, e)
                news_scores[ticker] = 0
                news_tags[ticker] = "중립"
                news_heads[ticker] = None
        else:
            news_scores[ticker] = 0
            news_tags[ticker] = "중립"
            news_heads[ticker] = None

    merged["rel_volume"] = merged["ticker"].map(rel_vols).fillna(1.0)
    merged["rsi"] = merged["ticker"].map(rsis)
    merged["macd"] = merged["ticker"].map(macds)
    merged["macd_signal_line"] = merged["ticker"].map(macd_signals)
    merged["macd_hist"] = merged["ticker"].map(macd_hists)
    merged["macd_golden_cross"] = merged["ticker"].map(goldens).fillna(False)
    merged["macd_dead_cross"] = merged["ticker"].map(deads).fillna(False)
    merged["news_score"] = merged["ticker"].map(news_scores).fillna(0)
    merged["news_tag"] = merged["ticker"].map(news_tags).fillna("중립")
    merged["news_headline"] = merged["ticker"].map(news_heads)
    merged["name"] = merged["ticker"].apply(stock.get_market_ticker_name)
    merged["sector"] = merged["ticker"].map(sector_map).fillna("기타")

    out = pd.DataFrame(
        {
            "market": merged["market"],
            "ticker": merged["ticker"],
            "name": merged["name"],
            "sector": merged["sector"],
            "price": merged["종가"],
            "change_pct": merged["등락률"],
            "volume": merged["거래량"],
            "rel_volume": merged["rel_volume"],
            "rsi": merged["rsi"],
            "macd": merged["macd"],
            "macd_signal_line": merged["macd_signal_line"],
            "macd_hist": merged["macd_hist"],
            "macd_golden_cross": merged["macd_golden_cross"],
            "macd_dead_cross": merged["macd_dead_cross"],
            "news_score": merged["news_score"],
            "news_tag": merged["news_tag"],
            "news_headline": merged["news_headline"],
            "per": merged["PER"].replace(0, pd.NA),
            "pbr": merged["PBR"].replace(0, pd.NA),
            "marketcap": merged["시가총액"],
        }
    )
    return out
