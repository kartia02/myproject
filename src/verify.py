# 표층 라벨이 발화 안에 실제로 있는지 검사하고 어긋나면 라벨을 고친다 (결정 14)

"""역방향 생성은 정답을 먼저 확정하므로 **라벨이 틀릴 일은 없다.**
그러나 **라벨과 발화가 어긋날 수는 있다.** 그게 결정 3의 사각지대였다.

    샘플링된 정답   time="아침",  amount="반 그릇"
    GPT 생성 발화   "콩이 오전에 사료 절반 정도 줬어"

모델이 발화대로 `"오전"`·`"절반 정도"` 를 출력하면 **정답 동작인데 오답으로 채점된다.**
완전 일치율이 이유 없이 깎이고 7분류표의 "파라미터 오류" 칸이 오염된다.

세 단계로 처리한다.

1. 라벨 값이 발화 안에 있으면 통과
2. 없으면 **같은 슬롯의 값 풀** 안에서 발화에 등장하는 값을 찾아 **라벨을 고친다**
   — 발화를 다시 만들지 않는 이유는 발화의 자연스러움이 이 데이터셋의 자산이기 때문이다
3. 그것도 없으면 **버린다**

같은 슬롯의 값 풀로 범위를 좁히는 것이 핵심이다. 발화 아무 데서나 표현을 주워오면
`time` 칸에 음식 이름이 들어가는 사고가 난다.

비교는 채점기(CLAUDE.md 채점 규칙)와 **같은 정규화**를 쓴다. 여기서 통과한 것이
채점에서 틀리면 안 되기 때문이다.
"""

import unicodedata
from collections import Counter

import sampler as S
import tools as T


def norm(s):
    """채점 규칙과 동일한 정규화 — 공백 제거 · 전각→반각 · 소문자화.

    조사는 떼지 않는다. 부분 문자열로 검사하므로 `"아침에"` 안의 `"아침"` 은 걸린다.
    """
    return unicodedata.normalize("NFKC", str(s)).replace(" ", "").lower()


def _spec(tool, param):
    return next(p for p in T.TOOLS[tool]["params"] if p["name"] == param)


def _candidates(tool, param):
    """이 슬롯이 가질 수 있는 값과, 그 값을 발화에서 찾을 때 쓸 표층 표현."""
    spec = _spec(tool, param)
    if spec["kind"] == "enum":
        # enum 은 영문 키라 발화에 그대로 나오지 않는다. 표층 어휘로 찾는다
        return {k: v for k, v in T.ENUMS[spec["enum"]].items()}
    return {v: [v] for v in S._pool(tool, spec)}


def check(sample):
    """발화가 붙은 시드 하나를 검사한다.

    반환 — (판정, 고쳐진 시드 또는 None, 고친 내역)
    판정은 "ok" · "realigned" · "dropped" 중 하나다.
    """
    said = norm(sample["utterance"])
    label = sample["label"]
    if label["tool"] is None:
        return "ok", sample, {}  # 거절 층은 담을 값이 없다

    args = dict(label["arguments"])
    fixes = {}

    for param, value in label["arguments"].items():
        if value is None:
            continue
        cands = _candidates(label["tool"], param)

        # 1) 라벨대로 들어있나
        if any(norm(s) in said for s in cands.get(value, [value])):
            continue

        # 2) 같은 슬롯의 다른 값이 들어있나 → 라벨을 고친다
        #
        # 한 글자짜리 후보는 쓰지 않는다. `"다"` 같은 값은 `"줬다"`·`"먹었다"` 에
        # 걸려 아무 발화에나 매칭되고, 그 결과 엉뚱한 라벨로 바뀐다.
        hit = [k for k, surfaces in cands.items()
               if k != value and any(len(norm(s)) > 1 and norm(s) in said
                                     for s in surfaces)]
        if len(hit) == 1:
            args[param] = hit[0]
            fixes[param] = (value, hit[0])
            continue

        # 3) 특정 불가 — 버린다
        return "dropped", None, {param: (value, None)}

    if not fixes:
        return "ok", sample, {}
    return "realigned", {**sample, "label": {**label, "arguments": args}}, fixes


def verify(samples, verbose=True):
    """배치 전체를 검사하고 통계를 낸다.

    재정렬률·폐기율이 높으면 **생성 프롬프트가 라벨을 무시하고 있다는 신호**다.
    데이터를 더 뽑기 전에 프롬프트부터 고친다.
    """
    kept, stats, dropped_params, fixed_params = [], Counter(), Counter(), Counter()

    for s in samples:
        verdict, fixed, fixes = check(s)
        stats[verdict] += 1
        if verdict == "dropped":
            dropped_params[next(iter(fixes))] += 1
        else:
            kept.append(fixed)
            fixed_params.update(fixes)

    n = len(samples) or 1
    if verbose:
        print(f"검사 {len(samples)}건 — 통과 {stats['ok']} · "
              f"재정렬 {stats['realigned']} ({stats['realigned'] / n:.1%}) · "
              f"폐기 {stats['dropped']} ({stats['dropped'] / n:.1%})")
        if fixed_params:
            print(f"  재정렬된 슬롯 — {dict(fixed_params.most_common())}")
        if dropped_params:
            print(f"  폐기 원인 슬롯 — {dict(dropped_params.most_common())}")

    return kept, stats


if __name__ == "__main__":
    # 자기 검사 — 발화를 손으로 만들어 세 갈래가 다 나오는지 본다
    seed = {
        "id": "test", "layer": "simple",
        "label": {"tool": "log_meal",
                  "arguments": {"food": "사료", "amount": "반 그릇",
                                "time": "아침", "caregiver": None},
                  "reason": None},
        "hint": {},
    }
    cases = [
        ("아침에 사료 반 그릇 줬어", "ok"),
        ("저녁에 사료 반그릇 줬어", "realigned"),    # time 아침 → 저녁
        ("아침에 사료 절반 정도 줬어", "realigned"),  # amount 반 그릇 → 절반
        ("아침에 사료 쬐끔 줬어", "dropped"),         # 값 풀에 없는 표현
    ]
    for utterance, expect in cases:
        verdict, _, fixes = check({**seed, "utterance": utterance})
        mark = "○" if verdict == expect else "✗"
        print(f"{mark} {verdict:10s} {utterance}  {fixes}")
