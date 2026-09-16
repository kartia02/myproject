from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlalchemy.pool import StaticPool

from .config import get_settings
from .schemas import DailyRecord, PetEvent, ScenarioDetail, ScenarioSummary
from .synthetic import all_scenarios


class Base(DeclarativeBase):
    pass


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
                records_match = [
                    DailyRecord.model_validate(item, from_attributes=True) for item in stored_records
                ] == detail.records
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
        session.commit()


def list_scenarios() -> list[ScenarioSummary]:
    with Session(engine) as session:
        rows = session.scalars(select(ScenarioRow).order_by(ScenarioRow.id)).all()
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
