"use client";

import { useEffect, useState } from "react";
import { RadioTower } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { SourcesHealthTable } from "@/components/stack360/sources/SourcesHealthTable";
import { getSourcesHealth } from "@/lib/stack360/api";
import type { SourceHealth } from "@/lib/stack360/types";

export default function SourcesPage() {
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

  if (loading) return <LoadingState label="Carregando fontes..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!sources) return null;

  return (
    <div>
      <div className="mb-6 border-b-[4px] border-ink pb-4">
        <p className="flex items-center gap-2 font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
          <RadioTower className="h-4 w-4" /> Fontes e saúde
        </p>
        <h1 className="mt-2 font-headline text-5xl font-black uppercase tracking-tight sm:text-6xl">Fontes</h1>
      </div>
      <SourcesHealthTable sources={sources} />
    </div>
  );
}
