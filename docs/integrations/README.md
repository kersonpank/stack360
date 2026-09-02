# Stack360 — Integração

O Stack360 é a **camada canônica de dados e inteligência** (omnichannel data hub).
Qualquer fonte autorizada **alimenta**; qualquer consumidor autorizado **consulta**.
Ele organiza os dados em torno de: pessoas, identidades, empresas, relacionamentos,
interações, observações, experiências, execuções, respostas, resultados, scores e
**proveniência**.

O Stack360 **não é** CRM, campaign builder, sender de e-mail/WhatsApp, diagnostic
builder nem workflow engine. Ele **organiza e serve dados**.

## Índice

| Doc | Conteúdo |
|---|---|
| [quickstart.md](quickstart.md) | Integre um sistema novo em < 10 min |
| [rest-api.md](rest-api.md) | Autenticação, envelope, idempotência, endpoints de leitura, erros |
| [authentication.md](authentication.md) | API keys, scopes, workspace-from-key, revogação |
| [event-catalog.md](event-catalog.md) | Tipos de evento suportados (payload + entidades afetadas) |
| [webhooks.md](webhooks.md) | Inbound (implementado) e Outbound (contrato, fase seguinte) |
| [mcp.md](mcp.md) | Servidor MCP para agentes |
| [create-a-source.md](create-a-source.md) | Como conectar uma fonte nova sem tocar no core |
| [consume-stack360.md](consume-stack360.md) | REST vs MCP vs outbound; exemplos de consulta |
| [examples.md](examples.md) | Payloads completos e respostas |

## Conceitos de camada (RAW → FACT → KNOWLEDGE)

```
ingestion_event   dado bruto recebido (durável, replayável)
      │
      ├─ interaction     algo aconteceu
      ├─ answer          alguém declarou algo numa experiência
      ├─ observation     algo foi aprendido/inferido (append-only)
      ├─ result          saída de um motor/experiência (versionado)
      └─ score_history   métrica temporal
```

Conflitos e ambiguidades viram **`resolution_cases`** rastreáveis (nunca erros
descartados). IA = investigador/recomendador; Stack360/policy/humano = autoridade
de resolução.
