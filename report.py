# -*- coding: utf-8 -*-
"""
HTML 대시보드 생성 모듈 (단일 파일 산출물, 외부 서버 불필요)
"""
import datetime
import json
import os

import pandas as pd

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>주식 스크리닝 대시보드</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1117; --panel: #171a23; --border: #2a2e3a; --text: #e6e8ef;
    --muted: #9aa1b2; --accent: #4f8cff; --good: #34c38f; --bad: #f0616d; --warn: #f4c95d;
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif; }
  header { padding: 24px 32px; border-bottom: 1px solid var(--border); }
  header h1 { margin:0 0 4px; font-size: 22px; }
  header p { margin:0; color: var(--muted); font-size: 13px; }
  .banner { background:#3a2f12; color:#f4c95d; padding:10px 32px; font-size:13px; border-bottom:1px solid var(--border); }
  .container { padding: 24px 32px; }
  .tabs { display:flex; gap:8px; margin-bottom:16px; flex-wrap: wrap; }
  .tab-btn { background: var(--panel); border:1px solid var(--border); color:var(--text); padding:8px 16px; border-radius:8px; cursor:pointer; font-size:14px; }
  .tab-btn.active { background: var(--accent); border-color: var(--accent); color:#fff; }
  .card { background: var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:20px; }
  .grid { display:grid; grid-template-columns: 2.4fr 1fr; gap:20px; align-items:start; }
  table { width:100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 8px 10px; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }
  th:first-child, td:first-child, th:nth-child(2), td:nth-child(2), th:nth-child(3), td:nth-child(3) { text-align:left; }
  th { color: var(--muted); font-weight:600; cursor:pointer; user-select:none; position: sticky; top:0; background: var(--panel); }
  th:hover { color: var(--text); }
  tr:hover td { background: rgba(255,255,255,0.03); }
  .pos { color: var(--good); } .neg { color: var(--bad); }
  .sub { color: var(--muted); font-size: 11px; display:block; }
  .rsi-oversold { color: var(--good); font-weight:600; }
  .rsi-overbought { color: var(--bad); font-weight:600; }
  .filters { display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap; align-items:center; }
  select, input[type=text] { background:#11141c; border:1px solid var(--border); color:var(--text); padding:6px 10px; border-radius:6px; font-size:13px; }
  .checkbox-label { display:flex; align-items:center; gap:5px; font-size:13px; color: var(--muted); cursor:pointer; user-select:none; }
  .table-wrap { max-height: 640px; overflow:auto; }
  .theme-item { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed var(--border); font-size:13px; }
  .disclaimer { color: var(--muted); font-size:12px; line-height:1.6; margin-top: 30px; padding-top:16px; border-top:1px solid var(--border); }
  .badge { display:inline-block; padding:2px 7px; border-radius:5px; font-size:11px; margin:1px; white-space:nowrap; }
  .badge-buy { background: rgba(52,195,143,0.15); color: var(--good); border:1px solid rgba(52,195,143,0.4); }
  .badge-sell { background: rgba(240,97,109,0.15); color: var(--bad); border:1px solid rgba(240,97,109,0.4); }
  .badge-oversold { background: rgba(52,195,143,0.12); color: var(--good); }
  .badge-overbought { background: rgba(240,97,109,0.12); color: var(--bad); }
  .badge-undervalued { background: rgba(79,140,255,0.12); color: var(--accent); }
  .badge-volume { background: rgba(244,201,93,0.15); color: var(--warn); }
  .badge-news-pos { background: rgba(52,195,143,0.12); color: var(--good); }
  .badge-news-neg { background: rgba(240,97,109,0.12); color: var(--bad); }
  .badge-news-neu { background: rgba(154,161,178,0.12); color: var(--muted); }
  .news-cell { max-width: 220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:left !important; }
</style>
</head>
<body>
<header>
  <h1>📊 국내·해외 주식 스크리닝 대시보드</h1>
  <p>생성 시각: {{GENERATED_AT}} · 데이터 기준: 무료 API 지연 시세 (실시간 아님, 재실행 시에만 갱신) · 총 {{TOTAL_COUNT}}종목 분석</p>
  <p style="margin-top:4px; color:#9aa1b2; font-size:12px;">※ 장중에 생성된 경우 "상대거래량"은 그 시점까지의 거래량을 하루 기준으로 환산한 예상치입니다. 장 마감 후 재실행하면 확정치로 바뀝니다.</p>
</header>
{{BANNER}}
<div class="container">

  <div class="tabs" id="tabs"></div>

  <div class="grid">
    <div class="card">
      <div class="filters">
        <select id="sectorFilter"><option value="">전체 업종/테마</option></select>
        <input type="text" id="searchBox" placeholder="종목명 또는 코드 검색">
        <label class="checkbox-label"><input type="checkbox" id="oversoldOnly"> 과매도만</label>
        <label class="checkbox-label"><input type="checkbox" id="buySignalOnly"> 매수신호만</label>
        <label class="checkbox-label"><input type="checkbox" id="sellSignalOnly"> 매도신호만</label>
        <label class="checkbox-label"><input type="checkbox" id="newsPosOnly"> 뉴스호재만</label>
      </div>
      <div class="table-wrap">
        <table id="stockTable">
          <thead>
            <tr>
              <th data-key="name">종목</th>
              <th data-key="ticker">코드</th>
              <th data-key="sector">업종/테마</th>
              <th data-key="price">현재가</th>
              <th data-key="change_pct">등락률</th>
              <th data-key="per">PER(업종평균)</th>
              <th data-key="pbr">PBR</th>
              <th data-key="rsi">RSI</th>
              <th data-key="macd_hist">MACD</th>
              <th data-key="rel_volume">상대거래량</th>
              <th data-key="news_score">뉴스</th>
              <th data-key="combined_score">종합점수</th>
              <th data-key="signal_count">신호</th>
            </tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="card">
        <h3 style="margin-top:0;">종합점수 Top 10</h3>
        <canvas id="topChart" height="260"></canvas>
      </div>
      <div class="card">
        <h3 style="margin-top:0;">업종/테마별 평균 점수·PER Top 8</h3>
        <div id="themeList"></div>
      </div>
    </div>
  </div>

  <div class="disclaimer">
    ⚠️ 본 대시보드는 PER·PBR·RSI·MACD 등 공개 지표와, 뉴스 헤드라인에 대한 단순 키워드 매칭(진짜 AI 감성분석이
    아님)을 기준으로 한 정량 스크리닝 결과이며, 투자 추천이나 매수·매도 자문이 아닙니다. "매수 신호"/"매도 신호"/
    "과매도"/"호재" 등의 표시는 여러 규칙을 기계적으로 조합한 참고용 태그일 뿐, 실제 주가 방향을 보장하지
    않습니다. 뉴스 스크래핑은 원 사이트(네이버 금융, 야후 파이낸스)의 페이지 구조에 의존하므로 일부 종목은
    수집이 되지 않을 수 있습니다. 지표가 좋다고 해서 반드시 좋은 투자처는 아니며, 실제 투자 결정 전 반드시
    최신 공시와 재무제표, 원문 뉴스를 직접 확인하시기 바랍니다. 시세는 실시간이 아닌 지연 시세이며, 스크립트를
    재실행해야 데이터가 갱신됩니다.
  </div>
</div>

<script>
const DATA = {{DATA_JSON}};
let currentMarket = Object.keys(DATA)[0];
let sortKey = "combined_score";
let sortAsc = false;
let chart = null;

function fmt(v, digits=2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  return Number(v).toLocaleString("ko-KR", {maximumFractionDigits: digits});
}

function renderTabs() {
  const tabs = document.getElementById("tabs");
  tabs.innerHTML = "";
  Object.keys(DATA).forEach(market => {
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (market === currentMarket ? " active" : "");
    btn.textContent = market + " (" + DATA[market].length + ")";
    btn.onclick = () => { currentMarket = market; renderTabs(); populateSectorFilter(); renderAll(); };
    tabs.appendChild(btn);
  });
}

function populateSectorFilter() {
  const sel = document.getElementById("sectorFilter");
  const sectors = [...new Set(DATA[currentMarket].map(r => r.sector))].sort();
  sel.innerHTML = '<option value="">전체 업종/테마</option>' + sectors.map(s => `<option value="${s}">${s}</option>`).join("");
}

function getFiltered() {
  let rows = DATA[currentMarket];
  const sector = document.getElementById("sectorFilter").value;
  const q = document.getElementById("searchBox").value.trim().toLowerCase();
  const oversoldOnly = document.getElementById("oversoldOnly").checked;
  const buySignalOnly = document.getElementById("buySignalOnly").checked;
  const sellSignalOnly = document.getElementById("sellSignalOnly").checked;
  const newsPosOnly = document.getElementById("newsPosOnly").checked;
  if (sector) rows = rows.filter(r => r.sector === sector);
  if (q) rows = rows.filter(r => r.name.toLowerCase().includes(q) || r.ticker.toLowerCase().includes(q));
  if (oversoldOnly) rows = rows.filter(r => r.oversold);
  if (buySignalOnly) rows = rows.filter(r => r.buy_signal);
  if (sellSignalOnly) rows = rows.filter(r => r.sell_signal);
  if (newsPosOnly) rows = rows.filter(r => r.news_positive);
  rows = [...rows].sort((a, b) => {
    const va = a[sortKey], vb = b[sortKey];
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });
  return rows;
}

function rsiClass(rsi) {
  if (rsi === null || rsi === undefined) return "";
  if (rsi <= 30) return "rsi-oversold";
  if (rsi >= 70) return "rsi-overbought";
  return "";
}

function macdCell(r) {
  const cls = (r.macd_hist ?? 0) >= 0 ? "pos" : "neg";
  let tag = "";
  if (r.macd_golden_cross) tag = ' <span class="sub" style="display:inline;color:var(--good)">골든</span>';
  if (r.macd_dead_cross) tag = ' <span class="sub" style="display:inline;color:var(--bad)">데드</span>';
  return `<span class="${cls}">${fmt(r.macd_hist)}</span>${tag}`;
}

function newsBadgeClass(tag) {
  if (tag === "호재") return "badge-news-pos";
  if (tag === "악재") return "badge-news-neg";
  return "badge-news-neu";
}

function signalBadges(r) {
  let badges = "";
  if (r.buy_signal) badges += '<span class="badge badge-buy">매수신호</span>';
  if (r.sell_signal) badges += '<span class="badge badge-sell">매도신호</span>';
  if (r.oversold) badges += '<span class="badge badge-oversold">과매도</span>';
  if (r.overbought) badges += '<span class="badge badge-overbought">과매수</span>';
  if (r.undervalued) badges += '<span class="badge badge-undervalued">저평가</span>';
  if (r.volume_surge) badges += '<span class="badge badge-volume">거래량급증</span>';
  return badges || '<span class="sub">-</span>';
}

function renderTable() {
  const rows = getFiltered();
  const tbody = document.getElementById("tableBody");
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.name}</td>
      <td>${r.ticker}</td>
      <td>${r.sector}</td>
      <td>${fmt(r.price, 0)}</td>
      <td class="${r.change_pct >= 0 ? 'pos' : 'neg'}">${r.change_pct >= 0 ? '+' : ''}${fmt(r.change_pct)}%</td>
      <td>${fmt(r.per)}<span class="sub">업종평균 ${fmt(r.sector_avg_per)}</span></td>
      <td>${fmt(r.pbr)}</td>
      <td class="${rsiClass(r.rsi)}">${fmt(r.rsi, 0)}</td>
      <td>${macdCell(r)}</td>
      <td>${fmt(r.rel_volume)}x</td>
      <td class="news-cell" title="${(r.news_headline || '').replace(/"/g,'&quot;')}">
        <span class="badge ${newsBadgeClass(r.news_tag)}">${r.news_tag || '중립'}</span>
        ${r.news_headline ? '<span class="sub">' + r.news_headline + '</span>' : ''}
      </td>
      <td><b>${fmt(r.combined_score, 0)}</b></td>
      <td>${signalBadges(r)}</td>
    </tr>
  `).join("");
}

function renderChart() {
  const top = [...DATA[currentMarket]].sort((a,b) => b.combined_score - a.combined_score).slice(0, 10);
  const ctx = document.getElementById("topChart");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: top.map(r => r.name),
      datasets: [{ label: "종합점수", data: top.map(r => r.combined_score), backgroundColor: "#4f8cff" }]
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { max: 100, ticks: { color: "#9aa1b2" }, grid: { color: "#2a2e3a" } },
        y: { ticks: { color: "#e6e8ef" }, grid: { display: false } }
      }
    }
  });
}

function renderThemes() {
  const rows = DATA[currentMarket];
  const bySector = {};
  rows.forEach(r => {
    if (!bySector[r.sector]) bySector[r.sector] = { scores: [], pers: [] };
    bySector[r.sector].scores.push(r.combined_score);
    if (r.per !== null && r.per !== undefined && r.per > 0) bySector[r.sector].pers.push(r.per);
  });
  const avgs = Object.entries(bySector)
    .map(([sector, v]) => ({
      sector,
      avgScore: v.scores.reduce((a,b)=>a+b,0)/v.scores.length,
      avgPer: v.pers.length ? v.pers.reduce((a,b)=>a+b,0)/v.pers.length : null,
      n: v.scores.length
    }))
    .sort((a,b) => b.avgScore - a.avgScore)
    .slice(0, 8);
  document.getElementById("themeList").innerHTML = avgs.map(t => `
    <div class="theme-item">
      <span>${t.sector} <span style="color:var(--muted)">(${t.n})</span></span>
      <span><b>${t.avgScore.toFixed(1)}점</b> <span class="sub" style="display:inline">PER ${t.avgPer ? t.avgPer.toFixed(1) : '-'}</span></span>
    </div>
  `).join("");
}

function renderAll() {
  renderTable();
  renderChart();
  renderThemes();
}

document.querySelectorAll("#stockTable th").forEach(th => {
  th.addEventListener("click", () => {
    const key = th.dataset.key;
    if (sortKey === key) sortAsc = !sortAsc; else { sortKey = key; sortAsc = false; }
    renderTable();
  });
});
document.getElementById("sectorFilter").addEventListener("change", renderAll);
document.getElementById("searchBox").addEventListener("input", renderTable);
document.getElementById("oversoldOnly").addEventListener("change", renderTable);
document.getElementById("buySignalOnly").addEventListener("change", renderTable);
document.getElementById("sellSignalOnly").addEventListener("change", renderTable);
document.getElementById("newsPosOnly").addEventListener("change", renderTable);

renderTabs();
populateSectorFilter();
renderAll();
</script>
</body>
</html>
"""


def build_dashboard(df, output_path, demo_mode=False, error_message=None):
    """
    df: scoring.compute_scores() + add_sector_benchmarks() + compute_signals() 결과 DataFrame
    market 컬럼 값별로 그룹화해 JSON으로 임베드한다.
    """
    data = {}
    clean = df.where(pd.notna(df), None)
    for market, g in clean.groupby("market"):
        data[market] = g.to_dict(orient="records")

    banner = ""
    if demo_mode:
        banner = (
            '<div class="banner">⚠️ 데이터 수집에 실패하여 샘플(데모) 데이터로 표시 중입니다. '
            "인터넷 연결과 패키지 설치 상태를 확인한 뒤 다시 실행해주세요."
            + (f" (오류: {error_message})" if error_message else "")
            + "</div>"
        )

    html = (
        TEMPLATE.replace("{{GENERATED_AT}}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        .replace("{{TOTAL_COUNT}}", str(len(df)))
        .replace("{{BANNER}}", banner)
        .replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False))
    )

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
