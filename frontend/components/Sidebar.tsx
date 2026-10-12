"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type NavItem = { href: string; label: string; icon: string };

const SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Analyze",
    items: [
      { href: "/", label: "Dashboard", icon: "M3 3h7v7H3zM14 3h7v4h-7zM14 10h7v11h-7zM3 13h7v8H3z" },
      { href: "/feedback", label: "Feedback", icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" },
    ],
  },
  {
    title: "Adaption",
    items: [
      { href: "/refinery", label: "Feedback Refinery", icon: "M4 4h16L14 12v6l-4 2v-8z" },
    ],
  },
  {
    title: "Act",
    items: [
      { href: "/recommendations", label: "Recommendations", icon: "M12 2v4m0 12v4M4.9 4.9l2.8 2.8m8.6 8.6 2.8 2.8M2 12h4m12 0h4M4.9 19.1l2.8-2.8m8.6-8.6 2.8-2.8" },
      { href: "/issues", label: "Issues", icon: "M9 11l3 3 8-8M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" },
      { href: "/reports", label: "Reports", icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 13h6M9 17h6" },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [mode, setMode] = useState<"live" | "demo" | null>(null);

  useEffect(() => {
    api.refineryStatus().then((s) => setMode(s.mode)).catch(() => setMode(null));
  }, [pathname]);

  return (
    <aside className="shrink-0 border-b border-[var(--border)] bg-[var(--bg-subtle)] lg:w-[222px] lg:border-b-0 lg:border-r">
      {/* brand */}
      <div className="flex h-[52px] items-center gap-2.5 border-b border-[var(--border)] px-4">
        <span className="grid h-6 w-6 place-items-center rounded-[5px] bg-[var(--accent)]">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 17l5-7 4 4 5-8" />
          </svg>
        </span>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold leading-tight tracking-[-0.01em]">InsightFlow</p>
          <p className="truncate text-[10.5px] leading-tight text-[var(--text-3)]">Customer feedback platform</p>
        </div>
      </div>

      {/* nav */}
      <nav className="flex gap-1 overflow-x-auto px-3 py-3 lg:flex-col lg:gap-0 lg:overflow-visible lg:px-2.5 lg:py-4">
        {SECTIONS.map((section) => (
          <div key={section.title} className="lg:mb-5">
            <p className="label mb-1.5 hidden px-2 lg:block">{section.title}</p>
            <div className="flex gap-1 lg:flex-col lg:gap-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-2.5 rounded-[5px] px-2 py-[7px] text-[12.5px] transition-colors ${
                      active
                        ? "bg-[var(--surface-3)] font-medium text-[var(--text)]"
                        : "text-[var(--text-2)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                    }`}
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={active ? "text-[var(--accent)]" : "text-[var(--text-3)]"}
                    >
                      <path d={item.icon} />
                    </svg>
                    <span className="whitespace-nowrap">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* status footer */}
      {mode && (
        <div className="mt-auto hidden border-t border-[var(--border)] px-4 py-3 lg:block">
          <p className="label mb-1.5">Refinery mode</p>
          <p className="flex items-center gap-1.5 text-[11.5px] text-[var(--text-2)]">
            <span
              className="dot"
              style={{ background: mode === "live" ? "var(--ok)" : "var(--warn)" }}
            />
            {mode === "live" ? "Live · Adaption API" : "Demo artifact"}
          </p>
        </div>
      )}
    </aside>
  );
}
