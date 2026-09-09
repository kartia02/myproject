# 검수 판정을 시험지에 반영한다 — 원본 test.jsonl 은 건드리지 않고 새 파일을 만든다

"""테스트 200건 검수 결과를 채점용 시험지로 바꾼다.

    python src/apply_review.py            data/test_reviewed.jsonl · data/review_applied.md 생성
    python src/apply_review.py --check    쓰지 않고 검증만 한다

**원본을 직접 고치지 않는다.** `test.jsonl` 을 덮어쓰면 "무엇을 왜 고쳤는지"가
사라지고, 되돌리려면 재생성해야 하는데 생성은 `temperature=1.0` 이라 복원이 안 된다.
반영은 스크립트가 맡고 원본과 결과가 나란히 남는다.

**판정과 고칠 값을 다른 곳에 둔 이유가 있다.** TSV 의 `사유` 칸은 사람이 읽는
근거이고 문장이다. 그것을 파싱해서 값을 뽑으면 문장을 고칠 때마다 데이터가 바뀐다.
그래서 기계가 읽는 값은 아래 `FIXES` 표에 따로 적고, **둘이 서로를 검증한다** —
`라벨수정` 인데 표에 없거나, 표에 있는데 판정이 다르면 멈춘다.

버려진 행은 시험지에서 빠지므로 채점 대상이 줄어든다. 예측 파일은 200건 그대로라
`evaluate.py --subset` 으로 채점한다.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

# 라벨수정 판정이 난 행에서 **실제로 바꿀 값**. TSV 의 사유와 한 건씩 대응한다.
# `None` 은 JSON 의 null 이다 — 미언급을 뜻하고 빈 문자열과 다르다.
FIXES = {
    # 발화에 먼저 나온 것이 since, 나중이 until (labeling-guide §4)
    "0235": {"since": "오늘 아침", "until": "며칠 전"},
    "0439": {"since": "어제 밤", "until": "일주일째"},
    "0693": {"since": "어제", "until": "3일 전"},
    # 한 시점만 말했는데 양쪽에 같은 값이 들어가 구간처럼 보이던 것
    "0098": {"until": None},
    "0203": {"until": None},
    "0724": {"until": None},
    "0889": {"until": None},
    # caregiver 는 돌본 사람일 때만 채운다 (labeling-guide §4)
    "1332": {"caregiver": None},
    "1525": {"caregiver": None},
    "1772": {"caregiver": None},
    "2378": {"caregiver": None},
    # 발화에 있는데 안 담긴 값
    "1246": {"food": "호두"},
    "1381": {"time": "잠깐 전"},
}

TSVS = ["review_decisions.tsv", "review_draft.tsv"]
VERDICTS = {"맞음", "라벨수정", "버림"}


def load_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_reviews(base):
    """두 TSV 를 합친다. 같은 id 가 양쪽에 있으면 멈춘다 — 어느 판정이 이겼는지 모른다."""
    reviews = {}
    for name in TSVS:
        for line in (base / name).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            sample_id, verdict, reason, decider = (line.split("\t") + ["", "", ""])[:4]
            if verdict not in VERDICTS:
                raise SystemExit(f"{sample_id} — 알 수 없는 판정 {verdict!r}")
            if sample_id in reviews:
                raise SystemExit(f"{sample_id} — 두 파일에 겹친다")
            reviews[sample_id] = {"verdict": verdict, "reason": reason,
                                  "decider": decider, "source": name}
    return reviews


def check(rows, reviews):
    """시험지·판정·수정표 셋이 서로 맞는지 본다. 하나라도 어긋나면 멈춘다."""
    ids = {row["id"] for row in rows}
    if missing := ids - set(reviews):
        raise SystemExit(f"판정이 없는 행 {len(missing)}건 — {sorted(missing)[:5]}")
    if extra := set(reviews) - ids:
        raise SystemExit(f"시험지에 없는 판정 {len(extra)}건 — {sorted(extra)[:5]}")

    edited = {i for i, r in reviews.items() if r["verdict"] == "라벨수정"}
    if unfixed := edited - set(FIXES):
        raise SystemExit(f"라벨수정인데 고칠 값이 없다 — {sorted(unfixed)}")
    if orphan := set(FIXES) - edited:
        raise SystemExit(f"FIXES 에 있는데 판정이 라벨수정이 아니다 — {sorted(orphan)}")

    by_id = {row["id"]: row for row in rows}
    for sample_id, patch in FIXES.items():
        args = by_id[sample_id]["label"]["arguments"]
        if unknown := set(patch) - set(args):
            raise SystemExit(f"{sample_id} — 이 툴에 없는 파라미터 {sorted(unknown)}")
        if all(args[k] == v for k, v in patch.items()):
            raise SystemExit(f"{sample_id} — 이미 그 값이라 고칠 게 없다")


def apply(rows, reviews):
    """살아남은 행만 돌려주고, 로그에 쓸 변경 내역을 함께 낸다."""
    kept, changes = [], []
    for row in rows:
        review = reviews[row["id"]]
        if review["verdict"] == "버림":
            continue
        if review["verdict"] == "라벨수정":
            args = row["label"]["arguments"]
            before = {k: args[k] for k in FIXES[row["id"]]}
            args.update(FIXES[row["id"]])
            changes.append((row["id"], before, FIXES[row["id"]], review))
        kept.append(row)
    return kept, changes


def show(value):
    return "`null`" if value is None else f"`{value}`"


def log(rows, kept, reviews, changes):
    counts = Counter(r["verdict"] for r in reviews.values())
    dropped = [(i, r) for i, r in reviews.items() if r["verdict"] == "버림"]
    layers = Counter(row["layer"] for row in kept)

    out = [
        f"# 검수 반영 — {len(rows)}건 → {len(kept)}건",
        "",
        "`test.jsonl` 은 그대로 두고 `test_reviewed.jsonl` 을 새로 만들었다. "
        "재현하려면 `python src/apply_review.py`.",
        "",
        "| 판정 | 건수 |", "| --- | --- |",
        *(f"| {k} | {counts[k]}건 |" for k in ("맞음", "라벨수정", "버림")),
        "",
        "| 층 | 남은 건수 |", "| --- | --- |",
        *(f"| `{k}` | {layers[k]}건 |" for k in sorted(layers)),
        "",
        f"## 라벨을 고친 {len(changes)}건",
        "",
        "| id | 바뀐 값 | 사유 | 결정자 |", "| --- | --- | --- | --- |",
    ]
    for sample_id, before, after, review in changes:
        diff = " · ".join(f"`{k}` {show(before[k])} → {show(after[k])}" for k in after)
        out.append(f"| `{sample_id}` | {diff} | {review['reason']} | {review['decider']} |")

    out += ["", f"## 버린 {len(dropped)}건", "",
            "| id | 사유 | 결정자 |", "| --- | --- | --- |"]
    for sample_id, review in sorted(dropped):
        out.append(f"| `{sample_id}` | {review['reason']} | {review['decider']} |")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="data")
    parser.add_argument("--out", default="data/test_reviewed.jsonl")
    parser.add_argument("--log", default="data/review_applied.md")
    parser.add_argument("--check", action="store_true", help="쓰지 않고 검증만")
    args = parser.parse_args()

    base = Path(args.dir)
    rows = load_jsonl(base / "test.jsonl")
    reviews = load_reviews(base)
    check(rows, reviews)

    kept, changes = apply(rows, reviews)
    counts = Counter(r["verdict"] for r in reviews.values())
    print(f"{len(rows)}건 → {len(kept)}건 "
          f"(맞음 {counts['맞음']} · 라벨수정 {counts['라벨수정']} · 버림 {counts['버림']})")
    if args.check:
        return

    Path(args.out).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept),
        encoding="utf-8")
    Path(args.log).write_text(log(rows, kept, reviews, changes), encoding="utf-8")
    print(f"시험지 → {args.out}\n반영 로그 → {args.log}")


if __name__ == "__main__":
    main()
