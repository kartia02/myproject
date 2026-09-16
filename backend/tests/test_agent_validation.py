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
