"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Chip, EmptyState, ErrorBox, Field, PageHeader, Panel, SentimentChip, SkeletonRows, TopicChip } from "@/components/ui";
import { api, type Facets, type Feedback, type FeedbackPage } from "@/lib/api";

const PAGE_SIZE = 12;

export default function FeedbackPage() {
  const [page, setPage] = useState<FeedbackPage | null>(null);
  const [facets, setFacets] = useState<Facets | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState({ sentiment: "", topic: "", channel: "", sort: "newest" });
  const [pg, setPg] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, f] = await Promise.all([
        api.feedback({ q, ...filters, page: pg, page_size: PAGE_SIZE }),
        api.facets(),
      ]);
      setPage(p);
      setFacets(f);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [q, filters, pg]);

  useEffect(() => { load(); }, [load]);

  const flash = (m: string) => { setNotice(m); setTimeout(() => setNotice(null), 4500); };

  async function importCsv(file: File) {
    try {
      const r = await api.importCsv(file);
      flash(`Imported ${r.imported.toLocaleString()} rows from ${r.filename}${r.skipped ? ` (${r.skipped} skipped)` : ""}. Run the refinery to adapt them.`);
      load();
    } catch (e) {
      flash(`Import failed: ${e}`);
    }
  }

  async function remove(id: number) {
    if (!confirm("Delete this feedback item?")) return;
    await api.deleteFeedback(id);
    load();
  }

  const totalPages = page ? Math.max(1, Math.ceil(page.total / page.page_size)) : 1;
  const dirty = q || Object.values(filters).some((v, i) => (i < 3 ? v : false));

  return (
    <>
      <PageHeader
        title="Feedback"
        subtitle="Search, filter and inspect every feedback record. Items display adapted text once the refinery has processed them."
        right={
          <>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && importCsv(e.target.files[0])}
            />
            <button className="btn" onClick={() => fileRef.current?.click()}>Import CSV</button>
            <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
              {showForm ? "Cancel" : "Add feedback"}
            </button>
          </>
        }
      />

      {notice && (
        <div className="mb-4 rounded-md border border-[var(--accent-line)] bg-[var(--accent-dim)] px-3.5 py-2.5 text-[12.5px] text-[var(--text)]">
          {notice}
        </div>
      )}

      {showForm && <AddForm onDone={(m) => { flash(m); setShowForm(false); load(); }} />}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          className="input max-w-[260px]"
          placeholder="Search feedback text"
          value={q}
          onChange={(e) => { setQ(e.target.value); setPg(1); }}
        />
        <select className="input w-auto" value={filters.sentiment} onChange={(e) => { setFilters({ ...filters, sentiment: e.target.value }); setPg(1); }}>
          <option value="">All sentiments</option>
          <option value="negative">Negative</option>
          <option value="neutral">Neutral</option>
          <option value="positive">Positive</option>
        </select>
        <select className="input w-auto" value={filters.topic} onChange={(e) => { setFilters({ ...filters, topic: e.target.value }); setPg(1); }}>
          <option value="">All categories</option>
          {facets?.topics.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="input w-auto" value={filters.channel} onChange={(e) => { setFilters({ ...filters, channel: e.target.value }); setPg(1); }}>
          <option value="">All channels</option>
          {facets?.channels.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
        </select>
        <select className="input w-auto" value={filters.sort} onChange={(e) => setFilters({ ...filters, sort: e.target.value })}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="most_negative">Most negative</option>
          <option value="most_positive">Most positive</option>
        </select>
        {dirty && (
          <button className="btn btn-ghost" onClick={() => { setQ(""); setFilters({ sentiment: "", topic: "", channel: "", sort: "newest" }); setPg(1); }}>
            Reset
          </button>
        )}
      </div>

      {error && <ErrorBox error={error} />}
      {loading && !page && <SkeletonRows rows={8} />}

      {page && (
        <Panel flush>
          <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-2.5">
            <p className="text-[12px] text-[var(--text-2)]">
              <span className="num font-medium text-[var(--text)]">{page.total.toLocaleString()}</span>{" "}
              {page.total === 1 ? "record" : "records"}
              {q && <span className="text-[var(--text-3)]"> matching “{q}”</span>}
            </p>
            <div className="flex items-center gap-1.5">
              <button className="btn !h-[26px] !px-2" disabled={pg <= 1} onClick={() => setPg((p) => p - 1)} aria-label="Previous page">←</button>
              <span className="num px-1 text-[11.5px] text-[var(--text-3)]">{pg} / {totalPages}</span>
              <button className="btn !h-[26px] !px-2" disabled={pg >= totalPages} onClick={() => setPg((p) => p + 1)} aria-label="Next page">→</button>
            </div>
          </div>

          <div className="scroll-thin overflow-x-auto">
            <table className="data">
              <thead>
                <tr>
                  <th style={{ minWidth: "42%" }}>Feedback</th>
                  <th>Sentiment</th>
                  <th>Classification</th>
                  <th>Urgency</th>
                  <th>Source</th>
                  <th className="num">Date</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {page.items.map((f) => (
                  <Row
                    key={f.id}
                    f={f}
                    showRaw={showRaw === f.id}
                    onToggleRaw={() => setShowRaw(showRaw === f.id ? null : f.id)}
                    onDelete={() => remove(f.id)}
                  />
                ))}
                {page.items.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState
                        title="No feedback matches these filters"
                        body="Try removing a filter, or import additional feedback to widen the dataset."
                        action={dirty ? <button className="btn" onClick={() => { setQ(""); setFilters({ sentiment: "", topic: "", channel: "", sort: "newest" }); }}>Reset filters</button> : undefined}
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </>
  );
}

function Row({ f, showRaw, onToggleRaw, onDelete }: {
  f: Feedback;
  showRaw: boolean;
  onToggleRaw: () => void;
  onDelete: () => void;
}) {
  const adapted = !!f.adapted_text && f.adapted_text.trim() !== f.text.trim();
  const hasTruth = !!f.official_category;
  const match = !hasTruth || f.official_category === f.predicted_category;

  return (
    <tr>
      <td>
        <p className="leading-relaxed text-[var(--text)]">{showRaw ? f.text : f.display_text}</p>

        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-[var(--text-3)]">
            {f.author}
            {f.product ? ` · ${f.product}` : ""}
          </span>
          {f.rating != null && <span className="num text-[11px] text-[var(--text-3)]">{f.rating}/5 rating</span>}
          {adapted && (
            <button className="chip chip-accent cursor-pointer" onClick={onToggleRaw}>
              {showRaw ? "Show adapted" : "Show original"}
            </button>
          )}
          {f.detected_language && f.detected_language !== "en" && (
            <Chip mono>{f.detected_language} → en</Chip>
          )}
          {f.is_duplicate && <Chip>duplicate · excluded</Chip>}
        </div>

        {f.adaption_action && (
          <p className="mt-2 border-l-2 border-[var(--accent-line)] bg-[var(--accent-dim)] px-2.5 py-1.5 text-[11.5px] leading-relaxed text-[var(--text-2)]">
            <span className="font-medium text-[var(--text)]">Adaption recommends: </span>
            {f.adaption_action}
          </p>
        )}

        {f.reasoning_trace && (
          <details className="mt-2">
            <summary className="cursor-pointer text-[11px] font-medium text-[var(--text-3)] hover:text-[var(--text-2)]">
              Refinery reasoning
            </summary>
            <p className="mt-1.5 rounded-md border-l-2 border-[var(--border-strong)] bg-[var(--bg-subtle)] px-2.5 py-2 text-[11.5px] leading-relaxed text-[var(--text-2)]">
              {f.reasoning_trace}
            </p>
          </details>
        )}
      </td>

      <td><SentimentChip value={f.sentiment} /></td>

      <td>
        {f.predicted_category ? (
          <div className="space-y-1">
            <Chip tone={hasTruth ? (match ? "ok" : "danger") : "accent"}>{f.predicted_category}</Chip>
            {hasTruth && (
              <p className="text-[10.5px] text-[var(--text-3)]">
                {match ? "matches label" : `label: ${f.official_category}`}
              </p>
            )}
          </div>
        ) : (
          <span className="text-[12px] text-[var(--text-3)]">—</span>
        )}
      </td>

      <td>
        {f.urgency >= 2 ? (
          <span className="text-[11.5px] font-medium text-[var(--warn)]">{f.urgency}/3</span>
        ) : (
          <span className="num text-[12px] text-[var(--text-3)]">{f.urgency}</span>
        )}
      </td>

      <td><span className="text-[12px] text-[var(--text-2)]">{f.channel.replace("_", " ")}</span></td>

      <td className="num whitespace-nowrap text-right text-[11.5px] text-[var(--text-3)]">
        {(f.source_date || f.created_at)?.slice(0, 10)}
      </td>

      <td className="text-right">
        <button
          onClick={onDelete}
          title="Delete"
          aria-label="Delete feedback"
          className="rounded p-1 text-[var(--text-3)] transition-colors hover:bg-[var(--danger-dim)] hover:text-[var(--danger)]"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
            <path d="M3 6h18M8 6V4h8v2m1 0-1 14H8L7 6" />
          </svg>
        </button>
      </td>
    </tr>
  );
}

function AddForm({ onDone }: { onDone: (msg: string) => void }) {
  const [text, setText] = useState("");
  const [channel, setChannel] = useState("form");
  const [author, setAuthor] = useState("");
  const [rating, setRating] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (text.trim().length < 8) return;
    setBusy(true);
    try {
      const created = await api.createFeedback({
        text,
        channel,
        author: author || "Anonymous",
        rating: rating ? Number(rating) : null,
      });
      onDone(`Feedback added — classified as “${created.predicted_category ?? created.topic}”, sentiment “${created.sentiment}”.`);
      setText("");
      setRating("");
      setAuthor("");
    } catch (e) {
      onDone(`Failed to add: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Add feedback" className="mb-4">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_170px_150px_130px_auto] lg:items-end">
        <Field label="Feedback text" hint="Imported rows are analyzed automatically on save.">
          <textarea
            className="input min-h-[64px] resize-y"
            placeholder="What did the customer say?"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </Field>
        <Field label="Customer">
          <input className="input" placeholder="Name" value={author} onChange={(e) => setAuthor(e.target.value)} />
        </Field>
        <Field label="Channel">
          <select className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
            {["form", "review", "survey", "support", "app_store", "social"].map((c) => (
              <option key={c} value={c}>{c.replace("_", " ")}</option>
            ))}
          </select>
        </Field>
        <Field label="Rating">
          <select className="input" value={rating} onChange={(e) => setRating(e.target.value)}>
            <option value="">None</option>
            {[1, 2, 3, 4, 5].map((r) => <option key={r} value={r}>{r} of 5</option>)}
          </select>
        </Field>
        <button className="btn btn-primary" disabled={busy || text.trim().length < 8} onClick={submit}>
          {busy ? "Adding…" : "Add"}
        </button>
      </div>
    </Panel>
  );
}
