import { BrutalCard } from "@/components/ui/BrutalCard";
import { Badge } from "@/components/ui/Badge";
import { formatDateTime } from "@/components/ui/format";
import { getScoreKeyDef } from "@/lib/stack360/registry";
import type { Score } from "@/lib/stack360/types";

export function ScoresTable({ scores }: { scores: Score[] }) {
  if (scores.length === 0) {
    return (
      <BrutalCard>
        <p className="font-headline text-sm font-black uppercase text-ink/60">Nenhum score registrado.</p>
      </BrutalCard>
    );
  }

  return (
    <BrutalCard>
      <h3 className="mb-3 border-b-2 border-ink/20 pb-2 font-headline text-sm font-black uppercase tracking-widest text-ink/70">
        Scores
      </h3>
      <div className="flex flex-col divide-y-2 divide-ink/10">
        {scores.map((score) => {
          const def = getScoreKeyDef(score.score_key);
          const bandLabel = score.score_band ? def.bandLabels?.[score.score_band] ?? score.score_band : null;
          const bandTone = score.score_band ? def.bandTone?.[score.score_band] ?? "default" : "default";
          return (
            <div key={score.score_key} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div>
                <span className="font-headline text-sm font-black uppercase">{def.label}</span>
                <span className="ml-2 font-headline text-base font-black">{score.score_value}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-ink/60">
                {bandLabel ? <Badge tone={bandTone}>{bandLabel}</Badge> : null}
                <Badge tone="default">{score.data_source_key ?? "fonte desconhecida"}</Badge>
                <span>{formatDateTime(score.calculated_at)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </BrutalCard>
  );
}
