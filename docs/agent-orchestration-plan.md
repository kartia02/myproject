# Agent 오케스트레이션 전환 계획

## 목적

현재 Pet Detective는 GPT-5.6 Luna를 실제 호출하고 네 개의 Tool을 실행하지만, 서버가 Luna 호출 전에 변화와 Evidence를 계산해 전달하고 모든 Tool 호출을 강제한다. 따라서 현재 구현은 안전하게 제한된 Tool 사용 LLM이며, 질문에 따라 조사 계획을 세우는 Agent 동작은 아직 제한적이다.

이번 전환의 목표는 Python 분석 결과를 진실의 원천으로 유지하면서 Luna가 사용자 질문을 해석하고 필요한 Tool, 호출 순서, 추가 조사 여부를 결정하도록 만드는 것이다.

```text
사용자 질문
    ↓
DB에서 조사 대상 Scenario Snapshot 고정
    ↓
Luna가 질문을 해석하고 필요한 Tool 선택
    ↓
Python·SQL Tool 실행
    ↓
서버가 Tool 결과를 Evidence Ledger에 누적
    ↓
Luna가 추가 조사 여부 결정
    ↓
Structured Output으로 최종 답변 작성
    ↓
서버가 Evidence·수치·날짜·금지 표현 검증
    ↓
통과 시 Agent 결과, 실패 시 Safe fallback
```

합성 데이터 사용 여부와 Agent 동작 여부는 분리한다. v1.0 공개 데모는 합성 데이터를 유지하며, 실제 사용자 데이터 입력과 계정 기능은 별도 범위로 둔다.

## 유지할 책임 경계

| 구성요소 | 책임 |
| --- | --- |
| Python 분석 엔진 | Baseline, 변화량, 방향, 지속 조건, 시작일 계산 |
| PostgreSQL | 시나리오 Snapshot, 일별 기록, 이벤트, 조사 결과 저장 |
| Luna Agent | 질문 이해, Tool 선택, 호출 순서, 추가 조사 판단, 설명 작성 |
| Tool Dispatcher | 인자 검증, Scenario 고정, Step 제한, 중복 호출 방지 |
| Evidence Ledger | Tool이 실제로 반환한 근거만 누적 |
| 검증 계층 | Evidence ID, 수치, 날짜, Tool 영역, 인과·진단 표현 검증 |
| React UI | 결과, Evidence, 사용한 Tool과 조사 목적 표시 |

Luna가 통계를 직접 계산하거나 Python 결과를 덮어쓰도록 만들지 않는다.

## Tool 계약 변경

현재 Tool은 인자가 없고 모두 호출해야 한다. 전환 후 질문에 필요한 지표와 기간만 조회할 수 있게 한다.

| Tool | 역할 | 허용 인자 |
| --- | --- | --- |
| `get_baseline` | 평소 수준 조회 | `metrics` |
| `detect_changes` | 변화, 방향, 시작일 탐지 | `metrics` |
| `compare_periods` | Baseline과 최근 기간 비교 | `metrics` |
| `get_events` | 변화 주변 이벤트 조회 | `start_date`, `end_date`, `kinds` |

모델은 Scenario ID를 전달하지 않는다. 서버가 조사 시작 시 Neon에서 읽은 동일한 Scenario Snapshot을 모든 Tool에 주입한다. 날짜는 해당 시나리오 범위 안에서만 허용하고, 지표는 서버의 Metric Catalog에 존재하는 값만 허용한다.

## 질문별 예상 동작

| 질문 예시 | 예상 Tool 흐름 |
| --- | --- |
| 평소 활동 시간은 어느 정도야? | `get_baseline` |
| 최근 달라진 점이 있어? | `detect_changes` |
| 밤에 깨는 게 언제부터 늘었어? | `detect_changes` |
| 산책 감소와 활동량을 비교해줘. | `detect_changes` → `compare_periods` |
| 비가 온 시기와 활동 감소가 겹쳐? | `detect_changes` → `compare_periods` → `get_events` |
| 관련 기록까지 모두 조사해줘. | 질문에 필요한 범위에서 최대 4개 Tool |

서버는 모든 Tool을 강제하지 않고 최종 주장에 필요한 Tool이 호출됐는지 검사한다.

- 변화 주장에는 `detect_changes` 결과가 필요하다.
- Baseline 수치에는 `get_baseline` 또는 동일 값을 제공한 분석 결과가 필요하다.
- 기간 비교 주장에는 `compare_periods` 결과가 필요하다.
- 이벤트 언급에는 `get_events` 결과가 필요하다.

## Evidence Ledger

Luna에게 사전 계산된 Evidence Catalog를 전달하지 않는다. 각 Tool 실행 후 서버가 결과를 Evidence Ledger에 등록한다.

```json
{
  "id": "E2",
  "source_tool": "detect_changes",
  "metric": "night_awakenings",
  "statement": "야간 각성이 2026-08-03부터 변화 기준을 충족했다.",
  "values": [1.8, 4.79, 165.4],
  "dates": ["2026-08-03", "2026-08-23", "2026-08-29"]
}
```

최종 답변은 Ledger에 존재하는 Evidence만 인용할 수 있다. Tool을 호출하지 않고 생성한 숫자, 날짜, 변화, 이벤트 주장은 거부한다.

## Agent 실행 정책

- 요청당 Tool 호출은 최대 4회다.
- 동일 Tool과 동일 인자의 반복 호출을 금지한다.
- 모델이 Scenario를 선택하거나 바꾸지 못하게 한다.
- 허용되지 않은 지표와 범위 밖 날짜를 거부한다.
- Tool 인자 오류는 한 번만 수정할 수 있게 한다.
- 변화가 없으면 불필요한 추가 조사를 중단한다.
- Step 한도 안에 답변을 완성하지 못하면 Safe fallback을 반환한다.
- OpenAI API 오류, Tool 오류, 출력 검증 실패에도 Safe fallback을 유지한다.

## Structured Output

자유 텍스트 대신 다음 구조로 최종 답변을 받는다.

```json
{
  "headline": "야간 각성이 평소보다 증가했습니다.",
  "findings": [
    {
      "text": "야간 각성은 2026-08-03부터 변화 기준을 충족했습니다.",
      "evidence_ids": ["E2"]
    }
  ],
  "limitations": [
    "현재 기록만으로 원인을 판단할 수 없습니다."
  ]
}
```

서버는 Pydantic Schema로 구조를 검사하고, 각 Finding 문장과 Evidence를 다시 대조한다.

## 검증 규칙

- 인용한 Evidence ID가 Ledger에 존재해야 한다.
- 문장의 숫자와 날짜가 인용 Evidence에 존재해야 한다.
- 증가·감소 주장에는 해당 지표의 변화 Evidence가 필요하다.
- 이벤트 언급에는 이벤트 Evidence가 필요하다.
- 호출하지 않은 Tool 영역의 주장을 허용하지 않는다.
- 원인, 질병, 진단을 확정하는 표현을 금지한다.
- 다른 Scenario의 데이터나 ID를 사용할 수 없다.
- 검증 실패 시 Agent 문장을 사용자에게 노출하지 않는다.

## 구현 순서

1. Tool별 Pydantic 인자 Schema와 서버 검증을 추가한다.
2. 요청 시작 시 Scenario Snapshot을 고정하는 조사 Context를 만든다.
3. Evidence Ledger와 Tool 결과→Evidence 변환기를 구현한다.
4. Luna 초기 입력에서 사전 계산 Evidence를 제거한다.
5. 모든 Tool 호출 강제 조건을 제거한다.
6. 최대 4 Step의 동적 Tool 반복 루프를 구현한다.
7. 동일 Tool·동일 인자 중복 호출을 차단한다.
8. 최종 응답을 Structured Output으로 변경한다.
9. 검증 계층을 Evidence Ledger 기준으로 변경한다.
10. fallback이 기존과 동일한 분석 결과를 반환하는지 회귀 테스트한다.
11. 질문별 Tool 선택 평가 세트를 추가한다.
12. React UI에 선택한 Tool과 짧은 조사 목적을 표시한다.
13. 실제 Luna 반복 평가 후 비용·지연·채택률을 기록한다.
14. README와 구현 명세, 라이브 평가 결과를 갱신한다.

## 파일별 예상 변경 범위

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/schemas.py` | Tool 인자, Ledger Evidence, Structured Output Schema |
| `backend/app/tools.py` | 인자 검증과 Tool별 Evidence 생성 |
| `backend/app/agent.py` | 동적 실행 루프, 중복 방지, Structured Output 처리 |
| `backend/app/analysis.py` | Tool이 사용할 분석 함수와 Evidence 변환 경계 정리 |
| `backend/tests/test_tools.py` | 허용·금지 인자와 Scenario 고정 테스트 |
| `backend/tests/test_agent_validation.py` | Ledger 기반 주장 검증 테스트 |
| `backend/tests/test_report.py` | fallback과 Agent 리포트 회귀 테스트 |
| `evaluation/agent_cases.json` | 질문별 필수·허용 Tool Ground Truth |
| `evaluation/evaluate_agent.py` | Tool 선택과 근거 정확도 평가 |
| `evaluation/evaluate_live.py` | 실제 Luna 선택률·비용·지연 평가 확장 |
| `frontend/src/App.tsx` | 조사 목적과 선택된 Tool 표시 |

## 평가 계획

합성 시나리오별로 Baseline, 변화, 시작일, 기간 비교, 이벤트, 변화 없음 질문을 구성해 20~30개 질문을 만든다.

| 지표 | 목표 |
| --- | ---: |
| 필수 Tool 선택 Recall | 95% 이상 |
| 불필요한 Tool 호출률 | 20% 이하 |
| Evidence Precision | 100% |
| Unsupported Claim Rate | 0% |
| Agent 응답 채택률 | 90% 이상 |
| 평균 Tool 호출 수 | 2~3회 |
| 예상 비용 | 요청당 $0.001 이하 |

결정론적 테스트에서는 Tool Dispatcher, Ledger, 검증기, fallback을 검사한다. 실제 Luna 평가는 질문 유형별로 여러 번 실행해 출력 변동성을 측정한다.

## 완료 조건

- Baseline 질문이 불필요한 변화·이벤트 Tool을 호출하지 않는다.
- 변화 질문이 `detect_changes` 결과를 근거로 답한다.
- 환경·이벤트 질문이 필요한 경우에만 비교와 이벤트 Tool을 추가 호출한다.
- 모든 최종 주장에 실제 Tool Evidence가 연결된다.
- Scenario 전환, 범위 밖 날짜, 허용되지 않은 지표 요청이 차단된다.
- 실패 상황에서 기존 Safe fallback이 정상 동작한다.
- 자동 테스트, 결정론적 평가, 실제 Luna 평가, 프런트엔드 빌드가 통과한다.
- Neon `investigation_runs`에 선택한 Tool, Evidence, 사용량과 최종 모드가 저장된다.

## 예상 작업량

- Backend Tool·Ledger·Agent 루프: 약 0.5~1일
- 평가 세트와 실제 Luna 반복 검증: 약 0.5일
- UI·문서·전체 회귀 검증: 약 0.5일

전체 예상은 1.5~2일이다. 구현 도중에도 기존 deterministic fallback과 현재 배포 가능한 흐름은 유지한다.
