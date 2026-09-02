# Webhooks

## INBOUND (implementado) — serviços externos → Stack360

Para fontes que só sabem "mandar um POST". Nenhum adapter de serviço específico
(Gmail/Instagram/WhatsApp/…) é implementado nesta fase — só a **infra**:

```
raw webhook  ──►  adapter (por source_type)  ──►  StackEvent (envelope universal)  ──►  gateway
```

### Configurar um endpoint

```bash
python -m app.stack360.admin create-webhook-endpoint \
  --workspace stack360-empresas --source minha-app --source-key minha-app-hook \
  [--signature-header X-Signature] [--signature-scheme hmac-sha256]

python -m app.stack360.admin list-webhook-endpoints
python -m app.stack360.admin disable-webhook-endpoint --source-key minha-app-hook
python -m app.stack360.admin rotate-webhook-secret  --source-key minha-app-hook   # se HMAC disponível
```

O endpoint pertence a **exatamente uma `data_source`** e ao mesmo workspace.

### Enviar

`POST /api/v1/webhooks/{source_key}` com o corpo cru do serviço externo.

Autenticação (uma das):

1. **API key source-bound** no header `Authorization: Bearer st_...`. O Stack360
   valida `api_key.workspace_id == endpoint.workspace_id` **E**
   `api_key.data_source_id == endpoint.data_source_id`. Uma key da Source A **não**
   publica no endpoint da Source B (mesmo no mesmo workspace).
2. **HMAC** — `hmac-sha256` do corpo cru vs o header configurado. O segredo é
   **cifrado at-rest** (AES-GCM, master key `STACK360_WEBHOOK_SECRET_KEY`),
   decifrado só em memória para validar. **Nunca** plaintext; **nunca** hash
   irreversível para "validar" HMAC.

> **Decisão efetiva nesta rodada:** o segredo HMAC é cifrado at-rest quando
> `STACK360_WEBHOOK_SECRET_KEY` está definido e `cryptography` disponível
> (opção A). Caso contrário, HMAC configurável **não** é implementado e o
> webhook aceita apenas API key source-bound (opção C). Adapters de assinatura
> provider-specific ficam para fase posterior.

### Adapter `passthrough` (v1)

`mapping` (coluna `webhook_endpoints.mapping`, JSON) aceita:

| chave | efeito |
|---|---|
| `event_type` | event_type fixo (default `"webhook.received"`) |
| `event_id_path` | caminho pontilhado no JSON para o id externo (idempotência); ausente → `sha256(source_key + body)` |
| `occurred_at_path` | caminho pontilhado para o timestamp; ausente → `now()` |

O corpo cru vira `data` do StackEvent. Se o `event_type` resolvido tem handler,
processa; senão o `ingestion_event` fica `pending` para um handler/adapter futuro.

---

## OUTBOUND (contrato — **fase seguinte**, não implementado)

Stack360 → consumidores reativos. **Nada é entregue nesta rodada** (sem engine,
sem tabelas `webhook_subscriptions`/`webhook_deliveries`, sem UI). Contrato-alvo:

### Eventos

`person.created` · `person.updated` · `identity.linked` · `company.created` ·
`observation.created` · `interaction.created` · `experience.completed` ·
`score.created`

### Envelope de entrega (proposto)

```jsonc
{
  "delivery_id": "uuid",                 // idempotency identifier
  "event": "person.created",
  "occurred_at": "…",
  "workspace": "stack360-empresas",
  "data": { /* entidade canônica */ }
}
```

### Requisitos (proposto)

- **HMAC-SHA256** do corpo cru no header `X-Stack360-Signature`, segredo por subscription.
- **Retry** com backoff exponencial (ex. 1m, 5m, 30m, 2h, 6h) até N tentativas.
- **`delivery status`** persistido por tentativa (`pending`/`delivered`/`failed`/`dropped`).
- **Idempotência** no consumidor via `delivery_id`.
- Sem workflow engine.
