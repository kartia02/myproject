import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { clearWorkspace, loadWorkspace, saveWorkspace } from "./storage";
import type { DailyRecord, ExperienceMode, PersonalWorkspace, PetProfile, Report, Scenario, ScenarioDetail } from "./types";

const REQUIRED_RECORDS = 37;
const metrics: { key: keyof DailyRecord; label: string; unit: string }[] = [
  { key: "night_awakenings", label: "야간 각성", unit: "회" },
  { key: "evening_walk_minutes", label: "저녁 산책", unit: "분" },
  { key: "scratching_count", label: "긁기", unit: "회" },
  { key: "activity_minutes", label: "활동 시간", unit: "분" }
];

const scenarioNames: Record<string, (name: string) => string> = {
  "night-restlessness": (name) => `밤잠이 불안정해진 ${name}`,
  "rainy-slowdown": (name) => `장마철 활동이 줄어든 ${name}`,
  "stable-routine": (name) => `평소 리듬을 유지한 ${name}`
};

function MiniChart({ records, metric }: { records: DailyRecord[]; metric: keyof DailyRecord }) {
  const values = records.map((row) => Number(row[metric]));
  if (!values.length) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const denominator = Math.max(values.length - 1, 1);
  const points = values.map((value, index) => `${(index / denominator) * 100},${46 - ((value - min) / range) * 40}`).join(" ");
  const baselineWidth = Math.min((30 / values.length) * 100, 100);
  const recentStart = Math.max(((values.length - 7) / values.length) * 100, 0);
  return (
    <svg className="mini-chart" viewBox="0 0 100 50" preserveAspectRatio="none" aria-label={`${values.length}일 추이 차트`}>
      <rect x="0" y="0" width={baselineWidth} height="50" className="baseline-zone" />
      <rect x={recentStart} y="0" width={100 - recentStart} height="50" className="recent-zone" />
      <polyline points={points} fill="none" className="trend-line" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export default function App() {
  const [workspace, setWorkspace] = useState<PersonalWorkspace | null>(() => loadWorkspace());

  useEffect(() => { if (workspace) saveWorkspace(workspace); }, [workspace]);

  function resetWorkspace() {
    if (!window.confirm("이 브라우저에 저장된 반려동물 정보와 기록을 모두 삭제할까요?")) return;
    clearWorkspace();
    setWorkspace(null);
  }

  function exportWorkspace() {
    if (!workspace) return;
    const blob = new Blob([JSON.stringify(workspace, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${workspace.profile.name}-pet-detective-records.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (!workspace) return <Onboarding onComplete={setWorkspace} />;
  return (
    <div className="app-shell">
      <Header profile={workspace.profile} onExport={exportWorkspace} onReset={resetWorkspace} />
      {workspace.profile.mode === "sample"
        ? <SampleExperience profile={workspace.profile} />
        : <PersonalExperience workspace={workspace} onChange={setWorkspace} />}
      <footer>Pet Detective v1.1 · Personal Baseline Demo</footer>
    </div>
  );
}

function Header({ profile, onExport, onReset }: { profile: PetProfile; onExport: () => void; onReset: () => void }) {
  return (
    <header className="topbar">
      <a className="brand" href="#top"><span className="brand-mark">PD</span><span>Pet Detective</span></a>
      <div className="profile-actions">
        <span><strong>{profile.name}</strong> · {profile.mode === "sample" ? "샘플 체험" : "내 기록"}</span>
        {profile.mode === "personal" && <button className="text-button" onClick={onExport}>기록 내보내기</button>}
        <button className="text-button danger-text" onClick={onReset}>처음부터</button>
      </div>
    </header>
  );
}

function Onboarding({ onComplete }: { onComplete: (workspace: PersonalWorkspace) => void }) {
  const [name, setName] = useState("");
  const [breed, setBreed] = useState("");
  const [age, setAge] = useState("");
  const [mode, setMode] = useState<ExperienceMode>("sample");

  function submit(event: FormEvent) {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) return;
    onComplete({ profile: { name: trimmedName, breed: breed.trim() || undefined, age: age ? Number(age) : undefined, mode }, records: [], events: [] });
  }

  return (
    <div className="onboarding-shell">
      <section className="onboarding-copy">
        <a className="brand onboarding-brand" href="#top"><span className="brand-mark">PD</span><span>Pet Detective</span></a>
        <p className="eyebrow">PERSONAL BASELINE INVESTIGATION</p>
        <h1>함께 기록할<br />반려견을 알려주세요.</h1>
        <p>이름을 등록하고 합성 기록으로 바로 체험하거나, 실제 일별 기록을 이 브라우저에 쌓을 수 있습니다.</p>
      </section>
      <form className="onboarding-card" onSubmit={submit}>
        <div className="field-row">
          <label>반려견 이름 <span>필수</span><input value={name} onChange={(e) => setName(e.target.value)} maxLength={40} required placeholder="예: 초코" /></label>
          <label>나이 <span>선택</span><input value={age} onChange={(e) => setAge(e.target.value)} min="0" max="30" type="number" placeholder="예: 5" /></label>
        </div>
        <label>품종 <span>선택</span><input value={breed} onChange={(e) => setBreed(e.target.value)} maxLength={60} placeholder="예: 말티즈" /></label>
        <fieldset>
          <legend>어떻게 시작할까요?</legend>
          <button type="button" className={`mode-choice ${mode === "sample" ? "selected" : ""}`} onClick={() => setMode("sample")}>
            <strong>60일 샘플 기록으로 바로 체험</strong><small>등록한 이름에 합성 기록을 적용해 Agent 분석을 즉시 확인합니다.</small>
          </button>
          <button type="button" className={`mode-choice ${mode === "personal" ? "selected" : ""}`} onClick={() => setMode("personal")}>
            <strong>내 반려견 기록 시작</strong><small>일별 기록을 이 브라우저에 저장하고 37일부터 변화를 분석합니다.</small>
          </button>
        </fieldset>
        <button className="primary-button" type="submit">{name.trim() || "반려견"}와 시작하기 <span>→</span></button>
        <p className="privacy-note">계정 없이 사용합니다. 이름과 직접 입력한 기록은 서버 DB가 아닌 현재 브라우저에 저장됩니다. 분석 요청 중에는 이름과 계산에 필요한 기록이 서버에 일시적으로 전달됩니다.</p>
      </form>
    </div>
  );
}

function Hero({ name, personal = false }: { name: string; personal?: boolean }) {
  return <section className="hero"><p className="eyebrow">{personal ? "MY PET RECORD" : "SYNTHETIC PERSONAL BASELINE"}</p><h1>{name}의 평소와<br />달라진 순간을 찾습니다.</h1><p className="hero-copy">과거 기록을 기준으로 최근 변화를 찾고, 같은 시기에 나타난 근거를 조사합니다.</p></section>;
}

function SampleExperience({ profile }: { profile: PetProfile }) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<ScenarioDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [question, setQuestion] = useState(`최근 ${profile.name}에게 달라진 점이 있어?`);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    void api.health().catch(() => undefined);
    const timer = window.setTimeout(() => setWaking(true), 3000);
    api.scenarios().then((items) => { setScenarios(items); if (items[0]) setSelectedId(items[0].id); })
      .catch((err: Error) => setError(err.message)).finally(() => { window.clearTimeout(timer); setWaking(false); });
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    setReport(null); setDetail(null); setError("");
    api.scenario(selectedId, controller.signal)
      .then((item) => setDetail({ ...item, scenario: { ...item.scenario, dog_name: profile.name } }))
      .catch((err: Error) => { if (err.name !== "AbortError") setError(err.message); });
    return () => controller.abort();
  }, [selectedId, profile.name]);

  const recentMetrics = useRecentMetrics(detail?.records ?? []);
  async function ask() {
    if (!selectedId || !question.trim()) return;
    setLoading(true); setError("");
    try { setReport(await api.investigate(selectedId, question.trim(), profile.name)); }
    catch (err) { setError(err instanceof Error ? err.message : "조사에 실패했습니다."); }
    finally { setLoading(false); }
  }

  return (
    <main id="top">
      <Hero name={profile.name} />
      <div className="sample-disclosure"><strong>합성 기록 체험</strong> 입력한 이름에 사전 생성된 60일 기록을 적용합니다. 실제 {profile.name}의 행동을 분석한 결과가 아닙니다.</div>
      {waking && <div className="notice" role="status">서버를 깨우는 중입니다. 첫 응답에 최대 1분이 걸릴 수 있습니다.</div>}
      <section className="workspace">
        <aside className="scenario-panel">
          <div className="section-heading"><span>01</span><h2>체험할 기록</h2></div>
          <div className="scenario-list">{scenarios.map((scenario) => <button key={scenario.id} className={`scenario-card ${selectedId === scenario.id ? "selected" : ""}`} onClick={() => setSelectedId(scenario.id)}><span className="dog-avatar">{profile.name.slice(0, 1)}</span><span><strong>{scenarioNames[scenario.id]?.(profile.name) ?? scenario.name}</strong><small>{scenario.description}</small></span></button>)}</div>
          {detail && <DataNote detail={detail} />}
        </aside>
        <div className="main-panel">
          <MetricsCard name={profile.name} records={detail?.records ?? []} recentMetrics={recentMetrics} />
          <QuestionCard question={question} setQuestion={setQuestion} ask={ask} loading={loading} disabled={!detail} />
          {error && <div className="error" role="alert">{error}</div>}
          {report && <ReportView report={report} />}
        </div>
      </section>
    </main>
  );
}

type RecordDraft = Omit<DailyRecord, "date"> & { date: string; note: string };
function localDateString(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function missingRecordDates(records: DailyRecord[], today = localDateString()): string[] {
  if (!records.length) return [];
  const savedDates = new Set(records.map((record) => record.date));
  const firstDate = [...savedDates].sort()[0];
  if (firstDate > today) return [];
  const missing: string[] = [];
  const cursor = new Date(`${firstDate}T00:00:00`);
  const end = new Date(`${today}T00:00:00`);
  while (cursor <= end) {
    const offset = cursor.getTimezoneOffset() * 60_000;
    const date = new Date(cursor.getTime() - offset).toISOString().slice(0, 10);
    if (!savedDates.has(date)) missing.push(date);
    cursor.setDate(cursor.getDate() + 1);
  }
  return missing;
}

function displayDate(date: string): string {
  return new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric", weekday: "short" })
    .format(new Date(`${date}T00:00:00`));
}

function emptyDraft(): RecordDraft {
  return { date: localDateString(), activity_minutes: 0, sleep_hours: 0, night_awakenings: 0, meal_grams: 0, evening_walk_minutes: 0, scratching_count: 0, barking_count: 0, temperature_c: 20, precipitation_mm: 0, note: "" };
}

function PersonalExperience({ workspace, onChange }: { workspace: PersonalWorkspace; onChange: (value: PersonalWorkspace) => void }) {
  const [draft, setDraft] = useState<RecordDraft>(() => emptyDraft());
  const [question, setQuestion] = useState(`최근 ${workspace.profile.name}에게 달라진 점이 있어?`);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const records = useMemo(() => [...workspace.records].sort((a, b) => a.date.localeCompare(b.date)), [workspace.records]);
  const missingDates = useMemo(() => missingRecordDates(records), [records]);
  const recentMetrics = useRecentMetrics(records);
  const ready = records.length >= REQUIRED_RECORDS;

  function setNumber(key: keyof DailyRecord, value: string) { setDraft((current) => ({ ...current, [key]: Number(value) })); }
  function saveRecord(event: FormEvent) {
    event.preventDefault();
    const { note, ...record } = draft;
    const nextRecords = [...workspace.records.filter((item) => item.date !== record.date), record].sort((a, b) => a.date.localeCompare(b.date));
    const nextEvents = workspace.events.filter((item) => item.date !== record.date);
    if (note.trim()) nextEvents.push({ date: record.date, kind: "note", note: note.trim() });
    onChange({ ...workspace, records: nextRecords, events: nextEvents.sort((a, b) => a.date.localeCompare(b.date)) });
    setDraft(emptyDraft()); setReport(null);
  }
  function editRecord(record: DailyRecord) {
    const note = workspace.events.find((item) => item.date === record.date)?.note ?? "";
    setDraft({ ...record, note }); window.scrollTo({ top: 300, behavior: "smooth" });
  }
  function deleteRecord(date: string) {
    onChange({ ...workspace, records: workspace.records.filter((item) => item.date !== date), events: workspace.events.filter((item) => item.date !== date) });
    setReport(null);
  }
  function startMissingRecord(date: string) {
    setDraft({ ...emptyDraft(), date });
    document.getElementById("record-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  async function ask() {
    if (!ready || !question.trim()) return;
    setLoading(true); setError("");
    try { setReport(await api.investigatePersonal(workspace.profile.name, records, workspace.events, question.trim())); }
    catch (err) { setError(err instanceof Error ? err.message : "조사에 실패했습니다."); }
    finally { setLoading(false); }
  }

  return (
    <main id="top">
      <Hero name={workspace.profile.name} personal />
      <div className="privacy-banner"><strong>브라우저 저장</strong> 이름과 원본 기록은 이 기기에만 저장됩니다. 분석할 때 일시적으로 서버에 전달되며 Neon에는 실행 모드와 사용량만 남습니다.</div>
      <section className="personal-layout">
        <RecordForm draft={draft} setDraft={setDraft} setNumber={setNumber} onSubmit={saveRecord} />
        <div className="personal-main">
          <ProgressCard count={records.length} missingCount={missingDates.length} />
          {missingDates.length > 0 && <MissingRecordsCard dates={missingDates} onSelect={startMissingRecord} />}
          {records.length > 0 && <MetricsCard name={workspace.profile.name} records={records} recentMetrics={recentMetrics} />}
          <RecordList records={records} onEdit={editRecord} onDelete={deleteRecord} />
          {ready && <QuestionCard question={question} setQuestion={setQuestion} ask={ask} loading={loading} disabled={false} />}
          {error && <div className="error" role="alert">{error}</div>}
          {report && <ReportView report={report} />}
        </div>
      </section>
    </main>
  );
}

function RecordForm({ draft, setDraft, setNumber, onSubmit }: { draft: RecordDraft; setDraft: (value: RecordDraft | ((current: RecordDraft) => RecordDraft)) => void; setNumber: (key: keyof DailyRecord, value: string) => void; onSubmit: (event: FormEvent) => void }) {
  const numberFields: { key: keyof DailyRecord; label: string; unit: string; min?: number; max: number; step?: string }[] = [
    { key: "activity_minutes", label: "활동 시간", unit: "분", max: 1440 }, { key: "sleep_hours", label: "수면 시간", unit: "시간", max: 24, step: "0.1" },
    { key: "night_awakenings", label: "야간 각성", unit: "회", max: 100 }, { key: "meal_grams", label: "식사량", unit: "g", max: 5000 },
    { key: "evening_walk_minutes", label: "저녁 산책", unit: "분", max: 1440 }, { key: "scratching_count", label: "긁기", unit: "회", max: 1000 },
    { key: "barking_count", label: "짖음", unit: "회", max: 1000 }, { key: "temperature_c", label: "평균 기온", unit: "°C", min: -60, max: 60, step: "0.1" },
    { key: "precipitation_mm", label: "강수량", unit: "mm", max: 2000, step: "0.1" }
  ];
  return (
    <form className="record-form" id="record-form" onSubmit={onSubmit}>
      <div className="section-heading"><span>01</span><h2>{draft.date < localDateString() ? "지난 기록 작성" : "오늘의 기록"}</h2></div>
      <label>날짜<input type="date" max={localDateString()} value={draft.date} onChange={(e) => setDraft((current) => ({ ...current, date: e.target.value }))} required /></label>
      <div className="record-fields">{numberFields.map((field) => <label key={field.key}>{field.label}<span>{field.unit}</span><input type="number" min={field.min ?? 0} max={field.max} step={field.step ?? "1"} value={Number(draft[field.key])} onChange={(e) => setNumber(field.key, e.target.value)} required /></label>)}</div>
      <label>특이사항 <span>선택</span><textarea value={draft.note} onChange={(e) => setDraft((current) => ({ ...current, note: e.target.value }))} maxLength={300} placeholder="예: 비가 와서 산책을 짧게 함" /></label>
      {draft.date < localDateString() && <p className="past-record-note">놓친 {displayDate(draft.date)} 기록을 작성하고 있습니다.</p>}
      <button className="primary-button" type="submit">이 날짜 기록 저장</button><p className="helper">같은 날짜를 다시 저장하면 기존 기록을 수정합니다.</p>
    </form>
  );
}

function ProgressCard({ count, missingCount }: { count: number; missingCount: number }) {
  const progress = Math.min((count / REQUIRED_RECORDS) * 100, 100);
  return <section className="progress-card"><div><p className="eyebrow">PERSONAL BASELINE</p><h2>{count >= REQUIRED_RECORDS ? "변화 분석 준비가 완료됐습니다." : "평소 기준을 만들고 있습니다."}</h2></div><strong>{count}<small> / {REQUIRED_RECORDS}일</small></strong><div className="progress-track"><span style={{ width: `${progress}%` }} /></div><p>과거 30일과 최근 7일을 비교하므로 날짜가 서로 다른 기록 37개가 필요합니다.{missingCount > 0 && ` 비어 있는 날짜 ${missingCount}개를 아래에서 확인할 수 있습니다.`}</p></section>;
}

function MissingRecordsCard({ dates, onSelect }: { dates: string[]; onSelect: (date: string) => void }) {
  const recentMissing = [...dates].reverse().slice(0, 8);
  return (
    <section className="missing-records-card" aria-live="polite">
      <div><p className="eyebrow">MISSING RECORDS</p><h2>작성하지 않은 날짜가 {dates.length}개 있습니다.</h2><p>기억나는 범위에서 보완해 주세요. 누락 기록이 있어도 37개가 모이면 분석은 가능합니다.</p></div>
      <div className="missing-date-list">
        {recentMissing.map((date) => <button key={date} onClick={() => onSelect(date)}>{date === localDateString() ? "오늘" : displayDate(date)} <span>작성하기 →</span></button>)}
      </div>
      {dates.length > recentMissing.length && <small>가장 최근 날짜부터 8개를 표시합니다. 그 외 {dates.length - recentMissing.length}개가 더 있습니다.</small>}
    </section>
  );
}

function RecordList({ records, onEdit, onDelete }: { records: DailyRecord[]; onEdit: (record: DailyRecord) => void; onDelete: (date: string) => void }) {
  const ordered = [...records].sort((a, b) => b.date.localeCompare(a.date));
  return <section className="record-list-card"><div className="section-heading"><span>02</span><h2>저장된 기록</h2></div>{!ordered.length ? <p className="empty-state">아직 저장된 기록이 없습니다. 첫 기록을 남겨보세요.</p> : <div className="record-table-wrap"><table><thead><tr><th>날짜</th><th>활동</th><th>수면</th><th>산책</th><th /></tr></thead><tbody>{ordered.map((record) => <tr key={record.date}><td>{record.date}</td><td>{record.activity_minutes}분</td><td>{record.sleep_hours}시간</td><td>{record.evening_walk_minutes}분</td><td><button onClick={() => onEdit(record)}>수정</button><button className="danger-text" onClick={() => onDelete(record.date)}>삭제</button></td></tr>)}</tbody></table></div>}</section>;
}

function useRecentMetrics(records: DailyRecord[]) {
  return useMemo(() => {
    if (!records.length) return [];
    return metrics.map((metric) => { const last = records.slice(-7).map((row) => Number(row[metric.key])); return { ...metric, value: (last.reduce((sum, value) => sum + value, 0) / last.length).toFixed(1) }; });
  }, [records]);
}

function DataNote({ detail }: { detail: ScenarioDetail }) { return <div className="data-note"><strong>{detail.scenario.days}일 기록</strong><span>{detail.scenario.start_date} — {detail.scenario.end_date}</span><p>앞 30일은 Baseline, 마지막 7일은 최근 구간으로 비교합니다.</p></div>; }

function MetricsCard({ name, records, recentMetrics }: { name: string; records: DailyRecord[]; recentMetrics: ReturnType<typeof useRecentMetrics> }) {
  return <section className="dashboard-card"><div className="section-heading"><span>03</span><h2>{name}의 최근 {Math.min(records.length, 7)}일</h2></div><div className="metrics-grid">{recentMetrics.map((metric) => <article className="metric-card" key={metric.key}><div><span>{metric.label}</span><strong>{metric.value}<small>{metric.unit}</small></strong></div><MiniChart records={records} metric={metric.key} /></article>)}</div><div className="legend"><span className="baseline-key" /> Baseline 30일 <span className="recent-key" /> 최근 7일</div></section>;
}

function QuestionCard({ question, setQuestion, ask, loading, disabled }: { question: string; setQuestion: (value: string) => void; ask: () => void; loading: boolean; disabled: boolean }) {
  return <section className="question-card"><div className="section-heading"><span>04</span><h2>Detective에게 질문하기</h2></div><div className="question-box"><textarea value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={300} /><button onClick={ask} disabled={loading || disabled}>{loading ? "기록 조사 중…" : "변화 조사하기"}<span>→</span></button></div><p className="helper">행동 변화와 함께 나타난 기록을 설명합니다. 질병을 진단하거나 원인을 단정하지 않습니다.</p></section>;
}

function ReportView({ report }: { report: Report }) {
  return <section className="report-card"><div className="report-title"><div><p className="eyebrow">INVESTIGATION COMPLETE</p><h2>{report.headline}</h2></div><span className="mode-badge">{report.mode === "agent" ? "GPT-5.6 Luna" : "Safe fallback"}</span></div><p className="report-summary">{report.summary}</p>{report.changes.length > 0 && <div className="change-list">{report.changes.map((change) => <div className="change-row" key={change.metric}><span>{change.label}</span><strong className={change.direction}>{change.percent_change !== null && change.percent_change > 0 ? "+" : ""}{change.percent_change}%</strong><small>{change.baseline_mean}{change.unit} → {change.comparison_mean}{change.unit}</small></div>)}</div>}<div className="report-columns"><div><h3>Evidence</h3>{report.evidence.length ? report.evidence.map((item) => <article className="evidence" key={item.id}><span>{item.id}</span><p>{item.statement}</p></article>) : <p className="muted">기준을 넘는 변화 근거가 없습니다.</p>}</div><div><h3>조사 과정</h3><ol className="trace">{report.tool_trace.map((item) => <li key={item.step}><span>{item.tool}</span>{item.summary}</li>)}</ol></div></div><div className="limitation">{report.limitations[0]}</div></section>;
}
