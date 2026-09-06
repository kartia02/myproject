# 테스트셋을 사람이 눈으로 검수할 Markdown 체크리스트로 뽑는다

"""사람 검수용 Markdown 체크리스트를 만든다.

학습·평가 데이터는 바꾸지 않는다. 검수자는 생성된 문서의 각 행에 판정만 기록하고,
수정이 필요하면 원본 id와 사유를 남긴다.

    python src/review_dataset.py --input data/test.jsonl --out data/test_review.md
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/test.jsonl")
    parser.add_argument("--out", default="data/test_review.md")
    args = parser.parse_args()

    rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line]
    lines = [
        "# PawNote 테스트셋 검수", "",
        "각 행에서 발화·라벨·자연스러움을 확인한다. `OK` / `수정` / `제외` 중 하나를 적고,",
        "수정·제외는 사유를 남긴다. 기준은 `labeling-guide.md` §7~§9이다.", "",
    ]
    for number, row in enumerate(rows, 1):
        label = json.dumps(row["label"], ensure_ascii=False)
        lines += [
            f"## {number:03d} — {row['id']} · {row['layer']}", "",
            f"- 발화: {row['utterance']}",
            f"- 라벨: `{label}`",
            "- 판정: [ ] OK  [ ] 수정  [ ] 제외",
            "- 사유 / 수정안:", "",
        ]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"검수 문서 {len(rows)}건 → {args.out}")


if __name__ == "__main__":
    main()
