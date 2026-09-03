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
   조사(에·을·를·이·가·은·는·도·만)나 어미는 붙여도 된다.
   단어 자체를 바꾸면 안 된다 — "반 그릇"을 "절반"으로, "아침"을 "오전"으로 바꾸지 마라.
2. **[골라 쓸 말]이 있으면 그중 하나를 골라 쓴다.** 다른 말로 바꾸지 마라.
3. **[담을 값]·[골라 쓸 말]이 여러 줄이면 전부 담는다.** 하나라도 빠지면 안 된다.
4. **아래 [말투]에 적힌 대로 쓴다.**
5. **한 발화에 사건 하나, 질문 하나.** 두 가지를 한꺼번에 말하지 마라.
6. **묻는 발화는 앱에 명령하듯 쓰지 마라.**
   "조회해줘"·"보여줘"가 아니라 가족에게 묻듯 자연스럽게 물어라.
   다 쓰고 읽었을 때 "얘가 지금 뭘 물어보는 거지?"라는 생각이 들면 실패다. 다시 써라.
7. **{n}개가 서로 달라야 한다.** 문장 구조·시작 단어·길이를 서로 다르게 하라.
8. **아래 표현은 쓰지 마라.**
   {banned}

# 출력

JSON 배열만 출력한다. 설명·코드펜스 없이.

[{{"id": "0001", "utterance": "..."}}, ...]"""


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

    if hint.get("confuse_with"):
        # 툴 이름이 아니라 그 툴이 하는 일로 설명한다
        lines.append(
            f'  주의 — "{T.TOOLS[hint["confuse_with"]]["desc"]}" 로 오해하기 쉽게 쓴다. '
            f'그래도 위 상황이 정답이 되도록 써라'
        )
    elif hint.get("note"):
        lines.append(f'  주의 — {hint["note"]}')

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

    for i in range(0, len(seeds), BATCH_SIZE):
        batch = seeds[i:i + BATCH_SIZE]
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
            print(f"  배치 {i // BATCH_SIZE} 실패 — {e}")
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
