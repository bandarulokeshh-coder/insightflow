"use client";

import type { ReactNode } from "react";

// ─────────────────────────────────────────────────────────────────────
// Layout
// ─────────────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-4">
      <div className="min-w-0">
        <h1 className="text-[17px] font-semibold tracking-[-0.01em] text-[var(--text)]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-[12.5px] leading-relaxed text-[var(--text-2)]">{subtitle}</p>}
      </div>
      {right && <div className="flex shrink-0 flex-wrap items-center gap-2">{right}</div>}
    </header>
  );
}

export function Panel({
  title, subtitle, right, children, className = "", flush = false,
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  flush?: boolean;
}) {
  return (
    <section className={`panel ${className}`}>
      {(title || right) && (
        <div className="panel-head">
          <div className="min-w-0">
            {title && <h2 className="panel-title">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[11.5px] text-[var(--text-3)]">{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      <div className={flush ? "" : "panel-body"}>{children}</div>
    </section>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label mb-1.5 block">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-[var(--text-3)]">{hint}</span>}
    </label>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Status primitives — color carries meaning, never decoration
// ─────────────────────────────────────────────────────────────────────
type Tone = "neutral" | "ok" | "warn" | "danger" | "accent";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "",
  ok: "chip-ok",
  warn: "chip-warn",
  danger: "chip-danger",
  accent: "chip-accent",
};

export function Chip({ children, tone = "neutral", mono = false, title }: { children: ReactNode; tone?: Tone; mono?: boolean; title?: string }) {
  return <span className={`chip ${TONE_CLASS[tone]} ${mono ? "chip-mono" : ""}`} title={title}>{children}</span>;
}

const SENTIMENT_TONE: Record<string, Tone> = {
  positive: "ok",
  neutral: "neutral",
  negative: "danger",
};

export function SentimentChip({ value }: { value: string | null }) {
  const v = value || "neutral";
  const dotColor = v === "positive" ? "var(--ok)" : v === "negative" ? "var(--danger)" : "var(--text-3)";
  return (
    <span className={`chip ${TONE_CLASS[SENTIMENT_TONE[v] ?? "neutral"]}`}>
      <span className="dot" style={{ background: dotColor }} />
      {v}
    </span>
  );
}

const PRIORITY_TONE: Record<string, Tone> = {
  critical: "danger",
  high: "warn",
  medium: "neutral",
  low: "neutral",
};

export function PriorityChip({ label, score }: { label: string; score?: number }) {
  return (
    <span className={`chip ${TONE_CLASS[PRIORITY_TONE[label] ?? "neutral"]}`} title={score !== undefined ? `priority score ${score}` : undefined}>
      <span className="font-semibold uppercase tracking-wide">{label}</span>
      {score !== undefined && <span className="opacity-70">· {Math.round(score)}</span>}
    </span>
  );
}

export function TopicChip({ value }: { value: string | null }) {
  if (!value) return null;
  return <span className="chip">{value}</span>;
}

export function StatusDot({ tone = "neutral", label }: { tone?: Tone; label: string }) {
  const color = { ok: "var(--ok)", warn: "var(--warn)", danger: "var(--danger)", accent: "var(--accent)", neutral: "var(--text-3)" }[tone];
  return (
    <span className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[var(--text-2)]">
      <span className="dot" style={{ background: color }} />
      {label}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Metrics
// ─────────────────────────────────────────────────────────────────────
export function Stat({
  label, value, detail, tone, align = "left",
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "default" | "ok" | "warn" | "danger";
  align?: "left" | "right";
}) {
  const valueColor: Record<string, string> = {
    default: "var(--text)",
    ok: "var(--ok)",
    warn: "var(--warn)",
    danger: "var(--danger)",
  };
  return (
    <div className="panel px-3.5 py-3" style={{ textAlign: align }}>
      <p className="label">{label}</p>
      <p className="stat-value mt-1.5 text-[21px] font-semibold leading-none tracking-[-0.02em]" style={{ color: valueColor[tone ?? "default"] }}>
        {value}
      </p>
      {detail && <p className="mt-1.5 text-[11.5px] leading-snug text-[var(--text-3)]">{detail}</p>}
    </div>
  );
}

export function Meter({ value, max = 100, tone = "accent" }: { value: number; max?: number; tone?: "accent" | "ok" | "danger" | "warn" }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const color = { accent: "var(--accent)", ok: "var(--ok)", danger: "var(--danger)", warn: "var(--warn)" }[tone];
  return (
    <div className="h-[3px] w-full overflow-hidden rounded-full bg-[var(--surface-3)]">
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Feedback states — skeletons, not spinners, for a product feel
// ─────────────────────────────────────────────────────────────────────
export function SkeletonRows({ rows = 4, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-2.5 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-9 w-full" style={{ opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-[12.5px] text-[var(--text-3)]">
      <svg className="animate-spin" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M21 12a9 9 0 1 1-6.2-8.6" strokeLinecap="round" />
      </svg>
      {label ?? "Loading"}
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
      <p className="text-[13px] font-medium text-[var(--text)]">{title}</p>
      {body && <p className="mt-1 max-w-md text-[12px] leading-relaxed text-[var(--text-2)]">{body}</p>}
      {action && <div className="mt-3.5">{action}</div>}
    </div>
  );
}

export function ErrorBox({ error, hint }: { error: string; hint?: string }) {
  return (
    <div className="mb-4 rounded-md border border-[rgba(239,95,104,0.3)] bg-[var(--danger-dim)] px-3.5 py-2.5">
      <p className="text-[12.5px] font-medium text-[var(--danger)]">Request failed</p>
      <p className="mt-0.5 font-mono text-[11.5px] text-[var(--text-2)]">{error}</p>
      {hint !== "" && (
        <p className="mt-1 text-[11.5px] text-[var(--text-3)]">
          {hint ?? (
            <>
              Check the API is running: <code className="font-mono">uvicorn app.main:app --reload</code> (port 8000)
            </>
          )}
        </p>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Controls
// ─────────────────────────────────────────────────────────────────────
export function Toggle({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`flex w-full items-start gap-3 rounded-md border px-3 py-2.5 text-left transition-colors ${
        checked
          ? "border-[var(--accent-line)] bg-[var(--accent-dim)]"
          : "border-[var(--border)] bg-[var(--bg-subtle)] hover:border-[var(--border-strong)]"
      }`}
    >
      <span
        className="relative mt-[1px] inline-flex h-[15px] w-[26px] shrink-0 items-center rounded-full transition-colors"
        style={{ background: checked ? "var(--accent)" : "var(--surface-3)" }}
      >
        <span
          className="absolute h-[11px] w-[11px] rounded-full bg-white transition-all"
          style={{ left: checked ? 13 : 2 }}
        />
      </span>
      <span className="min-w-0">
        <span className="block text-[12.5px] font-medium text-[var(--text)]">{label}</span>
        {hint && <span className="mt-0.5 block text-[11.5px] leading-relaxed text-[var(--text-3)]">{hint}</span>}
      </span>
    </button>
  );
}

/**
 * Quality uplift banner.
 *
 * Two legitimate but DIFFERENT scales are shown side by side and never conflated:
 *   · live Adaption run  → platform score on a 0–10 scale, with letter grades
 *                          (returned by Adaptive Data's evaluation)
 *   · demo artifact      → InsightFlow's own 0–100 composite score
 */
export function GradeBanner({
  before, after, improvement, mode, note,
}: {
  before: number | null;
  after: number | null;
  improvement: number | null;
  mode: string | null;
  note?: string | null;
}) {
  if (after === null) {
    return (
      <div className="panel flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="text-[12.5px] font-medium">No refinery run yet</p>
          <p className="mt-0.5 text-[11.5px] text-[var(--text-2)]">
            Run the Feedback Refinery to deduplicate, normalize and adapt this dataset before analysis.
          </p>
        </div>
        <a href="/refinery" className="btn btn-primary">Run refinery</a>
      </div>
    );
  }

  // letter grades come back in the run note, e.g. "…: E → B (platform score 2.0 → 7.2 …)"
  const letters = note?.match(/([A-F][+-]?)\s*→\s*([A-F][+-]?)/);
  const isPlatformScale = Math.max(before ?? 0, after) <= 10;
  const scaleLabel = isPlatformScale ? "/10 platform score" : "/100 composite";

  return (
    <div className="panel">
      <div className="flex flex-wrap items-center gap-x-10 gap-y-4 px-4 py-3.5">
        <div>
          <p className="label">
            Data quality · {mode === "live" ? "Adaption platform evaluation" : "demo artifact"}
          </p>
          <div className="mt-1.5 flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
            {letters ? (
              <>
                <span className="text-[22px] font-semibold leading-none text-[var(--ok)]">{letters[2]}</span>
                <span className="text-[11px] text-[var(--text-3)]">grade {letters[2]}, up from {letters[1]}</span>
                <span className="mx-1 hidden h-4 w-px bg-[var(--border)] sm:inline-block" />
              </>
            ) : null}
            <span className="num text-[15px] text-[var(--text-3)] line-through decoration-[var(--danger)]/50">{before}</span>
            <span className="text-[var(--text-3)]">→</span>
            <span className="num text-[24px] font-semibold leading-none tracking-[-0.02em] text-[var(--ok)]">{after}</span>
            <span className="text-[10.5px] text-[var(--text-3)]">{scaleLabel}</span>
          </div>
        </div>

        <div>
          <p className="label">Improvement</p>
          <p className="num mt-1.5 text-[17px] font-semibold text-[var(--ok)]">+{improvement}%</p>
        </div>

        <p className="max-w-sm text-[11.5px] leading-relaxed text-[var(--text-3)]">
          {mode === "live"
            ? "Scores reported by the Adaption platform for this run — measured on the data before any insight was drawn."
            : "InsightFlow composite (uniqueness, diversity, language, clarity, metadata) computed on the demo pipeline, which mirrors the Adaption stages."}
        </p>
      </div>
    </div>
  );
}
