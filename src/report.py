# 채점 결과와 예측 파일을 모아 README에 붙일 비교표를 만든다 — 지연·토큰·비용 집계

"""숫자를 손으로 옮겨 적지 않는다.

`evaluate.py` 는 대상 하나를 채점하고 끝난다. **여러 대상을 나란히 놓는 표**와
지연·토큰·비용은 아무도 안 만들고 있었고, 손으로 옮기면 README와 실측이 어긋난다.

    python src/report.py                       data/report.md 생성
    python src/report.py --print               화면에도 찍는다

없는 대상은 건너뛴다. Day 5의 `ollama` 는 서빙 전에는 파일이 없다.

비용은 **두 기준을 따로 낸다** (CLAUDE.md · Day 0 확정, 사후 변경 금지).

    (a) 계산 자원 환산   로컬 추론 시간 × GPU 시간 단가  vs  GPT-4.1 API 요금
    (b) 사업자 부담      GPT는 API 요금, 온디바이스는 0 (사용자 기기)

**P2 판정은 (a)로 한다.** 섞으면 유리한 쪽을 골랐다는 인상이 남는다.
"""

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# --- 단가 -------------------------------------------------------------------
# **고정된 것은 계산법이고 단가는 입력값이다.** 요금이 바뀌면 여기만 고치고,
# README에는 어느 시점 단가로 계산했는지 함께 적는다.
#
# ⚠ 실행 전에 현재 요금을 확인하고 맞춘다 — 추정치를 그대로 쓰면 P2 판정이 흔들린다.
GPT41_USD_PER_1M_IN = 2.00
GPT41_USD_PER_1M_CACHED_IN = 0.50
GPT41_USD_PER_1M_OUT = 8.00
GPU_USD_PER_HOUR = 0.35          # T4급 클라우드 GPU 시간 단가
PRICING_NOTE = "2026-09-07 확인 · 요금은 report.py 상단 상수"

# **캐시 적용가로 판정한다.** 200건이 같은 시스템 프롬프트 + 같은 few-shot 8쌍을
# 접두사로 공유하므로 자동 프롬프트 캐싱이 걸렸을 것이고, 그러면 GPT 쪽이 싸진다.
# 상대가 싸질수록 우리 비교는 불리해지는데, CLAUDE.md 가 (a)를 **더 엄격한 쪽**으로
# 정의했으므로 그쪽을 택한다. 정가 기준도 표에 함께 낸다.
USE_CACHED_FOR_VERDICT = True

CATEGORIES = ["exact", "parameter_error", "wrong_tool", "tool_hallucination",
              "schema_violation", "parse_failure", "over_refusal", "missed_refusal"]
LABEL = {
    "exact": "완전 일치", "parameter_error": "파라미터 오류", "wrong_tool": "툴 오류",
    "tool_hallucination": "**툴 환각**", "schema_violation": "**스키마 위반**",
    "parse_failure": "**파싱 실패**", "over_refusal": "과잉 거절",
    "missed_refusal": "놓친 거절",
}

# (표시 이름, eval 파일, pred 파일, API 요금을 내는가)
TARGETS = [
    ("GPT-4.1", "eval_gpt41.jsonl", "pred_gpt41.jsonl", True),
    ("base + few-shot", "eval_base.jsonl", "pred_base.jsonl", False),
    ("**파인튜닝**", "eval_ft.jsonl", "pred_ft_lr0.0002_ep2.jsonl", False),
    ("파인튜닝 (Ollama)", "eval_ollama.jsonl", "pred_ollama.jsonl", False),
]


def load(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def collect(base, name, ev, pr, paid):
    """한 대상의 채점·측정치를 모은다. 파일이 없으면 None."""
    ev_path, pr_path = base / ev, base / pr
    if not (ev_path.exists() and pr_path.exists()):
        return None

    rows = load(ev_path)
    preds = load(pr_path)
    n = len(rows)
    lat = sorted(p["latency_ms"] for p in preds)
    ins = [p["input_tokens"] for p in preds if p.get("input_tokens")]
    outs = [p["output_tokens"] for p in preds if p.get("output_tokens")]

    def p(q):
        return lat[min(int(len(lat) * q), len(lat) - 1)]

    return {
        "name": name, "n": n, "paid": paid,
        "counts": Counter(r["category"] for r in rows),
        "by_layer": _rate(rows, "layer"),
        "fenced": sum(1 for r in rows if r.get("fenced")),
        "think": sum(1 for p_ in preds if "<think>" in str(p_["output"])),
        "p50": p(0.5), "p95": p(0.95), "mean_ms": statistics.mean(lat),
        "in_tok": statistics.mean(ins) if ins else None,
        "out_tok": statistics.mean(outs) if outs else None,
    }


def _rate(rows, key):
    total, hit = Counter(), Counter()
    for r in rows:
        total[r[key]] += 1
        hit[r[key]] += r["category"] == "exact"
    return {k: (hit[k], total[k]) for k in sorted(total)}


def cost(t, cached=False):
    """1,000건당 비용 두 가지. 단위는 USD.

    (a) API 요금을 내는 대상은 토큰 요금, 아니면 **추론에 쓴 GPU 시간 × 단가**.
        온디바이스라고 0으로 두지 않는 것이 (a)를 더 엄격한 기준으로 만든다.
    (b) 사업자가 실제로 내는 돈. 온디바이스는 사용자 기기라 0이다.

    ``cached`` 는 입력 토큰에 캐시 요금을 적용한다. API 대상에만 의미가 있다.
    """
    if t["paid"]:
        rate = GPT41_USD_PER_1M_CACHED_IN if cached else GPT41_USD_PER_1M_IN
        api = (t["in_tok"] * rate + t["out_tok"] * GPT41_USD_PER_1M_OUT) / 1e6
        return api * 1000, api * 1000
    gpu = t["mean_ms"] / 1000 / 3600 * GPU_USD_PER_HOUR
    return gpu * 1000, 0.0


def table(targets):
    out = ["| | " + " | ".join(t["name"] for t in targets) + " |",
           "| --- | " + " | ".join("---" for _ in targets) + " |"]

    def row(title, fn):
        out.append(f"| {title} | " + " | ".join(fn(t) for t in targets) + " |")

    for c in CATEGORIES:
        strong = c == "exact"
        row(f"**{LABEL[c]}**" if strong else LABEL[c],
            lambda t, c=c: f'{t["counts"][c] / t["n"]:.1%}' + (
                f' ({t["counts"][c]})' if t["counts"][c] else ""))
    out.append("| | " + " | ".join("" for _ in targets) + " |")
    row("입력 토큰/건", lambda t: f'{t["in_tok"]:,.0f}' if t["in_tok"] else "—")
    row("출력 토큰/건", lambda t: f'{t["out_tok"]:,.0f}' if t["out_tok"] else "—")
    row("지연 p50", lambda t: f'{t["p50"]:,.0f}ms')
    row("지연 p95", lambda t: f'{t["p95"]:,.0f}ms')
    row("코드펜스", lambda t: f'{t["fenced"]}건')
    row("`<think>` 블록", lambda t: f'{t["think"]}건')
    row("1,000건당 (a) 정가 기준", lambda t: f"${cost(t)[0]:.3f}")
    row("**1,000건당 (a) 캐시 적용 — 판정 기준**",
        lambda t: f"${cost(t, cached=True)[0]:.3f}")
    row("(b) 사업자 부담", lambda t: f"${cost(t)[1]:.3f}")
    return "\n".join(out)


def verdict(targets):
    """P1·P2를 기준 그대로 판정한다. 손으로 세면 유리한 쪽으로 기운다."""
    by = {t["name"]: t for t in targets}
    base, ft = by.get("base + few-shot"), by.get("**파인튜닝**")
    gpt = by.get("GPT-4.1")
    if not (base and ft and gpt):
        return "_판정에 필요한 대상이 빠져 있다._"

    rate = lambda t, c: t["counts"][c] / t["n"]
    gain = (rate(ft, "exact") - rate(base, "exact")) * 100
    ratio = rate(ft, "exact") / rate(gpt, "exact") * 100
    ok = lambda b: "✅" if b else "❌"

    return "\n".join([
        "| 기준 | 조건 | 실측 | |",
        "| --- | --- | --- | --- |",
        f"| P1 | base 대비 +15%p 이상 | **+{gain:.1f}%p** | {ok(gain >= 15)} |",
        f"| P1 | 스키마 위반 5% 미만 | {rate(ft, 'schema_violation'):.1%} | {ok(rate(ft, 'schema_violation') < .05)} |",
        f"| P1 | 툴 환각 2% 미만 | {rate(ft, 'tool_hallucination'):.1%} | {ok(rate(ft, 'tool_hallucination') < .02)} |",
        f"| P2 | GPT-4.1의 90% 이상 | **{ratio:.0f}%** | {ok(ratio >= 90)} |",
        f"| P2 | 건당 비용 1/10 이하 | "
        f"{cost(gpt, USE_CACHED_FOR_VERDICT)[0] / cost(ft)[0]:.1f}배 저렴 "
        f"({'캐시 적용가' if USE_CACHED_FOR_VERDICT else '정가'} 기준) | "
        f"{ok(cost(ft)[0] * 10 <= cost(gpt, USE_CACHED_FOR_VERDICT)[0])} |",
        f"| P2 | p50 지연 더 낮음 | {ft['p50']:,.0f}ms vs {gpt['p50']:,.0f}ms | {ok(ft['p50'] < gpt['p50'])} |",
    ])


def layers(targets):
    keys = sorted({k for t in targets for k in t["by_layer"]})
    out = ["| 층 | " + " | ".join(t["name"] for t in targets) + " |",
           "| --- | " + " | ".join("---" for _ in targets) + " |"]
    for k in keys:
        cells = []
        for t in targets:
            hit, total = t["by_layer"].get(k, (0, 0))
            cells.append(f"{hit / total:.1%} ({hit}/{total})" if total else "—")
        out.append(f"| `{k}` | " + " | ".join(cells) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data")
    ap.add_argument("--out", default="data/report.md")
    ap.add_argument("--print", dest="show", action="store_true")
    args = ap.parse_args()

    base = Path(args.dir)
    targets = [t for t in (collect(base, *spec) for spec in TARGETS) if t]
    if not targets:
        raise SystemExit("채점 결과가 없다 — evaluate.py 를 먼저 돌린다")

    n = targets[0]["n"]
    text = "\n\n".join([
        f"# 결과 — 테스트 {n}건",
        f"_{PRICING_NOTE} · GPU ${GPU_USD_PER_HOUR}/시간_",
        "## 3자 비교 · 7분류 오답 분해", table(targets),
        "## 성공 기준 판정", verdict(targets),
        "## 난이도 층별 완전 일치", layers(targets),
    ]) + "\n"

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"대상 {len(targets)}개 → {args.out}")
    if args.show:
        print("\n" + text)


if __name__ == "__main__":
    main()
