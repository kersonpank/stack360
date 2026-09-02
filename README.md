# Stack360

**Omnichannel Data & Intelligence Hub.** Camada canônica que organiza dados de
**qualquer fonte** (diagnósticos, formulários, WhatsApp, apps próprios…) em torno de
pessoas, identidades, empresas, relacionamentos, interações, observações, experiências,
execuções, respostas, resultados, scores — sempre com **proveniência**. Qualquer fonte
autorizada **alimenta**; qualquer app ou agente de IA autorizado **consulta**.

Não é CRM, campaign builder, sender nem workflow engine. **Organiza e serve dados.**

---

## Duas aplicações neste repositório

| | Comando | O que é |
|---|---|---|
| **Stack360 Canonical Core** *(atual)* | `uvicorn app.stack360.main:app` | API canônica multi-workspace, com auth por API key, ingestão universal, leitura/contexto, webhooks inbound e servidor MCP. Código em [`app/stack360/`](app/stack360/). |
| **API legada (WhatsApp)** | `uvicorn app.main:app` | Inteligência read-only sobre conversas de WhatsApp (frete). **Intocada** pelo core novo. Doc: [`docs/legacy-whatsapp-api.md`](docs/legacy-whatsapp-api.md). |

Os dois processos são independentes: o core novo **não** importa o legado, **não** roda
os schedulers legados e **não** expõe rotas legadas. Coexistem no mesmo banco em schemas
separados (`stack360` vs `public`).

## Consumir o Stack360 (apps e IA)

Comece por **[`docs/integrations/`](docs/integrations/)**:

| Doc | Para quê |
|---|---|
| [quickstart.md](docs/integrations/quickstart.md) | integrar um sistema novo em < 10 min |
| [rest-api.md](docs/integrations/rest-api.md) | auth, envelope de evento, idempotência, endpoints, contrato de erro |
| [authentication.md](docs/integrations/authentication.md) | API keys, scopes, revogação |
| [event-catalog.md](docs/integrations/event-catalog.md) | tipos de evento aceitos + entidades afetadas |
| [mcp.md](docs/integrations/mcp.md) | servidor MCP para agentes de IA |
| [webhooks.md](docs/integrations/webhooks.md) · [create-a-source.md](docs/integrations/create-a-source.md) · [consume-stack360.md](docs/integrations/consume-stack360.md) · [examples.md](docs/integrations/examples.md) | webhooks, conectar fonte nova, exemplos |

Contrato vivo (OpenAPI): `GET /openapi.json` · UI: `/docs` e `/redoc`.

## Rodar localmente

```bash
python -m venv .venv && . .venv/Scripts/activate    # (Linux/mac: . .venv/bin/activate)
pip install -r requirements.txt -r requirements-stack360.txt

# Postgres local (dev + testes) na porta 5433
docker compose -f docker-compose.stack360.yml up -d

# banco vazio -> baseline legado + schema canônico
export NORMALIZER_DATABASE_URL=postgresql+psycopg2://stack360:stack360@localhost:5433/stack360_dev
export DATABASE_URL=$NORMALIZER_DATABASE_URL
python -m alembic stamp 13b31f818410
python -m alembic upgrade aa47386e4e9f

uvicorn app.stack360.main:app --port 8010
curl -s localhost:8010/api/v1/health      # {"status":"ok","service":"stack360-core"}
```

Detalhes de fluxo (workspace, source, API key, primeiro evento): [quickstart.md](docs/integrations/quickstart.md).

## Testes

```bash
python -m pytest -q                       # 228 testes (171 legado + 57 stack360)
python -m pytest -q --ignore=tests/stack360   # só o legado (não precisa de Postgres)
```

Os testes do Stack360 exigem o Postgres local (`docker-compose.stack360.yml`) e
pulam com mensagem clara se ele não estiver de pé.

## Deploy

VPS + Docker Compose (Postgres + API + Caddy com HTTPS e Basic Auth no `/docs`):
**[`docs/DEPLOY.md`](docs/DEPLOY.md)**. Arquivos em [`deploy/`](deploy/).

## Layout

```
app/
  main.py            entrypoint LEGADO (WhatsApp)
  api/ models/ ...    código legado (intocado)
  stack360/          >>> Stack360 Canonical Core <<<
    main.py           entrypoint canônico (uvicorn app.stack360.main:app)
    api/ services/ repositories/ models/ schemas/
    ingestion/        gateway de 3 transações + handlers por família de evento
    resolution/       identidade e empresa (determinístico, sem fuzzy/merge)
    mcp/              servidor MCP (stdio) para agentes
    admin.py          CLI: workspace / source / api-key / experience / webhook ...
adapters/             adapters de webhook (v1: passthrough)
alembic/versions/     aa47386e4e9f_stack360_core.py  = migration do schema stack360
docs/
  integrations/       documentação para quem consome o Stack360
  DEPLOY.md            guia de deploy
  legacy-whatsapp-api.md
deploy/               Dockerfile, docker-compose.prod.yml, Caddyfile, .env.prod.example
frontend/             dashboard Next.js (hoje aponta para a API LEGADA — ver DEPLOY.md §9)
tests/stack360/       suíte do core (Postgres real)
```

## Frontend

`frontend/` é um dashboard Next.js 15 que **hoje consome a API legada**, não o Stack360.
Para usá-lo com o core novo, `frontend/src/lib/` precisa ser reapontado para os endpoints
do Stack360. Ver [`docs/DEPLOY.md`](docs/DEPLOY.md) §9.
