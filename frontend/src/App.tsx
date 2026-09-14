import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { DailyRecord, Report, Scenario, ScenarioDetail } from "./types";

const metrics: { key: keyof DailyRecord; label: string; unit: string }[] = [
  { key: "night_awakenings", label: "야간 각성", unit: "회" },
  { key: "evening_walk_minutes", label: "저녁 산책", unit: "분" },
  { key: "scratching_count", label: "긁기", unit: "회" },
  { key: "activity_minutes", label: "활동 시간", unit: "분" }
];

function MiniChart({ records, metric }: { records: DailyRecord[]; metric: keyof DailyRecord }) {
  const values = records.map((row) => Number(row[metric]));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((value, index) => `${(index / (values.length - 1)) * 100},${46 - ((value - min) / range) * 40}`).join(" ");
  return (
    <svg className="mini-chart" viewBox="0 0 100 50" preserveAspectRatio="none" aria-label="60일 추이 차트">
      <rect x="0" y="0" width="50" height="50" className="baseline-zone" />
      <rect x="88" y="0" width="12" height="50" className="recent-zone" />
      <polyline points={points} fill="none" className="trend-line" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<ScenarioDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [question, setQuestion] = useState("최근 우리 강아지에게 달라진 점이 있어?");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.scenarios().then((items) => {
      setScenarios(items);
      if (items[0]) setSelectedId(items[0].id);
    }).catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setReport(null);
    api.scenario(selectedId).then(setDetail).catch((err: Error) => setError(err.message));
  }, [selectedId]);

  const recentMetrics = useMemo(() => {
    if (!detail) return [];
    return metrics.map((metric) => {
      const last = detail.records.slice(-7).map((row) => Number(row[metric.key]));
      return { ...metric, value: (last.reduce((sum, value) => sum + value, 0) / last.length).toFixed(1) };
    });
  }, [detail]);

  async function ask() {
    if (!selectedId || !question.trim()) return;
    setLoading(true);
    setError("");
    try { setReport(await api.investigate(selectedId, question.trim())); }
    catch (err) { setError(err instanceof Error ? err.message : "조사에 실패했습니다."); }
    finally { setLoading(false); }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark">PD</span><span>Pet Detective</span></a>
        <div className="status"><span className="status-dot" /> Synthetic data demo</div>
      </header>

      <main id="top">
        <section className="hero">
          <p className="eyebrow">PERSONAL BASELINE INVESTIGATION</p>
          <h1>평소와 달라진 순간을<br />기록에서 찾아냅니다.</h1>
          <p className="hero-copy">한 반려견의 지난 기록을 기준으로 최근 변화를 찾고, 같은 시기에 나타난 근거를 조사합니다.</p>
        </section>

        <section className="workspace">
          <aside className="scenario-panel">
            <div className="section-heading"><span>01</span><h2>조사할 기록</h2></div>
            <div className="scenario-list">
              {scenarios.map((scenario) => (
                <button key={scenario.id} className={`scenario-card ${selectedId === scenario.id ? "selected" : ""}`} onClick={() => setSelectedId(scenario.id)}>
                  <span className="dog-avatar">{scenario.dog_name.slice(0, 1)}</span>
                  <span><strong>{scenario.name}</strong><small>{scenario.description}</small></span>
                </button>
              ))}
            </div>
            {detail && <div className="data-note"><strong>{detail.scenario.days}일 기록</strong><span>{detail.scenario.start_date} — {detail.scenario.end_date}</span><p>앞 30일은 Baseline, 마지막 7일은 최근 구간으로 비교합니다.</p></div>}
          </aside>

          <div className="main-panel">
            <section className="dashboard-card">
              <div className="section-heading"><span>02</span><h2>{detail?.scenario.dog_name ?? "반려견"}의 최근 7일</h2></div>
              <div className="metrics-grid">
                {recentMetrics.map((metric) => (
                  <article className="metric-card" key={metric.key}>
                    <div><span>{metric.label}</span><strong>{metric.value}<small>{metric.unit}</small></strong></div>
                    {detail && <MiniChart records={detail.records} metric={metric.key} />}
                  </article>
                ))}
              </div>
              <div className="legend"><span className="baseline-key" /> Baseline 30일 <span className="recent-key" /> 최근 7일</div>
            </section>

            <section className="question-card">
              <div className="section-heading"><span>03</span><h2>Detective에게 질문하기</h2></div>
              <div className="question-box">
                <textarea value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={300} />
                <button onClick={ask} disabled={loading || !detail}>{loading ? "기록 조사 중…" : "변화 조사하기"}<span>→</span></button>
              </div>
              <p className="helper">행동 변화와 함께 나타난 기록을 설명합니다. 질병을 진단하거나 원인을 단정하지 않습니다.</p>
            </section>

            {error && <div className="error" role="alert">{error}</div>}
            {report && <ReportView report={report} />}
          </div>
        </section>
      </main>
      <footer>Pet Detective v1.0 · Synthetic Scenario Demo</footer>
    </div>
  );
}

function ReportView({ report }: { report: Report }) {
  return (
    <section className="report-card">
      <div className="report-title"><div><p className="eyebrow">INVESTIGATION COMPLETE</p><h2>{report.headline}</h2></div><span className="mode-badge">{report.mode === "agent" ? "GPT-5.6 Luna" : "Safe fallback"}</span></div>
      <p className="report-summary">{report.summary}</p>
      {report.changes.length > 0 && <div className="change-list">{report.changes.map((change) => <div className="change-row" key={change.metric}><span>{change.label}</span><strong className={change.direction}>{change.percent_change !== null && change.percent_change > 0 ? "+" : ""}{change.percent_change}%</strong><small>{change.baseline_mean}{change.unit} → {change.comparison_mean}{change.unit}</small></div>)}</div>}
      <div className="report-columns">
        <div><h3>Evidence</h3>{report.evidence.length ? report.evidence.map((item) => <article className="evidence" key={item.id}><span>{item.id}</span><p>{item.statement}</p></article>) : <p className="muted">기준을 넘는 변화 근거가 없습니다.</p>}</div>
        <div><h3>조사 과정</h3><ol className="trace">{report.tool_trace.map((item) => <li key={item.step}><span>{item.tool}</span>{item.summary}</li>)}</ol></div>
      </div>
      <div className="limitation">{report.limitations[0]}</div>
    </section>
  );
}
