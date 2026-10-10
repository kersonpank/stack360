import type { ObservationKeyDef } from "./types";

// `observation.key` é livre no backend (sem enum) — este registro é a ÚNICA
// fonte de rótulos do frontend, curada manualmente. Chave desconhecida cai no
// fallback de getObservationKeyDef (mostra a própria chave técnica, nunca
// esconde nem adivinha).
export const OBSERVATION_KEYS: Record<string, ObservationKeyDef> = {
  "relationship.tsm": {
    key: "relationship.tsm",
    label: "Relacionamento",
    type: "enum",
    group: "comercial",
    expectedSourceHint: "Worker de enriquecimento (legado) ou fonte equivalente",
    enumLabels: {
      desconhecido: "Desconhecido",
      lead: "Lead",
      motorista: "Motorista",
      fornecedor: "Fornecedor",
      cliente: "Cliente",
      grupo: "Grupo",
    },
  },
  summary: {
    key: "summary",
    label: "Resumo",
    type: "text",
    group: "comercial",
    expectedSourceHint: "Worker de enriquecimento (legado) ou fonte equivalente",
  },
  document_number: {
    key: "document_number",
    label: "CPF/CNPJ",
    type: "document",
    group: "identidade",
  },
  company_role: {
    key: "company_role",
    label: "Papel na empresa",
    type: "text",
    group: "comercial",
  },
};

export const PRIORITY_PERSON_OBSERVATION_KEYS: string[] = ["relationship.tsm", "summary"];
export const PRIORITY_COMPANY_OBSERVATION_KEYS: string[] = ["summary"];

export function getObservationKeyDef(key: string): ObservationKeyDef {
  return (
    OBSERVATION_KEYS[key] ?? {
      key,
      label: key,
      type: "text",
      group: "outros",
    }
  );
}
