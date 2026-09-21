# 배포 계획

Pet Detective 공개 데모를 월 결제금 $0으로 배포한다. 백엔드는 Render 무료 웹 서비스, 프론트엔드는 Vercel Hobby, 데이터베이스는 Neon 무료 티어를 사용한다. AWS 이전은 이 단계에 포함하지 않으며 11절에 선택지로만 기록한다.

## 1. 구성

| 조각 | 서비스 | 비용 | 비고 |
| --- | --- | --- | --- |
| Backend | Render Web Service (Docker) | $0 | 15분 유휴 시 절전, 재기동 40~60초 |
| Frontend | Vercel Hobby | $0 | 정적 CDN, 백엔드 상태와 무관하게 즉시 로드 |
| Database | Neon PostgreSQL | $0 | 기존 프로젝트 재사용, [Neon 연결 문서](neon-setup.md) |
| LLM | OpenAI Responses API | 조사 1회 약 $0.00083 | 초기 일일 상한 50회와 OpenAI 월 한도로 비용 통제 |

프론트엔드와 백엔드는 서로 다른 도메인에 배포한다. 코드가 이미 `VITE_API_BASE_URL`과 `ALLOWED_ORIGINS`로 분리 배포를 전제하므로 추가 구조 변경이 없다. `frontend/Dockerfile`과 `frontend/nginx.conf`는 Docker Compose 로컬 실행 전용으로 남긴다.

### 무료 티어의 전제

이 계획의 모든 수정 사항은 다음 두 가지 전제에서 나온다.

1. **백엔드 프로세스는 자주 죽고 자주 다시 뜬다.** 15분간 요청이 없으면 절전되고, 다음 요청에 새 프로세스로 기동된다. 따라서 시작 경로는 빠르고 실패에 강해야 하며, 프로세스 메모리에 보관하는 상태는 언제든 사라진다고 가정해야 한다.
2. **Neon 컴퓨트도 유휴 시 잠든다.** 백엔드 콜드 스타트와 데이터베이스 콜드 스타트가 겹칠 수 있다.

## 2. 배포 전 필수 수정

이 절의 일곱 항목은 모두 적용 완료다. 2.7은 코드 변경 없이 환경변수로 처리하므로 8절에서 설정한다.

### 2.1 컨테이너 포트와 프록시 헤더

`backend/Dockerfile`의 `CMD`가 포트 8000을 고정하고 있다. Render는 `PORT` 환경변수로 포트를 주입하므로 이를 읽도록 바꾼다. 동시에 프록시 뒤에서 클라이언트 IP를 복원하도록 `--proxy-headers`와 `--forwarded-allow-ips`를 추가한다.

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]
```

`--forwarded-allow-ips=*`는 신뢰할 수 있는 프록시 뒤에서만 안전하다. Render는 이 조건을 만족한다.

### 2.2 Rate Limit의 클라이언트 IP

`backend/app/rate_limit.py`가 `request.client.host`를 사용한다. 프록시 뒤에서는 이 값이 프록시 IP로 고정되어 전체 방문자가 버킷 하나를 공유하고, 한 명이 분당 10회를 쓰면 모두 429를 받는다. `X-Forwarded-For`의 첫 번째 IP를 우선 사용하도록 고친다.

```python
def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

`X-Forwarded-For`는 클라이언트가 위조할 수 있다. 이 값은 분당 제한의 키로만 쓰고, 실제 지출 상한은 2.3의 총량 제한이 담당한다.

### 2.3 LLM 호출 일일 총량 상한

`agent_daily_call_limit` 설정을 추가하고 기본값을 50으로 둔다. 상한에 도달하면 `use_llm`이 참이어도 API를 호출하지 않고 `deterministic_fallback` 경로를 사용한다. 이 경로는 `backend/app/agent.py`에 이미 구현되어 있어 방문자에게는 오류가 아니라 정상 응답으로 보인다.

카운터는 메모리가 아니라 데이터베이스에서 센다. 1절의 전제 1에 따라 메모리 카운터는 절전마다 0으로 리셋되어 상한 역할을 하지 못한다. `investigation_runs`에서 기준 시각 이후의 Agent 호출 행 수를 세고, 그 값이 상한 이상이면 건너뛴다. 조사 요청 1건당 `SELECT COUNT` 한 번이 늘어난다.

**채택되지 않은 Agent 응답도 상한에 반영한다.** `mode = 'agent'`만 세면 검증에 실패해 계산 리포트로 대체된 조사가 빠지는데, 그 호출도 토큰 비용은 이미 발생했다. 실제 지출보다 상한이 느슨해지지 않게 `investigation_runs.mode`에 `agent_rejected`를 함께 기록하고 두 값을 모두 센다. `mode` 컬럼은 `String(40)`이라 스키마 변경이 필요 없고, API 응답 본문의 `mode`는 기존 두 값을 그대로 유지해 프론트엔드 계약을 바꾸지 않는다.

상한을 `0`으로 두면 API를 전혀 호출하지 않는다. 환경변수만으로 Agent를 즉시 끌 수 있는 비상 스위치로 쓴다.

기준 시각은 KST 자정으로 한다. UTC 자정을 쓰면 한국 시간 오전 9시에 상한이 초기화되어 확인하기 불편하다. 비교는 timezone-aware datetime으로 수행해 SQLite와 PostgreSQL에서 같게 동작하게 한다.

공개 배포의 초기 상한 50회는 측정 평균 기준 하루 약 $0.04, 30일 약 $1.25다. 실제 비용은 토큰 사용량에 따라 달라지므로 OpenAI 측 월 사용 한도를 별도로 둔다.

### 2.4 OpenAI 클라이언트 타임아웃

`backend/app/agent.py`가 `OpenAI(api_key=...)`를 기본 설정으로 만든다. SDK 기본 타임아웃은 10분 수준이고 기본 재시도도 있다. 측정된 정상 지연이 6.5초인데, API가 응답하지 않으면 방문자는 스피너를 10분 동안 보게 되고 그 사이 워커 스레드 하나가 점유된다. 무료 단일 인스턴스에서는 이 영향이 크다.

```python
client = OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1)
```

조사 1회에 API 요청이 2회 발생하므로 최악의 경우가 약 60초로 묶인다. 타임아웃이 발생하면 기존 `except` 절이 잡아서 계산 리포트로 응답한다.

### 2.5 시작 시 데이터베이스 초기화 내구성

가장 중요한 수정이다. `backend/app/main.py`의 lifespan이 `initialize_database()`를 호출하는데, 이 함수가 예외를 던지면 애플리케이션이 기동에 실패한다. 1절의 전제 1에 따라 이 경로는 배포 시 한 번이 아니라 **절전에서 깨어날 때마다** 실행된다. 즉 Neon 연결이 한 번 실패할 때마다 서비스 전체가 죽고, Render가 재시작을 반복할 수 있다.

두 가지를 넣는다.

1. **재시도** 짧은 백오프로 3회까지 재시도한다. Neon 컴퓨트가 잠들어 있다가 깨는 동안의 일시적 실패를 흡수한다.
2. **실패해도 프로세스를 죽이지 않는다** 최종 실패 시 예외를 로그로 남기고 기동은 계속한다. `/health`가 계속 응답하므로 Render가 재시작 루프에 빠지지 않고, 데이터베이스가 돌아오면 다음 기동에서 회복된다. 그동안 `/api/scenarios`는 오류를 반환하지만, 이는 서비스 전체가 내려가는 것보다 낫다.

### 2.6 프론트엔드의 절전 대응

백엔드가 자고 있으면 첫 요청이 40~60초 걸린다. Neon까지 잠들어 있으면 조금 더 걸린다. 화면이 이유 없이 멈춘 것처럼 보이지 않게 세 가지를 넣는다.

1. `App.tsx` 마운트 시 시나리오 목록 요청과 함께 `/health`를 호출해 백엔드를 미리 깨운다.
2. 첫 응답이 3초를 넘기면 "서버를 깨우는 중입니다. 최대 1분이 걸릴 수 있습니다." 안내를 표시한다.
3. 네트워크 실패 시 `api.ts`가 던지는 메시지가 브라우저 기본 문구(`Failed to fetch`)라서 영어로 노출된다. 한국어 안내로 감싼다.

`/health`는 데이터베이스를 건드리지 않으므로 깨우기 용도로 적합하다.

### 2.7 CORS 도메인과 미리보기 배포

`ALLOWED_ORIGINS`는 코드 수정 없이 Render 환경변수로 지정한다. Vercel 도메인이 확정된 뒤 8절에서 설정한다. 이 값이 비어 있거나 틀리면 브라우저가 요청을 차단하는데, **백엔드 로그에는 아무 오류도 남지 않고 브라우저 콘솔에만 나타난다.** 증상을 미리 알아둔다.

Vercel은 배포마다 `<프로젝트>-<해시>.vercel.app` 형태의 미리보기 주소를 따로 발급한다. 이 주소들은 `ALLOWED_ORIGINS` 목록에 없으므로 미리보기 배포에서는 API 호출이 차단된다. 운영 도메인만 쓰기로 하고 미리보기는 화면 확인용으로만 사용한다. 미리보기에서도 API를 쓰려면 `allow_origin_regex`로 전환해야 하는데, 공개 데모에서 허용 범위를 넓히는 변경이므로 이 단계에서는 하지 않는다.

## 3. 배포 전 권장 수정

어느 항목도 배포 성공이나 데모 동작을 좌우하지 않는다. 판단 근거를 측정값과 함께 남긴다.

### 3.1 로깅 설정 — 적용 완료

`logging.getLogger(__name__)`만 쓰고 로깅 설정이 없으면 Python 기본 동작에 의존해 WARNING 이상만 시각·레벨·출처 없이 stderr로 나간다. 호스팅 대시보드의 로그가 유일한 디버깅 수단이므로 `backend/app/main.py` 시작 시점에 설정한다.

```python
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
```

루트 로거 레벨이 INFO가 되므로 OpenAI SDK가 사용하는 `httpx`의 요청 로그도 함께 보인다. 조사 1건당 한두 줄이고 메서드·URL·상태 코드만 남으므로 Agent 호출 여부를 확인하는 데 오히려 도움이 된다.

### 3.2 Rate Limit 메모리 정리 — 적용 완료

`rate_limit.py`의 `_requests`는 IP별 버킷을 쌓기만 하고 지우지 않아 방문한 IP 수만큼 항목이 영구히 남는다. 항목당 약 400~500바이트다.

이 배포에서는 실질적 위험이 낮다. 1절의 전제 1에 따라 15분마다 프로세스가 죽고 메모리가 비워지기 때문이다. 그러나 유료 플랜이나 AWS로 옮겨 상시 가동이 되는 순간 그대로 메모리 증가가 된다. 그때 이 사실을 다시 찾아내지 않도록 지금 닫는다. 5분마다 유휴 IP 항목을 정리하고, 추적 IP 수가 상한을 넘으면 즉시 정리한다.

### 3.3 콜드 스타트 단축 — 하지 않는다

측정 결과 이 항목은 효용이 없다. 이미 동기화된 상태에서 `initialize_database()`가 재기동 시 발행하는 SQL은 **13개(SELECT 9개 + 테이블 존재 확인 4개)**다. Neon이 같은 리전이면 왕복 10~30ms이므로 0.1~0.4초이고, Pydantic 검증 180건은 수 밀리초다. Render 콜드 스타트 40~60초의 1% 미만이다.

콜드 스타트의 실제 원인은 이 함수가 아니라 컨테이너 기동이다. 0.3초를 줄이려고 버전 표식이라는 복잡도를 들이고 데이터 정합성 검사를 약화시킬 이유가 없다.

### 3.4 공유용 메타데이터 — 배포 직후

`frontend/index.html`에 `<title>`과 viewport만 있다. 포트폴리오 링크를 카카오톡, Slack, LinkedIn에 공유하면 미리보기 카드 없이 기본 아이콘으로 표시된다. 다음을 추가한다.

- `<meta name="description">` 한 줄 설명
- Open Graph 태그 (`og:title`, `og:description`, `og:image`, `og:url`)
- 파비콘
- 합성 데이터 데모임을 제목이나 설명에 명시

공개 데모의 첫인상을 결정하는 부분인데 비용은 파일 두 개다. **배포 전에는 할 수 없다.** `og:image`와 `og:url`은 절대 URL이 필요하므로 도메인이 확정된 뒤에 채운다.

### 3.5 보안 응답 헤더 — 나중

`frontend/vercel.json`의 `headers`로 `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`를 지정한다.

실질적 위험 감소는 거의 없다. 이 사이트에는 로그인, 쿠키, 프론트엔드가 보관하는 사용자 데이터가 없어서 클릭재킹으로 탈취할 세션이 없고, 정적 자산은 호스팅이 올바른 타입으로 서빙한다. 이 앱에서 실제로 의미 있는 보안 통제는 백엔드 CORS를 한 도메인으로 제한하는 것이고 그것은 2.7에 있다. 스캐너 지적이나 코드 리뷰를 대비한 위생 수준으로 다룬다.

### 3.6 investigation_runs 보존 정책 — 나중

`save_investigation()`이 모든 조사에 대해 리포트 JSON 전체와 방문자가 입력한 질문 문자열을 저장한다.

- **증가량** 측정 결과 리포트 JSON은 행당 약 4KB다. 하루 200건 상한을 매일 꽉 채우면 0.77MB/일, 23MB/월이다. Neon 무료 저장 0.5GB 기준으로 최대 속도에서도 약 20개월이고, 실제 트래픽은 상한보다 훨씬 낮으므로 수년이다. 지금 할 일이 아니다.
- **정리 시 제약** 2.3의 일일 상한이 이 테이블의 오늘 행 수를 세서 동작한다. 따라서 **정리 작업은 오늘보다 오래된 행만 지워야 한다.** 오늘 행을 지우면 상한이 초기화되어 비용 방어가 풀린다.
- **내용** 질문은 공개 방문자가 자유롭게 입력한 텍스트다(최대 300자). 데이터베이스에 남는다는 점을 인지하고, 문제가 되면 저장을 질문 대신 시나리오 ID와 모드로 줄인다.

### 3.7 `ENVIRONMENT` 설정의 처리 — 작업 없음

`backend/app/config.py`에 `environment` 필드가 있지만 코드 어디에서도 사용하지 않는다. 환경변수로 넣어도 아무 효과가 없다. 둘 중 하나를 고른다.

- 필드를 그대로 두고 환경변수는 설정하지 않는다(기본).
- 이 값으로 `/docs`와 `/openapi.json` 노출을 제어한다. 현재 두 경로는 공개되어 있고 누구나 API를 직접 호출할 수 있다. 포트폴리오로서는 API 문서를 보여주는 것이 장점이므로 **공개 유지를 권한다.** 숨기려면 `FastAPI(docs_url=None, openapi_url=None)`을 프로덕션에서만 적용한다.

## 4. 수정 후 검증

```powershell
cd D:\MyProject\backend
pytest
cd ..\frontend
npm run build
```

`backend/tests/test_api.py`는 `DATABASE_URL`을 인메모리 SQLite로 덮어쓴다. 2.3의 일일 상한 질의가 SQLite에서도 동작하는지 `test_budget.py`로, 2.2의 IP 판별과 3.2의 정리 동작을 `test_rate_limit.py`로 확인한다.

적용 시점의 결과는 백엔드 테스트 28개 통과, 프론트엔드 빌드 성공이다. 프록시 헤더와 일일 상한은 다음을 직접 확인했다.

- 상한 소진 상태에서 `use_llm=true`로 조사해도 `agent_usage`가 `null`이고 API를 호출하지 않는다.
- 서로 다른 IP 12개는 모두 200을 받는다(프록시 뒤 버킷 공유가 해소됨).
- 같은 IP로 12회 연타하면 11번째부터 429가 반환된다.

## 5. 사전 준비

1. **Neon** 기존 프로젝트의 pooled connection string을 준비한다. 새로 만든다면 리전을 Render 백엔드 리전과 가까운 곳으로 고른다. 무료 플랜의 저장 용량과 컴퓨트 시간 한도는 변경될 수 있으므로 현재 조건을 확인한다.
2. **OpenAI** 배포 전용 API Key를 새로 발급한다. 로컬 `.env`의 키와 분리하면 유출 시 한쪽만 폐기할 수 있다.
3. **OpenAI 예산 한도** 대시보드의 Limits에서 월 한도를 $5로, 알림 임계값을 $1로 설정한다. 이것이 최종 하드 스톱이다.
4. **GitHub** 현재 `origin`은 `kartia02/myproject`다. 수정 사항을 커밋하고 push한다. `.env`는 `.gitignore`에 있고 Git 히스토리에 올라간 적이 없음을 확인했다. push 전에 `git status`로 한 번 더 확인한다.

### 청구 사고 방지 규칙

무료 티어에서 예상치 못한 결제가 발생하는 경우는 거의 항상 결제 수단이 이미 등록된 계정이다. 다음을 지킨다.

1. **Render, Vercel, Neon에 결제 수단을 등록하지 않는다.** 세 곳 모두 무료 플랜은 카드 없이 가입된다. 카드가 없으면 한도 초과 시 과금이 아니라 일시 정지로 동작한다. 이 구성의 실패 모드는 "청구서 도착"이 아니라 "사이트가 잠시 멈춤"이어야 한다.
2. **OpenAI만 선불 결제가 필요하다.** $5~10만 충전하고 **자동 충전(auto-recharge)을 반드시 끈다.** 자동 충전을 켜두면 크레딧 소진 시마다 재결제된다. 자동 충전을 끄면 충전액이 물리적 상한이 된다.
3. **한도 관련 메일을 무시하지 않는다.** 하드 캡 구성에서는 메일이 유일한 경고 신호다.
4. 각 서비스의 무료 플랜 조건은 바뀌므로, 가입 시점에 Billing 페이지에서 한도 초과 시 동작을 확인한다.

## 6. Render 백엔드 배포

1. Render에 GitHub 계정으로 가입하고 저장소 접근을 허용한다.
2. New → Web Service → 저장소 선택.
3. 설정값:
   - Root Directory: `backend`
   - Runtime: Docker (`backend/Dockerfile` 자동 감지)
   - Instance Type: Free
   - Health Check Path: `/health`
   - Region: Neon 리전과 가까운 곳
4. 환경변수:

| 키 | 값 |
| --- | --- |
| `DATABASE_URL` | Neon pooled connection string |
| `OPENAI_API_KEY` | 배포 전용 키 |
| `OPENAI_MODEL` | `gpt-5.6-luna` |
| `AGENT_REASONING_EFFORT` | `low` |
| `AGENT_MAX_STEPS` | `4` |
| `AGENT_MAX_OUTPUT_TOKENS` | `900` |
| `AGENT_DAILY_CALL_LIMIT` | `50` |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `ALLOWED_ORIGINS` | 8절에서 설정 |

`ENVIRONMENT`는 3.7의 결정에 따른다. 기본은 설정하지 않는다.

5. 배포 후 로그에서 애플리케이션 시작을 확인한다. 첫 기동 시 `initialize_database()`가 테이블을 만들고 시나리오 3종과 180행을 Neon에 동기화한다.

## 7. 백엔드 단독 검증

프론트엔드를 연결하기 전에 백엔드만 확인한다. 한꺼번에 올리면 문제가 생겼을 때 백엔드 문제인지 CORS 문제인지 구분할 수 없다. `<backend>`는 Render가 발급한 `.onrender.com` 주소다.

```powershell
curl https://<backend>/health
curl https://<backend>/api/scenarios
```

`/health`가 `{"status":"ok"}`를, `/api/scenarios`가 3건을 반환해야 한다. 그다음 조사를 1회 실행한다.

```powershell
curl -X POST https://<backend>/api/investigations -H "Content-Type: application/json" -d "{\"scenario_id\":\"night-restlessness\",\"question\":\"최근 달라진 점이 있어?\",\"use_llm\":true}"
```

응답의 `mode`가 `agent`이면 OpenAI 연결까지 정상이다. `deterministic_fallback`이면 키나 모델 설정을 확인한다. Neon Console에서 `investigation_runs`에 행이 늘었는지도 확인한다.

## 8. Vercel 프론트엔드 배포

1. 기존 Vercel 계정으로 로그인하고 Add New → Project → GitHub 저장소 연결. 결제 수단은 등록하지 않는다.
2. 설정값:
   - Framework Preset: Vite (자동 감지)
   - Root Directory: `frontend`
   - Install Command: `npm ci`
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - 환경변수 `VITE_API_BASE_URL` = `https://<backend>` (끝에 슬래시 없음), Production 환경에 설정
3. `package.json`의 의존성이 모두 `latest`이므로 Install Command를 `npm ci`로 고정해 `package-lock.json`의 버전으로 빌드한다. 빌드 결과가 매번 달라지는 것을 막는다.
4. Node 버전은 Project Settings에서 확인한다. 기본 LTS로 충분하다.
5. 배포가 끝나면 `<project>.vercel.app` 주소를 받는다.
6. Render로 돌아가 `ALLOWED_ORIGINS`에 그 주소를 넣고 재배포한다.

```
ALLOWED_ORIGINS=https://<project>.vercel.app
```

`VITE_API_BASE_URL`은 빌드 시점에 번들에 박힌다. 값을 바꾸면 Vercel에서 다시 배포해야 한다.

## 9. 최종 확인

공개 URL에서 순서대로 확인한다. 항목 1~4는 README의 로컬 검증 절차와 같다.

1. 보리 시나리오에서 야간 각성·긁기 증가와 저녁 산책 감소가 보인다.
2. 몽이 시나리오에서 활동 시간·저녁 산책 감소와 강수 이벤트가 보인다.
3. 두부 시나리오에서 뚜렷한 변화가 없다는 결과가 나온다.
4. 변화가 있는 시나리오의 결과 배지가 `GPT-5.6 Luna`다.
5. Neon Console의 `investigation_runs`에 행이 추가된다.
6. 20분 이상 방치한 뒤 다시 열었을 때, 화면은 즉시 뜨고 "서버를 깨우는 중" 안내가 표시된 후 정상 응답으로 이어진다.
7. 브라우저 콘솔에 CORS 오류가 없다.
8. 휴대폰 등 다른 네트워크에서도 동작한다.
9. 분당 제한을 초과했을 때 한국어 429 메시지가 화면에 보인다.
10. 링크를 메신저에 붙여 미리보기 카드가 나오는지 확인한다(3.4를 적용한 경우).

## 10. 운영

**비용 방어는 3중이다.** OpenAI 대시보드 월 한도가 최종 차단선이고, 일일 총량 상한이 실제 지출을 묶고, IP별 분당 제한이 단순 연타를 막는다. 셋 중 어느 하나도 단독으로는 충분하지 않다.

**Render 무료 티어의 한계를 전제로 운영한다.** 월 인스턴스 시간 한도가 있어 외부 핑으로 24시간 깨워두면 한도에 근접한다. 기본은 절전을 허용하고 2.6의 깨우기로 대응한다. 무료 티어 조건은 변경될 수 있으므로 배포 시점에 현재 약관을 확인한다.

**로그는 Render 대시보드의 Logs 탭에서 본다.** Agent 응답이 검증에 실패하면 `Agent response failed tool or evidence validation` 경고가, API 호출 자체가 실패하면 `Agent investigation failed` 예외가 남는다. 두 경우 모두 서비스는 계산 리포트로 계속 응답한다. 3.1을 적용하면 이 로그가 안정적으로 보인다.

**롤백은 Render의 이전 배포로 되돌린다.** 데이터베이스 스키마를 바꾸는 변경은 롤백이 어려우므로 별도로 다룬다. 현재는 마이그레이션 도구가 없고 `create_all`에 의존하므로, 컬럼 변경이 필요해지면 Alembic 도입을 먼저 검토한다.

**키가 노출되면 즉시 회전한다.** OpenAI 대시보드에서 기존 키를 폐기하고 새 키를 발급한 뒤 Render 환경변수를 교체한다. Neon 비밀번호도 Console에서 재설정할 수 있다.

**배포 후 README에 공개 URL을 추가한다.** 합성 데이터 데모이며 수의학적 판단을 제공하지 않는다는 경계도 함께 명시한다.

## 10.1 2026-09-21 공개 배포 결과

- Production Frontend: `https://pet-detective-one.vercel.app`
- Backend API: `https://pet-detective-api.onrender.com`
- 배포 브랜치: `main`
- 공개 환경에서 시나리오 3종 조회, Luna 리포트, Evidence 4건, Tool 호출 과정과 Neon 저장을 확인했다.
- Render의 `ALLOWED_ORIGINS`에는 고정 Production 도메인을 등록한다. `pet-detective-<hash>-<team>.vercel.app` 형식의 배포별 URL은 다른 Origin이므로 CORS에서 차단되는 것이 정상이다.

## 11. 이후 선택지

**AWS 이전.** 이 단계에는 포함하지 않는다. 옮기더라도 바뀌는 것은 백엔드 한 조각뿐이다. `backend/Dockerfile`을 App Runner에 그대로 올리고, Vercel의 `VITE_API_BASE_URL`과 백엔드의 `ALLOWED_ORIGINS`를 새 주소로 교체하면 된다. 프론트엔드와 Neon은 그대로 둔다. App Runner는 무료 티어가 없으므로 월 $5~25가 발생하며, 시작 전에 AWS Budgets 알림을 먼저 설정한다.

**콜드 스타트 제거.** 데모를 자주 보여주게 되면 Render 유료 플랜(월 $7) 또는 Google Cloud Run(콜드 스타트 2~5초, 무료 한도 내 $0)을 검토한다.

**커스텀 도메인.** Vercel과 Render 모두 무료 플랜에서 커스텀 도메인과 HTTPS를 지원한다. 도메인 구입 비용만 든다.
