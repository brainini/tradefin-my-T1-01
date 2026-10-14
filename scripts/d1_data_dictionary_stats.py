"""1일차: d1_buyers_raw.xlsx 변수 정의서용 열별 통계 (읽기 전용)

실행: uv run python scripts/d1_data_dictionary_stats.py [xlsx 경로]
  경로를 주지 않으면 data/day1/d1_buyers_raw.xlsx를 읽는다.
출력: workbench/day1/outputs/d1_data_dictionary.md 의 '결측 수' · '관측 범위' 숫자를 화면에 찍는다.
결측 = 빈 셀. 숫자 열의 글자 값(예: '49.2k')은 결측이 아니라 '글자 n건'으로 따로 센다.
"""

import sys

import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/day1/d1_buyers_raw.xlsx"
df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
print("행:", len(df), "| 열:", df.shape[1])

for c in df.columns:
    s = df[c]
    nonnull = s.dropna()
    is_text = nonnull.map(lambda v: isinstance(v, str))
    num = pd.to_numeric(nonnull[~is_text], errors="coerce")
    line = f"{c}: 결측 {s.isna().sum()} | 글자 {is_text.sum()} | 숫자 {len(num)}"
    if len(num):
        line += f" | 숫자 범위 {num.min()} ~ {num.max()} | 중앙값 {num.median()}"
    if s.nunique() <= 10:
        line += f" | 값 {nonnull.astype(str).value_counts().to_dict()}"
    print(line)

# 재무 지표 참고 통계
fin = ["current_ratio_fy2025", "debt_to_equity_fy2025", "dso_fy2025", "op_margin_fy2025"]
f = df[fin].apply(pd.to_numeric, errors="coerce")
print("\n재무 지표 분위수")
print(f.describe(percentiles=[0.25, 0.5, 0.75]).round(4).to_string())
print("유동비율 < 1.0:", (f.current_ratio_fy2025 < 1).sum(),
      "| 부채비율 < 0(자본잠식):", (f.debt_to_equity_fy2025 < 0).sum(),
      "| 영업이익률 < 0:", (f.op_margin_fy2025 < 0).sum())
