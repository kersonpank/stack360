import { BrutalCard } from "@/components/ui/BrutalCard";

export function FutureHooksNotice() {
  return (
    <BrutalCard className="bg-panel/60">
      <h3 className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">Em breve</h3>
      <ul className="mt-2 flex flex-col gap-1 text-xs font-semibold text-ink/60">
        <li>Timeline — depende da projeção legado→canônico (fase futura).</li>
        <li>Fila de resolução — recomendação só existe via MCP hoje (fase futura).</li>
      </ul>
    </BrutalCard>
  );
}
