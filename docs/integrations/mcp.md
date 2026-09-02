# MCP — Stack360 para agentes

O servidor MCP é uma **interface para agentes**. Ele **não tem lógica de negócio
própria** — reutiliza exatamente os mesmos services da REST API (zero
divergência de regra).

## Conexão

Transporte **stdio** (v1). HTTP/SSE é follow-up.

```bash
STACK360_API_KEY=st_...  python -m app.stack360.mcp.server
```

`workspace` e `source` da sessão ficam **fixos** no start. A **autorização** é
**revalidada** contra o banco a cada chamada de tool, com um cache de TTL curto:

| env | default | efeito |
|---|---|---|
| `STACK360_MCP_AUTH_TTL` | `30` (segundos) | janela em que o `AuthContext` é reaproveitado sem novo lookup |
| `STACK360_MCP_AUTH_TTL=0` | — | revalida **toda** chamada |

Assim, uma key **revogada** / com `status != active` / com **scope removido**, ou
uma **source desativada** (para writes), passa a ser rejeitada **sem reiniciar o
processo MCP** (após a janela de TTL). O plaintext da key fica **só em memória**
do processo, para revalidação — nunca é logado nem persistido. O agente **nunca**
passa `workspace_id`.

Config de cliente MCP (ex.):

```json
{
  "mcpServers": {
    "stack360": {
      "command": "python",
      "args": ["-m", "app.stack360.mcp.server"],
      "env": { "STACK360_API_KEY": "st_...", "STACK360_DATABASE_URL": "postgresql+psycopg2://..." }
    }
  }
}
```

## Ferramentas

### Leitura (`read` ou `mcp`)

| tool | parâmetros | retorna |
|---|---|---|
| `search_people` | `query?`, `identity_type?`, `identity_value?`, `limit?` | lista de pessoas |
| `get_person` | `person_id` | pessoa |
| `get_person_context` | `person_id`, `limit?`, `include?` | **contexto completo** (idêntico ao REST) |
| `search_companies` | `query?`, `domain?`, `limit?` | lista |
| `get_company` / `get_company_context` | `company_id`, … | empresa / contexto |
| `list_recent_interactions` | `person_id?`, `company_id?`, `limit?` | interações |
| `list_experience_runs` | `experience_key?`, `limit?` | runs |
| `get_experience_run` | `run_id` | run |
| `list_sources` / `get_source_health` | – | fontes / saúde |
| `list_resolution_cases` | `status?`, `case_type?`, `limit?` | casos de data quality |
| `get_resolution_case` | `case_id` | caso + recomendações |

### Escrita controlada

| tool | scope | efeito |
|---|---|---|
| `ingest_event` | `ingest` (key **source-bound**) | envia um envelope universal pelo mesmo gateway |
| `record_observation` | `ingest` | açúcar → `observation.recorded` |
| `record_interaction` | `ingest` | açúcar → `interaction.*` |
| `submit_resolution_recommendation` | `mcp`/`read` | **cria uma recommendation** num `resolution_case` |

## Data Quality Agent — limites

`submit_resolution_recommendation` **apenas registra uma recomendação**
(`recommended_action`, `evidence` estruturada, `confidence`, `summary` curto).
Ela **nunca** faz merge, nunca altera Person/Company/identidade. Não armazene
chain-of-thought — só a conclusão auditável.

**IA = investigador/recomendador. Stack360 / policy / humano = autoridade de
resolução.** O merge/unmerge auditável é fase futura.

## Isolamento

Toda tool respeita `workspace`, `source`, `scope` e `auth` derivados da key.
Um agente da Workspace A não enxerga dados da Workspace B.
