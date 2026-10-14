"""1일차: d1_buyers_raw.xlsx 품질 진단 (읽기 전용 — 값을 고치지 않는다)

실행: uv run python scripts/d1_quality_diagnose.py [xlsx 경로]
  경로를 주지 않으면 data/day1/d1_buyers_raw.xlsx를 읽는다.
  (엑셀에서 파일을 열어 두어 잠겨 있으면 사본 경로를 인자로 준다)
출력: workbench/day1/outputs/d1_quality_report.md 작성에 쓴 숫자를 화면에 찍는다.
행 번호는 엑셀 행 번호(머리글 = 1행)다.
"""

import re
import sys

import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/day1/d1_buyers_raw.xlsx"
DICT = "data/data_dictionary.xlsx"

df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
df.index = df.index + 2  # 엑셀 행 번호


def section(title):
    print(f"\n===== {title}")


# 1) 열별 유형 · 결측
section("열별 저장 유형 · 결측 · 고유값")
for c in df.columns:
    s = df[c]
    types = s.dropna().map(lambda v: type(v).__name__).value_counts().to_dict()
    print(f"{c}: 결측 {s.isna().sum()} | 고유 {s.nunique()} | {types}")

# 2) 중복
section("중복")
print("전체 행:", len(df), "| buyer_id 고유:", df.buyer_id.nunique())
dup_id = df[df.buyer_id.duplicated(keep=False)]
print("buyer_id 중복 행:", dup_id[["buyer_id", "buyer_name"]].to_dict("index"))
print("완전 동일 행:", df[df.duplicated(keep=False)].buyer_id.to_dict())
others = df.columns.drop(["buyer_name"])
print("buyer_name만 다른 행:", df[df.duplicated(subset=others, keep=False) & ~df.duplicated(keep=False)].buyer_id.to_dict())
norm = df.buyer_name.str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
g = df.groupby(norm).buyer_id.unique()
print("정규화 상호가 같은데 ID가 다른 경우:", g[g.map(len) > 1].to_dict())

# 3) 국가 · 코드 일관성
section("country → country_code")
print(df.groupby("country").country_code.unique().to_dict())
print("코드별 region:", df.groupby("country_code").region.unique().map(list).to_dict())
print("코드별 oecd_crc:", df.groupby("country_code").oecd_crc.unique().map(list).to_dict())
print(pd.crosstab(df.segment, df.buyer_type))
print("industry 결측:", df[df.industry.isna()][["buyer_id", "buyer_type"]].to_dict("index"))

# 4) 결제조건
section("payment_terms_raw")
pt = df.payment_terms_raw
up = pt.str.strip().str.upper()
print("원표기 고유", pt.nunique(), "| TRIM 후", pt.str.strip().nunique(), "| TRIM+UPPER 후", up.nunique())
print("앞뒤 공백:", pt[pt != pt.str.strip()].map(repr).to_dict())
ptm = pd.read_excel(DICT, sheet_name="payment_terms_map", header=2, dtype=str)
mp = dict(zip(ptm.raw_upper.str.strip(), ptm.payment_method))
print("사전 코드표에 없는 표기:", pt[~up.isin(mp)].map(repr).value_counts().to_dict())
print("코드표 대조 분포(참고):", up.map(mp).value_counts(dropna=False).to_dict())

# 5) 숫자처럼 보이는 글자
section("숫자 열의 글자 · 소수 값")
for c in ["ar_balance", "max_dpd_days", "overdue_amount", "pay_score", "oecd_crc",
          "revenue_usd_fy2025", "current_ratio_fy2025", "debt_to_equity_fy2025",
          "dso_fy2025", "op_margin_fy2025"]:
    s = df[c]
    txt = s[s.map(lambda v: isinstance(v, str))]
    print(f"{c}: 글자 {len(txt)}건", txt.map(repr).value_counts().to_dict() if c == "oecd_crc" else
          {k: (df.at[k, "buyer_id"], v) for k, v in txt.items()})
for c in ["ar_balance", "overdue_amount"]:
    s = df[c]
    f = s[s.map(lambda v: isinstance(v, float) and v == v and v != int(v))]
    print(f"{c}: 센트 단위 소수", {k: (df.at[k, "buyer_id"], v) for k, v in f.items()})
usd_pre = df.ar_balance.astype(str).str.startswith("USD") | df.overdue_amount.astype(str).str.startswith("USD")
print("USD 접두 행의 ar_currency:", df[usd_pre].set_index("buyer_id").ar_currency.to_dict())
print("ar_balance 결측:", df[df.ar_balance.isna()][["buyer_id", "ar_currency", "overdue_amount"]].to_dict("index"))

section("ar_currency")
print(df.ar_currency.value_counts().to_dict())
print(pd.crosstab(df.country_code, df.ar_currency).loc[lambda t: (t[["usd", "US$", "¥", "€"]] > 0).any(axis=1)])

# 6) 날짜 형식
section("since_date 형식")
PATS = [
    (r"^\d{4}-\d{2}-\d{2}$", "YYYY-MM-DD", "%Y-%m-%d"),
    (r"^\d{4}\.\d{1,2}\.\d{1,2}$", "YYYY.M.D", "%Y.%m.%d"),
    (r"^\d{2}/\d{2}/\d{4}$", "NN/NN/YYYY", "%d/%m/%Y"),
    (r"^[A-Z][a-z]{2} \d{1,2} \d{4}$", "Mon D YYYY", "%b %d %Y"),
]


def kind(v):
    for p, name, _ in PATS:
        if re.match(p, str(v)):
            return name
    return "기타"


fm = df.since_date.map(kind)
print(fm.value_counts().to_dict())
for name in fm.unique():
    print(name, "예:", df.since_date[fm == name].head(3).to_dict())
sl = df.since_date[fm == "NN/NN/YYYY"].str.split("/", expand=True).astype(int)
print("슬래시형", len(sl), "| 앞자리>12:", (sl[0] > 12).sum(), "| 가운데>12:", (sl[1] > 12).sum(),
      "| 둘 다 ≤12(모호):", ((sl[0] <= 12) & (sl[1] <= 12)).sum())
amb = sl[(sl[0] <= 12) & (sl[1] <= 12)].index
print("모호한 행:", {k: (df.at[k, "buyer_id"], df.at[k, "since_date"]) for k in amb})
parsed = pd.Series(pd.NaT, index=df.index)
for _, name, fmt in PATS:
    m = fm == name
    parsed[m] = pd.to_datetime(df.since_date[m], format=fmt)
print("범위(슬래시형은 DD/MM 가정):", parsed.min().date(), "~", parsed.max().date(),
      "| 기준일(2026-09-30) 이후:", (parsed > "2026-09-30").sum())

# 7) 교차 점검
section("교차 점검")
num = lambda c: pd.to_numeric(df[c], errors="coerce")
ar, od, dpd = num("ar_balance"), num("overdue_amount"), num("max_dpd_days")
print("미납 > 잔액:", (od > ar).sum(), "| 연체일>0인데 미납 0:", ((dpd > 0) & (od == 0)).sum(),
      "| 미납>0인데 연체일 0:", ((od > 0) & (dpd == 0)).sum())
fin = ["revenue_usd_fy2025", "current_ratio_fy2025", "debt_to_equity_fy2025", "dso_fy2025", "op_margin_fy2025"]
nr = df.fin_summary_text.str.contains("not received")
nd = df.fin_summary_text.str.contains("not disclosed")
part = df[fin].isna().any(axis=1) & ~nr
print("미수령 문장", nr.sum(), "→ 재무 5열 모두 빈칸", df[nr][fin].isna().all(axis=1).sum())
print("일부 빈칸", part.sum(), "→ 'not disclosed' 문장 있음", (part & nd).sum())
rv_txt = df.fin_summary_text.str.extract(r"USD ([\d.]+)M")[0].astype(float)
print("요약문 매출 ≠ 매출 열(±0.05M):", ((rv_txt - num("revenue_usd_fy2025") / 1e6).abs() > 0.05).sum())
om_txt = df.fin_summary_text.str.extract(r"operating (?:margin|loss) \(?(-?[\d.]+)%")[0].astype(float)
print("요약문 영업이익률 ≠ 열(±0.06%p):", ((om_txt - num("op_margin_fy2025") * 100).abs() > 0.06).sum(),
      "/ 대조", om_txt.notna().sum())
cr_txt = df.fin_summary_text.str.extract(r"Current ratio below 1.0 \(([\d.]+)\)")[0].astype(float)
print("요약문 유동비율 ≠ 열(±0.006):", ((cr_txt - num("current_ratio_fy2025")).abs() > 0.006).sum(),
      "/ 대조", cr_txt.notna().sum())
print("pay_score 결측 유형:", df[df.pay_score.isna()].buyer_type.value_counts().to_dict())
print("pay_score < 50:", df[num("pay_score") < 50][["buyer_id", "pay_score", "max_dpd_days"]].values.tolist())
de = num("debt_to_equity_fy2025")
print("부채비율 음수:", df[de < 0][["buyer_id", "debt_to_equity_fy2025"]].values.tolist())
print("부채비율 > 5:", df[de > 5][["buyer_id", "debt_to_equity_fy2025"]].values.tolist())
print("max_dpd_days 최대:", dpd.max(), "| 91일 이상:", df[dpd >= 91][["buyer_id", "max_dpd_days"]].values.tolist())
