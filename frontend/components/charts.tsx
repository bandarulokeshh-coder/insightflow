"use client";

import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

/**
 * Charts use a muted, product-grade palette:
 *   one accent for volume, status colors only where they mean something.
 */
export const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#3ecf8e",
  neutral: "#7d8894",
  negative: "#ef5f68",
};

const GRID = "#1c2229";
const AXIS_TICK = { fill: "#6a7481", fontSize: 11 };

const TOOLTIP = {
  background: "#12161b",
  border: "1px solid #2e3742",
  borderRadius: 6,
  fontSize: 12,
  color: "#e7e9ec",
  boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
  padding: "7px 10px",
};

const LEGEND = { fontSize: 11.5, color: "#9aa4b0", paddingTop: 6 };

export function SentimentDonut({ data }: { data: { name: string; value: number }[] }) {
  const total = data.reduce((a, b) => a + b.value, 0) || 1;
  return (
    <div className="relative h-[218px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={54}
            outerRadius={78}
            paddingAngle={2}
            strokeWidth={0}
          >
            {data.map((d) => (
              <Cell key={d.name} fill={SENTIMENT_COLORS[d.name] || "#7d8894"} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={TOOLTIP}
            formatter={(value, name) => {
              const v = typeof value === "number" ? value : Number(value ?? 0);
              return [`${v}  (${Math.round((v / total) * 100)}%)`, String(name ?? "")];
            }}
          />
          <Legend iconType="circle" iconSize={7} wrapperStyle={LEGEND} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 grid place-items-center pb-8">
        <div className="text-center">
          <p className="num text-[19px] font-semibold leading-none tracking-[-0.02em]">{total.toLocaleString()}</p>
          <p className="label mt-1">items</p>
        </div>
      </div>
    </div>
  );
}

export function TrendChart({ data }: { data: { month: string; positive: number; neutral: number; negative: number }[] }) {
  return (
    <div className="h-[240px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="month" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: GRID }} dy={4} />
          <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} width={44} />
          <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: "#9aa4b0", marginBottom: 4 }} cursor={{ stroke: "#2e3742" }} />
          <Legend iconType="plainline" iconSize={12} wrapperStyle={LEGEND} />
          <Line type="monotone" dataKey="negative" stroke={SENTIMENT_COLORS.negative} strokeWidth={1.75} dot={false} activeDot={{ r: 3 }} />
          <Line type="monotone" dataKey="positive" stroke={SENTIMENT_COLORS.positive} strokeWidth={1.75} dot={false} activeDot={{ r: 3 }} />
          <Line type="monotone" dataKey="neutral" stroke={SENTIMENT_COLORS.neutral} strokeWidth={1.25} dot={false} strokeDasharray="3 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TopicBars({ data }: { data: { topic: string; total: number; negative: number }[] }) {
  const rows = data.slice(0, 8);
  return (
    <div className="h-[276px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 14, left: 26, bottom: 0 }} barGap={1}>
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis type="number" tick={AXIS_TICK} tickLine={false} axisLine={false} />
          <YAxis
            type="category"
            dataKey="topic"
            tick={{ ...AXIS_TICK, fontSize: 11.5 }}
            tickLine={false}
            axisLine={false}
            width={108}
          />
          <Tooltip contentStyle={TOOLTIP} cursor={{ fill: "rgba(255,255,255,0.025)" }} />
          <Legend iconType="circle" iconSize={7} wrapperStyle={LEGEND} />
          <Bar dataKey="total" name="total" fill="#39414d" radius={[0, 2, 2, 0]} barSize={8} />
          <Bar dataKey="negative" name="negative" fill={SENTIMENT_COLORS.negative} radius={[0, 2, 2, 0]} barSize={8} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
