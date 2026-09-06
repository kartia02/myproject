# 툴 12종의 스펙 정의 — 데이터 생성기·채점기·베이스라인 프롬프트가 참조하는 단일 원본

"""파라미터 종류(kind)는 세 가지다.

- ``enum``   닫힌 집합. 영문으로 정규화한다. 모델이 분류를 수행하는 슬롯
- ``free``   열린 집합. 발화의 표층 표현을 그대로 담는다 (수량·명칭)
- ``time``   시간 표현. 표층 그대로 담고 ISO 변환은 앱 코드가 맡는다 (결정 9)

``free``와 ``time``은 채점 방식이 같지만, 생성기와 오답 분석에서 구분이 필요해
따로 둔다.
"""

# --- 거절 사유 ------------------------------------------------------------

REASONS = ["out_of_scope", "ambiguous"]

# --- enum 값 도메인 -------------------------------------------------------
# surface 는 그 값을 유발하는 한국어 표층 어휘. 역방향 생성의 시드로 쓰고,
# 라벨링 가이드의 판정 근거가 된다. 발화가 여기 없는 표현을 쓸 수는 있으나
# 정답 라벨은 반드시 아래 key 중 하나다.

ENUMS = {
    "excretion_type": {
        "feces": ["응가", "똥", "대변", "큰 거"],
        "urine": ["쉬", "오줌", "소변", "작은 거"],
    },
    "excretion_condition": {
        "normal": ["정상", "잘 봤어", "평소처럼"],
        "soft": ["무름", "물렁", "질척"],
        "diarrhea": ["설사", "묽게", "죽처럼"],
        "hard": ["딱딱", "된 변", "힘들어함"],
        "bloody": ["피", "혈변", "붉은 게 섞임"],
    },
    "care_type": {  # log_care — 약이 아닌 위생 관리만
        "teeth": ["양치", "이빨 닦기", "치약"],
        "nail": ["발톱", "발톱깎기", "네일"],
        "bath": ["목욕", "샤워", "씻김"],
        "anal_gland": ["항문낭", "항문낭 짜기"],
        "brushing": ["빗질", "브러싱", "털 빗기"],
        "ear": ["귀 청소", "귀 닦기", "이어클리너"],
    },
    "activity_type": {
        "walk": ["산책", "걷기", "동네 한 바퀴"],
        "play": ["놀이", "공놀이", "터그", "장난감"],
        "training": ["훈련", "교육", "앉아 연습"],
        "outing": ["외출", "카페", "애견운동장", "나들이"],
    },
    "symptom_severity": {
        "mild": ["살짝", "약간", "조금"],
        "moderate": ["꽤", "제법", "좀 심하게"],
        "severe": ["심하게", "많이", "계속"],
    },
    "record_type": {  # get_records — log_* 8종에 대응
        "meal": ["밥", "사료", "식사"],
        "water": ["물", "음수"],
        "excretion": ["배변", "응가", "화장실"],
        "medication": ["약", "투약"],
        "care": ["케어", "관리", "미용"],
        "symptom": ["증상", "아픈 거"],
        "activity": ["산책", "활동", "운동"],
        "weight": ["몸무게", "체중"],
    },
    "trend_metric": {  # 추이가 의미 있는 항목만. 주기성 항목은 get_care_due 소관
        "weight": ["몸무게", "체중"],
        "water": ["물", "음수량"],
        "meal": ["식사량", "밥 먹는 양", "식욕"],
        "activity": ["산책", "활동량", "활력"],
        "excretion": ["배변", "응가"],
        "symptom": ["증상"],
    },
    "due_care_type": {  # get_care_due — 주기가 있는 항목. 예방약은 여기서만 조회된다
        "heartworm": ["심장사상충", "심장사상충 약", "하트가드"],
        "deworming": ["구충", "구충제", "회충약"],
        "vaccine": ["예방접종", "백신", "종합백신"],
        "nail": ["발톱"],
        "bath": ["목욕"],
        "anal_gland": ["항문낭"],
        "teeth": ["양치", "스케일링"],
    },
}

# --- 툴 정의 --------------------------------------------------------------
# required=True 인 파라미터가 발화에서 확정되지 않으면 ambiguous 로 거절한다.


def _p(name, kind, *, enum=None, required=False, desc=""):
    return {"name": name, "kind": kind, "enum": enum, "required": required, "desc": desc}


TOOLS = {
    # === 기록계 ===========================================================
    "log_meal": {
        "desc": "사료·간식 등 먹은 것을 기록한다",
        "params": [
            _p("food", "free", desc="먹은 것의 이름. 사료·습식·간식·닭가슴살 등"),
            _p("amount", "free", desc="양. '반 그릇', '한 줌', '조금' 같은 모호 단위 허용"),
            _p("time", "time", desc="먹은 시각의 표층 표현"),
            _p("caregiver", "free", desc="준 사람. 미언급 시 null"),
        ],
    },
    "log_water": {
        "desc": "물 마신 것을 기록한다",
        "params": [
            _p("amount", "free", desc="양. '많이', '한 그릇', '200ml' 모두 표층 그대로"),
            _p("time", "time"),
            _p("caregiver", "free"),
        ],
    },
    "log_excretion": {
        "desc": "대소변을 기록한다",
        "params": [
            _p("type", "enum", enum="excretion_type", required=True),
            _p("condition", "enum", enum="excretion_condition", desc="상태 미언급 시 null"),
            _p("time", "time"),
        ],
    },
    "log_medication": {
        "desc": "약·영양제·구충제·예방약 투여를 기록한다. 먹이는 것이든 바르는 것이든 약이면 여기다",
        "params": [
            _p("name", "free", required=True, desc="약 이름. '심장사상충약', '구충제', '관절 영양제'"),
            _p("dose", "free", desc="용량. '한 알', '반 알', '1cc'"),
            _p("time", "time"),
            _p("caregiver", "free"),
        ],
    },
    "log_care": {
        "desc": "약이 아닌 위생 관리를 기록한다. 양치·발톱·목욕·항문낭·빗질·귀 청소",
        "params": [
            _p("care_type", "enum", enum="care_type", required=True),
            _p("time", "time"),
            _p("caregiver", "free"),
        ],
    },
    "log_symptom": {
        "desc": "증상·이상 징후를 기록한다. 원인은 판단하지 않는다",
        "params": [
            _p("symptom", "free", required=True, desc="증상의 표층 표현. '토했어', '절뚝여', '기침'"),
            _p("severity", "enum", enum="symptom_severity", desc="정도 미언급 시 null"),
            _p("time", "time"),
        ],
    },
    "log_activity": {
        "desc": "산책·놀이 등 활동을 기록한다",
        "params": [
            _p("activity_type", "enum", enum="activity_type", required=True),
            _p("duration", "free", desc="시간. '30분', '짧게', '한 시간쯤'"),
            _p("time", "time"),
        ],
    },
    "log_weight": {
        "desc": "몸무게를 기록한다",
        "params": [
            _p("weight", "free", required=True, desc="'5.2킬로', '5킬로 200' 표층 그대로"),
            _p("date", "time"),
        ],
    },
    # === 조회계 ===========================================================
    "get_records": {
        "desc": "지난 기록을 조회한다. 이미 있었던 일을 묻는 경우",
        "params": [
            _p("record_type", "enum", enum="record_type", desc="미지정 시 null = 전체"),
            _p("since", "time"),
            _p("until", "time"),
            _p("caregiver", "free"),
        ],
    },
    "get_trend": {
        "desc": "일정 기간의 변화 추이를 조회한다. 늘었는지 줄었는지를 묻는 경우",
        "params": [
            _p("metric", "enum", enum="trend_metric", required=True),
            _p("period", "time", desc="'요즘', '최근 일주일', '한 달'"),
        ],
    },
    "get_care_due": {
        "desc": "다음에 챙겨야 할 시점을 조회한다. 아직 안 한 일, 앞으로 할 일",
        "params": [
            _p("care_type", "enum", enum="due_care_type", desc="미지정 시 null = 전체"),
        ],
    },
    "get_vet_summary": {
        # "방문용"만 적었더니 GPT가 "다녀온 진료 정리"로 오해했다 (30건 테스트).
        # 이 툴은 진료 전 준비용이고, 다녀온 뒤 회고는 get_records 소관이다
        "desc": "곧 있을 병원 방문에 대비해 최근 기록을 요약한다. 다녀온 진료의 내용을 묻는 것이 아니다",
        "params": [
            _p("since", "time", desc="언제부터의 기록인지"),
        ],
    },
}


# --- 유틸 -----------------------------------------------------------------

def tool_names():
    return list(TOOLS)


def param_names(tool):
    return [p["name"] for p in TOOLS[tool]["params"]]


def enum_values(enum_key):
    return list(ENUMS[enum_key])


def empty_arguments(tool):
    """모든 파라미터가 null인 arguments 틀. 생성기가 여기서 시작한다."""
    return {p["name"]: None for p in TOOLS[tool]["params"]}
