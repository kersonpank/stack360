import { HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { formatDateTime } from "@/components/ui/format";
import type { ObservationKeyDef, ScoreKeyDef } from "@/lib/stack360/registry";
import type { Observation, Score } from "@/lib/stack360/types";

function formatObservationValue(value: unknown, type: ObservationKeyDef["type"], enumLabels?: Record<string, string>) {
  if (value === null || value === undefined || value === "") return null;
  if (type === "enum" && typeof value === "string") return enumLabels?.[value] ?? value;
  if (type === "boolean") return value ? "Sim" : "Não";
  if (type === "date" && typeof value === "string") return formatDateTime(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function confidenceLabel(confidence: number | null) {
  if (confidence === null) return "Sem confiança informada";
  return `${Math.round(confidence * 100)}% de confiança`;
}

type CanonicalFieldProps = {
  def: ObservationKeyDef;
  observation?: Observation | null;
};

export function CanonicalField({ def, observation }: CanonicalFieldProps) {
  if (!observation) {
    return (
      <div className="brutal-border-thin border-ink/40 bg-panel/60 p-4">
        <div className="flex items-center gap-2 text-ink/60">
          <HelpCircle className="h-4 w-4 flex-none" />
          <h3 className="font-headline text-xs font-black uppercase tracking-widest">{def.label}</h3>
        </div>
        <p className="mt-2 font-headline text-lg font-black uppercase text-ink/50">Não sei</p>
        {def.expectedSourceHint ? (
          <p className="mt-1 text-xs font-semibold text-ink/50">Fonte esperada: {def.expectedSourceHint}</p>
        ) : null}
      </div>
    );
  }

  const value = formatObservationValue(observation.value, def.type, def.enumLabels);

  return (
    <div className="brutal-border-thin border-ink bg-panel p-4">
      <h3 className="font-headline text-xs font-black uppercase tracking-widest text-ink/70">{def.label}</h3>
      <p className="mt-2 font-headline text-xl font-black uppercase">{value ?? "Não sei"}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase text-ink/60">
        <Badge tone="default">{observation.data_source_key ?? "fonte desconhecida"}</Badge>
        <span>{confidenceLabel(observation.confidence)}</span>
        <span>{formatDateTime(observation.observed_at)}</span>
      </div>
    </div>
  );
}

type CanonicalScoreFieldProps = {
  def: ScoreKeyDef;
  score?: Score | null;
};

export function CanonicalScoreField({ def, score }: CanonicalScoreFieldProps) {
  if (!score) {
    return (
      <div className="brutal-border-thin border-ink/40 bg-panel/60 p-4">
        <div className="flex items-center gap-2 text-ink/60">
          <HelpCircle className="h-4 w-4 flex-none" />
          <h3 className="font-headline text-xs font-black uppercase tracking-widest">{def.label}</h3>
        </div>
        <p className="mt-2 font-headline text-lg font-black uppercase text-ink/50">Não sei</p>
      </div>
    );
  }

  const bandLabel = score.score_band ? def.bandLabels?.[score.score_band] ?? score.score_band : null;
  const bandTone = score.score_band ? def.bandTone?.[score.score_band] ?? "default" : "default";

  return (
    <div className="brutal-border-thin border-ink bg-panel p-4">
      <h3 className="font-headline text-xs font-black uppercase tracking-widest text-ink/70">{def.label}</h3>
      <p className="mt-2 font-headline text-xl font-black uppercase">{score.score_value}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase text-ink/60">
        {bandLabel ? <Badge tone={bandTone}>{bandLabel}</Badge> : null}
        <Badge tone="default">{score.data_source_key ?? "fonte desconhecida"}</Badge>
        <span>{formatDateTime(score.calculated_at)}</span>
      </div>
    </div>
  );
}
