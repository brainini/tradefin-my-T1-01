"""3일차 D-1 · 03: design.md 토큰의 글자/바탕 대비(WCAG 2.x) 계산.

실행: uv run python scripts/d3_contrast.py
같은 토큰이면 같은 결과. 기준 4.5 : 1 이상.
"""

TOKENS = {
    "color-bg": "#F7F6F3",
    "color-surface": "#FFFFFF",
    "color-border": "#E2E0DB",
    "color-text": "#1C1B19",
    "color-text-muted": "#5E5B55",
    "color-accent": "#1F4E79",
    "grade-s": "#1E7044",
    "grade-a": "#9CC34A",
    "grade-b": "#E8A92A",
    "grade-c": "#B8322A",
}

# (글자 토큰, 바탕 토큰, 쓰는 곳)
PAIRS = [
    ("color-text", "color-bg", "본문 · 제목 (페이지 바탕)"),
    ("color-text", "color-surface", "본문 · KPI 숫자 · 표 (카드 면)"),
    ("color-text-muted", "color-bg", "보조 글자 · 기준일 · 바닥글 (페이지 바탕)"),
    ("color-text-muted", "color-surface", "보조 글자 · 표 머리 · 캡션 (카드 면)"),
    ("color-accent", "color-bg", "강조 글자 (페이지 바탕)"),
    ("color-accent", "color-surface", "강조 글자 · 슬라이더 값 (카드 면)"),
    ("color-surface", "grade-s", "등급 라벨 S (흰 글자 / S 바탕)"),
    ("color-text", "grade-a", "등급 라벨 A (본문 글자 / A 바탕)"),
    ("color-text", "grade-b", "등급 라벨 B (본문 글자 / B 바탕)"),
    ("color-surface", "grade-c", "등급 라벨 C (흰 글자 / C 바탕)"),
]


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float:
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


if __name__ == "__main__":
    print("| 글자 | 바탕 | 쓰는 곳 | 대비 | 4.5 이상 |")
    print("|---|---|---|---:|---|")
    worst = None
    for fg, bg, where in PAIRS:
        r = contrast(TOKENS[fg], TOKENS[bg])
        worst = r if worst is None else min(worst, r)
        ok = "예" if r >= 4.5 else "아니오"
        print(f"| `{fg}` {TOKENS[fg]} | `{bg}` {TOKENS[bg]} | {where} | {r:.2f} : 1 | {ok} |")
    print(f"\n가장 낮은 값: {worst:.2f} : 1")
