export type Scenario = {
  id: string;
  name: string;
  dog_name: string;
  description: string;
  start_date: string;
  end_date: string;
  days: number;
};

export type DailyRecord = {
  date: string;
  activity_minutes: number;
  sleep_hours: number;
  night_awakenings: number;
  meal_grams: number;
  evening_walk_minutes: number;
  scratching_count: number;
  barking_count: number;
  temperature_c: number;
  precipitation_mm: number;
};

export type ScenarioDetail = {
  scenario: Scenario;
  records: DailyRecord[];
  events: { date: string; kind: string; note: string }[];
};

export type ChangeFinding = {
  metric: keyof DailyRecord;
  label: string;
  unit: string;
  direction: "increase" | "decrease";
  baseline_mean: number;
  comparison_mean: number;
  absolute_change: number;
  percent_change: number | null;
  start_date: string;
  severity: number;
};

export type Evidence = {
  id: string;
  kind: "change" | "comparison" | "event";
  statement: string;
  start_date: string;
  end_date: string;
  source_dates: string[];
};

export type Report = {
  scenario_id: string;
  status: string;
  mode: "agent" | "deterministic_fallback";
  headline: string;
  summary: string;
  changes: ChangeFinding[];
  evidence: Evidence[];
  tool_trace: { step: number; tool: string; summary: string }[];
  limitations: string[];
};
