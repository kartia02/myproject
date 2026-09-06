# 정답 Tool Call을 코드로 먼저 균등 샘플링한다 — 역방향 생성의 앞단 (결정 3)

"""GPT는 여기서 나온 시드를 받아 발화만 쓴다. 정답은 이 파일이 확정한다.

역방향으로 도는 이유가 둘이다 (결정 3).

1. 파라미터 조합이 구조적으로 고르게 퍼진다 — GPT에게 맡기면 흔한 조합만 나온다
2. 정답이 먼저 확정돼 있어 **틀릴 여지가 없다**

출력은 발화가 아니라 시드다. 시드 하나가 나중에 학습 샘플 하나가 된다.

    {"id", "layer", "label", "hint"}

``label`` 이 그대로 정답이고, ``hint`` 는 발화를 쓸 때 GPT에게 넘길 지시다.
``hint`` 는 라벨에 영향을 주지 않는다 — 페르소나·반려동물 이름·혼동 상대는
발화의 겉모습만 바꾼다.

경로 — ``src`` 를 import 경로에 넣고 쓴다.
"""

import random
from collections import Counter

import lexicon as L
import tools as T

# --- 유형 비중 (CLAUDE.md 데이터셋 구성 · 합계 100%) -----------------------

LAYER_RATIO = {
    "simple": 0.22,        # 단순 1툴
    "multi": 0.28,         # 파라미터 다중
    "confusion": 0.28,     # 어휘 미스매치·혼동 쌍
    "tense": 0.10,         # 시제·맥락 판별
    "out_of_scope": 0.07,
    "ambiguous": 0.05,
}

# 처리 순서 — 툴이 고정된 층을 먼저 돌린다.
# confusion 은 혼동 쌍이, tense 는 축③이 툴을 정해버려 균등화 여지가 없다.
# 자유로운 simple·multi 를 뒤에 두어야 _pick_tool 이 부족한 툴을 메울 수 있다.
# 순서를 뒤집으면 툴 편차가 3배 넘게 벌어진다 (실측).
LAYER_ORDER = ["confusion", "tense", "out_of_scope", "ambiguous", "simple", "multi"]

# --- 혼동 쌍 ---------------------------------------------------------------
# 해소된 경계 케이스에서 그대로 도출했다. 근거 결정을 함께 적어 추적 가능하게 둔다.
# (정답 툴, 오인하기 쉬운 툴, 근거)

CONFUSION_PAIRS = [
    ("log_excretion", "log_symptom", "결정 15 — 배설물 상태는 전용 칸이 있다"),
    ("log_symptom", "log_activity", "결정 15 — 활동 중 이상은 담을 칸이 없다"),
    ("log_medication", "log_care", "결정 13 — 구충제도 약이다"),
    ("log_medication", "log_meal", "결정 13 — 영양제도 약이다"),
    ("get_trend", "get_records", "결정 16 축① — 합쳐야 답이면 trend"),
    ("get_vet_summary", "get_records", "결정 16 축② — 진료 맥락 + 종류 미지정"),
    ("get_records", "get_trend", "결정 16 축① — 나열로 답이 되면 records"),
    ("get_records", "get_vet_summary", "결정 16 축② — 종류가 특정되면 records"),
]

# --- 시제·맥락 층 ----------------------------------------------------------
# 결정 16 축③ 전용. 핵심 난이도는 "과거형인데 미래를 묻는" 쪽이므로 무게를 둔다.

TENSE_TOOLS = [("get_care_due", 0.6), ("get_records", 0.4)]

TENSE_NOTE = {
    # 지난 날짜만 묻는 말은 get_records 다. 금지를 명시하지 않으면 GPT가
    # "마지막에 맞은 게 언제였더라"로 끝내 라벨이 뒤집힌다 (30건 테스트)
    "get_care_due": (
        "겉보기 시제는 과거인데 묻는 목적은 '이제 할 때인가'인 발화로 쓴다. "
        "'한 달 됐나?', '안 밀렸나?' 처럼 마지막으로 한 뒤 얼마나 지났는지를 통해 "
        "다음 차례를 확인하는 말이다. "
        "지난 날짜만 묻는 말은 쓰지 마라 — '마지막에 한 게 언제였지', "
        "'언제 했더라'로 끝나면 지난 기록을 묻는 말이 되어 실패다. "
        "다음 차례를 신경 쓰고 있다는 것이 드러나야 한다"
    ),
    "get_records": (
        "묻는 목적이 '있었던 일'인 발화로 쓴다. 언제 했는지·했는지 안 했는지를 "
        "확인할 뿐 다음 차례를 묻지 않는다"
    ),
}

# --- 파라미터 값 풀 --------------------------------------------------------
# enum 은 tools.py 에서 온다. 여기는 열린 집합과 시간만 매핑한다.

FREE_POOLS = {
    ("log_meal", "food"): L.FOOD,
    ("log_meal", "amount"): L.MEAL_AMOUNT,
    ("log_water", "amount"): L.WATER_AMOUNT,
    ("log_medication", "name"): L.MEDICATION_NAME,
    ("log_medication", "dose"): L.MEDICATION_DOSE,
    ("log_symptom", "symptom"): L.SYMPTOM,
    ("log_activity", "duration"): L.ACTIVITY_DURATION,
    ("log_weight", "weight"): L.WEIGHT,
}

# 시간 파라미터가 어떤 종류의 표현을 받는가.
# log_* 는 시점, get_records 는 구간, get_trend 는 기간 (결정 16 축①의 근거이기도 하다)
TIME_POOLS = {
    ("log_weight", "date"): ("relative_day", "relative_week", "weekday"),
    ("get_records", "since"): ("relative_day", "relative_week", "weekday", "period"),
    ("get_records", "until"): ("relative_day", "weekday"),
    ("get_trend", "period"): ("period",),
    ("get_vet_summary", "since"): ("relative_day", "relative_week", "period"),
}
DEFAULT_TIME_KINDS = ("time_of_day", "clock", "relative_day")

# caregiver 슬롯을 가진 툴에서 이 확률로 채운다.
# 슬롯 보유 툴이 12개 중 5개라 전체 비중은 약 20%가 된다 (CLAUDE.md).
# 실제 비율은 summarize() 로 확인하고 조정한다.
CAREGIVER_FILL_RATE = 0.53

# 조회계에서 파라미터가 전부 null 인 "전체 조회" 발화의 비율.
# 유효한 발화이지만("오늘 뭐 했지?", "뭐 챙길 거 있어?") 제한하지 않으면
# get_care_due 167건 중 78건이 같은 말이 된다 (실측).
ALL_NULL_RATE = 0.15

# 툴을 식별하는 칸. 필수 파라미터가 없는 기록계에서 최소 한 칸을 채울 때 이쪽을 먼저 쓴다.
# log_meal 에서 amount 만 차면 "반만 줬어"가 되어 밥·물·약을 가릴 수 없다.
IDENTIFYING_PARAM = {"log_meal": "food", "log_water": "amount"}

# 조회계와 거절 층에서만 쓰는 페르소나.
# 기록계에 붙으면 "배를 자꾸 핥아?" 처럼 기록이 질문으로 바뀌어 라벨과 어긋난다.
QUERY_ONLY_PERSONAS = {"질문형"}


def _pool(tool, param):
    """파라미터 하나가 가질 수 있는 값 목록."""
    if param["kind"] == "enum":
        return T.enum_values(param["enum"])
    if param["kind"] == "time":
        kinds = TIME_POOLS.get((tool, param["name"]), DEFAULT_TIME_KINDS)
        return L.time_expressions(*kinds)
    if param["name"] == "caregiver":
        return L.CAREGIVER
    return FREE_POOLS[(tool, param["name"])]


def _fill(tool, n_optional, rng):
    """필수 파라미터를 채우고 선택 파라미터를 n_optional 개 더 채운다."""
    args = T.empty_arguments(tool)
    params = T.TOOLS[tool]["params"]

    required = [p for p in params if p["required"]]
    optional = [p for p in params if not p["required"]]

    # caregiver 는 개수 배정과 무관하게 별도 확률로 정한다.
    # 전체의 약 20%라는 목표가 층별 파라미터 개수와 섞이면 맞출 수 없기 때문이다.
    caregiver = next((p for p in optional if p["name"] == "caregiver"), None)
    if caregiver:
        optional.remove(caregiver)
        if rng.random() < CAREGIVER_FILL_RATE:
            args["caregiver"] = rng.choice(_pool(tool, caregiver))

    for p in required:
        args[p["name"]] = rng.choice(_pool(tool, p))

    rng.shuffle(optional)
    for p in optional[:n_optional]:
        args[p["name"]] = rng.choice(_pool(tool, p))

    # 빈 라벨 처리.
    # 기록계는 항상 한 칸을 채운다 — 전부 null 이면 GPT가 쓸 발화가 없다.
    # 조회계는 전부 null 도 유효하지만 ALL_NULL_RATE 만큼만 남긴다.
    if not any(v is not None for k, v in args.items() if k != "caregiver"):
        if tool.startswith("log_") or rng.random() > ALL_NULL_RATE:
            pool = [q for q in optional if q["name"] != "caregiver"]
            wanted = IDENTIFYING_PARAM.get(tool)
            p = next((q for q in pool if q["name"] == wanted), None) or rng.choice(pool)
            args[p["name"]] = rng.choice(_pool(tool, p))

    # until 은 since 없이 혼자 서지 못한다 — "토요일 아침까지"만 있는 발화는
    # 실제로 하지 않는 말이라 결정 17에 걸린다.
    # 빈 라벨 보정이 until 을 단독으로 고를 수 있으므로 그 뒤에 둔다.
    if args.get("until") and not args.get("since"):
        since = next(p for p in params if p["name"] == "since")
        args["since"] = rng.choice(_pool(tool, since))

    return args


def _pick_persona(tool, rng):
    names = [p["name"] for p in L.PERSONAS]
    if tool and tool.startswith("log_"):
        names = [n for n in names if n not in QUERY_ONLY_PERSONAS]
    return rng.choice(names)


def _pick_tool(counts, candidates, rng):
    """가장 적게 쓰인 툴을 고른다 — 툴당 최소 100건(checklist Day 2)을 구조적으로 보장."""
    fewest = min(counts[t] for t in candidates)
    return rng.choice([t for t in candidates if counts[t] == fewest])


def _label(tool=None, args=None, reason=None):
    """직렬화 규칙(CLAUDE.md) — 키 순서 tool → arguments → reason. 거절 시 arguments 는 {}."""
    return {"tool": tool, "arguments": args if args is not None else {}, "reason": reason}


def _counts_by_layer(n):
    """비중을 건수로 바꾼다. 반올림 오차는 가장 큰 층이 흡수한다."""
    counts = {k: int(n * r) for k, r in LAYER_RATIO.items()}
    biggest = max(LAYER_RATIO, key=LAYER_RATIO.get)
    counts[biggest] += n - sum(counts.values())
    return counts


def sample(n, seed=0):
    """시드 n개를 만든다. 같은 seed 면 같은 결과가 나온다."""
    rng = random.Random(seed)
    tool_counts = Counter({t: 0 for t in T.tool_names()})
    all_tools = T.tool_names()
    seeds = []

    by_layer = _counts_by_layer(n)
    for layer in LAYER_ORDER:
        for _ in range(by_layer[layer]):
            tool, extra = None, {}

            if layer in T.REASONS:  # out_of_scope · ambiguous
                pool = (L.OUT_OF_SCOPE_SEEDS if layer == "out_of_scope"
                        else L.AMBIGUOUS_SEEDS)
                s = rng.choice(pool)
                extra = {"kind": s["kind"], "note": s["note"]}
                label = _label(reason=layer)

            elif layer == "confusion":
                tool, other, why = rng.choice(CONFUSION_PAIRS)
                # 툴 이름은 구조화된 채로 둔다. GPT에게 보여줄 한국어 문장은
                # generate.py 가 만든다 — GPT는 툴 이름을 모르고, 알 필요도 없다.
                # why 는 프롬프트에 넣지 않는다. Day 4의 혼동 쌍별 오답률 분석용이다.
                extra = {"confuse_with": other, "why": why}
                label = _label(tool, _fill(tool, rng.randint(0, 2), rng))

            elif layer == "tense":
                tool = rng.choices(
                    [t for t, _ in TENSE_TOOLS], [w for _, w in TENSE_TOOLS]
                )[0]
                extra = {"note": TENSE_NOTE[tool]}
                label = _label(tool, _fill(tool, rng.randint(0, 1), rng))

            else:  # simple · multi
                tool = _pick_tool(tool_counts, all_tools, rng)
                n_opt = rng.randint(0, 1) if layer == "simple" else 3
                label = _label(tool, _fill(tool, n_opt, rng))

            if tool:
                tool_counts[tool] += 1

            # 페르소나는 툴이 정해진 뒤에 고른다 — 기록계에 질문형이 붙으면 안 된다
            seeds.append({
                "id": f"{len(seeds):04d}",
                "layer": layer,
                "label": label,
                "hint": {
                    "persona": _pick_persona(tool, rng),
                    "pet": (rng.choice(L.PET_NAMES + L.PET_NICKNAMES)
                            if rng.random() < 0.5 else None),
                    **extra,
                },
            })

    rng.shuffle(seeds)
    return seeds


# --- 분포 확인 -------------------------------------------------------------

def summarize(seeds):
    """생성 전에 분포를 눈으로 본다. 여기서 치우쳐 있으면 GPT를 부를 필요가 없다."""
    layers = Counter(s["layer"] for s in seeds)
    tools_ = Counter(s["label"]["tool"] for s in seeds if s["label"]["tool"])
    filled = Counter()
    caregiver_slots = caregiver_filled = 0

    for s in seeds:
        for k, v in s["label"]["arguments"].items():
            if k == "caregiver":
                caregiver_slots += 1
                caregiver_filled += v is not None
            if v is not None:
                filled[k] += 1

    return {
        "총": len(seeds),
        "층": dict(layers),
        "툴": dict(tools_.most_common()),
        "툴_최소": min(tools_.values()) if tools_ else 0,
        "caregiver_전체비율": round(caregiver_filled / len(seeds), 3),
        "caregiver_슬롯대비": round(caregiver_filled / caregiver_slots, 3) if caregiver_slots else 0,
        "파라미터별_채움": dict(filled.most_common()),
    }


if __name__ == "__main__":
    import json

    result = summarize(sample(2400, seed=0))
    print(json.dumps(result, ensure_ascii=False, indent=2))
