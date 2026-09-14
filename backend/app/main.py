from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import investigate
from .config import get_settings
from .database import initialize_database, list_scenarios, load_scenario, save_investigation
from .rate_limit import enforce_rate_limit
from .schemas import InvestigationReport, InvestigationRequest, ScenarioDetail, ScenarioSummary


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/scenarios", response_model=list[ScenarioSummary])
def scenarios() -> list[ScenarioSummary]:
    return list_scenarios()


@app.get("/api/scenarios/{scenario_id}", response_model=ScenarioDetail)
def scenario_detail(scenario_id: str) -> ScenarioDetail:
    scenario = load_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다.")
    return scenario


@app.post(
    "/api/investigations",
    response_model=InvestigationReport,
    dependencies=[Depends(enforce_rate_limit)],
)
def run_investigation(payload: InvestigationRequest) -> InvestigationReport:
    if load_scenario(payload.scenario_id) is None:
        raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다.")
    report = investigate(payload.scenario_id, payload.question, payload.use_llm, settings)
    save_investigation(
        payload.scenario_id,
        payload.question,
        report.mode,
        report.model_dump(mode="json"),
    )
    return report
