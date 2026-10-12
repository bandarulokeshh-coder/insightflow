"use client";

import { useCallback, useEffect, useState } from "react";
import { Chip, EmptyState, ErrorBox, PageHeader, Panel, PriorityChip, SkeletonRows, TopicChip } from "@/components/ui";
import { api, type Recommendation } from "@/lib/api";

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await api.recommendations();
      setRecs(r.recommendations);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function track(rec: Recommendation) {
    try {
      await api.createIssue({
        title: rec.title,
        topic: rec.topic,
        priority: Math.round(rec.priority),
        priority_label: rec.priority_label,
        description: rec.action,
        evidence: JSON.stringify({ why: rec.why, examples: rec.examples.slice(0, 3), count: rec.evidence_count }),
      });
      setNotice(`“${rec.title}” added to the issue tracker.`);
      setTimeout(() => setNotice(null), 4000);
    } catch (e) {
      setNotice(`Failed to track: ${e}`);
    }
  }

  return (
    <>
      <PageHeader
        title="Recommendations"
        subtitle="Ranked by priority = frequency (30%) + negative share (30%) + severity (40%). Severity floors each issue class, so money-loss and safety issues are not outranked by sheer volume."
      />

      {notice && (
        <div className="mb-4 rounded-md border border-[var(--accent-line)] bg-[var(--accent-dim)] px-3.5 py-2.5 text-[12.5px]">
          {notice}
        </div>
      )}
      {error && <ErrorBox error={error} />}
      {!recs && !error && <SkeletonRows rows={4} />}

      {recs && recs.length === 0 && (
        <Panel>
          <EmptyState title="No recommendations available" body="Import feedback to generate prioritised recommendations." />
        </Panel>
      )}

      {recs && recs.length > 0 && (
        <div className="space-y-3">
          {recs.map((r, i) => (
            <Panel key={r.topic}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="num mt-[3px] w-4 shrink-0 text-right text-[13px] font-semibold text-[var(--text-3)]">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-[13.5px] font-semibold">{r.title}</h3>
                      <TopicChip value={r.topic} />
                      <PriorityChip label={r.priority_label} score={r.priority} />
                      <Chip tone={r.trend === "rising" ? "danger" : r.trend === "easing" ? "ok" : "neutral"}>
                        {r.trend === "rising" ? "↑ rising" : r.trend === "easing" ? "↓ easing" : "→ steady"}
                      </Chip>
                    </div>

                    <dl className="mt-2.5 flex flex-wrap gap-x-6 gap-y-1 text-[11.5px]">
                      <div className="flex gap-1.5">
                        <dt className="text-[var(--text-3)]">Items</dt>
                        <dd className="num font-medium">{r.evidence_count}</dd>
                      </div>
                      <div className="flex gap-1.5">
                        <dt className="text-[var(--text-3)]">Negative</dt>
                        <dd className="num font-medium text-[var(--danger)]">{r.negative_count}</dd>
                      </div>
                      <div className="flex gap-1.5">
                        <dt className="text-[var(--text-3)]">Negative share</dt>
                        <dd className="num font-medium">{Math.round(r.negative_share * 100)}%</dd>
                      </div>
                      <div className="flex gap-1.5">
                        <dt className="text-[var(--text-3)]">Max urgency</dt>
                        <dd className="num font-medium">{r.urgency_max}/3</dd>
                      </div>
                    </dl>
                  </div>
                </div>

                <button className="btn shrink-0" onClick={() => track(r)}>Track as issue</button>
              </div>

              <div className="mt-3.5 grid gap-3 lg:grid-cols-2">
                <div className="rounded-md border border-[var(--border)] bg-[var(--bg-subtle)] px-3 py-2.5">
                  <p className="label mb-1">Why this ranks here</p>
                  <p className="text-[12px] leading-relaxed text-[var(--text-2)]">{r.why}</p>
                </div>
                <div className="rounded-md border border-[var(--border)] bg-[var(--bg-subtle)] px-3 py-2.5">
                  <p className="label mb-1">Recommended action</p>
                  <p className="text-[12px] leading-relaxed text-[var(--text-2)]">{r.action}</p>
                </div>
              </div>

              {r.examples.length > 0 && (
                <details className="mt-2.5">
                  <summary className="cursor-pointer text-[11.5px] font-medium text-[var(--text-3)] hover:text-[var(--text-2)]">
                    Supporting evidence ({r.examples.length} {r.examples.length === 1 ? "quote" : "quotes"})
                  </summary>
                  <ul className="mt-2 space-y-1.5">
                    {r.examples.slice(0, 3).map((e, j) => (
                      <li key={j} className="border-l-2 border-[var(--border-strong)] bg-[var(--bg-subtle)] px-2.5 py-1.5 text-[11.5px] leading-relaxed text-[var(--text-2)]">
                        {e}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </Panel>
          ))}
        </div>
      )}
    </>
  );
}
