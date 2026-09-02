# Quickstart — integrar um sistema novo em < 10 min

> Todos os comandos rodam localmente contra o Postgres do Stack360
> (`docker compose -f docker-compose.stack360.yml up -d`). Nenhum secret real.

## 0. Subir o core (uma vez)

```bash
docker compose -f docker-compose.stack360.yml up -d

# banco local vazio -> baseline legado + schema canônico
export NORMALIZER_DATABASE_URL=postgresql+psycopg2://stack360:stack360@localhost:5433/stack360_dev
export DATABASE_URL=$NORMALIZER_DATABASE_URL
python -m alembic stamp 13b31f818410
python -m alembic upgrade aa47386e4e9f     # cria o schema stack360 (21 tabelas)

# API
uvicorn app.stack360.main:app --port 8010
```

## 1. Registrar o workspace (negócio dono dos dados) e a source

```bash
export STACK360_DATABASE_URL=postgresql+psycopg2://stack360:stack360@localhost:5433/stack360_dev

python -m app.stack360.admin create-workspace --slug stack360-empresas --name "Stack360 Empresas"

python -m app.stack360.admin create-source \
  --workspace stack360-empresas --key minha-app --name "Minha App" --type custom
```

## 2. Gerar a API key (workspace + source vêm da key)

```bash
# key de INGESTÃO — SEMPRE vinculada a UMA source
python -m app.stack360.admin create-api-key \
  --workspace stack360-empresas --source minha-app --name "ingest" --scopes ingest

# key de LEITURA — pode ser workspace-level
python -m app.stack360.admin create-api-key \
  --workspace stack360-empresas --name "read" --scopes read,mcp
```

Guarde as chaves impressas (`st_...`) — não são exibidas de novo.

## 3. Enviar um evento

```bash
curl -sS -X POST http://localhost:8010/api/v1/ingest/events \
  -H "Authorization: Bearer $INGEST_KEY" -H "content-type: application/json" -d '{
    "schema_version": "1.0",
    "event_id": "evt-0001",
    "event_type": "identity.observed",
    "occurred_at": "2026-09-01T12:00:00Z",
    "subject": { "identities": [ { "type": "email", "value": "joao@empresaabc.com.br" } ] },
    "company": { "cnpj": "12.345.678/0001-99", "name": "Empresa ABC Ltda" }
  }'
# -> {"accepted":true,"event_id":"evt-0001","status":"accepted","entities":{"person_id":"...","company_id":"..."}}
```

Reenvie o **mesmo `event_id` + mesmo payload** → `{"status":"duplicate","duplicate":true}` (idempotente).
Reenvie o **mesmo `event_id` com payload diferente** → `409 EVENT_ID_CONFLICT`: o evento
original fica **intacto**, abre-se um `resolution_case`, e nada é sobrescrito. Corrija o
`event_id` (ou o payload) na origem.

## 4. Consultar o contexto

```bash
curl -sS http://localhost:8010/api/v1/people/$PERSON_ID/context \
  -H "Authorization: Bearer $READ_KEY"
```

Retorna `person`, `identities`, `companies`, `recent_interactions`, `observations`,
`experience_runs`, `results`, `scores`. Use `?include=identities,companies&limit=10&since=2026-01-01`.

## 5. (Opcional) Conectar um agente via MCP

```bash
STACK360_API_KEY=$READ_KEY python -m app.stack360.mcp.server   # stdio
```

Ferramentas: `search_people`, `get_person_context`, `get_company_context`,
`list_recent_interactions`, `list_resolution_cases`, ... e escrita controlada
`ingest_event` / `record_observation` / `submit_resolution_recommendation`.

## Experiências (diagnósticos / quizzes / simuladores)

Uma experiência **precisa ser registrada** antes de enviar runs:

```bash
python -m app.stack360.admin create-experience \
  --workspace stack360-empresas --key diagnostico-expansao-ma --version 1 \
  --name "Diagnóstico de Expansão MA" --type diagnostic
```

Sem isso, eventos `experience.run_started` retornam **`EXPERIENCE_NOT_FOUND`** (422)
e o `ingestion_event` fica `failed` (o raw é preservado para replay).

Fluxo de eventos: `experience.run_started` → `experience.answer_recorded` (N) →
`experience.identity_captured` (email/empresa) → `experience.run_completed` (+ result).
