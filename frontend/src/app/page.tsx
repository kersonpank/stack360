"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, RadioTower, XCircle } from "lucide-react";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { SourcesHealthTable } from "@/components/stack360/sources/SourcesHealthTable";
import { getSourcesHealth } from "@/lib/stack360/api";
import type { SourceHealth } from "@/lib/stack360/types";

export default function DashboardPage() {
  const [sources, setSources] = useState<SourceHealth[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setSources(await getSourcesHealth());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao consultar fontes.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <LoadingState label="Carregando Stack360..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!sources) return null;

  const feeding = sources.filter((s) => s.feeding).length;
  const withErrors = sources.filter((s) => s.failed_24h > 0).length;

  return (
    <div>
      <div className="mb-6 border-b-[4px] border-ink pb-4">
        <p className="font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">Stack360</p>
        <h1 className="mt-2 font-headline text-5xl font-black uppercase tracking-tight sm:text-6xl">
          Coração de dados
        </h1>
      </div>

      <div className="mb-7 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <KpiCard label="Fontes" value={sources.length} icon={RadioTower} footer="Cadastradas no workspace" />
        <KpiCard
          label={"Alimentando\nagora"}
          value={feeding}
          icon={CheckCircle2}
          tone="yellow"
          footer="Com evento nas últimas 24h"
        />
        <KpiCard
          label={"Com erro\nnas 24h"}
          value={withErrors}
          icon={XCircle}
          tone={withErrors > 0 ? "red" : "paper"}
          footer="Verificar em Fontes"
        />
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-headline text-xl font-black uppercase">Fontes</h2>
        <Link
          href="/sources"
          className="flex items-center gap-1 font-headline text-xs font-black uppercase tracking-widest text-blue hover:underline"
        >
          Ver todas <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <SourcesHealthTable sources={sources.slice(0, 3)} />

      <div className="mt-7 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <BrutalCard className="bg-panel/60">
          <h3 className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">Em breve</h3>
          <p className="mt-2 text-xs font-semibold text-ink/60">
            Fila de resolução — fica disponível quando o endpoint de recomendação for exposto via REST.
          </p>
        </BrutalCard>
        <BrutalCard className="bg-panel/60">
          <h3 className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">Em breve</h3>
          <p className="mt-2 text-xs font-semibold text-ink/60">
            Política de contato (opt-out) — exige migration nova, ainda não implementada.
          </p>
        </BrutalCard>
      </div>
    </div>
  );
}
