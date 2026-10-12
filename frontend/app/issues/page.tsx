"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Chip, EmptyState, ErrorBox, PageHeader, Panel, PriorityChip, SkeletonRows } from "@/components/ui";
import { api, type Issue } from "@/lib/api";

const STATUS_TONE: Record<string, "danger" | "warn" | "ok"> = {
  open: "danger",
  in_progress: "warn",
  resolved: "ok",
};

const FILTERS = [
  { value: "", label: "All" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "resolved", label: "Resolved" },
];

export default function IssuesPage() {
  const [issues, setIssues] = useState<Issue[] | null>(null);
  const [all, setAll] = useState<Issue[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const load = useCallback(async () => {
    try {
      const [filtered, everything] = await Promise.all([
        api.issues(filter || undefined),
        api.issues(),
      ]);
      setIssues(filtered.issues);
      setAll(everything.issues);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  async function setStatus(issue: Issue, status: Issue["status"]) {
    await api.updateIssue(issue.id, { status });
    load();
  }

  async function remove(issue: Issue) {
    if (!confirm(`Delete issue “${issue.title}”?`)) return;
    await api.deleteIssue(issue.id);
    load();
  }

  const count = (v: string) => (v === "" ? all.length : all.filter((i) => i.status === v).length);

  return (
    <>
      <PageHeader
        title="Issues"
        subtitle="Recommendations that were actioned, tracked from open through to resolved."
        right={
          <div className="flex flex-wrap gap-1.5" role="tablist">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                role="tab"
                aria-selected={filter === f.value}
                onClick={() => setFilter(f.value)}
                className={`btn ${filter === f.value ? "border-[var(--accent-line)] bg-[var(--accent-dim)] text-[var(--accent)]" : "btn-ghost"}`}
              >
                {f.label}
                <span className="num text-[11px] opacity-70">{count(f.value)}</span>
              </button>
            ))}
          </div>
        }
      />

      {error && <ErrorBox error={error} />}
      {!issues && !error && <SkeletonRows rows={4} />}

      {issues && issues.length === 0 && (
        <Panel>
          <EmptyState
            title="No issues in this view"
            body="Track a recommendation to create your first issue."
            action={<Link href="/recommendations" className="btn btn-primary">Go to recommendations</Link>}
          />
        </Panel>
      )}

      {issues && issues.length > 0 && (
        <Panel flush>
          <table className="data">
            <thead>
              <tr>
                <th style={{ width: "32%" }}>Issue</th>
                <th>Priority</th>
                <th>Status</th>
                <th style={{ width: "26%" }}>Action</th>
                <th>Updated</th>
                <th aria-label="Controls" />
              </tr>
            </thead>
            <tbody>
              {issues.map((issue) => {
                let evidence: { why?: string; examples?: string[] } = {};
                try {
                  evidence = issue.evidence ? JSON.parse(issue.evidence) : {};
                } catch {
                  evidence = {};
                }
                return (
                  <tr key={issue.id}>
                    <td>
                      <p className="font-medium">{issue.title}</p>
                      {issue.topic && <p className="mt-0.5 text-[11px] text-[var(--text-3)]">{issue.topic}</p>}
                      {evidence.examples && evidence.examples.length > 0 && (
                        <details className="mt-1.5">
                          <summary className="cursor-pointer text-[11px] font-medium text-[var(--text-3)] hover:text-[var(--text-2)]">
                            Evidence
                          </summary>
                          <ul className="mt-1.5 space-y-1">
                            {evidence.examples.slice(0, 3).map((e, i) => (
                              <li key={i} className="border-l-2 border-[var(--border-strong)] pl-2 text-[11.5px] leading-relaxed text-[var(--text-2)]">
                                {e}
                              </li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </td>
                    <td><PriorityChip label={issue.priority_label} score={issue.priority} /></td>
                    <td><Chip tone={STATUS_TONE[issue.status]}>{issue.status.replace("_", " ")}</Chip></td>
                    <td className="text-[12px] leading-relaxed text-[var(--text-2)]">{issue.description}</td>
                    <td className="num whitespace-nowrap text-[11.5px] text-[var(--text-3)]">
                      {(issue.updated_at || issue.created_at)?.slice(0, 10)}
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-1.5">
                        <select
                          className="input !h-[26px] !w-auto !py-0 !text-[11.5px]"
                          value={issue.status}
                          onChange={(e) => setStatus(issue, e.target.value as Issue["status"])}
                          aria-label={`Status for ${issue.title}`}
                        >
                          <option value="open">Open</option>
                          <option value="in_progress">In progress</option>
                          <option value="resolved">Resolved</option>
                        </select>
                        <button
                          onClick={() => remove(issue)}
                          className="rounded p-1 text-[var(--text-3)] transition-colors hover:bg-[var(--danger-dim)] hover:text-[var(--danger)]"
                          title="Delete issue"
                          aria-label={`Delete ${issue.title}`}
                        >
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
                            <path d="M3 6h18M8 6V4h8v2m1 0-1 14H8L7 6" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>
      )}
    </>
  );
}
