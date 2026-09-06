# 데이터셋을 QLoRA 학습용 대화 포맷으로 바꾼다 — hint 를 버리고 messages 만 남긴다

"""학습 데이터와 평가 프롬프트가 **글자 단위로 같아야** 한다.

그래서 여기서 프롬프트를 새로 짜지 않고 [predict.py](predict.py) 의
``build_messages("ft", ...)`` 를 **그대로 불러 쓴다.** 손으로 다시 적으면 언젠가
한쪽만 고쳐지고, 그러면 Day 4에서 재는 것이 파인튜닝 효과가 아니라
**포맷 불일치**가 된다. 그것은 프로젝트 전체를 무효로 만드는 종류의 사고다.

    python src/build_sft.py                          data/sft_train.jsonl · sft_val.jsonl
    python src/build_sft.py --peek 3                 변환 결과를 눈으로 본다

무엇이 빠지는가 — `hint` 를 통째로 버린다.

`hint.confuse_with` 에는 **툴 이름이 그대로 들어 있다** (`"get_records"`).
이것이 입력에 새면 결정 2(툴 스펙을 프롬프트에 넣지 않는다)가 깨지고
파인튜닝 기여도 측정이 무효가 된다. 학습 샘플에 쓰는 것은 `utterance` 와
`label` 둘뿐이고, **그 사실을 주석이 아니라 검사로 강제한다** (``leak_check``).

`layer` 도 안 넘긴다. 층은 **분석용 꼬리표**이지 모델이 볼 것이 아니다.

출력 형태 — TRL `SFTTrainer` 의 대화 포맷이다.

    {"id": "1790", "messages": [{"role": "user", ...}, {"role": "assistant", ...}]}

`ft` 대상은 시스템 메시지가 없다. 발화 한 줄이 통째로 입력이다 (결정 2).
`id` 는 학습에 안 쓰이지만 나쁜 샘플을 원본으로 되짚기 위해 남긴다.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import predict as P
import tools as T

SPLITS = ["train", "val"]


def canonical(label):
    """직렬화 규칙대로 키 순서를 고정한다 (CLAUDE.md 직렬화 규칙).

    `tool` → `arguments` → `reason`, `arguments` 내부는 `tools.py` 의 정의 순서.
    채점기는 파싱한 뒤 비교하므로 순서를 안 보지만 **모델은 글자를 배운다.**
    순서가 흔들린 라벨로 학습시키면 형식 안정성이 그만큼 깎인다.
    """
    tool = label["tool"]
    if tool is None:
        return {"tool": None, "arguments": {}, "reason": label["reason"]}

    order = [p["name"] for p in T.TOOLS[tool]["params"]]
    if set(order) != set(label["arguments"]):
        raise ValueError(f"{tool} 파라미터 불일치 — {sorted(label['arguments'])}")
    return {"tool": tool,
            "arguments": {k: label["arguments"][k] for k in order},
            "reason": label["reason"]}


def leak_check(rows):
    """입력 쪽에 툴 이름이 새지 않았는지 본다. 새면 멈춘다.

    라벨(assistant)에는 툴 이름이 당연히 있다. 문제는 **user 메시지**다.
    """
    names = list(T.TOOLS)
    leaked = []
    for r in rows:
        for m in r["messages"]:
            if m["role"] == "assistant":
                continue
            hit = [n for n in names if n in m["content"]]
            if hit:
                leaked.append((r["id"], hit))
    if leaked:
        for rid, hit in leaked[:5]:
            print(f"  [{rid}] {hit}")
        raise SystemExit(f"입력에 툴 이름이 샜다 — {len(leaked)}건. 결정 2가 깨진다")


def convert(rows):
    out, reordered = [], 0
    for r in rows:
        label = canonical(r["label"])
        if json.dumps(label, ensure_ascii=False) != json.dumps(r["label"], ensure_ascii=False):
            reordered += 1
        messages = P.build_messages("ft", r["utterance"])
        messages.append({"role": "assistant",
                         "content": json.dumps(label, ensure_ascii=False)})
        out.append({"id": r["id"], "messages": messages})
    return out, reordered


def report(name, src, made):
    """무엇이 들어갔는지 숫자로 남긴다. 학습을 돌린 뒤에는 확인이 비싸다."""
    tools = Counter(r["label"]["tool"] or f'거절:{r["label"]["reason"]}' for r in src)
    lens = sorted(len(m["content"]) for r in made for m in r["messages"]
                  if m["role"] == "assistant")
    print(f"{name:5s} {len(made):5d}건 · 층 {dict(Counter(r['layer'] for r in src))}")
    print(f"      툴 {len(tools)}종 · 최소 {min(tools.values())}건 · "
          f"거절 {sum(v for k, v in tools.items() if k.startswith('거절')) / len(src):.1%}")
    print(f"      라벨 길이 중앙 {lens[len(lens) // 2]}자 · 최대 {lens[-1]}자")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data")
    ap.add_argument("--peek", type=int, default=0, help="변환 결과를 N건 찍어본다")
    args = ap.parse_args()

    base = Path(args.dir)
    for name in SPLITS:
        src = [json.loads(l) for l in (base / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        made, reordered = convert(src)
        leak_check(made)

        report(name, src, made)
        if reordered:
            print(f"      ⚠ 키 순서를 바로잡은 라벨 {reordered}건")

        out = base / f"sft_{name}.jsonl"
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in made),
                       encoding="utf-8")
        print(f"      → {out}")

        for r in made[:args.peek]:
            print(f"\n  [{r['id']}]")
            for m in r["messages"]:
                print(f"    {m['role']:9s} {m['content']}")


if __name__ == "__main__":
    main()
