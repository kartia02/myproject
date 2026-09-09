# 발화 임베딩으로 의미가 겹치는 쌍을 센다 — 합성 데이터 균질화 측정의 마지막 칸

"""임베딩 유사도 0.9 이상 중복을 **측정한다.**

    python src/dedup_check.py               재고 data/dedup.md 에 쓴다
    python src/dedup_check.py --threshold 0.95

`distinct-2` 는 n-gram 이 겹치는지만 본다. **말을 바꿔 쓴 같은 문장**은 못 잡는다 —
"아침에 사료 줬어" 와 "오전에 밥 먹였어" 는 겹치는 2-gram 이 없다. 그 자리를
임베딩이 메운다.

**지우지 않고 센다.** 학습이 이미 끝났으므로 `train` 에서 행을 빼면 재학습이고,
`test` 에서 빼면 확정한 숫자가 다시 움직인다. 규모를 먼저 보고 뺄지 정한다 —
[labeling-guide.md](labeling-guide.md) §7 ④ 에서 자동 보정을 규모 재보고 접었던 것과
같은 순서다.

**제일 중요한 것은 층 안이 아니라 `train`↔`test` 다.** 학습에서 본 문장과 거의 같은
것이 시험지에 있으면 점수가 부풀려진다. 검수가 걷어낸 것과 같은 종류의 부풀림이고,
이쪽은 사람 눈으로 못 잡는다 — 2,000건과 169건을 교차로 읽을 수는 없으니까.

임베딩은 `data/embeddings.jsonl` 에 저장해 다시 부르지 않는다.
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np

MODEL = "text-embedding-3-small"
BATCH = 256
SPLITS = ["train", "val", "test_reviewed"]


def load_env(path=".env"):
    """python-dotenv 없이 .env 를 읽는다. 의존성을 하나라도 줄인다."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def load_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def embed(rows, cache_path):
    """캐시에 없는 발화만 부른다. 두 번째 실행부터는 API 호출이 0이다."""
    cache = {}
    if cache_path.exists():
        cache = {r["id"]: r["vec"] for r in load_jsonl(cache_path)}

    todo = [r for r in rows if r["id"] not in cache]
    if todo:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        for start in range(0, len(todo), BATCH):
            chunk = todo[start:start + BATCH]
            result = client.embeddings.create(
                model=MODEL, input=[r["utterance"] for r in chunk])
            for row, item in zip(chunk, result.data):
                cache[row["id"]] = item.embedding
            print(f"  임베딩 {min(start + BATCH, len(todo))}/{len(todo)}")
        with open(cache_path, "w", encoding="utf-8") as handle:
            for sample_id, vec in cache.items():
                handle.write(json.dumps({"id": sample_id, "vec": vec}) + "\n")

    matrix = np.array([cache[r["id"]] for r in rows], dtype=np.float32)
    # 코사인 유사도를 내적 한 번으로 끝내려고 미리 길이를 1로 맞춘다
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def pairs_within(vectors, rows, threshold):
    """같은 묶음 안에서 임계값을 넘는 쌍. 자기 자신과 대칭 쌍은 뺀다."""
    sim = vectors @ vectors.T
    i, j = np.triu_indices(len(rows), k=1)
    hit = sim[i, j] >= threshold
    return sorted(zip(sim[i, j][hit], i[hit], j[hit]), reverse=True)


def pairs_across(left_vec, right_vec, threshold):
    """다른 묶음 사이의 쌍. 각 왼쪽 행에 대해 가장 닮은 오른쪽 행만 본다."""
    sim = left_vec @ right_vec.T
    best = sim.argmax(axis=1)
    top = sim[np.arange(len(sim)), best]
    hit = np.where(top >= threshold)[0]
    return sorted(zip(top[hit], hit, best[hit]), reverse=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="data")
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--out", default="data/dedup.md")
    parser.add_argument("--show", type=int, default=10, help="예시로 적을 쌍 개수")
    args = parser.parse_args()

    load_env()
    base = Path(args.dir)
    data = {name: load_jsonl(base / f"{name}.jsonl") for name in SPLITS}
    vecs = {name: embed(rows, base / "embeddings.jsonl")
            for name, rows in data.items()}

    threshold = args.threshold
    out = [f"# 임베딩 중복 측정 — 유사도 {threshold} 이상",
           "",
           f"`{MODEL}` · 코사인 유사도 · 발화 텍스트만 비교한다. "
           "`distinct-2` 가 못 보는 **말을 바꿔 쓴 같은 문장**을 잡는 자리다.",
           "",
           "## 묶음 안", "",
           "| 묶음 | 건수 | 쌍 | 관련된 행 |", "| --- | --- | --- | --- |"]

    within = {}
    for name in SPLITS:
        found = pairs_within(vecs[name], data[name], threshold)
        within[name] = found
        touched = len({i for _, i, j in found} | {j for _, i, j in found})
        out.append(f"| `{name}` | {len(data[name])}건 | {len(found)}쌍 | "
                   f"{touched}건 ({touched / len(data[name]):.1%}) |")

    out += ["", "## 묶음 사이 — 학습에서 본 문장이 시험지에 있는가", "",
            "| | 건수 | 임계값 넘는 행 |", "| --- | --- | --- |"]

    across = {}
    for name in ("test_reviewed", "val"):
        found = pairs_across(vecs[name], vecs["train"], threshold)
        across[name] = found
        out.append(f"| `{name}` ↔ `train` | {len(data[name])}건 | "
                   f"{len(found)}건 ({len(found) / len(data[name]):.1%}) |")

    for title, found, left, right in [
        (f"`test_reviewed` ↔ `train` 상위 {args.show}쌍",
         across["test_reviewed"], "test_reviewed", "train"),
        (f"`train` 안 상위 {args.show}쌍", within["train"], "train", "train"),
    ]:
        out += ["", f"## {title}", "",
                "| 유사도 | 한쪽 | 다른 쪽 |", "| --- | --- | --- |"]
        for score, i, j in found[:args.show]:
            a, b = data[left][i], data[right][j]
            out.append(f"| {score:.3f} | `{a['id']}` {a['utterance']} "
                       f"| `{b['id']}` {b['utterance']} |")
        if not found:
            out.append("| — | 없다 | |")

    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"→ {args.out}")
    for name in SPLITS:
        print(f"  {name} 안 {len(within[name])}쌍")
    for name in ("test_reviewed", "val"):
        print(f"  {name} ↔ train {len(across[name])}건")


if __name__ == "__main__":
    main()
