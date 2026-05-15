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
