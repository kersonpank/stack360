"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Users } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatDateTime } from "@/components/ui/format";
import { CanonicalSummary } from "@/components/stack360/record/CanonicalSummary";
import { ObservationsTable } from "@/components/stack360/record/ObservationsTable";
import { ScoresTable } from "@/components/stack360/record/ScoresTable";
import { InteractionsList } from "@/components/stack360/record/InteractionsList";
import { PersonCompaniesList } from "@/components/stack360/record/RelationshipsList";
import { FutureHooksNotice } from "@/components/stack360/record/FutureHooksNotice";
import { getPersonContext } from "@/lib/stack360/api";
import { PRIORITY_PERSON_OBSERVATION_KEYS } from "@/lib/stack360/registry/observationKeys";
import { PRIORITY_SCORE_KEYS } from "@/lib/stack360/registry/scoreKeys";
import type { PersonContext } from "@/lib/stack360/types";

export default function PersonDetailPage() {
  const params = useParams<{ personId: string }>();
  const personId = params.personId;
  const [context, setContext] = useState<PersonContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setContext(await getPersonContext(personId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao carregar ficha.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personId]);

  if (loading) return <LoadingState label="Carregando ficha..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!context) return null;

  const observations = context.observations ?? [];
  const scores = context.scores ?? [];

  return (
    <div>
      <Link href="/people" className="mb-4 inline-flex items-center gap-2 font-headline text-xs font-black uppercase tracking-widest text-ink/60 hover:text-ink">
        <ArrowLeft className="h-4 w-4" /> Voltar pra pessoas
      </Link>

      <div className="mb-6 border-b-[4px] border-ink pb-4">
        <p className="flex items-center gap-2 font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
          <Users className="h-4 w-4" /> Ficha canônica
        </p>
        <h1 className="mt-2 font-headline text-4xl font-black uppercase tracking-tight sm:text-5xl">
          {context.person.canonical_name}
        </h1>
        <p className="mt-1 text-xs font-bold uppercase text-ink/50">
          Criado em {formatDateTime(context.person.created_at)}
        </p>
      </div>

      <section className="mb-7">
        <h2 className="mb-3 font-headline text-xl font-black uppercase">Chaves canônicas</h2>
        <CanonicalSummary
          observationKeys={PRIORITY_PERSON_OBSERVATION_KEYS}
          scoreKeys={PRIORITY_SCORE_KEYS}
          observations={observations}
          scores={scores}
        />
      </section>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <section className="flex flex-col gap-5">
          {context.identities && context.identities.length > 0 ? (
            <BrutalCard>
              <h3 className="mb-3 border-b-2 border-ink/20 pb-2 font-headline text-sm font-black uppercase tracking-widest text-ink/70">
                Identidades
              </h3>
              <div className="flex flex-col divide-y-2 divide-ink/10">
                {context.identities.map((identity, index) => (
                  <div key={index} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <div>
                      <span className="font-headline text-sm font-black uppercase">{identity.identity_type}</span>
                      <span className="ml-2 text-xs font-semibold text-ink/60">{identity.value_normalized}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-ink/60">
                      {identity.is_verified ? <Badge tone="yellow">Verificado</Badge> : null}
                      <Badge tone="default">{identity.data_source_key ?? "fonte desconhecida"}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            </BrutalCard>
          ) : null}

          <PersonCompaniesList links={context.companies ?? []} />
          <InteractionsList interactions={context.recent_interactions ?? []} />
          <FutureHooksNotice />
        </section>

        <section className="flex flex-col gap-5">
          <ObservationsTable observations={observations} />
          <ScoresTable scores={scores} />
        </section>
      </div>
    </div>
  );
}
