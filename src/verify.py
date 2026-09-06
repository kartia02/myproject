# 표층 라벨이 발화 안에 실제로 있는지 검사하고 어긋나면 라벨을 고친다 (결정 14)

"""역방향 생성은 정답을 먼저 확정하므로 **라벨이 틀릴 일은 없다.**
그러나 **라벨과 발화가 어긋날 수는 있다.** 그게 결정 3의 사각지대였다.

    샘플링된 정답   time="아침",  amount="반 그릇"
    GPT 생성 발화   "콩이 오전에 사료 절반 정도 줬어"

모델이 발화대로 `"오전"`·`"절반 정도"` 를 출력하면 **정답 동작인데 오답으로 채점된다.**
완전 일치율이 이유 없이 깎이고 7분류표의 "파라미터 오류" 칸이 오염된다.

**두 방향을 모두 본다.**

정방향 — 라벨에 있는 값이 발화에 있는가

1. 라벨 값이 발화 안에 있으면 통과
2. 없으면 **같은 슬롯의 값 풀** 안에서 발화에 등장하는 값을 찾아 **라벨을 고친다**
   — 발화를 다시 만들지 않는 이유는 발화의 자연스러움이 이 데이터셋의 자산이기 때문이다
3. 그것도 없으면 **버린다**

역방향 — 발화에 있는 값이 라벨에 빠졌는가 (30건 테스트에서 발견한 구멍)

    발화  "응가 상태가 좀 묽었던 것 같은데"
    라벨  log_excretion(type="feces")        ← condition 이 비어 있다

**정방향만 보면 이것을 통과시킨다.** 라벨에 있는 값은 전부 발화에 있기 때문이다.
그러면 "말했는데 정답에는 없는" 데이터가 학습에 들어가고, 모델이 그 칸을 언제
채우는지 배우지 못한다. 평가에서는 모델이 맞게 뽑아도 오답이 된다.

그래서 **`null` 인 칸도 발화를 훑어 값이 있으면 채운다.**

**한계** — 값 풀의 표층 어휘와 정확히 겹칠 때만 잡힌다. `"묽었던"` 은 시드에 있는
`"묽게"`·`"무름"` 어느 쪽과도 문자열이 겹치지 않아 못 잡는다. 그래서 1차 방어는
생성 프롬프트가 맡고(없는 정보를 덧붙이지 말 것) 여기는 2차 그물이다.

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


def _hits(cands, said, exclude=None):
    """발화에 등장하는 후보 값들.

    한 글자짜리 후보는 쓰지 않는다. `"다"` 같은 값은 `"줬다"`·`"먹었다"` 에 걸려
    아무 발화에나 매칭되고, 그 결과 엉뚱한 라벨이 만들어진다.
    """
    return [k for k, surfaces in cands.items()
            if k != exclude and any(len(norm(s)) > 1 and norm(s) in said
                                    for s in surfaces)]


def _longest(cands, hit):
    """후보가 여럿이면 가장 긴 표층 표현을 가진 것을 고른다.

    `"오늘 아침에 줬어"` 는 `"오늘"`·`"오늘 아침"`·`"아침"` 이 모두 걸린다.
    사람이 라벨을 붙인다면 가장 구체적인 `"오늘 아침"` 을 고른다.
    길이가 같은 것이 둘 이상이면 판단을 포기한다.
    """
    scored = [(max(len(norm(s)) for s in cands[k]), k) for k in hit]
    scored.sort(reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def check(sample):
    """발화가 붙은 시드 하나를 검사한다.

    반환 — (판정, 고쳐진 시드 또는 None, 고친 내역)
    판정은 "ok" · "realigned" · "dropped" 중 하나다.
    고친 내역의 값은 ``(이전, 이후)`` 이고, 이전이 ``None`` 이면 역방향으로 채운 것이다.
    """
    said = norm(sample["utterance"])
    label = sample["label"]
    if label["tool"] is None:
        return "ok", sample, {}  # 거절 층은 담을 값이 없다

    args = dict(label["arguments"])
    fixes = {}

    for param, value in label["arguments"].items():
        cands = _candidates(label["tool"], param)

        # --- 역방향 — 빈 칸인데 발화에 값이 있는가 ---
        if value is None:
            hit = _hits(cands, said)
            if hit and (pick := _longest(cands, hit)):
                args[param] = pick
                fixes[param] = (None, pick)
            continue

        # --- 정방향 1) 라벨대로 들어있나 ---
        if any(norm(s) in said for s in cands.get(value, [value])):
            continue

        # --- 정방향 2) 같은 슬롯의 다른 값이 들어있나 → 라벨을 고친다 ---
        hit = _hits(cands, said, exclude=value)
        if len(hit) == 1:
            args[param] = hit[0]
            fixes[param] = (value, hit[0])
            continue

        # --- 정방향 3) 특정 불가 — 버린다 ---
        return "dropped", None, {param: (value, None)}

    if not fixes:
        return "ok", sample, {}
    return "realigned", {**sample, "label": {**label, "arguments": args}}, fixes


def verify(samples, verbose=True):
    """배치 전체를 검사하고 통계를 낸다.

    재정렬률·폐기율이 높으면 **생성 프롬프트가 라벨을 무시하고 있다는 신호**다.
    데이터를 더 뽑기 전에 프롬프트부터 고친다.
    """
    kept, stats = [], Counter()
    dropped_params, moved_params, filled_params = Counter(), Counter(), Counter()

    for s in samples:
        verdict, fixed, fixes = check(s)
        stats[verdict] += 1
        if verdict == "dropped":
            dropped_params[next(iter(fixes))] += 1
            continue
        kept.append(fixed)
        for param, (before, _) in fixes.items():
            # before 가 None 이면 빈 칸을 채운 것(역방향), 아니면 값을 바꾼 것(정방향)
            (filled_params if before is None else moved_params)[param] += 1

    n = len(samples) or 1
    if verbose:
        print(f"검사 {len(samples)}건 — 통과 {stats['ok']} · "
              f"수정 {stats['realigned']} ({stats['realigned'] / n:.1%}) · "
              f"폐기 {stats['dropped']} ({stats['dropped'] / n:.1%})")
        if moved_params:
            print(f"  값 교체(정방향) — {dict(moved_params.most_common())}")
        if filled_params:
            print(f"  빈 칸 채움(역방향) — {dict(filled_params.most_common())}")
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
        (seed, "아침에 사료 반 그릇 줬어", "ok"),
        (seed, "저녁에 사료 반그릇 줬어", "realigned"),     # time 아침 → 저녁
        (seed, "아침에 사료 절반 정도 줬어", "realigned"),   # amount 반 그릇 → 절반
        (seed, "아침에 사료 쬐끔 줬어", "dropped"),          # 값 풀에 없는 표현
    ]

    # 역방향 — 라벨이 비어 있는데 발화에 값이 있는 경우
    empty = {
        "id": "test2", "layer": "simple",
        "label": {"tool": "log_excretion",
                  "arguments": {"type": "feces", "condition": None, "time": None},
                  "reason": None},
        "hint": {},
    }
    cases += [
        (empty, "응가 쌌어", "ok"),                          # 채울 것이 없다
        (empty, "아침에 응가 쌌는데 설사였어", "realigned"),   # condition·time 채움
    ]

    for s, utterance, expect in cases:
        verdict, _, fixes = check({**s, "utterance": utterance})
        mark = "○" if verdict == expect else "✗"
        print(f"{mark} {verdict:10s} {utterance}  {fixes}")
