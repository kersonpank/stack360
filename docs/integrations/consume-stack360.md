# Consumir o Stack360

| Opção | Para quem | Como |
|---|---|---|
| **REST** | aplicações tradicionais, jobs, BI | `GET /api/v1/*` com key de scope `read` |
| **MCP** | agentes de IA | servidor stdio, tools de leitura + escrita controlada |
| **Outbound webhook** | sistemas reativos | **fase seguinte** — ver [webhooks.md](webhooks.md) |
| **Batch / export** | data warehouse | fase futura |

## Exemplos (REST)

### "Tudo que sabemos do João"

```bash
PID=$(curl -s "$BASE/api/v1/people?identity_type=email&identity_value=joao@empresaabc.com.br" \
      -H "Authorization: Bearer $READ" | jq -r '.items[0].id')

curl -s "$BASE/api/v1/people/$PID/context" -H "Authorization: Bearer $READ" | jq
```

Retorna `person`, `identities`, `companies`, `recent_interactions`,
`observations` (última por chave), `experience_runs`, `results`, `scores`
(última por chave). Use `?include=` e `?limit=` e `?since=` para recortar.

### "Contexto da Empresa ABC"

```bash
CID=$(curl -s "$BASE/api/v1/companies?cnpj=12345678000199" -H "Authorization: Bearer $READ" | jq -r '.items[0].id')
curl -s "$BASE/api/v1/companies/$CID/context" -H "Authorization: Bearer $READ" | jq
```

### "Interações recentes"

```bash
curl -s "$BASE/api/v1/interactions?since=2026-08-01T00:00:00Z&limit=50" -H "Authorization: Bearer $READ" | jq
```

### "Resultados de diagnósticos"

```bash
EID=$(curl -s "$BASE/api/v1/experiences" -H "Authorization: Bearer $READ" | jq -r '.items[0].id')
curl -s "$BASE/api/v1/experiences/$EID/runs" -H "Authorization: Bearer $READ" | jq '.items[].id'
curl -s "$BASE/api/v1/runs/$RUN_ID" -H "Authorization: Bearer $READ" | jq '.results'
```

## Exemplos (MCP)

```
tool get_person_context { "person_id": "…", "include": "identities,companies,scores" }
tool list_recent_interactions { "person_id": "…", "limit": 20 }
tool list_resolution_cases { "status": "open", "case_type": "identity_conflict" }
```

## Cliente Python mínimo

```python
from app.stack360.client import Stack360Client
c = Stack360Client("http://localhost:8010", api_key="st_...")
c.ingest_event({...})
c.get_person_context(person_id, include="identities,companies")
```
