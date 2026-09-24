import type { DailyRecord, Report, Scenario, ScenarioDetail } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch (error) {
    // 취소는 호출한 쪽에서 구분해야 하므로 그대로 전달한다.
    if ((error as { name?: string } | null)?.name === "AbortError") throw error;
    // 절전 중인 서버, 네트워크 단절, CORS 차단이 모두 여기로 온다. 브라우저 기본 문구가
    // 영어로 노출되지 않게 감싼다.
    throw new Error("서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "요청을 처리하지 못했습니다.");
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  scenarios: () => request<Scenario[]>("/api/scenarios"),
  scenario: (id: string, signal?: AbortSignal) =>
    request<ScenarioDetail>(`/api/scenarios/${id}`, { signal }),
  investigate: (scenarioId: string, question: string, petName?: string) =>
    request<Report>("/api/investigations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId, question, use_llm: true, pet_name: petName })
    }),
  investigatePersonal: (
    petName: string,
    records: DailyRecord[],
    events: { date: string; kind: string; note: string }[],
    question: string
  ) => request<Report>("/api/personal-investigations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pet_name: petName, records, events, question, use_llm: true })
  })
};
