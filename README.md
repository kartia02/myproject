# Pet Detective

개별 반려견의 일상 기록으로 Personal Baseline을 만들고, 최근 변화를 탐지한 뒤 Agent가 관련 기록을 조사해 Evidence와 함께 설명하는 공개 데모입니다.

## 현재 구현

- 60일 Synthetic Scenario 3종과 평가 전용 Ground Truth
- Fixed Personal Baseline과 변화율·절대 변화량·효과크기를 함께 사용하는 설명 가능한 변화 탐지
- `get_baseline`, `detect_changes`, `compare_periods`, `get_events` Tool
- OpenAI Responses API 기반 Agent 및 필수 Tool 호출·문장별 Evidence·수치·금지 주장 검증
- API 실패 시에도 동작하는 계산 기반 안전 리포트
- FastAPI REST API, React Dashboard, PostgreSQL 저장
- IP 기반 Rate Limit, Agent 최대 4 Step, 출력 토큰 제한
- Docker Compose 실행 환경과 정량 평가 스크립트

자세한 결정은 [구현 명세](docs/implementation-spec.md)에 기록되어 있습니다.

## 로컬 실행

Docker가 설치되어 있으면 다음과 같이 전체 서비스를 실행합니다.

```bash
cp .env.example .env
docker compose up --build
```

웹은 `http://localhost:8080`, API 문서는 `http://localhost:8000/docs`에서 확인할 수 있습니다. `OPENAI_API_KEY`가 비어 있으면 동일한 분석 결과를 규칙 기반 Evidence 리포트로 제공합니다.

Docker 없이 개발할 때는 Backend와 Frontend를 각각 실행합니다.

```bash
cd backend
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

기본 개발 DB는 SQLite이며 Docker 환경에서는 PostgreSQL을 사용합니다.

## 검증

```bash
cd backend
pytest
cd ../evaluation
python evaluate.py
# 유료 실제 모델 평가(키 설정 후)
python evaluate_live.py --runs 1
cd ../frontend
npm run build
```

평가 결과는 변화 탐지 Precision·Recall·F1, 변화 시작일 오차, 강건성 케이스 통과 수, Evidence Precision, Unsupported Claim Rate를 출력합니다.
현재 고정 평가 결과는 [`evaluation/results.json`](evaluation/results.json)에 보관합니다. 3개 공개 시나리오와 23개 결정론적 강건성 케이스를 검증하며, 실제 Luna 응답 평가는 API Key 설정 후 별도 실행해야 합니다.
실제 Luna 표본 결과는 [`evaluation/live_results.json`](evaluation/live_results.json)에 보관합니다. Agent 리포트에는 API 요청 수, Tool 호출 수, 입력·출력 토큰, 지연 시간과 채택 여부가 포함됩니다.

## API

- `GET /health`
- `GET /api/scenarios`
- `GET /api/scenarios/{scenario_id}`
- `POST /api/investigations`

조사 요청 예시:

```json
{
  "scenario_id": "night-restlessness",
  "question": "최근 우리 강아지에게 달라진 점이 있어?",
  "use_llm": true
}
```

## 프로젝트 경계

이 서비스는 합성 기록에서 관찰된 변화와 함께 나타난 기록을 설명합니다. 인과관계, 질병, 수의학적 판단은 제공하지 않습니다. v1.0에는 회원가입, 업로드, Timeline Search, Adaptive Baseline이 포함되지 않습니다.
