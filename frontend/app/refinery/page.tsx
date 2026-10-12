"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Chip, ErrorBox, Field, PageHeader, Panel, SkeletonRows, StatusDot, Toggle,
} from "@/components/ui";
import { api, type AdaptionRun, type RefineryStatus } from "@/lib/api";

const DEFAULT_RECIPES = {
  deduplication: true,
  prompt_rephrase: true,
  reasoning_traces: true,
  language_expansion: false,
  hallucination_mitigation: false,
};

const STATUS_TONE: Record<string, "ok" | "warn" | "danger" | "neutral"> = {
  succeeded: "ok",
  running: "warn",
  pending: "warn",
  failed: "danger",
};

export default function RefineryPage() {
  const [status, setStatus] = useState<RefineryStatus | null>(null);
  const [recipes, setRecipes] = useState<Record<string, boolean>>(DEFAULT_RECIPES);
  const [maxRows, setMaxRows] = useState(400);
  const [uniqueRows, setUniqueRows] = useState<number | null>(null);
  const [blueprint, setBlueprint] = useState("");
  const [runs, setRuns] = useState<AdaptionRun[]>([]);
  const [activeRun, setActiveRun] = useState<AdaptionRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadRuns = useCallback(async () => {
    const r = await api.runs();
    setRuns(r.runs);
    return r.runs;
  }, []);

  useEffect(() => {
    api.refineryStatus()
      .then((s) => { setStatus(s); setBlueprint(s.blueprint_default); })
      .catch((e) => setError(String(e)));
    api.dedup()
      .then((d) => { setUniqueRows(d.unique); setMaxRows(Math.min(400, d.unique)); })
      .catch(() => {});
    loadRuns().catch((e) => setError(String(e)));
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loadRuns]);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const { run_id } = await api.startRun({ mode: "auto", max_rows: maxRows, recipes, blueprint });
      setActiveRun(await api.run(run_id));
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        const r = await api.run(run_id);
        setActiveRun(r);
        if (r.status === "succeeded" || r.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          loadRuns();
        }
      }, 1200);
    } catch (e) {
      setError(String(e));
    } finally {
      setStarting(false);
    }
  }

  const running = activeRun && (activeRun.status === "running" || activeRun.status === "pending");
  const rowOptions = [...new Set([50, 100, 200, uniqueRows ?? 400])]
    .filter((n): n is number => typeof n === "number" && n > 0 && (uniqueRows === null || n <= uniqueRows))
    .sort((a, b) => a - b);

  return (
    <>
      <PageHeader
        title="Feedback Refinery"
        subtitle="The Adaption integration. Raw, duplicated, multilingual feedback goes in — deduplicated, normalized, rephrased and adapted data comes out, with measured quality grades."
        right={
          status && (
            <div className="flex items-center gap-2">
              <StatusDot
                tone={status.mode === "live" ? "ok" : "warn"}
                label={status.mode === "live" ? "Live · Adaptive Data API" : "Demo artifact"}
              />
            </div>
          )
        }
      />

      {error && <ErrorBox error={error} />}
      {!status && !error && <SkeletonRows rows={5} />}

      {status && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-4">
            {/* configuration */}
            <Panel
              title="Recipes"
              subtitle="Each transformation is applied in order, before any analysis runs"
            >
              <div className="grid gap-2 sm:grid-cols-2">
                {status.recipes_catalog.map((r) => (
                  <Toggle
                    key={r.key}
                    checked={!!recipes[r.key]}
                    onChange={(v) => setRecipes((p) => ({ ...p, [r.key]: v }))}
                    label={r.label}
                    hint={r.why}
                  />
                ))}
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-[190px_minmax(0,1fr)]">
                <Field
                  label="Rows to process"
                  hint={uniqueRows !== null ? `${uniqueRows.toLocaleString()} unique rows available` : undefined}
                >
                  <select className="input" value={maxRows} onChange={(e) => setMaxRows(Number(e.target.value))}>
                    {rowOptions.map((n) => (
                      <option key={n} value={n}>{n}{n === uniqueRows ? " (all)" : ""}</option>
                    ))}
                  </select>
                </Field>

                <Field
                  label="Blueprint"
                  hint="Injected as a system instruction for every generated row — analyst persona, output schema and tone."
                >
                  <textarea
                    className="input min-h-[92px] resize-y font-mono !text-[11px]"
                    value={blueprint}
                    onChange={(e) => setBlueprint(e.target.value)}
                  />
                </Field>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-[var(--border)] pt-4">
                <button className="btn btn-primary" onClick={start} disabled={starting || !!running}>
                  {running ? "Refinery running…" : starting ? "Starting…" : "Run refinery"}
                </button>
                <p className="text-[11.5px] text-[var(--text-3)]">
                  {status.mode === "live"
                    ? "Live mode reserves credits — an estimate is fetched before the run starts."
                    : "Demo mode replays the same pipeline locally · 0 credits."}
                </p>
              </div>
            </Panel>

            {/* run output */}
            {activeRun && (
              <Panel
                title={`Run #${activeRun.id}`}
                subtitle={`${activeRun.mode} · ${activeRun.status}`}
                right={<Chip tone={STATUS_TONE[activeRun.status]}>{activeRun.status}</Chip>}
              >
                {activeRun.grade_after !== null && (
                  <div className="mb-4 flex flex-wrap items-center gap-x-8 gap-y-3 rounded-md border border-[var(--border)] bg-[var(--bg-subtle)] px-3.5 py-3">
                    <div>
                      <p className="label">Data quality</p>
                      <p className="num mt-1 text-[15px]">
                        <span className="text-[var(--text-3)] line-through">{activeRun.grade_before}</span>
                        <span className="mx-1.5 text-[var(--text-3)]">→</span>
                        <span className="text-[17px] font-semibold text-[var(--ok)]">{activeRun.grade_after}</span>
                      </p>
                    </div>
                    <div>
                      <p className="label">Improvement</p>
                      <p className="num mt-1 text-[15px] font-semibold text-[var(--ok)]">+{activeRun.improvement_percent}%</p>
                    </div>
                    <div>
                      <p className="label">Duplicates removed</p>
                      <p className="num mt-1 text-[15px]">{activeRun.duplicates_removed.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="label">Rows adapted</p>
                      <p className="num mt-1 text-[15px]">{activeRun.rows_out.toLocaleString()}</p>
                    </div>
                  </div>
                )}

                <pre className="scroll-thin max-h-[280px] overflow-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 log">
{activeRun.log}
{running ? "▌" : ""}
                </pre>

                {activeRun.evaluation_note && (
                  <p className="mt-2.5 text-[11.5px] leading-relaxed text-[var(--text-3)]">{activeRun.evaluation_note}</p>
                )}
              </Panel>
            )}
          </div>

          {/* side column */}
          <div className="space-y-4">
            <Panel title="Run history" flush>
              {runs.length === 0 ? (
                <p className="px-4 py-6 text-center text-[12px] text-[var(--text-3)]">No runs yet.</p>
              ) : (
                <ul>
                  {runs.map((r) => (
                    <li key={r.id} className="border-b border-[var(--border)] last:border-b-0">
                      <button
                        onClick={() => setActiveRun(r)}
                        className={`w-full px-3.5 py-2.5 text-left transition-colors ${
                          activeRun?.id === r.id ? "bg-[var(--accent-dim)]" : "hover:bg-[var(--surface-2)]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="num text-[12px] font-medium">Run #{r.id}</span>
                          <Chip tone={STATUS_TONE[r.status]}>{r.status}</Chip>
                        </div>
                        <p className="mt-1 text-[11px] leading-relaxed text-[var(--text-3)]">
                          {r.created_at?.slice(0, 16).replace("T", " ")} · {r.mode}
                          <br />
                          {r.rows_in.toLocaleString()} in → {r.rows_out.toLocaleString()} out
                          {r.grade_after !== null && (
                            <>
                              {" · "}
                              <span className="num">{r.grade_before}</span>
                              {" → "}
                              <span className="num text-[var(--ok)]">{r.grade_after}</span>
                            </>
                          )}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="How a run executes" subtitle="Adaptive Data SDK call sequence">
              <ol className="space-y-1.5 font-mono text-[11px] leading-relaxed text-[var(--text-2)]">
                <li>1 · datasets.upload_file()</li>
                <li>2 · datasets.get_status()</li>
                <li>3 · datasets.adapt(estimate=True)</li>
                <li>4 · datasets.adapt(recipes, blueprint)</li>
                <li>5 · wait_for_completion()</li>
                <li>6 · get_evaluation()</li>
                <li>7 · download() → analysis</li>
              </ol>
            </Panel>

            <Panel title="Quality dimensions">
              <dl className="space-y-2.5 text-[11.5px] leading-relaxed">
                {[
                  ["Uniqueness", "30%", "Exact and near-duplicate rows removed. Duplicates skew frequency-based priority scores."],
                  ["Diversity", "20%", "Share of rows that are not a re-wording of another row. Template corpora score low even after deduplication."],
                  ["Language", "20%", "Non-English rows normalized so analysis compares like with like."],
                  ["Clarity", "20%", "Emoji, typos, shorthand and whitespace normalization."],
                  ["Metadata", "10%", "Applied only when the source carries rating or product fields."],
                ].map(([name, weight, desc]) => (
                  <div key={name} className="flex gap-3">
                    <dt className="w-[74px] shrink-0 font-medium text-[var(--text)]">{name}</dt>
                    <dd className="min-w-0 text-[var(--text-3)]">
                      <span className="num mr-1.5 text-[var(--text-2)]">{weight}</span>
                      {desc}
                    </dd>
                  </div>
                ))}
              </dl>
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}
