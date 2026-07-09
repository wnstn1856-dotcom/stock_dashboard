# -*- coding: utf-8 -*-
"""
뉴스 헤드라인 수집 및 간단 키워드 기반 호재/악재 판별.
- 국내: 네이버 금융 종목 뉴스 페이지 스크래핑 (비공식 페이지 구조 사용, 네이버가 마크업을
  바꾸면 깨질 수 있음 -> 실패해도 예외처리되어 프로그램 전체는 계속 진행됨)
- 해외: yfinance Ticker.news (야후 파이낸스 제공, 필드명이 버전에 따라 달라질 수 있어
  여러 필드명을 순차 시도)

주의: 진짜 감성분석(NLP)이 아니라 단순 키워드 매칭 기반 참고 지표입니다.
"""
import logging
import time

logger = logging.getLogger(__name__)

POSITIVE_KEYWORDS_KO = [
    "상향", "신기록", "최대 실적", "흑자전환", "수주", "계약 체결", "특허", "승인",
    "호실적", "어닝서프라이즈", "목표주가 상향", "배당 확대", "자사주 매입", "인수",
    "파트너십", "신제품", "급등", "강세", "매수의견", "사상 최대", "돌파", "훈풍",
]
NEGATIVE_KEYWORDS_KO = [
    "하향", "적자", "급락", "소송", "리콜", "상장폐지", "유상증자", "목표주가 하향",
    "매도의견", "횡령", "배임", "부도", "부진", "경고", "감사의견 거절", "구조조정",
    "감산", "실적 쇼크", "급감",
]
POSITIVE_KEYWORDS_EN = [
    "upgrade", "beat", "record", "surge", "partnership", "acquisition", "patent",
    "approval", "buyback", "dividend increase", "outperform", "raises guidance",
    "strong demand", "all-time high", "soars", "rally",
]
NEGATIVE_KEYWORDS_EN = [
    "downgrade", "miss", "lawsuit", "recall", "plunge", "bankruptcy", "investigation",
    "cuts guidance", "underperform", "weak demand", "layoffs", "probe", "sinks", "slump",
]


def _score_headlines(headlines, lang="ko"):
    pos = POSITIVE_KEYWORDS_KO if lang == "ko" else [p.lower() for p in POSITIVE_KEYWORDS_EN]
    neg = NEGATIVE_KEYWORDS_KO if lang == "ko" else [n.lower() for n in NEGATIVE_KEYWORDS_EN]
    score = 0
    for h in headlines:
        text = h.lower() if lang == "en" else h
        if any(k in text for k in pos):
            score += 1
        if any(k in text for k in neg):
            score -= 1
    return score


def fetch_kr_news(ticker, max_items=5, timeout=4):
    """네이버 금융 종목 뉴스 목록에서 최신 헤드라인 몇 개를 가져온다. 실패 시 빈 리스트."""
    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://finance.naver.com/item/news_news.naver?code={ticker}&page=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=timeout)
        res.encoding = "euc-kr"
        soup = BeautifulSoup(res.text, "html.parser")
        titles = [a.get_text(strip=True) for a in soup.select("td.title a")]
        titles = [t for t in titles if t][:max_items]
        return titles
    except Exception as e:
        logger.debug("국내 뉴스 수집 실패 (%s): %s", ticker, e)
        return []


def fetch_us_news(yf_ticker, max_items=5):
    """yfinance Ticker 객체에서 최신 뉴스 헤드라인 몇 개를 가져온다. 실패 시 빈 리스트."""
    try:
        news_items = yf_ticker.news or []
        titles = []
        for item in news_items[:max_items]:
            title = item.get("title")
            if not title and isinstance(item.get("content"), dict):
                title = item["content"].get("title")
            if title:
                titles.append(title)
        return titles
    except Exception as e:
        logger.debug("해외 뉴스 수집 실패: %s", e)
        return []


def analyze_kr_ticker_news(ticker, max_items=5, sleep_sec=0.15):
    headlines = fetch_kr_news(ticker, max_items=max_items)
    if sleep_sec:
        time.sleep(sleep_sec)
    score = _score_headlines(headlines, lang="ko")
    tag = "호재" if score > 0 else ("악재" if score < 0 else "중립")
    return {
        "news_score": score,
        "news_tag": tag,
        "news_headline": headlines[0] if headlines else None,
        "news_count": len(headlines),
    }


def analyze_us_ticker_news(yf_ticker, max_items=5):
    headlines = fetch_us_news(yf_ticker, max_items=max_items)
    score = _score_headlines(headlines, lang="en")
    tag = "호재" if score > 0 else ("악재" if score < 0 else "중립")
    return {
        "news_score": score,
        "news_tag": tag,
        "news_headline": headlines[0] if headlines else None,
        "news_count": len(headlines),
    }
