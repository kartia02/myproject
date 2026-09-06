# 세 비교 대상의 예측을 같은 경로로 뽑는다 — 채점기에 넣을 {"id","output"} JSONL 생성기

"""채점기는 있는데 채점할 것을 만드는 코드가 없어서 만든다.

**세 대상이 이 스크립트 하나를 쓴다.** 대상마다 다른 스크립트를 쓰면 출력 처리·
지연 측정·파일 형식이 조금씩 달라져 비교가 오염된다.

    gpt41   GPT-4.1 + 툴 목록 프롬프트     현실의 상한선
    base    같은 4B + 툴 스펙 + few-shot   파인튜닝 기여도의 기준선
    ft      파인튜닝 모델 + 발화만          본 프로젝트 산출물

**프롬프트가 대상마다 다른 것은 오염이 아니라 실험 그 자체다** (결정 2).
`ft` 만 툴 스펙을 안 받는 것이 이 프로젝트가 재려는 차이다. 통일해야 하는 것은
프롬프트가 아니라 **출력 처리·지연 측정·파일 형식**이고 그것을 여기서 묶는다.

⚠ **`ft` 프롬프트는 학습 데이터 포맷과 글자 단위로 같아야 한다.**
Day 3에서 학습 데이터를 만들 때 ``build_messages("ft", ...)`` 를 그대로 쓴다.
여기서 시스템 메시지를 붙였는데 학습에선 안 붙이면, 재는 것이 파인튜닝 효과가
아니라 포맷 불일치가 된다.

사용법

    python src/predict.py --target gpt41 --input data/test.jsonl --out data/pred_gpt41.jsonl
    python src/predict.py --target base  --input data/test.jsonl --out data/pred_base.jsonl \\
        --engine ollama --model qwen3-4b --shots data/train.jsonl
    python src/predict.py --target ft --input data/test.jsonl --dump data/prompts_ft.jsonl

``--dump`` 는 API를 부르지 않고 프롬프트만 뽑는다. Colab처럼 다른 런타임에서
돌릴 때 **프롬프트가 환경마다 달라지는 것**을 막는다.
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import tools as T

# 평가는 재현돼야 한다. 생성 단계와 달리 여기서 다양성은 해악이다
TEMPERATURE = 0.0
N_SHOTS = 8


# --- 툴 스펙 프롬프트 -------------------------------------------------------
# tools.py 에서 만든다. 문서를 손으로 옮겨 적으면 코드와 어긋난다.
#
# **일부러 넉넉하게 적는다.** GPT-4.1 은 "현실의 상한선" 역할이라 스펙이 부실하면
# 상한선이 실제보다 낮게 잡히고, 그러면 우리 결과가 부당하게 좋아 보인다.

def tool_spec_text():
    lines = []
    for name, spec in T.TOOLS.items():
        params = []
        for p in spec["params"]:
            desc = f'{p["name"]}'
            if p["kind"] == "enum":
                desc += f' (다음 중 하나 또는 null — {", ".join(T.enum_values(p["enum"]))})'
            elif p["kind"] == "time":
                desc += " (시간 표현. 발화에 나온 그대로)"
            else:
                desc += " (발화에 나온 그대로)"
            if p["required"]:
                desc += " **필수**"
            params.append(desc)
        lines.append(f'- `{name}` — {spec["desc"]}\n  ' + "\n  ".join(params))
    return "\n".join(lines)


RULES = """너는 반려동물 케어 기록 앱의 입력 변환기다.
보호자의 발화를 아래 툴 중 하나의 호출로 바꾼다.

# 툴 12개

{spec}

# 출력 형식 — 반드시 이 JSON 하나만 출력한다

{{"tool": "log_meal", "arguments": {{"food": "사료", "amount": "반 그릇", "time": "아침", "caregiver": null}}, "reason": null}}

- 키는 `tool`·`arguments`·`reason` 셋뿐이고 순서도 이대로다
- `arguments` 는 그 툴의 파라미터를 **전부** 담는다. 미언급은 `null`
- 설명·인사·코드펜스 없이 JSON만 출력한다

# 거절

처리할 수 없으면 툴을 부르지 않고 아래 형태로 답한다. `arguments` 는 빈 객체다.

{{"tool": null, "arguments": {{}}, "reason": "out_of_scope"}}
{{"tool": null, "arguments": {{}}, "reason": "ambiguous"}}

- `out_of_scope` — 지원하지 않는 요청. 날씨·추천·구매·잡담, 그리고 **진단·투약 판단**
- `ambiguous` — 툴은 있으나 확정 불가. 사건이 둘이거나, 지시대명사뿐이거나,
  **필수 파라미터가 발화에서 확정되지 않는** 경우

# 값을 담는 규칙

1. **enum 파라미터는 위에 적힌 영문 키로 바꾼다.** "응가" → `feces`, "양치" → `teeth`
2. **그 밖의 값은 발화에 나온 표현 그대로 담는다.** 계산하거나 단위를 바꾸지 않는다
   - "아침에" → `"아침"` (`"08:00"` 아님)
   - "5킬로 200" → `"5킬로 200"` (`5.2` 아님)
   - "짧게" → `"짧게"` (`null` 아님)
   - 조사는 뗀다 — "사료를" → `"사료"`
3. **1인칭 주어는 `caregiver` 에 담지 않는다.** "내가 약 먹였어" → `caregiver: null`
4. **반려동물 이름·호칭은 어느 칸에도 담지 않는다**

# 툴 고르기

- **약이면 전부 `log_medication`** — 구충제·심장사상충약·영양제 포함.
  `log_care` 는 약이 아닌 위생 관리(양치·발톱·목욕·항문낭·빗질·귀 청소)
- **이상 상태를 담을 전용 칸이 있으면 그 툴** — "설사했어"는 `log_excretion(condition=diarrhea)`.
  담을 칸이 없으면 `log_symptom`
- **나열로 답이 되면 `get_records`, 합쳐야 답이 되면 `get_trend`**
- **진료 맥락이 있고 기록 종류를 특정하지 않으면 `get_vet_summary`.** 종류가 특정되면 `get_records`
- **"이제 해야 하나"를 물으면 `get_care_due`.** 시제 어미가 아니라 묻는 목적으로 가른다"""


def system_prompt(with_spec):
    """`ft` 만 스펙을 받지 않는다. 그 차이가 결정 2의 측정 대상이다."""
    return RULES.format(spec=tool_spec_text()) if with_spec else None


# --- few-shot ---------------------------------------------------------------

def load_shots(path, n=N_SHOTS):
    """학습셋에서 층을 고루 덮는 예시를 뽑는다.

    **테스트셋에서 뽑으면 안 된다.** 시험 문제를 예시로 보여주는 셈이 된다.
    id 순으로 층마다 돌아가며 집어 실행할 때마다 같은 것이 나오게 한다.
    """
    rows = sorted((json.loads(l) for l in open(path, encoding="utf-8") if l.strip()),
                  key=lambda r: r["id"])
    by_layer, picked = {}, []
    for r in rows:
        by_layer.setdefault(r["layer"], []).append(r)
    while len(picked) < n and any(by_layer.values()):
        for layer in sorted(by_layer):
            if by_layer[layer] and len(picked) < n:
                picked.append(by_layer[layer].pop(0))
    return picked


def shot_messages(shots):
    out = []
    for s in shots:
        out.append({"role": "user", "content": s["utterance"]})
        out.append({"role": "assistant",
                    "content": json.dumps(s["label"], ensure_ascii=False)})
    return out


# --- 프롬프트 조립 ----------------------------------------------------------

def build_messages(target, utterance, shots=()):
    """대상별 프롬프트. `ft` 는 발화 한 줄뿐이다 (결정 2)."""
    messages = []
    if system := system_prompt(with_spec=target != "ft"):
        messages.append({"role": "system", "content": system})
    messages += shot_messages(shots)
    messages.append({"role": "user", "content": utterance})
    return messages


# --- 실행 엔진 --------------------------------------------------------------
# 엔진이 달라도 출력 처리와 측정은 같은 자리에서 한다

def call_openai(messages, model, client):
    res = client.chat.completions.create(
        model=model, messages=messages, temperature=TEMPERATURE)
    usage = res.usage
    return res.choices[0].message.content, usage.prompt_tokens, usage.completion_tokens


def call_ollama(messages, model, endpoint):
    import urllib.request

    body = json.dumps({
        "model": model, "messages": messages, "stream": False,
        "options": {"temperature": TEMPERATURE},
    }).encode()
    req = urllib.request.Request(f"{endpoint}/api/chat", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        data = json.load(res)
    return (data["message"]["content"],
            data.get("prompt_eval_count"), data.get("eval_count"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=["gpt41", "base", "ft"])
    ap.add_argument("--input", default="data/test.jsonl")
    ap.add_argument("--out")
    ap.add_argument("--dump", help="API를 부르지 않고 프롬프트만 JSONL로 저장")
    ap.add_argument("--shots", help="few-shot 예시를 뽑을 학습셋 (base 전용)")
    ap.add_argument("--engine", choices=["openai", "ollama"], default="openai")
    ap.add_argument("--model", help="기본값 — gpt41이면 gpt-4.1, 그 외는 지정 필수")
    ap.add_argument("--endpoint", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, help="앞에서 N건만. 연결 확인용")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.input, encoding="utf-8") if l.strip()]
    if args.limit:
        rows = rows[:args.limit]

    shots = load_shots(args.shots) if args.shots else ()
    if args.target == "base" and not shots:
        print("경고 — base 대상인데 --shots 가 없다. few-shot 없이 재면 기준선이 아니다")

    # 프롬프트만 뽑고 끝낸다. Colab 등 다른 런타임이 이 파일을 읽어 출력을 만든다
    if args.dump:
        Path(args.dump).parent.mkdir(parents=True, exist_ok=True)
        with open(args.dump, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(
                    {"id": r["id"],
                     "messages": build_messages(args.target, r["utterance"], shots)},
                    ensure_ascii=False) + "\n")
        print(f"프롬프트 {len(rows)}건 → {args.dump}")
        return

    if not args.out:
        ap.error("--out 또는 --dump 가 필요하다")

    model = args.model or ("gpt-4.1" if args.target == "gpt41" else None)
    if not model:
        ap.error("--model 을 지정한다")

    client = None
    if args.engine == "openai":
        from openai import OpenAI
        if not os.environ.get("OPENAI_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent.parent / ".env")
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    results, latencies, in_tok, out_tok, failed = [], [], 0, 0, 0

    for i, r in enumerate(rows):
        messages = build_messages(args.target, r["utterance"], shots)
        started = time.perf_counter()
        try:
            if args.engine == "openai":
                text, pt, ct = call_openai(messages, model, client)
            else:
                text, pt, ct = call_ollama(messages, model, args.endpoint)
        except Exception as e:
            # 빈 출력을 남긴다. 건너뛰면 id 가 어긋나 채점기가 멈춘다.
            # 채점에서는 파싱 실패로 잡히고, 그건 사실 그대로다
            print(f"  {r['id']} 실패 — {e}", flush=True)
            text, pt, ct, failed = "", None, None, failed + 1
        elapsed = (time.perf_counter() - started) * 1000

        latencies.append(elapsed)
        in_tok += pt or 0
        out_tok += ct or 0
        results.append({"id": r["id"], "output": text, "latency_ms": round(elapsed, 1),
                        "input_tokens": pt, "output_tokens": ct})

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(rows)}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ordered = sorted(latencies)
    p = lambda q: ordered[min(int(len(ordered) * q), len(ordered) - 1)]
    print(f"\n{args.target} · {model} · {len(results)}건 · 실패 {failed}건 → {args.out}")
    print(f"지연 p50 {p(0.5):.0f}ms · p95 {p(0.95):.0f}ms · 평균 {statistics.mean(latencies):.0f}ms")
    print(f"입력 토큰 {in_tok:,} (건당 {in_tok / len(results):.0f}) · "
          f"출력 토큰 {out_tok:,} (건당 {out_tok / len(results):.0f})")


if __name__ == "__main__":
    main()
