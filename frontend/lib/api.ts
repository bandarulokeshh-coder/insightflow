/**
 * Typed API client.
 *
 * In local dev the Next.js server proxies /api/* → FastAPI (see next.config.ts),
 * so relative paths work everywhere. For a split deploy (Vercel + Render),
 * set NEXT_PUBLIC_API_URL to the backend origin.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText} — ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<Health>("/health"),

  feedback: (params: Record<string, string | number | boolean | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== null) qs.set(k, String(v));
    });
    return req<FeedbackPage>(`/feedback?${qs.toString()}`);
  },
  createFeedback: (body: { text: string; author?: string; channel?: string; product?: string; rating?: number | null }) =>
    req<Feedback>(`/feedback`, { method: "POST", body: JSON.stringify(body) }),
  facets: () => req<Facets>("/feedback/facets"),
  importCsv: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_BASE}/api/feedback/import`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<{ imported: number; skipped: number; filename: string }>;
  },
  deleteFeedback: (id: number) => req<void>(`/feedback/${id}`, { method: "DELETE" }),

  dedup: () => req<DedupStats>("/analytics/dedup"),
  agreement: () => req<Agreement>("/analytics/agreement"),
  importSample: () => req<{ imported: number; duplicates: number; unique: number; file: string }>(
    "/demo/import-sample", { method: "POST" }
  ),

  overview: (params: Record<string, string | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, v));
    return req<Overview>(`/analytics/overview?${qs.toString()}`);
  },
  recommendations: (params: Record<string, string | undefined> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, v));
    return req<{ count: number; recommendations: Recommendation[] }>(`/analytics/recommendations?${qs}`);
  },

  refineryStatus: () => req<RefineryStatus>("/adaption/status"),
  startRun: (body: { mode: string; max_rows: number; recipes: Record<string, boolean>; blueprint?: string }) =>
    req<{ run_id: number; mode: string; status: string }>("/adaption/runs", { method: "POST", body: JSON.stringify(body) }),
  runs: () => req<{ runs: AdaptionRun[] }>("/adaption/runs"),
  run: (id: number) => req<AdaptionRun>(`/adaption/runs/${id}`),

  issues: (status?: string) => req<{ issues: Issue[] }>(`/issues${status ? `?status=${status}` : ""}`),
  createIssue: (body: Partial<Issue>) => req<Issue>("/issues", { method: "POST", body: JSON.stringify(body) }),
  updateIssue: (id: number, body: Partial<Issue>) => req<Issue>(`/issues/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteIssue: (id: number) => req<void>(`/issues/${id}`, { method: "DELETE" }),

  report: () => req<Report>("/reports/insight"),
  exportUrl: (format: "md" | "json") => `${API_BASE}/api/reports/export?format=${format}`,
};

// ─── types ──────────────────────────────────────────────────────────────
export type Health = {
  ok: boolean;
  refinery: { sdk_installed: boolean; api_key_present: boolean; mode: "live" | "demo" };
};

export type Feedback = {
  id: number;
  text: string;
  adapted_text: string | null;
  display_text: string;
  author: string;
  channel: string;
  product: string;
  rating: number | null;
  source_date: string | null;
  created_at: string;
  sentiment: "positive" | "neutral" | "negative" | null;
  sentiment_score: number | null;
  topic: string | null;
  complaint: string | null;
  urgency: number;
  detected_language: string | null;
  official_category: string | null;
  predicted_category: string | null;
  adaption_action: string | null;
  reasoning_trace: string | null;
  is_duplicate: boolean;
  analyzed: boolean;
};

export type FeedbackPage = { total: number; page: number; page_size: number; items: Feedback[] };
export type Facets = { topics: string[]; channels: string[]; products: string[] };

export type Overview = {
  metrics: {
    total_feedback: number;
    negative: number;
    negative_share: number;
    positive_share: number;
    avg_rating: number | null;
    high_urgency: number;
    analyzed: number;
    tracked_issues: number;
  };
  sentiment_distribution: { name: string; value: number }[];
  topic_distribution: { topic: string; total: number; negative: number }[];
  channel_distribution: { name: string; value: number }[];
  trend: { month: string; total: number; positive: number; neutral: number; negative: number }[];
  top_complaints: { complaint: string; count: number }[];
  data_quality: {
    mode: string | null;
    grade_before: number | null;
    grade_after: number | null;
    improvement_percent: number | null;
    run_id: number | null;
    status: string | null;
    evaluation_note: string | null;
  };
};

export type Recommendation = {
  topic: string;
  priority: number;
  priority_label: string;
  title: string;
  action: string;
  why: string;
  evidence_count: number;
  negative_count: number;
  negative_share: number;
  trend: string;
  urgency_max: number;
  examples: string[];
};

export type DedupStats = {
  rows_ingested: number;
  exact_duplicates: number;
  unique: number;
  duplication_rate: number;
  note: string;
};

export type Agreement = {
  available: boolean;
  reason?: string;
  labelled_rows?: number;
  correct?: number;
  accuracy?: number;
  labels?: string[];
  per_class?: { label: string; support: number; precision: number; recall: number; f1: number }[];
  matrix?: { truth: string; predicted: string; count: number }[];
  method?: string;
};

export type RefineryStatus = {
  sdk_installed: boolean;
  api_key_present: boolean;
  mode: "live" | "demo";
  blueprint_default: string;
  recipes_catalog: { key: string; label: string; why: string }[];
};

export type AdaptionRun = {
  id: number;
  run_ref: string | null;
  mode: string;
  status: "pending" | "running" | "succeeded" | "failed";
  max_rows: number;
  recipes: string;
  blueprint: string;
  rows_in: number;
  rows_out: number;
  duplicates_removed: number;
  languages_normalized: number;
  credits_estimate: number | null;
  credits_consumed: number | null;
  grade_before: number | null;
  grade_after: number | null;
  improvement_percent: number | null;
  evaluation_note: string;
  log: string;
  created_at: string;
  finished_at: string | null;
};

export type Issue = {
  id: number;
  title: string;
  topic: string;
  description: string;
  priority: number;
  priority_label: string;
  status: "open" | "in_progress" | "resolved";
  evidence: string;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type Report = {
  generated_at: string;
  headline: {
    total_feedback: number;
    negative_share: number;
    top_priority: string | null;
    data_quality: {
      grade_before: number | null;
      grade_after: number | null;
      improvement_percent: number | null;
      mode: string | null;
    };
  };
  recommendations: Recommendation[];
  tracked_issues: Issue[];
  topic_distribution: { topic: string; total: number; negative: number }[];
};
