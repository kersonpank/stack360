export type FieldType =
  | "text"
  | "number"
  | "boolean"
  | "date"
  | "percent"
  | "currency"
  | "phone"
  | "email"
  | "document"
  | "enum"
  | "json";

export type ObservationKeyDef = {
  key: string;
  label: string;
  type: FieldType;
  group: string;
  /** Texto estático de configuração — nunca calculado em runtime. */
  expectedSourceHint?: string;
  enumLabels?: Record<string, string>;
};

export type ScoreKeyDef = {
  key: string;
  label: string;
  type: "number" | "percent";
  bandLabels?: Record<string, string>;
  bandTone?: Record<string, "default" | "yellow" | "red" | "blue" | "dark">;
};
