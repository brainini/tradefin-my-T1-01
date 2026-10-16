"""3일차 D-1 · 04: 바이어 리스크 보드 첫 화면(v1).

labs/day3/lab-d/buyer_board.csv를 읽어 계산하고 HTML 한 장을 쓴다.
실행: uv run python scripts/board_page.py
같은 입력이면 같은 결과. 원본 CSV는 읽기만 한다.
모양은 workbench/day3/outputs/design.md의 토큰(아래 TOKENS)만 쓴다.
"""

import html
import json
import math
import sys
from pathlib import Path

import pandas as pd

# design.md 2절 토큰 — 화면의 색 · 글꼴 · 크기 · 간격 · 모서리는 이 값만 쓴다
TOKENS = {
    # 2-1 색 6개
    "color-bg": "#F7F6F3",
    "color-surface": "#FFFFFF",
    "color-border": "#E2E0DB",
    "color-text": "#1C1B19",
    "color-text-muted": "#5E5B55",
    "color-accent": "#1F4E79",
    # 2-2 등급 색 4개
    "grade-s": "#1E7044",
    "grade-a": "#9CC34A",
    "grade-b": "#E8A92A",
    "grade-c": "#B8322A",
    # 2-3 글꼴
    "font-sans": "'Noto Sans KR', sans-serif",
    "weight-regular": "400",
    "weight-medium": "500",
    "weight-bold": "700",
    # 2-4 글자 크기 6단계 (줄 높이)
    "text-xs": "12px",
    "lh-xs": "1.5",
    "text-sm": "14px",
    "lh-sm": "1.5",
    "text-md": "16px",
    "lh-md": "1.6",
    "text-lg": "20px",
    "lh-lg": "1.4",
    "text-xl": "28px",
    "lh-xl": "1.3",
    "text-2xl": "40px",
    "lh-2xl": "1.2",
    # 2-5 간격 (4의 배수)
    "space-1": "4px",
    "space-2": "8px",
    "space-3": "12px",
    "space-4": "16px",
    "space-6": "24px",
    "space-8": "32px",
    "space-12": "48px",
    "space-16": "64px",
    # 2-6 모서리 · 그림자
    "radius-sm": "4px",
    "radius-md": "8px",
    "shadow": "none",
    # 2-7 레이아웃 값
    "layout-max": "1184px",
    "border-width": "1px",
}
# design.md 2-7 bp-phone — @media 조건에는 CSS 변수를 쓸 수 없어 여기서 넣는다
BP_PHONE = "720px"

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "labs" / "day3" / "lab-d" / "buyer_board.csv"
OUT = ROOT / "workbench" / "day3" / "outputs" / "buyer_board.html"

AS_OF = "2026-09-30"
BASE_LINE_PCT = 17
LINE_MIN, LINE_MAX = 5, 30
GRADES = ["S", "A", "B", "C"]

# 나라는 표기가 흔들리는 country 대신 country_code로 묶는다
COUNTRY_KO = {
    "ARE": "아랍에미리트",
    "BRA": "브라질",
    "CHN": "중국",
    "DEU": "독일",
    "EGY": "이집트",
    "GBR": "영국",
    "IDN": "인도네시아",
    "IND": "인도",
    "JPN": "일본",
    "MEX": "멕시코",
    "MYS": "말레이시아",
    "NGA": "나이지리아",
    "NLD": "네덜란드",
    "POL": "폴란드",
    "SAU": "사우디아라비아",
    "THA": "태국",
    "TUR": "튀르키예",
    "TWN": "대만",
    "USA": "미국",
    "VNM": "베트남",
}


def grade_of(p: float, line: float) -> str:
    """C부터 검사: 선 이상 C · 선의 절반 이상 B · 선의 4분의 1 이상 A · 나머지 S."""
    if p >= line:
        return "C"
    if p >= line / 2:
        return "B"
    if p >= line / 4:
        return "A"
    return "S"


def money(v) -> str:
    return f"${int(round(v)):,}"


def pct1(part, whole) -> str:
    return f"{(part / whole * 100) if whole else 0:.1f}%"


def summarize(df: pd.DataFrame, line_pct: int) -> dict:
    line = line_pct / 100
    g = df["pd_30d"].map(lambda p: grade_of(p, line))
    return {
        "grades": g,
        "count": {k: int((g == k).sum()) for k in GRADES},
        "ar": {k: int(df.loc[g == k, "open_ar_usd"].sum()) for k in GRADES},
        "region_c": {
            r: int(v) for r, v in df.loc[g == "C"].groupby("region")["open_ar_usd"].sum().items()
        },
    }


def clean(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def esc(s) -> str:
    return "–" if s is None else html.escape(str(s))


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--color-bg)}
body{color:var(--color-text);font-family:var(--font-sans);font-size:var(--text-md);line-height:var(--lh-md);font-weight:var(--weight-regular);word-break:keep-all;overflow-wrap:break-word;padding:var(--space-16) var(--space-12)}
.wrap{max-width:var(--layout-max);margin:0 auto}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.r{text-align:right}
.muted{color:var(--color-text-muted)}
.eyebrow{font-size:var(--text-xs);line-height:var(--lh-xs);font-weight:var(--weight-medium);color:var(--color-text-muted);margin-bottom:var(--space-2)}

.head{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:var(--space-4);margin-bottom:var(--space-12)}
.head h1{font-size:var(--text-xl);line-height:var(--lh-xl);font-weight:var(--weight-bold);color:var(--color-text)}
.head .sub{font-size:var(--text-sm);line-height:var(--lh-sm);color:var(--color-text-muted);margin-top:var(--space-3)}
.asof{font-size:var(--text-sm);line-height:var(--lh-sm);color:var(--color-text-muted)}
.asof b{color:var(--color-text);font-weight:var(--weight-medium)}

.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:var(--border-width) solid var(--color-border);border-bottom:var(--border-width) solid var(--color-border);margin-bottom:var(--space-12)}
.kpi{padding:var(--space-6);border-left:var(--border-width) solid var(--color-border);min-width:0}
.kpi:first-child{border-left:none;padding-left:0}
.kpi-label{display:flex;align-items:center;gap:var(--space-2);font-size:var(--text-sm);line-height:var(--lh-sm);font-weight:var(--weight-medium);color:var(--color-text-muted)}
.kpi-num{display:block;overflow:hidden;font-size:var(--text-2xl);line-height:var(--lh-2xl);font-weight:var(--weight-bold);color:var(--color-text);margin-top:var(--space-2)}
.kpi-num.step-down{font-size:var(--text-xl);line-height:var(--lh-2xl)}
.kpi-basis{font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted);margin-top:var(--space-2)}

.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:var(--space-6)}
.span-12{grid-column:span 12}
.span-8{grid-column:span 8}
.span-4{grid-column:span 4}
.card{background:var(--color-surface);border:var(--border-width) solid var(--color-border);border-radius:var(--radius-md);padding:var(--space-8);min-width:0;box-shadow:var(--shadow)}
.card h2{font-size:var(--text-lg);line-height:var(--lh-lg);font-weight:var(--weight-bold);color:var(--color-text)}
.card .desc{font-size:var(--text-sm);line-height:var(--lh-sm);color:var(--color-text-muted);margin-top:var(--space-3);margin-bottom:var(--space-6)}

.badge{display:inline-block;padding:var(--space-1) var(--space-2);border-radius:var(--radius-sm);font-size:var(--text-sm);line-height:var(--lh-sm);font-weight:var(--weight-bold);text-align:center}
.g-S{background:var(--grade-s);color:var(--color-surface)}
.g-A{background:var(--grade-a);color:var(--color-text)}
.g-B{background:var(--grade-b);color:var(--color-text)}
.g-C{background:var(--grade-c);color:var(--color-surface)}
.seg-S{fill:var(--grade-s)}
.seg-A{fill:var(--grade-a)}
.seg-B{fill:var(--grade-b)}
.seg-C{fill:var(--grade-c)}

.dist-bar{border-radius:var(--radius-sm);overflow:hidden;line-height:0}
.dist-bar svg{display:block;width:100%;height:var(--space-6)}
.legend{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--space-4);margin-top:var(--space-4);list-style:none}
.legend li{display:flex;align-items:center;gap:var(--space-3);min-width:0}
.legend .cnt{font-size:var(--text-md);line-height:var(--lh-md);font-weight:var(--weight-bold);color:var(--color-text)}
.legend .amt{display:block;font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}

.slider{border-top:var(--border-width) solid var(--color-border);margin-top:var(--space-6);padding-top:var(--space-6)}
.slider-row{display:flex;align-items:center;gap:var(--space-4)}
.slider label{font-size:var(--text-sm);line-height:var(--lh-sm);font-weight:var(--weight-medium);color:var(--color-text);white-space:nowrap}
.slider input{flex:1;min-width:0;accent-color:var(--color-accent)}
.slider output{font-size:var(--text-lg);line-height:var(--lh-lg);font-weight:var(--weight-bold);color:var(--color-accent)}
.ticks{display:flex;justify-content:space-between;font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted);margin-top:var(--space-1)}
.delta{font-size:var(--text-sm);line-height:var(--lh-sm);color:var(--color-text);margin-top:var(--space-4)}
.delta b{color:var(--color-accent);font-weight:var(--weight-bold)}
.rule{font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted);margin-top:var(--space-2)}

table{width:100%;border-collapse:collapse;font-size:var(--text-sm);line-height:var(--lh-sm)}
th{font-weight:var(--weight-medium);color:var(--color-text-muted);text-align:left;padding:var(--space-3) var(--space-2);border-bottom:var(--border-width) solid var(--color-border)}
td{color:var(--color-text);padding:var(--space-3) var(--space-2);border-bottom:var(--border-width) solid var(--color-border);vertical-align:top}
th:first-child,td:first-child{padding-left:0}
th:last-child,td:last-child{padding-right:0}
th.r,td.r{text-align:right}
td.name{font-weight:var(--weight-medium)}
td.sig{color:var(--color-text-muted)}
.top-cards{display:none;list-style:none;gap:var(--space-4)}
.bcard{border:var(--border-width) solid var(--color-border);border-radius:var(--radius-md);padding:var(--space-4);background:var(--color-surface)}
.bcard-top{display:flex;justify-content:space-between;align-items:flex-start;gap:var(--space-3)}
.bcard-name{font-size:var(--text-md);line-height:var(--lh-md);font-weight:var(--weight-bold);color:var(--color-text)}
.bcard-meta{font-size:var(--text-sm);line-height:var(--lh-sm);color:var(--color-text-muted);margin-top:var(--space-1)}
.bcard dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--space-3);margin-top:var(--space-3)}
.bcard dt{font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}
.bcard dd{font-size:var(--text-sm);line-height:var(--lh-sm);font-weight:var(--weight-medium);color:var(--color-text)}
.bcard-sig{font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted);margin-top:var(--space-3)}

.regions{list-style:none}
.regions li{padding:var(--space-3) 0;border-bottom:var(--border-width) solid var(--color-border)}
.regions li:first-child{padding-top:0}
.reg-top{display:flex;justify-content:space-between;gap:var(--space-3);font-size:var(--text-sm);line-height:var(--lh-sm)}
.reg-name{font-weight:var(--weight-medium);color:var(--color-text)}
.reg-total{font-weight:var(--weight-bold);color:var(--color-text)}
.regions svg{display:block;width:100%;height:var(--space-3);margin-top:var(--space-2)}
.bar-total{fill:var(--color-border)}
.bar-c{fill:var(--grade-c)}
.reg-c{font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted);margin-top:var(--space-1)}

.foot{border-top:var(--border-width) solid var(--color-border);margin-top:var(--space-16);padding-top:var(--space-6);font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}

@media (max-width: __BP_PHONE__){
  body{padding:var(--space-12) var(--space-4)}
  .head{margin-bottom:var(--space-6)}
  .kpis{grid-template-columns:minmax(0,1fr)}
  .kpi{border-left:none;border-top:var(--border-width) solid var(--color-border);padding:var(--space-4) 0}
  .kpi:first-child{border-top:none}
  .kpi-num{font-size:var(--text-xl);line-height:var(--lh-xl)}
  .kpi-num.step-down{font-size:var(--text-lg);line-height:var(--lh-xl)}
  .grid{grid-template-columns:minmax(0,1fr);gap:var(--space-4)}
  .span-12,.span-8,.span-4{grid-column:1 / -1}
  .card{padding:var(--space-4)}
  .legend{grid-template-columns:repeat(2,minmax(0,1fr))}
  .top-table{display:none}
  .top-cards{display:grid}
}
"""

JS = """
(function(){
  var DATA = JSON.parse(document.getElementById('board-data').textContent);
  var REGIONS = JSON.parse(document.getElementById('region-data').textContent);
  var BASE = __BASE__, GR = ['S','A','B','C'], W = 1000;
  var TOTAL = 0; DATA.forEach(function(d){ TOTAL += d.open_ar_usd; });
  var MAXR = REGIONS.length ? REGIONS[0].total : 1;

  function gradeOf(p, line){
    if (p >= line) return 'C';
    if (p >= line / 2) return 'B';
    if (p >= line / 4) return 'A';
    return 'S';
  }
  function money(v){ return '$' + Math.round(v).toLocaleString('en-US'); }
  function pct1(part, whole){ return (whole ? (part / whole * 100) : 0).toFixed(1) + '%'; }
  function stats(pct){
    var line = pct / 100, c = {S:0,A:0,B:0,C:0}, ar = {S:0,A:0,B:0,C:0}, rc = {};
    DATA.forEach(function(d){
      var g = gradeOf(d.pd_30d, line);
      c[g] += 1; ar[g] += d.open_ar_usd;
      if (g === 'C') rc[d.region] = (rc[d.region] || 0) + d.open_ar_usd;
    });
    return {line: line, count: c, ar: ar, rc: rc};
  }
  function setText(id, t){ var el = document.getElementById(id); if (el) el.textContent = t; }
  var base = stats(BASE);

  function fit(){
    var els = document.querySelectorAll('.fit');
    for (var i = 0; i < els.length; i++){
      els[i].classList.remove('step-down');
      if (els[i].scrollWidth > els[i].clientWidth) els[i].classList.add('step-down');
    }
  }

  function render(pct){
    var s = stats(pct);
    setText('line-val', pct + '%');
    setText('kpi-c-count', s.count.C + '곳');
    setText('kpi-line', '150곳 중 · 위험 선 ' + pct + '% 기준');
    setText('kpi-c-ar', money(s.ar.C));
    setText('kpi-c-share', '전체 채권의 ' + pct1(s.ar.C, TOTAL));

    var x = 0;
    GR.forEach(function(g){
      var w = s.count[g] / DATA.length * W;
      var seg = document.getElementById('seg-' + g);
      seg.setAttribute('x', x.toFixed(3)); seg.setAttribute('width', w.toFixed(3));
      x += w;
      setText('lg-cnt-' + g, s.count[g] + '곳');
      setText('lg-ar-' + g, money(s.ar[g]));
    });

    var dn = s.count.C - base.count.C, da = s.ar.C - base.ar.C;
    setText('delta-n', (dn < 0 ? '-' : '+') + Math.abs(dn) + '곳');
    setText('delta-ar', (da < 0 ? '-' : '+') + money(Math.abs(da)));

    var badges = document.querySelectorAll('.js-grade');
    for (var i = 0; i < badges.length; i++){
      var g = gradeOf(parseFloat(badges[i].getAttribute('data-pd')), s.line);
      badges[i].textContent = g;
      badges[i].className = 'badge js-grade g-' + g;
      badges[i].setAttribute('aria-label', g + '등급');
    }

    REGIONS.forEach(function(r, i){
      var v = s.rc[r.name] || 0;
      document.getElementById('rc-' + i).setAttribute('width', (v / MAXR * W).toFixed(3));
      setText('rcv-' + i, '지금 C등급 ' + money(v) + ' · ' + pct1(v, r.total));
    });
    fit();
  }

  var slider = document.getElementById('line');
  slider.addEventListener('input', function(){ render(parseInt(slider.value, 10)); });
  window.addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  render(parseInt(slider.value, 10));
})();
"""


def main() -> None:
    df = pd.read_csv(SRC, encoding="utf-8-sig")

    unknown = sorted(set(df["country_code"]) - set(COUNTRY_KO))
    if unknown:
        sys.exit(f"COUNTRY_KO에 없는 country_code: {unknown} — 한글 이름을 더한 뒤 다시 실행")
    df["country_ko"] = df["country_code"].map(COUNTRY_KO)

    n = len(df)
    total_ar = int(df["open_ar_usd"].sum())
    overdue_sum = int(df["overdue_usd"].sum())
    overdue_n = int((df["overdue_usd"] > 0).sum())
    s = summarize(df, BASE_LINE_PCT)

    # 검증: grade 열과 17% 규칙으로 다시 매긴 등급
    same = s["grades"] == df["grade"]
    print(f"[검증] grade 열 vs {BASE_LINE_PCT}% 규칙: {int(same.sum())}/{n}줄 일치")
    if not same.all():
        diff = df.loc[~same, ["buyer_id", "pd_30d", "grade"]].assign(rule=s["grades"][~same])
        print(diff.to_string(index=False))
    print("[등급별 곳 수 · 채권]")
    for g in GRADES:
        print(f"  {g}: {s['count'][g]}곳 · {money(s['ar'][g])}")
    print(f"[C등급 채권] {money(s['ar']['C'])} / 전체 {money(total_ar)} = {pct1(s['ar']['C'], total_ar)}")
    print(f"[연체] {money(overdue_sum)} · {overdue_n}곳")

    top10 = df.sort_values(["pd_30d", "buyer_id"], ascending=[False, True]).head(10)
    reg = (
        df.groupby("region")["open_ar_usd"].sum().reset_index()
        .sort_values(["open_ar_usd", "region"], ascending=[False, True])
    )
    regions = [{"name": r, "total": int(v)} for r, v in zip(reg["region"], reg["open_ar_usd"])]
    max_r = regions[0]["total"]

    cols = ["buyer_id", "buyer_name", "country_ko", "region", "open_ar_usd", "overdue_usd", "pd_30d", "signal_1"]
    records = [
        {("country" if k == "country_ko" else k): clean(v) for k, v in row.items()}
        for row in df.sort_values("buyer_id")[cols].to_dict("records")
    ]

    def js_json(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    root_css = ":root{" + "".join(f"--{k}:{v};" for k, v in TOKENS.items()) + "}"
    css = root_css + CSS.replace("__BP_PHONE__", BP_PHONE)
    js = JS.replace("__BASE__", str(BASE_LINE_PCT))

    # ② KPI
    kpis = f"""
<section class="kpis" aria-label="핵심 숫자">
  <div class="kpi">
    <div class="kpi-label">위험 바이어 <span class="badge g-C">C</span></div>
    <span class="kpi-num num fit" id="kpi-c-count">{s['count']['C']}곳</span>
    <div class="kpi-basis" id="kpi-line">150곳 중 · 위험 선 {BASE_LINE_PCT}% 기준</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">C등급 채권</div>
    <span class="kpi-num num fit" id="kpi-c-ar">{money(s['ar']['C'])}</span>
    <div class="kpi-basis" id="kpi-c-share">전체 채권의 {pct1(s['ar']['C'], total_ar)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">전체 채권</div>
    <span class="kpi-num num fit">{money(total_ar)}</span>
    <div class="kpi-basis">{n}곳 · 미결 채권 합</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">연체 금액</div>
    <span class="kpi-num num fit">{money(overdue_sum)}</span>
    <div class="kpi-basis">연체가 있는 곳 {overdue_n}곳</div>
  </div>
</section>"""

    # ③ 등급 분포 + 슬라이더
    segs, x = [], 0.0
    for g in GRADES:
        w = s["count"][g] / n * 1000
        segs.append(f'<rect id="seg-{g}" class="seg-{g}" x="{x:.3f}" y="0" width="{w:.3f}" height="24"/>')
        x += w
    legend = "".join(
        f'<li><span class="badge g-{g}">{g}</span><span><span class="cnt num" id="lg-cnt-{g}">{s["count"][g]}곳</span>'
        f'<span class="amt num" id="lg-ar-{g}">{money(s["ar"][g])}</span></span></li>'
        for g in GRADES
    )
    dist = f"""
<section class="card span-12" aria-labelledby="t-dist">
  <div class="eyebrow">신호등 등급</div>
  <h2 id="t-dist">등급별 바이어 수와 채권</h2>
  <p class="desc">막대 길이는 곳 수입니다. 위험 선을 움직이면 등급을 다시 매깁니다.</p>
  <div class="dist-bar"><svg viewBox="0 0 1000 24" preserveAspectRatio="none" role="img" aria-label="등급별 곳 수 막대">{''.join(segs)}</svg></div>
  <ul class="legend">{legend}</ul>
  <div class="slider">
    <div class="slider-row">
      <label for="line">위험 선</label>
      <input type="range" id="line" min="{LINE_MIN}" max="{LINE_MAX}" step="1" value="{BASE_LINE_PCT}" autocomplete="off">
      <output for="line" id="line-val" class="num">{BASE_LINE_PCT}%</output>
    </div>
    <div class="ticks num"><span>{LINE_MIN}%</span><span>{LINE_MAX}%</span></div>
    <p class="delta">처음 {BASE_LINE_PCT}%보다 C등급 <b class="num" id="delta-n">+0곳</b> · <b class="num" id="delta-ar">+$0</b></p>
    <p class="rule">위험 점수가 선 이상이면 C, 선의 절반 이상 B, 선의 4분의 1 이상 A, 나머지 S</p>
  </div>
</section>"""

    # ④ 위험 상위 10
    rows, cards = [], []
    line = BASE_LINE_PCT / 100
    for r in top10.itertuples():
        g = grade_of(r.pd_30d, line)
        badge = f'<span class="badge js-grade g-{g}" data-pd="{r.pd_30d!r}" aria-label="{g}등급">{g}</span>'
        sig = None if pd.isna(r.signal_1) else r.signal_1
        rows.append(
            f'<tr><td class="name">{esc(r.buyer_name)}</td><td>{esc(r.country_ko)}</td><td>{badge}</td>'
            f'<td class="r num">{pct1(r.pd_30d, 1)}</td><td class="r num">{money(r.open_ar_usd)}</td>'
            f'<td class="r num">{money(r.overdue_usd)}</td><td class="sig">{esc(sig)}</td></tr>'
        )
        cards.append(
            f'<li class="bcard"><div class="bcard-top"><span class="bcard-name">{esc(r.buyer_name)}</span>{badge}</div>'
            f'<div class="bcard-meta">{esc(r.country_ko)} · 위험 점수 <span class="num">{pct1(r.pd_30d, 1)}</span></div>'
            f'<dl><div><dt>채권</dt><dd class="num">{money(r.open_ar_usd)}</dd></div>'
            f'<div><dt>연체</dt><dd class="num">{money(r.overdue_usd)}</dd></div></dl>'
            f'<p class="bcard-sig">위험 신호 · {esc(sig)}</p></li>'
        )
    top = f"""
<section class="card span-8" aria-labelledby="t-top">
  <div class="eyebrow">이번 주 전화할 곳</div>
  <h2 id="t-top">위험 상위 10</h2>
  <p class="desc">위험 점수(30일 내 연체 가능성)가 높은 순입니다. 위험 신호는 확인해 볼 이유입니다.</p>
  <table class="top-table">
    <thead><tr><th>바이어</th><th>나라</th><th>등급</th><th class="r">위험 점수</th><th class="r">채권</th><th class="r">연체</th><th>위험 신호</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <ul class="top-cards">{''.join(cards)}</ul>
</section>"""

    # ⑤ 지역별 채권
    reg_items = []
    for i, r in enumerate(regions):
        c = s["region_c"].get(r["name"], 0)
        reg_items.append(
            f'<li><div class="reg-top"><span class="reg-name">{esc(r["name"])}</span>'
            f'<span class="reg-total num">{money(r["total"])}</span></div>'
            f'<svg viewBox="0 0 1000 12" preserveAspectRatio="none" aria-hidden="true">'
            f'<rect class="bar-total" x="0" y="0" width="{r["total"] / max_r * 1000:.3f}" height="12"/>'
            f'<rect id="rc-{i}" class="bar-c" x="0" y="0" width="{c / max_r * 1000:.3f}" height="12"/></svg>'
            f'<div class="reg-c num" id="rcv-{i}">지금 C등급 {money(c)} · {pct1(c, r["total"])}</div></li>'
        )
    region_html = f"""
<section class="card span-4" aria-labelledby="t-reg">
  <div class="eyebrow">지역별 채권</div>
  <h2 id="t-reg">돈이 어디에 물려 있나</h2>
  <p class="desc">회색은 지역 채권 합, 빨강은 그중 지금 C등급인 몫입니다.</p>
  <ul class="regions">{''.join(reg_items)}</ul>
</section>"""

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>바이어 리스크 한눈에</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap">
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header class="head">
  <div>
    <div class="eyebrow">채권관리팀 · 주간 점검</div>
    <h1>바이어 리스크 한눈에</h1>
    <p class="sub">(가상) 한빛정밀(주) 바이어 {n}곳 · 합성 데이터</p>
  </div>
  <p class="asof">기준일 <b class="num">{AS_OF}</b></p>
</header>
{kpis}
<div class="grid">
{dist}
{top}
{region_html}
</div>
<footer class="foot">(가상) 합성 데이터 · 기준일 {AS_OF} · 위험 점수는 판단을 돕는 값이고 결정은 사람이 합니다</footer>
</div>
<script type="application/json" id="board-data">{js_json(records)}</script>
<script type="application/json" id="region-data">{js_json(regions)}</script>
<script>{js}</script>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"[저장] {OUT.relative_to(ROOT).as_posix()} ({len(page.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    main()
