# -*- coding: utf-8 -*-
"""
데이터 수집이 실패했을 때(인터넷 연결 없음 등) 대시보드 동작을 확인할 수 있도록
제공하는 샘플 데이터 생성기. 실제 시세/뉴스가 아닙니다.
"""
import random

import pandas as pd

_KR_SAMPLE = [
    ("005930", "삼성전자", "KOSPI", "반도체"),
    ("000660", "SK하이닉스", "KOSPI", "반도체"),
    ("035420", "NAVER", "KOSPI", "인터넷"),
    ("035720", "카카오", "KOSPI", "인터넷"),
    ("051910", "LG화학", "KOSPI", "2차전지"),
    ("006400", "삼성SDI", "KOSPI", "2차전지"),
    ("373220", "LG에너지솔루션", "KOSPI", "2차전지"),
    ("207940", "삼성바이오로직스", "KOSPI", "바이오"),
    ("068270", "셀트리온", "KOSPI", "바이오"),
    ("005380", "현대차", "KOSPI", "자동차"),
    ("000270", "기아", "KOSPI", "자동차"),
    ("105560", "KB금융", "KOSPI", "금융"),
    ("055550", "신한지주", "KOSPI", "금융"),
    ("247540", "에코프로비엠", "KOSDAQ", "2차전지"),
    ("086520", "에코프로", "KOSDAQ", "2차전지"),
    ("091990", "셀트리온헬스케어", "KOSDAQ", "바이오"),
    ("263750", "펄어비스", "KOSDAQ", "게임"),
    ("293490", "카카오게임즈", "KOSDAQ", "게임"),
    ("196170", "알테오젠", "KOSDAQ", "바이오"),
    ("112040", "위메이드", "KOSDAQ", "게임"),
]

_US_SAMPLE = [
    ("AAPL", "Apple Inc.", "Technology"),
    ("MSFT", "Microsoft Corp.", "Technology"),
    ("NVDA", "NVIDIA Corp.", "Technology"),
    ("GOOGL", "Alphabet Inc.", "Communication"),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary"),
    ("META", "Meta Platforms", "Communication"),
    ("TSLA", "Tesla Inc.", "Consumer Discretionary"),
    ("JPM", "JPMorgan Chase", "Financials"),
    ("LLY", "Eli Lilly", "Healthcare"),
    ("XOM", "Exxon Mobil", "Energy"),
    ("AVGO", "Broadcom Inc.", "Technology"),
    ("V", "Visa Inc.", "Financials"),
    ("PLTR", "Palantir Technologies", "Technology"),
    ("AMD", "Advanced Micro Devices", "Technology"),
    ("COIN", "Coinbase Global", "Financials"),
]

_SAMPLE_HEADLINES = {
    1: "실적 호조, 목표주가 상향 조정",
    -1: "업황 부진 우려, 목표주가 하향",
    0: "정기 주주총회 개최 공시",
}


def _rand_row(market, ticker, name, sector, rng):
    news_score = rng.choice([-1, -1, 0, 0, 0, 1, 1, 1])
    return {
        "market": market,
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "price": round(rng.uniform(10, 500) * (1000 if market != "US" else 1), 0),
        "change_pct": round(rng.uniform(-8, 8), 2),
        "volume": int(rng.uniform(1e5, 5e6)),
        "rel_volume": round(rng.uniform(0.4, 3.5), 2),
        "rsi": round(rng.uniform(15, 85), 1) if rng.random() > 0.1 else None,
        "macd": round(rng.uniform(-5, 5), 2),
        "macd_signal_line": round(rng.uniform(-5, 5), 2),
        "macd_hist": round(rng.uniform(-2, 2), 2),
        "macd_golden_cross": rng.random() > 0.85,
        "macd_dead_cross": rng.random() > 0.9,
        "news_score": news_score,
        "news_tag": "호재" if news_score > 0 else ("악재" if news_score < 0 else "중립"),
        "news_headline": _SAMPLE_HEADLINES[news_score],
        "per": round(rng.uniform(3, 60), 1) if rng.random() > 0.1 else None,
        "pbr": round(rng.uniform(0.4, 8), 2) if rng.random() > 0.1 else None,
        "marketcap": int(rng.uniform(1e11, 5e14)),
    }


def generate_demo_dataframe(seed=42):
    rng = random.Random(seed)
    rows = []
    for ticker, name, market, sector in _KR_SAMPLE:
        rows.append(_rand_row(market, ticker, name, sector, rng))
    for ticker, name, sector in _US_SAMPLE:
        rows.append(_rand_row("US", ticker, name, sector, rng))
    return pd.DataFrame(rows)
