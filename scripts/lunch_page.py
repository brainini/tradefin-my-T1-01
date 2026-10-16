"""3일차 실습 C: 한빛식당 밥 예보 페이지 — workbench/day3/outputs/hanbit_lunch.html을 계산해서 쓴다

실행: uv run python scripts/lunch_page.py
입력: workbench/day3/outputs/lunch_clean.csv (정제된 표) · labs/day3/lab-c/nutritionist_memo.md (믿음 글)
출력: workbench/day3/outputs/hanbit_lunch.html — 손으로 고치지 않는다. 같은 입력이면 같은 페이지.
      labs/day3/lab-c/next_week_plan.csv (다음 주 계획, 읽기만)
구역: 머리 → 다음 주 예보 → 예보 성적표 → 영양사님 감 검증
페이지 규칙: 파일 하나 · 데이터는 페이지 안 JSON · fetch 없음 · 외부 스크립트는 Chart.js 4.4.1 하나 · 글꼴 Noto Sans KR
"""

import html
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression

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

# ---- 예보관 시험
SPLIT = "2026-09-14"  # 이 날 전 = 배우는 기간, 이 날부터 = 시험 기간
COST = 4500  # 1인분 원가(가정)
SPARE = 10  # AI 준비 = 예보 + 10
TEXT_COLS = ["요일", "날씨", "메인메뉴", "행사"]
NUM_COLS = ["최고기온", "월급날", "출근예정"]
MULT = {"돈가스": 1.1, "카레": 1.1, "샐러드": 0.9}  # 영양사님 공식의 메뉴 배수(나머지 1.0)


def half_up(x):
    return int(math.floor(x + 0.5))


train = df[df["날짜"] < SPLIT]
test = df[df["날짜"] >= SPLIT].reset_index(drop=True)
assert len(test) == 20, f"시험 기간이 20일이 아님: {len(test)}"
temp_fill = float(train["최고기온"].median())  # 최고기온 빈칸 = 배우는 기간의 가운데 값


def features(rows, columns=None):
    """재료 열 → 글자 열은 값마다 0/1(drop_first 없이). columns를 주면 배울 때와 같은 열로 맞추고 없는 열은 0."""
    x = rows[TEXT_COLS + NUM_COLS].copy()
    x["행사"] = x["행사"].replace("", "없음")
    x["최고기온"] = x["최고기온"].fillna(temp_fill)
    x = pd.get_dummies(x, columns=TEXT_COLS, dtype=float)
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0.0)
    return x.astype(float)


X_train = features(train)
FEATURE_COLS = list(X_train.columns)
X_test = features(test, FEATURE_COLS)
y_train, actual = train["식수"].to_numpy(float), test["식수"].to_numpy(float)

forecasters = {
    "선형 회귀": LinearRegression(),
    "LightGBM": LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15,
                              min_child_samples=5, random_state=42, verbose=-1),
}
preds, mae = {}, {}
for name, model in forecasters.items():
    model.fit(X_train.to_numpy(), y_train)
    preds[name] = model.predict(X_test.to_numpy())
    mae[name] = float(abs(preds[name] - actual).mean())  # 하루 평균 몇 인분 차이
chosen = min(mae, key=lambda k: (mae[k], k))  # 더 작은 쪽 = 우리 예보관
ai_pred = preds[chosen]


def nutritionist(day, weekday, menu):
    """그날 전 같은 요일의 실제 식수 4개(깨끗한 표에서 가장 가까운 날부터)의 평균 × 메뉴 배수."""
    prev = df[(df["요일"] == weekday) & (df["날짜"] < day)].sort_values("날짜").tail(4)
    return float(prev["식수"].mean()) * MULT.get(menu, 1.0)


formula = [nutritionist(r.날짜, r.요일, r.메인메뉴) for r in test.itertuples()]
mae_formula = float(sum(abs(f - a) for f, a in zip(formula, actual)) / len(test))


def outcome(prep):
    """준비 인분(정수) → 남은 밥 · 모자란 밥."""
    left = [max(p - a, 0) for p, a in zip(prep, actual)]
    short = [max(a - p, 0) for p, a in zip(prep, actual)]
    return {"left": int(sum(left)), "left_won": int(sum(left)) * COST,
            "short": int(sum(short)), "short_days": int(sum(s > 0 for s in short))}


prep_ai = [half_up(p) + SPARE for p in ai_pred]  # 예보는 인분이라 반올림한 뒤 + 10
prep_formula = [half_up(f) for f in formula]
res_ai = {"mae": mae[chosen], **outcome(prep_ai)}
res_formula = {"mae": mae_formula, **outcome(prep_formula)}

EVENTS = {"2026-09-23": "추석 연휴 전날 · 돈가스", "2026-09-30": "비 오는 수요일 · 카레"}
test_rows = [{"date": r.날짜, "label": f"{int(r.날짜[5:7])}/{int(r.날짜[8:])}({r.요일})", "actual": int(r.식수),
              "ai": half_up(p), "ai_prep": pa, "formula": half_up(f), "formula_prep": pf}
             for r, p, pa, f, pf in zip(test.itertuples(), ai_pred, prep_ai, formula, prep_formula)]
marks = [{"i": i, "date": t["date"], "short": t["label"].split("(")[0], "note": EVENTS[t["date"]], **t}
         for i, t in enumerate(test_rows) if t["date"] in EVENTS]

# ---- 다음 주 예보
PLAN = "labs/day3/lab-c/next_week_plan.csv"
plan = pd.read_csv(PLAN, encoding="utf-8-sig", dtype=str, keep_default_na=False)
for r in plan.itertuples():
    assert "월화수목금토일"[pd.Timestamp(r.날짜).weekday()] == r.요일, f"계획의 요일이 날짜와 다름: {r.날짜} {r.요일}"
nw = pd.DataFrame({  # 계획 → 배울 때와 같은 이름 · 같은 처리
    "날짜": plan["날짜"], "요일": plan["요일"], "날씨": plan["날씨예보"],
    "최고기온": pd.to_numeric(plan["최고기온예보"], errors="coerce"),
    "메인메뉴": plan["메인메뉴"], "행사": plan["행사"],
    "월급날": (plan["월급날"] == "Y").astype(int), "출근예정": pd.to_numeric(plan["출근예정"]),
})
X_next = features(nw, FEATURE_COLS)
unseen = sorted({f"{c}={v or '없음'}" for c in TEXT_COLS for v in nw[c]
                 if f"{c}_{v or '없음'}" not in FEATURE_COLS})  # 배울 때 없던 값(있으면 그 열은 0)
next_pred = forecasters[chosen].predict(X_next.to_numpy())

card_by_id = {c["id"]: c for c in cards}
att_median = half_up(float(df["출근예정"].median()))
WEEKDAY = {"월": "월요일", "화": "화요일", "수": "수요일", "목": "목요일", "금": "금요일"}


def more_less(x):
    return "더" if x > 0 else "덜"


def josa(word, with_final, without_final):
    """받침이 있으면 with_final(은 · 이), 없으면 without_final(는 · 가)."""
    ch = word[-1]
    has_final = "가" <= ch <= "힣" and (ord(ch) - ord("가")) % 28 != 0
    return word + (with_final if has_final else without_final)


def comment(r, fc, fo):
    """영양사님께 드리는 한 줄 — 그날 조건과 공식과의 차이. 숫자는 위에서 계산한 값만."""
    h = []
    if r.월급날:
        d = card_by_id["pay"]["diff"]
        h.append(f"월급날은 보통 날보다 100명당 {abs(d):.1f}명 {more_less(d)} 오셨어요")
    if r.날씨 == "비":
        d = card_by_id["b1"]["diff"]
        h.append(f"비 오는 날은 맑은 날보다 100명당 {abs(d):.1f}명 {more_less(d)} 오셨어요")
    if r.행사 == "전사 교육":
        h.append(f"전사 교육으로 출근예정이 {r.출근예정}명(기록의 가운데 값 {att_median}명)이에요")
    elif r.행사:
        h.append(f"{josa(r.행사, '이', '가')} 있는 날이에요")
    if r.요일 == "금":
        d = card_by_id["b2"]["diff"]
        h.append(f"금요일은 월–목보다 100명당 {abs(d):.1f}명 {more_less(d)} 오셨어요")
    rank = [g["label"] for g in menu]
    if r.메인메뉴 in rank and rank.index(r.메인메뉴) in (0, len(rank) - 1):
        g = menu[rank.index(r.메인메뉴)]
        h.append(f"{josa(r.메인메뉴, '은', '는')} 메뉴 중 100명당 {g['value']:.1f}명으로 {'가장 많았' if rank.index(r.메인메뉴) == 0 else '가장 적었'}어요")
    lead = (". ".join(h[:2]) + ". ") if h else f"{WEEKDAY[r.요일]} · {r.날씨} · {r.메인메뉴}, 특별한 일이 없는 날이에요. "
    diff = fc - fo
    tail = (f"예보는 영양사님 공식({fo}인분)과 같아요." if diff == 0 else
            f"예보는 영양사님 공식({fo}인분)보다 {abs(diff)}명 {'많아요' if diff > 0 else '적어요'}.")
    return lead + tail


next_rows = []
for r, p in zip(nw.itertuples(), next_pred):
    fc = half_up(p)
    fo = half_up(nutritionist(r.날짜, r.요일, r.메인메뉴))
    next_rows.append({"date": r.날짜, "day": r.요일, "label": f"{int(r.날짜[5:7])}/{int(r.날짜[8:])}",
                      "forecast": fc, "prep": fc + SPARE, "formula": fo,
                      "badges": [r.날씨, r.메인메뉴] + ([r.행사] if r.행사 else []) + (["월급날"] if r.월급날 else []),
                      "comment": comment(r, fc, fo)})
top_i = max(range(len(next_rows)), key=lambda i: (next_rows[i]["forecast"], -i))
low_i = min(range(len(next_rows)), key=lambda i: (next_rows[i]["forecast"], i))


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


def section_forecast():
    boxes = []
    for name in forecasters:
        pick = name == chosen
        boxes.append(f"""<div class="fc{' pick' if pick else ''}">
      <div class="fc-name">{esc(name)}{'<span class="badge ok">우리 예보관</span>' if pick else ''}</div>
      <div class="fc-num">{mae[name]:.1f}<small>인분</small></div>
      <div class="fc-cap">시험 20일 하루 평균 차이</div>
    </div>""")
    notes = "".join(
        f"<li><b>{esc(m['short'])}({esc(m['note'])})</b> 실제 {m['actual']}명 · 우리 예보관 {m['ai']}명(준비 {m['ai_prep']}인분)"
        f" · 영양사님 공식 {m['formula_prep']}인분</li>" for m in marks)

    def duo(title, ai_html, f_html, cap=""):
        return f"""<article class="card duo">
      <h3>{esc(title)}</h3>
      <div class="duo-row"><div><span class="who">AI</span><span class="big">{ai_html}</span></div>
      <div><span class="who">영양사님 공식</span><span class="big">{f_html}</span></div></div>
      {f'<p class="sub">{esc(cap)}</p>' if cap else ''}
    </article>"""

    cards3 = "\n".join([
        duo("하루 평균 몇 인분 차이", f"{res_ai['mae']:.1f}<small>인분</small>", f"{res_formula['mae']:.1f}<small>인분</small>",
            "날마다 예보와 실제의 차이를 크기만 재어 평균"),
        duo("남은 밥", f"{res_ai['left']:,}<small>인분</small><em>{res_ai['left_won']:,}원</em>",
            f"{res_formula['left']:,}<small>인분</small><em>{res_formula['left_won']:,}원</em>", f"1인분 원가 {COST:,}원(가정)"),
        duo("모자란 밥(컵라면을 드신 분)", f"{res_ai['short']:,}<small>인분</small><em>모자란 날 {res_ai['short_days']}일</em>",
            f"{res_formula['short']:,}<small>인분</small><em>모자란 날 {res_formula['short_days']}일</em>"),
    ])
    return f"""<section id="scorecard">
  <h2>예보 성적표</h2>
  <p class="lead">{esc(SPLIT)} 전 {len(train)}일로 배우고, {esc(SPLIT)}부터 {len(test)}일(배울 때 쓰지 않은 날)로 시험했습니다.</p>
  <div class="fcs">
    {''.join(boxes)}
  </div>
  <p class="line">복잡한 쪽이 늘 이기지는 않는다 — 시험으로 고른다.</p>
  <p class="sub">두 예보관의 설정은 모두 같은 결과를 보려고 고정했습니다.</p>
  <article class="card wide">
    <h3>시험 20일 — 실제와 예보</h3>
    <div class="chart" style="height:320px"><canvas id="cv-test" role="img" aria-label="시험 20일 실제 · 우리 예보관 · 영양사님 공식 선 그래프"></canvas></div>
    <ul class="notes">{notes}</ul>
  </article>
  <div class="cards three">
{cards3}
  </div>
  <p class="sub">AI 준비 = 우리 예보관({esc(chosen)})의 예보(반올림) + {SPARE}인분 · 영양사님 준비 = 공식(최근 같은 요일 4번 평균 × 메뉴 배수, 반올림).</p>
</section>"""


def section_next_week():
    items = []
    for i, d in enumerate(next_rows):
        flag = "이번 주 가장 많은 날" if i == top_i else "이번 주 가장 적은 날" if i == low_i else ""
        badges = "".join(f"<span class='tag'>{esc(b)}</span>" for b in d["badges"])
        items.append(f"""<article class="day{' top' if i == top_i else ' low' if i == low_i else ''}">
      <div class="day-flag">{esc(flag) if flag else '&nbsp;'}</div>
      <div class="day-date">{esc(d['label'])} <span>{esc(WEEKDAY[d['day']])}</span></div>
      <div class="day-num">{d['forecast']}<small>명</small></div>
      <div class="day-prep">준비 {d['prep']}인분</div>
      <div class="day-formula">영양사님 공식이면 {d['formula']}인분</div>
      <div class="tags">{badges}</div>
      <p class="day-note">{esc(d['comment'])}</p>
    </article>""")
    return f"""<section id="next-week">
  <h2>다음 주 예보</h2>
  <p class="lead">우리 예보관({esc(chosen)})에게 다음 주({esc(next_rows[0]['label'])}–{esc(next_rows[-1]['label'])}) 계획을 물었습니다. 준비 = 예보 + {SPARE}인분입니다. 준비량은 영양사님이 정해 주세요.</p>
  <div class="days">
{chr(10).join(items)}
  </div>
</section>"""


SECTIONS = [section_next_week, section_forecast, section_beliefs]  # 머리 아래 구역 순서

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
        "test": {"labels": [t["label"] for t in test_rows], "actual": [t["actual"] for t in test_rows],
                 "ai": [t["ai"] for t in test_rows], "formula": [t["formula_prep"] for t in test_rows],
                 "chosen": chosen, "marks": [{"i": m["i"], "text": m["short"]} for m in marks]},
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
.fcs {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; }}
.fc {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.fc.pick {{ border:2px solid var(--accent); background:var(--bg); }}
.fc-name {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; font-weight:700; }}
.fc-num {{ font-size:32px; font-weight:700; line-height:1.2; margin-top:4px; }}
.fc-num small, .big small {{ font-size:15px; font-weight:500; margin-left:2px; }}
.fc-cap {{ font-size:14px; color:var(--muted); }}
.card.wide {{ margin-top:16px; }}
.notes {{ margin:8px 0 0; padding-left:18px; font-size:15px; }}
.notes li {{ margin:2px 0; }}
.cards.three {{ margin-top:16px; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); }}
.duo-row {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }}
.who {{ display:block; font-size:14px; color:var(--muted); font-weight:700; }}
.big {{ display:block; font-size:24px; font-weight:700; line-height:1.3; }}
.big em {{ display:block; font-style:normal; font-size:14px; font-weight:500; color:var(--muted); }}
.days {{ display:grid; grid-template-columns:1fr; gap:12px; }}
@media (min-width:640px) {{ .days {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }} }}
@media (min-width:960px) {{ .days {{ grid-template-columns:repeat(5, minmax(0, 1fr)); }} }}
.day {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:14px; min-width:0; display:flex; flex-direction:column; }}
.day.top, .day.low {{ background:var(--bg); border:2px solid var(--accent); }}
.day-flag {{ font-size:14px; font-weight:700; color:var(--accent); min-height:22px; }}
.day-date {{ font-size:18px; font-weight:700; }}
.day-date span {{ font-size:15px; font-weight:500; color:var(--muted); margin-left:4px; }}
.day-num {{ font-size:44px; font-weight:700; line-height:1.1; margin-top:6px; }}
.day-num small {{ font-size:18px; font-weight:500; margin-left:2px; }}
.day-prep {{ font-size:17px; font-weight:700; margin-top:4px; }}
.day-formula {{ font-size:14px; color:var(--muted); }}
.tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }}
.tag {{ font-size:14px; padding:1px 8px; border-radius:6px; background:#e3e6ea; color:var(--ink); }}
.day-note {{ font-size:15px; margin:10px 0 0; }}
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
const T = D.test;
const markLines = {  // 9/23 · 9/30 세로 점선과 날짜 표시
  id: 'markLines',
  afterDatasetsDraw(chart) {
    const {ctx, chartArea: a, scales: {x}} = chart;
    ctx.save();
    for (const m of T.marks) {
      const px = x.getPixelForValue(m.i);
      ctx.strokeStyle = '#5b636e'; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = '#1f2328';
      ctx.font = "700 14px 'Noto Sans KR', sans-serif"; ctx.textAlign = 'center';
      ctx.fillText(m.text, px, a.top - 6);
    }
    ctx.restore();
  }
};
new Chart(document.getElementById('cv-test'), {
  type: 'line',
  data: {
    labels: T.labels,
    datasets: [
      {label: '실제', data: T.actual, borderColor: '#1f2328', backgroundColor: '#1f2328', borderWidth: 2, pointRadius: 3},
      {label: '우리 예보관(' + T.chosen + ')', data: T.ai, borderColor: D.colors.accent, backgroundColor: D.colors.accent, borderWidth: 2, pointRadius: 3},
      {label: '영양사님 공식', data: T.formula, borderColor: '#8a929c', backgroundColor: '#8a929c', borderWidth: 2, borderDash: [6, 4], pointRadius: 3},
    ]
  },
  options: {
    maintainAspectRatio: false, animation: false,
    layout: {padding: {top: 22}},
    interaction: {mode: 'index', intersect: false},
    plugins: {
      legend: {position: 'bottom', labels: {boxWidth: 14, boxHeight: 2}},
      tooltip: {callbacks: {label: (t) => `${t.dataset.label} ${t.parsed.y}명`}}
    },
    scales: {
      x: {grid: {display: false}, ticks: {maxRotation: 0, autoSkip: true, autoSkipPadding: 8}},
      y: {grid: {color: '#eceef1'}, border: {display: false}, title: {display: true, text: '명(인분)'}}
    }
  },
  plugins: [markLines]
});
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
print(f"[예보 성적표] 배우는 기간 {len(train)}일 · 시험 기간 {len(test)}일 · 재료 열 {len(FEATURE_COLS)}개 · 최고기온 빈칸 채움 {temp_fill}")
print("  시험 성적(하루 평균 차이):", {k: round(v, 2) for k, v in mae.items()}, "→ 우리 예보관:", chosen)
for m in marks:
    print(f"  {m['date']} 실제 {m['actual']} · AI 예보 {m['ai']}(준비 {m['ai_prep']}) · 공식 {m['formula_prep']}")
print("  AI   :", res_ai)
print("  공식 :", res_formula)
print(f"[다음 주 예보] 우리 예보관 {chosen} · 배울 때 없던 값: {unseen or '없음'}")
for i, d in enumerate(next_rows):
    flag = " ← 가장 많음" if i == top_i else " ← 가장 적음" if i == low_i else ""
    print(f"  {d['date']}({d['day']}) 예보 {d['forecast']} · 준비 {d['prep']} · 공식 {d['formula']}{flag} | {d['comment']}")
print("  구역 순서: 머리 → " + " → ".join({"section_next_week": "다음 주 예보", "section_forecast": "예보 성적표",
                                          "section_beliefs": "영양사님 감 검증"}[s.__name__] for s in SECTIONS))
print("저장:", OUT)
