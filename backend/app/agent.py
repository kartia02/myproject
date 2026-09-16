from __future__ import annotations

import json
import logging
import re
from time import perf_counter

from openai import OpenAI

from .analysis import build_evidence, detect_changes
from .config import Settings
from .metrics import METRICS
from .schemas import AgentUsage, Evidence, InvestigationReport, ScenarioDetail, ToolTrace
from .tools import TOOL_DEFINITIONS, execute_tool_json


logger = logging.getLogger(__name__)

REQUIRED_TOOL_NAMES = frozenset(definition["name"] for definition in TOOL_DEFINITIONS)
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
당신은 반려견 행동 변화 조사 Agent다. 질병이나 인과관계를 추정하거나 진단하지 않는다.
반드시 제공된 네 도구로 개인 Baseline, 변화, 기간 비교, 이벤트를 조사한다.
최종 답변은 서버가 제공한 모든 Evidence를 빠짐없이 각각 한 문장으로 작성한다.
각 문장은 Evidence의 statement를 그대로 복사한 뒤 해당 [E1] 형식의 ID를 붙인다. 서로 다른 Evidence를 한 문장으로 합치지 않는다.
조사 대상 이름, Evidence에 없는 날짜·기간·수치·해석을 추가하지 않는다.
이벤트는 관찰 기록일 뿐 변화의 원인이나 질병이라고 표현하지 않는다.
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
    parts = [e.statement + f" [{e.id}]" for e in evidence if e.kind == "change"]
    event = next((e for e in evidence if e.kind == "event"), None)
    if event:
        parts.append(f"{event.statement}; 같은 시기의 기록이지만 원인으로 판단할 수는 없습니다. [{event.id}]")
    return headline, " ".join(parts)


def _agent_response_is_valid(text: str, evidence: list[Evidence]) -> bool:
    evidence_by_id = {item.id: item for item in evidence}
    if not text.strip() or any(pattern.search(text) for pattern in _FORBIDDEN_ASSERTIONS):
        return False

    normalized_text = re.sub(
        r"([.!?])\s*((?:\[E\d+\]\s*)+)",
        lambda match: f" {match.group(2).strip()}{match.group(1)} ",
        text.strip(),
    )
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])(?:\s+|$)|\n+", normalized_text)
        if sentence.strip()
    ]
    if not 2 <= len(sentences) <= 4:
        return False

    for sentence in sentences:
        cited_ids = set(re.findall(r"\[(E\d+)\]", sentence))
        if not cited_ids or not cited_ids <= evidence_by_id.keys():
            return False

        claim_without_citations = re.sub(r"\[E\d+\]", "", sentence)
        claim_without_citations = _KOREAN_DATE.sub(
            lambda match: f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}",
            claim_without_citations,
        )
        claim_without_citations = _SHORT_DATE_RANGE.sub(
            lambda match: (
                f"{match.group(1)}-{match.group(2)}-{match.group(3)}~"
                f"{match.group(1)}-{match.group(4)}-{match.group(5)}"
            ),
            claim_without_citations,
        )
        claim_values = set(_NUMBER_OR_DATE.findall(claim_without_citations))
        source_text = " ".join(evidence_by_id[evidence_id].statement for evidence_id in cited_ids)
        source_values = set(_NUMBER_OR_DATE.findall(source_text))
        for evidence_id in cited_ids:
            source_dates = evidence_by_id[evidence_id].source_dates
            if source_dates:
                source_values.add(str(len(set(source_dates))))
        if not claim_values <= source_values:
            return False

        for item in evidence:
            if item.kind != "change" or not item.metric:
                continue
            label = METRICS[item.metric][0]
            asserts_change = "증가" in sentence or "감소" in sentence
            if label in sentence and asserts_change and item.id not in cited_ids:
                return False

    return True


def _required_tools_were_called(trace: list[ToolTrace]) -> bool:
    called = [item.tool for item in trace]
    return len(called) == len(REQUIRED_TOOL_NAMES) and set(called) == REQUIRED_TOOL_NAMES


def _run_tool_agent(
    scenario: ScenarioDetail,
    question: str,
    evidence: list[Evidence],
    settings: Settings,
) -> tuple[str, list[ToolTrace], AgentUsage]:
    started_at = perf_counter()
    client = OpenAI(api_key=settings.openai_api_key)
    evidence_catalog = json.dumps(
        [{"id": item.id, "statement": item.statement} for item in evidence],
        ensure_ascii=False,
    )
    response = client.responses.create(
        model=settings.openai_model,
        reasoning={"effort": settings.agent_reasoning_effort},
        instructions=AGENT_INSTRUCTIONS,
        input=(
            f"조사 대상: {scenario.scenario.dog_name}\n사용자 질문: {question}\n"
            f"서버가 검증한 Evidence 목록: {evidence_catalog}"
        ),
        tools=TOOL_DEFINITIONS,
        max_output_tokens=settings.agent_max_output_tokens,
    )
    api_requests = 1
    input_tokens = response.usage.input_tokens if response.usage else 0
    output_tokens = response.usage.output_tokens if response.usage else 0
    trace: list[ToolTrace] = []
    calls_used = 0
    while calls_used < settings.agent_max_steps:
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            usage = AgentUsage(
                api_requests=api_requests,
                tool_calls=len(trace),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=round((perf_counter() - started_at) * 1000),
            )
            return response.output_text, trace, usage
        outputs = []
        for call in calls:
            if calls_used >= settings.agent_max_steps:
                break
            output = execute_tool_json(call.name, call.arguments, scenario)
            calls_used += 1
            trace.append(ToolTrace(step=calls_used, tool=call.name, summary=f"{call.name} 조회 완료"))
            outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": output})
        response = client.responses.create(
            model=settings.openai_model,
            reasoning={"effort": settings.agent_reasoning_effort},
            instructions=AGENT_INSTRUCTIONS,
            previous_response_id=response.id,
            input=outputs,
            tools=TOOL_DEFINITIONS,
            max_output_tokens=settings.agent_max_output_tokens,
        )
        api_requests += 1
        if response.usage:
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
    usage = AgentUsage(
        api_requests=api_requests,
        tool_calls=len(trace),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        latency_ms=round((perf_counter() - started_at) * 1000),
    )
    return response.output_text, trace, usage


def investigate(
    scenario: ScenarioDetail,
    question: str,
    use_llm: bool,
    settings: Settings,
) -> InvestigationReport:
    changes = detect_changes(scenario.records)[:3]
    evidence = build_evidence(scenario.records, changes, scenario.events)
    headline, summary = _fallback_text(changes, evidence)
    mode = "deterministic_fallback"
    trace = [
        ToolTrace(step=1, tool="get_baseline", summary="초기 30일 개인 Baseline 계산"),
        ToolTrace(step=2, tool="detect_changes", summary="최근 7일의 지속 변화 탐지"),
        ToolTrace(step=3, tool="compare_periods", summary="행동·환경 지표 동시 비교"),
        ToolTrace(step=4, tool="get_events", summary="변화 시점 주변 이벤트 조회"),
    ]
    agent_usage = None
    if use_llm and settings.openai_api_key and evidence:
        try:
            agent_text, agent_trace, agent_usage = _run_tool_agent(scenario, question, evidence, settings)
            if _required_tools_were_called(agent_trace) and _agent_response_is_valid(agent_text, evidence):
                summary = agent_text
                trace = agent_trace
                mode = "agent"
                agent_usage.accepted = True
            else:
                logger.warning("Agent response failed tool or evidence validation; using deterministic fallback")
        except Exception:
            # The public demo still returns calculated evidence when the model is unavailable.
            logger.exception("Agent investigation failed; using deterministic fallback")
    return InvestigationReport(
        scenario_id=scenario.scenario.id,
        question=question,
        status="completed" if len(scenario.records) >= 37 else "insufficient_data",
        mode=mode,
        headline=headline,
        summary=summary,
        changes=changes,
        evidence=evidence,
        tool_trace=trace,
        agent_usage=agent_usage,
        limitations=[
            "이 결과는 합성 기록에서 관찰된 동시 변화를 설명하며 인과관계나 질병을 판단하지 않습니다.",
            "Baseline은 시나리오의 초기 30일, 비교 기간은 마지막 7일입니다.",
        ],
    )
