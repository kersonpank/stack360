import { BrutalCard } from "@/components/ui/BrutalCard";
import { Badge } from "@/components/ui/Badge";
import { formatDateTime } from "@/components/ui/format";
import type { Interaction } from "@/lib/stack360/types";

export function InteractionsList({ interactions }: { interactions: Interaction[] }) {
  if (interactions.length === 0) {
    return (
      <BrutalCard>
        <p className="font-headline text-sm font-black uppercase text-ink/60">Nenhuma interação recente.</p>
      </BrutalCard>
    );
  }

  return (
    <BrutalCard>
      <h3 className="mb-3 border-b-2 border-ink/20 pb-2 font-headline text-sm font-black uppercase tracking-widest text-ink/70">
        Interações recentes
      </h3>
      <div className="flex flex-col gap-3">
        {interactions.map((interaction, index) => (
          <div key={index} className="brutal-border-thin border-ink/30 bg-panel/60 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge tone="blue">{interaction.interaction_type}</Badge>
                {interaction.channel ? <Badge tone="default">{interaction.channel}</Badge> : null}
                {interaction.direction ? <Badge tone="default">{interaction.direction}</Badge> : null}
              </div>
              <span className="text-[11px] font-bold uppercase text-ink/60">
                {formatDateTime(interaction.occurred_at)} · {interaction.data_source_key ?? "fonte desconhecida"}
              </span>
            </div>
            {interaction.metadata ? (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs font-bold uppercase text-ink/50">metadata</summary>
                <pre className="mt-1 overflow-x-auto text-xs text-ink/70">
                  {JSON.stringify(interaction.metadata, null, 2)}
                </pre>
              </details>
            ) : null}
          </div>
        ))}
      </div>
    </BrutalCard>
  );
}
