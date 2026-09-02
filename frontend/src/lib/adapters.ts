import type {
  ApiConversation,
  ApiMessage,
  ApiMessageList,
  ApiNormalizationStatus,
  ApiOpportunity,
  ApiStakeholderDetail,
  ApiStakeholderListResponse,
  ApiStakeholderSearchResult,
  ApiTimelineEvent,
  UiConversation,
  UiMessage,
  UiMessageList,
  UiNormalizationStatus,
  UiOpportunity,
  UiStakeholderDetail,
  UiStakeholderListResponse,
  UiStakeholderSearchResult,
  UiTimelineEvent,
} from "./types";

const UNKNOWN = "unknown";

function text(value: string | null | undefined, fallback = "") {
  return value && value.trim().length > 0 ? value : fallback;
}

function number(value: number | null | undefined) {
  return value ?? 0;
}

function normalizeTimelineType(value: string | null | undefined): UiTimelineEvent["type"] {
  const upper = text(value, "SIGNAL").toUpperCase();
  if (upper.includes("MESSAGE")) return "MESSAGE";
  if (upper.includes("OPPORT")) return "OPPORTUNITY";
  if (upper.includes("CONTRACT")) return "CONTRACT";
  if (upper.includes("PENDING")) return "PENDING";
  return "SIGNAL";
}

export function mapApiStakeholderSearchToUi(
  stakeholder: ApiStakeholderSearchResult,
): UiStakeholderSearchResult {
  const id = stakeholder.contact_id;
  const phone = text(stakeholder.telefone, id);

  return {
    id,
    name: text(stakeholder.nome_atual, phone || id),
    type: text(stakeholder.tipo_relacionamento, UNKNOWN),
    status: text(stakeholder.status_relacionamento, "active"),
    phone,
    roles: stakeholder.tags ?? [],
    channels: [],
    lastInteraction: text(stakeholder.ultimo_contato_em),
    totalMessages: number(stakeholder.total_mensagens),
    score: number(stakeholder.score_oportunidade),
    riskScore: number(stakeholder.score_risco),
    confidence: 0,
    nextAction: "Completar dados",
  };
}

export function mapApiStakeholderDetailToUi(stakeholder: ApiStakeholderDetail): UiStakeholderDetail {
  const base = mapApiStakeholderSearchToUi(stakeholder);
  const roles = stakeholder.tags ?? [];
  const score = number(stakeholder.score_oportunidade);
  const riskScore = number(stakeholder.score_risco);

  return {
    ...base,
    roles,
    score,
    status: text(stakeholder.status_relacionamento, "status desconhecido"),
    firstContact: text(stakeholder.primeiro_contato_em),
    summary: text(stakeholder.resumo_geral, "Resumo ainda não gerado."),
    riskScore,
    nextBestAction: {
      title: "Completar dados do stakeholder",
      priority: riskScore >= 70 ? "HIGH" : "MEDIUM",
      description: "Validar nome, empresa, papel, documento e dados operacionais.",
    },
  };
}

export function mapApiStakeholderListToUi(
  response: ApiStakeholderListResponse,
): UiStakeholderListResponse {
  return {
    total: response.total,
    page: response.page,
    pageSize: response.page_size,
    items: response.items.map(mapApiStakeholderSearchToUi),
  };
}

export function mapApiConversationToUi(conversation: ApiConversation): UiConversation {
  return {
    id: conversation.conversation_id,
    contactId: text(conversation.contact_id),
    channel: text(
      conversation.instance_name,
      text(conversation.source_account_id, "Canal desconhecido"),
    ),
    remoteJid: text(conversation.remote_jid),
    chatType: text(conversation.tipo_chat, "chat"),
    firstMessageAt: text(conversation.primeira_mensagem_em),
    lastMessageAt: text(conversation.ultima_mensagem_em),
    totalMessages: number(conversation.total_mensagens),
    subject: text(conversation.assunto_principal),
    lastMessage: text(conversation.resumo_conversa, text(conversation.assunto_principal)),
    status: text(conversation.status_conversa, "desconhecido"),
  };
}

export function mapApiMessageToUi(message: ApiMessage): UiMessage {
  const rawType = text(message.tipo_mensagem, "conversation");

  return {
    id: message.message_id,
    direction: message.enviada_por_mim ? "OUTBOUND" : "INBOUND",
    content: text(message.texto, "[sem texto extraído]"),
    timestamp: text(message.data_hora),
    type: mapApiMessageType(rawType),
    rawType,
    contactName: text(message.nome_contato),
    status: text(message.status),
    source: text(message.source),
  };
}

export function mapApiMessageListToUi(messages: ApiMessageList): UiMessageList {
  return {
    total: messages.total,
    limit: messages.limit,
    offset: messages.offset,
    items: messages.items.map(mapApiMessageToUi),
  };
}

export function mapApiTimelineToUi(event: ApiTimelineEvent): UiTimelineEvent {
  return {
    id: String(event.event_id),
    type: normalizeTimelineType(event.tipo_evento),
    title: text(event.titulo, text(event.tipo_evento, "Evento")),
    description: text(event.descricao, "Evento sem descrição."),
    date: text(event.data_hora),
    origin: text(event.conversation_id, text(event.message_id, "Sistema")),
    importance: text(event.importancia, "normal"),
  };
}

export function mapApiOpportunityToUi(opportunity: ApiOpportunity): UiOpportunity {
  return {
    id: String(opportunity.opportunity_id),
    title: text(opportunity.tipo_oportunidade, "Oportunidade detectada"),
    score: number(opportunity.score),
    evidence: text(opportunity.descricao, "Sem evidência textual."),
    nextAction: text(opportunity.proxima_acao, "Revisar oportunidade"),
    status: text(opportunity.status, "novo"),
    responsible: text(opportunity.responsavel, "Sem responsável"),
    conversationId: text(opportunity.conversation_id),
  };
}

export function mapApiNormalizationStatusToUi(
  status: ApiNormalizationStatus,
): UiNormalizationStatus {
  return {
    totalRaw: status.total_raw,
    totalRawNormalized: status.total_raw_normalized,
    totalRawPending: status.total_raw_pending,
    totalContacts: status.total_contacts,
    totalConversations: status.total_conversations,
    totalMessages: status.total_messages,
    bySourceAccount: status.by_source_account.map((source) => ({
      id: text(source.source_account_id, text(source.instance_name, "unknown-source")),
      instanceName: text(source.instance_name, text(source.source_account_id, "Instância desconhecida")),
      totalRaw: source.total_raw,
      normalized: source.normalized,
      pending: source.pending,
      normalizedPercent:
        source.total_raw > 0 ? Math.round((source.normalized / source.total_raw) * 100) : 0,
    })),
  };
}

function mapApiMessageType(type: string): UiMessage["type"] {
  if (type === "conversation" || type === "extendedTextMessage") return "TEXT";
  if (type === "audioMessage" || type === "ptt") return "AUDIO";
  if (type === "imageMessage") return "IMAGE";
  if (type === "documentMessage") return "PDF";
  return "TEXT";
}
