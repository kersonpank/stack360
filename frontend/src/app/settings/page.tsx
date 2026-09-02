"use client";

import { useState } from "react";
import { Activity, DatabaseZap } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { Button } from "@/components/ui/Button";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { API_BASE_URL, USE_MOCKS, getHealth, getNormalizationStatus } from "@/lib/api";

type TestResult = {
  name: string;
  data: unknown;
};

export default function SettingsPage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TestResult | null>(null);

  async function run(name: string, action: () => Promise<unknown>) {
    setLoading(name);
    setError(null);
    setResult(null);
    try {
      setResult({ name, data: await action() });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido no teste de API.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="max-w-5xl">
      <div className="mb-6 border-b-[4px] border-ink pb-5">
        <p className="font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">Debug</p>
        <h1 className="mt-2 font-headline text-5xl font-black uppercase tracking-tight">Settings</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <BrutalCard>
          <h2 className="mb-4 font-headline text-2xl font-black uppercase">Runtime</h2>
          <div className="space-y-4">
            <ConfigRow label="API_BASE_URL" value={API_BASE_URL} />
            <ConfigRow label="USE_MOCKS" value={String(USE_MOCKS)} />
            <div className="flex flex-wrap gap-2">
              <Badge tone={USE_MOCKS ? "yellow" : "blue"}>{USE_MOCKS ? "Mock mode" : "API real"}</Badge>
              <Badge>Sem credenciais</Badge>
            </div>
          </div>
        </BrutalCard>

        <BrutalCard className="bg-yellow">
          <h2 className="mb-4 font-headline text-2xl font-black uppercase">API checks</h2>
          <div className="flex flex-wrap gap-3">
            <Button type="button" variant="dark" onClick={() => void run("GET /health", getHealth)}>
              <Activity className="h-4 w-4" />
              Testar health
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void run("GET /system/normalization-status", getNormalizationStatus)}
            >
              <DatabaseZap className="h-4 w-4" />
              Testar status
            </Button>
          </div>
        </BrutalCard>
      </div>

      <div className="mt-7">
        {loading ? <LoadingState label={`Executando ${loading}...`} /> : null}
        {error ? <ErrorState message={error} /> : null}
        {result ? (
          <BrutalCard>
            <h2 className="mb-3 font-headline text-xl font-black uppercase">{result.name}</h2>
            <pre className="brutal-border-thin max-h-[520px] overflow-auto bg-ink p-4 text-sm font-bold text-yellow">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          </BrutalCard>
        ) : null}
      </div>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="brutal-border-thin bg-muted p-3">
      <div className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">{label}</div>
      <div className="mt-1 break-all font-bold">{value}</div>
    </div>
  );
}
