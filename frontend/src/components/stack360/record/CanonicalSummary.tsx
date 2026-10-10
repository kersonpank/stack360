import { CanonicalField, CanonicalScoreField } from "@/components/stack360/ui/CanonicalField";
import { getObservationKeyDef, getScoreKeyDef } from "@/lib/stack360/registry";
import type { Observation, Score } from "@/lib/stack360/types";

type CanonicalSummaryProps = {
  observationKeys: string[];
  scoreKeys: string[];
  observations: Observation[];
  scores: Score[];
};

export function CanonicalSummary({ observationKeys, scoreKeys, observations, scores }: CanonicalSummaryProps) {
  const observationByKey = new Map(observations.map((o) => [o.key, o]));
  const scoreByKey = new Map(scores.map((s) => [s.score_key, s]));

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {observationKeys.map((key) => (
        <CanonicalField key={key} def={getObservationKeyDef(key)} observation={observationByKey.get(key)} />
      ))}
      {scoreKeys.map((key) => (
        <CanonicalScoreField key={key} def={getScoreKeyDef(key)} score={scoreByKey.get(key)} />
      ))}
    </div>
  );
}
