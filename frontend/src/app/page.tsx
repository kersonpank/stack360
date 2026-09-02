"use client";

import { useEffect, useState } from "react";
import { Database, MessageSquareText, RadioTower, Rows3, Users, Workflow } from "lucide-react";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatNumber, percentLabel } from "@/components/ui/format";
import { getNormalizationStatus } from "@/lib/api";
import type { UiNormalizationStatus } from "@/lib/types";

export default function DashboardPage() {
  const [status, setStatus] = useState<UiNormalizationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setStatus(await getNormalizationStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao consultar normalization-status.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <LoadingState label="Carregando normalization-status..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!status) return null;

  return (
    <div className="grid grid-cols-1 gap-7 xl:grid-cols-12">
      <section className="xl:col-span-8">
        <div className="mb-6 border-b-[4px] border-ink pb-4">
          <p className="font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
            Real-time normalization
          </p>
          <h1 className="mt-2 font-headline text-5xl font-black uppercase tracking-tight sm:text-6xl">
            Intelligence 360
          </h1>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <KpiCard label={"Total\nRAW"} value={status.totalRaw} icon={Database} footer="Base capturada" />
          <KpiCard
            label={"RAW\nnormalizado"}
            value={status.totalRawNormalized}
            icon={Workflow}
            tone="yellow"
            footer="Pronto para leitura"
          />
          <KpiCard
            label={"RAW\npendente"}
            value={status.totalRawPending}
            icon={Rows3}
            tone="red"
            footer="Exige normalização"
          />
          <KpiCard
            label={"Stakeholders\nidentificados"}
            value={status.totalContacts}
            icon={Users}
            footer="Contatos consolidados"
          />
          <KpiCard
            label={"Conversas"}
            value={status.totalConversations}
            icon={RadioTower}
            footer="Threads normalizadas"
          />
          <KpiCard
            label={"Mensagens"}
            value={status.totalMessages}
            icon={MessageSquareText}
            tone="dark"
            footer="Volume operacional"
          />
        </div>
      </section>

      <aside className="xl:col-span-4">
        <BrutalCard className="bg-ink text-white">
          <h2 className="border-b-2 border-white/30 pb-4 font-headline text-3xl font-black uppercase">
            Progresso por instância
          </h2>
          <div className="mt-5 space-y-4">
            {status.bySourceAccount.map((source) => (
              <div key={source.id} className="brutal-border-thin border-white bg-paper p-4 text-ink">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-headline text-lg font-black uppercase">{source.instanceName}</h3>
                    <p className="text-xs font-bold uppercase text-ink/65">ID: {source.id}</p>
                  </div>
                  <span className="brutal-border-thin bg-yellow px-2 py-1 font-headline text-sm font-black">
                    {percentLabel(source.normalizedPercent)}
                  </span>
                </div>
                <div className="mt-4 h-5 border-2 border-ink bg-panel">
                  <div
                    className="h-full border-r-2 border-ink bg-yellow"
                    style={{ width: percentLabel(source.normalizedPercent) }}
                  />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center font-headline text-xs font-black uppercase">
                  <div className="border-2 border-ink bg-panel p-2">
                    {formatNumber(source.totalRaw)}
                    <span className="block text-[10px] text-ink/60">raw</span>
                  </div>
                  <div className="border-2 border-ink bg-panel p-2">
                    {formatNumber(source.normalized)}
                    <span className="block text-[10px] text-ink/60">norm</span>
                  </div>
                  <div className="border-2 border-ink bg-panel p-2">
                    {formatNumber(source.pending)}
                    <span className="block text-[10px] text-ink/60">pend</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </BrutalCard>
      </aside>
    </div>
  );
}
