export type ApiHealth = {
  status: string;
  service: string;
};

export type ApiStakeholderSearchResult = {
  contact_id: string;
  telefone?: string | null;
  nome_atual?: string | null;
  tipo_relacionamento?: string | null;
  status_relacionamento?: string | null;
  ultimo_contato_em?: string | null;
  total_mensagens?: number | null;
  score_oportunidade?: number | null;
  score_risco?: number | null;
  tags?: string[] | null;
};

export type ApiStakeholderListResponse = {
  total: number;
  page: number;
  page_size: number;
  items: ApiStakeholderSearchResult[];
};

export type ApiStakeholderDetail = ApiStakeholderSearchResult & {
  status_relacionamento?: string | null;
  primeiro_contato_em?: string | null;
  score_oportunidade?: number | null;
  score_risco?: number | null;
  tags?: string[] | null;
  resumo_geral?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ApiConversation = {
  conversation_id: string;
  contact_id?: string | null;
  source_account_id?: string | null;
  instance_name?: string | null;
  remote_jid?: string | null;
  tipo_chat?: string | null;
  primeira_mensagem_em?: string | null;
  ultima_mensagem_em?: string | null;
  total_mensagens?: number | null;
  assunto_principal?: string | null;
  resumo_conversa?: string | null;
  status_conversa?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ApiMessage = {
  message_id: string;
  data_hora?: string | null;
  enviada_por_mim?: boolean | null;
  nome_contato?: string | null;
  tipo_mensagem?: string | null;
  texto?: string | null;
  status?: string | null;
  source?: string | null;
};

export type ApiMessageList = {
  total: number;
  limit: number;
  offset: number;
  items: ApiMessage[];
};

export type ApiTimelineEvent = {
  event_id: number | string;
  contact_id?: string | null;
  conversation_id?: string | null;
  message_id?: string | null;
  data_hora?: string | null;
  tipo_evento?: string | null;
  titulo?: string | null;
  descricao?: string | null;
  importancia?: string | null;
  payload?: unknown;
};

export type ApiOpportunity = {
  opportunity_id: number | string;
  contact_id?: string | null;
  conversation_id?: string | null;
  origem_message_id?: string | null;
  tipo_oportunidade?: string | null;
  descricao?: string | null;
  score?: number | null;
  status?: string | null;
  proxima_acao?: string | null;
  responsavel?: string | null;
  espo_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ApiSourceAccountStatus = {
  source_account_id?: string | null;
  instance_name?: string | null;
  total_raw: number;
  normalized: number;
  pending: number;
};

export type ApiNormalizationStatus = {
  total_raw: number;
  total_raw_normalized: number;
  total_raw_pending: number;
  total_contacts: number;
  total_conversations: number;
  total_messages: number;
  by_source_account: ApiSourceAccountStatus[];
};

export type UiStakeholderSearchResult = {
  id: string;
  name: string;
  type: string;
  status: string;
  phone: string;
  roles: string[];
  channels: string[];
  lastInteraction: string;
  totalMessages: number;
  score: number;
  riskScore: number;
  confidence: number;
  nextAction: string;
};

export type UiStakeholderDetail = UiStakeholderSearchResult & {
  firstContact: string;
  summary: string;
  nextBestAction: {
    title: string;
    priority: "HIGH" | "MEDIUM" | "LOW";
    description: string;
  };
};

export type UiStakeholderListResponse = {
  total: number;
  page: number;
  pageSize: number;
  items: UiStakeholderSearchResult[];
};

export type UiConversation = {
  id: string;
  contactId: string;
  channel: string;
  remoteJid: string;
  chatType: string;
  firstMessageAt: string;
  lastMessageAt: string;
  totalMessages: number;
  subject: string;
  lastMessage: string;
  status: string;
};

export type UiMessage = {
  id: string;
  direction: "INBOUND" | "OUTBOUND";
  content: string;
  type: "TEXT" | "AUDIO" | "IMAGE" | "PDF";
  rawType: string;
  timestamp: string;
  contactName: string;
  status: string;
  source: string;
};

export type UiMessageList = {
  total: number;
  limit: number;
  offset: number;
  items: UiMessage[];
};

export type UiTimelineEvent = {
  id: string;
  type: "MESSAGE" | "SIGNAL" | "OPPORTUNITY" | "CONTRACT" | "PENDING";
  title: string;
  description: string;
  date: string;
  origin: string;
  importance: string;
};

export type UiOpportunity = {
  id: string;
  title: string;
  score: number;
  evidence: string;
  nextAction: string;
  status: string;
  responsible: string;
  conversationId: string;
};

export type UiSourceAccountStatus = {
  id: string;
  instanceName: string;
  totalRaw: number;
  normalized: number;
  pending: number;
  normalizedPercent: number;
};

export type UiNormalizationStatus = {
  totalRaw: number;
  totalRawNormalized: number;
  totalRawPending: number;
  totalContacts: number;
  totalConversations: number;
  totalMessages: number;
  bySourceAccount: UiSourceAccountStatus[];
};
