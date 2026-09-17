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

자세한 결정은 [구현 명세](docs/implementation-spec.md)에 기록되어 있습니다. 질문에 따라 Tool을 선택하는 다음 단계는 [Agent 오케스트레이션 전환 계획](docs/agent-orchestration-plan.md)을 따릅니다.

## 로컬 실행

### 1. 환경변수 준비

저장소 루트에 `.env`를 만들고 OpenAI API Key와 DB 주소를 설정합니다. `.env`는 Git에 포함되지 않습니다.

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-luna
DATABASE_URL=postgresql://USER:PASSWORD@ep-...-pooler....neon.tech/neondb?sslmode=require&channel_binding=require
```

Neon 없이 화면만 확인하려면 `DATABASE_URL=sqlite:///./pet_detective.db`를 사용할 수 있습니다. `OPENAI_API_KEY`가 비어 있으면 Luna 대신 계산된 Evidence를 사용하는 안전한 리포트를 반환합니다.

### 2. Backend 실행

PowerShell 터미널에서 다음 명령을 실행합니다.

```powershell
cd D:\MyProject\backend
python -m pip install -r requirements-dev.txt
python check_database.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`check_database.py`가 `Database connection OK`를 출력하면 Neon 인증과 SQL 실행이 정상입니다. Backend 시작 시 필요한 테이블을 만들고 Synthetic Scenario 3종과 180개의 일별 기록을 동기화합니다.

### 3. Frontend 실행

새 PowerShell 터미널을 열어 실행합니다.

```powershell
cd D:\MyProject\frontend
npm install
npm run dev -- --host 127.0.0.1
```

웹은 `http://127.0.0.1:5173`, API 문서는 `http://127.0.0.1:8000/docs`에서 확인합니다. Vite 개발 서버가 `/api` 요청을 Backend로 전달합니다.

### 4. 화면에서 직접 확인

1. 보리 시나리오에서 야간 각성·긁기 증가와 저녁 산책 감소를 확인합니다.
2. 몽이 시나리오에서 활동 시간·저녁 산책 감소와 강수 이벤트를 확인합니다.
3. 두부 시나리오에서 뚜렷한 변화가 없다는 결과를 확인합니다.
4. 변화가 있는 시나리오의 결과 배지가 `GPT-5.6 Luna`인지 확인합니다.
5. Neon Console에서 `investigation_runs` 행이 추가됐는지 확인합니다.

서버를 종료할 때는 각 터미널에서 `Ctrl+C`를 누릅니다.

### Docker Compose 실행

Docker가 설치된 환경에서는 로컬 PostgreSQL을 포함한 전체 서비스를 실행할 수 있습니다.

```bash
docker compose up --build
```

이 경우 웹은 `http://localhost:8080`, API 문서는 `http://localhost:8000/docs`에서 확인합니다. 운영 PostgreSQL은 Neon을 사용하며 세부 설정은 [Neon 연결 문서](docs/neon-setup.md)를 따릅니다.

## 검증

```powershell
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
