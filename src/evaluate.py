# 모델 출력을 정답과 대조해 7분류 오답 분해표를 낸다 — CLAUDE.md 채점 규칙의 구현

"""PawNote Tool Call 평가기.

모델 출력(JSON 문자열)과 데이터셋 행을 비교해 CLAUDE.md의 7분류로 판정한다.

**채점 규칙은 CLAUDE.md가 단일 원본이다.** 여기서 규칙을 새로 만들지 않는다.
규칙에 없어 판단이 필요했던 자리는 셋이고, 전부 주석으로 근거를 남긴다.

- 조사만 다른 값은 **오답이되 따로 집계**한다. 규칙이 "조사만 다른 *오답*" 이라고
  적었으므로 정답으로 완화하지 않는다
- 거절은 맞고 `reason` 만 틀린 것은 **파라미터 오류**다. 모델이 거절 자체는 했으므로
  "놓친 거절"(툴 없는데 호출)이 아니다. 7분류를 늘리지 않으면서 실제 상태를 담는다
- 빈 문자열은 `null` 과 다르다. 미언급은 `null` 이라고 스키마가 못 박았으므로
  "안 채운 것"과 "빈 값을 채운 것"을 섞지 않는다

사용법
    python src/evaluate.py --gold data/test.jsonl --pred data/gpt41_predictions.jsonl

예측 파일은 행마다 ``{"id": "...", "output": "모델의 원문 출력"}`` 형식이다.
``output`` 대신 ``prediction`` 또는 ``text`` 키를 써도 된다.
"""

import argparse
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import tools as T


CATEGORIES = (
    "exact", "parameter_error", "wrong_tool", "tool_hallucination",
    "schema_violation", "parse_failure", "over_refusal", "missed_refusal",
)


def normalize(value):
    """표층 값 비교 규칙: NFKC·소문자·모든 공백 제거만 적용한다."""
    return "" if value is None else "".join(
        unicodedata.normalize("NFKC", str(value)).lower().split()
    )


def same_value(predicted, expected):
    """표층 값이 같은가. **`None` 과 빈 문자열은 다르다.**

    `normalize(None)` 이 `""` 라서 그냥 비교하면 모델이 `""` 를 뱉었을 때
    미언급으로 통과한다. 미언급은 `null` 이라고 스키마에 못 박았으므로 구분한다.
    """
    if (predicted is None) != (expected is None):
        return False
    return normalize(predicted) == normalize(expected)


def is_fenced(text):
    """출력을 코드펜스로 감쌌는가. 채점에는 쓰지 않고 별도 지표로만 기록한다.

    본문 아무 데나 백틱이 있는 것과 **감싼 것**은 다르므로 시작 위치로 판정한다.
    """
    return str(text).strip().startswith("```")


def extract_object(text):
    """첫 `{` 부터 짝이 맞는 `}` 까지를 꺼낸다. 코드펜스로 감싼 출력도 통과한다."""
    text = str(text).strip()
    start = text.find("{")
    if start < 0:
        raise ValueError("JSON object not found")

    depth, quoted, escaped = 0, False, False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:index + 1])
    raise ValueError("unclosed JSON object")


def schema_error(obj):
    """고정 스키마 위반이면 사유를, 통과하면 None을 돌려준다."""
    if not isinstance(obj, dict) or set(obj) != {"tool", "arguments", "reason"}:
        return "top_level_keys"
    if not isinstance(obj["arguments"], dict):
        return "arguments_type"
    if obj["tool"] is not None and not isinstance(obj["tool"], str):
        return "tool_type"
    if obj["reason"] is not None and not isinstance(obj["reason"], str):
        return "reason_type"

    if obj["tool"] is None:
        if obj["arguments"] != {} or obj["reason"] not in T.REASONS:
            return "refusal_shape"
        return None

    # `called_tool_has_reason` 은 여기서 보지 않는다 — 툴 환각 판정보다 뒤여야 해서
    # grade() 로 옮겼다. 규칙의 판정 순서가 ② 스키마 → ③ 툴 환각이기 때문이다.
    if obj["tool"] in T.TOOLS:
        expected = set(T.param_names(obj["tool"]))
        if set(obj["arguments"]) != expected:
            return "argument_keys"
    return None


def has_only_particle_difference(predicted, expected):
    """조사만 붙은 차이를 부가 지표로 센다. 정답 처리로 완화하지는 않는다."""
    particles = ("은", "는", "이", "가", "을", "를", "에", "도", "만", "과", "와", "의", "에게", "한테")
    p, e = normalize(predicted), normalize(expected)
    return any(p == e + particle or e == p + particle for particle in particles)


def grade(gold, raw_output):
    """한 예측을 채점한다. 반환값에는 분류·세부 사유·코드펜스 여부가 담긴다."""
    expected = gold["label"]
    fenced = is_fenced(raw_output)

    def verdict(category, detail=None, **extra):
        return {"category": category, "detail": detail, "fenced": fenced, **extra}

    # ① 파싱
    try:
        predicted = extract_object(raw_output)
    except (ValueError, json.JSONDecodeError) as error:
        return verdict("parse_failure", str(error))

    # ② 최상위 키·타입
    if issue := schema_error(predicted):
        return verdict("schema_violation", issue)

    # ③ 툴 환각
    tool = predicted["tool"]
    if tool is not None and tool not in T.TOOLS:
        return verdict("tool_hallucination", tool)

    # 툴을 부르면서 reason 까지 채운 출력. 규칙의 판정 순서에는 없지만
    # 그냥 두면 `{"tool":"log_meal", ..., "reason":"ambiguous"}` 가 완전 일치로
    # 통과한다. 스키마가 스스로 모순된 것이므로 스키마 위반으로 본다.
    if tool is not None and predicted["reason"] is not None:
        return verdict("schema_violation", "called_tool_has_reason")

    # 거절 판정
    if expected["tool"] is None:
        if tool is not None:
            return verdict("missed_refusal", tool)
        if predicted["reason"] != expected["reason"]:
            # 거절은 했고 사유만 틀렸다. 툴은 맞고 값이 틀린 것과 성격이 같다
            return verdict("parameter_error",
                           f"reason: {predicted['reason']} != {expected['reason']}")
        return verdict("exact")

    if tool is None:
        return verdict("over_refusal", predicted["reason"])
    if tool != expected["tool"]:
        return verdict("wrong_tool", f"{tool} != {expected['tool']}")

    # ⑤ enum 허용값 → ⑥ 값 비교
    mismatched = []
    for param, expected_value in expected["arguments"].items():
        predicted_value = predicted["arguments"][param]
        spec = next(p for p in T.TOOLS[tool]["params"] if p["name"] == param)
        if spec["kind"] == "enum" and predicted_value not in (None, *T.enum_values(spec["enum"])):
            return verdict("parameter_error", f"{param}: invalid enum")
        if not same_value(predicted_value, expected_value):
            mismatched.append(param)

    if not mismatched:
        return verdict("exact")

    # 조사만 다른 것도 오답이다. 정답으로 완화하지 않고 별도 지표로만 센다
    particle_only = all(
        has_only_particle_difference(predicted["arguments"][p], expected["arguments"][p])
        for p in mismatched
    )
    return verdict("parameter_error", ",".join(mismatched), particle_only=particle_only)


def load_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def self_test():
    """분류 우선순위가 바뀌지 않았는지 확인하는 의존성 없는 회귀 검사."""
    gold = {
        "label": {"tool": "log_meal", "arguments": {
            "food": "사료", "amount": "반 그릇", "time": "아침", "caregiver": None,
        }, "reason": None},
    }
    refusal = {"label": {"tool": None, "arguments": {}, "reason": "out_of_scope"}}
    meal = '{"tool":"log_meal","arguments":{"food":%s,"amount":"반 그릇","time":"아침","caregiver":%s},"reason":null}'
    cases = [
        (gold, meal % ('"사료"', "null"), "exact"),
        (gold, '```json\n' + meal % ('"사료"', "null") + '\n```', "exact"),
        (gold, '{"tool":"log_meal","arguments":{},"reason":null}', "schema_violation"),
        (gold, '{"tool":"made_up","arguments":{},"reason":null}', "tool_hallucination"),
        (gold, '{"tool":null,"arguments":{},"reason":"ambiguous"}', "over_refusal"),
        (gold, "not json", "parse_failure"),
        # 아래 넷은 규칙에 없어 판단이 필요했던 자리다. 되돌아가지 않도록 못을 박는다
        (gold, meal % ('"사료를"', "null"), "parameter_error"),        # 조사만 달라도 오답
        (gold, meal % ('"사료"', '""'), "parameter_error"),            # 빈 문자열 != null
        (gold, '{"tool":"log_food","arguments":{},"reason":"ambiguous"}', "tool_hallucination"),
        (refusal, '{"tool":null,"arguments":{},"reason":"ambiguous"}', "parameter_error"),
        (refusal, '{"tool":null,"arguments":{},"reason":"out_of_scope"}', "exact"),
        (refusal, meal % ('"사료"', "null"), "missed_refusal"),
    ]
    for row, output, expected in cases:
        actual = grade(row, output)["category"]
        if actual != expected:
            raise AssertionError(f"{expected} expected, got {actual}: {output}")

    assert grade(gold, meal % ('"사료를"', "null"))["particle_only"] is True
    assert grade(gold, meal % ('"간식"', "null"))["particle_only"] is False
    assert is_fenced("```json\n{}\n```") and not is_fenced('{"a":"```"}')
    print(f"self-test passed ({len(cases)} cases)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", help="정답 데이터셋 JSONL")
    parser.add_argument("--pred", help="모델 원문 출력 JSONL")
    parser.add_argument("--details", help="건별 채점 결과를 JSONL로 저장")
    parser.add_argument("--subset", action="store_true",
                        help="검수에서 버린 건이 있어 시험지가 예측보다 적은 경우")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return
    if not args.gold or not args.pred:
        parser.error("--gold와 --pred가 필요합니다 (--self-test 제외)")

    gold = {row["id"]: row for row in load_jsonl(args.gold)}

    # 키가 없으면 None → "None" → 파싱 실패로 조용히 집계된다.
    # 파일 형식 실수가 모델 결함으로 둔갑하므로 여기서 끊는다.
    predictions = {}
    for row in load_jsonl(args.pred):
        text = next((row[k] for k in ("output", "prediction", "text") if k in row), None)
        if text is None:
            raise SystemExit(f"예측 {row.get('id')} — output·prediction·text 키가 없다")
        predictions[row["id"]] = text

    # 누락은 언제나 오류다 — 안 푼 문제를 0점이 아니라 없는 문제로 세면 안 된다.
    # 남는 예측은 검수에서 버린 건일 수 있으므로 `--subset` 일 때만 허용하고,
    # 그 경우에도 몇 건이 빠졌는지 찍는다. 조용히 줄어드는 것이 제일 나쁘다.
    missing = set(gold) - set(predictions)
    extra = set(predictions) - set(gold)
    if missing or (extra and not args.subset):
        raise SystemExit(f"id 불일치 — 누락 {len(missing)}건 · 추가 {len(extra)}건")
    if extra:
        print(f"시험지에 없는 예측 {len(extra)}건은 채점에서 뺀다 (--subset)")

    results, counts = [], Counter()
    by_layer, by_tool = defaultdict(Counter), defaultdict(Counter)
    particle_only = 0
    for sample_id, row in gold.items():
        result = grade(row, predictions[sample_id])
        result["id"], result["layer"] = sample_id, row["layer"]
        counts[result["category"]] += 1
        by_layer[row["layer"]][result["category"]] += 1
        tool_group = row["label"]["tool"] or row["label"]["reason"]
        by_tool[tool_group][result["category"]] += 1
        particle_only += bool(result.get("particle_only"))
        results.append(result)

    total = len(results) or 1
    print(f"총 {len(results)}건 · 완전 일치 {counts['exact'] / total:.1%}")
    for category in CATEGORIES:
        print(f"  {category:18s} {counts[category]:3d} ({counts[category] / total:.1%})")
    print(f"코드펜스 사용 {sum(r['fenced'] for r in results)}건 · "
          f"조사만 다른 오답 {particle_only}건 (파라미터 오류에 포함)")
    print("층별 완전 일치:")
    for layer in sorted(by_layer):
        layer_total = sum(by_layer[layer].values())
        print(f"  {layer:14s} {by_layer[layer]['exact']}/{layer_total} ({by_layer[layer]['exact'] / layer_total:.1%})")
    print("툴별 완전 일치:")
    for tool in sorted(by_tool):
        tool_total = sum(by_tool[tool].values())
        print(f"  {tool:14s} {by_tool[tool]['exact']}/{tool_total} ({by_tool[tool]['exact'] / tool_total:.1%})")

    if args.details:
        with open(args.details, "w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
