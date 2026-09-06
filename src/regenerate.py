# MUST_KEEP 규칙을 어긴 행만 다시 생성해 제자리에 교체한다

"""데이터 전체를 다시 만들지 않는다. **결함이 확인된 행만** 고친다.

    python src/regenerate.py --dry-run          어떤 행이 대상인지만 본다
    python src/regenerate.py                    실제로 고친다

왜 부분 재생성인가.

- 전체 재생성은 비용이 400배이고, **분할이 통째로 달라져** 이미 낸 수치와 이어지지 않는다
- `id` 와 `layer` 를 유지하므로 학습/검증/테스트 소속이 안 흔들린다

무엇이 대상인가.

``generate.CUE`` 의 패턴에 걸리지 않는 행이다. `MUST_KEEP` 에 적은 지시가
지켜지지 않았다는 뜻이고, 그 툴은 **파라미터만으로 자기를 식별하지 못하므로**
발화에 단서가 없으면 라벨이 사실상 틀린 것이 된다.

실패해도 원본을 지우지 않는다. 재시도해서 안 되면 그대로 두고 보고한다 —
**고치려다 잃는 것이 고치지 않는 것보다 나쁘다.**
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_dataset as B
import generate as G
import verify as V

FILES = ["train", "val", "test"]
MAX_ROUNDS = 3


def defective(rows):
    """CUE 패턴에 안 걸리는 행. 툴별 정규식은 generate.py 가 갖는다."""
    pats = {t: re.compile(p) for t, p in G.CUE.items()}
    return [r for r in rows
            if r["label"]["tool"] in pats
            and not pats[r["label"]["tool"]].search(r["utterance"])]


def regenerate(targets):
    """대상을 다시 생성한다. CUE 를 통과하고 라벨 검증도 통과한 것만 돌려준다."""
    pats = {t: re.compile(p) for t, p in G.CUE.items()}
    fixed, pending = {}, list(targets)

    for round_no in range(1, MAX_ROUNDS + 1):
        if not pending:
            break
        print(f"\n--- {round_no}회차 · {len(pending)}건 ---")
        # hint·label 만 넘긴다. 이전 발화가 들어가면 GPT가 그것에 끌려간다
        seeds = [{k: v for k, v in r.items() if k != "utterance"} for r in pending]
        made = G.generate(seeds)

        still = []
        for row in made:
            tool = row["label"]["tool"]
            if not pats[tool].search(row["utterance"]):
                still.append(row)
                continue
            verdict, checked, _ = V.check(row)
            if verdict == "dropped":
                still.append(row)
                continue
            fixed[row["id"]] = checked

        got = {r["id"] for r in made}
        pending = still + [r for r in pending if r["id"] not in got]
        print(f"  성공 {len(made) - len(still)}건 · 남은 {len(pending)}건")

    return fixed, pending


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dir", default="data")
    args = ap.parse_args()

    B.load_env()
    base = Path(args.dir)
    loaded = {n: [json.loads(l) for l in (base / f"{n}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
              for n in FILES}

    targets = []
    for name, rows in loaded.items():
        bad = defective(rows)
        by_tool = Counter(r["label"]["tool"] for r in bad)
        print(f"{name:6s} {len(rows):5d}건 → 대상 {len(bad):3d}건 {dict(by_tool)}")
        targets += bad

    if not targets:
        print("\n고칠 것이 없다")
        return
    if args.dry_run:
        print(f"\n총 {len(targets)}건. 발화 미리보기")
        for r in targets[:10]:
            print(f"  [{r['id']}] {r['label']['tool']} · {r['hint']['persona']} — {r['utterance'][:55]}")
        return

    fixed, failed = regenerate(targets)

    print(f"\n=== 교체 {len(fixed)}건 · 실패 {len(failed)}건 ===")
    for name, rows in loaded.items():
        changed = sum(1 for r in rows if r["id"] in fixed)
        if not changed:
            continue
        merged = [fixed.get(r["id"], r) for r in rows]
        B.save(merged, base / f"{name}.jsonl")
        print(f"  {name} — {changed}건 교체")

    if failed:
        print("\n원본을 유지한 건 (재생성 실패)")
        for r in failed:
            print(f"  [{r['id']}] {r['utterance'][:55]}")


if __name__ == "__main__":
    main()
