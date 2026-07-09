# -*- coding: utf-8 -*-
"""
실행 진입점.
사용법:
    python main.py            # 실제 데이터 수집 시도, 실패 시 샘플 데이터로 대시보드 생성
    python main.py --demo     # 무조건 샘플 데이터로 대시보드 생성 (테스트용, 네트워크 불필요)
    python main.py --no-news  # 뉴스 수집을 건너뛰고 실행 (훨씬 빠름)
"""
import argparse
import datetime
import logging
import os

import pandas as pd

import config
import scoring
import report

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def collect_real_data(fetch_news):
    import data_kr
    import data_us

    logger.info(
        "국내 주식 데이터 수집 시작 (최대 %d종목 x %d개 시장). 시간이 꽤 걸릴 수 있습니다...",
        config.KR_TOP_N_BY_MARKETCAP, len(config.KR_MARKETS),
    )
    kr_df = data_kr.fetch_kr_stocks(
        config.KR_MARKETS,
        config.KR_TOP_N_BY_MARKETCAP,
        rsi_period=config.RSI_PERIOD,
        macd_fast=config.MACD_FAST,
        macd_slow=config.MACD_SLOW,
        macd_signal=config.MACD_SIGNAL,
        history_days=config.KR_HISTORY_DAYS,
        fetch_news=fetch_news,
        news_max_items=config.NEWS_MAX_ITEMS,
        news_sleep_sec=config.NEWS_SLEEP_SEC,
    )
    logger.info("국내 %d종목 수집 완료", len(kr_df))

    logger.info("해외 주식 데이터 수집 시작 (최대 %d종목)...", config.US_UNIVERSE_SIZE)
    us_df = data_us.fetch_us_stocks(
        config.US_FALLBACK_TICKERS,
        config.US_UNIVERSE_SIZE,
        rsi_period=config.RSI_PERIOD,
        macd_fast=config.MACD_FAST,
        macd_slow=config.MACD_SLOW,
        macd_signal=config.MACD_SIGNAL,
        history_period=config.US_HISTORY_PERIOD,
        fetch_news=fetch_news,
        news_max_items=config.NEWS_MAX_ITEMS,
    )
    logger.info("해외 %d종목 수집 완료", len(us_df))

    df = pd.concat([kr_df, us_df], ignore_index=True)
    if df.empty:
        raise RuntimeError("수집된 데이터가 없습니다.")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="샘플 데이터로만 실행 (네트워크 불필요)")
    parser.add_argument("--no-news", action="store_true", help="뉴스 수집을 건너뛰고 실행 (훨씬 빠름)")
    parser.add_argument("--output", default=None, help="출력 HTML 파일 경로")
    args = parser.parse_args()

    demo_mode = False
    error_message = None
    fetch_news = config.FETCH_NEWS and not args.no_news

    if args.demo:
        from demo_data import generate_demo_dataframe

        logger.info("데모 모드로 실행합니다 (샘플 데이터).")
        df = generate_demo_dataframe()
        demo_mode = True
    else:
        try:
            df = collect_real_data(fetch_news)
        except Exception as e:
            logger.error("실 데이터 수집 실패: %s", e)
            logger.info("샘플 데이터로 대체합니다. 인터넷 연결 및 패키지 설치를 확인해주세요.")
            from demo_data import generate_demo_dataframe

            df = generate_demo_dataframe()
            demo_mode = True
            error_message = str(e)

    scored = scoring.compute_scores(
        df, weight_valuation=config.WEIGHT_VALUATION, weight_momentum=config.WEIGHT_MOMENTUM
    )
    scored = scoring.add_sector_benchmarks(scored)
    scored = scoring.compute_signals(
        scored,
        oversold_rsi=config.OVERSOLD_RSI,
        overbought_rsi=config.OVERBOUGHT_RSI,
        volume_surge_mult=config.VOLUME_SURGE_MULT,
        undervalued_percentile=config.UNDERVALUED_PERCENTILE,
        buy_signal_min_count=config.BUY_SIGNAL_MIN_COUNT,
        sell_signal_min_count=config.SELL_SIGNAL_MIN_COUNT,
    )

    output_path = args.output or os.path.join(
        config.OUTPUT_DIR, f"dashboard_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.html"
    )
    report.build_dashboard(scored, output_path, demo_mode=demo_mode, error_message=error_message)
    logger.info("대시보드 생성 완료: %s", os.path.abspath(output_path))

    top = scored.sort_values("combined_score", ascending=False).head(config.TOP_N_RECOMMEND)
    print("\n=== 종합점수 상위 추천 종목 ===")
    for _, r in top.iterrows():
        tags = []
        if r.get("oversold"):
            tags.append("과매도")
        if r.get("undervalued"):
            tags.append("저평가")
        if r.get("volume_surge"):
            tags.append("거래량급증")
        if r.get("macd_golden_cross"):
            tags.append("MACD골든크로스")
        if r.get("news_positive"):
            tags.append("뉴스호재")
        if r.get("sell_signal"):
            tags.append("매도신호주의")
        tag_str = f" [{'/'.join(tags)}]" if tags else ""
        print(
            f"[{r['market']}] {r['name']}({r['ticker']}) "
            f"종합 {r['combined_score']:.0f}점 | PER {r['per']}(업종평균 {r['sector_avg_per']}) "
            f"RSI {r['rsi']} | MACD {r.get('macd')} | 뉴스 {r.get('news_tag')} | {r['sector']}{tag_str}"
        )


if __name__ == "__main__":
    main()
