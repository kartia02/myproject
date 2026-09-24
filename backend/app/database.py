from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlalchemy.pool import StaticPool

from .config import get_settings
from .schemas import DailyRecord, PetEvent, ScenarioDetail, ScenarioSummary
from .synthetic import all_scenarios


class Base(DeclarativeBase):
    pass


# investigation_runs.mode에 기록하는 값. Agent API를 호출한 조사는 응답이 채택되지 않아도
# 비용이 발생하므로 agent_rejected로 남기고 일일 총량 상한에 함께 반영한다.
AGENT_ATTEMPT_MODES = ("agent", "agent_rejected")
PERSONAL_DEMO_SCENARIO_ID = "personal-browser-demo"


class ScenarioRow(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    dog_name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer)
    records: Mapped[list["DailyRecordRow"]] = relationship(cascade="all, delete-orphan")
    events: Mapped[list["PetEventRow"]] = relationship(cascade="all, delete-orphan")


class DailyRecordRow(Base):
    __tablename__ = "daily_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    activity_minutes: Mapped[float] = mapped_column(Float)
    sleep_hours: Mapped[float] = mapped_column(Float)
    night_awakenings: Mapped[float] = mapped_column(Float)
    meal_grams: Mapped[float] = mapped_column(Float)
    evening_walk_minutes: Mapped[float] = mapped_column(Float)
    scratching_count: Mapped[float] = mapped_column(Float)
    barking_count: Mapped[float] = mapped_column(Float)
    temperature_c: Mapped[float] = mapped_column(Float)
    precipitation_mm: Mapped[float] = mapped_column(Float)


class PetEventRow(Base):
    __tablename__ = "pet_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(Text)


class InvestigationRunRow(Base):
    __tablename__ = "investigation_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    question: Mapped[str] = mapped_column(String(300))
    mode: Mapped[str] = mapped_column(String(40))
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


settings = get_settings()
engine_options: dict = {"pool_pre_ping": True}
if settings.database_url == "sqlite:///:memory:":
    engine_options.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
elif settings.database_url.startswith("postgresql"):
    engine_options["pool_recycle"] = 300
engine = create_engine(settings.database_url, **engine_options)


def initialize_database() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for detail in all_scenarios():
            summary = detail.scenario
            row = session.get(ScenarioRow, summary.id)
            if row is None:
                row = ScenarioRow(
                    id=summary.id,
                    name=summary.name,
                    dog_name=summary.dog_name,
                    description=summary.description,
                    start_date=summary.start_date,
                    end_date=summary.end_date,
                    days=summary.days,
                )
                session.add(row)
                session.flush()
            else:
                stored_records = session.scalars(
                    select(DailyRecordRow)
                    .where(DailyRecordRow.scenario_id == summary.id)
                    .order_by(DailyRecordRow.date)
                ).all()
                stored_events = session.scalars(
                    select(PetEventRow)
                    .where(PetEventRow.scenario_id == summary.id)
                    .order_by(PetEventRow.date)
                ).all()
                record_fields = tuple(DailyRecord.model_fields)
                records_match = len(stored_records) == len(detail.records) and all(
                    all(getattr(stored, field) == getattr(expected, field) for field in record_fields)
                    for stored, expected in zip(stored_records, detail.records, strict=True)
                )
                events_match = [
                    PetEvent.model_validate(item, from_attributes=True) for item in stored_events
                ] == detail.events
                summary_matches = all(
                    getattr(row, field) == getattr(summary, field)
                    for field in ("name", "dog_name", "description", "start_date", "end_date", "days")
                )
                if records_match and events_match and summary_matches:
                    continue
                row.name = summary.name
                row.dog_name = summary.dog_name
                row.description = summary.description
                row.start_date = summary.start_date
                row.end_date = summary.end_date
                row.days = summary.days
                session.execute(delete(DailyRecordRow).where(DailyRecordRow.scenario_id == summary.id))
                session.execute(delete(PetEventRow).where(PetEventRow.scenario_id == summary.id))
            session.add_all(
                [DailyRecordRow(scenario_id=summary.id, **record.model_dump()) for record in detail.records]
            )
            session.add_all(
                [PetEventRow(scenario_id=summary.id, **event.model_dump()) for event in detail.events]
            )
        if session.get(ScenarioRow, PERSONAL_DEMO_SCENARIO_ID) is None:
            session.add(
                ScenarioRow(
                    id=PERSONAL_DEMO_SCENARIO_ID,
                    name="브라우저 개인 기록",
                    dog_name="개인 기록",
                    description="원본 기록을 저장하지 않는 브라우저 기반 분석",
                    start_date=date(1970, 1, 1),
                    end_date=date(1970, 1, 1),
                    days=0,
                )
            )
        session.commit()


def list_scenarios() -> list[ScenarioSummary]:
    with Session(engine) as session:
        rows = session.scalars(
            select(ScenarioRow)
            .where(ScenarioRow.id != PERSONAL_DEMO_SCENARIO_ID)
            .order_by(ScenarioRow.id)
        ).all()
        return [
            ScenarioSummary(
                id=row.id,
                name=row.name,
                dog_name=row.dog_name,
                description=row.description,
                start_date=row.start_date,
                end_date=row.end_date,
                days=row.days,
            )
            for row in rows
        ]


def load_scenario(scenario_id: str) -> ScenarioDetail | None:
    with Session(engine) as session:
        row = session.get(ScenarioRow, scenario_id)
        if row is None:
            return None
        record_rows = session.scalars(
            select(DailyRecordRow)
            .where(DailyRecordRow.scenario_id == scenario_id)
            .order_by(DailyRecordRow.date)
        ).all()
        event_rows = session.scalars(
            select(PetEventRow)
            .where(PetEventRow.scenario_id == scenario_id)
            .order_by(PetEventRow.date)
        ).all()
        return ScenarioDetail(
            scenario=ScenarioSummary.model_validate(row, from_attributes=True),
            records=[DailyRecord.model_validate(item, from_attributes=True) for item in record_rows],
            events=[PetEvent.model_validate(item, from_attributes=True) for item in event_rows],
        )


def count_agent_attempts_since(threshold: datetime) -> int:
    with Session(engine) as session:
        total = session.scalar(
            select(func.count())
            .select_from(InvestigationRunRow)
            .where(
                InvestigationRunRow.mode.in_(AGENT_ATTEMPT_MODES),
                InvestigationRunRow.created_at >= threshold,
            )
        )
        return int(total or 0)


def save_investigation(scenario_id: str, question: str, mode: str, report: dict) -> None:
    with Session(engine) as session:
        session.add(
            InvestigationRunRow(
                scenario_id=scenario_id,
                question=question,
                mode=mode,
                report=report,
            )
        )
        session.commit()


def save_personal_demo_investigation(mode: str, report: dict) -> None:
    """비용 집계에 필요한 실행 메타데이터만 저장하고 사용자 입력은 보관하지 않는다."""
    usage = report.get("agent_usage")
    save_investigation(
        PERSONAL_DEMO_SCENARIO_ID,
        "[personal demo question not stored]",
        mode,
        {
            "scenario_id": PERSONAL_DEMO_SCENARIO_ID,
            "status": report.get("status"),
            "mode": report.get("mode"),
            "agent_usage": usage,
        },
    )
