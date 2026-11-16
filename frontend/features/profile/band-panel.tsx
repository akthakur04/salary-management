import { BandGauge } from "@/components/band-gauge";
import { BandStatus } from "@/components/band-status";
import { Panel } from "@/components/page-heading";
import { formatMoney } from "@/lib/format";
import type { EmployeeProfile } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-background p-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="amount text-base">{value}</span>
    </div>
  );
}

function bandSentence(profile: EmployeeProfile): string | null {
  const band = profile.band;
  if (!band?.band) return null;
  const firstName = profile.name.split(" ")[0];
  const base = band.fte_equivalent_base;
  const mid = band.band.midpoint;
  const gap = { amount_minor: Math.abs(base.amount_minor - mid.amount_minor), currency: mid.currency };
  const side = base.amount_minor < mid.amount_minor ? "below" : "above";
  const where = {
    below: `below band, ${formatMoney(band.gap_to_minimum ?? gap)} short of the minimum`,
    above: "above band",
    in_band: "in band",
    no_band: "not banded",
  }[band.position];
  const fte = profile.employment_type === "part_time" ? " Compared at full-time equivalent." : "";
  return `${firstName} is ${where}, ${formatMoney(gap)} ${side} the midpoint.${fte}`;
}

export function BandPanel({ profile }: { profile: EmployeeProfile }) {
  const band = profile.band;
  const roleLabel = profile.role
    ? `${profile.role.title} L${profile.role.level}${profile.country ? ` · ${profile.country.name}` : ""}`
    : "";

  return (
    <Panel title="Pay band" id="band" aside={roleLabel}>
      {profile.employment_type === "contractor" ? (
        <p className="text-sm text-subtle-foreground">
          Contractors aren&apos;t banded, so there&apos;s no compa-ratio. Their pay still counts in
          cost figures.
        </p>
      ) : !band?.band ? (
        <p className="text-sm text-subtle-foreground">
          There&apos;s no pay band for this role in this country yet.
        </p>
      ) : (
        <>
          <div className="flex items-baseline gap-3">
            <span className="amount text-4xl font-medium tracking-tight">{band.compa_ratio}</span>
            <BandStatus band={{ ...band, compa_ratio: null }} />
          </div>
          <p className="text-sm leading-normal text-subtle-foreground">
            Compa-ratio: base salary ÷ band midpoint. {bandSentence(profile)}
          </p>
          <BandGauge band={band.band} value={band.fte_equivalent_base} position={band.position} />
        </>
      )}
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Peers in role & country" value={profile.peers.count.toLocaleString("en-US")} />
        <Stat
          label="Peer median base"
          value={profile.peers.median_base ? formatMoney(profile.peers.median_base) : "—"}
        />
      </div>
    </Panel>
  );
}
