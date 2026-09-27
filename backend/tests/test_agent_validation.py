from app.agent import _agent_answer_is_valid, _agent_response_is_valid, investigate
from app.config import Settings
from app.schemas import AgentAnswer, AgentFinding, ToolTrace
from app.synthetic import get_scenario
from app.tools import execute_tool


def evidence_for_changed_scenario():
    report = investigate(
        get_scenario("night-restlessness"),
        "최근 변화가 있어?",
        use_llm=False,
        settings=Settings(openai_api_key=None),
    )
    return report.evidence


def test_agent_response_requires_evidence_for_every_sentence() -> None:
    evidence = evidence_for_changed_scenario()
    valid = (
        f"{evidence[0].statement} [{evidence[0].id}]. "
        f"{evidence[1].statement} [{evidence[1].id}]."
    )
    missing_citation = f"{evidence[0].statement} [{evidence[0].id}]. 추가 변화가 있습니다."

    assert _agent_response_is_valid(valid, evidence)
    assert not _agent_response_is_valid(missing_citation, evidence)


def test_agent_response_rejects_unsupported_numbers_and_causal_claims() -> None:
    evidence = evidence_for_changed_scenario()
    unsupported_number = (
        f"최근 값이 999회로 증가했습니다 [{evidence[0].id}]. "
        f"{evidence[1].statement} [{evidence[1].id}]."
    )
    causal_claim = (
        f"저녁 산책 감소가 원인입니다 [{evidence[0].id}]. "
        f"{evidence[1].statement} [{evidence[1].id}]."
    )

    assert not _agent_response_is_valid(unsupported_number, evidence)
    assert not _agent_response_is_valid(causal_claim, evidence)


def test_agent_response_accepts_korean_date_equivalent_to_iso_evidence() -> None:
    report = investigate(
        get_scenario("night-restlessness"),
        "최근 변화가 있어?",
        use_llm=False,
        settings=Settings(openai_api_key=None),
    )
    event = next(item for item in report.evidence if item.kind == "event")
    text = (
        f"{event.start_date.year}년 {event.start_date.month}월 {event.start_date.day}일에 기록이 있습니다. [{event.id}] "
        f"같은 날짜의 관찰 기록입니다. [{event.id}]"
    )

    assert _agent_response_is_valid(text, report.evidence)


def test_agent_response_accepts_abbreviated_date_range_and_supported_period_count() -> None:
    report = investigate(
        get_scenario("rainy-slowdown"),
        "최근 변화가 있어?",
        use_llm=False,
        settings=Settings(openai_api_key=None),
    )
    change = report.evidence[0]
    text = (
        f"최근 7일(2026-08-23~08-29) {change.statement.split('이 ', 1)[0]}이 달라졌습니다. [{change.id}] "
        f"해당 기간의 관찰 결과입니다. [{change.id}]"
    )

    assert _agent_response_is_valid(text, report.evidence)


def test_agent_response_requires_evidence_for_each_named_change() -> None:
    report = investigate(
        get_scenario("rainy-slowdown"),
        "최근 변화가 있어?",
        use_llm=False,
        settings=Settings(openai_api_key=None),
    )
    event = next(item for item in report.evidence if item.kind == "event")
    unsupported = (
        f"활동 시간과 저녁 산책 감소가 같은 시기에 나타났습니다. [{event.id}] "
        f"{event.statement}입니다. [{event.id}]"
    )

    assert not _agent_response_is_valid(unsupported, report.evidence)


def test_event_can_name_metric_without_claiming_detected_change() -> None:
    report = investigate(
        get_scenario("night-restlessness"),
        "최근 변화가 있어?",
        use_llm=False,
        settings=Settings(openai_api_key=None),
    )
    event = next(item for item in report.evidence if item.kind == "event")
    text = f"{event.statement} [{event.id}]\n같은 시기의 관찰 기록입니다. [{event.id}]"

    assert _agent_response_is_valid(text, report.evidence)


def test_structured_answer_requires_evidence_from_the_called_tool() -> None:
    scenario = get_scenario("night-restlessness")
    execution = execute_tool("get_baseline", {"metrics": ["sleep_hours"]}, scenario)
    evidence = execution.evidence
    trace = [ToolTrace(step=1, tool="get_baseline", summary="done", arguments={"metrics": ["sleep_hours"]})]
    answer = AgentAnswer(
        status="completed",
        headline="평소 수면 시간",
        findings=[AgentFinding(text=evidence[0].statement, evidence_ids=[evidence[0].id])],
        limitations=[],
    )

    assert _agent_answer_is_valid(answer, evidence, trace)
    assert not _agent_answer_is_valid(answer, evidence, [ToolTrace(step=1, tool="detect_changes", summary="done")])


def test_structured_answer_rejects_new_calculations_and_accepts_clean_out_of_scope() -> None:
    scenario = get_scenario("rainy-slowdown")
    execution = execute_tool(
        "compare_periods",
        {"metrics": ["activity_minutes", "evening_walk_minutes"]},
        scenario,
    )
    trace = [ToolTrace(step=1, tool="compare_periods", summary="done")]
    unsupported = AgentAnswer(
        status="completed",
        headline="비교 결과",
        findings=[AgentFinding(text="두 지표의 차이는 999%포인트입니다.", evidence_ids=["E1", "E2"])],
        limitations=[],
    )
    unsupported_headline = AgentAnswer(
        status="completed",
        headline="최근 값은 999회입니다.",
        findings=[AgentFinding(text=execution.evidence[0].statement, evidence_ids=["E1"])],
        limitations=[],
    )
    out_of_scope = AgentAnswer(
        status="out_of_scope",
        headline="진단할 수 없습니다.",
        findings=[],
        limitations=["수의학적 진단은 제공하지 않습니다."],
    )

    assert not _agent_answer_is_valid(unsupported, execution.evidence, trace)
    assert not _agent_answer_is_valid(unsupported_headline, execution.evidence, trace)
    assert _agent_answer_is_valid(out_of_scope, [], [])
