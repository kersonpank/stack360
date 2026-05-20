-- ============================================================
-- Schema fix: contact_evidence — adicionar colunas e índices
-- Executar como superuser (postgres) no banco:
--   memory_operation_group_evo_whatsapp
--
-- Idempotente: seguro rodar múltiplas vezes.
-- ============================================================

ALTER TABLE contact_evidence ADD COLUMN IF NOT EXISTS conversation_id text;
ALTER TABLE contact_evidence ADD COLUMN IF NOT EXISTS payload jsonb DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS ix_contact_evidence_contact_id
    ON contact_evidence(contact_id);

CREATE INDEX IF NOT EXISTS ix_contact_evidence_evidence_type
    ON contact_evidence(evidence_type);

CREATE INDEX IF NOT EXISTS ix_contact_evidence_conversation_id
    ON contact_evidence(conversation_id);

CREATE INDEX IF NOT EXISTS ix_contact_evidence_message_id
    ON contact_evidence(message_id);
