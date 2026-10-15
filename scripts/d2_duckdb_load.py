"""2일차: CSV 3개를 DuckDB 테이블로 올리고 행 수 · 스키마 · 빈 값을 점검 (원본 CSV는 읽기만 한다)

실행: uv run python scripts/d2_duckdb_load.py
입력: workbench/day2/data/의 d1_buyers_raw.csv · d1_invoices.csv · fred_dexkous.csv
출력:
  - DuckDB 파일 workbench/day2/data/d2_duckdb.db (테이블 이름 = CSV 파일 이름)
    확장자 .db는 .gitignore의 *.db 줄에 걸려 커밋되지 않는다 — 이 스크립트로 언제든 다시 만든다.
  - 점검표 workbench/day2/outputs/d2_duckdb_profile.md (화면에도 같은 내용을 찍는다)
형 추론은 DuckDB 자동 감지(read_csv)에 맡긴다. 지저분한 값이 섞인 열은 VARCHAR가 된다.
"""

import csv
import sys
from pathlib import Path

import duckdb

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path("workbench/day2/data")
DB = DATA / "d2_duckdb.db"
OUT = Path("workbench/day2/outputs/d2_duckdb_profile.md")
TABLES = {
    "d1_buyers_raw": DATA / "d1_buyers_raw.csv",
    "d1_invoices": DATA / "d1_invoices.csv",
    "fred_dexkous": DATA / "fred_dexkous.csv",
}
KEYS = {"d1_buyers_raw": "buyer_id", "d1_invoices": "invoice_id", "fred_dexkous": "observation_date"}
# NULL은 아니지만 값이 없다는 뜻일 수 있는 표기 — 빈 값으로 세지 않고 따로 보인다
PSEUDO_EMPTY = ["-", "확인중", "N/A", "NA", "n/a", "null", "NULL", "None", "nan"]

con = duckdb.connect(str(DB))
lines = []


def out(s=""):
    print(s)
    lines.append(s)


def q(name):
    return '"' + name.replace('"', '""') + '"'


out("# 2일차 DuckDB 적재 점검")
out()
out(f"- DB 파일: `{DB.as_posix()}` · 만든 코드: `scripts/d2_duckdb_load.py` · DuckDB {duckdb.__version__}")
out("- 빈 값 = DuckDB가 NULL로 읽은 칸(CSV에서 비어 있던 칸). 계산식: `count(*) - count(열)`")
out(f"- '빈 값 같은 표기' = VARCHAR 열에서 공백뿐이거나 {PSEUDO_EMPTY} 중 하나인 칸 — 빈 값 개수에는 넣지 않았다")
out()

# 1) 적재 + 행 수 대조 (DuckDB 행 수 vs 파이썬 csv 모듈로 센 데이터 행 수)
out("## 1. 행 수")
out()
out("| 테이블 | DuckDB 행 수 | csv 모듈 행 수 | 일치 | 열 수 | 키 열 | 키 고유값 | 키 중복 행 |")
out("|---|---:|---:|---|---:|---|---:|---:|")
for t, path in TABLES.items():
    con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_csv(?, header = true)", [path.as_posix()])
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    with open(path, encoding="utf-8-sig", newline="") as f:
        n_csv = sum(1 for _ in csv.reader(f)) - 1
    ncol = len(con.execute(f"DESCRIBE {t}").fetchall())
    k = KEYS[t]
    nk = con.execute(f"SELECT count(DISTINCT {q(k)}) FROM {t}").fetchone()[0]
    out(f"| {t} | {n:,} | {n_csv:,} | {'O' if n == n_csv else 'X'} | {ncol} | {k} | {nk:,} | {n - nk:,} |")
out()

# 2) 스키마 + 빈 값 (테이블마다)
for t in TABLES:
    cols = con.execute(f"DESCRIBE {t}").fetchall()  # (column_name, column_type, null, key, default, extra)
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    nulls = con.execute(
        "SELECT " + ", ".join(f"count(*) - count({q(c[0])})" for c in cols) + f" FROM {t}"
    ).fetchone()
    in_list = ", ".join("'" + v.replace("'", "''") + "'" for v in PSEUDO_EMPTY)
    pseudo = {}
    for c in cols:
        if c[1] == "VARCHAR":
            pseudo[c[0]] = con.execute(
                f"SELECT count(*) FILTER (WHERE trim({q(c[0])}) = '' OR trim({q(c[0])}) IN ({in_list})) FROM {t}"
            ).fetchone()[0]
    out(f"## 2. {t} — 스키마 · 빈 값 ({n:,}행)")
    out()
    out("| # | 열 | DuckDB 형 | 빈 값(NULL) | 빈 값 비율 | 빈 값 같은 표기 |")
    out("|---:|---|---|---:|---:|---:|")
    for i, (c, nn) in enumerate(zip(cols, nulls), 1):
        p = pseudo.get(c[0])
        out(f"| {i} | {c[0]} | {c[1]} | {nn:,} | {nn / n:.1%} | {'' if p is None else f'{p:,}'} |")
    out(f"| | **합계** | | **{sum(nulls):,}** | | **{sum(pseudo.values()):,}** |")
    out()

con.close()
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n저장: {OUT.as_posix()}")
