# 시드를 GPT-4.1에 넘겨 한국어 발화를 받는다 — 역방향 생성의 뒷단 (결정 3)

"""``sampler.py`` 가 만든 정답에 발화를 입힌다. **정답은 절대 바꾸지 않는다.**

프롬프트 설계에 결정 셋이 걸려 있다.

- **결정 14** — 표층 라벨이 발화 안에 글자 그대로 남아야 한다. 안 남으면 모델이
  맞아도 오답으로 채점된다. 프롬프트로 1차 방어하고, ``verify.py`` 가 2차로 잡는다
- **결정 17** — 조회계는 "앱에 명령하듯"이 아니라 **"가족에게 묻듯"** 쓰게 한다.
  조회 발화는 아무도 해본 적이 없어 상상하면 어색해진다
- **균질화 방지** — 배치로 묶어 "서로 다르게 쓰라"고 요구하고, 금지 표현을 주입한다

배치로 부르는 이유가 둘이다. 호출 수가 줄어 비용이 내려가고, **배치 안에서 서로
겹치지 말라**는 지시를 줄 수 있다. 한 건씩 부르면 GPT가 매번 가장 흔한 표현을 쓴다.

경로 — ``src`` 를 import 경로에 넣고 쓴다.
"""

import json
import os
import re

import lexicon as L
import sampler as S
import tools as T

MODEL = "gpt-4.1"
BATCH_SIZE = 6

SYSTEM = """너는 한국에서 개를 키우는 보호자다.
방금 있었던 일을 폰에 대고 짧게 말하거나, 문득 궁금해진 것을 물어본다.

너는 앱 사용법을 모르고 툴 이름도 모른다. 평소 가족에게 하던 말투 그대로 말한다.
설명하지 말고, 그냥 말해라."""

RULES = """아래 각 항목에 대해 보호자가 실제로 할 법한 발화를 하나씩 써라.

# 반드시 지킬 것

1. **[담을 값]에 적힌 문자열은 글자 그대로 발화에 넣는다.**
   조사는 여기 적힌 것만 붙인다 — 에·을·를·이·가·은·는·도·만. 어미는 자유다.
   "처럼"·"같이"처럼 뜻을 바꾸는 말은 붙이지 마라.
   "할아버지가"는 되지만 "할아버지처럼"은 뜻이 달라져 틀린 말이 된다.
   단어 자체를 바꾸면 안 된다 — "반 그릇"을 "절반"으로, "아침"을 "오전"으로 바꾸지 마라.
2. **[골라 쓸 말]이 있으면 그중 하나를 골라 쓴다.** 다른 말로 바꾸지 마라.
3. **[담을 값]·[골라 쓸 말]이 여러 줄이면 전부 담는다.** 하나라도 빠지면 안 된다.
4. **적힌 것 말고 다른 정보를 덧붙이지 마라.**
   상태·정도·종류·시간을 새로 지어내지 마라.
   예 — [골라 쓸 말]에 상태가 없는데 "묽었다"고 쓰면 안 된다.
   적혀 있지 않은 것은 말하지 않은 것이다.
5. **아래 [말투]에 적힌 대로 쓴다.**
6. **한 발화에 사건 하나, 질문 하나.** 두 가지를 한꺼번에 말하지 마라.
7. **묻는 발화는 앱에 명령하듯 쓰지 마라.**
   "조회해줘"·"보여줘"가 아니라 가족에게 묻듯 자연스럽게 물어라.
   다 쓰고 읽었을 때 "얘가 지금 뭘 물어보는 거지?"라는 생각이 들면 실패다. 다시 써라.
8. **뜻 없는 말을 붙이지 마라.**
   "확인불요", "기록은 함", "오타다노" 같은 군더더기를 붙이지 마라.
   실제 사람이 입 밖에 내는 말만 쓴다.
9. **{n}개가 서로 달라야 한다.** 문장 구조·시작 단어·길이를 서로 다르게 하라.
10. **아래 표현은 쓰지 마라.**
   {banned}

# 출력

JSON 배열만 출력한다. 설명·코드펜스 없이.

- **`id` 는 아래 각 항목의 대괄호 `[ ]` 안 번호를 그대로 옮겨 적는다.** 새로 매기지 마라
- **항목 수만큼만** 출력한다. 더 만들지 마라

[{{"id": "<대괄호 안 번호>", "utterance": "..."}}]"""


# 발화에서 절대 빠지면 안 되는 맥락.
#
# 툴의 정체성이 파라미터가 아니라 맥락에 있는 경우가 있다. get_vet_summary 는
# "곧 병원에 간다"가 빠지면 get_records 와 구별할 근거가 사라진다 (결정 16 축②).
# 30건 테스트에서 혼동 쌍 지시("어휘만 그쪽으로")가 이 맥락까지 지워
# 라벨이 틀린 데이터가 2건 나왔다. 그래서 혼동 지시보다 **뒤에** 둔다 —
# 마지막에 오는 지시가 앞의 것을 덮는다.
MUST_KEEP = {
    "get_vet_summary": (
        "곧 병원에 간다는 것이 발화에 드러나야 한다 — "
        "'병원 가는데', '내일 진료라', '수의사한테 보여주려고' 처럼. "
        "이 맥락이 빠지면 실패다"
    ),
    # 2026-09-06 추가. get_vet_summary 와 같은 부류인데 빠져 있었다.
    #
    # log_water 의 파라미터는 amount·time·caregiver 뿐이라 **툴을 식별하는 말이
    # 라벨 어디에도 없다.** "한 그릇"·"거의 안"·"계속" 은 물인지 밥인지 못 가린다.
    # 설계 때는 "발화의 동사가 식별한다"고 봤으나 급한 메모체에서 동사가 통째로
    # 사라지고, GPT가 "먹었어" 를 쓰기도 한다.
    #
    # 실측 — 이 지시 없이 만든 데이터에서 물 단서 없는 발화가
    # test 4/19(21%) · val 3/14(21%) · train 34/132(26%) 였다.
    "log_water": (
        "**물을 마셨다는 것이 반드시 드러나야 한다** — '물', '마셨어', '마심' 같은 말이 "
        "발화에 들어가야 한다. 이 말이 없으면 밥 먹은 기록과 구별할 수 없어 실패다. "
        "'먹었어'·'드셨어' 처럼 먹는 것을 가리키는 말은 쓰지 마라"
    ),
}

# MUST_KEEP 이 지켜졌는지 검사할 패턴.
#
# 지시와 검사를 **같은 자리에** 둔다. 떨어뜨려 놓으면 지시를 고칠 때 검사가 따라오지
# 않는다. 이 패턴은 생성 후 검수(regenerate.py)와 데이터 점검에서 쓴다.
# 패턴을 좁게 잡으면 멀쩡한 데이터를 결함으로 몰아 재생성하게 된다. 실측으로 둘을 넓혔다.
#
# - `마[시셨…]` 에 오타형을 넣는다 — 오타 페르소나가 "마섯음"·"마셯슴"·"마셧다"를 쓴다.
#   사람은 읽으면 바로 물인 줄 안다. 이걸 결함으로 세면 4건을 헛돌린다
# - `ml`·`미리` 는 액체 단서다 — 시드에서 `ml` 은 WATER_AMOUNT 에만 있고
#   MEAL_AMOUNT 는 "그램"·"컵"뿐이라 이 데이터셋 안에서는 물 전용 신호다
CUE = {
    "log_water": r"물|마[시셨심신셔섯셧셯싯]|음수|들이켜|\d\s*(ml|㎖|미리|밀리)",
    "get_vet_summary": r"병원|진료|수의사|검진|데려가|보여주려|보여드리",
}


def _surface_hint(tool, param, value):
    """enum 값에 대응하는 한국어 표층 어휘. 모델은 영문 키를 출력하지만 발화는 한국어다."""
    spec = next(p for p in T.TOOLS[tool]["params"] if p["name"] == param)
    if spec["kind"] != "enum":
        return None
    return T.ENUMS[spec["enum"]][value]


def render_seed(seed):
    """시드 하나를 프롬프트에 넣을 블록으로 만든다."""
    hint, label = seed["hint"], seed["label"]
    lines = [f'[{seed["id"]}] 페르소나 — {hint["persona"]}']

    if hint.get("pet"):
        lines.append(f'  반려동물을 "{hint["pet"]}" 라고 부른다')

    if label["tool"] is None:
        kind = "이 앱이 처리할 수 없는 요청" if label["reason"] == "out_of_scope" \
            else "무엇을 말하는지 확정할 수 없는 애매한 말"
        lines.append(f'  성격 — {kind}')
        lines.append(f'  유형 — {hint["note"]}')
        return "\n".join(lines)

    lines.append(f'  상황 — {T.TOOLS[label["tool"]]["desc"]}')

    for name, value in label["arguments"].items():
        if value is None:
            continue
        surface = _surface_hint(label["tool"], name, value)
        if surface:
            lines.append(f'  [골라 쓸 말] {" / ".join(surface)}')
        else:
            lines.append(f'  [담을 값] "{value}"')

    # 기록계는 평서문이어야 한다. 질문으로 끝나면 조회 발화가 되어 라벨과 어긋난다.
    # 질문형 페르소나는 sampler 가 이미 막지만, 수다형도 "~기억나?" 로 끝날 수 있다
    if label["tool"].startswith("log_"):
        lines.append('  형식 — 있었던 일을 알리는 평서문. 질문으로 끝내지 마라')

    if hint.get("confuse_with"):
        # 툴 이름이 아니라 그 툴이 하는 일로 설명한다.
        #
        # "오해하기 쉽게 쓰라"고만 하면 GPT가 내용까지 그쪽으로 옮겨 정답이 뒤집힌다
        # (30건 테스트에서 실측). 바꿔도 되는 것은 어휘뿐임을 명시한다.
        lines.append(
            f'  주의 — 어휘만 "{T.TOOLS[hint["confuse_with"]]["desc"]}" 를 떠올리게 쓴다. '
            f'말하는 내용 자체는 반드시 위 [상황] 그대로여야 한다 — '
            f'내용이 그쪽으로 넘어가면 실패다'
        )
    elif hint.get("note"):
        lines.append(f'  주의 — {hint["note"]}')

    # 혼동 지시 뒤에 온다. 어휘는 헷갈리게 써도 이 맥락만은 남겨야 한다
    if must := MUST_KEEP.get(label["tool"]):
        lines.append(f'  필수 — {must}')

    return "\n".join(lines)


# 결정 번호는 우리 문서의 것이라 GPT에겐 노이즈다. 지시문만 남긴다.
PERSONA_DESC = {
    p["name"]: re.sub(r"\s*\(결정 [\d·]+\)", "", p["desc"]) for p in L.PERSONAS
}


def build_messages(batch):
    # 말투 설명은 배치당 한 번만 낸다. 시드마다 반복하면 토큰만 늘어난다.
    used = dict.fromkeys(s["hint"]["persona"] for s in batch)
    styles = "\n".join(f"- **{n}** — {PERSONA_DESC[n]}" for n in used)

    rules = RULES.format(banned=" · ".join(L.BANNED_PHRASES), n=len(batch))
    body = "\n\n".join(render_seed(s) for s in batch)
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"{rules}\n\n# 말투\n\n{styles}\n\n---\n\n{body}"},
    ]


def generate(seeds, client=None):
    """시드 목록에 발화를 붙여 돌려준다. 실패한 배치는 건너뛰고 개수를 보고한다."""
    from openai import OpenAI

    client = client or OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    out, failed = [], 0

    total = -(-len(seeds) // BATCH_SIZE)

    for i in range(0, len(seeds), BATCH_SIZE):
        batch = seeds[i:i + BATCH_SIZE]
        n_batch = i // BATCH_SIZE

        # 2,400건은 배치가 400회라 30분 넘게 조용하다. 살아 있는지 보이게 한다
        if n_batch and n_batch % 25 == 0:
            print(f"  {n_batch}/{total} 배치 · 누적 {len(out)}건", flush=True)

        try:
            res = client.chat.completions.create(
                model=MODEL,
                messages=build_messages(batch),
                temperature=1.0,  # 다양성이 이 단계의 목적이다
            )
            text = res.choices[0].message.content.strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```")
            said = {d["id"]: d["utterance"] for d in json.loads(text)}
        except Exception as e:
            print(f"  배치 {n_batch} 실패 — {e}", flush=True)
            failed += len(batch)
            continue

        for s in batch:
            if s["id"] in said:
                out.append({**s, "utterance": said[s["id"]].strip()})
            else:
                failed += 1

    print(f"생성 {len(out)}건 · 실패 {failed}건")
    return out


if __name__ == "__main__":
    # API 키 없이 프롬프트만 확인한다. 돈 쓰기 전에 눈으로 보는 단계.
    batch = S.sample(30, seed=7)[:BATCH_SIZE]
    for m in build_messages(batch):
        print(f"===== {m['role']} =====")
        print(m["content"])
