"""2일차: 뉴스 점수 파일(news_scored.jsonl)을 규칙 파일(news_score_v1.md)의 [출력] · 규칙 2 · 5에 맞춰 검사 (점수는 고치지 않는다)

실행: uv run python scripts/validate_scores.py [검사할 jsonl 경로]
입력: workbench/day2/outputs/news_scored.jsonl(경로를 주면 그 파일) · data/checkpoints/d2_news.csv(원문, 읽기만 한다)
검사:
  1. 줄 수가 EXPECTED_LINES(100)인가
  2. news_sent_0_10이 0–10 정수인가 (7.0 같은 실수 · true/false · 문자열은 위반)
  3. label이 점수 대역과 맞는가 — 0–2 severe, 3–4 high, 5 watch, 6–10 low
  4. evidence가 같은 news_id 원문의 headline 또는 body_short 안에 글자 그대로 있는가
출력: 위반 행 표(화면). 위반이 하나라도 있으면 종료 코드 1.
"""

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCORES = Path(sys.argv[1] if len(sys.argv) > 1 else "workbench/day2/outputs/news_scored.jsonl")
NEWS = Path("data/checkpoints/d2_news.csv")
EXPECTED_LINES = 100
BANDS = [(0, 2, "severe"), (3, 4, "high"), (5, 5, "watch"), (6, 10, "low")]


def band(score):
    return next(label for lo, hi, label in BANDS if lo <= score <= hi)


with open(NEWS, encoding="utf-8-sig", newline="") as f:
    news = {r["news_id"]: r for r in csv.DictReader(f)}
lines = SCORES.read_text(encoding="utf-8-sig").splitlines()

problems = []  # (줄 번호, news_id, 검사 항목, 내용)
if len(lines) != EXPECTED_LINES:
    problems.append(("-", "-", "1. 줄 수", f"{len(lines)}줄 (기대 {EXPECTED_LINES}줄)"))

for i, line in enumerate(lines, 1):
    try:
        row = json.loads(line)
    except json.JSONDecodeError as e:
        problems.append((i, "-", "JSON", f"읽지 못함 — {e}"))
        continue
    nid = row.get("news_id", "-")

    score = row.get("news_sent_0_10")
    score_ok = isinstance(score, int) and not isinstance(score, bool) and 0 <= score <= 10
    if not score_ok:
        problems.append((i, nid, "2. 점수", f"{score!r} — 0–10 정수가 아님"))
    elif row.get("label") != band(score):
        problems.append((i, nid, "3. 라벨", f"점수 {score} → {band(score)}여야 하는데 {row.get('label')!r}"))

    ev = row.get("evidence")
    src = news.get(nid)
    if src is None:
        problems.append((i, nid, "4. evidence", "원문에 이 news_id가 없음"))
    elif not isinstance(ev, str) or not ev or (ev not in src["headline"] and ev not in src["body_short"]):
        problems.append((i, nid, "4. evidence", f"원문 headline · body_short에 그대로 없음 — {ev!r}"))

print(f"# 뉴스 점수 검사 — {SCORES.as_posix()}")
print()
print(f"- 줄 수 {len(lines)} / 기대 {EXPECTED_LINES} · 원문 {NEWS.as_posix()} {len(news)}행")
print(f"- 위반 {len(problems)}건 · 위반 행 {len({p[0] for p in problems if p[0] != '-'})}줄")
print()
if problems:
    print("| 줄 | news_id | 검사 | 내용 |")
    print("|---:|---|---|---|")
    for p in problems:
        print(f"| {p[0]} | {p[1]} | {p[2]} | {p[3].replace('|', '\\|')} |")
else:
    print("위반 없음")
sys.exit(1 if problems else 0)
