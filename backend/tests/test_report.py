from app.agent import investigate
from app.config import Settings
from app.synthetic import get_scenario


def test_report_links_claims_to_evidence_without_api_key() -> None:
    report = investigate(
        get_scenario("night-restlessness"),
        "최근 우리 강아지에게 달라진 점이 있어?",
        use_llm=True,
        settings=Settings(openai_api_key=None),
    )

    assert report.mode == "deterministic_fallback"
    assert report.evidence
    assert all(f"[{item.id}]" in report.summary for item in report.evidence[:3])
    assert "긁기가" in report.summary
    assert "분으로" in report.summary
    assert "인과관계" in report.limitations[0]


def test_no_change_report_is_explicit() -> None:
    report = investigate(
        get_scenario("stable-routine"),
        "최근 변화가 있어?",
        use_llm=False,
        settings=Settings(openai_api_key=None),
    )

    assert report.changes == []
    assert "발견되지 않았습니다" in report.headline


def test_fallback_includes_event_only_once() -> None:
    report = investigate(
        get_scenario("rainy-slowdown"),
        "최근 변화가 있어?",
        use_llm=False,
        settings=Settings(openai_api_key=None),
    )

    event = next(item for item in report.evidence if item.kind == "event")
    assert report.summary.count(event.statement) == 1
