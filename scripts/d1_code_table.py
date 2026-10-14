"""1일차: payment_terms_raw 표기 → 표준 결제조건 코드 7종 매핑표 만들기

실행: uv run python scripts/d1_code_table.py [xlsx 경로]
  경로를 주지 않으면 data/day1/d1_buyers_raw.xlsx를 읽는다(원본은 읽기만).
출력: workbench/day1/outputs/d1_code_table.csv (utf-8-sig)
  열: 원래 표기 | 표준 코드 | 판단 근거(어느 단어로) | 확신(높음/낮음)

규칙은 위에서부터 차례로 보고 처음 맞는 규칙을 쓴다. 비교는 앞뒤 공백 제거 + 대문자로 한다.
애매한 표기는 코드를 추측하지 않고 '검토 필요'로 둔다.
끝에 data/data_dictionary.xlsx의 payment_terms_map과 대조해 차이를 화면에 찍는다(대조만, 매핑에는 안 씀).
"""

import re
import sys

import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/day1/d1_buyers_raw.xlsx"
DICT = "data/data_dictionary.xlsx"
OUT = "workbench/day1/outputs/d1_code_table.csv"
REVIEW = "검토 필요"

# (정규식, 표준 코드, 판단 근거, 확신) — 순서가 중요하다
RULES = [
    (r"^(T/T|TT)$", REVIEW,
     "'TT'만 있음 — 선적 전(선수금)인지 선적 후(사후송금)인지, 기간이 없음", "낮음"),
    (r"10%.*90%", REVIEW,
     "'10% T/T advance + 90% O/A' — 10/90 분할은 7종에 맞는 코드 없음(30/70만 있음)", "낮음"),
    (r"30%.*ADVANCE.*70%.*AFTER B/L", "TT_SPLIT_30_70",
     "'30% T/T advance' + '70% within 30 days after B/L' — 코드 정의와 문구 일치", "높음"),
    (r"^T/T 30\s*[/:]\s*70$", "TT_SPLIT_30_70",
     "'30/70'(또는 30:70) 분할 비율 — 단 잔금 70%의 지급 시점(선적 전/후)이 표기에 없음", "낮음"),
    (r"(L/C|\bLC\b).*(AT SIGHT)|신용장 일람불", "LC_SIGHT",
     "'L/C'·'신용장' + 'at sight'·'일람불'", "높음"),
    (r"USANCE.*L/C|L/C \d+ DAYS", "LC_USANCE",
     "'L/C' + 'usance' 또는 일수(기한부)", "높음"),
    (r"^D/?P\b|DOCUMENTS AGAINST PAYMENT", "DP",
     "'D/P'·'DP' (지급인도 추심)", "높음"),
    (r"^D/?A\s*\d|^D/A\b|DOCUMENTS AGAINST ACCEPTANCE", "DA",
     "'D/A'·'DA'·'Documents against acceptance' (인수인도 추심)", "높음"),
    (r"T/T IN ADVANCE|100% T/T BEFORE SHIPMENT", "TT_ADV",
     "'in advance'·'before shipment' (선적 전 송금)", "높음"),
    (r"\bO/?A\b|^OA\d|O/A\d|OPEN ACC(OUN)?T", "OA",
     "'O/A'·'OA'·'Open account' (사후송금)", "높음"),
    (r"^NET \d+", "OA",
     "'Net N' — 송장 후 N일 지급 = 사후송금(사전 codes 시트 OA 비고: '공공 Net30 포함')", "높음"),
    (r"^T/T \d+\s*DAYS", "OA",
     "'T/T' + 일수(+ after B/L) — 선적 후 송금 = 사후송금(사전 codes 시트 OA 비고)", "높음"),
]


def classify(raw):
    key = raw.strip().upper()
    for pat, code, why, conf in RULES:
        if re.search(pat, key):
            return code, why, conf
    return REVIEW, "맞는 규칙 없음", "낮음"


df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
raws = pd.Series(df.payment_terms_raw.unique())

table = pd.DataFrame(
    [(r, *classify(r)) for r in raws],
    columns=["원래 표기", "표준 코드", "판단 근거(어느 단어로)", "확신(높음/낮음)"],
)
order = ["TT_ADV", "TT_SPLIT_30_70", "LC_SIGHT", "LC_USANCE", "DP", "DA", "OA", REVIEW]
table["_o"] = table["표준 코드"].map(order.index)
table["_k"] = table["원래 표기"].str.strip().str.upper()
table = table.sort_values(["_o", "_k", "원래 표기"]).drop(columns=["_o", "_k"])
table.to_csv(OUT, index=False, encoding="utf-8-sig")

print("표기 종류:", len(table), "| 행 수:", len(df))
print(table["표준 코드"].value_counts().to_dict())
print(table["확신(높음/낮음)"].value_counts().to_dict())
rows = df.payment_terms_raw.map(dict(zip(table["원래 표기"], table["표준 코드"])))
print("행 기준 분포:", rows.value_counts().to_dict())

# 사전 코드표와 대조 (매핑에는 쓰지 않음)
ptm = pd.read_excel(DICT, sheet_name="payment_terms_map", header=2, dtype=str)
mp = dict(zip(ptm.raw_upper.str.strip(), ptm.payment_method))
table["사전"] = table["원래 표기"].str.strip().str.upper().map(mp)
diff = table[table["사전"].notna() & (table["사전"] != table["표준 코드"])]
print("사전과 다른 표기:", diff[["원래 표기", "표준 코드", "사전"]].values.tolist())
print("사전에 없는 표기:", table[table["사전"].isna()][["원래 표기", "표준 코드"]].values.tolist())
