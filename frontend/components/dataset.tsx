"use client";

import { useState } from "react";
import { Chip, Panel } from "@/components/ui";
import type { Agreement, DedupStats } from "@/lib/api";

export function DatasetCard({ dedup, onLoadSample, loading }: {
  dedup: DedupStats;
  onLoadSample: () => void;
  loading: boolean;
}) {
  const pct = Math.round(dedup.duplication_rate * 1000) / 10;
  const multiplier = Math.round(dedup.rows_ingested / Math.max(1, dedup.unique));

  return (
    <Panel
      title="Dataset integrity"
      subtitle="Measured on ingestion, before any analysis"
      right={
        <button className="btn btn-ghost" onClick={onLoadSample} disabled={loading}>
          {loading ? "Importing…" : "Import dated sample feed"}
        </button>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
        <p className="max-w-3xl text-[12.5px] leading-relaxed text-[var(--text-2)]">
          The official BuildBattle dataset contains{" "}
          <span className="num font-medium text-[var(--text)]">{dedup.rows_ingested.toLocaleString()}</span> rows, but only{" "}
          <span className="num font-medium text-[var(--text)]">{dedup.unique.toLocaleString()} unique</span> reviews —{" "}
          <span className="num font-medium text-[var(--danger)]">{pct}% of the file is exact duplication</span>. Without
          collapsing them, every frequency-based priority score is inflated roughly{" "}
          <span className="num font-medium text-[var(--text)]">{multiplier}×</span>. Deduplication therefore runs at
          ingestion, before a single metric is computed.
        </p>

        <dl className="flex gap-8">
          <div>
            <dt className="label">Ingested</dt>
            <dd className="num mt-1 text-[16px] font-semibold">{dedup.rows_ingested.toLocaleString()}</dd>
          </div>
          <div>
            <dt className="label">Duplicates</dt>
            <dd className="num mt-1 text-[16px] font-semibold text-[var(--danger)]">{dedup.exact_duplicates.toLocaleString()}</dd>
          </div>
          <div>
            <dt className="label">Unique</dt>
            <dd className="num mt-1 text-[16px] font-semibold text-[var(--ok)]">{dedup.unique.toLocaleString()}</dd>
          </div>
        </dl>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <div className="h-[3px] flex-1 overflow-hidden rounded-full bg-[var(--surface-3)]">
          <div className="h-full rounded-full bg-[var(--danger)]" style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
        <span className="num text-[11px] text-[var(--text-3)]">{pct}% duplicated</span>
      </div>
    </Panel>
  );
}

export function AgreementCard({ agreement }: { agreement: Agreement }) {
  const [showMatrix, setShowMatrix] = useState(false);

  if (!agreement.available) {
    return (
      <Panel title="Classification agreement">
        <p className="py-4 text-center text-[12px] text-[var(--text-3)]">
          No labelled rows in this workspace. Import a dataset with a <code className="font-mono">category</code> column
          to measure classifier agreement.
        </p>
      </Panel>
    );
  }

  const acc = Math.round((agreement.accuracy ?? 0) * 1000) / 10;
  const labels = agreement.labels || [];
  const matrix = agreement.matrix || [];
  const cell = (t: string, p: string) => matrix.find((m) => m.truth === t && m.predicted === p)?.count ?? 0;

  return (
    <Panel
      title="Classification agreement"
      subtitle="Our classifier scored against the dataset's own ground-truth labels"
      right={
        <button className="btn btn-ghost" onClick={() => setShowMatrix((s) => !s)} aria-expanded={showMatrix}>
          {showMatrix ? "Hide matrix" : "Confusion matrix"}
        </button>
      }
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div>
          <div className="flex items-baseline gap-2.5">
            <span className="num text-[28px] font-semibold leading-none tracking-[-0.02em] text-[var(--ok)]">{acc}%</span>
            <span className="text-[11.5px] text-[var(--text-3)]">
              <span className="num">{agreement.correct}</span> of{" "}
              <span className="num">{agreement.labelled_rows}</span> rows match
            </span>
          </div>
          <p className="mt-2.5 text-[11.5px] leading-relaxed text-[var(--text-3)]">
            The AI layer is measured rather than asserted. Rules were tuned on this corpus, so this is
            in-sample agreement — stated plainly rather than presented as generalisation.
          </p>
        </div>

        <dl className="space-y-2">
          {(agreement.per_class || []).map((c) => (
            <div key={c.label}>
              <div className="flex items-baseline justify-between gap-2 text-[11.5px]">
                <dt className="font-medium text-[var(--text-2)]">{c.label}</dt>
                <dd className="num shrink-0 text-[var(--text-3)]">
                  n={c.support} · P {Math.round(c.precision * 100)}% · R {Math.round(c.recall * 100)}%
                </dd>
              </div>
              <div className="mt-1 h-[3px] overflow-hidden rounded-full bg-[var(--surface-3)]">
                <div
                  className="h-full rounded-full bg-[var(--accent)]"
                  style={{ width: `${Math.round(c.f1 * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </dl>
      </div>

      {showMatrix && (
        <div className="mt-4 border-t border-[var(--border)] pt-4">
          <div className="scroll-thin overflow-x-auto">
            <table className="data">
              <thead>
                <tr>
                  <th>Truth ↓ / Predicted →</th>
                  {labels.map((l) => <th key={l} className="num">{l.split(" ")[0]}</th>)}
                </tr>
              </thead>
              <tbody>
                {labels.map((t) => (
                  <tr key={t}>
                    <td className="whitespace-nowrap font-medium">{t}</td>
                    {labels.map((p) => {
                      const v = cell(t, p);
                      return (
                        <td key={p} className="num">
                          <span className={v === 0 ? "text-[var(--text-3)]" : t === p ? "font-semibold text-[var(--ok)]" : "font-semibold text-[var(--danger)]"}>
                            {v}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {agreement.method && <p className="mt-2.5 text-[11px] text-[var(--text-3)]">{agreement.method}</p>}
        </div>
      )}
    </Panel>
  );
}
