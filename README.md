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
- 계정 없이 반려견 이름을 등록하고 합성 예시 또는 개인 기록 모드를 선택하는 브라우저 기반 체험
- 개인 기록은 브라우저 `localStorage`에 보관하고 30일 Baseline + 최근 7일이 모이면 동일한 분석 흐름으로 조사

자세한 결정은 [구현 명세](docs/implementation-spec.md)에 기록되어 있습니다. 질문에 따라 Tool을 선택하는 다음 단계는 [Agent 오케스트레이션 전환 계획](docs/agent-orchestration-plan.md)을 따릅니다.

## 공개 데모

- Frontend: https://pet-detective-one.vercel.app
- Backend API: https://pet-detective-api.onrender.com
- API 문서: https://pet-detective-api.onrender.com/docs

2026-09-21 기준으로 Vercel → Render → Neon → Python 변화 분석 → GPT-5.6 Luna Tool Calling 흐름을 공개 환경에서 검증했습니다. Render 무료 인스턴스는 유휴 상태에서 절전되므로 첫 접속에는 약 1분이 걸릴 수 있습니다. Vercel의 배포별 Preview URL은 Render CORS 허용 목록에 없으므로 고정 Production 도메인을 사용합니다.

처음 접속하면 반려견 이름을 등록하고 두 가지 체험 중 하나를 선택합니다.

1. **예시 데이터로 바로 체험**: 60일 합성 기록으로 전체 분석 흐름을 즉시 확인합니다. 화면에 등록한 이름을 사용하지만 기록 자체는 실제 반려견 데이터가 아닙니다.
2. **직접 기록 시작**: 하루 단위 기록을 브라우저에 저장합니다. 서로 다른 날짜의 기록이 37일 이상 모이면 최초 30일을 Baseline, 마지막 7일을 비교 구간으로 분석합니다.

계정은 만들지 않습니다. 이름과 직접 입력한 기록은 Neon에 저장하지 않고 현재 브라우저에만 남습니다. 분석을 실행할 때에만 필요한 기록이 Backend로 전송되며, Neon에는 일일 Agent 예산 관리를 위한 익명 실행 메타데이터만 저장합니다. 브라우저 데이터를 지우거나 다른 기기를 사용하면 기록이 이어지지 않으므로 개인 기록 화면에서 JSON 백업을 내려받을 수 있습니다.

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

1. 반려견 이름을 입력하고 예시 데이터 모드 또는 직접 기록 모드를 선택합니다.
2. 예시 데이터 모드에서 보리·몽이·두부 합성 시나리오와 분석 결과를 확인합니다.
3. 직접 기록 모드에서 하루 기록을 저장한 뒤 새로고침해도 기록이 남는지 확인합니다.
4. 직접 기록이 37일 미만일 때 남은 날짜 수를 안내하고 Agent를 호출하지 않는지 확인합니다.
5. 37일 이상일 때 결과 배지가 `GPT-5.6 Luna`인지 확인합니다.
6. Neon Console에는 이름·원본 기록·자유 입력 질문 대신 익명 실행 메타데이터만 추가됐는지 확인합니다.

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

공개 배포에서도 세 시나리오 조회, `GPT-5.6 Luna` 리포트, Evidence 4건, Tool 호출 과정, Neon 조사 기록 저장을 확인했습니다. 운영 설정과 재배포 순서는 [배포 계획](docs/deployment-plan.md)을 따릅니다.

## API

- `GET /health`
- `GET /api/scenarios`
- `GET /api/scenarios/{scenario_id}`
- `POST /api/investigations`
- `POST /api/personal-investigations`

조사 요청 예시:

```json
{
  "scenario_id": "night-restlessness",
  "question": "최근 우리 강아지에게 달라진 점이 있어?",
  "use_llm": true
}
```

직접 기록 조사 요청은 `pet_name`, 날짜별 `records`, 선택적인 `events`, `question`, `use_llm`을 전달합니다. 날짜 중복, 허용 범위를 벗어난 수치, 기록 범위 밖의 이벤트는 `422`로 거절합니다. 37일 미만의 요청은 Agent를 호출하지 않고 필요한 추가 기록 일수를 반환합니다.

## 프로젝트 경계

이 서비스는 합성 또는 사용자가 직접 입력한 기록에서 관찰된 변화와 함께 나타난 기록을 설명합니다. 인과관계, 질병, 수의학적 판단은 제공하지 않습니다. 현재 버전에는 회원가입, 기기 간 동기화, Timeline Search, Adaptive Baseline이 포함되지 않습니다.
