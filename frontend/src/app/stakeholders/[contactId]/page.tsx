"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CalendarClock,
  CheckSquare,
  MessageSquareText,
  Phone,
  ShieldAlert,
  Sparkles,
  Tag,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatDateTime, formatNumber } from "@/components/ui/format";
import {
  getStakeholder,
  getStakeholderConversations,
  getStakeholderOpportunities,
  getStakeholderTimeline,
} from "@/lib/api";
import type {
  UiConversation,
  UiOpportunity,
  UiStakeholderDetail,
  UiTimelineEvent,
} from "@/lib/types";

const pendingItems = [
  "Confirmar nome completo",
  "Confirmar empresa representada",
  "Confirmar CNPJ/CPF",
  "Confirmar papel: cliente, lead, motorista, fornecedor",
  "Confirmar veículo, se motorista",
  "Confirmar cidade base, se motorista",
  "Confirmar interesse comercial",
];

export default function Stakeholder360Page() {
  const params = useParams<{ contactId: string }>();
  const router = useRouter();
  const contactId = safeDecodeURIComponent(params.contactId);
  const [stakeholder, setStakeholder] = useState<UiStakeholderDetail | null>(null);
  const [conversations, setConversations] = useState<UiConversation[]>([]);
  const [timeline, setTimeline] = useState<UiTimelineEvent[]>([]);
  const [opportunities, setOpportunities] = useState<UiOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [detail, conversationData, timelineData, opportunityData] = await Promise.all([
        getStakeholder(contactId),
        getStakeholderConversations(contactId),
        getStakeholderTimeline(contactId),
        getStakeholderOpportunities(contactId),
      ]);
      setStakeholder(detail);
      setConversations(conversationData);
      setTimeline(timelineData);
      setOpportunities(opportunityData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao carregar Stakeholder 360.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contactId]);

  if (loading) return <LoadingState label="Carregando Stakeholder 360..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!stakeholder) return null;

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 border-b-[4px] border-ink pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <button
            type="button"
            onClick={() => router.back()}
            className="mb-4 inline-flex items-center gap-2 font-headline text-sm font-black uppercase tracking-widest text-blue underline decoration-2 underline-offset-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </button>
          <p className="font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
            Stakeholder Profile
          </p>
          <h1 className="mt-2 break-words font-headline text-4xl font-black uppercase tracking-tight sm:text-6xl">
            {stakeholder.name}
          </h1>
        </div>
        <Button href="/stakeholders" variant="dark">
          Registry
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-7 xl:grid-cols-12">
        <aside className="space-y-7 xl:col-span-3">
          <BrutalCard>
            <h2 className="border-b-2 border-ink pb-3 font-headline text-2xl font-black uppercase">
              Identity
            </h2>
            <div className="mt-4 space-y-4">
              <InfoRow icon={Phone} label="Telefone" value={stakeholder.phone} />
              <InfoRow icon={Tag} label="Relacionamento" value={stakeholder.type} />
              <InfoRow icon={ShieldAlert} label="Status" value={stakeholder.status} />
              <InfoRow icon={CalendarClock} label="Primeiro contato" value={formatDateTime(stakeholder.firstContact)} />
              <InfoRow icon={CalendarClock} label="Último contato" value={formatDateTime(stakeholder.lastInteraction)} />
              <InfoRow
                icon={MessageSquareText}
                label="Mensagens"
                value={formatNumber(stakeholder.totalMessages)}
              />
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {stakeholder.roles.length > 0 ? (
                stakeholder.roles.map((role) => <Badge key={role}>{role}</Badge>)
              ) : (
                <Badge>Sem tags</Badge>
              )}
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <ScoreBox label="Oportunidade" value={stakeholder.score} tone="yellow" />
              <ScoreBox label="Risco" value={stakeholder.riskScore} tone="red" />
            </div>
          </BrutalCard>

          <BrutalCard className="bg-muted">
            <h2 className="mb-4 font-headline text-xl font-black uppercase">Pending Data</h2>
            <div className="space-y-3">
              {pendingItems.map((item) => (
                <label key={item} className="flex items-start gap-3 font-bold">
                  <span className="brutal-border-thin mt-0.5 flex h-5 w-5 flex-none items-center justify-center bg-panel">
                    <CheckSquare className="h-3 w-3 opacity-0" />
                  </span>
                  <span className="text-sm">{item}</span>
                </label>
              ))}
            </div>
          </BrutalCard>
        </aside>

        <section className="space-y-7 xl:col-span-6">
          <BrutalCard className="bg-yellow">
            <div className="mb-4 flex items-center gap-3">
              <Sparkles className="h-7 w-7" />
              <h2 className="font-headline text-2xl font-black uppercase">Intelligence Summary</h2>
            </div>
            <p className="text-lg font-semibold leading-relaxed">{stakeholder.summary}</p>
          </BrutalCard>

          <BrutalCard className="bg-red text-white">
            <div className="mb-4 flex items-center gap-3">
              <Zap className="h-7 w-7" />
              <h2 className="font-headline text-2xl font-black uppercase">Next Best Action</h2>
            </div>
            <h3 className="font-headline text-xl font-black uppercase">{stakeholder.nextBestAction.title}</h3>
            <p className="mt-3 text-lg font-bold leading-relaxed">{stakeholder.nextBestAction.description}</p>
          </BrutalCard>

          <section>
            <h2 className="mb-4 font-headline text-2xl font-black uppercase">Conversations</h2>
            {conversations.length === 0 ? (
              <EmptyState
                title="Nenhuma conversa encontrada"
                message="Este stakeholder ainda não possui conversas normalizadas."
              />
            ) : (
              <div className="space-y-4">
                {conversations.map((conversation) => (
                  <BrutalCard key={conversation.id}>
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex flex-wrap gap-2">
                          <Badge tone="dark">{conversation.channel}</Badge>
                          <Badge>{conversation.chatType}</Badge>
                          <Badge tone="yellow">{conversation.totalMessages} msgs</Badge>
                        </div>
                        <h3 className="mt-3 font-headline text-xl font-black uppercase">
                          {conversation.subject || "Conversa sem assunto"}
                        </h3>
                        <p className="mt-2 max-w-2xl font-semibold text-ink/75">
                          {conversation.lastMessage || "Sem resumo de conversa."}
                        </p>
                        <p className="mt-2 text-xs font-bold uppercase text-ink/60">
                          {formatDateTime(conversation.firstMessageAt)} {"->"}{" "}
                          {formatDateTime(conversation.lastMessageAt)}
                        </p>
                      </div>
                      <Button
                        href={`/conversations/${encodeURIComponent(conversation.id)}?channel=${encodeURIComponent(
                          conversation.channel,
                        )}&contact=${encodeURIComponent(stakeholder.name)}`}
                        variant="dark"
                      >
                        Abrir conversa
                      </Button>
                    </div>
                  </BrutalCard>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-4 font-headline text-2xl font-black uppercase">Timeline</h2>
            {timeline.length === 0 ? (
              <EmptyState
                title="Ainda não há eventos inteligentes gerados"
                message="Quando sinais forem criados pela API, eles aparecerão nesta linha do tempo."
              />
            ) : (
              <div className="border-l-[4px] border-ink pl-5">
                {timeline.map((event) => (
                  <div key={event.id} className="relative mb-5">
                    <span className="absolute -left-[34px] top-1 h-5 w-5 border-[3px] border-ink bg-yellow" />
                    <div className="brutal-border-thin bg-panel p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={event.type === "OPPORTUNITY" ? "yellow" : "default"}>{event.type}</Badge>
                        <span className="text-xs font-bold uppercase text-ink/60">{formatDateTime(event.date)}</span>
                      </div>
                      <h3 className="mt-2 font-headline text-lg font-black uppercase">{event.title}</h3>
                      <p className="mt-1 text-sm font-semibold">{event.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </section>

        <aside className="space-y-7 xl:col-span-3">
          <BrutalCard>
            <h2 className="mb-4 flex items-center justify-between font-headline text-xl font-black uppercase">
              Opportunities
              <Badge tone="blue">{opportunities.length}</Badge>
            </h2>
            {opportunities.length === 0 ? (
              <p className="font-semibold text-ink/70">Nenhuma oportunidade detectada ainda.</p>
            ) : (
              <div className="space-y-4">
                {opportunities.map((opportunity) => (
                  <div key={opportunity.id} className="border-b-2 border-ink pb-4 last:border-b-0 last:pb-0">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-headline text-lg font-black uppercase">{opportunity.title}</h3>
                      <Badge tone="yellow">{opportunity.score}</Badge>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-ink/75">{opportunity.evidence}</p>
                    <p className="mt-3 font-headline text-xs font-black uppercase tracking-widest text-blue">
                      {opportunity.nextAction}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </BrutalCard>
        </aside>
      </div>
    </div>
  );
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 h-4 w-4 flex-none" />
      <div className="min-w-0">
        <div className="font-headline text-[11px] font-black uppercase tracking-widest text-ink/55">{label}</div>
        <div className="break-words text-sm font-bold">{value || "Não informado"}</div>
      </div>
    </div>
  );
}

function ScoreBox({ label, value, tone }: { label: string; value: number; tone: "yellow" | "red" }) {
  return (
    <div className={`brutal-border-thin p-3 ${tone === "yellow" ? "bg-yellow text-ink" : "bg-red text-white"}`}>
      <div className="font-headline text-[10px] font-black uppercase tracking-widest">{label}</div>
      <div className="font-headline text-3xl font-black">{value}</div>
    </div>
  );
}

function safeDecodeURIComponent(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
