# -*- coding: utf-8 -*-
"""
종합 스코어링 로직
- 밸류에이션 점수: PER/PBR가 낮을수록(동일 시장 내 상대적으로) 높은 점수
- 모멘텀 점수: 등락률, 상대거래량(평소 대비 거래량 급증)이 높을수록 높은 점수
- 종합 점수 = 가중합 (0~100)
- 업종/테마 평균 PER·PBR 대비 비교
- 과매도(RSI)·저평가·거래량급증·MACD 골든크로스·뉴스 호재 규칙 기반 매수 신호
- 과매수·MACD 데드크로스·뉴스 악재 규칙 기반 매도 신호
"""
import pandas as pd


def _percentile_score(series, ascending_is_good=True):
    """
    시리즈를 0~100 백분위 점수로 변환.
    ascending_is_good=True  -> 값이 작을수록 100점에 가까움 (예: PER)
    ascending_is_good=False -> 값이 클수록 100점에 가까움 (예: 등락률)
    결측치는 중앙값(50점) 처리.
    """
    s = series.copy()
    valid = s.dropna()
    if valid.empty:
        return pd.Series(50.0, index=series.index)

    ranks = valid.rank(pct=True, ascending=ascending_is_good)
    scores = ranks * 100
    return scores.reindex(series.index).fillna(50.0)


def compute_scores(df, weight_valuation=0.5, weight_momentum=0.5):
    """
    df: market, ticker, name, sector, price, change_pct, volume, rel_volume, rsi, per, pbr, marketcap ...
    시장(market)별로 그룹을 나눠 상대 점수를 매긴 뒤 합친다 (국내/해외, KOSPI/KOSDAQ 간 지표 스케일이 달라서).
    """
    total_w = weight_valuation + weight_momentum
    w_val = weight_valuation / total_w
    w_mom = weight_momentum / total_w

    out_frames = []
    for market, g in df.groupby("market"):
        g = g.copy()

        # PER, PBR: 0 이하(적자/이상치)는 매우 나쁜 값으로 취급
        per_clean = g["per"].where(g["per"] > 0)
        pbr_clean = g["pbr"].where(g["pbr"] > 0)

        per_score = _percentile_score(per_clean, ascending_is_good=True)
        pbr_score = _percentile_score(pbr_clean, ascending_is_good=True)
        valuation_score = (per_score.fillna(10) + pbr_score.fillna(10)) / 2

        change_score = _percentile_score(g["change_pct"], ascending_is_good=False)
        relvol_score = _percentile_score(g["rel_volume"], ascending_is_good=False)
        momentum_score = (change_score + relvol_score) / 2

        g["valuation_score"] = valuation_score.round(1)
        g["momentum_score"] = momentum_score.round(1)
        g["combined_score"] = (w_val * valuation_score + w_mom * momentum_score).round(1)

        out_frames.append(g)

    result = pd.concat(out_frames).sort_values("combined_score", ascending=False)
    return result.reset_index(drop=True)


def add_sector_benchmarks(df):
    """
    같은 시장(market) 내 같은 업종/테마(sector)의 평균 PER·PBR을 각 행에 붙여준다.
    -> '이 종목 PER이 업종 평균보다 싼가?'를 바로 비교할 수 있게 함.
    """
    df = df.copy()
    per_valid = df["per"].where(df["per"] > 0)
    pbr_valid = df["pbr"].where(df["pbr"] > 0)

    group_keys = [df["market"], df["sector"]]
    df["sector_avg_per"] = per_valid.groupby(group_keys).transform("mean").round(1)
    df["sector_avg_pbr"] = pbr_valid.groupby(group_keys).transform("mean").round(2)

    # 업종 평균 대비 몇 % 저평가/고평가인지
    df["per_vs_sector_pct"] = (
        (df["per"] - df["sector_avg_per"]) / df["sector_avg_per"] * 100
    ).round(1)
    return df


def compute_signals(
    df,
    oversold_rsi=30,
    overbought_rsi=70,
    volume_surge_mult=2.0,
    undervalued_percentile=70,
    buy_signal_min_count=3,
    sell_signal_min_count=2,
):
    """
    규칙 기반 참고 지표를 추가한다 (투자 자문이 아닌 정량 스크리닝 보조 지표):

    매수 신호 후보 (5개 중 buy_signal_min_count 개 이상 -> buy_signal=True):
    - oversold: RSI 과매도
    - undervalued: 시장 내 밸류에이션 점수 상위 (PER/PBR가 상대적으로 낮음)
    - volume_surge: 평소 대비 거래량 급증
    - macd_golden_cross: MACD 히스토그램이 음수 -> 양수로 전환
    - news_positive: 최근 헤드라인 키워드 스코어가 양수 ("호재")

    매도 신호 후보 (3개 중 sell_signal_min_count 개 이상 -> sell_signal=True):
    - overbought: RSI 과매수
    - macd_dead_cross: MACD 히스토그램이 양수 -> 음수로 전환
    - news_negative: 최근 헤드라인 키워드 스코어가 음수 ("악재")
    """
    df = df.copy()

    df["oversold"] = df["rsi"].fillna(50) <= oversold_rsi
    df["overbought"] = df["rsi"].fillna(50) >= overbought_rsi
    df["undervalued"] = df["valuation_score"] >= undervalued_percentile
    df["volume_surge"] = df["rel_volume"].fillna(0) >= volume_surge_mult

    if "macd_golden_cross" not in df.columns:
        df["macd_golden_cross"] = False
    if "macd_dead_cross" not in df.columns:
        df["macd_dead_cross"] = False
    df["macd_golden_cross"] = df["macd_golden_cross"].fillna(False)
    df["macd_dead_cross"] = df["macd_dead_cross"].fillna(False)

    if "news_score" not in df.columns:
        df["news_score"] = 0
    df["news_score"] = df["news_score"].fillna(0)
    df["news_positive"] = df["news_score"] > 0
    df["news_negative"] = df["news_score"] < 0

    df["signal_count"] = (
        df["oversold"].astype(int)
        + df["undervalued"].astype(int)
        + df["volume_surge"].astype(int)
        + df["macd_golden_cross"].astype(int)
        + df["news_positive"].astype(int)
    )
    df["buy_signal"] = df["signal_count"] >= buy_signal_min_count

    df["sell_signal_count"] = (
        df["overbought"].astype(int)
        + df["macd_dead_cross"].astype(int)
        + df["news_negative"].astype(int)
    )
    df["sell_signal"] = df["sell_signal_count"] >= sell_signal_min_count

    return df
