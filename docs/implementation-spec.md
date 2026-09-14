# Pet Detective v1.0 구현 명세

이 문서는 `Pet Detective — 개인 반려견 행동 변화 분석 AI Agent 기획서.md`를 코드 수준으로 구체화한 v1.0 기준이다.

## 확정 범위

- 사전 생성 Synthetic Scenario 선택형 공개 데모
- 계정, 로그인, 데이터 업로드 없음
- React + TypeScript, FastAPI, PostgreSQL
- OpenAI Responses API와 `gpt-5.6-luna`를 기본 Agent 모델로 사용
- 월 API 비용 $5 이하를 목표로 요청당 최대 4회 Tool 호출, 최대 900 출력 토큰, 분당 10회 제한 적용
- API Key 또는 LLM 호출 실패 시 계산된 Evidence를 이용한 안전한 규칙 기반 리포트 제공
- P1 Timeline Search와 P2 Adaptive Baseline은 v1.0에서 제외

## 데이터 계약

기록은 반려견·날짜별 일일 집계다. 행동 지표는 활동 시간, 수면 시간, 야간 각성, 식사량, 저녁 산책, 긁기, 짖기이며 환경 지표는 평균 기온과 강수량이다. `0`은 관측값이고 결측값과 구분한다. v1.0 합성 데이터에는 결측값을 넣지 않는다.

각 시나리오는 60일이며 재현 가능한 고정 seed로 생성한다.

1. `night-restlessness`: 저녁 산책 감소, 3일 뒤 야간 각성 증가, 2일 뒤 긁기 증가
2. `rainy-slowdown`: 연속 강수와 같은 시기에 저녁 산책 및 활동 감소
3. `stable-routine`: 삽입 변화가 없는 음성 대조군

Ground Truth는 `evaluation/ground_truth.json`에만 보관하며 서비스와 Agent Tool에는 제공하지 않는다.

## 분석 규칙

- Baseline: 최초 30일의 평균, 표준편차, 중앙값
- 현재 비교 구간: 데이터상 마지막 날짜까지의 7일
- 변화 후보: Baseline 평균 대비 지표별 최소 변화율과 1.5 표준편차 이상의 차이
- 지속 조건: 최근 7일 중 4일 이상이 Baseline 평균에서 같은 방향으로 1 표준편차를 벗어남
- 시작일: Baseline 이후 4일 창에서 3일 이상 같은 방향으로 벗어난 최초 날짜
- 결과: severity 순서로 최대 3개
- 데이터 부족과 변화 없음은 별도 상태로 구분

## Agent와 Evidence

숫자는 Python 분석 모듈에서 계산한다. Agent는 다음 Tool만 호출한다.

- `get_baseline()`
- `detect_changes()`
- `compare_periods()`
- `get_events()`

Evidence에는 고유 ID, 지표, 기준 기간, 비교 기간, 기준값, 관측값, 단위, 원본 날짜가 포함된다. 자연어 응답은 `[E1]` 형식으로 Evidence ID를 연결해야 한다. 존재하지 않는 ID가 포함되면 LLM 응답을 사용하지 않고 안전한 리포트로 대체한다.

서비스는 동시에 나타난 변화와 날짜 기반 이벤트를 설명할 수 있지만 원인 또는 질병으로 표현하지 않는다.

## 평가 규칙

변화 탐지는 지표와 방향이 모두 같은 경우 한 건의 정탐으로 계산한다. Precision, Recall, F1 및 시작일 평균 절대 오차를 보고한다. Evidence Precision은 응답이 인용한 Evidence ID 중 실제 생성된 ID의 비율이고 Unsupported Claim Rate는 그 보수적 보수값이다. LLM 자연어의 의미 단위 평가는 후속 평가 세트에서 별도 표본 검토한다.
