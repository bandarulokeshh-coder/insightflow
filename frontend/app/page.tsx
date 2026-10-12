"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Chip, EmptyState, ErrorBox, GradeBanner, Meter, PageHeader, Panel,
  PriorityChip, SkeletonRows, Stat, TopicChip,
} from "@/components/ui";
import { SentimentDonut, TopicBars, TrendChart } from "@/components/charts";
import { AgreementCard, DatasetCard } from "@/components/dataset";
import {
  api, type Agreement, type DedupStats, type Facets, type Overview, type Recommendation,
} from "@/lib/api";

export default function Dashboard() {
  const [data, setData] = useState<Overview | null>(null);
  const [facets, setFacets] = useState<Facets | null>(null);
  const [topRec, setTopRec] = useState<Recommendation | null>(null);
  const [dedup, setDedup] = useState<DedupStats | null>(null);
  const [agreement, setAgreement] = useState<Agreement | null>(null);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({ sentiment: "", topic: "", channel: "" });

  const load = useCallback(async () => {
    try {
      const [ov, fc, rc, dd, ag] = await Promise.all([
        api.overview(filters),
        api.facets(),
        api.recommendations(filters),
        api.dedup(),
        api.agreement(),
      ]);
      setData(ov);
      setFacets(fc);
      setTopRec(rc.recommendations[0] ?? null);
      setDedup(dd);
      setAgreement(ag);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  async function loadSample() {
    setImporting(true);
    try {
      await api.importSample();
      await load();
    } finally {
      setImporting(false);
    }
  }

  const set = (k: keyof typeof filters, v: string) => setFilters((f) => ({ ...f, [k]: v }));
  const active = Object.values(filters).some(Boolean);

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="All figures are computed from feedback that passed through the Feedback Refinery — deduplicated, normalized and adapted before analysis."
        right={
          <>
            {active && (
              <button className="btn btn-ghost" onClick={() => setFilters({ sentiment: "", topic: "", channel: "" })}>
                Clear filters
              </button>
            )}
            <Link href="/refinery" className="btn btn-primary">Run refinery</Link>
          </>
        }
      />

      {error && <ErrorBox error={error} />}
      {!data && !error && <SkeletonRows rows={6} className="mt-2" />}

      {data && (
        <div className="space-y-4">
          <GradeBanner
            before={data.data_quality.grade_before}
            after={data.data_quality.grade_after}
            improvement={data.data_quality.improvement_percent}
            mode={data.data_quality.mode}
            note={data.data_quality.evaluation_note}
          />

          {dedup && <DatasetCard dedup={dedup} onLoadSample={loadSample} loading={importing} />}

          {agreement && <AgreementCard agreement={agreement} />}

          {/* filters */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="label mr-1">Filters</span>
            <select className="input w-auto" value={filters.sentiment} onChange={(e) => set("sentiment", e.target.value)}>
              <option value="">All sentiments</option>
              <option value="negative">Negative</option>
              <option value="neutral">Neutral</option>
              <option value="positive">Positive</option>
            </select>
            <select className="input w-auto" value={filters.topic} onChange={(e) => set("topic", e.target.value)}>
              <option value="">All categories</option>
              {facets?.topics.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <select className="input w-auto" value={filters.channel} onChange={(e) => set("channel", e.target.value)}>
              <option value="">All channels</option>
              {facets?.channels.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
            </select>
          </div>

          {/* metrics */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Stat label="Feedback analyzed" value={data.metrics.total_feedback.toLocaleString()} detail={`${data.metrics.analyzed.toLocaleString()} with analysis`} />
            <Stat label="Negative" value={`${Math.round(data.metrics.negative_share * 100)}%`} tone="danger" detail={`${data.metrics.negative.toLocaleString()} of ${data.metrics.total_feedback.toLocaleString()}`} />
            <Stat label="Avg rating" value={data.metrics.avg_rating ?? "—"} detail={data.metrics.avg_rating ? "where provided" : "not in dataset"} />
            <Stat label="High urgency" value={data.metrics.high_urgency} tone="warn" detail="refund / escalation signals" />
            <Stat label="Tracked issues" value={data.metrics.tracked_issues} detail={<Link href="/issues" className="link">Open issue tracker</Link>} />
          </div>

          {/* charts */}
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
            <Panel title="Sentiment distribution" subtitle="Share of analyzed feedback">
              <SentimentDonut data={data.sentiment_distribution} />
            </Panel>

            <Panel title="Sentiment trend" subtitle="Monthly volume by sentiment">
              {data.trend.length > 1 ? (
                <TrendChart data={data.trend} />
              ) : (
                <EmptyState
                  title="No timestamps in this dataset"
                  body="Trends cannot be computed honestly without dates. The official BuildBattle dataset ships without them — import the dated sample feed to enable this view."
                  action={
                    <button className="btn" onClick={loadSample} disabled={importing}>
                      {importing ? "Importing…" : "Import dated sample feed"}
                    </button>
                  }
                />
              )}
            </Panel>
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
            <Panel title="Issues by category" subtitle="Total volume against negative volume">
              <TopicBars data={data.topic_distribution} />
            </Panel>

            <Panel title="Top categories" flush>
              <table className="data">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th className="num">Items</th>
                    <th className="num">Negative</th>
                    <th>Share</th>
                  </tr>
                </thead>
                <tbody>
                  {data.topic_distribution.slice(0, 6).map((t) => (
                    <tr key={t.topic}>
                      <td className="font-medium">{t.topic}</td>
                      <td className="num">{t.total}</td>
                      <td className="num text-[var(--danger)]">{t.negative}</td>
                      <td className="w-[92px]">
                        <div className="flex items-center gap-2">
                          <Meter value={t.total ? (t.negative / t.total) * 100 : 0} tone="danger" />
                          <span className="num w-8 shrink-0 text-right text-[11px] text-[var(--text-3)]">
                            {Math.round((t.negative / Math.max(1, t.total)) * 100)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
          </div>

          {data.top_complaints.length > 0 && (
            <Panel title="Most frequent complaints" subtitle="Extracted from the adapted text" flush>
              <ul>
                {data.top_complaints.map((c, i) => (
                  <li key={i} className="flex items-start gap-3 border-b border-[var(--border)] px-4 py-2.5 last:border-b-0">
                    <span className="num mt-[1px] w-5 shrink-0 text-right text-[11.5px] font-medium text-[var(--text-3)]">{c.count}</span>
                    <span className="text-[12.5px] leading-relaxed text-[var(--text-2)]">{c.complaint}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          )}

          {topRec && (
            <Panel
              title="Highest-priority recommendation"
              right={<Link href="/recommendations" className="btn btn-ghost">View all</Link>}
            >
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-[13.5px] font-semibold">{topRec.title}</h3>
                <TopicChip value={topRec.topic} />
                <PriorityChip label={topRec.priority_label} score={topRec.priority} />
                <Chip>{topRec.trend} trend</Chip>
              </div>
              <p className="mt-2 max-w-4xl text-[12.5px] leading-relaxed text-[var(--text-2)]">{topRec.why}</p>
            </Panel>
          )}
        </div>
      )}
    </>
  );
}
