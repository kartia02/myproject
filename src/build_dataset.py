# 샘플링 → 발화 생성 → 라벨 검증을 한 번에 돌린다 — 데이터셋 빌드 진입점

"""세 단계를 잇는다.

    sampler.sample()  →  generate.generate()  →  verify.verify()
    정답 확정             발화 입히기              라벨 정합 검사

30건 테스트와 2,400건 본생성이 같은 경로를 쓴다. 30건에서 확인한 것이
본생성에서 그대로 재현되어야 하기 때문이다.

사용법

    python src/build_dataset.py -n 30 --out data/sample30.jsonl
    python src/build_dataset.py -n 2400 --out data/all.jsonl --split

``--split`` 은 학습 2,000 / 검증 200 / 테스트 200 으로 나눠 따로 저장한다.
"""

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import generate as G
import sampler as S
import verify as V


def load_env(path=".env"):
    """python-dotenv 없이 .env 를 읽는다. 의존성을 하나라도 줄인다."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def dedup(rows):
    """발화가 글자 그대로 같은 것을 지운다.

    같은 발화가 학습과 테스트에 나뉘어 들어가면 **답을 외운 것을 실력으로 잰다.**
    실측에서는 `"이거"`·`"양치 완료"` 처럼 아주 짧은 발화만 부딪혔다.
    임베딩 유사도 기반의 근접 중복 제거는 별도 단계다 (checklist Day 2).
    """
    seen, out = set(), []
    for r in rows:
        if r["utterance"] not in seen:
            seen.add(r["utterance"])
            out.append(r)
    if len(out) < len(rows):
        print(f"완전 중복 {len(rows) - len(out)}건 제거")
    return out


def _allocate(rows, n):
    """층 비율대로 n건을 배분한다. 반올림 오차는 가장 큰 층이 흡수한다."""
    layers = Counter(r["layer"] for r in rows)
    take = {k: int(n * c / len(rows)) for k, c in layers.items()}
    take[max(layers, key=layers.get)] += n - sum(take.values())
    return take


def split(rows, n_test=200, n_val=200, seed=0):
    """층 비율을 유지하며 셋으로 나눈다.

    앞에서 그냥 잘라내면(``rows[:200]``) 층이 크게 흔들린다. 실측에서
    ``tense`` 가 20 → 12, ``ambiguous`` 가 10 → 6 이 됐다.
    **Day 4의 층별 정확도 분해가 12건 위에서는 성립하지 않는다** — 1건이
    8%p를 움직이므로 재는 것이 실력인지 우연인지 구분되지 않는다.

    나눈 뒤 다시 섞는다. 층별로 모아 담으면 파일이 층 순서로 정렬돼
    검수할 때 앞뒤 발화가 서로 힌트가 된다.
    """
    by_layer = defaultdict(list)
    for r in rows:
        by_layer[r["layer"]].append(r)

    take_test, take_val = _allocate(rows, n_test), _allocate(rows, n_val)
    parts = {"test": [], "val": [], "train": []}

    for layer, group in by_layer.items():
        i = take_test[layer]
        j = i + take_val[layer]
        parts["test"] += group[:i]
        parts["val"] += group[i:j]
        parts["train"] += group[j:]

    rng = random.Random(seed)
    for rows_ in parts.values():
        rng.shuffle(rows_)
    return parts


def save(rows, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"저장 {len(rows)}건 → {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=30, help="생성할 건수")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/sample30.jsonl")
    ap.add_argument("--split", action="store_true",
                    help="학습 2,000 / 검증 200 / 테스트 200 으로 나눠 저장")
    args = ap.parse_args()

    load_env()

    # 1) 정답 샘플링 — 여기서 분포가 치우쳐 있으면 GPT를 부를 필요가 없다
    seeds = S.sample(args.n, seed=args.seed)
    summary = S.summarize(seeds)
    print("=== 시드 분포 ===")
    print(f"총 {summary['총']} · 층 {summary['층']}")
    print(f"툴 최소 {summary['툴_최소']}건 · caregiver {summary['caregiver_전체비율']:.1%}")

    # 2) 발화 생성
    print("\n=== 발화 생성 ===")
    said = G.generate(seeds)

    # 3) 라벨 검증 (결정 14)
    print("\n=== 라벨 검증 ===")
    kept, _ = V.verify(said)

    kept = dedup(kept)

    if not args.split:
        save(kept, args.out)
        return

    base = Path(args.out).parent
    for name, rows in split(kept).items():
        save(rows, base / f"{name}.jsonl")
    print("\n테스트 200건은 사람이 눈으로 검수한다 — labeling-guide.md 참조")


if __name__ == "__main__":
    main()
