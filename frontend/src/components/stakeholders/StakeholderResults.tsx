import { ArrowDownUp, ArrowLeft, ArrowRight, Eye, MessageSquareText } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDateTime, formatNumber } from "@/components/ui/format";
import type { UiStakeholderSearchResult } from "@/lib/types";

type StakeholderResultsProps = {
  stakeholders: UiStakeholderSearchResult[];
  total: number;
  page: number;
  pageSize: number;
  sortLabel: string;
  onPageChange: (page: number) => void;
};

export function StakeholderResults({
  stakeholders,
  total,
  page,
  pageSize,
  sortLabel,
  onPageChange,
}: StakeholderResultsProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);

  return (
    <div className="space-y-4">
      <div className="brutal-border brutal-shadow-sm flex flex-col gap-3 bg-panel p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">
            Registro
          </div>
          <div className="mt-1 font-headline text-2xl font-black uppercase">
            {formatNumber(total)} stakeholders
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-widest text-ink/65">
          <span>
            {formatNumber(start)}-{formatNumber(end)}
          </span>
          <span className="h-4 w-[2px] bg-ink/30" />
          <ArrowDownUp className="h-4 w-4" aria-hidden="true" />
          <span>{sortLabel}</span>
        </div>
      </div>

      <div className="brutal-border brutal-shadow overflow-x-auto bg-panel">
        <table className="w-full min-w-[980px] border-collapse text-left">
          <thead className="bg-ink text-white">
            <tr className="font-headline text-xs font-black uppercase tracking-widest">
              <th className="p-4">Stakeholder</th>
              <th className="p-4">Telefone / contact_id</th>
              <th className="p-4">Tipo</th>
              <th className="p-4">Status</th>
              <th className="p-4">Ultimo contato</th>
              <th className="p-4">Mensagens</th>
              <th className="p-4">Scores</th>
              <th className="p-4 text-right">Acao</th>
            </tr>
          </thead>
          <tbody>
            {stakeholders.map((stakeholder) => (
              <tr
                key={stakeholder.id}
                className="border-t-[3px] border-ink transition-[background-color,transform] duration-150 hover:bg-yellow/25 motion-reduce:transition-none"
              >
                <td className="p-4 align-top">
                  <div className="flex gap-3">
                    <div className="brutal-border-thin flex h-11 w-11 flex-none items-center justify-center bg-yellow font-headline text-xl font-black uppercase">
                      {stakeholder.name.charAt(0)}
                    </div>
                    <div>
                      <div className="font-headline text-lg font-black leading-tight">
                        {stakeholder.name}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {stakeholder.roles.length > 0 ? (
                          stakeholder.roles.map((role) => <Badge key={role}>{role}</Badge>)
                        ) : (
                          <Badge>Sem tags</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="max-w-[260px] p-4 align-top">
                  <div className="font-bold">{stakeholder.phone}</div>
                  <div className="mt-1 break-all text-xs font-semibold text-ink/65">
                    {stakeholder.id}
                  </div>
                </td>
                <td className="p-4 align-top">
                  <Badge tone="yellow">{stakeholder.type}</Badge>
                  {stakeholder.channels.length > 0 ? (
                    <div className="mt-2 text-xs font-bold uppercase text-ink/65">
                      {stakeholder.channels.join(" / ")}
                    </div>
                  ) : null}
                </td>
                <td className="p-4 align-top">
                  <Badge tone={stakeholder.status === "active" ? "blue" : "default"}>
                    {stakeholder.status}
                  </Badge>
                </td>
                <td className="p-4 align-top text-sm font-bold">
                  {formatDateTime(stakeholder.lastInteraction)}
                </td>
                <td className="p-4 align-top">
                  <div className="inline-flex items-center gap-2 font-headline text-lg font-black">
                    <MessageSquareText className="h-4 w-4" aria-hidden="true" />
                    {formatNumber(stakeholder.totalMessages)}
                  </div>
                </td>
                <td className="p-4 align-top">
                  <div className="grid min-w-28 grid-cols-2 gap-2">
                    <Score label="OP" value={stakeholder.score} />
                    <Score label="RI" value={stakeholder.riskScore} tone="red" />
                  </div>
                </td>
                <td className="p-4 text-right align-top">
                  <Button href={`/stakeholders/${encodeURIComponent(stakeholder.id)}`} variant="dark">
                    <Eye className="h-4 w-4" aria-hidden="true" />
                    Abrir 360
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">
          Pagina {formatNumber(page)} de {formatNumber(totalPages)}
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Anterior
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="disabled:cursor-not-allowed disabled:opacity-50"
          >
            Proxima
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function Score({ label, value, tone = "blue" }: { label: string; value: number; tone?: "blue" | "red" }) {
  return (
    <div className={`border-2 border-ink px-2 py-1 ${tone === "red" ? "bg-red text-white" : "bg-blue text-white"}`}>
      <div className="text-[10px] font-black leading-none">{label}</div>
      <div className="font-headline text-sm font-black leading-tight">{formatNumber(value)}</div>
    </div>
  );
}
