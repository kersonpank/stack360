from typing import Any, Dict, List, Set

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message

# psycopg2 suporta até 65535 parâmetros por statement
_MAX_PARAMS = 65535


def _dedup_contacts(rows: List[Dict]) -> List[Dict]:
    """Reduz múltiplas linhas com mesmo contact_id em uma só (merge aplicado)."""
    merged: Dict[str, Dict] = {}
    for r in rows:
        cid = r["contact_id"]
        if cid not in merged:
            merged[cid] = dict(r)
        else:
            m = merged[cid]
            # nome_atual: primeiro não-nulo
            if m["nome_atual"] is None:
                m["nome_atual"] = r["nome_atual"]
            # telefone: primeiro não-nulo
            if m["telefone"] is None:
                m["telefone"] = r["telefone"]
            # primeiro_contato_em: mínimo
            if r["primeiro_contato_em"] and m["primeiro_contato_em"]:
                m["primeiro_contato_em"] = min(m["primeiro_contato_em"], r["primeiro_contato_em"])
            # ultimo_contato_em: máximo
            if r["ultimo_contato_em"] and m["ultimo_contato_em"]:
                m["ultimo_contato_em"] = max(m["ultimo_contato_em"], r["ultimo_contato_em"])
    return list(merged.values())


def _dedup_conversations(rows: List[Dict]) -> List[Dict]:
    """Reduz múltiplas linhas com mesmo conversation_id em uma só."""
    merged: Dict[str, Dict] = {}
    for r in rows:
        cid = r["conversation_id"]
        if cid not in merged:
            merged[cid] = dict(r)
        else:
            m = merged[cid]
            if r["primeira_mensagem_em"] and m["primeira_mensagem_em"]:
                m["primeira_mensagem_em"] = min(m["primeira_mensagem_em"], r["primeira_mensagem_em"])
            if r["ultima_mensagem_em"] and m["ultima_mensagem_em"]:
                m["ultima_mensagem_em"] = max(m["ultima_mensagem_em"], r["ultima_mensagem_em"])
    return list(merged.values())


def _dedup_messages(rows: List[Dict]) -> List[Dict]:
    """Remove duplicatas por message_id (mantém a primeira ocorrência)."""
    seen: Set[str] = set()
    result = []
    for r in rows:
        mid = r["message_id"]
        if mid not in seen:
            seen.add(mid)
            result.append(r)
    return result


class NormalizationRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Métodos bulk (usados pelo worker) ---

    def bulk_upsert_contacts(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        deduped = _dedup_contacts(rows)
        num_cols = len(deduped[0])
        chunk_size = max(1, _MAX_PARAMS // num_cols)
        for i in range(0, len(deduped), chunk_size):
            chunk = deduped[i : i + chunk_size]
            stmt = pg_insert(Contact).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["contact_id"],
                set_={
                    "nome_atual": text(
                        "CASE "
                        "  WHEN contacts.nome_atual IS NULL OR contacts.nome_atual = '' "
                        "  THEN EXCLUDED.nome_atual "
                        "  ELSE contacts.nome_atual "
                        "END"
                    ),
                    "telefone": text("COALESCE(contacts.telefone, EXCLUDED.telefone)"),
                    "ultimo_contato_em": text(
                        "GREATEST(EXCLUDED.ultimo_contato_em, contacts.ultimo_contato_em)"
                    ),
                    "primeiro_contato_em": text(
                        "LEAST(EXCLUDED.primeiro_contato_em, contacts.primeiro_contato_em)"
                    ),
                    "updated_at": text("NOW()"),
                },
            )
            self.db.execute(stmt)

    def bulk_upsert_conversations(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        deduped = _dedup_conversations(rows)
        num_cols = len(deduped[0])
        chunk_size = max(1, _MAX_PARAMS // num_cols)
        for i in range(0, len(deduped), chunk_size):
            chunk = deduped[i : i + chunk_size]
            stmt = pg_insert(Conversation).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["conversation_id"],
                set_={
                    "ultima_mensagem_em": text(
                        "GREATEST(EXCLUDED.ultima_mensagem_em, conversations.ultima_mensagem_em)"
                    ),
                    "primeira_mensagem_em": text(
                        "LEAST(EXCLUDED.primeira_mensagem_em, conversations.primeira_mensagem_em)"
                    ),
                    "updated_at": text("NOW()"),
                },
            )
            self.db.execute(stmt)

    def bulk_upsert_messages(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        deduped = _dedup_messages(rows)
        num_cols = len(deduped[0])
        chunk_size = max(1, _MAX_PARAMS // num_cols)
        for i in range(0, len(deduped), chunk_size):
            chunk = deduped[i : i + chunk_size]
            stmt = pg_insert(Message).values(chunk)
            stmt = stmt.on_conflict_do_nothing(index_elements=["message_id"])
            self.db.execute(stmt)

    def bulk_recalculate_conversation_aggregates(self, conversation_ids: Set[str]) -> None:
        if not conversation_ids:
            return
        self.db.execute(
            text("""
                UPDATE conversations c
                SET
                    total_mensagens      = sub.total,
                    primeira_mensagem_em = sub.primeira,
                    ultima_mensagem_em   = sub.ultima,
                    updated_at           = NOW()
                FROM (
                    SELECT conversation_id,
                           COUNT(*)       AS total,
                           MIN(data_hora) AS primeira,
                           MAX(data_hora) AS ultima
                    FROM messages
                    WHERE conversation_id = ANY(:cids)
                    GROUP BY conversation_id
                ) sub
                WHERE c.conversation_id = sub.conversation_id
            """),
            {"cids": list(conversation_ids)},
        )

    def bulk_recalculate_contact_aggregates(self, contact_ids: Set[str]) -> None:
        if not contact_ids:
            return
        self.db.execute(
            text("""
                UPDATE contacts ct
                SET
                    total_mensagens     = sub.total,
                    primeiro_contato_em = sub.primeiro,
                    ultimo_contato_em   = sub.ultimo,
                    updated_at          = NOW()
                FROM (
                    SELECT contact_id,
                           COUNT(*)       AS total,
                           MIN(data_hora) AS primeiro,
                           MAX(data_hora) AS ultimo
                    FROM messages
                    WHERE contact_id = ANY(:cids)
                    GROUP BY contact_id
                ) sub
                WHERE ct.contact_id = sub.contact_id
            """),
            {"cids": list(contact_ids)},
        )

    # --- Métodos individuais (mantidos para compatibilidade) ---

    def upsert_contact(self, contact_data: Dict[str, Any]) -> None:
        stmt = pg_insert(Contact).values(**contact_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["contact_id"],
            set_={
                "nome_atual": text(
                    "CASE "
                    "  WHEN contacts.nome_atual IS NULL OR contacts.nome_atual = '' "
                    "  THEN EXCLUDED.nome_atual "
                    "  ELSE contacts.nome_atual "
                    "END"
                ),
                "telefone": text("COALESCE(contacts.telefone, EXCLUDED.telefone)"),
                "ultimo_contato_em": text(
                    "GREATEST(EXCLUDED.ultimo_contato_em, contacts.ultimo_contato_em)"
                ),
                "primeiro_contato_em": text(
                    "LEAST(EXCLUDED.primeiro_contato_em, contacts.primeiro_contato_em)"
                ),
                "updated_at": text("NOW()"),
            },
        )
        self.db.execute(stmt)

    def upsert_conversation(self, conv_data: Dict[str, Any]) -> None:
        stmt = pg_insert(Conversation).values(**conv_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["conversation_id"],
            set_={
                "ultima_mensagem_em": text(
                    "GREATEST(EXCLUDED.ultima_mensagem_em, conversations.ultima_mensagem_em)"
                ),
                "primeira_mensagem_em": text(
                    "LEAST(EXCLUDED.primeira_mensagem_em, conversations.primeira_mensagem_em)"
                ),
                "updated_at": text("NOW()"),
            },
        )
        self.db.execute(stmt)

    def upsert_message(self, msg_data: Dict[str, Any]) -> None:
        stmt = pg_insert(Message).values(**msg_data)
        stmt = stmt.on_conflict_do_nothing(index_elements=["message_id"])
        self.db.execute(stmt)

    def recalculate_conversation_aggregates(self, conversation_id: str) -> None:
        self.db.execute(
            text("""
                UPDATE conversations
                SET
                    total_mensagens      = (SELECT COUNT(*)        FROM messages WHERE conversation_id = :cid),
                    primeira_mensagem_em = (SELECT MIN(data_hora)  FROM messages WHERE conversation_id = :cid),
                    ultima_mensagem_em   = (SELECT MAX(data_hora)  FROM messages WHERE conversation_id = :cid),
                    updated_at           = NOW()
                WHERE conversation_id = :cid
            """),
            {"cid": conversation_id},
        )

    def recalculate_contact_aggregates(self, contact_id: str) -> None:
        self.db.execute(
            text("""
                UPDATE contacts
                SET
                    total_mensagens      = (SELECT COUNT(*)        FROM messages WHERE contact_id = :cid),
                    primeiro_contato_em  = (SELECT MIN(data_hora)  FROM messages WHERE contact_id = :cid),
                    ultimo_contato_em    = (SELECT MAX(data_hora)  FROM messages WHERE contact_id = :cid),
                    updated_at           = NOW()
                WHERE contact_id = :cid
            """),
            {"cid": contact_id},
        )
