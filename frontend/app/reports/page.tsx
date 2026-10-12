"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBox, Meter, PageHeader, Panel, PriorityChip, SkeletonRows } from "@/components/ui";
import { api, type Report } from "@/lib/api";

export default function ReportsPage() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setReport(await api.report());
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const h = report?.headline;
  const dq = h?.data_quality;
  const hasData = (h?.total_feedback ?? 0) > 0;

  return (
    <>
      <PageHeader
        title="Insight report"
        subtitle="A shareable summary of the current analysis: quality uplift, prioritised actions with their rationale, and tracked issues."
        right={
          <>
            <a className="btn" href={api.exportUrl("json")} target="_blank" rel="noreferrer">Export JSON</a>
            <a className="btn btn-primary" href={api.exportUrl("md")} target="_blank" rel="noreferrer">Export Markdown</a>
          </>
        }
      />

      {error && <ErrorBox error={error} />}
      {!report && !error && <SkeletonRows rows={5} />}

      {report && h && !hasData && (
        <Panel>
          <EmptyState
            title="No analyzed feedback yet"
            body="Import feedback and run the refinery to generate a report."
          />
        </Panel>
      )}

      {report && h && hasData && (
        <div className="space-y-4">
          {/* summary strip */}
          <Panel>
            <dl className="flex flex-wrap gap-x-12 gap-y-4">
              <div>
                <dt className="label">Feedback analyzed</dt>
                <dd className="num mt-1.5 text-[21px] font-semibold leading-none tracking-[-0.02em]">
                  {h.total_feedback.toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="label">Negative share</dt>
                <dd className="num mt-1.5 text-[21px] font-semibold leading-none tracking-[-0.02em] text-[var(--danger)]">
                  {Math.round(h.negative_share * 100)}%
                </dd>
              </div>
              <div>
                <dt className="label">Top priority</dt>
                <dd className="mt-1.5 max-w-[280px] text-[13px] font-medium leading-snug">{h.top_priority ?? "—"}</dd>
              </div>
              {dq && dq.grade_after !== null && (
                <div>
                  <dt className="label">Data quality · {dq.mode === "live" ? "Adaption live" : "demo artifact"}</dt>
                  <dd className="num mt-1.5 text-[15px]">
                    <span className="text-[var(--text-3)] line-through">{dq.grade_before}</span>
                    <span className="mx-1.5 text-[var(--text-3)]">→</span>
                    <span className="font-semibold text-[var(--ok)]">{dq.grade_after}</span>
                    <span className="ml-2 text-[12px] font-medium text-[var(--ok)]">+{dq.improvement_percent}%</span>
                  </dd>
                </div>
              )}
            </dl>
            <p className="mt-4 border-t border-[var(--border)] pt-3 text-[11px] text-[var(--text-3)]">
              Generated {report.generated_at.slice(0, 19).replace("T", " ")} UTC
            </p>
          </Panel>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
            <Panel title="Priority actions" flush>
              <ol>
                {report.recommendations.map((r, i) => (
                  <li key={r.topic} className="flex gap-3 border-b border-[var(--border)] px-4 py-3 last:border-b-0">
                    <span className="num w-4 shrink-0 text-right text-[12.5px] font-semibold text-[var(--text-3)]">{i + 1}</span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[12.5px] font-medium">{r.title}</span>
                        <PriorityChip label={r.priority_label} score={r.priority} />
                      </div>
                      <p className="mt-1 text-[11.5px] leading-relaxed text-[var(--text-2)]">{r.action}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </Panel>

            <Panel title="Category distribution" flush>
              <table className="data">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th className="num">Items</th>
                    <th className="num">Negative</th>
                    <th className="num">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {report.topic_distribution.map((t) => (
                    <tr key={t.topic}>
                      <td className="font-medium">{t.topic}</td>
                      <td className="num">{t.total}</td>
                      <td className="num text-[var(--danger)]">{t.negative}</td>
                      <td className="num text-[var(--text-3)]">
                        {Math.round((t.negative / Math.max(1, t.total)) * 100)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
          </div>

          {report.tracked_issues.length > 0 && (
            <Panel title={`Tracked issues (${report.tracked_issues.length})`} flush>
              <table className="data">
                <thead>
                  <tr>
                    <th>Issue</th>
                    <th>Priority</th>
                    <th>Category</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {report.tracked_issues.map((i) => (
                    <tr key={i.id}>
                      <td className="font-medium">{i.title}</td>
                      <td><PriorityChip label={i.priority_label} score={i.priority} /></td>
                      <td className="text-[var(--text-2)]">{i.topic}</td>
                      <td className="text-[var(--text-2)]">{i.status.replace("_", " ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
          )}
        </div>
      )}
    </>
  );
}
