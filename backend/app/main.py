import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import investigate
from .budget import agent_calls_remaining
from .config import get_settings
from .database import initialize_database, list_scenarios, load_scenario, save_investigation
from .rate_limit import enforce_rate_limit
from .schemas import InvestigationReport, InvestigationRequest, ScenarioDetail, ScenarioSummary


# 배포 환경에서는 호스팅 대시보드의 로그가 유일한 디버깅 수단이다. 설정하지 않으면
# 애플리케이션 경고에 시각과 출처가 붙지 않아 uvicorn 로그와 구분하기 어렵다.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

logger = logging.getLogger(__name__)
settings = get_settings()

# 무료 호스팅에서는 절전에서 깨어날 때마다 이 경로가 실행되고 Neon 컴퓨트도 함께 깨어난다.
# 일시적인 연결 실패를 흡수한다.
STARTUP_DB_ATTEMPTS = 3
STARTUP_DB_BACKOFF_SECONDS = 1.0


@asynccontextmanager
async def lifespan(_: FastAPI):
    for attempt in range(1, STARTUP_DB_ATTEMPTS + 1):
        try:
            initialize_database()
            logger.info("Database initialized; scenarios are ready")
            break
        except Exception:
            if attempt == STARTUP_DB_ATTEMPTS:
                # 기동을 중단하면 재시작 루프에 빠진다. /health는 계속 응답하게 두고
                # 다음 기동에서 회복시킨다.
                logger.exception(
                    "Database initialization failed after %d attempts; starting anyway",
                    STARTUP_DB_ATTEMPTS,
                )
                break
            delay = STARTUP_DB_BACKOFF_SECONDS * attempt
            logger.warning(
                "Database initialization attempt %d failed; retrying in %.1fs", attempt, delay
            )
            await asyncio.sleep(delay)
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


def _stored_mode(report: InvestigationReport) -> str:
    # Agent를 호출했으면 응답이 채택되지 않아도 비용이 발생한다. 일일 상한이 이를 놓치지
    # 않도록 호출 사실을 기록한다. 응답 본문의 mode는 그대로 둔다.
    if report.mode != "agent" and report.agent_usage is not None:
        return "agent_rejected"
    return report.mode


@app.post(
    "/api/investigations",
    response_model=InvestigationReport,
    dependencies=[Depends(enforce_rate_limit)],
)
def run_investigation(payload: InvestigationRequest) -> InvestigationReport:
    scenario = load_scenario(payload.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="시나리오를 찾을 수 없습니다.")
    use_llm = payload.use_llm
    if use_llm and settings.openai_api_key and agent_calls_remaining(settings) <= 0:
        logger.warning("Daily agent call limit reached; serving the calculated report")
        use_llm = False
    report = investigate(scenario, payload.question, use_llm, settings)
    save_investigation(
        payload.scenario_id,
        payload.question,
        _stored_mode(report),
        report.model_dump(mode="json"),
    )
    return report
