import type { ScoreKeyDef } from "./types";

// `score.score_key` é livre no backend — mesma lógica do registro de observations.
export const SCORE_KEYS: Record<string, ScoreKeyDef> = {
  opportunity: {
    key: "opportunity",
    label: "Score de oportunidade",
    type: "number",
    bandLabels: { low: "Baixo", medium: "Médio", high: "Alto" },
    bandTone: { low: "default", medium: "yellow", high: "red" },
  },
  risk: {
    key: "risk",
    label: "Score de risco",
    type: "number",
    bandLabels: { low: "Baixo", medium: "Médio", high: "Alto" },
    bandTone: { low: "default", medium: "yellow", high: "red" },
  },
};

export const PRIORITY_SCORE_KEYS: string[] = ["opportunity", "risk"];

export function getScoreKeyDef(key: string): ScoreKeyDef {
  return (
    SCORE_KEYS[key] ?? {
      key,
      label: key,
      type: "number",
    }
  );
}
