# buyers 정제 전·후 비교 — 2일차

> `scripts/clean_buyers.py`가 만든 파일입니다. 숫자는 모두 스크립트 계산값입니다. 규칙: `workbench/day2/rules/정제규칙.md` 1–7칸

- 입력(읽기만): `data/checkpoints/d2_start.xlsx` 시트 `buyers` · `fx_at_ref`, `data/checkpoints/fx_krw_daily.csv`
- 기준일: 2026-08-31
- 원본 SHA-256 실행 전 `724ad02fe09f…` = 실행 후 `724ad02fe09f…` (같음, 원본 무수정)
- 출력: `workbench/day2/outputs/d2_buyers_clean.csv` — 150행 × 25열, buyer_id 고유 150

## 1. 전·후 건수

| 항목 | 정제 전 | 정제 후 | 규칙 |
|---|---|---|---|
| 통화 표기 종류(`currency` → `ccy_clean`) | 9 | 4 | 1칸 |
| 글자로 저장된 금액 칸(금액 6열) | 13 | 0 | 2칸 |
| 센트 소수 금액 칸(금액 6열) | 2 | 2 (값 그대로) | 2칸 |
| `oecd_crc` 글자 칸(`"-"`) | 57 | 0 | 6칸 |
| 재무 7열 빈칸(칸 수) | 203 | 0 (중위수로 채운 내부 열 `*_fill`) | 3칸 |
| 재무 결측 바이어(`fin_missing` = 1) | – | 47 | 3칸 |
| 단위 의심(`unit_flag` = 1) | – | 1 (값은 그대로) | 4칸 |
| 잔액 ≠ 구간 합(`bal_mismatch`, CSV 열 없음) | 2 | 2 (표시만) | 4칸 |
| 자본잠식(`neg_equity` = 1) | – | 2 | 5칸 |
| 국가위험 미분류(`crc_unclassified` = 1) | – | 57 | 6칸 |

## 2. 변환 내역

### 통화 표기 → `ccy_clean`

| 원본 표기 | ccy_clean | 건수 |
|---|---|---|
| CNY | CNY | 5 |
| RMB | CNY | 2 |
| EUR | EUR | 18 |
| euro | EUR | 5 |
| JPY | JPY | 8 |
| yen | JPY | 2 |
| US$ | USD | 15 |
| USD | USD | 81 |
| usd | USD | 14 |

### 글자 · 소수 금액 → 숫자

| 행 | buyer_id | 열 | 원본 | ccy | 숫자 |
|---|---|---|---|---|---|
| 6 | B005 | ar_balance | `' 195900 '` | USD | 195,900.00 |
| 10 | B009 | ar_balance | `'CNY 317,000'` | CNY | 317,000.00 |
| 16 | B015 | ar_balance | `'7,680'` | USD | 7,680.00 |
| 30 | B029 | ar_balance | `60187.68` | USD | 60,187.68 |
| 35 | B034 | ar_balance | `'200,520'` | EUR | 200,520.00 |
| 44 | B043 | ar_balance | `'155,200 CNY'` | CNY | 155,200.00 |
| 84 | B083 | ar_balance | `'2,200'` | USD | 2,200.00 |
| 87 | B086 | ar_balance | `'EUR 143,620'` | EUR | 143,620.00 |
| 115 | B114 | ar_balance | `' 1458000 '` | JPY | 1,458,000.00 |
| 142 | B141 | ar_balance | `'47.0k'` | EUR | 47,000.00 |
| 77 | B076 | ar_current | `'51,970'` | EUR | 51,970.00 |
| 92 | B091 | ar_current | `'7,980'` | EUR | 7,980.00 |
| 9 | B008 | ar_1_30 | `'6,850'` | EUR | 6,850.00 |
| 73 | B072 | ar_1_30 | `'8,320'` | EUR | 8,320.00 |
| 30 | B029 | ar_31_60 | `21007.68` | USD | 21,007.68 |

## 3. 결과 열 빈칸

| 열 | 빈칸 | 이유 |
|---|---|---|
| pct_current | 51 | 구간 합(미결 잔액) 0 |
| pct_ar_31p | 51 | 구간 합(미결 잔액) 0 |
| pct_91plus | 51 | 구간 합(미결 잔액) 0 |
| avg_days_late | 11 | `invoices_12m` = 0 — 3칸에서 채우지 않기로 함 |
| late_ratio | 11 | `invoices_12m` = 0 |
| dpd_trend | 55 | 최근 · 직전 3개월 평균 DPD 중 하나라도 빈칸 — 3칸에서 채우지 않기로 함 |
| dispute_ratio | 11 | `invoices_12m` = 0 |
| debt_to_equity | 2 | `neg_equity` = 1 — 5칸 |

나머지 17열은 빈칸이 없습니다.

## 4. 결측 채우기(3칸)

재무 7열의 빈칸을 그 열에서 값이 있는 행의 중위수로 채운 뒤 비율을 계산했습니다.

| 열 | 빈칸 | 채운 중위수(USD) |
|---|---|---|
| current_assets | 18 | 17,593,000 |
| current_liabilities | 39 | 11,560,000 |
| total_liabilities | 18 | 22,628,500 |
| equity | 34 | 14,948,000 |
| accounts_receivable | 39 | 6,499,000 |
| revenue | 18 | 44,007,000 |
| operating_income | 37 | 1,704,000 |

- `fin_missing`은 5열(유동자산 · 유동부채 · 총부채 · 자기자본 · 매출)만 봅니다. 매출채권 · 영업이익만 빈 **25행**은 채워졌지만 `fin_missing` = 0입니다.
- 비율마다 재료가 실제 값인지, 채운 값인지, 둘이 섞였는지 나눠 봤습니다. 섞인 행은 실제 값 하나와 중위수 하나로 계산되므로 값이 튈 수 있습니다.

| 비율 | 실제 값만 | 모두 채운 값 | 섞임 | 실제 값 범위 | 섞인 행 범위 |
|---|---|---|---|---|---|
| current_ratio | 111 | 18 | 21 | 0.3600 ~ 2.5861 | 0.1807 ~ 32.5401 |
| debt_to_equity | 114 | 18 | 16 | 0.2695 ~ 10.4589 | 0.2434 ~ 7.5199 |
| dso_buyer | 111 | 18 | 21 | 30.3081 ~ 146.8463 | 4.7311 ~ 367.2604 |
| op_margin | 113 | 18 | 19 | -0.2487 ~ 0.1740 | 0.0034 ~ 0.3163 |

## 5. 환율(7칸)

관측일: 기준일 2026-08-31 · 30일 전 → 2026-07-31 · 60일 전 → 2026-07-02 (그날 관측이 없으면 직전 관측일)

| 통화 | KRW(기준일) | fx_chg_30d | fx_chg_30d_lag30 | fx_at_ref chg_30d / chg_60d | 대조 |
|---|---|---|---|---|---|
| USD | 1,368.25 | -4.7717% | -6.5824% | -4.77% / -11.04% | 같음 |
| EUR | 1,589.50 | -3.9612% | -6.0031% | -3.96% / -9.73% | 같음 |
| CNY | 203.62 | -4.3274% | -6.0602% | -4.33% / -10.13% | 같음 |
| JPY | 856.55 | -5.1177% | -5.5602% | -5.12% / -10.39% | 같음 |

USD 환산 = 금액 × (KRW/통화) ÷ (KRW/USD), JPY는 100엔당 값이라 ÷100. 기준일 뒤 값(2026-09 환율)은 쓰지 않았습니다.

## 6. 플래그 대상

| 행 | buyer_id | ar_balance(원본) | 구간 합 | USD 환산 | 한도 | 한도 대비 | unit_flag | bal_mismatch |
|---|---|---|---|---|---|---|---|---|
| 73 | B072 | `8320000` EUR | 8,320.00 | 9,665,368 | 10,000 | 966.5배 | 1 | 1 |
| 142 | B141 | `'47.0k'` EUR | 47,030.00 | 54,600 | 80,000 | 0.7배 | 0 | 1 |

| 행 | buyer_id | equity | total_liabilities |
|---|---|---|---|
| 14 | B013 | -15,126,000 | 109,262,000 |
| 49 | B048 | -37,662,000 | 160,609,000 |

4칸 규칙대로 B072 등 단위 의심 값은 고치지 않았습니다. 원천을 확인한 뒤 사람이 정합니다.

## 7. 결과 열 정의와 출처

| 열 | 계산 | 출처 |
|---|---|---|
| buyer_id · payment_method · max_dpd · late_30d | 원본 그대로 | 원본 |
| ccy_clean | `currency` TRIM + UPPER → 4종 매핑 | 정제규칙 1칸 |
| amt_num | `ar_balance` 숫자 변환(공백 · 콤마 · 통화 글자 제거, k ×1,000) | 정제규칙 2칸 |
| ar_balance_usd | amt_num × KRW/통화 ÷ KRW/USD | 정제규칙 7칸 |
| pct_current · pct_ar_31p · pct_91plus | 구간 금액 ÷ 구간 5열 합, 0이면 빈칸 | 과정 사전 `data/data_dictionary.xlsx`(d3) — **분모를 구간 합으로 한 것은 이번에 정함(확인 필요)** |
| avg_days_late | `avg_days_late_12m` 그대로(빈칸 유지) | 정제규칙 3칸 |
| late_ratio | `late_invoices_12m` ÷ `invoices_12m`, 0건이면 빈칸 | **사전 · 규칙에 없음 — 이번에 정함(확인 필요)** |
| dpd_trend | `avg_dpd_last3m` − `avg_dpd_prev3m`, 한쪽 빈칸이면 빈칸 | 과정 사전 `data/data_dictionary.xlsx`(d3) |
| dispute_ratio | `dispute_cnt_12m` ÷ `invoices_12m`, 0건이면 빈칸 | **사전 · 규칙에 없음 — 이번에 정함(확인 필요)** |
| current_ratio · dso_buyer · op_margin | 채운 재무 열로 계산(유동자산 ÷ 유동부채 · 매출채권 ÷ 매출 × 365 · 영업이익 ÷ 매출) | 과정 사전 `data/data_dictionary.xlsx` + 정제규칙 3칸 |
| debt_to_equity | 총부채 ÷ 자기자본, `neg_equity` = 1이면 빈칸 | 과정 사전 `data/data_dictionary.xlsx` + 정제규칙 3 · 5칸 |
| fin_missing | 5열 중 하나라도 빈칸이면 1 | 정제규칙 3칸 |
| neg_equity | 원본 `equity` ≤ 0이면 1 | 정제규칙 5칸 |
| country_risk · crc_unclassified | `"-"` · 빈칸 → 0 + 1 | 정제규칙 6칸 |
| unit_flag | USD 환산 잔액 > 한도 × 10 | 정제규칙 4칸 |
| fx_chg_30d · fx_chg_30d_lag30 | 청구 통화의 기준일 ÷ 30일 전 − 1 · 30일 전 ÷ 60일 전 − 1 | 정제규칙 7칸 |

반올림: `ar_balance_usd`는 소수 2자리, 비율 · 환율 변화 열은 소수 6자리. `amt_num`은 원본 자릿수 그대로.

