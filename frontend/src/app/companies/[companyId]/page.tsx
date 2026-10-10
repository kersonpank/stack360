"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Building2 } from "lucide-react";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { CanonicalSummary } from "@/components/stack360/record/CanonicalSummary";
import { ObservationsTable } from "@/components/stack360/record/ObservationsTable";
import { ScoresTable } from "@/components/stack360/record/ScoresTable";
import { InteractionsList } from "@/components/stack360/record/InteractionsList";
import { CompanyPeopleList } from "@/components/stack360/record/RelationshipsList";
import { FutureHooksNotice } from "@/components/stack360/record/FutureHooksNotice";
import { getCompanyContext } from "@/lib/stack360/api";
import { PRIORITY_COMPANY_OBSERVATION_KEYS } from "@/lib/stack360/registry/observationKeys";
import { PRIORITY_SCORE_KEYS } from "@/lib/stack360/registry/scoreKeys";
import type { CompanyContext } from "@/lib/stack360/types";

export default function CompanyDetailPage() {
  const params = useParams<{ companyId: string }>();
  const companyId = params.companyId;
  const [context, setContext] = useState<CompanyContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setContext(await getCompanyContext(companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao carregar ficha.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  if (loading) return <LoadingState label="Carregando ficha..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!context) return null;

  const observations = context.observations ?? [];
  const scores = context.scores ?? [];

  return (
    <div>
      <Link href="/companies" className="mb-4 inline-flex items-center gap-2 font-headline text-xs font-black uppercase tracking-widest text-ink/60 hover:text-ink">
        <ArrowLeft className="h-4 w-4" /> Voltar pra empresas
      </Link>

      <div className="mb-6 border-b-[4px] border-ink pb-4">
        <p className="flex items-center gap-2 font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
          <Building2 className="h-4 w-4" /> Ficha canônica
        </p>
        <h1 className="mt-2 font-headline text-4xl font-black uppercase tracking-tight sm:text-5xl">
          {context.company.canonical_name}
        </h1>
        <p className="mt-1 text-xs font-bold uppercase text-ink/50">
          {context.company.domain ?? "Sem domínio"} · {context.company.cnpj_normalized ?? "CNPJ não informado"}
        </p>
      </div>

      <section className="mb-7">
        <h2 className="mb-3 font-headline text-xl font-black uppercase">Chaves canônicas</h2>
        <CanonicalSummary
          observationKeys={PRIORITY_COMPANY_OBSERVATION_KEYS}
          scoreKeys={PRIORITY_SCORE_KEYS}
          observations={observations}
          scores={scores}
        />
      </section>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <section className="flex flex-col gap-5">
          <CompanyPeopleList links={context.people ?? []} />
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
