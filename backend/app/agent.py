from __future__ import annotations

import json
import logging
import re
from time import perf_counter

from openai import OpenAI

from .analysis import BASELINE_DAYS, COMPARISON_DAYS, build_evidence, detect_changes
from .config import Settings
from .metrics import ENVIRONMENT_METRICS, METRICS
from .schemas import AgentAnswer, AgentUsage, Evidence, InvestigationReport, ScenarioDetail, ToolTrace
from .tools import TOOL_DEFINITIONS, execute_tool


logger = logging.getLogger(__name__)
OPENAI_TIMEOUT_SECONDS = 30.0
OPENAI_MAX_RETRIES = 1
_NUMBER_OR_DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)?%?")
_KOREAN_DATE = re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")
_SHORT_DATE_RANGE = re.compile(r"(\d{4})-(\d{2})-(\d{2})~(\d{2})-(\d{2})")
_FORBIDDEN_ASSERTIONS = (
    re.compile(r"(?:원인|이유)(?:이|가|으로)?\s*(?:다|입니다)"),
    re.compile(r"때문에[^.?!]*(?:증가|감소|변화)"),
    re.compile(r"(?:질병|병명)[^.?!]*(?:이다|입니다)"),
    re.compile(r"진단(?:했|할 수 있|됩니다|입니다)"),
)


AGENT_INSTRUCTIONS = """
당신은 반려견 행동 기록을 조사하는 제한된 Agent다.
사용자 질문이 기록의 평소 수준, 변화, 기간 비교, 사건을 묻는다면 반드시 필요한 Tool만 호출한다.
평소·보통·원래 수준은 get_baseline, 최근 변화와 시작일은 detect_changes, 명시적인 수치 비교는 compare_periods,
보호자 메모·생활 사건·날씨 기록은 get_events를 사용한다. 질문과 관계없는 Tool을 호출하지 않는다.
compare_periods 결과에는 초기 30일과 최근 7일 평균이 모두 포함되므로, 두 기간의 평균 비교만 요청한 질문에는 get_baseline을 추가 호출하지 않는다.
사용자가 이벤트 종류를 특정하지 않은 일반 기록·메모 질문에는 get_events의 kinds로 ["all"]을 사용한다.
각 Tool 결과를 확인한 다음 추가 조사가 필요한지 결정한다. 같은 Tool과 같은 인자를 반복하지 않는다.
변화 시작 시점 주변 기록을 묻는다면 detect_changes가 반환한 start_date를 기준으로 앞뒤 날짜를 get_events로 조회한다.
강수량이나 기온 같은 환경 수치와 행동 변화를 함께 묻는다면 detect_changes 후 compare_periods로 행동·환경 지표를 비교하고, 기록도 요구할 때 get_events를 추가한다.
질병 진단, 약물 추천, 인과관계 확정 요청에는 Tool을 호출하지 말고 out_of_scope로 답한다.
최종 finding은 Tool이 반환한 Evidence ID를 하나 이상 인용해야 하며, Evidence에 없는 숫자·날짜·사실을 추가하지 않는다.
Tool 결과의 숫자를 서로 빼거나 나누어 새로운 수치를 계산하지 않는다. 비교 결과에 이미 제공된 수치만 그대로 설명한다.
이벤트와 변화가 같은 시기에 나타났다고 설명할 수 있지만 원인이라고 단정하지 않는다.
기록에서 결과가 발견되지 않으면 발견되지 않았다고 설명하고 사실을 만들어내지 않는다.
""".strip()


def _fallback_text(changes, evidence: list[Evidence]) -> tuple[str, str]:
    if not changes:
        return (
            "최근 뚜렷한 변화가 발견되지 않았습니다.",
            "최근 7일 기록을 개인 Baseline과 비교했지만 설정한 지속성과 변화 크기 기준을 넘는 지표가 없었습니다.",
        )
    primary = changes[0]
    verb = "증가" if primary.direction == "increase" else "감소"
    headline = f"최근 가장 큰 변화는 {primary.label} {verb}입니다."
    parts = [item.statement + f" [{item.id}]" for item in evidence if item.kind == "change"]
    event = next((item for item in evidence if item.kind == "event"), None)
    if event:
        parts.append(f"{event.statement}; 같은 시기의 기록이지만 원인으로 판단할 수는 없습니다. [{event.id}]")
    return headline, " ".join(parts)


def _normalized_claim_values(text: str) -> set[str]:
    text = _KOREAN_DATE.sub(
        lambda match: f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}", text
    )
    text = _SHORT_DATE_RANGE.sub(
        lambda match: f"{match.group(1)}-{match.group(2)}-{match.group(3)}~{match.group(1)}-{match.group(4)}-{match.group(5)}",
        text,
    )
    return set(_NUMBER_OR_DATE.findall(text))


def _evidence_values(items: list[Evidence]) -> set[str]:
    source_values: set[str] = set()
    for item in items:
        source_values |= _normalized_claim_values(item.statement)
        for value in item.values.values():
            if value is None:
                continue
            source_values.add(str(value))
            if isinstance(value, (int, float)):
                source_values.add(str(abs(value)))
                source_values.add(f"{abs(value)}%")
                if float(value).is_integer():
                    source_values.add(str(abs(int(value))))
        if item.source_dates:
            source_values.add(str(len(set(item.source_dates))))
    return source_values


def _claim_is_supported(text: str, cited_ids: set[str], evidence_by_id: dict[str, Evidence]) -> bool:
    if not text.strip() or any(pattern.search(text) for pattern in _FORBIDDEN_ASSERTIONS):
        return False
    if not cited_ids or not cited_ids <= evidence_by_id.keys():
        return False
    claim_values = _normalized_claim_values(text)
    cited = [evidence_by_id[evidence_id] for evidence_id in cited_ids]
    source_values = _evidence_values(cited)
    if not claim_values <= source_values:
        return False
    if ("증가" in text or "감소" in text) and not any(item.kind in {"change", "comparison"} for item in cited):
        return False
    return True


def _agent_answer_is_valid(answer: AgentAnswer, evidence: list[Evidence], trace: list[ToolTrace]) -> bool:
    if any(pattern.search(text) for pattern in _FORBIDDEN_ASSERTIONS for text in [answer.headline, *answer.limitations]):
        return False
    if answer.status == "out_of_scope":
        return not answer.findings and not trace and bool(answer.limitations)
    if not answer.findings or not evidence:
        return False
    evidence_by_id = {item.id: item for item in evidence}
    headline_values = _normalized_claim_values(answer.headline)
    all_source_values = _evidence_values(evidence)
    if not headline_values <= all_source_values:
        return False
    called_tools = {item.tool for item in trace}
    for finding in answer.findings:
        cited_ids = set(finding.evidence_ids)
        if not _claim_is_supported(finding.text, cited_ids, evidence_by_id):
            return False
        if any(evidence_by_id[evidence_id].source_tool not in called_tools for evidence_id in cited_ids):
            return False
    return True


def _agent_response_is_valid(text: str, evidence: list[Evidence]) -> bool:
    """Compatibility validator for deterministic and legacy free-text tests."""
    evidence_by_id = {item.id: item for item in evidence}
    normalized = re.sub(r"([.!?])\s*((?:\[E\d+\]\s*)+)", lambda match: f" {match.group(2).strip()}{match.group(1)} ", text.strip())
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])(?:\s+|$)|\n+", normalized) if item.strip()]
    if not 2 <= len(sentences) <= 4:
        return False
    for sentence in sentences:
        cited_ids = set(re.findall(r"\[(E\d+)\]", sentence))
        claim = re.sub(r"\[E\d+\]", "", sentence)
        if not _claim_is_supported(claim, cited_ids, evidence_by_id):
            return False
        for item in evidence:
            if item.kind != "change" or not item.metric:
                continue
            if METRICS[item.metric][0] in sentence and ("증가" in sentence or "감소" in sentence) and item.id not in cited_ids:
                return False
    return True


def _agent_input(scenario: ScenarioDetail, question: str) -> str:
    metric_catalog = {name: details[0] for name, details in (METRICS | ENVIRONMENT_METRICS).items()}
    return (
        f"조사 대상: {scenario.scenario.dog_name}\n"
        f"기록 범위: {scenario.scenario.start_date.isoformat()}~{scenario.scenario.end_date.isoformat()}\n"
        f"사용 가능한 지표: {json.dumps(metric_catalog, ensure_ascii=False)}\n"
        f"사용자 질문: {question}"
    )


def _run_tool_agent(
    scenario: ScenarioDetail,
    question: str,
    settings: Settings,
) -> tuple[AgentAnswer, list[ToolTrace], list[Evidence], AgentUsage]:
    started_at = perf_counter()
    client = OpenAI(api_key=settings.openai_api_key, timeout=OPENAI_TIMEOUT_SECONDS, max_retries=OPENAI_MAX_RETRIES)
    request = {
        "model": settings.openai_model,
        "reasoning": {"effort": settings.agent_reasoning_effort},
        "instructions": AGENT_INSTRUCTIONS,
        "input": _agent_input(scenario, question),
        "tools": TOOL_DEFINITIONS,
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "max_tool_calls": settings.agent_max_steps,
        "max_output_tokens": settings.agent_max_output_tokens,
        "text_format": AgentAnswer,
    }
    response = client.responses.parse(**request)
    api_requests = 1
    input_tokens = response.usage.input_tokens if response.usage else 0
    output_tokens = response.usage.output_tokens if response.usage else 0
    trace: list[ToolTrace] = []
    ledger: list[Evidence] = []
    signatures: set[str] = set()
    correction_used = False
    answer_correction_used = False

    while True:
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            answer = response.output_parsed
            if answer is None:
                raise ValueError("Agent did not return structured output")
            if not _agent_answer_is_valid(answer, ledger, trace) and not answer_correction_used:
                answer_correction_used = True
                response = client.responses.parse(
                    model=settings.openai_model,
                    reasoning={"effort": settings.agent_reasoning_effort},
                    instructions=AGENT_INSTRUCTIONS,
                    previous_response_id=response.id,
                    input=(
                        "최종 답변 검증에 실패했습니다. Tool Evidence에 직접 존재하지 않는 계산값·날짜·사실을 제거하고, "
                        "각 finding이 인용한 Evidence 문장과 values에 있는 내용만 사용해 한 번 다시 작성하세요."
                    ),
                    max_output_tokens=settings.agent_max_output_tokens,
                    text_format=AgentAnswer,
                )
                api_requests += 1
                if response.usage:
                    input_tokens += response.usage.input_tokens
                    output_tokens += response.usage.output_tokens
                continue
            usage = AgentUsage(
                api_requests=api_requests, tool_calls=len(trace), input_tokens=input_tokens,
                output_tokens=output_tokens, total_tokens=input_tokens + output_tokens,
                latency_ms=round((perf_counter() - started_at) * 1000),
                accepted=_agent_answer_is_valid(answer, ledger, trace),
            )
            return answer, trace, ledger, usage

        call = calls[0]
        if len(trace) >= settings.agent_max_steps:
            raise ValueError("Agent exceeded the tool step limit")
        try:
            arguments = json.loads(call.arguments)
            signature = json.dumps({"tool": call.name, "arguments": arguments}, sort_keys=True, ensure_ascii=False)
            if signature in signatures:
                raise ValueError("The same tool and arguments cannot be repeated")
            execution = execute_tool(call.name, arguments, scenario, evidence_start_index=len(ledger) + 1)
            signatures.add(signature)
            if call.name == "get_events":
                scope = ", ".join(arguments.get("kinds", []))
                summary = f"관련 기록 조회: {scope}"
            else:
                labels = []
                for metric in arguments.get("metrics", []):
                    labels.append("전체 지표" if metric == "all" else (METRICS | ENVIRONMENT_METRICS).get(metric, (metric,))[0])
                action = {"get_baseline": "평소 수준 조회", "detect_changes": "최근 변화 탐지", "compare_periods": "기간 수치 비교"}.get(call.name, "조회")
                summary = f"{action}: {', '.join(labels)}"
            trace.append(ToolTrace(step=len(trace) + 1, tool=call.name, summary=summary, arguments=arguments))
            ledger.extend(execution.evidence)
            output = execution.model_output_json()
        except (json.JSONDecodeError, ValueError) as exc:
            if correction_used:
                raise ValueError("Agent tool arguments failed validation twice") from exc
            correction_used = True
            output = json.dumps({"error": str(exc), "retry": "Correct the arguments once or finish without this claim."}, ensure_ascii=False)

        response = client.responses.parse(
            model=settings.openai_model,
            reasoning={"effort": settings.agent_reasoning_effort},
            instructions=AGENT_INSTRUCTIONS,
            previous_response_id=response.id,
            input=[{"type": "function_call_output", "call_id": call.call_id, "output": output}],
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            parallel_tool_calls=False,
            max_tool_calls=max(1, settings.agent_max_steps - len(trace)),
            max_output_tokens=settings.agent_max_output_tokens,
            text_format=AgentAnswer,
        )
        api_requests += 1
        if response.usage:
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens


def _answer_summary(answer: AgentAnswer) -> str:
    return " ".join(
        f"{finding.text} {' '.join(f'[{evidence_id}]' for evidence_id in finding.evidence_ids)}"
        for finding in answer.findings
    )


def investigate(scenario: ScenarioDetail, question: str, use_llm: bool, settings: Settings) -> InvestigationReport:
    is_personal_demo = scenario.scenario.id == "personal-browser-demo"
    minimum_records = BASELINE_DAYS + COMPARISON_DAYS
    if len(scenario.records) < minimum_records:
        remaining = minimum_records - len(scenario.records)
        return InvestigationReport(
            scenario_id=scenario.scenario.id, question=question, status="insufficient_data",
            mode="deterministic_fallback", headline="Personal Baseline을 만들 기록이 더 필요합니다.",
            summary=(f"현재 {len(scenario.records)}일의 기록이 있습니다. 과거 {BASELINE_DAYS}일과 최근 "
                     f"{COMPARISON_DAYS}일을 비교하려면 {remaining}일의 기록이 더 필요합니다."),
            changes=[], evidence=[], tool_trace=[], agent_usage=None,
            limitations=["기록이 충분해질 때까지 변화 여부를 판단하지 않습니다."],
        )

    fallback_changes = detect_changes(scenario.records)[:3]
    fallback_evidence = build_evidence(scenario.records, fallback_changes, scenario.events)
    headline, summary = _fallback_text(fallback_changes, fallback_evidence)
    mode = "deterministic_fallback"
    status = "completed"
    changes = fallback_changes
    evidence = fallback_evidence
    trace = [
        ToolTrace(step=1, tool="get_baseline", summary="초기 30일 개인 Baseline 계산"),
        ToolTrace(step=2, tool="detect_changes", summary="최근 7일의 지속 변화 탐지"),
        ToolTrace(step=3, tool="compare_periods", summary="행동·환경 지표 동시 비교"),
        ToolTrace(step=4, tool="get_events", summary="변화 시점 주변 이벤트 조회"),
    ]
    limitations = [
        ("이 결과는 브라우저에서 전달된 기록의 동시 변화를 설명하며 인과관계나 질병을 판단하지 않습니다."
         if is_personal_demo else
         "이 결과는 합성 기록에서 관찰된 동시 변화를 설명하며 인과관계나 질병을 판단하지 않습니다."),
        "Baseline은 시나리오의 초기 30일, 비교 기간은 마지막 7일입니다.",
    ]
    agent_usage = None

    if use_llm and settings.openai_api_key:
        try:
            answer, agent_trace, ledger, agent_usage = _run_tool_agent(scenario, question, settings)
            if _agent_answer_is_valid(answer, ledger, agent_trace):
                status = answer.status
                headline = answer.headline
                summary = _answer_summary(answer) if answer.findings else " ".join(answer.limitations)
                changes = [item for item in fallback_changes if any(e.metric == item.metric and e.kind == "change" for e in ledger)]
                evidence = ledger
                trace = agent_trace
                limitations = answer.limitations or limitations
                mode = "agent"
                agent_usage.accepted = True
            else:
                logger.warning("Agent response failed tool or evidence validation; using deterministic fallback")
        except Exception:
            logger.exception("Agent investigation failed; using deterministic fallback")

    return InvestigationReport(
        scenario_id=scenario.scenario.id, question=question, status=status, mode=mode,
        headline=headline, summary=summary, changes=changes, evidence=evidence,
        tool_trace=trace, agent_usage=agent_usage, limitations=limitations,
    )
