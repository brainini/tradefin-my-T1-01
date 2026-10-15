"""2일차: buyers 시트 정제 — workbench/day2/rules/정제규칙.md 1–7칸을 코드로 옮긴 것

실행: uv run python scripts/clean_buyers.py
입력(읽기만): data/checkpoints/d2_start.xlsx 시트 buyers · fx_at_ref
              data/checkpoints/fx_krw_daily.csv
출력: workbench/day2/outputs/d2_buyers_clean.csv (150행 × 25열)
      workbench/day2/outputs/dq_report.md (정제 전·후 비교)
규칙에 없는 상황(모르는 통화 표기, 숫자로 바뀌지 않는 금액 등)을 만나면 추측하지 않고 멈춘다.
행 번호는 엑셀 행 번호(머리글 = 1행)다.
"""

import hashlib
import numbers
import re
from pathlib import Path

import pandas as pd

SRC = Path("data/checkpoints/d2_start.xlsx")
FX_DAILY = Path("data/checkpoints/fx_krw_daily.csv")
OUT_CSV = Path("workbench/day2/outputs/d2_buyers_clean.csv")
OUT_MD = Path("workbench/day2/outputs/dq_report.md")
ASOF = pd.Timestamp("2026-08-31")

AMT = ["ar_balance", "ar_current", "ar_1_30", "ar_31_60", "ar_61_90", "ar_91p"]
BUCKETS = AMT[1:]
FIN5 = ["current_assets", "current_liabilities", "total_liabilities", "equity", "revenue"]
FIN7 = ["current_assets", "current_liabilities", "total_liabilities", "equity",
        "accounts_receivable", "revenue", "operating_income"]
RATIO_IN = {
    "current_ratio": ["current_assets", "current_liabilities"],
    "debt_to_equity": ["total_liabilities", "equity"],
    "dso_buyer": ["accounts_receivable", "revenue"],
    "op_margin": ["operating_income", "revenue"],
}
# 1칸 매핑표(TRIM + UPPER 뒤 키)
CCY_MAP = {"USD": "USD", "US$": "USD", "EUR": "EUR", "EURO": "EUR",
           "JPY": "JPY", "YEN": "JPY", "CNY": "CNY", "RMB": "CNY"}
FX_COL = {"USD": "usd_krw", "EUR": "eur_krw", "CNY": "cny_krw", "JPY": "jpy100_krw"}
FX_UNIT = {"USD": 1, "EUR": 1, "CNY": 1, "JPY": 100}  # JPY는 100엔당 값

OUT_COLS = [
    "buyer_id", "payment_method", "ccy_clean", "amt_num", "ar_balance_usd",
    "pct_current", "pct_ar_31p", "pct_91plus", "max_dpd", "avg_days_late",
    "late_ratio", "dpd_trend", "dispute_ratio", "current_ratio", "debt_to_equity",
    "dso_buyer", "op_margin", "fin_missing", "neg_equity", "country_risk",
    "crc_unclassified", "unit_flag", "fx_chg_30d", "fx_chg_30d_lag30", "late_30d",
]


def stop(msg):
    raise SystemExit(f"[멈춤] {msg}")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def f(x, d=0):
    return "빈칸" if pd.isna(x) else f"{x:,.{d}f}"


hash_before = sha256(SRC)
raw = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
fx_ref = pd.read_excel(SRC, sheet_name="fx_at_ref", dtype=object)
fx = pd.read_csv(FX_DAILY, parse_dates=["date"]).set_index("date").sort_index()
xrow = raw.index + 2
bid = raw.buyer_id
g = lambda c: pd.to_numeric(raw[c])

# ── 1칸 통화
cur_key = raw.currency.astype(str).str.strip().str.upper()
unknown = sorted(set(cur_key) - set(CCY_MAP))
if unknown:
    stop(f"1칸: 매핑표에 없는 통화 표기 {unknown}")
ccy = cur_key.map(CCY_MAP)


# ── 2칸 숫자 변환
def to_num(v, k, where):
    if isinstance(v, numbers.Number) and not isinstance(v, bool):
        if pd.isna(v):
            stop(f"2칸: {where} 빈칸")
        return float(v)
    t = str(v).strip()
    mult = 1
    if re.search(r"\d\s*[kK]$", t):
        mult, t = 1000, t[:-1]
    for w in re.findall(r"[A-Za-z$]+", t):
        if CCY_MAP.get(w.upper()) != k:
            stop(f"2칸: {where} 금액 칸 통화 '{w}'가 ccy {k}와 다름")
    t = re.sub(r"[A-Za-z$,\s]", "", t)
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        stop(f"2칸: {where} 값 {v!r}를 숫자로 바꿀 수 없음")
    return float(t) * mult


num = pd.DataFrame(
    {c: [to_num(v, k, f"{b} {c}(행 {r})") for v, k, b, r in zip(raw[c], ccy, bid, xrow)] for c in AMT},
    index=raw.index,
)
is_text = raw[AMT].map(lambda v: isinstance(v, str))
is_cent = num.map(lambda v: v != int(v))


# ── 7칸 환율 · 시차: 그날 또는 직전 관측일 값, 기준일 뒤 값은 쓰지 않는다
def rate_on(day):
    s = fx.loc[:day]
    return s.index[-1], s.iloc[-1]


d0, r0 = rate_on(ASOF)
d30, r30 = rate_on(ASOF - pd.Timedelta(days=30))
d60, r60 = rate_on(ASOF - pd.Timedelta(days=60))
if d0 > ASOF:
    stop("7칸: 기준일 뒤 환율이 잡혔음")
krw = {c: r0[col] / FX_UNIT[c] for c, col in FX_COL.items()}
chg30 = {c: r0[col] / r30[col] - 1 for c, col in FX_COL.items()}
chg60 = {c: r0[col] / r60[col] - 1 for c, col in FX_COL.items()}
lag30 = {c: r30[col] / r60[col] - 1 for c, col in FX_COL.items()}
ar_balance_usd = num.ar_balance * ccy.map(krw) / krw["USD"]

# ── 4칸 단위 의심(값은 고치지 않는다)
limit = g("credit_limit_usd")
unit_flag = (ar_balance_usd > limit * 10).astype(int)
bucket_sum = num[BUCKETS].sum(axis=1)
bal_mismatch = ((num.ar_balance - bucket_sum).abs() > 1).astype(int)

# 잔액 비중: 분모 = 구간 5열 합(미결 잔액), 0이면 빈칸
den = bucket_sum.where(bucket_sum > 0)
pct_current = num.ar_current / den
pct_ar_31p = num[["ar_31_60", "ar_61_90", "ar_91p"]].sum(axis=1) / den
pct_91plus = num.ar_91p / den

# 연체 · 분쟁: 인보이스 0건이면 빈칸
inv = g("invoices_12m").where(lambda s: s > 0)
late_ratio = g("late_invoices_12m") / inv
dispute_ratio = g("dispute_cnt_12m") / inv
dpd_trend = g("avg_dpd_last3m") - g("avg_dpd_prev3m")

# ── 3칸 결측: 플래그 + 재무 7열 중위수 채움(*_fill, 내부 열)
fin = raw[FIN7].apply(pd.to_numeric)
fin_missing = fin[FIN5].isna().any(axis=1).astype(int)
med = fin.median()
fill = fin.fillna(med)

# ── 5칸 자본잠식: 원본 equity ≤ 0이면 플래그, D/E는 빈칸
neg_equity = (fin.equity <= 0).astype(int)
current_ratio = fill.current_assets / fill.current_liabilities
debt_to_equity = (fill.total_liabilities / fill.equity).where(neg_equity == 0)
dso_buyer = fill.accounts_receivable / fill.revenue * 365
op_margin = fill.operating_income / fill.revenue

# ── 6칸 국가위험
crc_raw = raw.oecd_crc
crc_unclassified = (crc_raw.isna() | (crc_raw.astype(str).str.strip() == "-")).astype(int)
country_risk = pd.to_numeric(crc_raw.where(crc_unclassified == 0, 0), errors="coerce")
if country_risk.isna().any() or not country_risk.between(0, 7).all():
    stop(f"6칸: 숫자로 읽히지 않는 oecd_crc {crc_raw[country_risk.isna()].unique().tolist()}")
country_risk = country_risk.astype(int)
per_cc = pd.DataFrame({"cc": raw.country_code, "r": country_risk}).groupby("cc").r.nunique()
if (per_cc > 1).any():
    stop(f"6칸: 같은 국가코드 안에서 등급이 다름 {per_cc[per_cc > 1].index.tolist()}")

# ── 결과 표
out = pd.DataFrame({
    "buyer_id": bid,
    "payment_method": raw.payment_method,
    "ccy_clean": ccy,
    "amt_num": num.ar_balance,
    "ar_balance_usd": ar_balance_usd.round(2),
    "pct_current": pct_current.round(6),
    "pct_ar_31p": pct_ar_31p.round(6),
    "pct_91plus": pct_91plus.round(6),
    "max_dpd": g("max_dpd").astype(int),
    "avg_days_late": g("avg_days_late_12m"),
    "late_ratio": late_ratio.round(6),
    "dpd_trend": dpd_trend.round(6),
    "dispute_ratio": dispute_ratio.round(6),
    "current_ratio": current_ratio.round(6),
    "debt_to_equity": debt_to_equity.round(6),
    "dso_buyer": dso_buyer.round(6),
    "op_margin": op_margin.round(6),
    "fin_missing": fin_missing,
    "neg_equity": neg_equity,
    "country_risk": country_risk,
    "crc_unclassified": crc_unclassified,
    "unit_flag": unit_flag,
    "fx_chg_30d": ccy.map(chg30).round(6),
    "fx_chg_30d_lag30": ccy.map(lag30).round(6),
    "late_30d": g("late_30d").astype(int),
})[OUT_COLS]
if len(out) != 150 or not out.buyer_id.is_unique:
    stop(f"결과 행 수 {len(out)} 또는 buyer_id 중복")
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_CSV, index=False, encoding="utf-8")

hash_after = sha256(SRC)
if hash_after != hash_before:
    stop("원본 해시가 바뀌었음")

# ── dq_report.md
L = []
L.append("# buyers 정제 전·후 비교 — 2일차\n")
L.append("> `scripts/clean_buyers.py`가 만든 파일입니다. 숫자는 모두 스크립트 계산값입니다. "
         "규칙: `workbench/day2/rules/정제규칙.md` 1–7칸\n")
L.append(f"- 입력(읽기만): `{SRC.as_posix()}` 시트 `buyers` · `fx_at_ref`, `{FX_DAILY.as_posix()}`")
L.append(f"- 기준일: {ASOF.date()}")
L.append(f"- 원본 SHA-256 실행 전 `{hash_before[:12]}…` = 실행 후 `{hash_after[:12]}…` (같음, 원본 무수정)")
L.append(f"- 출력: `{OUT_CSV.as_posix()}` — {len(out)}행 × {out.shape[1]}열, buyer_id 고유 {out.buyer_id.nunique()}\n")

L.append("## 1. 전·후 건수\n")
fin_blank_cells = int(fin.isna().sum().sum())
L.append(md_table(["항목", "정제 전", "정제 후", "규칙"], [
    ["통화 표기 종류(`currency` → `ccy_clean`)", raw.currency.nunique(), out.ccy_clean.nunique(), "1칸"],
    ["글자로 저장된 금액 칸(금액 6열)", int(is_text.values.sum()), 0, "2칸"],
    ["센트 소수 금액 칸(금액 6열)", int(is_cent.values.sum()), f"{int(is_cent.values.sum())} (값 그대로)", "2칸"],
    ["`oecd_crc` 글자 칸(`\"-\"`)", int((crc_raw.astype(str).str.strip() == "-").sum()), 0, "6칸"],
    ["재무 7열 빈칸(칸 수)", fin_blank_cells, f"0 (중위수로 채운 내부 열 `*_fill`)", "3칸"],
    ["재무 결측 바이어(`fin_missing` = 1)", "–", int(fin_missing.sum()), "3칸"],
    ["단위 의심(`unit_flag` = 1)", "–", f"{int(unit_flag.sum())} (값은 그대로)", "4칸"],
    ["잔액 ≠ 구간 합(`bal_mismatch`, CSV 열 없음)", int(bal_mismatch.sum()), f"{int(bal_mismatch.sum())} (표시만)", "4칸"],
    ["자본잠식(`neg_equity` = 1)", "–", int(neg_equity.sum()), "5칸"],
    ["국가위험 미분류(`crc_unclassified` = 1)", "–", int(crc_unclassified.sum()), "6칸"],
]))
L.append("")

L.append("## 2. 변환 내역\n")
L.append("### 통화 표기 → `ccy_clean`\n")
cmap = raw.groupby([raw.currency, ccy.rename("ccy_clean")]).size().reset_index(name="n").sort_values(["ccy_clean", "currency"])
L.append(md_table(["원본 표기", "ccy_clean", "건수"], cmap.values.tolist()))
L.append("")
L.append("### 글자 · 소수 금액 → 숫자\n")
rows = []
for c in AMT:
    for i in raw.index[is_text[c] | is_cent[c]]:
        rows.append([xrow[i], bid[i], c, f"`{raw.at[i, c]!r}`", ccy[i], f(num.at[i, c], 2)])
L.append(md_table(["행", "buyer_id", "열", "원본", "ccy", "숫자"], rows))
L.append("")

L.append("## 3. 결과 열 빈칸\n")
blank = out.isna().sum()
why = {
    "pct_current": "구간 합(미결 잔액) 0", "pct_ar_31p": "구간 합(미결 잔액) 0", "pct_91plus": "구간 합(미결 잔액) 0",
    "avg_days_late": "`invoices_12m` = 0 — 3칸에서 채우지 않기로 함",
    "late_ratio": "`invoices_12m` = 0", "dispute_ratio": "`invoices_12m` = 0",
    "dpd_trend": "최근 · 직전 3개월 평균 DPD 중 하나라도 빈칸 — 3칸에서 채우지 않기로 함",
    "debt_to_equity": "`neg_equity` = 1 — 5칸",
}
L.append(md_table(["열", "빈칸", "이유"], [[c, int(blank[c]), why.get(c, "")] for c in OUT_COLS if blank[c] > 0]))
L.append(f"\n나머지 {sum(blank == 0)}열은 빈칸이 없습니다.\n")

L.append("## 4. 결측 채우기(3칸)\n")
L.append("재무 7열의 빈칸을 그 열에서 값이 있는 행의 중위수로 채운 뒤 비율을 계산했습니다.\n")
L.append(md_table(["열", "빈칸", "채운 중위수(USD)"], [[c, int(fin[c].isna().sum()), f(med[c])] for c in FIN7]))
gap = int(((fin[["accounts_receivable", "operating_income"]].isna().any(axis=1)) & (fin_missing == 0)).sum())
L.append(f"\n- `fin_missing`은 5열(유동자산 · 유동부채 · 총부채 · 자기자본 · 매출)만 봅니다. "
         f"매출채권 · 영업이익만 빈 **{gap}행**은 채워졌지만 `fin_missing` = 0입니다.")
L.append("- 비율마다 재료가 실제 값인지, 채운 값인지, 둘이 섞였는지 나눠 봤습니다. "
         "섞인 행은 실제 값 하나와 중위수 하나로 계산되므로 값이 튈 수 있습니다.\n")
rows = []
for k, cols in RATIO_IN.items():
    miss = fin[cols].isna()
    valid = out[k].notna()
    actual, allf = ~miss.any(axis=1) & valid, miss.all(axis=1) & valid
    mixed = miss.any(axis=1) & ~miss.all(axis=1) & valid
    rng = lambda m: f"{f(out.loc[m, k].min(), 4)} ~ {f(out.loc[m, k].max(), 4)}" if m.any() else "–"
    rows.append([k, int(actual.sum()), int(allf.sum()), int(mixed.sum()), rng(actual), rng(mixed)])
L.append(md_table(["비율", "실제 값만", "모두 채운 값", "섞임", "실제 값 범위", "섞인 행 범위"], rows))
L.append("")

L.append("## 5. 환율(7칸)\n")
L.append(f"관측일: 기준일 {d0.date()} · 30일 전 → {d30.date()} · 60일 전 → {d60.date()} (그날 관측이 없으면 직전 관측일)\n")
ref = fx_ref[pd.to_datetime(fx_ref.ref_date) == ASOF].assign(ccy=lambda d: d.ccy.replace({"JPY100": "JPY"})).set_index("ccy")
rows = []
for c in FX_COL:
    same = (round(chg30[c], 4) == round(float(ref.at[c, "chg_30d"]), 4)
            and round(chg60[c], 4) == round(float(ref.at[c, "chg_60d"]), 4))
    rows.append([c, f(r0[FX_COL[c]], 2), f"{chg30[c]:.4%}", f"{lag30[c]:.4%}",
                 f"{float(ref.at[c, 'chg_30d']):.2%} / {float(ref.at[c, 'chg_60d']):.2%}", "같음" if same else "**다름**"])
L.append(md_table(["통화", "KRW(기준일)", "fx_chg_30d", "fx_chg_30d_lag30", "fx_at_ref chg_30d / chg_60d", "대조"], rows))
L.append("\nUSD 환산 = 금액 × (KRW/통화) ÷ (KRW/USD), JPY는 100엔당 값이라 ÷100. 기준일 뒤 값(2026-09 환율)은 쓰지 않았습니다.\n")

L.append("## 6. 플래그 대상\n")
rows = []
for i in raw.index[(unit_flag == 1) | (bal_mismatch == 1)]:
    rows.append([xrow[i], bid[i], f"`{raw.at[i, 'ar_balance']!r}` {ccy[i]}", f(bucket_sum[i], 2),
                 f(ar_balance_usd[i], 0), f(limit[i]), f"{ar_balance_usd[i] / limit[i]:.1f}배", unit_flag[i], bal_mismatch[i]])
L.append(md_table(["행", "buyer_id", "ar_balance(원본)", "구간 합", "USD 환산", "한도", "한도 대비", "unit_flag", "bal_mismatch"], rows))
L.append("")
rows = [[xrow[i], bid[i], f(fin.at[i, "equity"]), f(fin.at[i, "total_liabilities"])] for i in raw.index[neg_equity == 1]]
L.append(md_table(["행", "buyer_id", "equity", "total_liabilities"], rows))
L.append("\n4칸 규칙대로 B072 등 단위 의심 값은 고치지 않았습니다. 원천을 확인한 뒤 사람이 정합니다.\n")

L.append("## 7. 결과 열 정의와 출처\n")
DICT = "과정 사전 `data/data_dictionary.xlsx`"
L.append(md_table(["열", "계산", "출처"], [
    ["buyer_id · payment_method · max_dpd · late_30d", "원본 그대로", "원본"],
    ["ccy_clean", "`currency` TRIM + UPPER → 4종 매핑", "정제규칙 1칸"],
    ["amt_num", "`ar_balance` 숫자 변환(공백 · 콤마 · 통화 글자 제거, k ×1,000)", "정제규칙 2칸"],
    ["ar_balance_usd", "amt_num × KRW/통화 ÷ KRW/USD", "정제규칙 7칸"],
    ["pct_current · pct_ar_31p · pct_91plus", "구간 금액 ÷ 구간 5열 합, 0이면 빈칸", f"{DICT}(d3) — **분모를 구간 합으로 한 것은 이번에 정함(확인 필요)**"],
    ["avg_days_late", "`avg_days_late_12m` 그대로(빈칸 유지)", "정제규칙 3칸"],
    ["late_ratio", "`late_invoices_12m` ÷ `invoices_12m`, 0건이면 빈칸", "**사전 · 규칙에 없음 — 이번에 정함(확인 필요)**"],
    ["dpd_trend", "`avg_dpd_last3m` − `avg_dpd_prev3m`, 한쪽 빈칸이면 빈칸", f"{DICT}(d3)"],
    ["dispute_ratio", "`dispute_cnt_12m` ÷ `invoices_12m`, 0건이면 빈칸", "**사전 · 규칙에 없음 — 이번에 정함(확인 필요)**"],
    ["current_ratio · dso_buyer · op_margin", "채운 재무 열로 계산(유동자산 ÷ 유동부채 · 매출채권 ÷ 매출 × 365 · 영업이익 ÷ 매출)", f"{DICT} + 정제규칙 3칸"],
    ["debt_to_equity", "총부채 ÷ 자기자본, `neg_equity` = 1이면 빈칸", f"{DICT} + 정제규칙 3 · 5칸"],
    ["fin_missing", "5열 중 하나라도 빈칸이면 1", "정제규칙 3칸"],
    ["neg_equity", "원본 `equity` ≤ 0이면 1", "정제규칙 5칸"],
    ["country_risk · crc_unclassified", "`\"-\"` · 빈칸 → 0 + 1", "정제규칙 6칸"],
    ["unit_flag", "USD 환산 잔액 > 한도 × 10", "정제규칙 4칸"],
    ["fx_chg_30d · fx_chg_30d_lag30", "청구 통화의 기준일 ÷ 30일 전 − 1 · 30일 전 ÷ 60일 전 − 1", "정제규칙 7칸"],
]))
L.append("\n반올림: `ar_balance_usd`는 소수 2자리, 비율 · 환율 변화 열은 소수 6자리. `amt_num`은 원본 자릿수 그대로.\n")

OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"원본 해시 같음: {hash_before == hash_after}")
print(f"{OUT_CSV}: {out.shape[0]}행 × {out.shape[1]}열 | 첫 열 {out.columns[0]} | 끝 열 {out.columns[-1]}")
print(f"통화 {raw.currency.nunique()} → {out.ccy_clean.nunique()} | 글자 금액 {int(is_text.values.sum())} → 0 | "
      f"fin_missing {int(fin_missing.sum())} | unit_flag {bid[unit_flag == 1].tolist()} | "
      f"neg_equity {bid[neg_equity == 1].tolist()} | crc_unclassified {int(crc_unclassified.sum())}")
print("채운 중위수:", {c: float(med[c]) for c in FIN7})
print("빈칸:", {c: int(v) for c, v in blank.items() if v})
print(f"{OUT_MD} 작성")
