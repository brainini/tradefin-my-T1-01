"""3일차 실습 C: 한빛식당 밥 예보 페이지 — workbench/day3/outputs/hanbit_lunch.html을 계산해서 쓴다

실행: uv run python scripts/lunch_page.py
입력: workbench/day3/outputs/lunch_clean.csv (정제된 표) · labs/day3/lab-c/nutritionist_memo.md (믿음 글)
출력: workbench/day3/outputs/hanbit_lunch.html — 손으로 고치지 않는다. 같은 입력이면 같은 페이지.
구역: 머리 → 영양사님 감 검증 (다음 단계에서 구역을 더한다)
페이지 규칙: 파일 하나 · 데이터는 페이지 안 JSON · fetch 없음 · 외부 스크립트는 Chart.js 4.4.1 하나 · 글꼴 Noto Sans KR
"""

import html
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

CLEAN = "workbench/day3/outputs/lunch_clean.csv"
MEMO = "labs/day3/lab-c/nutritionist_memo.md"
OUT = Path("workbench/day3/outputs/hanbit_lunch.html")
CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"
GAP = 2.0  # 100명당 2명 이상 차이 = '차이 있음' (사람이 정한 선)

ACCENT, WARN, GRAY_BAR = "#1F6FB2", "#C2410C", "#B8BEC6"

df = pd.read_csv(CLEAN, encoding="utf-8-sig")
df["행사"] = df["행사"].fillna("")
df["per100"] = df["식수"] / df["출근예정"] * 100  # 출근 100명당 식수
base = df[(df["행사"] == "") & (df["월급날"] == 0)]  # 행사 없고 월급날 아닌 날

# 메모의 믿음 글: "1. **굵은 글** 덧붙인 글"
beliefs_text = {}
for line in Path(MEMO).read_text(encoding="utf-8").splitlines():
    m = re.match(r"^(\d)\. \*\*(.+?)\*\*\s*(.*)$", line)
    if m:
        beliefs_text[int(m.group(1))] = (m.group(2), m.group(3))


def grp(label, rows, highlight):
    return {"label": label, "value": round(float(rows["per100"].mean()), 1),
            "raw": float(rows["per100"].mean()), "n": int(len(rows)), "hl": highlight}


def verdict(subj, other, expect):
    """expect = 믿음이 말하는 방향('higher' · 'lower'). 차이는 반올림 전 값으로 판정."""
    diff = subj["raw"] - other["raw"]
    if abs(diff) < GAP:
        return "반만", diff
    return ("맞음" if (diff > 0) == (expect == "higher") else "틀림"), diff


def sentence(subj, other, diff):
    word = "많다" if diff > 0 else "적다"
    return f"{subj['label']}이 {other['label']}보다 100명당 {abs(diff):.1f}명 {word}."


# ---- 감 검증 계산
cards = []


def pair_card(no, subj, other, expect, extra=""):
    v, diff = verdict(subj, other, expect)
    title, sub = beliefs_text[no]
    cards.append({"id": f"b{no}", "kind": f"믿음 {no}", "title": title, "sub": sub, "badge": v,
                  "groups": [subj, other], "line": sentence(subj, other, diff) + extra, "diff": round(diff, 1)})


weather_rain = base[base["날씨"] == "비"]
weather_sun = base[base["날씨"] == "맑음"]
pair_card(1, grp("비 오는 날", weather_rain, True), grp("맑은 날", weather_sun, False), "higher")

pair_card(2, grp("금요일", base[base["요일"] == "금"], True),
          grp("월–목", base[base["요일"].isin(list("월화수목"))], False), "lower")

# 믿음 3: 메뉴별(높은 순) — 돈가스가 1등이고 2등보다 2명 이상 많으면 맞음, 1등과 2명 안쪽이면 반만, 그 밖은 틀림
menu = [grp(k, g, k == "돈가스") for k, g in base.groupby("메인메뉴")]
menu.sort(key=lambda g: (-g["raw"], g["label"]))
top, second = menu[0], menu[1]
don = next(g for g in menu if g["label"] == "돈가스")
don_rank = menu.index(don) + 1
if top is don and top["raw"] - second["raw"] >= GAP:
    v3 = "맞음"
elif top["raw"] - don["raw"] < GAP:
    v3 = "반만"
else:
    v3 = "틀림"
if top is don:
    line3 = f"돈가스가 1등, 2등 {second['label']}보다 100명당 {top['raw'] - second['raw']:.1f}명 많다."
else:
    line3 = f"1등은 {top['label']}({top['value']:.1f}명), 돈가스는 {don_rank}등({don['value']:.1f}명) — 1등보다 {top['raw'] - don['raw']:.1f}명 적다."
title, sub = beliefs_text[3]
cards.append({"id": "b3", "kind": "믿음 3", "title": title, "sub": sub, "badge": v3, "groups": menu,
              "line": line3, "diff": round(don["raw"] - (second if top is don else top)["raw"], 1)})

t = base["최고기온"]
hot, warm = base[t >= 31], base[(t >= 25) & (t < 31)]
pair_card(4, grp("31도 이상", hot, True), grp("25도 이상 31도 미만", warm, False), "lower",
          f" 31도 이상인 날은 {len(hot)}일.")

pair_card(5, grp("월요일", base[base["요일"] == "월"], True),
          grp("화–목", base[base["요일"].isin(list("화수목"))], False), "lower")

# 메모에 없던 규칙: 월급날(월급날인 날 모두) vs 보통 날(행사 없고 월급날 아닌 날)
pay, normal = grp("월급날", df[df["월급날"] == 1], True), grp("보통 날", base, False)
diff = pay["raw"] - normal["raw"]
cards.append({"id": "pay", "kind": "메모에 없던 규칙", "title": "월급날에는 몇 분이 오실까?",
              "sub": "메모에는 없지만 기록에서 보인 차이입니다. 월급날은 행사가 있는 날도 모두 넣었습니다.",
              "badge": "차이 있음" if abs(diff) >= GAP else "차이 작음",
              "groups": [pay, normal], "line": sentence(pay, normal, diff), "diff": round(diff, 1)})

period = f"{df['날짜'].min()} ~ {df['날짜'].max()}"


# ---- 페이지 조각
def esc(s):
    return html.escape(str(s))


def section_head():
    return f"""<header class="head">
  <h1>한빛식당 밥 예보</h1>
  <p>(가상) 한빛정밀(주) 본사 구내식당 · 기록 {esc(period)} · 만든 사람 총무팀 최 대리(가상)</p>
</header>"""


BADGE_CLASS = {"맞음": "ok", "반만": "half", "틀림": "bad", "차이 있음": "half", "차이 작음": "half"}


def section_beliefs():
    items = []
    for c in cards:
        nums = " · ".join(f"<b>{esc(g['label'])}</b> {g['value']:.1f}명<span class='n'>({g['n']}일)</span>"
                          for g in (c["groups"] if c["id"] != "b3" else c["groups"][:3]))
        if c["id"] == "b3":
            nums += f" · <b>돈가스</b> {don['value']:.1f}명<span class='n'>({don['n']}일, {don_rank}등)</span>" if don_rank > 3 else ""
        items.append(f"""<article class="card{' extra' if c['id'] == 'pay' else ''}">
  <div class="card-top"><span class="kind">{esc(c['kind'])}</span><span class="badge {BADGE_CLASS[c['badge']]}">{esc(c['badge'])}</span></div>
  <h3>“{esc(c['title'])}”</h3>
  <p class="sub">{esc(c['sub'])}</p>
  <p class="nums">{nums}</p>
  <div class="chart" style="height:{36 * len(c['groups']) + 40}px"><canvas id="cv-{c['id']}" role="img" aria-label="{esc(c['kind'])} 막대 그래프"></canvas></div>
  <p class="line">{esc(c['line'])}</p>
</article>""")
    return f"""<section id="beliefs">
  <h2>영양사님 감 검증</h2>
  <p class="lead">행사가 없고 월급날이 아닌 날 {len(base)}일을 '출근 100명당 식수'(식수 ÷ 출근예정 × 100, 날마다 구해 평균)로 견주었습니다.
  100명당 {GAP:.0f}명 이상 차이 나면 '차이 있음'으로 봅니다({GAP:.0f}명은 사람이 정한 선). 믿음대로 차이가 있으면 맞음, 차이가 {GAP:.0f}명보다 작으면 반만, 믿음과 반대면 틀림입니다.</p>
  <div class="cards">
{chr(10).join(items)}
  </div>
</section>"""


SECTIONS = [section_beliefs]  # 머리 아래 구역 순서 — 다음 단계에서 앞쪽에 더한다

def axis_label(s):
    """막대 옆 이름이 길면 가운데 띄어쓰기에서 두 줄로 나눈다(좁은 화면에서 잘리지 않게)."""
    if len(s) <= 8 or " " not in s:
        return s
    sp = [i for i, ch in enumerate(s) if ch == " "]
    cut = min(sp, key=lambda i: abs(i - len(s) / 2))
    return [s[:cut], s[cut + 1:]]


DATA = {"cards": [{"id": c["id"], "groups": [{**{k: g[k] for k in ("label", "value", "n", "hl")}, "axis": axis_label(g["label"])}
                                             for g in c["groups"]]}
                  for c in cards],
        "colors": {"accent": ACCENT, "other": GRAY_BAR}}

CSS = f"""
:root {{ --bg:#ffffff; --panel:#f5f6f7; --ink:#1f2328; --muted:#5b636e; --line:#e3e6ea; --accent:{ACCENT}; --warn:{WARN}; }}
* {{ box-sizing:border-box; }}
html {{ -webkit-text-size-adjust:100%; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:'Noto Sans KR',sans-serif; font-size:16px; line-height:1.6; word-break:keep-all; overflow-wrap:break-word; }}
main {{ max-width:1040px; margin:0 auto; padding:24px 16px 48px; }}
.head h1 {{ margin:0 0 4px; font-size:28px; }}
.head p {{ margin:0; color:var(--muted); font-size:15px; }}
section {{ margin-top:32px; }}
h2 {{ font-size:22px; margin:0 0 8px; padding-bottom:6px; border-bottom:2px solid var(--ink); }}
.lead {{ color:var(--muted); font-size:15px; margin:0 0 16px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); gap:16px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; min-width:0; }}
.card.extra {{ background:var(--bg); border-style:dashed; }}
.card-top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
.kind {{ font-size:14px; color:var(--muted); font-weight:700; }}
.badge {{ font-size:14px; font-weight:700; padding:2px 10px; border-radius:999px; white-space:nowrap; }}
.badge.ok {{ background:var(--accent); color:#fff; }}
.badge.half {{ background:#e3e6ea; color:var(--ink); }}
.badge.bad {{ background:var(--warn); color:#fff; }}
.card h3 {{ font-size:18px; margin:8px 0 2px; }}
.sub {{ font-size:14px; color:var(--muted); margin:0 0 8px; }}
.nums {{ font-size:15px; margin:0 0 8px; }}
.n {{ color:var(--muted); font-size:14px; margin-left:2px; }}
.chart {{ position:relative; width:100%; }}
.line {{ font-size:15px; margin:8px 0 0; font-weight:500; }}
"""

JS = """
const D = JSON.parse(document.getElementById('page-data').textContent);
Chart.defaults.font.family = "'Noto Sans KR', sans-serif";
Chart.defaults.font.size = 14;
Chart.defaults.color = '#5b636e';
const endLabel = {  // 막대 끝에 값 표시
  id: 'endLabel',
  afterDatasetsDraw(chart) {
    const {ctx} = chart;
    const meta = chart.getDatasetMeta(0);
    ctx.save();
    ctx.fillStyle = '#1f2328';
    ctx.font = "500 14px 'Noto Sans KR', sans-serif";
    ctx.textBaseline = 'middle';
    meta.data.forEach((bar, i) => {
      ctx.fillText(chart.data.datasets[0].data[i].toFixed(1), bar.x + 6, bar.y);
    });
    ctx.restore();
  }
};
for (const c of D.cards) {
  const g = c.groups;
  new Chart(document.getElementById('cv-' + c.id), {
    type: 'bar',
    data: {
      labels: g.map(x => x.axis),
      datasets: [{
        data: g.map(x => x.value),
        backgroundColor: g.map(x => x.hl ? D.colors.accent : D.colors.other),
        borderRadius: 4, borderSkipped: 'start', barThickness: 18,
      }]
    },
    options: {
      indexAxis: 'y', maintainAspectRatio: false, animation: false,
      layout: {padding: {right: 44}},
      plugins: {
        legend: {display: false},
        tooltip: {callbacks: {label: (t) => `출근 100명당 ${g[t.dataIndex].value.toFixed(1)}명 · ${g[t.dataIndex].n}일`}}
      },
      scales: {
        x: {beginAtZero: true, max: 100, grid: {color: '#eceef1'}, border: {display: false}, ticks: {stepSize: 25}},
        y: {grid: {display: false}, border: {display: false}, ticks: {color: '#1f2328', autoSkip: false}}
      }
    },
    plugins: [endLabel]
  });
}
"""

data_json = json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/")
page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>한빛식당 밥 예보</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<main>
{section_head()}
{chr(10).join(s() for s in SECTIONS)}
</main>
<script id="page-data" type="application/json">{data_json}</script>
<script src="{CHART_JS}"></script>
<script>{JS}</script>
</body>
</html>
"""
OUT.write_text(page, encoding="utf-8", newline="\n")

# ---- 화면 요약
print(f"깨끗한 표 {len(df)}줄 · 기록 {period} · 비교에 쓴 날(행사 없음 · 월급날 아님) {len(base)}일")
for c in cards:
    print(f"[{c['kind']}] {c['badge']} | " + " · ".join(f"{g['label']} {g['value']:.1f}({g['n']}일)" for g in c["groups"])
          + f" | {c['line']}")
print("저장:", OUT)
