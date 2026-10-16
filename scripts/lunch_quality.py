"""3일차 실습 C: hanbit_lunch_log.csv 품질 진단 (읽기 전용 — 값을 고치지 않는다)

실행: uv run python scripts/lunch_quality.py
출력: workbench/day3/outputs/lunch_quality.md — 보고서의 숫자는 모두 이 코드가 센 값이다.
줄 번호는 CSV 파일의 줄 번호다(머리글 = 1행).
날짜는 진단용으로만 읽는다(원본은 그대로). 연도 없는 'M월 D일'은 안내서 R1대로 10–12월 → 2025년, 1–9월 → 2026년.
"""

import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SRC = "labs/day3/lab-c/hanbit_lunch_log.csv"
OUT = Path("workbench/day3/outputs/lunch_quality.md")

df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)
df.index = df.index + 2  # CSV 줄 번호

PATS = [
    (r"^\d{4}-\d{2}-\d{2}$", "YYYY-MM-DD"),
    (r"^\d{4}/\d{2}/\d{2}$", "YYYY/MM/DD"),
    (r"^\d{4}\.\d{1,2}\.\d{1,2}$", "YYYY.M.D"),
    (r"^\d{1,2}월 \d{1,2}일$", "M월 D일"),
]
DAYS = "월화수목금토일"
EN_DAYS = {"Mon": "월", "Tue": "화", "Wed": "수", "Thu": "목", "Fri": "금", "Sat": "토", "Sun": "일"}
STD_WEATHER = ["맑음", "흐림", "비", "눈"]
MENU_VAR = {"돈까스": "돈가스", "카레라이스": "카레", "제육": "제육볶음", "치킨마요덮밥": "치킨마요", "김치 찌개": "김치찌개"}
EVENT_VAR = {"외부손님": "외부 손님 방문", "전사교육": "전사 교육"}


def date_kind(v):
    for p, name in PATS:
        if re.match(p, v):
            return name
    return "기타"


def parse_date(v):
    kind = date_kind(v)
    if kind == "기타":
        return pd.NaT
    nums = [int(x) for x in re.findall(r"\d+", v)]
    if kind == "M월 D일":
        m, d = nums
        y = 2025 if m >= 10 else 2026
    else:
        y, m, d = nums
    return pd.Timestamp(y, m, d)


def day_kind(v):
    if v in list("월화수목금"):
        return "한 글자(월)"
    if re.fullmatch(r"[월화수목금토일]요일", v):
        return "○요일(월요일)"
    if v in EN_DAYS:
        return "영어 약자(Mon)"
    return "기타"


def day_char(v):
    if v and v[0] in DAYS:
        return v[0]
    return EN_DAYS.get(v, "")


def counts(s):
    """값별 줄 수 — 많은 순, 같으면 먼저 나온 순."""
    g = s.groupby(s, sort=False).size()
    return sorted(g.items(), key=lambda kv: -kv[1])


def q(v):
    return f"`{v}`" if v != "" else "(빈칸)"


def examples(mask, fmt, n=2):
    return " · ".join(fmt(i) for i in df.index[mask][:n])


def breakdown(pairs):
    return " · ".join(f"{k} {v}" for k, v in pairs)


def ex_date(i):
    return f"{i}행 {q(df.at[i, '날짜'])}"


# ---- 계산용 열(원본은 그대로)
dk = df["날짜"].map(date_kind)
parsed = df["날짜"].map(parse_date)
dyk = df["요일"].map(day_kind)
true_day = parsed.map(lambda t: DAYS[t.weekday()] if pd.notna(t) else "")
att = pd.to_numeric(df["출근예정"], errors="coerce")
meal = pd.to_numeric(df["식수"], errors="coerce")
hol = df["비고"] == "휴무"
work = ~hol

# ---- 종류별 표시(mask)
m_date = dk != "YYYY-MM-DD"
m_day = dyk != "한 글자(월)"
m_mis = parsed.notna() & (df["요일"].map(day_char) != true_day)
m_dup = parsed.notna() & parsed.duplicated(keep=False)
m_meal_blank = df["식수"] == ""
both = work & att.notna() & meal.notna()
m_imp = both & ((meal > att) | (meal < att * 0.2))
w = df["날씨"]
m_w = work & (w != "") & ~w.isin(STD_WEATHER)
m_wb = work & (w == "")
t = df["최고기온"]
m_c1 = work & t.str.contains("℃", regex=False)
m_c2 = work & t.str.contains("°C", regex=False)
m_tb = work & (t == "")
m_temp = m_c1 | m_c2 | m_tb
m_menu = df["메인메뉴"].isin(list(MENU_VAR))
m_event = df["행사"].isin(list(EVENT_VAR))
m_name = m_menu | m_event
m_att_blank = work & (df["출근예정"] == "")
bad_num = {c: int(((df[c] != "") & pd.to_numeric(df[c], errors="coerce").isna()).sum()) for c in ["출근예정", "식수"]}

# 같은 날짜 묶음
dup_groups = []
for d, g in df[m_dup].groupby(parsed[m_dup], sort=True):
    if g.duplicated(keep=False).all():
        kind = "모든 열이 같음"
    elif g["비고"].str.contains("재집계").any():
        kind = "비고에 재집계"
    else:
        kind = "기타(값이 다름)"
    dup_groups.append((d, g, kind))
dup_kind_counts = pd.Series([k for _, _, k in dup_groups]).value_counts()

# ---- 보고서
L = []
a = L.append
a("# 한빛식당 점심 기록 품질 진단")
a("")
a(f"- 원본: `{SRC}`(UTF-8 BOM) — 읽기만 했다. 고치거나 뺀 줄은 없다.")
a("- 코드: `scripts/lunch_quality.py` — 이 보고서의 숫자는 모두 이 코드가 센 값이다.")
a("- 줄 번호는 CSV 파일의 줄 번호(머리글 = 1행)다. 예시는 파일 순서상 처음 2개를 원본 글자 그대로 옮겼다.")
a("- '휴무 제외'라고 적은 종류는 비고가 `휴무`인 줄(날씨 · 메뉴가 비어 있고 출근예정 · 식수가 0)을 빼고 셌다.")
a("")
a("## 1. 줄 수 · 열 이름 · 날짜 범위")
a("")
a("| 항목 | 값 |")
a("|---|---|")
a(f"| 데이터 줄 수(머리글 제외) | {len(df)} |")
a(f"| 열 수 | {len(df.columns)} |")
a(f"| 열 이름 | {' · '.join(df.columns)} |")
a(f"| 날짜 범위 | {parsed.min():%Y-%m-%d} ~ {parsed.max():%Y-%m-%d} |")
a(f"| 날짜를 읽지 못한 줄 | {int(parsed.isna().sum())} |")
a(f"| 출근예정 · 식수 칸에 숫자가 아닌 글자 | 출근예정 {bad_num['출근예정']} · 식수 {bad_num['식수']} |")
a("")
a("날짜 형식(진단용으로 읽은 방법). 연도 없는 `M월 D일`은 안내서 R1대로 10–12월 → 2025년, 1–9월 → 2026년으로 읽었다.")
a("")
a("| 형식 | 줄 수 | 예시 |")
a("|---|---|---|")
for _, name in PATS + [(None, "기타")]:
    m = dk == name
    if name == "기타" and not m.any():
        continue
    a(f"| {name} | {int(m.sum())} | {examples(m, ex_date)} |")
a("")

a("## 2. 엉망인 곳 — 종류별")
a("")
a("| 종류 | 줄 수 | 예시 2개(원본 글자 그대로) |")
a("|---|---|---|")
rows = [
    ("날짜 형식 섞임(`YYYY-MM-DD`가 아님)",
     f"{int(m_date.sum())} ({breakdown(counts(dk[m_date]))})",
     examples(m_date, ex_date)),
    ("요일 표기 섞임(한 글자가 아님)",
     f"{int(m_day.sum())} ({breakdown(counts(dyk[m_day]))})",
     examples(m_day, lambda i: f"{i}행 {q(df.at[i, '날짜'])} {q(df.at[i, '요일'])}")),
    ("(덧붙임) 적힌 요일 ≠ 날짜로 계산한 요일",
     f"{int(m_mis.sum())}",
     examples(m_mis, lambda i: f"{i}행 {q(df.at[i, '날짜'])} {q(df.at[i, '요일'])} → 실제 {true_day[i]}")),
    ("같은 날짜가 두 줄",
     f"{int(m_dup.sum())}줄 · 날짜 {len(dup_groups)}개 ({breakdown(dup_kind_counts.items())})",
     " · ".join(f"{'·'.join(map(str, g.index))}행 {q(g['날짜'].iloc[0])} 식수 {'/'.join(g['식수'])}"
                for _, g, _ in dup_groups[:2])),
    ("휴무 줄(비고 = `휴무`)",
     f"{int(hol.sum())}",
     examples(hol, lambda i: f"{i}행 {q(df.at[i, '날짜'])} 출근예정 {q(df.at[i, '출근예정'])} 식수 {q(df.at[i, '식수'])}")),
    ("식수 빈칸",
     f"{int(m_meal_blank.sum())}",
     examples(m_meal_blank, lambda i: f"{i}행 {q(df.at[i, '날짜'])} 비고 {q(df.at[i, '비고'])}")),
    ("불가능해 보이는 식수(식수 > 출근예정, 또는 < 출근예정의 20%) — 휴무 제외",
     f"{int(m_imp.sum())} (많음 {int((m_imp & (meal > att)).sum())} · 너무 적음 {int((m_imp & (meal < att * 0.2)).sum())})",
     examples(m_imp, lambda i: f"{i}행 {q(df.at[i, '날짜'])} 출근예정 {q(df.at[i, '출근예정'])} 식수 {q(df.at[i, '식수'])}")),
    ("날씨 표기 섞임(맑음 · 흐림 · 비 · 눈이 아님) — 휴무 제외",
     f"{int(m_w.sum())} ({breakdown((f'`{k}`', v) for k, v in counts(w[m_w]))})",
     examples(m_w, lambda i: f"{i}행 {q(df.at[i, '날씨'])}")),
    ("날씨 빈칸 — 휴무 제외",
     f"{int(m_wb.sum())}",
     examples(m_wb, lambda i: f"{i}행 {q(df.at[i, '날짜'])} 날씨 {q(df.at[i, '날씨'])}")),
    ("최고기온 단위(℃ · °C)와 빈칸 — 휴무 제외",
     f"{int(m_temp.sum())} (`℃` {int(m_c1.sum())} · `°C` {int(m_c2.sum())} · 빈칸 {int(m_tb.sum())})",
     examples(m_temp, lambda i: f"{i}행 {q(df.at[i, '최고기온'])}")),
    ("메뉴 · 행사 이름 섞임(안내서 R9의 변형 이름)",
     f"{int(m_name.sum())} (메뉴 {int(m_menu.sum())} · 행사 {int(m_event.sum())})",
     examples(m_name, lambda i: f"{i}행 " + " / ".join(
         f"{col} {q(df.at[i, col])}" for col, m in [("메인메뉴", m_menu), ("행사", m_event)] if m[i]))),
    ("출근예정 빈칸 — 휴무 제외",
     f"{int(m_att_blank.sum())}",
     examples(m_att_blank, lambda i: f"{i}행 {q(df.at[i, '날짜'])} 출근예정 {q(df.at[i, '출근예정'])} 식수 {q(df.at[i, '식수'])}")),
]
for name, n, ex in rows:
    a(f"| {name} | {n} | {ex} |")
a("")

a("### 2-1. 같은 날짜가 두 줄 — 전부")
a("")
a("| 날짜(읽은 값) | 줄 | 원본 날짜 | 식수 | 비고 | 구분 |")
a("|---|---|---|---|---|---|")
for d, g, kind in dup_groups:
    a(f"| {d:%Y-%m-%d} | {', '.join(map(str, g.index))} | {' / '.join(map(q, g['날짜']))} | "
      f"{' / '.join(g['식수'])} | {' / '.join(map(q, g['비고']))} | {kind} |")
a("")

a("### 2-2. 적힌 요일이 날짜와 다른 줄 — 전부")
a("")
a("| 줄 | 원본 날짜 | 적힌 요일 | 날짜로 계산한 요일 |")
a("|---|---|---|---|")
for i in df.index[m_mis]:
    a(f"| {i} | {q(df.at[i, '날짜'])} | {q(df.at[i, '요일'])} | {true_day[i]} |")
a("")

a("### 2-3. 메뉴 · 행사 이름과 줄 수(휴무 제외) — 놓친 변형이 없는지 사람이 보는 표")
a("")
for col, var in [("메인메뉴", MENU_VAR), ("행사", EVENT_VAR)]:
    a(f"| {col} | 줄 수 | R9 변형이면 |")
    a("|---|---|---|")
    for k, v in counts(df.loc[work, col]):
        a(f"| {q(k)} | {v} | {'→ ' + var[k] if k in var else ''} |")
    a("")

a("## 3. 비고 열에 나오는 글")
a("")
a("| 비고(원본 그대로) | 줄 수 |")
a("|---|---|")
note = df["비고"]
for k, v in counts(note[note != ""]):
    a(f"| {q(k)} | {v} |")
a(f"| (빈칸) | {int((note == '').sum())} |")
a("")

a("## 4. 지울지 고칠지 사람이 정해야 할 줄")
a("")
a("'불가능해 보이는 식수'에 걸린 줄이다. 판단은 하지 않고, 기록에 있는 것만 적는다.")
a("")
a("| 줄 | 날짜 | 출근예정 | 식수 | 식수 ÷ 출근예정 | 비고 | 메모 |")
a("|---|---|---|---|---|---|---|")
human = []
for i in df.index[m_imp]:
    nt = df.at[i, "비고"]
    if nt == "수기 집계":
        memo = (f"정제 R6에서 수강생이 `뺀다` / `×10 보정` 중 정할 줄 "
                f"(참고: ×10이면 {meal[i] * 10:.0f} = 출근예정의 {meal[i] * 10 / att[i] * 100:.1f}%)")
    elif nt == "":
        memo = "비고 없음 — 고칠 근거가 기록에 없다(R6대로면 빠지는 줄)"
    else:
        memo = "비고 있음 — 비고를 보고 사람이 정한다"
    human.append((i, df.at[i, "날짜"], df.at[i, "출근예정"], df.at[i, "식수"], nt))
    a(f"| {i} | {q(df.at[i, '날짜'])} | {df.at[i, '출근예정']} | {df.at[i, '식수']} | "
      f"{meal[i] / att[i] * 100:.1f}% | {q(nt)} | {memo} |")
a("")

OUT.write_text("\n".join(L), encoding="utf-8", newline="\n")

# ---- 화면 요약
print(f"줄 수 {len(df)} | 날짜 {parsed.min():%Y-%m-%d} ~ {parsed.max():%Y-%m-%d}")
for name, n, _ in rows:
    print(f"- {name}: {n}")
print("사람이 정할 줄:", human)
print("저장:", OUT)
