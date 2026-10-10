import { BrutalCard } from "@/components/ui/BrutalCard";
import { formatDateTime } from "@/components/ui/format";
import { SourceStatusBadge } from "@/components/stack360/ui/SourceStatusBadge";
import type { SourceHealth } from "@/lib/stack360/types";

function dateOrNever(value: string | null) {
  return value ? formatDateTime(value) : "Nunca";
}

export function SourcesHealthTable({ sources }: { sources: SourceHealth[] }) {
  if (sources.length === 0) {
    return (
      <BrutalCard>
        <p className="font-headline text-sm font-black uppercase text-ink/60">
          Nenhuma fonte cadastrada neste workspace ainda.
        </p>
      </BrutalCard>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {sources.map((source) => (
        <BrutalCard key={source.source_key}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-headline text-lg font-black uppercase">{source.name}</h3>
              <p className="text-xs font-bold uppercase text-ink/60">{source.source_key}</p>
            </div>
            <SourceStatusBadge status={source.status} feeding={source.feeding} />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
            <div className="brutal-border-thin border-ink bg-panel p-3">
              <div className="font-headline text-2xl font-black">{source.events_24h}</div>
              <div className="text-[10px] font-black uppercase text-ink/60">eventos 24h</div>
            </div>
            <div className={`brutal-border-thin border-ink p-3 ${source.failed_24h > 0 ? "bg-red text-white" : "bg-panel"}`}>
              <div className="font-headline text-2xl font-black">{source.failed_24h}</div>
              <div className="text-[10px] font-black uppercase opacity-80">falhas 24h</div>
            </div>
            <div className="brutal-border-thin border-ink bg-panel p-3">
              <div className="font-headline text-xs font-black">{dateOrNever(source.last_event_at)}</div>
              <div className="text-[10px] font-black uppercase text-ink/60">último evento</div>
            </div>
            <div className="brutal-border-thin border-ink bg-panel p-3">
              <div className="font-headline text-xs font-black">{dateOrNever(source.last_success_at)}</div>
              <div className="text-[10px] font-black uppercase text-ink/60">último sucesso</div>
            </div>
          </div>

          {source.failed_24h > 0 && source.last_error_message ? (
            <div className="mt-4 border-2 border-red bg-red/10 p-3 text-sm font-semibold text-red">
              Último erro ({dateOrNever(source.last_error_at)}): {source.last_error_message}
            </div>
          ) : null}
        </BrutalCard>
      ))}
    </div>
  );
}
