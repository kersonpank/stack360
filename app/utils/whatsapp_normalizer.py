import json
from typing import Any, Optional


def parse_json_if_needed(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def normalize_phone_from_jid(jid: str) -> Optional[str]:
    """Extrai telefone puro de um JID @s.whatsapp.net. Retorna None se não for individual com telefone."""
    if not jid or "@s.whatsapp.net" not in jid:
        return None
    user_part = jid.split("@")[0].split(":")[0]
    return user_part if user_part.isdigit() else None


def get_chat_type(remote_jid: str) -> str:
    if not remote_jid:
        return "desconhecido"
    if remote_jid.endswith("@s.whatsapp.net"):
        return "individual"
    if remote_jid.endswith("@g.us"):
        return "grupo"
    if remote_jid.endswith("@lid"):
        return "lid"
    if remote_jid == "status@broadcast":
        return "broadcast"
    return "desconhecido"


def is_useful_push_name(push_name: Optional[str]) -> bool:
    """Retorna True se push_name é um nome real útil para gravar em nome_atual."""
    if not push_name or not push_name.strip():
        return False

    name = push_name.strip()

    # Filtrar "Você" e variações sem acento
    normalized = name.lower()
    if normalized in ("você", "voce", "vc"):
        return False

    # Filtrar strings puramente numéricas (telefones, lids)
    if name.isdigit():
        return False

    # Filtrar números longos com separadores (e.g. 149155674611828)
    digits_only = name.replace("-", "").replace("+", "").replace(" ", "")
    if digits_only.isdigit() and len(digits_only) > 6:
        return False

    # Filtrar JIDs
    if "@" in name:
        return False

    # Filtrar nomes muito curtos (1 char)
    if len(name) < 2:
        return False

    return True


def resolve_contact_id(
    remote_jid: str,
    participant: Optional[str],
    raw_key: Optional[Any],
    external_message_id: str,
) -> str:
    """
    Retorna contact_id global baseado em telefone real quando possível.
    A mesma pessoa em canais diferentes deve sempre ter o mesmo contact_id.

    Prioridade por tipo de JID:
      @g.us      → participant phone > raw_key.participantPn > group:<id>
      @s.whatsapp.net → telefone do remote_jid SEMPRE (nunca senderPn)
      @lid       → raw_key.senderPn/previousRemoteJid > lid:<id>
      broadcast  → broadcast:status
      outro      → unknown:<external_message_id>
    """
    if not remote_jid:
        return f"unknown:{external_message_id}"

    # Grupos: o contato é o sender (participant), não o grupo
    if remote_jid.endswith("@g.us"):
        group_id = remote_jid.split("@")[0]

        if participant:
            phone = normalize_phone_from_jid(participant)
            if phone:
                return phone
            user = participant.split("@")[0].split(":")[0]
            domain = participant.split("@")[1] if "@" in participant else ""
            if domain == "lid":
                return f"lid:{user}"

        if raw_key:
            rk = parse_json_if_needed(raw_key)
            if isinstance(rk, dict):
                for field in ("participantPn", "participant"):
                    jid_candidate = rk.get(field)
                    if jid_candidate and "@s.whatsapp.net" in str(jid_candidate):
                        phone = normalize_phone_from_jid(str(jid_candidate))
                        if phone:
                            return phone

        return f"group:{group_id}"

    # Individual: SEMPRE usa remote_jid — nunca senderPn/previousRemoteJid do raw_key
    # (senderPn em from_me=True é o telefone do dono da conta, não do contato)
    if remote_jid.endswith("@s.whatsapp.net"):
        phone = normalize_phone_from_jid(remote_jid)
        if phone:
            return phone
        user_part = remote_jid.split("@")[0].split(":")[0]
        return user_part if user_part else f"unknown:{external_message_id}"

    # @lid: tentar resolver telefone real via raw_key
    if remote_jid.endswith("@lid"):
        lid_id = remote_jid.split("@")[0]
        if raw_key:
            rk = parse_json_if_needed(raw_key)
            if isinstance(rk, dict):
                for field in ("senderPn", "previousRemoteJid"):
                    jid_candidate = rk.get(field)
                    if jid_candidate and "@s.whatsapp.net" in str(jid_candidate):
                        phone = normalize_phone_from_jid(str(jid_candidate))
                        if phone:
                            return phone
        return f"lid:{lid_id}"

    # broadcast
    if remote_jid == "status@broadcast":
        return "broadcast:status"

    return f"unknown:{external_message_id}"


def build_conversation_id(source_account_id: str, remote_jid: str) -> str:
    return f"{source_account_id}:{remote_jid}"


def extract_text(raw_message: Any) -> Optional[str]:
    """
    Extrai texto de raw_message (JSONB direto do conteúdo da mensagem —
    não encapsulado em {'message': ...}).
    """
    if not raw_message:
        return None
    msg = parse_json_if_needed(raw_message)
    if not isinstance(msg, dict):
        return None

    if "conversation" in msg:
        return msg["conversation"] or None
    if "extendedTextMessage" in msg:
        return (msg["extendedTextMessage"] or {}).get("text")
    if "imageMessage" in msg:
        return (msg["imageMessage"] or {}).get("caption")
    if "videoMessage" in msg:
        return (msg["videoMessage"] or {}).get("caption")
    if "documentMessage" in msg:
        doc = msg["documentMessage"] or {}
        return doc.get("caption") or doc.get("title") or doc.get("fileName")
    if "contactMessage" in msg:
        return (msg["contactMessage"] or {}).get("displayName")
    if "contactsArrayMessage" in msg:
        return (msg["contactsArrayMessage"] or {}).get("displayName")
    return None
