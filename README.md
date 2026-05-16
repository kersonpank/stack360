# Stakeholder Intelligence API

API read-only para consulta de memória operacional e comercial baseada em conversas de WhatsApp.

## Pré-requisitos

- Python 3.11+
- PostgreSQL com banco `memory_operation_group_evo_whatsapp` acessível
- Docker + Docker Compose (opcional)

## Setup local

### 1. Ambiente virtual e dependências

```bash
cd stakeholder-intelligence-api
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### 2. Variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com as credenciais reais do banco
```

`.env` (nunca commitar):
```
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/memory_operation_group_evo_whatsapp
API_ENV=development
```

### 3. Rodar a API

```bash
uvicorn app.main:app --reload --port 8000
```

Acesse:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health:** http://localhost:8000/api/v1/health

## Rodar com Docker

```bash
cp .env.example .env  # Edite com credenciais reais
docker compose up --build
```

## Rodar testes (sem banco real)

```bash
pytest -v
```

Os testes usam `MagicMock` — não precisam de conexão real ao PostgreSQL.

## Testar com banco real

```bash
# Após configurar .env:
uvicorn app.main:app --reload --port 8000

# Health
curl http://localhost:8000/api/v1/health

# Buscar stakeholders
curl "http://localhost:8000/api/v1/stakeholders/search?q=joao"

# Detalhe do stakeholder
curl "http://localhost:8000/api/v1/stakeholders/<contact_id>"

# Conversas
curl "http://localhost:8000/api/v1/stakeholders/<contact_id>/conversations"

# Timeline
curl "http://localhost:8000/api/v1/stakeholders/<contact_id>/timeline"

# Oportunidades
curl "http://localhost:8000/api/v1/stakeholders/<contact_id>/opportunities"

# Mensagens (paginado)
curl "http://localhost:8000/api/v1/conversations/<conversation_id>/messages?limit=50&order=desc"
```

## Endpoints

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/health` | Status da API (sem DB) |
| GET | `/api/v1/stakeholders/search?q=` | Busca por id, telefone ou nome |
| GET | `/api/v1/stakeholders/{contact_id}` | Detalhe do stakeholder |
| GET | `/api/v1/stakeholders/{contact_id}/conversations` | Conversas do stakeholder |
| GET | `/api/v1/stakeholders/{contact_id}/timeline` | Timeline do stakeholder |
| GET | `/api/v1/stakeholders/{contact_id}/opportunities` | Oportunidades do stakeholder |
| GET | `/api/v1/conversations/{conversation_id}/messages` | Mensagens da conversa (paginado) |
| GET | `/api/v1/system/normalization-status` | Status de normalização (contagens globais e por instância) |

### Parâmetros — GET messages

| Param | Default | Máximo | Valores |
|-------|---------|--------|---------|
| `limit` | 100 | 500 | 1–500 |
| `offset` | 0 | — | ≥ 0 |
| `order` | `asc` | — | `asc` ou `desc` |

## Estrutura do projeto

```
app/
├── main.py                 # FastAPI app
├── core/
│   ├── config.py           # Settings via .env
│   └── database.py         # SQLAlchemy engine + get_db
├── api/v1/
│   ├── router.py           # Agrega routers v1
│   └── endpoints/          # Controladores HTTP
├── models/                 # ORM → tabelas existentes
├── schemas/                # Pydantic v2 response schemas
├── services/               # Lógica de negócio
└── repositories/           # Queries SQL via SQLAlchemy ORM
```

## Regras

- API é **100% read-only** — sem INSERT, UPDATE, DELETE ou migrations
- Credenciais ficam apenas no `.env` (não commitado)
- `.env.example` contém apenas placeholders

---

## Normalization Worker

Worker CLI que lê `raw_evolution_messages` (sem `normalized_at`) e popula `contacts`, `conversations` e `messages` via upserts idempotentes.

### Configurar credencial de escrita

Adicionar ao `.env` (nunca commitar):

```
NORMALIZER_DATABASE_URL=postgresql+psycopg2://<user>:<password>@host:5432/memory_operation_group_evo_whatsapp
```

### Dry-run (sem gravar no banco)

```bash
python -m app.workers.normalize_raw --dry-run --limit 10
python -m app.workers.normalize_raw --dry-run --limit 5000
```

### Lote real padrão (até 100 por batch)

```bash
python -m app.workers.normalize_raw --limit 100
```

### Lote real maior (requer --confirm-large-run)

```bash
# Um batch de 5.000
python -m app.workers.normalize_raw --limit 5000 --confirm-large-run

# 3 batches de 5.000 = até 15.000 registros
python -m app.workers.normalize_raw --limit 5000 --max-batches 3 --confirm-large-run
```

> **Aviso:** Não processar a base inteira sem autorização. Sempre rodar dry-run primeiro e aguardar validação humana antes de um lote real grande.

### Filtrar por instância

```bash
python -m app.workers.normalize_raw --dry-run --source-account-id <source_account_id>
```

### Status de normalização (endpoint read-only)

```bash
# Com API rodando:
curl http://localhost:8000/api/v1/system/normalization-status
```

Retorna contagens de `raw_evolution_messages` (total, normalizados, pendentes), `contacts`, `conversations`, `messages`, e breakdown por `source_account_id`.

### Regras dos IDs normalizados

| Campo | Regra |
|-------|-------|
| `contact_id` | Telefone puro para individuais (`5599999999999`); `group:<id>` para grupos; `lid:<id>` para lid; `broadcast:status` |
| `conversation_id` | `{source_account_id}:{remote_jid}` |
| `message_id` | `external_message_id` direto da tabela raw |

---

## Normalizer Scheduler

O **n8n** é responsável por trazer novas mensagens da Evolution para `raw_evolution_messages`.
O **Normalizer Scheduler** é responsável por transformar esses raws pendentes em `contacts`, `conversations` e `messages` de forma contínua e automática, sem cron externo ou execução manual.

### Arquitetura

```
n8n → raw_evolution_messages → [Scheduler] → contacts / conversations / messages
```

O scheduler roda dentro do processo da API como uma `asyncio.Task`. Executa em background, sem bloquear requests.

### Configurar .env (produção)

```
NORMALIZER_SCHEDULER_ENABLED=true
NORMALIZER_INTERVAL_SECONDS=300
NORMALIZER_INCREMENTAL_LIMIT=1000
NORMALIZER_INCREMENTAL_MAX_BATCHES=1
NORMALIZER_NIGHTLY_ENABLED=true
NORMALIZER_NIGHTLY_HOUR=2
NORMALIZER_NIGHTLY_LIMIT=5000
NORMALIZER_NIGHTLY_MAX_BATCHES=5
```

### Configurar .env (desenvolvimento)

```
NORMALIZER_SCHEDULER_ENABLED=false
```

> **Atenção:** Nunca habilitar o scheduler com `uvicorn --reload`. O `--reload` reinicia o processo a cada mudança de arquivo, o que pode iniciar múltiplas instâncias do scheduler. Em desenvolvimento, usar o worker CLI manualmente.

### Rodadas

| Tipo | Frequência | Equivalente |
|------|-----------|-------------|
| Incremental | A cada `NORMALIZER_INTERVAL_SECONDS` (default 300s) | `--limit 1000 --max-batches 1` |
| Noturna | Uma vez por dia na hora `NORMALIZER_NIGHTLY_HOUR` (default 2h UTC) | `--limit 5000 --max-batches 5` |

### Advisory lock

Cada rodada adquire `pg_try_advisory_lock` antes de processar. Se outro worker (CLI ou outra instância) já estiver rodando, a rodada é pulada e registrada como `skipped_lock`.

### Endpoint de status

```bash
GET /api/v1/system/normalizer-scheduler-status
```

Retorna estado em memória do scheduler:

```json
{
  "enabled": true,
  "running": false,
  "interval_seconds": 300,
  "nightly_enabled": true,
  "nightly_hour": 2,
  "last_run_started_at": "2025-05-15T02:00:01Z",
  "last_run_finished_at": "2025-05-15T02:00:04Z",
  "last_success_at": "2025-05-15T02:00:04Z",
  "last_error_at": null,
  "last_error_message": null,
  "last_result": { "processed": 0, "batches_executed": 1, "message": "Nenhuma mensagem pendente para normalizar." },
  "total_runs": 10,
  "total_success": 10,
  "total_failures": 0,
  "total_skipped_by_lock": 0,
  "next_run_estimate": "2025-05-15T02:05:04Z"
}
```

### Recomendação de produção

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1
```

Usar `--workers 1` para evitar múltiplas instâncias do scheduler no mesmo processo.
