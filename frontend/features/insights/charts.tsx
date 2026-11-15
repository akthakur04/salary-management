"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatCompactMoney, formatMoney } from "@/lib/format";
import type { BandGroup, PayBucket, PayGroup } from "@/lib/types";

/** Recharts via shadcn charts, themed with the design tokens. Each chart also has a data table for screen readers. */

const mixConfig = {
  fixed: { label: "Fixed (base + allowances)", color: "var(--primary)" },
  variable: { label: "Variable (bonus + commission)", color: "var(--primary-soft)" },
} satisfies ChartConfig;

export function MixChart({ groups }: { groups: PayGroup[] }) {
  const data = groups.map((group) => {
    const variable = Number(group.variable_share_percent ?? 0);
    return { name: group.label, fixed: Math.round((100 - variable) * 10) / 10, variable };
  });
  return (
    <>
      <ChartContainer config={mixConfig} className="aspect-auto w-full" style={{ height: 44 * data.length + 48 }} aria-hidden="true">
        <BarChart data={data} layout="vertical" stackOffset="expand" margin={{ left: 8, right: 8 }}>
          <XAxis type="number" hide domain={[0, 1]} />
          <YAxis type="category" dataKey="name" width={130} tickLine={false} axisLine={false} />
          <ChartTooltip content={<ChartTooltipContent formatter={(value, name) => `${mixConfig[name as keyof typeof mixConfig].label}: ${value}%`} />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="fixed" stackId="mix" fill="var(--color-fixed)" radius={[4, 0, 0, 4]} />
          <Bar dataKey="variable" stackId="mix" fill="var(--color-variable)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ChartContainer>
      <table className="sr-only">
        <caption>Share of total target pay that is variable, by group</caption>
        <tbody>
          {data.map((row) => (
            <tr key={row.name}>
              <th scope="row">{row.name}</th>
              <td>{row.variable}% variable</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

const bandConfig = {
  below: { label: "Below band", color: "var(--amber)" },
  in_band: { label: "In band", color: "var(--sage)" },
  above: { label: "Above band", color: "var(--violet)" },
} satisfies ChartConfig;

export function BandChart({ groups }: { groups: BandGroup[] }) {
  return (
    <>
      <ChartContainer config={bandConfig} className="aspect-auto w-full" style={{ height: 44 * groups.length + 48 }} aria-hidden="true">
        <BarChart data={groups} layout="vertical" stackOffset="expand" margin={{ left: 8, right: 8 }}>
          <XAxis type="number" hide domain={[0, 1]} />
          <YAxis type="category" dataKey="label" width={130} tickLine={false} axisLine={false} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="below" stackId="band" fill="var(--color-below)" radius={[4, 0, 0, 4]} />
          <Bar dataKey="in_band" stackId="band" fill="var(--color-in_band)" />
          <Bar dataKey="above" stackId="band" fill="var(--color-above)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ChartContainer>
      <table className="sr-only">
        <caption>Employees against their pay band, by group</caption>
        <thead>
          <tr>
            <th scope="col">Group</th>
            <th scope="col">Below band</th>
            <th scope="col">In band</th>
            <th scope="col">Above band</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <tr key={group.key}>
              <th scope="row">{group.label}</th>
              <td>{group.below}</td>
              <td>{group.in_band}</td>
              <td>{group.above}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

const histogramConfig = {
  count: { label: "People", color: "var(--primary)" },
} satisfies ChartConfig;

function people(count: number): string {
  return `${count.toLocaleString("en-US")} ${count === 1 ? "person" : "people"}`;
}

function bracket(bucket: PayBucket): string {
  return `${formatMoney(bucket.lower)} to under ${formatMoney(bucket.upper)}`;
}

export function PayHistogram({ buckets }: { buckets: PayBucket[] }) {
  const data = buckets.map((bucket) => ({
    name: formatCompactMoney(bucket.lower, 0),
    range: bracket(bucket),
    count: bucket.count,
  }));
  return (
    <>
      <ChartContainer config={histogramConfig} className="aspect-auto h-64 w-full" aria-hidden="true">
        <BarChart data={data} barCategoryGap={2} margin={{ left: 0, right: 8, top: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="name" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={12} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={44} />
          <ChartTooltip
            cursor={{ fill: "var(--muted)" }}
            content={
              <ChartTooltipContent
                labelFormatter={(_, items) => items[0]?.payload.range}
                formatter={(value) => people(Number(value))}
              />
            }
          />
          <Bar dataKey="count" fill="var(--color-count)" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ChartContainer>
      <table className="sr-only">
        <caption>Number of people by total target pay</caption>
        <tbody>
          {data.map((row) => (
            <tr key={row.range}>
              <th scope="row">{row.range}</th>
              <td>{people(row.count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
