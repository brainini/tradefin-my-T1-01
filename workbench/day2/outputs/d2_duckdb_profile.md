# 2일차 DuckDB 적재 점검

- DB 파일: `workbench/day2/data/d2_duckdb.db` · 만든 코드: `scripts/d2_duckdb_load.py` · DuckDB 1.5.6
- 빈 값 = DuckDB가 NULL로 읽은 칸(CSV에서 비어 있던 칸). 계산식: `count(*) - count(열)`
- '빈 값 같은 표기' = VARCHAR 열에서 공백뿐이거나 ['-', '확인중', 'N/A', 'NA', 'n/a', 'null', 'NULL', 'None', 'nan'] 중 하나인 칸 — 빈 값 개수에는 넣지 않았다

## 1. 행 수

| 테이블 | DuckDB 행 수 | csv 모듈 행 수 | 일치 | 열 수 | 키 열 | 키 고유값 | 키 중복 행 |
|---|---:|---:|---|---:|---|---:|---:|
| d1_buyers_raw | 153 | 153 | O | 23 | buyer_id | 150 | 3 |
| d1_invoices | 5,033 | 5,033 | O | 22 | invoice_id | 5,033 | 0 |
| fred_dexkous | 801 | 801 | O | 2 | observation_date | 801 | 0 |

## 2. d1_buyers_raw — 스키마 · 빈 값 (153행)

| # | 열 | DuckDB 형 | 빈 값(NULL) | 빈 값 비율 | 빈 값 같은 표기 |
|---:|---|---|---:|---:|---:|
| 1 | buyer_id | VARCHAR | 0 | 0.0% | 0 |
| 2 | buyer_name | VARCHAR | 0 | 0.0% | 0 |
| 3 | country | VARCHAR | 0 | 0.0% | 0 |
| 4 | country_code | VARCHAR | 0 | 0.0% | 0 |
| 5 | region | VARCHAR | 0 | 0.0% | 0 |
| 6 | industry | VARCHAR | 5 | 3.3% | 0 |
| 7 | segment | VARCHAR | 0 | 0.0% | 0 |
| 8 | buyer_type | VARCHAR | 0 | 0.0% | 0 |
| 9 | payment_terms_raw | VARCHAR | 0 | 0.0% | 0 |
| 10 | ar_balance | VARCHAR | 3 | 2.0% | 0 |
| 11 | ar_currency | VARCHAR | 0 | 0.0% | 0 |
| 12 | max_dpd_days | VARCHAR | 0 | 0.0% | 2 |
| 13 | overdue_amount | VARCHAR | 0 | 0.0% | 0 |
| 14 | pay_score | BIGINT | 46 | 30.1% |  |
| 15 | oecd_crc | VARCHAR | 0 | 0.0% | 58 |
| 16 | ksure_insured | VARCHAR | 0 | 0.0% | 0 |
| 17 | since_date | VARCHAR | 0 | 0.0% | 0 |
| 18 | fin_summary_text | VARCHAR | 0 | 0.0% | 0 |
| 19 | revenue_usd_fy2025 | BIGINT | 19 | 12.4% |  |
| 20 | current_ratio_fy2025 | DOUBLE | 40 | 26.1% |  |
| 21 | debt_to_equity_fy2025 | DOUBLE | 35 | 22.9% |  |
| 22 | dso_fy2025 | DOUBLE | 40 | 26.1% |  |
| 23 | op_margin_fy2025 | DOUBLE | 38 | 24.8% |  |
| | **합계** | | **226** | | **60** |

## 2. d1_invoices — 스키마 · 빈 값 (5,033행)

| # | 열 | DuckDB 형 | 빈 값(NULL) | 빈 값 비율 | 빈 값 같은 표기 |
|---:|---|---|---:|---:|---:|
| 1 | invoice_id | VARCHAR | 0 | 0.0% | 0 |
| 2 | buyer_id | VARCHAR | 0 | 0.0% | 0 |
| 3 | country_code | VARCHAR | 0 | 0.0% | 0 |
| 4 | invoice_date | DATE | 0 | 0.0% |  |
| 5 | payment_method | VARCHAR | 0 | 0.0% | 0 |
| 6 | terms_days | BIGINT | 0 | 0.0% |  |
| 7 | currency | VARCHAR | 0 | 0.0% | 0 |
| 8 | amount_ccy | DOUBLE | 0 | 0.0% |  |
| 9 | amount_usd | DOUBLE | 0 | 0.0% |  |
| 10 | fx_krw_at_invoice | DOUBLE | 0 | 0.0% |  |
| 11 | amount_krw_at_invoice | DOUBLE | 0 | 0.0% |  |
| 12 | due_date | DATE | 0 | 0.0% |  |
| 13 | advance_pct | DOUBLE | 0 | 0.0% |  |
| 14 | ksure_insured | VARCHAR | 0 | 0.0% | 0 |
| 15 | dispute_flag | BIGINT | 0 | 0.0% |  |
| 16 | dispute_type | VARCHAR | 4,357 | 86.6% | 0 |
| 17 | lc_discrepancy_days | BIGINT | 4,685 | 93.1% |  |
| 18 | settled_date | DATE | 316 | 6.3% |  |
| 19 | status | VARCHAR | 0 | 0.0% | 0 |
| 20 | amount_krw_at_settle | DOUBLE | 316 | 6.3% |  |
| 21 | fx_reval_krw | DOUBLE | 4,732 | 94.0% |  |
| 22 | fx_gain_loss_krw | DOUBLE | 15 | 0.3% |  |
| | **합계** | | **14,421** | | **0** |

## 2. fred_dexkous — 스키마 · 빈 값 (801행)

| # | 열 | DuckDB 형 | 빈 값(NULL) | 빈 값 비율 | 빈 값 같은 표기 |
|---:|---|---|---:|---:|---:|
| 1 | observation_date | DATE | 0 | 0.0% |  |
| 2 | DEXKOUS | DOUBLE | 34 | 4.2% |  |
| | **합계** | | **34** | | **0** |

