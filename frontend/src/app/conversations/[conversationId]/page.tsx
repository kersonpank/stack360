"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Hash, RadioTower } from "lucide-react";
import { MessageBubble } from "@/components/conversations/MessageBubble";
import { Badge } from "@/components/ui/Badge";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatNumber } from "@/components/ui/format";
import { getConversationMessages } from "@/lib/api";
import type { UiMessageList } from "@/lib/types";

export default function ConversationDetailPage() {
  const params = useParams<{ conversationId: string }>();
  const router = useRouter();
  const conversationId = safeDecodeURIComponent(params.conversationId);
  const [messages, setMessages] = useState<UiMessageList | null>(null);
  const [context, setContext] = useState({ channel: "", contact: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (conversationId === "sample") {
      setMessages(null);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      setMessages(await getConversationMessages(conversationId, { limit: 100, offset: 0, order: "desc" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao carregar mensagens.");
      setMessages(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const search = new URLSearchParams(window.location.search);
    setContext({
      channel: search.get("channel") ?? "",
      contact: search.get("contact") ?? "",
    });
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  return (
    <div>
      <div className="mb-6 border-b-[4px] border-ink pb-5">
        <button
          type="button"
          onClick={() => router.back()}
          className="mb-4 inline-flex items-center gap-2 font-headline text-sm font-black uppercase tracking-widest text-blue underline decoration-2 underline-offset-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </button>
        <p className="font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
          Conversation Detail
        </p>
        <h1 className="mt-2 break-all font-headline text-3xl font-black uppercase tracking-tight sm:text-5xl">
          {context.contact || "Conversa"}
        </h1>
      </div>

      <BrutalCard className="mb-7">
        <div className="grid gap-4 md:grid-cols-3">
          <HeaderMetric icon={Hash} label="conversation_id" value={conversationId} />
          <HeaderMetric icon={RadioTower} label="canal / instância" value={context.channel || "Canal desconhecido"} />
          <HeaderMetric
            icon={Hash}
            label="mensagens carregadas"
            value={messages ? formatNumber(messages.items.length) : "0"}
          />
        </div>
      </BrutalCard>

      {loading ? <LoadingState label="Carregando mensagens reais..." /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error && conversationId === "sample" ? (
        <EmptyState
          title="Abra uma conversa real pelo Stakeholder 360"
          message="A rota /conversations/sample nÃ£o representa uma conversa real. Busque um stakeholder, abra o perfil 360 e selecione uma conversa listada pela API."
        />
      ) : null}
      {!loading && !error && messages?.items.length === 0 ? (
        <EmptyState
          title="Nenhuma mensagem encontrada"
          message="A conversa existe, mas a API não retornou mensagens para os parâmetros atuais."
        />
      ) : null}
      {!loading && !error && messages && messages.items.length > 0 ? (
        <section>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge tone="dark">Total API: {messages.total}</Badge>
            <Badge>Limit: {messages.limit}</Badge>
            <Badge>Offset: {messages.offset}</Badge>
            <Badge tone="yellow">Order: desc</Badge>
          </div>
          <div className="space-y-4">
            {messages.items.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        </section>
      ) : null}
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

function HeaderMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="brutal-border-thin bg-muted p-4">
      <div className="mb-2 flex items-center gap-2 font-headline text-xs font-black uppercase tracking-widest text-ink/60">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className="break-all font-bold">{value || "Não informado"}</div>
    </div>
  );
}
