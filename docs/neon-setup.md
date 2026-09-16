# Neon PostgreSQL 연결

Pet Detective의 운영 데이터베이스는 Neon PostgreSQL을 사용한다. 로컬 화면 검증은 SQLite로 진행할 수 있으며, 배포 전에는 아래 순서로 Neon 연결을 확인한다.

1. Neon에서 프로젝트와 데이터베이스를 만든다. Backend 배포 지역과 가까운 리전을 선택한다.
2. Neon Console의 **Connect** 화면에서 pooled connection string을 복사한다. 호스트 이름에 `-pooler`가 포함되고 쿼리에 `sslmode=require&channel_binding=require`가 있는 주소를 사용한다.
3. 루트 `.env` 또는 배포 서비스의 Secret에 `DATABASE_URL`로 저장한다. `.env`는 Git에 포함되지 않는다.
4. 로컬에서 `cd backend` 후 `python check_database.py`를 실행한다.
5. Backend를 시작한다. 시작 시 테이블을 만들고 현재 코드의 Synthetic Scenario 3종과 DB 레코드를 동기화한다.
6. `GET /api/scenarios`가 3건을 반환하는지 확인하고 조사를 1회 실행한 뒤 Neon의 `investigation_runs` 테이블에 결과가 저장됐는지 확인한다.

## 로컬에서 Neon으로 실행

루트 `.env`의 `DATABASE_URL`을 Neon pooled connection string으로 설정한 뒤 두 터미널을 사용한다.

Backend:

```powershell
cd D:\MyProject\backend
python -m pip install -r requirements-dev.txt
python check_database.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd D:\MyProject\frontend
npm install
npm run dev -- --host 127.0.0.1
```

브라우저에서 `http://127.0.0.1:5173`을 열어 조사를 실행한다. 성공하면 응답의 `mode`가 `agent`이고 Tool 호출 과정과 Evidence가 표시된다. 조사 결과는 Neon의 `investigation_runs`에 저장된다.

## 연결 확인 기준

현재 검증된 초기 데이터 건수는 다음과 같다.

| 테이블 | 초기 건수 |
| --- | ---: |
| `scenarios` | 3 |
| `daily_records` | 180 |
| `pet_events` | 2 |
| `investigation_runs` | 사용자가 실행한 조사 수 |

`check_database.py`가 드라이버 오류를 출력하면 `python -m pip install -r requirements.txt`를 먼저 실행한다. 인증 오류라면 Neon Console에서 연결 문자열을 다시 복사하고 `.env`의 `DATABASE_URL` 한 줄을 교체한다. 연결 문자열이나 비밀번호는 Git, 문서, 채팅에 기록하지 않는다.

Neon이 제공하는 `postgresql://` 주소는 애플리케이션 설정에서 SQLAlchemy psycopg3 형식인 `postgresql+psycopg://`로 자동 변환된다. 런타임 연결에는 pooled 주소를 사용한다. 이후 Alembic 같은 별도 마이그레이션 도구를 도입하면 스키마 마이그레이션에는 direct 주소를 별도 Secret으로 둔다.
