"""3일차 실습 D · 내 아이디어(7절 ⑥): 바이어 월드 프로토타입.

labs/day3/lab-d/buyer_board.csv를 읽어 계산하고, 3D 월드 HTML 한 장을 쓴다.
- 지역 6개 = 섬 6개, 바이어 150곳 = 건물, 대표님 캐릭터가 섬과 건물 사이를 걸어 다닌다.
- 위험한 곳이 모인 섬은 흐리고 비가 오며(먹구름), 안전한 섬은 맑다. 날씨는 낙인이 아니라 '예보'다.
- 숫자와 배치 좌표는 이 스크립트가 계산해 페이지 안 JSON에 넣는다. 페이지 JS는 위험 선을
  움직일 때만 v1과 같은 등급 규칙으로 다시 계산한다.

실행: uv run python scripts/world_proto.py
      uv run python scripts/world_proto.py --artifact <경로>   # 아티팩트 게시용(문서 껍데기 없는 본문)
같은 입력이면 같은 결과. 원본 CSV는 읽기만 한다. v1(board_page.py · buyer_board.html)은 건드리지 않는다.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import board_page as bp  # noqa: E402  v1의 토큰 · 나라 이름 · 등급 규칙 · 표시 함수를 그대로 쓴다

# design.md 2-8 — 월드 프로토타입 토큰(v1 토큰 위에 더한다)
WORLD_TOKENS = {
    "world-sky": "#E6E9E7",
    "world-sea": "#B7C9CF",
    "world-land-1": "#C9D6A8",
    "world-land-2": "#C2C7A4",
    "world-land-3": "#B3B2A0",
    "world-land-4": "#9C968E",
    "world-wall": "#EFECE6",
    "world-cloud": "#F4F4F1",
    "world-storm": "#55585E",
    "world-rain": "#6E8794",
    "world-skin": "#E3BC9C",
    "world-hub": "#DAD6CE",
    "panel-w": "360px",
    "focus-width": "2px",
}
TOKENS = {**bp.TOKENS, **WORLD_TOKENS}

OUT = bp.ROOT / "workbench" / "day3" / "outputs" / "buyer_world_proto.html"
THREE_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.170.0/three.module.min.js"

# 섬 배치: 본사(가운데)를 중심으로 대략의 지리 방향(도, 위쪽 = 북쪽)
REGION_ANGLE = {
    "북미·중남미": 180,
    "서유럽": 125,
    "중동부유럽": 72,
    "동아시아": 18,
    "동남아·남아": -42,
    "중동·아프리카": -110,
}
HUB_R = 4.5      # 본사 광장 반지름
CELL = 2.2       # 건물 간격
ISLAND_PAD = 2.0  # 가장 바깥 건물에서 섬 가장자리까지
GAP = 3.0        # 섬과 섬 사이 최소 바다 폭
WEATHER_CUTS = (0.10, 0.25, 0.50)  # C등급 채권 비중 → 맑음 · 구름 조금 · 흐림 · 비


def weather_step(share: float) -> int:
    return sum(share >= c for c in WEATHER_CUTS)


def island_cells(n: int) -> list[tuple[int, int]]:
    """가운데에서 가까운 칸 n개를 고른 뒤 각도 순으로 늘어놓는다(나라가 부채꼴로 모이게)."""
    cells = [(i, j) for i in range(-8, 9) for j in range(-8, 9)]
    cells.sort(key=lambda c: (c[0] ** 2 + c[1] ** 2, round(math.atan2(c[1], c[0]), 9), c[0], c[1]))
    chosen = cells[:n]
    chosen.sort(key=lambda c: (round(math.atan2(-c[1], c[0]), 9), c[0] ** 2 + c[1] ** 2, c[0], c[1]))
    return chosen


def layout(df: pd.DataFrame) -> tuple[dict, dict]:
    """바이어 좌표(x, z)와 섬(가운데 · 반지름 · 표지판)을 결정적으로 계산한다."""
    pos, islands = {}, {}
    for region, ang in REGION_ANGLE.items():
        sub = df[df["region"] == region].sort_values(["country_code", "buyer_id"])
        cells = island_cells(len(sub))
        r = max(math.hypot(i, j) for i, j in cells) * CELL + ISLAND_PAD
        islands[region] = {"ang": ang, "r": r, "d": HUB_R + r + GAP, "cells": cells, "ids": list(sub["buyer_id"])}

    def centers():
        return {
            k: (v["d"] * math.cos(math.radians(v["ang"])), -v["d"] * math.sin(math.radians(v["ang"])))
            for k, v in islands.items()
        }

    # 겹치는 섬은 바깥으로 조금씩 민다(같은 입력 → 같은 결과)
    for _ in range(200):
        c, moved = centers(), False
        names = list(islands)
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                ka, kb = names[a], names[b]
                dist = math.dist(c[ka], c[kb])
                if dist < islands[ka]["r"] + islands[kb]["r"] + GAP:
                    islands[ka]["d"] += 0.5
                    islands[kb]["d"] += 0.5
                    moved = True
        if not moved:
            break

    c = centers()
    for region, v in islands.items():
        cx, cz = c[region]
        for bid, (i, j) in zip(v["ids"], v["cells"]):
            pos[bid] = (round(cx + i * CELL, 3), round(cz + j * CELL, 3))
        # 표지판: 섬 가장자리 중 본사 쪽
        ux, uz = -cx / math.hypot(cx, cz), -cz / math.hypot(cx, cz)
        v["center"] = (round(cx, 3), round(cz, 3))
        v["sign"] = (round(cx + ux * (v["r"] - 0.9), 3), round(cz + uz * (v["r"] - 0.9), 3))
    return pos, islands


HEAD_EXTRA = """<title>바이어 월드</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap">"""

CSS = """
*{box-sizing:border-box}
html,body{height:100%;margin:0;overflow:hidden;background:var(--world-sky)}
body{font-family:var(--font-sans);font-size:var(--text-sm);line-height:var(--lh-sm);color:var(--color-text);word-break:keep-all;overflow-wrap:break-word;-webkit-tap-highlight-color:transparent}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.muted{color:var(--color-text-muted)}
button{font:inherit;color:inherit}
button:focus-visible,input:focus-visible{outline:var(--focus-width) solid var(--color-accent);outline-offset:var(--focus-width)}

#stage{position:fixed;inset:0;background:var(--world-sky)}
#stage canvas{display:block;width:100%;height:100%;touch-action:none;cursor:pointer}
#labels{position:fixed;inset:0;pointer-events:none;overflow:hidden}
.lbl{position:absolute;left:0;top:0;pointer-events:auto;background:var(--color-surface);color:var(--color-text);border:var(--border-width) solid var(--color-border);border-radius:var(--radius-sm);padding:var(--space-1) var(--space-2);font-size:var(--text-xs);line-height:var(--lh-xs);font-weight:var(--weight-medium);white-space:nowrap;cursor:pointer}
.lbl b{font-weight:var(--weight-bold)}
.lbl.me{background:var(--color-accent);color:var(--color-surface);border-color:var(--color-accent);pointer-events:none}
.lbl[hidden]{display:none}

.hud{position:fixed;top:calc(var(--space-4) + env(safe-area-inset-top, 0px));left:calc(var(--space-4) + env(safe-area-inset-left, 0px));width:var(--panel-w);display:flex;flex-direction:column;gap:var(--space-3);pointer-events:none}
.card{pointer-events:auto;background:var(--color-surface);border:var(--border-width) solid var(--color-border);border-radius:var(--radius-md);padding:var(--space-4);box-shadow:var(--shadow)}
.eyebrow{font-size:var(--text-xs);line-height:var(--lh-xs);font-weight:var(--weight-medium);color:var(--color-text-muted)}
.brand h1{margin:var(--space-1) 0 0;font-size:var(--text-lg);line-height:var(--lh-lg);font-weight:var(--weight-bold)}
.brand p{margin:var(--space-1) 0 0;font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}
.legend{margin:var(--space-3) 0 0;padding:var(--space-3) 0 0;border-top:var(--border-width) solid var(--color-border);list-style:none;display:grid;gap:var(--space-1);font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}
.legend b{color:var(--color-text);font-weight:var(--weight-medium)}
.line-row{display:flex;align-items:center;gap:var(--space-3)}
.line-row label{font-weight:var(--weight-medium);white-space:nowrap}
.line-row input{flex:1;min-width:0;accent-color:var(--color-accent)}
.line-row output{font-size:var(--text-lg);line-height:var(--lh-lg);font-weight:var(--weight-bold);color:var(--color-accent)}
.delta{margin:var(--space-2) 0 0;font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text)}
.delta b{color:var(--color-accent)}
.actions{display:flex;flex-wrap:wrap;gap:var(--space-2);pointer-events:auto}
.btn{background:var(--color-surface);color:var(--color-text);border:var(--border-width) solid var(--color-border);border-radius:var(--radius-sm);padding:var(--space-3) var(--space-4);font-size:var(--text-sm);line-height:var(--lh-sm);font-weight:var(--weight-medium);cursor:pointer;white-space:nowrap}
.btn.primary{background:var(--color-accent);border-color:var(--color-accent);color:var(--color-surface)}
.btn.done{background:var(--grade-s);border-color:var(--grade-s);color:var(--color-surface)}
.status{pointer-events:none;align-self:flex-start;background:var(--color-surface);border:var(--border-width) solid var(--color-border);border-radius:var(--radius-sm);padding:var(--space-1) var(--space-2);font-size:var(--text-xs);line-height:var(--lh-xs)}
.status[hidden]{display:none}

.panel{position:fixed;top:calc(var(--space-4) + env(safe-area-inset-top, 0px));right:calc(var(--space-4) + env(safe-area-inset-right, 0px));bottom:calc(var(--space-4) + env(safe-area-inset-bottom, 0px));width:var(--panel-w);overflow-y:auto;overscroll-behavior:contain;display:flex;flex-direction:column;gap:var(--space-4)}
.panel[hidden]{display:none}
.p-head{display:flex;justify-content:space-between;align-items:flex-start;gap:var(--space-3)}
.p-head h2{margin:var(--space-1) 0 0;font-size:var(--text-lg);line-height:var(--lh-lg);font-weight:var(--weight-bold)}
.close{flex:none;background:var(--color-surface);border:var(--border-width) solid var(--color-border);border-radius:var(--radius-sm);padding:var(--space-2) var(--space-3);font-size:var(--text-xs);line-height:var(--lh-xs);cursor:pointer}
.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--space-4) var(--space-3)}
.kpi{min-width:0;border-top:var(--border-width) solid var(--color-border);padding-top:var(--space-2)}
.kpi .k-label{font-size:var(--text-xs);line-height:var(--lh-xs);font-weight:var(--weight-medium);color:var(--color-text-muted)}
.kpi .k-num{display:block;font-size:var(--text-lg);line-height:var(--lh-lg);font-weight:var(--weight-bold);color:var(--color-text)}
.kpi .k-basis{font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}
.insight{margin:0;padding:var(--space-3);background:var(--color-bg);border-radius:var(--radius-sm);font-size:var(--text-sm);line-height:var(--lh-sm)}
.insight b{font-weight:var(--weight-bold)}
.chips{display:flex;flex-wrap:wrap;gap:var(--space-2)}
.badge{display:inline-block;padding:var(--space-1) var(--space-2);border-radius:var(--radius-sm);font-size:var(--text-xs);line-height:var(--lh-xs);font-weight:var(--weight-bold)}
.g-S{background:var(--grade-s);color:var(--color-surface)}
.g-A{background:var(--grade-a);color:var(--color-text)}
.g-B{background:var(--grade-b);color:var(--color-text)}
.g-C{background:var(--grade-c);color:var(--color-surface)}
.rows{display:grid;grid-template-columns:auto minmax(0,1fr);gap:var(--space-2) var(--space-4);margin:0}
.rows dt{font-size:var(--text-xs);line-height:var(--lh-sm);color:var(--color-text-muted)}
.rows dd{margin:0;text-align:right;font-weight:var(--weight-medium)}
.signals{margin:0;padding:0 0 0 var(--space-4);display:grid;gap:var(--space-1)}
.fixed-line{margin:0;font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}
.list{list-style:none;margin:0;padding:0;display:grid;gap:var(--space-2)}
.list button{width:100%;display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:var(--space-3);text-align:left;background:var(--color-surface);border:var(--border-width) solid var(--color-border);border-radius:var(--radius-sm);padding:var(--space-2) var(--space-3);cursor:pointer}
.list .nm{font-weight:var(--weight-medium);min-width:0}
.list .sub{display:block;font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}
.list .r{text-align:right}
.foot{margin-top:auto;padding-top:var(--space-3);border-top:var(--border-width) solid var(--color-border);font-size:var(--text-xs);line-height:var(--lh-xs);color:var(--color-text-muted)}
.warn{color:var(--grade-c);font-weight:var(--weight-bold)}
.nogl{position:fixed;left:calc(var(--space-4) + env(safe-area-inset-left, 0px));bottom:calc(var(--space-4) + env(safe-area-inset-bottom, 0px));max-width:var(--panel-w)}
.nogl[hidden]{display:none}

@media (max-width: __BP_PHONE__){
  .hud{right:calc(var(--space-4) + env(safe-area-inset-right, 0px));width:auto;gap:var(--space-2)}
  .card{padding:var(--space-3)}
  .brand h1{font-size:var(--text-md);line-height:var(--lh-md)}
  .legend{display:none}
  .btn{padding:var(--space-3)}
  .panel{top:auto;left:0;right:0;bottom:0;width:auto;max-height:46%;border-radius:var(--radius-md) var(--radius-md) 0 0;border-bottom:none;padding:var(--space-4) max(var(--space-4), env(safe-area-inset-right, 0px)) calc(var(--space-4) + env(safe-area-inset-bottom, 0px)) max(var(--space-4), env(safe-area-inset-left, 0px))}
}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto}}
"""

BODY = """
<div id="stage" aria-hidden="true"></div>
<div id="labels"></div>
<div class="hud">
  <section class="card brand" aria-labelledby="t-title">
    <div class="eyebrow">채권관리팀 · 탐험 프로토타입</div>
    <h1 id="t-title">바이어 월드</h1>
    <p>기준일 <span class="num">__ASOF__</span> · (가상) 한빛정밀(주) 바이어 __N__곳 · 합성 데이터</p>
    <ul class="legend">
      <li><b>섬</b> = 지역 · <b>건물</b> = 바이어 · 건물 높이는 채권의 제곱근에 비례</li>
      <li><b>지붕 색</b> = 지금 위험 선 기준 등급(S · A · B · C) · <b>깃발</b> = 연체 있음</li>
      <li><b>먹구름과 비</b> = 지금 C등급 · <b>섬 날씨</b> = 지역 채권 중 C등급 비중(10% 미만 맑음 · 25% 미만 구름 조금 · 50% 미만 흐림 · 그 이상 비)</li>
    </ul>
    <p id="selfcheck" class="warn" hidden></p>
  </section>
  <section class="card" aria-label="위험 선">
    <div class="line-row">
      <label for="line">위험 선</label>
      <input type="range" id="line" min="__MIN__" max="__MAX__" step="1" value="__BASE__" autocomplete="off">
      <output for="line" id="line-val" class="num">__BASE__%</output>
    </div>
    <p class="delta">C등급 <b class="num" id="c-now"></b> · 처음 __BASE__%보다 <b class="num" id="delta"></b></p>
  </section>
  <div class="actions">
    <button type="button" class="btn primary" id="btn-quest"></button>
    <button type="button" class="btn" id="btn-hub">본사로</button>
    <button type="button" class="btn" id="btn-view">전체 보기</button>
  </div>
  <div class="status" id="status" role="status" hidden></div>
</div>
<aside class="panel card" id="panel" aria-live="polite"></aside>
<section class="card nogl" id="nogl" hidden>이 기기에서는 3D 화면을 그릴 수 없습니다. 아래 단추와 오른쪽 패널로 같은 숫자를 볼 수 있습니다.</section>
<noscript><p class="card nogl">이 페이지는 JavaScript가 켜져 있어야 보입니다. 같은 숫자는 buyer_board.html(v1 보드)에서 볼 수 있습니다.</p></noscript>
"""

JS = r"""
import * as THREE from "__THREE__";

const $ = (id) => document.getElementById(id);
const D = JSON.parse($("world-data").textContent);
const T = D.tokens, B = D.buyers, R = D.regions, GR = ["S", "A", "B", "C"];
const WEATHER = ["맑음", "구름 조금", "흐림", "비"];
const REDUCE = matchMedia("(prefers-reduced-motion: reduce)").matches;
const isPhone = () => innerWidth <= parseInt(D.bpPhone, 10);
const idx = {}; B.forEach((b, i) => { idx[b.id] = i; });
const regIdx = {}; R.forEach((r, i) => { regIdx[r.name] = i; });

// <calc> — 등급 · 집계 규칙(v1과 같다). node로 파이썬 계산과 대조한다.
function gradeOf(p, line) {
  if (p >= line) return "C";
  if (p >= line / 2) return "B";
  if (p >= line / 4) return "A";
  return "S";
}
function weatherStep(share) {
  let s = 0;
  for (const c of [0.10, 0.25, 0.50]) if (share >= c) s += 1;
  return s;
}
function stats(buyers, regions, pct) {
  const line = pct / 100, g = [], count = { S: 0, A: 0, B: 0, C: 0 }, ar = { S: 0, A: 0, B: 0, C: 0 }, reg = {};
  regions.forEach((r) => { reg[r.name] = { cn: 0, car: 0, counts: { S: 0, A: 0, B: 0, C: 0 } }; });
  buyers.forEach((b) => {
    const k = gradeOf(b.pd, line);
    g.push(k); count[k] += 1; ar[k] += b.ar;
    const q = reg[b.region]; q.counts[k] += 1;
    if (k === "C") { q.cn += 1; q.car += b.ar; }
  });
  regions.forEach((r) => { reg[r.name].step = weatherStep(r.total ? reg[r.name].car / r.total : 0); });
  return { line, g, count, ar, reg };
}
// </calc>

function money(v) { return "$" + Math.round(v).toLocaleString("en-US"); }
function pct1(part, whole) { return (whole ? part / whole * 100 : 0).toFixed(1) + "%"; }
function signed(n, unit) { return (n < 0 ? "-" : "+") + (unit === "$" ? money(Math.abs(n)) : Math.abs(n) + unit); }
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function badge(g) { const s = el("span", "badge g-" + g, g); s.setAttribute("aria-label", g + "등급"); return s; }
function hhmm() { const d = new Date(); return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0"); }

const TOTAL = B.reduce((s, b) => s + b.ar, 0);
const OVERDUE = B.reduce((s, b) => s + b.od, 0), OVERDUE_N = B.filter((b) => b.od > 0).length;
const BASE = stats(B, R, D.base);
const state = { pct: D.base, S: BASE, checked: new Map(), panel: { type: "hub" }, view: "overview", moving: null };

// 자체 검증: 페이지 JS의 처음 선 계산 = 파이썬 계산
(function selfCheck() {
  const c = D.check, bad = [];
  GR.forEach((g) => { if (c.count[g] !== BASE.count[g] || c.ar[g] !== BASE.ar[g]) bad.push(g); });
  R.forEach((r) => { if ((c.region_c[r.name] || 0) !== BASE.reg[r.name].car) bad.push(r.name); });
  if (bad.length) { const p = $("selfcheck"); p.textContent = "숫자 검증 실패(확인 필요): " + bad.join(", "); p.hidden = false; }
})();

// ---------- 3D 장면 ----------
const col = (k) => new THREE.Color(T[k]);
const GRADE_COL = { S: col("grade-s"), A: col("grade-a"), B: col("grade-b"), C: col("grade-c") };
const LAND = [col("world-land-1"), col("world-land-2"), col("world-land-3"), col("world-land-4")];
let renderer = null;
try { renderer = new THREE.WebGLRenderer({ antialias: true }); } catch (e) { renderer = null; }

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.5, 600);
const stage = $("stage");
const pickables = [];
const tmp = new THREE.Object3D(), v3 = new THREE.Vector3();
const std = (k, extra) => new THREE.MeshStandardMaterial(Object.assign({ color: col(k), roughness: 1, metalness: 0, flatShading: true }, extra || {}));

let walls, roofs, clouds, rain, stamps, puffs, islandMats = [], character, charHead;
const RAIN_PER = 6, PUFFS_PER = 5;
let rainList = [];

if (renderer) {
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  stage.appendChild(renderer.domElement);
  scene.background = col("world-sky");
  scene.fog = new THREE.Fog(col("world-sky"), D.extent * 1.6, D.extent * 3.6);
  scene.add(new THREE.HemisphereLight(col("world-sky"), col("world-sea"), 2.2));
  const sun = new THREE.DirectionalLight(col("color-surface"), 1.8); sun.position.set(30, 60, 25); scene.add(sun);

  const sea = new THREE.Mesh(new THREE.PlaneGeometry(D.extent * 8, D.extent * 8), std("world-sea"));
  sea.rotation.x = -Math.PI / 2; sea.position.y = -0.7; sea.userData = { kind: "sea" }; scene.add(sea); pickables.push(sea);

  const hub = new THREE.Mesh(new THREE.CylinderGeometry(D.hub.r, D.hub.r + 0.5, 1.2, 32), std("world-hub"));
  hub.position.set(0, -0.6, 0); hub.userData = { kind: "hub" }; scene.add(hub); pickables.push(hub);
  const hq = new THREE.Mesh(new THREE.BoxGeometry(2.2, 3.2, 2.2), std("color-accent"));
  hq.position.set(0, 1.6, -1.4); hq.userData = { kind: "hub" }; scene.add(hq); pickables.push(hq);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.4, 6), std("color-text-muted"));
  pole.position.set(1.6, 1.2, -1.4); scene.add(pole);

  R.forEach((r, i) => {
    const m = new THREE.MeshStandardMaterial({ color: LAND[0].clone(), roughness: 1, metalness: 0, flatShading: true });
    islandMats.push(m);
    const land = new THREE.Mesh(new THREE.CylinderGeometry(r.r, r.r + 0.8, 1.2, 40), m);
    land.position.set(r.x, -0.6, r.z); land.userData = { kind: "island", i }; scene.add(land); pickables.push(land);
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.16, 1.6, 0.16), std("color-text-muted"));
    post.position.set(r.sx, 0.8, r.sz); scene.add(post);
    const board = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.8, 0.12), std("color-surface"));
    board.position.set(r.sx, 1.5, r.sz); board.lookAt(0, 1.5, 0); board.userData = { kind: "island", i }; scene.add(board); pickables.push(board);
  });

  const n = B.length;
  walls = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), std("world-wall"), n);
  roofs = new THREE.InstancedMesh(new THREE.BoxGeometry(1.5, 0.36, 1.5), new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0, flatShading: true }), n);
  clouds = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 0), std("world-storm"), n);
  stamps = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.42, 0.42, 0.12, 16), std("color-accent"), n);
  rain = new THREE.InstancedMesh(new THREE.BoxGeometry(0.05, 0.7, 0.05), std("world-rain"), n * RAIN_PER);
  B.forEach((b, i) => {
    tmp.position.set(b.x, b.h / 2, b.z); tmp.scale.set(1.2, b.h, 1.2); tmp.rotation.set(0, 0, 0); tmp.updateMatrix(); walls.setMatrixAt(i, tmp.matrix);
    tmp.position.set(b.x, b.h + 0.18, b.z); tmp.scale.set(1, 1, 1); tmp.updateMatrix(); roofs.setMatrixAt(i, tmp.matrix);
    roofs.setColorAt(i, GRADE_COL.S);
  });
  walls.userData = { kind: "buyer" }; roofs.userData = { kind: "buyer" };
  [walls, roofs, clouds, stamps, rain].forEach((m) => scene.add(m));
  pickables.push(walls, roofs);

  const od = B.map((b, i) => i).filter((i) => B[i].od > 0);
  const flags = new THREE.InstancedMesh(new THREE.BoxGeometry(0.5, 0.32, 0.04), std("color-text-muted"), Math.max(od.length, 1));
  const poles = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.035, 0.035, 1.1, 5), std("color-text-muted"), Math.max(od.length, 1));
  od.forEach((i, k) => {
    const b = B[i];
    tmp.rotation.set(0, 0, 0); tmp.scale.set(1, 1, 1);
    tmp.position.set(b.x + 0.45, b.h + 0.36 + 0.55, b.z + 0.45); tmp.updateMatrix(); poles.setMatrixAt(k, tmp.matrix);
    tmp.position.set(b.x + 0.7, b.h + 0.36 + 0.9, b.z + 0.45); tmp.updateMatrix(); flags.setMatrixAt(k, tmp.matrix);
  });
  flags.count = poles.count = od.length; scene.add(flags, poles);

  puffs = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0, flatShading: true }), R.length * PUFFS_PER);
  for (let i = 0; i < R.length * PUFFS_PER; i++) puffs.setColorAt(i, col("world-cloud"));
  scene.add(puffs);

  character = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.42, 0.8, 4, 12), std("color-accent"));
  body.position.y = 0.85;
  charHead = new THREE.Mesh(new THREE.SphereGeometry(0.36, 16, 12), std("world-skin"));
  charHead.position.y = 1.9;
  const tie = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.42, 0.06), std("grade-c"));
  tie.position.set(0, 1.2, 0.42);
  character.add(body, charHead, tie);
  character.position.set(0, 0, D.hub.r - 1.6);
  scene.add(character);
} else {
  $("nogl").hidden = false;
}

function applyGrades() {
  const S = state.S;
  if (renderer) {
    rainList = [];
    B.forEach((b, i) => {
      const g = S.g[i];
      roofs.setColorAt(i, GRADE_COL[g]);
      const on = g === "C";
      tmp.rotation.set(0, 0, 0);
      tmp.position.set(b.x, b.h + 2.2, b.z); tmp.scale.setScalar(on ? 1 : 0); tmp.scale.y = on ? 0.55 : 0; tmp.updateMatrix(); clouds.setMatrixAt(i, tmp.matrix);
      if (on) rainList.push(i);
      const chk = state.checked.has(b.id);
      tmp.position.set(b.x, b.h + 0.44, b.z); tmp.scale.setScalar(chk ? 1 : 0); tmp.updateMatrix(); stamps.setMatrixAt(i, tmp.matrix);
    });
    roofs.instanceColor.needsUpdate = true; clouds.instanceMatrix.needsUpdate = true; stamps.instanceMatrix.needsUpdate = true;
    rain.count = rainList.length * RAIN_PER;
    R.forEach((r, i) => {
      const st = S.reg[r.name].step;
      islandMats[i].color.copy(LAND[st]);
      const shown = [0, 1, 3, 5][st];
      for (let k = 0; k < PUFFS_PER; k++) {
        const a = (k / PUFFS_PER) * Math.PI * 2 + i, rr = r.r * 0.55;
        tmp.rotation.set(0, 0, 0);
        tmp.position.set(r.x + Math.cos(a) * rr, 8 + (k % 2) * 0.6, r.z + Math.sin(a) * rr);
        tmp.scale.set(k < shown ? 1.7 : 0, k < shown ? 0.7 : 0, k < shown ? 1.3 : 0); tmp.updateMatrix();
        puffs.setMatrixAt(i * PUFFS_PER + k, tmp.matrix);
        puffs.setColorAt(i * PUFFS_PER + k, st === 3 ? col("world-storm") : col("world-cloud"));
      }
    });
    puffs.instanceMatrix.needsUpdate = true; puffs.instanceColor.needsUpdate = true;
  }
  updateLabels(true);
}

// ---------- 이름표(섬 · 본사 · 대표님) ----------
const labelsEl = $("labels"), labelItems = [];
function addLabel(text, x, y, z, onClick, cls) {
  const b = el(onClick ? "button" : "div", "lbl" + (cls ? " " + cls : ""), text || null);
  if (onClick) { b.type = "button"; b.addEventListener("click", onClick); }
  labelsEl.appendChild(b);
  const item = { el: b, pos: new THREE.Vector3(x, y, z), text };
  labelItems.push(item);
  return item;
}
const hubLabel = addLabel("", 0, 4.4, -1.4, () => goHub());
const regionLabels = R.map((r, i) => addLabel("", r.sx, 3.0, r.sz, () => goRegion(i)));
const meLabel = addLabel("대표님", 0, 0, 0, null, "me");
function updateLabels(textToo) {
  if (textToo) {
    hubLabel.el.replaceChildren(el("b", null, "본사"), document.createTextNode(" · 이번 주 숫자"));
    regionLabels.forEach((it, i) => {
      const q = state.S.reg[R[i].name];
      it.el.replaceChildren(el("b", null, R[i].name), document.createTextNode(" · " + WEATHER[q.step]));
      it.el.setAttribute("aria-label", R[i].name + "으로 이동, 날씨 " + WEATHER[q.step]);
    });
  }
  if (!renderer) { labelItems.forEach((it) => { it.el.hidden = true; }); return; }
  const w = stage.clientWidth, h = stage.clientHeight;
  if (character) meLabel.pos.set(character.position.x, character.position.y + 2.9, character.position.z);
  labelItems.forEach((it) => {
    v3.copy(it.pos).project(camera);
    const off = v3.z > 1 || v3.x < -1.1 || v3.x > 1.1 || v3.y < -1.1 || v3.y > 1.1;
    it.el.hidden = off;
    if (!off) it.el.style.transform = "translate(" + ((v3.x + 1) / 2 * w) + "px," + ((1 - v3.y) / 2 * h) + "px) translate(-50%,-100%)";
  });
}

// ---------- 패널 ----------
const panel = $("panel");
function head(eyebrow, title, extra) {
  const h = el("div", "p-head"), left = el("div");
  left.append(el("div", "eyebrow", eyebrow), el("h2", null, title));
  if (extra) left.append(extra);
  const x = el("button", "close", "닫기"); x.type = "button"; x.addEventListener("click", () => closePanel());
  h.append(left, x);
  return h;
}
function kpi(label, num, basis) {
  const k = el("div", "kpi");
  k.append(el("div", "k-label", label), el("span", "k-num num", num), el("div", "k-basis", basis));
  return k;
}
function foot() { return el("p", "foot", "(가상) 합성 데이터 · 기준일 " + D.asof + " · 위험 점수는 판단을 돕는 값이고 결정은 사람이 합니다"); }
function topRegion() {
  let best = null;
  R.forEach((r) => { const q = state.S.reg[r.name]; if (!best || q.car > best.car) best = { name: r.name, car: q.car }; });
  return best;
}
function buyerButton(i, right) {
  const b = B[i], li = el("li"), btn = el("button");
  btn.type = "button";
  const mid = el("span", "nm", b.name); mid.append(el("span", "sub", b.country + " · 위험 점수 " + pct1(b.pd, 1)));
  btn.append(badge(state.S.g[i]), mid, el("span", "r num", right != null ? right : money(b.ar)));
  btn.addEventListener("click", () => goBuyer(i));
  li.append(btn);
  return li;
}

function renderHub() {
  const S = state.S, tr = topRegion();
  const chips = el("div", "chips");
  GR.forEach((g) => { const c = el("span", "chips"); c.append(badge(g), el("span", "num", " " + S.count[g] + "곳")); chips.append(c); });
  const kp = el("div", "kpis");
  kp.append(
    kpi("위험 바이어(C)", S.count.C + "곳", B.length + "곳 중 · 위험 선 " + state.pct + "%"),
    kpi("C등급 채권", money(S.ar.C), "전체 채권의 " + pct1(S.ar.C, TOTAL)),
    kpi("전체 채권", money(TOTAL), B.length + "곳 · 미결 채권 합"),
    kpi("연체 금액", money(OVERDUE), "연체가 있는 곳 " + OVERDUE_N + "곳"),
  );
  const ins = el("p", "insight");
  ins.append(document.createTextNode("지금 C등급 채권이 가장 많은 섬은 "), el("b", null, tr.name),
    document.createTextNode("(" + money(tr.car) + ", C등급 채권의 " + pct1(tr.car, S.ar.C) + ")입니다."));
  const q = el("button", "btn primary", "이번 주 전화할 10곳 보기"); q.type = "button"; q.addEventListener("click", () => openPanel({ type: "quest" }));
  panel.replaceChildren(head("본사 광장 · 체크포인트", "이번 주 숫자"), kp, chips, ins, q, foot());
}
function renderRegion(i) {
  const r = R[i], q = state.S.reg[r.name];
  const kp = el("div", "kpis");
  kp.append(
    kpi("바이어", r.n + "곳", "C등급 " + q.cn + "곳"),
    kpi("채권", money(r.total), "전체의 " + pct1(r.total, TOTAL)),
    kpi("C등급 채권", money(q.car), "이 섬 채권의 " + pct1(q.car, r.total)),
    kpi("날씨", WEATHER[q.step], "C등급 비중 기준"),
  );
  const chips = el("div", "chips");
  GR.forEach((g) => { const c = el("span", "chips"); c.append(badge(g), el("span", "num", " " + q.counts[g] + "곳")); chips.append(c); });
  const ins = el("p", "insight");
  ins.append(document.createTextNode("전체 C등급 채권 " + money(state.S.ar.C) + " 가운데 "), el("b", null, pct1(q.car, state.S.ar.C)),
    document.createTextNode("가 이 섬에 있습니다."));
  const list = el("ul", "list");
  B.map((b, k) => k).filter((k) => B[k].region === r.name && state.S.g[k] === "C")
    .sort((a, b) => B[b].pd - B[a].pd || (B[a].id < B[b].id ? -1 : 1))
    .forEach((k) => list.append(buyerButton(k)));
  const parts = [head("섬 · 체크포인트", r.name), kp, chips, ins];
  if (list.childElementCount) parts.push(el("div", "eyebrow", "이 섬의 C등급 바이어(위험 점수 순)"), list);
  else parts.push(el("p", "muted", "지금 선에서는 이 섬에 C등급 바이어가 없습니다."));
  parts.push(foot());
  panel.replaceChildren(...parts);
}
function renderBuyer(i) {
  const b = B[i], g = state.S.g[i];
  const sub = el("div", "chips"); sub.append(badge(g), el("span", "muted", b.country + " · " + b.region));
  const rows = el("dl", "rows");
  const add = (k, v) => { rows.append(el("dt", null, k), el("dd", "num", v)); };
  add("업종", b.industry); rows.lastChild.className = "";
  add("결제방식", b.pay + " · " + b.terms + "일"); rows.lastChild.className = "";
  add("채권", money(b.ar)); add("연체", money(b.od)); add("위험 점수", pct1(b.pd, 1));
  const sig = el("ul", "signals");
  [b.s1, b.s2, b.s3].filter((s) => s).forEach((s) => sig.append(el("li", null, s)));
  const done = state.checked.get(b.id);
  const btn = el("button", "btn" + (done ? " done" : ""), done ? "확인 완료 · " + done : "확인 필요");
  btn.type = "button";
  btn.addEventListener("click", () => {
    if (state.checked.has(b.id)) state.checked.delete(b.id); else state.checked.set(b.id, hhmm());
    applyGrades(); renderQuestButton(); renderBuyer(i);
  });
  panel.replaceChildren(head("바이어 · " + b.id, b.name, sub), rows, el("div", "eyebrow", "위험 신호"), sig,
    el("p", "fixed-line", "이 신호들은 확인해 볼 이유이지, 연체의 원인이라는 뜻은 아닙니다."), btn, foot());
}
function renderQuest() {
  const list = el("ul", "list");
  D.top10.forEach((id) => { const i = idx[id]; list.append(buyerButton(i, state.checked.has(id) ? "확인 완료" : "확인 필요")); });
  const n = D.top10.filter((id) => state.checked.has(id)).length;
  panel.replaceChildren(head("퀘스트", "이번 주 전화할 10곳"),
    el("p", "muted", "위험 점수가 높은 순입니다. 누르면 대표님이 그 건물로 걸어갑니다. 확인 완료 " + n + "/10"),
    list, foot());
}
function renderPanel() {
  const p = state.panel;
  if (!p) return;
  if (p.type === "hub") renderHub();
  else if (p.type === "region") renderRegion(p.i);
  else if (p.type === "buyer") renderBuyer(p.i);
  else if (p.type === "quest") renderQuest();
}
function openPanel(p) { state.panel = p; panel.hidden = false; renderPanel(); panel.scrollTop = 0; fitView(); }
function closePanel() { state.panel = null; panel.hidden = true; fitView(); }
function renderQuestButton() {
  const n = D.top10.filter((id) => state.checked.has(id)).length;
  $("btn-quest").textContent = "전화할 10곳 · 확인 " + n + "/10";
}

// ---------- 이동 ----------
const statusEl = $("status");
function walkTo(x, z, label, arrive) {
  state.view = "follow"; $("btn-view").textContent = "전체 보기";
  if (!renderer || REDUCE) { if (character) character.position.set(x, 0, z); arrive && arrive(); return; }
  state.moving = { x, z, arrive };
  statusEl.textContent = label + "(으)로 이동 중"; statusEl.hidden = false;
}
function approach(x, z, gap) {
  const cx = character ? character.position.x : 0, cz = character ? character.position.z : 0;
  const dx = cx - x, dz = cz - z, d = Math.hypot(dx, dz) || 1;
  return [x + dx / d * gap, z + dz / d * gap];
}
function goBuyer(i) { const b = B[i]; const [x, z] = approach(b.x, b.z, 1.5); walkTo(x, z, b.name, () => openPanel({ type: "buyer", i })); }
function goRegion(i) { const r = R[i]; const [x, z] = approach(r.sx, r.sz, 1.2); walkTo(x, z, r.name, () => openPanel({ type: "region", i })); }
function goHub() { walkTo(0, D.hub.r - 1.6, "본사", () => openPanel({ type: "hub" })); }

// ---------- 카메라 ----------
const look = new THREE.Vector3(0, 0, 0), camGoal = new THREE.Vector3(), lookGoal = new THREE.Vector3();
function fitView() {
  if (!renderer) return;
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  const open = !panel.hidden;
  if (open && isPhone()) { const sh = panel.offsetHeight; camera.setViewOffset(w, h + sh, 0, sh / 2, w, h); }
  else if (open) { const pw = panel.offsetWidth + 16; camera.setViewOffset(w + pw, h, pw, 0, w, h); }
  else camera.clearViewOffset();
  camera.updateProjectionMatrix();
}
function cameraGoals() {
  if (state.view === "overview" || !character) {
    const e = D.extent * (isPhone() ? 2.15 : 1.25);
    camGoal.set(0, e * 1.05, e * 0.9); lookGoal.set(0, 0, 2);
  } else {
    const p = character.position, k = isPhone() ? 1.35 : 1;
    camGoal.set(p.x, 15 * k, p.z + 17 * k); lookGoal.set(p.x, 0.8, p.z);
  }
}

// ---------- 입력 ----------
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
let down = null;
if (renderer) {
  renderer.domElement.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY }; });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 8) { down = null; return; }
    down = null;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set((e.clientX - r.left) / r.width * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickables, false)[0];
    if (!hit) return;
    const k = hit.object.userData.kind;
    if (k === "buyer" && hit.instanceId != null) goBuyer(hit.instanceId);
    else if (k === "island") goRegion(hit.object.userData.i);
    else if (k === "hub") goHub();
    else if (k === "sea") {
      const lim = D.extent * 1.1, x = Math.max(-lim, Math.min(lim, hit.point.x)), z = Math.max(-lim, Math.min(lim, hit.point.z));
      walkTo(x, z, "바다 위 지점", null);
    }
  });
}
$("btn-hub").addEventListener("click", () => goHub());
$("btn-quest").addEventListener("click", () => openPanel({ type: "quest" }));
$("btn-view").addEventListener("click", () => {
  state.view = state.view === "overview" ? "follow" : "overview";
  $("btn-view").textContent = state.view === "overview" ? "대표님 따라가기" : "전체 보기";
});
const slider = $("line");
function onLine() {
  state.pct = parseInt(slider.value, 10);
  state.S = stats(B, R, state.pct);
  $("line-val").textContent = state.pct + "%";
  $("c-now").textContent = state.S.count.C + "곳 · " + money(state.S.ar.C);
  $("delta").textContent = signed(state.S.count.C - BASE.count.C, "곳") + " · " + signed(state.S.ar.C - BASE.ar.C, "$");
  applyGrades(); renderPanel();
}
slider.addEventListener("input", onLine);
addEventListener("resize", () => { fitView(); });

// ---------- 시작 ----------
onLine(); renderQuestButton();
if (isPhone() && renderer) closePanel(); else openPanel({ type: "hub" });  // 휴대폰은 월드가 보이게 패널을 닫고 시작
$("btn-view").textContent = "대표님 따라가기";
if (renderer) {
  cameraGoals(); camera.position.copy(camGoal); look.copy(lookGoal); camera.lookAt(look);
  if (!REDUCE) setTimeout(() => { if (!state.moving && state.view === "overview") { state.view = "follow"; $("btn-view").textContent = "전체 보기"; } }, 1800);
  const clock = new THREE.Clock();
  const loop = () => {
    const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
    if (state.moving && character) {
      const m = state.moving, p = character.position, dx = m.x - p.x, dz = m.z - p.z, d = Math.hypot(dx, dz), step = 14 * dt;
      character.rotation.y = Math.atan2(dx, dz);
      if (d <= step) { p.set(m.x, 0, m.z); state.moving = null; statusEl.hidden = true; m.arrive && m.arrive(); }
      else { p.x += dx / d * step; p.z += dz / d * step; p.y = Math.abs(Math.sin(t * 12)) * 0.28; }
    }
    if (!REDUCE) {
      for (let k = 0; k < rainList.length * RAIN_PER; k++) {
        const b = B[rainList[Math.floor(k / RAIN_PER)]], j = k % RAIN_PER;
        const ph = ((t * 1.6 + j * 0.37 + (k % 7) * 0.11) % 1);
        tmp.rotation.set(0, 0, 0); tmp.scale.set(1, 1, 1);
        tmp.position.set(b.x + Math.cos(j * 2.1) * 0.7, b.h + 1.8 - ph * (b.h + 1.6), b.z + Math.sin(j * 2.1) * 0.7);
        tmp.updateMatrix(); rain.setMatrixAt(k, tmp.matrix);
      }
      rain.instanceMatrix.needsUpdate = true;
    } else if (rain) {
      for (let k = 0; k < rainList.length * RAIN_PER; k++) {
        const b = B[rainList[Math.floor(k / RAIN_PER)]], j = k % RAIN_PER;
        tmp.rotation.set(0, 0, 0); tmp.scale.set(1, 1, 1);
        tmp.position.set(b.x + Math.cos(j * 2.1) * 0.7, b.h + 1.2 - (j / RAIN_PER) * b.h, b.z + Math.sin(j * 2.1) * 0.7);
        tmp.updateMatrix(); rain.setMatrixAt(k, tmp.matrix);
      }
      rain.instanceMatrix.needsUpdate = true;
    }
    cameraGoals();
    const a = REDUCE ? 1 : 1 - Math.exp(-dt * 2.6);
    camera.position.lerp(camGoal, a); look.lerp(lookGoal, a); camera.lookAt(look);
    renderer.render(scene, camera);
    updateLabels(false);
    requestAnimationFrame(loop);
  };
  fitView();
  requestAnimationFrame(loop);
}
"""


def build(df: pd.DataFrame) -> tuple[str, str, dict]:
    unknown = sorted(set(df["country_code"]) - set(bp.COUNTRY_KO))
    if unknown:
        sys.exit(f"COUNTRY_KO에 없는 country_code: {unknown}")
    df = df.copy()
    df["country_ko"] = df["country_code"].map(bp.COUNTRY_KO)

    pos, islands = layout(df)
    max_ar = int(df["open_ar_usd"].max())
    s = bp.summarize(df, bp.BASE_LINE_PCT)

    buyers = []
    for r in df.sort_values("buyer_id").itertuples():
        x, z = pos[r.buyer_id]
        buyers.append({
            "id": r.buyer_id, "name": r.buyer_name, "country": r.country_ko, "region": r.region,
            "industry": r.industry, "pay": r.payment_method, "terms": int(r.terms_days),
            "ar": int(r.open_ar_usd), "od": int(r.overdue_usd), "pd": float(r.pd_30d),
            "s1": bp.clean(r.signal_1), "s2": bp.clean(r.signal_2), "s3": bp.clean(r.signal_3),
            "x": x, "z": z, "h": round(0.6 + 5.4 * math.sqrt(r.open_ar_usd / max_ar), 3),
        })

    regions = []
    for name, v in islands.items():
        sub = df[df["region"] == name]
        regions.append({
            "name": name, "x": v["center"][0], "z": v["center"][1], "r": round(v["r"], 3),
            "sx": v["sign"][0], "sz": v["sign"][1], "n": int(len(sub)), "total": int(sub["open_ar_usd"].sum()),
        })
    extent = round(max(math.hypot(r["x"], r["z"]) + r["r"] for r in regions), 3)
    top10 = list(df.sort_values(["pd_30d", "buyer_id"], ascending=[False, True]).head(10)["buyer_id"])

    data = {
        "tokens": TOKENS, "bpPhone": bp.BP_PHONE, "asof": bp.AS_OF, "base": bp.BASE_LINE_PCT,
        "buyers": buyers, "regions": regions, "hub": {"r": HUB_R}, "extent": extent, "top10": top10,
        "check": {"count": s["count"], "ar": s["ar"], "region_c": s["region_c"]},
    }
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    root_css = ":root{" + "".join(f"--{k}:{v};" for k, v in TOKENS.items()) + "}"
    css = root_css + CSS.replace("__BP_PHONE__", bp.BP_PHONE)
    body = (BODY.replace("__ASOF__", bp.AS_OF).replace("__N__", str(len(df)))
            .replace("__MIN__", str(bp.LINE_MIN)).replace("__MAX__", str(bp.LINE_MAX))
            .replace("__BASE__", str(bp.BASE_LINE_PCT)))
    js = JS.replace("__THREE__", THREE_URL)

    head_inner = f"{HEAD_EXTRA}\n<style>{css}</style>"
    body_inner = (f"{body}\n<script type=\"application/json\" id=\"world-data\">{data_json}</script>\n"
                  f"<script type=\"module\">{js}</script>\n")
    full = (f"<!doctype html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            f"{head_inner}\n</head>\n<body>\n{body_inner}</body>\n</html>\n")
    fragment = f"{head_inner}\n{body_inner}"
    info = {"s": s, "regions": regions, "islands": islands, "extent": extent, "top10": top10}
    return full, fragment, info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", help="아티팩트 게시용 본문(문서 껍데기 없음)을 쓸 경로")
    args = ap.parse_args()

    df = pd.read_csv(bp.SRC, encoding="utf-8-sig")
    full, fragment, info = build(df)
    s = info["s"]

    same = s["grades"] == df["grade"]
    print(f"[검증] grade 열 vs {bp.BASE_LINE_PCT}% 규칙: {int(same.sum())}/{len(df)}줄 일치")
    print("[등급별 곳 수] " + " · ".join(f"{g} {s['count'][g]}곳" for g in bp.GRADES))
    total = int(df["open_ar_usd"].sum())
    print(f"[C등급 채권] {bp.money(s['ar']['C'])} / 전체 {bp.money(total)} = {bp.pct1(s['ar']['C'], total)}")
    print("[섬 배치 · 날씨(17%)]")
    for r in info["regions"]:
        c = s["region_c"].get(r["name"], 0)
        print(f"  {r['name']}: {r['n']}곳 · 채권 {bp.money(r['total'])} · C채권 {bp.money(c)}"
              f" ({bp.pct1(c, r['total'])}) · 날씨 {['맑음', '구름 조금', '흐림', '비'][weather_step(c / r['total'])]}"
              f" · 중심 ({r['x']}, {r['z']}) · 반지름 {r['r']}")
    print(f"[전화할 10곳] {', '.join(info['top10'])}")

    OUT.write_text(full, encoding="utf-8", newline="\n")
    print(f"[저장] {OUT.relative_to(bp.ROOT).as_posix()} ({len(full.encode('utf-8')):,} bytes)")
    if args.artifact:
        p = Path(args.artifact)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(fragment, encoding="utf-8", newline="\n")
        print(f"[게시용 본문] {p} ({len(fragment.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    main()
