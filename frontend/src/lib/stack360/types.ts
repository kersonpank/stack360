// Tipos 1:1 com o JSON devolvido pelo backend Stack360 (app/stack360/api/*.py,
// app/stack360/services/context.py). Nomes de campo em snake_case de propósito —
// espelham o contrato real da API, sem camada de tradução.

export type Stack360Error = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type SourceSummary = {
  id: string;
  key: string;
  name: string;
  source_type: string;
  status: string;
};

export type SourceHealth = {
  source_key: string;
  name: string;
  status: string;
  last_event_at: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  last_error_message: string | null;
  events_24h: number;
  failed_24h: number;
  feeding: boolean;
};

export type PersonSummary = {
  id: string;
  canonical_name: string;
  created_at: string;
};

export type PersonListResponse = {
  items: PersonSummary[];
  next_cursor: string | null;
};

export type CompanySummary = {
  id: string;
  canonical_name: string;
  domain: string | null;
  cnpj_normalized: string | null;
};

export type CompanyDetail = CompanySummary & {
  website: string | null;
  created_at: string;
};

export type CompanyListResponse = {
  items: CompanySummary[];
  next_cursor: string | null;
};

export type Identity = {
  identity_type: string;
  value_normalized: string;
  is_verified: boolean;
  data_source_key: string | null;
  last_seen_at: string;
};

export type PersonCompanyLink = {
  company: {
    id: string;
    canonical_name: string;
    domain: string | null;
    cnpj_normalized: string | null;
  };
  relationship: {
    role: string | null;
    title: string | null;
    is_current: boolean;
    first_seen_at: string;
  };
};

export type CompanyPersonLink = {
  person: { id: string; canonical_name: string };
  relationship: { role: string | null; title: string | null; is_current: boolean };
};

export type Interaction = {
  interaction_type: string;
  channel: string | null;
  direction: string | null;
  occurred_at: string;
  data_source_key: string | null;
  // só presente no context de pessoa, ausente no de empresa
  metadata?: Record<string, unknown> | null;
};

export type Observation = {
  key: string;
  value: unknown;
  confidence: number | null;
  source_kind: string | null;
  data_source_key: string | null;
  observed_at: string;
};

export type ExperienceRun = {
  run_id: string;
  experience_key: string;
  version: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  utm_source: string | null;
  utm_campaign: string | null;
};

export type ExperienceResult = {
  run_id: string;
  result_type: string;
  score: number | null;
  verdict: string | null;
  score_band: string | null;
  engine_name: string | null;
  engine_version: string | null;
  calculated_at: string;
};

export type Score = {
  score_key: string;
  score_value: number;
  score_band: string | null;
  calculated_at: string;
  data_source_key: string | null;
};

export type PersonContext = {
  person: PersonSummary;
  identities?: Identity[];
  companies?: PersonCompanyLink[];
  recent_interactions?: Interaction[];
  observations?: Observation[];
  experience_runs?: ExperienceRun[];
  results?: ExperienceResult[];
  scores?: Score[];
};

// --- Admin (gestão de workspace/source/api-key — scope "admin") ---

export type AdminWorkspace = {
  id: string;
  slug: string;
  name: string;
};

export type AdminSource = {
  id: string;
  key: string;
  name: string;
  source_type: string;
  status: string;
};

export type AdminApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  status: string;
  source_key: string | null;
  created_at: string;
  last_used_at: string | null;
};

export type CreatedApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  plaintext: string;
};

export type CompanyContext = {
  company: CompanyDetail;
  people?: CompanyPersonLink[];
  recent_interactions?: Interaction[];
  observations?: Observation[];
  scores?: Score[];
};
