from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.raw_evolution_message import RawEvolutionMessage
from app.repositories.normalization_repository import NormalizationRepository
from app.repositories.raw_message_repository import RawMessageRepository
from app.utils.whatsapp_normalizer import (
    build_conversation_id,
    extract_text,
    get_chat_type,
    is_useful_push_name,
    normalize_phone_from_jid,
    parse_json_if_needed,
    resolve_contact_id,
)


def _build_rows(raw: RawEvolutionMessage):
    """
    Retorna (contact_row, conv_row, msg_row, conversation_contact_id, sender_contact_id).

    Para grupos:
      - conversation.contact_id = group:<id>  (representa o grupo)
      - message.contact_id = sender_contact_id (quem enviou; pode ser o grupo se não identificado)
    Para individuais:
      - ambos usam o mesmo contact_id (telefone puro)
    """
    raw_message = parse_json_if_needed(raw.raw_message)
    raw_key = parse_json_if_needed(raw.raw_key)
    source_account_id = raw.source_account_id or raw.instance_name or "unknown"
    remote_jid = raw.remote_jid or ""
    external_message_id = raw.external_message_id or raw.whatsapp_message_id or ""

    # Identificar sender e grupo separadamente
    sender_contact_id = resolve_contact_id(
        remote_jid=remote_jid,
        participant=raw.participant,
        raw_key=raw_key,
        external_message_id=external_message_id,
    )

    is_group = remote_jid.endswith("@g.us")
    if is_group:
        group_id = remote_jid.split("@")[0]
        conversation_contact_id = f"group:{group_id}"
    else:
        conversation_contact_id = sender_contact_id

    conversation_id = build_conversation_id(source_account_id, remote_jid)
    message_id = external_message_id

    # Timestamp
    data_hora = raw.message_datetime
    if data_hora is None and raw.message_timestamp and raw.message_timestamp > 0:
        data_hora = datetime.fromtimestamp(raw.message_timestamp, tz=timezone.utc)

    chat_type = get_chat_type(remote_jid)
    texto = extract_text(raw_message)
    now = datetime.now(tz=timezone.utc)

    # Telefone do contato (para individuais; None para grupos/lid/broadcast)
    telefone = normalize_phone_from_jid(remote_jid) if not is_group else None

    # Para mensagens de grupo enviadas pelo account (from_me=True), sender pode ser
    # o grupo se não houver participant. Manter como está (group:<id>).

    # Nome do contato — filtrar push_names inúteis
    nome_util = raw.push_name if is_useful_push_name(raw.push_name) else None

    # contact_id principal do sender (para upsert em contacts)
    # Se sender_contact_id é group:<id>, não criar contato individual para o grupo
    contact_row = {
        "contact_id": sender_contact_id,
        "telefone": telefone if not sender_contact_id.startswith("group:") else None,
        "nome_atual": nome_util,
        "tipo_relacionamento": "unknown",
        "status_relacionamento": "active",
        "primeiro_contato_em": data_hora,
        "ultimo_contato_em": data_hora,
        "total_mensagens": 0,
        "score_oportunidade": 0,
        "score_risco": 0,
        "tags": ["whatsapp"],
        "resumo_geral": None,
        "created_at": now,
        "updated_at": now,
    }

    # Se é grupo e conversation_contact_id != sender_contact_id, criar também
    # um registro para o grupo em contacts (caso não exista) — só se diferentes
    group_contact_row = None
    if is_group and conversation_contact_id != sender_contact_id:
        group_contact_row = {
            "contact_id": conversation_contact_id,
            "telefone": None,
            "nome_atual": None,
            "tipo_relacionamento": "group",
            "status_relacionamento": "active",
            "primeiro_contato_em": data_hora,
            "ultimo_contato_em": data_hora,
            "total_mensagens": 0,
            "score_oportunidade": 0,
            "score_risco": 0,
            "tags": ["whatsapp", "group"],
            "resumo_geral": None,
            "created_at": now,
            "updated_at": now,
        }

    conv_row = {
        "conversation_id": conversation_id,
        "contact_id": conversation_contact_id,
        "source_account_id": source_account_id,
        "remote_jid": remote_jid,
        "tipo_chat": chat_type,
        "primeira_mensagem_em": data_hora,
        "ultima_mensagem_em": data_hora,
        "total_mensagens": 0,
        "assunto_principal": None,
        "resumo_conversa": None,
        "status_conversa": "active",
        "created_at": now,
        "updated_at": now,
    }

    # Telefone do sender para a mensagem (mesmo que o grupo não tenha)
    if sender_contact_id.isdigit():
        msg_telefone = sender_contact_id
    else:
        msg_telefone = telefone

    msg_row = {
        "message_id": message_id,
        "external_message_id": external_message_id,
        "conversation_id": conversation_id,
        "contact_id": sender_contact_id,
        "source_account_id": source_account_id,
        "data_hora": data_hora,
        "message_timestamp": raw.message_timestamp,
        "remote_jid": remote_jid,
        "canonical_jid": remote_jid,
        "telefone": msg_telefone,
        "enviada_por_mim": raw.from_me,
        "nome_contato": nome_util,
        "tipo_mensagem": raw.message_type,
        "status": raw.status or "received",
        "source": raw.source or "evolution",
        "texto": texto,
        "raw_message": raw_message,
        "enriched_at": None,
        "created_at": now,
    }

    return contact_row, group_contact_row, conv_row, msg_row, conversation_contact_id, sender_contact_id


class NormalizationService:
    def __init__(self, read_db: Session, write_db: Session):
        self.read_db = read_db
        self.write_db = write_db
        self.raw_repo = RawMessageRepository(read_db)
        self.norm_repo = NormalizationRepository(write_db)

    def run(
        self,
        limit: int = 100,
        dry_run: bool = False,
        source_account_id: Optional[str] = None,
    ) -> dict:
        raws = self.raw_repo.fetch_pending(limit=limit, source_account_id=source_account_id)
        print(f"[worker] {len(raws)} mensagens raw pendentes encontradas.", flush=True)

        if not raws:
            return {"processed": 0, "dry_run": dry_run, "total_found": 0}

        # Fechar a transação de leitura antes de escrever.
        # Evita que a SELECT transaction aberta bloqueie INSERT ON CONFLICT.
        # Os objetos já têm todos os campos carregados (raw_full deferiu), então
        # permanecem acessíveis após expunge.
        self.read_db.expunge_all()
        self.read_db.close()

        processed_ext_ids: List[str] = []
        conversation_ids_to_recalc: set = set()
        contact_ids_to_recalc: set = set()

        all_contact_rows: List[Dict[str, Any]] = []
        all_conv_rows: List[Dict[str, Any]] = []
        all_msg_rows: List[Dict[str, Any]] = []

        # Dry-run: rastrear únicos para estimativa
        dry_contact_ids: set = set()
        dry_conversation_ids: set = set()
        verbose_dry = len(raws) <= 20

        for i, raw in enumerate(raws):
            contact_row, group_contact_row, conv_row, msg_row, conv_contact_id, sender_contact_id = _build_rows(raw)

            if dry_run:
                dry_contact_ids.add(sender_contact_id)
                if conv_contact_id != sender_contact_id:
                    dry_contact_ids.add(conv_contact_id)
                dry_conversation_ids.add(conv_row["conversation_id"])

                if verbose_dry:
                    print(f"  [DRY-RUN] external_message_id = {raw.external_message_id}")
                    print(f"            sender contact_id   = {sender_contact_id}")
                    print(f"            conv contact_id     = {conv_contact_id}")
                    print(f"            conversation_id     = {conv_row['conversation_id']}")
                    print(f"            message_id          = {msg_row['message_id']}")
                    print(f"            tipo_chat           = {conv_row['tipo_chat']}")
                    print(f"            texto               = {msg_row['texto']!r}")
                    print(f"            nome_contato        = {msg_row['nome_contato']!r}")
                    print()
                elif i == 0 or (i + 1) % 500 == 0 or (i + 1) == len(raws):
                    print(f"  [DRY-RUN] {i + 1}/{len(raws)} processadas (simulado)...")
            else:
                all_contact_rows.append(contact_row)
                if group_contact_row:
                    all_contact_rows.append(group_contact_row)
                all_conv_rows.append(conv_row)
                all_msg_rows.append(msg_row)
                conversation_ids_to_recalc.add(conv_row["conversation_id"])
                contact_ids_to_recalc.add(sender_contact_id)
                if conv_contact_id != sender_contact_id:
                    contact_ids_to_recalc.add(conv_contact_id)
                processed_ext_ids.append(raw.external_message_id)

        if not dry_run:
            print(f"[worker] bulk_upsert_contacts: {len(all_contact_rows)} rows...", flush=True)
            self.norm_repo.bulk_upsert_contacts(all_contact_rows)
            print(f"[worker] bulk_upsert_contacts: OK", flush=True)

            print(f"[worker] bulk_upsert_conversations: {len(all_conv_rows)} rows...", flush=True)
            self.norm_repo.bulk_upsert_conversations(all_conv_rows)
            print(f"[worker] bulk_upsert_conversations: OK", flush=True)

            print(f"[worker] bulk_upsert_messages: {len(all_msg_rows)} rows...", flush=True)
            self.norm_repo.bulk_upsert_messages(all_msg_rows)
            print(f"[worker] bulk_upsert_messages: OK", flush=True)

            print(f"[worker] recalc conversations: {len(conversation_ids_to_recalc)}...", flush=True)
            self.norm_repo.bulk_recalculate_conversation_aggregates(conversation_ids_to_recalc)
            print(f"[worker] recalc conversations: OK", flush=True)

            print(f"[worker] recalc contacts: {len(contact_ids_to_recalc)}...", flush=True)
            self.norm_repo.bulk_recalculate_contact_aggregates(contact_ids_to_recalc)
            print(f"[worker] recalc contacts: OK", flush=True)

            self.write_db.commit()
            print(f"[worker] commit OK", flush=True)

            marked = self.raw_repo.mark_normalized(self.write_db, processed_ext_ids)
            self.write_db.commit()
            print(f"[worker] {marked} registros marcados como normalized_at.", flush=True)

        result = {
            "processed": len(processed_ext_ids),
            "dry_run": dry_run,
            "total_found": len(raws),
            "conversations_recalculated": len(conversation_ids_to_recalc) if not dry_run else 0,
            "contacts_recalculated": len(contact_ids_to_recalc) if not dry_run else 0,
        }
        if dry_run:
            result["estimated_unique_contacts"] = len(dry_contact_ids)
            result["estimated_unique_conversations"] = len(dry_conversation_ids)
            result["estimated_messages"] = len(raws)

        return result
