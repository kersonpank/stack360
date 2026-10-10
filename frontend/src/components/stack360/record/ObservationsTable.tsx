import { BrutalCard } from "@/components/ui/BrutalCard";
import { Badge } from "@/components/ui/Badge";
import { formatDateTime } from "@/components/ui/format";
import { getObservationKeyDef } from "@/lib/stack360/registry";
import type { Observation } from "@/lib/stack360/types";

export function ObservationsTable({ observations }: { observations: Observation[] }) {
  if (observations.length === 0) {
    return (
      <BrutalCard>
        <p className="font-headline text-sm font-black uppercase text-ink/60">Nenhuma observation registrada.</p>
      </BrutalCard>
    );
  }

  const groups = new Map<string, Observation[]>();
  for (const obs of observations) {
    const group = getObservationKeyDef(obs.key).group;
    groups.set(group, [...(groups.get(group) ?? []), obs]);
  }

  return (
    <div className="flex flex-col gap-5">
      {[...groups.entries()].map(([group, items]) => (
        <BrutalCard key={group}>
          <h3 className="mb-3 border-b-2 border-ink/20 pb-2 font-headline text-sm font-black uppercase tracking-widest text-ink/70">
            {group}
          </h3>
          <div className="flex flex-col divide-y-2 divide-ink/10">
            {items.map((obs) => {
              const def = getObservationKeyDef(obs.key);
              return (
                <div key={obs.key} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <div>
                    <span className="font-headline text-sm font-black uppercase">{def.label}</span>
                    <span className="ml-2 text-xs font-semibold text-ink/50">
                      {typeof obs.value === "object" ? JSON.stringify(obs.value) : String(obs.value)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-ink/60">
                    <Badge tone="default">{obs.data_source_key ?? "fonte desconhecida"}</Badge>
                    <span>{obs.confidence !== null ? `${Math.round(obs.confidence * 100)}%` : "sem confiança"}</span>
                    <span>{formatDateTime(obs.observed_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </BrutalCard>
      ))}
    </div>
  );
}
