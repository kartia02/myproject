from app.agent import _agent_response_is_valid, _required_tools_were_called, investigate
from app.config import Settings
from app.schemas import ToolTrace
from app.synthetic import get_scenario


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


def test_agent_mode_requires_each_investigation_tool_exactly_once() -> None:
    complete = [
        ToolTrace(step=1, tool="get_baseline", summary="done"),
        ToolTrace(step=2, tool="detect_changes", summary="done"),
        ToolTrace(step=3, tool="compare_periods", summary="done"),
        ToolTrace(step=4, tool="get_events", summary="done"),
    ]
    duplicate = complete[:-1] + [ToolTrace(step=4, tool="detect_changes", summary="done")]

    assert _required_tools_were_called(complete)
    assert not _required_tools_were_called(complete[:-1])
    assert not _required_tools_were_called(duplicate)
