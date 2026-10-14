"""1일차: 인보이스(d1_invoices.csv) 결제방식(payment_method)별 현황표와 막대 차트.

원본은 읽기만 한다.
실행: uv run python scripts/d1_ar_by_method.py
결과: workbench/day1/outputs/ar_by_method.csv, workbench/day1/outputs/charts/ar_by_method.png

계산식
- 연체일 = 결제일(settled_date) − 만기일(due_date). 결제일이 없으면 AS_OF − 만기일
- 30일 초과 연체 비율 = 연체일 > 30 인 인보이스 수 ÷ 그 결제방식의 인보이스 수
- 미결 금액 = status == "open" 인 인보이스의 amount_usd 합
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path("data/day1/d1_invoices.csv")
OUT_CSV = Path("workbench/day1/outputs/ar_by_method.csv")
OUT_PNG = Path("workbench/day1/outputs/charts/ar_by_method.png")
FONT = Path("tools/fonts/NanumGothic-Regular.ttf")
AS_OF = pd.Timestamp("2026-09-30")  # 결제일이 없을 때 쓰는 기준일
OVERDUE_DAYS = 30

COLS = ["결제방식", "인보이스 수", "금액 합계(USD)", "미결 금액(USD)", "30일 초과 연체 비율"]

# 차트 색(dataviz 기본 팔레트 라이트 모드)
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"

# ---------------------------------------------------------------- 계산
df = pd.read_csv(SRC, parse_dates=["due_date", "settled_date"])
df["days_late"] = (df["settled_date"].fillna(AS_OF) - df["due_date"]).dt.days
df["over30"] = df["days_late"] > OVERDUE_DAYS
df["open_usd"] = df["amount_usd"].where(df["status"] == "open", 0.0)


def summarize(g):
    return pd.Series({
        "인보이스 수": len(g),
        "금액 합계(USD)": g["amount_usd"].sum(),
        "미결 금액(USD)": g["open_usd"].sum(),
        "30일 초과 연체 비율": g["over30"].sum() / len(g),
    })


table = (df.groupby("payment_method")[["amount_usd", "open_usd", "over30"]]
         .apply(summarize)
         .sort_values("금액 합계(USD)", ascending=False)
         .rename_axis("결제방식").reset_index())
total = summarize(df)  # 합계 행: 비율도 전체 기준으로 다시 계산
table.loc[len(table)] = ["합계", *total.values]
table["인보이스 수"] = table["인보이스 수"].astype(int)

# 검산
assert table["인보이스 수"].iloc[-1] == len(df) == table["인보이스 수"].iloc[:-1].sum()
assert round(table["미결 금액(USD)"].iloc[-1], 2) == round(df.loc[df["status"] == "open", "amount_usd"].sum(), 2)

# ---------------------------------------------------------------- 저장(CSV)
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
out = table[COLS].copy()
out["금액 합계(USD)"] = out["금액 합계(USD)"].round(2)
out["미결 금액(USD)"] = out["미결 금액(USD)"].round(2)
out["30일 초과 연체 비율"] = out["30일 초과 연체 비율"].round(4)
out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 화면 출력(Markdown 표)
print(f"기준일 {AS_OF.date()} · 원본 {SRC} {len(df):,}건")
print("연체일 = settled_date(없으면 기준일) − due_date / 30일 초과 연체 비율 = (연체일 > 30) 건수 ÷ 인보이스 수\n")
print("| " + " | ".join(COLS) + " |")
print("|---|---:|---:|---:|---:|")
for r in table.itertuples(index=False):
    print(f"| {r[0]} | {r[1]:,} | {r[2]:,.2f} | {r[3]:,.2f} | {r[4]:.1%} |")
print(f"\n저장: {OUT_CSV}")

# ---------------------------------------------------------------- 차트
font_manager.fontManager.addfont(str(FONT))
plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(FONT)).get_name()
plt.rcParams["axes.unicode_minus"] = False

chart = table.iloc[:-1].iloc[::-1]  # 합계 행 제외, 큰 금액이 위로
y = range(len(chart))
h = 0.36


def usd_m(v, _=None):
    if v >= 1e6:
        return f"${v / 1e6:,.1f}M"
    return f"${v / 1e3:,.0f}K" if v >= 1e3 else f"${v:,.0f}"


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True,
                               gridspec_kw={"width_ratios": [1.6, 1], "wspace": 0.08})
fig.patch.set_facecolor(SURFACE)

b1 = ax1.barh([i + h / 2 for i in y], chart["금액 합계(USD)"], height=h, color=BLUE, label="금액 합계")
b2 = ax1.barh([i - h / 2 for i in y], chart["미결 금액(USD)"], height=h, color=ORANGE, label="미결 금액(status=open)")
for bars in (b1, b2):
    ax1.bar_label(bars, labels=[usd_m(v) for v in bars.datavalues], padding=4, fontsize=8.5, color=INK_2)
ax1.xaxis.set_major_formatter(FuncFormatter(usd_m))
ax1.set_xlim(0, chart["금액 합계(USD)"].max() * 1.15)
ax1.set_title("금액 합계 vs 미결 금액 (USD)", loc="left", fontsize=11.5, color=INK)
ax1.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK_2)

pct = chart["30일 초과 연체 비율"] * 100
b3 = ax2.barh(list(y), pct, height=h * 1.4, color=BLUE)
ax2.bar_label(b3, labels=[f"{v:.1f}%" for v in pct], padding=4, fontsize=8.5, color=INK_2)
ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax2.set_xlim(0, max(pct.max() * 1.25, 5))
ax2.set_title("30일 초과 연체 비율 (건수 기준)", loc="left", fontsize=11.5, color=INK)

ax1.set_yticks(list(y))
ax1.set_yticklabels([f"{m}  ({n:,}건)" for m, n in zip(chart["결제방식"], chart["인보이스 수"])])
for ax in (ax1, ax2):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)

fig.suptitle(f"결제방식별 인보이스 현황 (기준일 {AS_OF.date()}, 전체 {len(df):,}건)",
             x=0.01, ha="left", fontsize=14, color=INK)
fig.text(0.01, 0.01, "연체일 = 결제일(없으면 기준일) - 만기일. 자료: data/day1/d1_invoices.csv (합성 데이터)",
         fontsize=8, color=INK_2)
OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight", facecolor=SURFACE)
print(f"저장: {OUT_PNG}")
