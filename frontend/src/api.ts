import type { Report, Scenario, ScenarioDetail } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "요청을 처리하지 못했습니다.");
  }
  return response.json() as Promise<T>;
}

export const api = {
  scenarios: () => request<Scenario[]>("/api/scenarios"),
  scenario: (id: string) => request<ScenarioDetail>(`/api/scenarios/${id}`),
  investigate: (scenarioId: string, question: string) =>
    request<Report>("/api/investigations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId, question, use_llm: true })
    })
};
