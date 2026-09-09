# 채점 결과에서 README용 SVG 차트를 그린다 — 숫자를 손으로 박지 않는다

"""막대 세 장을 `assets/` 에 쓴다.

    python src/charts.py

`report.py` 와 같은 이유로 만든다. **그림 안의 숫자가 표와 어긋나면 표가 의심받는다.**
`data/eval_*.jsonl` 을 읽어 그리므로 재채점하면 그림도 같이 바뀐다.

**의존성을 늘리지 않으려고 SVG 문자열을 직접 쓴다.** 막대 세 장에 그림 라이브러리를
붙일 이유가 없고, SVG 는 텍스트라 `git diff` 로 무엇이 바뀌었는지 읽힌다.

색은 `prefers-color-scheme` 으로 두 벌 둔다 — GitHub 이 어두운 테마에서도 읽혀야 한다.
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

import report as R

W = 760
PAD = 24
LABEL_W = 150
ROW_H = 40

STYLE = """<style>
  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  .fg { fill: #111827 } .mut { fill: #6b7280 } .grid { stroke: #e5e7eb }
  .track { fill: #f3f4f6 }
  @media (prefers-color-scheme: dark) {
    .fg { fill: #e5e7eb } .mut { fill: #9ca3af } .grid { stroke: #374151 }
    .track { fill: #1f2937 }
  }
</style>"""

# 파인튜닝만 색을 준다. 나머지는 배경이다 — 눈이 먼저 갈 곳을 정해 둔다
TONE = {
    "GPT-4.1": "#6b7280",
    "base + few-shot": "#9ca3af",
    "파인튜닝": "#2563eb",
    "파인튜닝 (Ollama)": "#60a5fa",
}

SEGMENT = [
    ("exact", "완전 일치", "#16a34a"),
    ("parameter_error", "파라미터 오류", "#fbbf24"),
    ("wrong_tool", "툴 오류", "#f97316"),
    ("over_refusal", "과잉 거절", "#a78bfa"),
    ("missed_refusal", "놓친 거절", "#db2777"),
    ("schema_violation", "스키마 위반", "#dc2626"),
    ("tool_hallucination", "툴 환각", "#7f1d1d"),
    ("parse_failure", "파싱 실패", "#450a0a"),
]


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(height, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" '
            f'viewBox="0 0 {W} {height}" role="img">{STYLE}{body}</svg>\n')


def title(text, y=26):
    return f'<text x="{PAD}" y="{y}" class="fg" font-size="15" font-weight="600">{esc(text)}</text>'


def bar_rows(targets, value, text, top, width=None, clean=None):
    """가로 막대 한 벌. ``value`` 는 0~1, ``text`` 는 막대 끝에 적을 말."""
    width = width or W - PAD * 2 - LABEL_W - 60
    out = []
    for index, t in enumerate(targets):
        y = top + index * ROW_H
        name = t["name"].replace("**", "")
        weight = "600" if "파인튜닝" == name else "400"
        out.append(
            f'<text x="{PAD + LABEL_W - 10}" y="{y + 15}" text-anchor="end" '
            f'class="fg" font-size="13" font-weight="{weight}">{esc(name)}</text>'
            f'<rect x="{PAD + LABEL_W}" y="{y + 3}" width="{width}" height="16" '
            f'rx="3" class="track"/>'
            f'<rect x="{PAD + LABEL_W}" y="{y + 3}" '
            f'width="{max(2, width * value(t)):.1f}" height="16" rx="3" '
            f'fill="{TONE[name]}"/>'
            f'<text x="{PAD + LABEL_W + width + 8}" y="{y + 16}" class="fg" '
            f'font-size="12" font-weight="{weight}">{esc(text(t))}</text>')
    return "".join(out)


def chart_accuracy(targets, path):
    """완전 일치율 하나만. 제일 먼저 보일 그림이라 다른 걸 얹지 않는다."""
    rate = lambda t: t["counts"]["exact"] / t["n"]
    body = [title(f"완전 일치율 — 테스트 {targets[0]['n']}건"),
            bar_rows(targets, rate, lambda t: f"{rate(t):.1%}", 48)]
    Path(path).write_text(svg(48 + ROW_H * len(targets) + 12, "".join(body)),
                          encoding="utf-8")


def chart_errors(targets, path):
    """7분류를 한 줄에 쌓는다. 길이가 아니라 **색이 어디서 끊기는지**를 본다."""
    width = W - PAD * 2 - LABEL_W - 60
    body = [title("오답 유형 분포 — 심각도별")]
    top = 48
    for index, t in enumerate(targets):
        y = top + index * ROW_H
        name = t["name"].replace("**", "")
        weight = "600" if name == "파인튜닝" else "400"
        body.append(
            f'<text x="{PAD + LABEL_W - 10}" y="{y + 15}" text-anchor="end" '
            f'class="fg" font-size="13" font-weight="{weight}">{esc(name)}</text>')
        x = PAD + LABEL_W
        for key, _, color in SEGMENT:
            span = width * t["counts"][key] / t["n"]
            if span <= 0:
                continue
            body.append(f'<rect x="{x:.1f}" y="{y + 3}" width="{span:.1f}" '
                        f'height="16" fill="{color}"/>')
            x += span

    legend_y = top + ROW_H * len(targets) + 12
    x = PAD + LABEL_W
    for key, label, color in SEGMENT:
        if not any(t["counts"][key] for t in targets):
            continue
        body.append(f'<rect x="{x}" y="{legend_y}" width="10" height="10" rx="2" '
                    f'fill="{color}"/>'
                    f'<text x="{x + 14}" y="{legend_y + 9}" class="mut" '
                    f'font-size="11">{esc(label)}</text>')
        x += 22 + len(label) * 11
        if x > W - 120:
            x, legend_y = PAD + LABEL_W, legend_y + 18
    Path(path).write_text(svg(legend_y + 26, "".join(body)), encoding="utf-8")


def chart_cost(targets, path):
    """비용과 지연을 나란히. **한쪽은 이기고 한쪽은 진다** — 둘 다 같은 크기로 낸다."""
    costs = [R.cost(t, cached=R.USE_CACHED_FOR_VERDICT)[0] for t in targets]
    top_cost, top_lat = max(costs), max(t["p50"] for t in targets)

    body = [title("1,000건당 비용 — 계산 자원 환산 (P2 판정 기준)")]
    body.append(bar_rows(targets, lambda t: R.cost(t, R.USE_CACHED_FOR_VERDICT)[0] / top_cost,
                         lambda t: f"${R.cost(t, R.USE_CACHED_FOR_VERDICT)[0]:.3f}", 48))

    second = 48 + ROW_H * len(targets) + 28
    body.append(title("지연 p50 — 낮을수록 좋다", second - 8))
    body.append(bar_rows(targets, lambda t: t["p50"] / top_lat,
                         lambda t: f"{t['p50']:,.0f}ms", second + 14))
    Path(path).write_text(
        svg(second + 14 + ROW_H * len(targets) + 12, "".join(body)), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="data")
    parser.add_argument("--out", default="assets")
    args = parser.parse_args()

    base = Path(args.dir)
    targets = [t for t in (R.collect(base, *spec) for spec in R.TARGETS) if t]
    if not targets:
        raise SystemExit("채점 결과가 없다 — evaluate.py 를 먼저 돌린다")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    chart_accuracy(targets, out / "accuracy.svg")
    chart_errors(targets, out / "errors.svg")
    chart_cost(targets, out / "cost-latency.svg")
    print(f"차트 3장 → {out}/")


if __name__ == "__main__":
    main()
