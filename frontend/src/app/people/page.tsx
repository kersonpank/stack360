"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users } from "lucide-react";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatDateTime } from "@/components/ui/format";
import { listPeople } from "@/lib/stack360/api";
import type { PersonSummary } from "@/lib/stack360/types";

export default function PeoplePage() {
  const [query, setQuery] = useState("");
  const [people, setPeople] = useState<PersonSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(q: string) {
    setLoading(true);
    setError(null);
    try {
      setPeople(await listPeople({ query: q }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao buscar pessoas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load("");
  }, []);

  return (
    <div>
      <div className="mb-6 border-b-[4px] border-ink pb-4">
        <p className="flex items-center gap-2 font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
          <Users className="h-4 w-4" /> Ficha canônica
        </p>
        <h1 className="mt-2 font-headline text-5xl font-black uppercase tracking-tight sm:text-6xl">Pessoas</h1>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void load(query);
        }}
        className="mb-6 flex gap-3"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por nome..."
          className="brutal-border-thin border-ink bg-panel px-4 py-3 font-semibold outline-none focus-visible:brutal-focus flex-1"
        />
        <button
          type="submit"
          className="brutal-border-thin brutal-shadow-sm bg-yellow px-5 py-3 font-headline text-sm font-black uppercase tracking-widest text-ink hover:bg-red hover:text-white"
        >
          Buscar
        </button>
      </form>

      {loading ? <LoadingState label="Carregando pessoas..." /> : null}
      {error ? <ErrorState message={error} onRetry={() => load(query)} /> : null}
      {!loading && !error && people && people.length === 0 ? (
        <EmptyState title="Nenhuma pessoa encontrada" message="Ajuste a busca ou aguarde dados serem ingeridos." />
      ) : null}
      {!loading && !error && people && people.length > 0 ? (
        <div className="flex flex-col gap-3">
          {people.map((person) => (
            <Link key={person.id} href={`/people/${person.id}`}>
              <BrutalCard className="transition-colors hover:bg-yellow">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-headline text-lg font-black uppercase">{person.canonical_name}</h3>
                  <span className="text-xs font-bold uppercase text-ink/60">
                    Criado em {formatDateTime(person.created_at)}
                  </span>
                </div>
              </BrutalCard>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
