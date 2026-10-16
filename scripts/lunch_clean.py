"""3일차 실습 C: hanbit_lunch_log.csv 정제 — workbench/day3/outputs/lunch_rules.md의 표 그대로

실행: uv run python scripts/lunch_clean.py
입력: labs/day3/lab-c/hanbit_lunch_log.csv (UTF-8 BOM, 읽기만)
출력: workbench/day3/outputs/lunch_clean.csv (UTF-8 BOM, 원본과 같은 10개 열, 날짜순)
      workbench/day3/outputs/lunch_clean_log.md (규칙별 고친(뺀) 줄 수 — 그 규칙을 적용할 때 남아 있는 줄에서 셈)
적용 순서: R1 → R2 → R3 → R4 → R5 → R10 → R6 → R7 → R8 → R9
R6의 '수기 집계' 줄: 수강생 결정 = 뺀다
"""

import math
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SRC = "labs/day3/lab-c/hanbit_lunch_log.csv"
OUT_CSV = Path("workbench/day3/outputs/lunch_clean.csv")
OUT_LOG = Path("workbench/day3/outputs/lunch_clean_log.md")
HANDWRITTEN = "뺀다"  # R6 '수기 집계' 줄 — 수강생 결정("'수기 집계' 줄은 뺀다")

DAYS = "월화수목금토일"
EN_DAYS = {"Mon": "월", "Tue": "화", "Wed": "수", "Thu": "목", "Fri": "금", "Sat": "토", "Sun": "일"}
WEATHER = {"맑": "맑음", "sunny": "맑음", "구름많음": "흐림", "cloudy": "흐림",
           "rain": "비", "우천": "비", "소나기": "비", "흐리고 비": "비", "snow": "눈", "": "모름"}
MENU = {"돈까스": "돈가스", "카레라이스": "카레", "제육": "제육볶음", "치킨마요덮밥": "치킨마요", "김치 찌개": "김치찌개"}
EVENT = {"외부손님": "외부 손님 방문", "전사교육": "전사 교육"}

df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)
COLS = list(df.columns)
df.index = df.index + 2  # CSV 줄 번호(머리글 = 1행) — 기록용
n_start = len(df)
log = []  # (순서, 규칙, 할 일, 고친/뺀 줄 수, 남은 줄 수)
detail = {}


def record(rule, what, n):
    log.append((len(log) + 1, rule, what, n, len(df)))


def half_up(x):
    return int(math.floor(x + 0.5))


# R1 날짜를 YYYY-MM-DD로
def to_iso(v):
    if re.fullmatch(r"\d{1,2}월 \d{1,2}일", v):
        m, d = map(int, re.findall(r"\d+", v))
        y = 2025 if m >= 10 else 2026
    elif re.fullmatch(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", v):
        y, m, d = map(int, re.findall(r"\d+", v))
    else:
        raise ValueError(f"읽을 수 없는 날짜: {v!r}")
    return f"{y:04d}-{m:02d}-{d:02d}"


iso = df["날짜"].map(to_iso)
record("R1", "날짜를 YYYY-MM-DD로", int((iso != df["날짜"]).sum()))
df["날짜"] = iso
df = df.sort_values("날짜", kind="stable")  # 같은 날짜는 파일 순서 유지 → R4의 '나중 줄'

# R2 요일을 날짜에서 다시 계산(적힌 요일이 실제와 달랐던 줄만 셈)
true_day = pd.to_datetime(df["날짜"]).dt.weekday.map(lambda i: DAYS[i])
written = df["요일"].map(lambda v: v[0] if v and v[0] in DAYS else EN_DAYS.get(v, ""))
detail["R2"] = df.loc[written != true_day, ["날짜", "요일"]].assign(실제=true_day)
record("R2", "요일을 날짜에서 다시 계산(적힌 요일이 실제와 달랐던 줄)", int((written != true_day).sum()))
df["요일"] = true_day

# R3 휴무 줄 빼기
m = df["비고"] == "휴무"
df = df[~m]
record("R3", "비고가 `휴무`인 줄 빼기", int(m.sum()))

# R4 같은 날짜 두 줄 → 재집계 줄, 없으면 나중 줄
df = df.assign(_re=df["비고"].str.contains("재집계").astype(int), _ord=range(len(df)))
keep = df.sort_values(["날짜", "_re", "_ord"], kind="stable").groupby("날짜").tail(1).index
dropped = df.index.difference(keep)
detail["R4"] = df.loc[dropped, ["날짜", "식수", "비고"]]
df = df.loc[df.index.isin(keep)].drop(columns=["_re", "_ord"])
record("R4", "같은 날짜 두 줄 → 재집계 줄(없으면 나중 줄)만 남기기", len(dropped))

# R5 식수 빈칸 빼기
m = df["식수"] == ""
df = df[~m]
record("R5", "식수 빈칸 줄 빼기", int(m.sum()))

# R10 출근예정 빈칸 → 같은 요일 바로 앞 기록 4개(출근예정 있는 줄)의 가운데 값, 반올림(.5는 올림)
filled = []
has_att = df["출근예정"] != ""
for i in df.index[~has_att]:
    prev = df[has_att & (df["요일"] == df.at[i, "요일"]) & (df["날짜"] < df.at[i, "날짜"])].tail(4)
    med = pd.to_numeric(prev["출근예정"]).median()
    val = half_up(med)
    filled.append((df.at[i, "날짜"], df.at[i, "요일"], ", ".join(f"{d} {a}" for d, a in zip(prev["날짜"], prev["출근예정"])), med, val))
    df.at[i, "출근예정"] = str(val)
detail["R10"] = filled
record("R10", "출근예정 빈칸 채우기(같은 요일 바로 앞 4개의 가운데 값)", len(filled))

# R6 불가능한 식수 빼기 · '수기 집계' 줄은 수강생 결정대로
att = pd.to_numeric(df["출근예정"])
meal = pd.to_numeric(df["식수"])
hand = df["비고"] == "수기 집계"
if HANDWRITTEN == "×10 보정":
    df.loc[hand, "식수"] = (meal[hand] * 10).astype(int).astype(str)
    meal = pd.to_numeric(df["식수"])
    m = ~hand & ((meal > att) | (meal < att * 0.2))
else:  # 뺀다
    m = hand | (meal > att) | (meal < att * 0.2)
detail["R6"] = df.loc[m, ["날짜", "출근예정", "식수", "비고"]]
df = df[~m]
record("R6", f"불가능한 식수 줄 빼기(`수기 집계` 줄: {HANDWRITTEN})", int(m.sum()))

# R7 날씨 넷으로(빈칸 → 모름)
new = df["날씨"].map(lambda v: WEATHER.get(v, v))
bad = ~new.isin(["맑음", "흐림", "비", "눈", "모름"])
if bad.any():
    raise ValueError(f"R7 표에 없는 날씨: {sorted(set(new[bad]))}")
record("R7", "날씨를 맑음 · 흐림 · 비 · 눈(빈칸 → 모름)으로", int((new != df["날씨"]).sum()))
df["날씨"] = new

# R8 최고기온 단위 · 공백 떼기
new = df["최고기온"].str.replace("℃", "", regex=False).str.replace("°C", "", regex=False).str.replace(" ", "", regex=False)
bad = (new != "") & pd.to_numeric(new, errors="coerce").isna()
if bad.any():
    raise ValueError(f"R8 뒤에도 숫자가 아닌 최고기온: {sorted(set(new[bad]))}")
record("R8", "최고기온에서 `℃` · `°C` · 공백 떼기", int((new != df["최고기온"]).sum()))
df["최고기온"] = new

# R9 메뉴 · 행사 이름 통일(따로 세어 더함)
n_menu = int(df["메인메뉴"].isin(list(MENU)).sum())
n_event = int(df["행사"].isin(list(EVENT)).sum())
df["메인메뉴"] = df["메인메뉴"].map(lambda v: MENU.get(v, v))
df["행사"] = df["행사"].map(lambda v: EVENT.get(v, v))
record("R9", f"메뉴 · 행사 이름 통일(메뉴 {n_menu} + 행사 {n_event})", n_menu + n_event)

# 마무리: 월급날 Y→1 · 빈칸→0, 출근예정 · 식수 정수, 날짜순, 원본과 같은 10개 열
bad = ~df["월급날"].isin(["Y", ""])
if bad.any():
    raise ValueError(f"월급날에 Y · 빈칸 말고 다른 값: {sorted(set(df.loc[bad, '월급날']))}")
df["월급날"] = (df["월급날"] == "Y").astype(int)
df["출근예정"] = df["출근예정"].astype(int)
df["식수"] = df["식수"].astype(int)
df = df.sort_values("날짜", kind="stable")[COLS]
assert df["날짜"].is_unique
df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", lineterminator="\n")

# ---- 기록
L = ["# 한빛식당 점심 기록 정제 기록", "",
     "- 규칙: `workbench/day3/outputs/lunch_rules.md` · 코드: `scripts/lunch_clean.py` — 숫자는 모두 이 코드가 센 값이다.",
     "- 세는 법: 그 규칙을 적용할 때 **남아 있는 줄에서** 센다. R2는 적힌 요일이 실제 요일과 달랐던 줄만, R9는 메뉴와 행사를 따로 세어 더했다.",
     f"- `수기 집계` 줄: 수강생 결정대로 **{HANDWRITTEN}**.", "",
     f"처음 줄 수 **{n_start}** → 남은 줄 수 **{len(df)}** (날짜 {df['날짜'].min()} ~ {df['날짜'].max()})", "",
     "| 순서 | 규칙 | 할 일 | 고친(뺀) 줄 수 | 적용 뒤 남은 줄 수 |", "|---|---|---|---|---|"]
L += [f"| {o} | {r} | {w} | {n} | {left} |" for o, r, w, n, left in log]
L += ["", "## 자세히", "", "### R2 — 적힌 요일이 실제와 달랐던 줄", "", "| 날짜 | 적힌 요일 | 실제 요일 |", "|---|---|---|"]
L += [f"| {r.날짜} | {r.요일} | {r.실제} |" for r in detail["R2"].itertuples()]
L += ["", "### R4 — 같은 날짜에서 뺀 줄", "", "| 날짜 | 식수 | 비고 |", "|---|---|---|"]
L += [f"| {r.날짜} | {r.식수} | {r.비고 or '(빈칸)'} |" for r in detail["R4"].itertuples()]
L += ["", "### R10 — 채운 출근예정", "", "| 날짜 | 요일 | 바로 앞 같은 요일 4개(날짜 출근예정) | 가운데 값 | 채운 값 |", "|---|---|---|---|---|"]
L += [f"| {d} | {w} | {p} | {med:g} | {v} |" for d, w, p, med, v in detail["R10"]]
L += ["", "### R6 — 뺀 줄", "", "| 날짜 | 출근예정 | 식수 | 비고 |", "|---|---|---|---|"]
L += [f"| {r.날짜} | {r.출근예정} | {r.식수} | {r.비고 or '(빈칸)'} |" for r in detail["R6"].itertuples()]
L.append("")
OUT_LOG.write_text("\n".join(L), encoding="utf-8", newline="\n")

print(f"처음 {n_start}줄 → 남은 {len(df)}줄")
for o, r, w, n, left in log:
    print(f"{o:>2}. {r:<3} {n:>3}줄  (남은 {left})  {w}")
print("R10 채움:", [(d, v) for d, _, _, _, v in detail["R10"]])
print("R6 뺀 줄:", detail["R6"].to_dict("records"))
print("저장:", OUT_CSV, "·", OUT_LOG)
