import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/testdb")
os.environ.setdefault("API_ENV", "testing")

import pytest

from app.utils.whatsapp_normalizer import (
    build_conversation_id,
    extract_text,
    get_chat_type,
    is_useful_push_name,
    normalize_phone_from_jid,
    parse_json_if_needed,
    resolve_contact_id,
)


# --- normalize_phone_from_jid ---


def test_normalize_phone_individual():
    assert normalize_phone_from_jid("5511999990000@s.whatsapp.net") == "5511999990000"


def test_normalize_phone_strips_device_suffix():
    assert normalize_phone_from_jid("5511999990000:0@s.whatsapp.net") == "5511999990000"


def test_normalize_phone_group_returns_none():
    assert normalize_phone_from_jid("120363000000000000@g.us") is None


def test_normalize_phone_broadcast_returns_none():
    assert normalize_phone_from_jid("status@broadcast") is None


def test_normalize_phone_non_numeric_returns_none():
    # JID com parte não-numérica não é telefone válido
    assert normalize_phone_from_jid("abc@s.whatsapp.net") is None


# --- get_chat_type ---


def test_chat_type_individual():
    assert get_chat_type("5511999990000@s.whatsapp.net") == "individual"


def test_chat_type_group():
    assert get_chat_type("120363000000000000@g.us") == "grupo"


def test_chat_type_broadcast():
    assert get_chat_type("status@broadcast") == "broadcast"


def test_chat_type_lid():
    assert get_chat_type("abc123@lid") == "lid"


def test_chat_type_unknown():
    assert get_chat_type("something_else") == "desconhecido"


# --- resolve_contact_id ---


def test_contact_id_individual_phone():
    cid = resolve_contact_id(
        remote_jid="5599999999999@s.whatsapp.net",
        participant=None,
        raw_key=None,
        external_message_id="EXT1",
    )
    assert cid == "5599999999999"


def test_contact_id_same_person_different_accounts():
    id1 = resolve_contact_id("5599999999999@s.whatsapp.net", None, None, "E1")
    id2 = resolve_contact_id("5599999999999@s.whatsapp.net", None, None, "E2")
    assert id1 == id2 == "5599999999999"


def test_contact_id_group_with_participant_phone():
    cid = resolve_contact_id(
        remote_jid="120363000@g.us",
        participant="5588888888888@s.whatsapp.net",
        raw_key=None,
        external_message_id="E1",
    )
    assert cid == "5588888888888"


def test_contact_id_group_no_participant():
    cid = resolve_contact_id(
        remote_jid="5599999990003-1617218121@g.us",
        participant=None,
        raw_key=None,
        external_message_id="E1",
    )
    assert cid == "group:5599999990003-1617218121"


def test_contact_id_group_raw_key_participant_pn():
    # raw_key com participantPn contendo telefone real
    raw_key = {"participantPn": "5588888888888@s.whatsapp.net", "remoteJid": "120@g.us"}
    cid = resolve_contact_id("120@g.us", None, raw_key, "E1")
    assert cid == "5588888888888"


def test_contact_id_lid():
    cid = resolve_contact_id("abc123@lid", None, None, "E1")
    assert cid == "lid:abc123"


def test_contact_id_broadcast():
    cid = resolve_contact_id("status@broadcast", None, None, "E1")
    assert cid == "broadcast:status"


def test_contact_id_fallback():
    cid = resolve_contact_id("unknown_jid", None, None, "EXT_FALLBACK")
    assert cid == "unknown:EXT_FALLBACK"


def test_contact_id_individual_raw_key_sender_pn_not_used():
    # Bug crítico: senderPn em from_me=True é o dono da conta, não o contato remoto
    raw_key = {"senderPn": "5511999990001@s.whatsapp.net", "remoteJid": "5577999990002@s.whatsapp.net"}
    cid = resolve_contact_id(
        remote_jid="5577999990002@s.whatsapp.net",
        participant=None,
        raw_key=raw_key,
        external_message_id="EXT1",
    )
    assert cid == "5577999990002"


def test_contact_id_lid_uses_sender_pn_from_raw_key():
    # @lid sem telefone no JID → buscar em raw_key.senderPn
    raw_key = {"senderPn": "5511999990001@s.whatsapp.net"}
    cid = resolve_contact_id(
        remote_jid="abc123@lid",
        participant=None,
        raw_key=raw_key,
        external_message_id="EXT1",
    )
    assert cid == "5511999990001"


def test_contact_id_group_sender_is_participant_not_group():
    # Para grupos: resolve_contact_id retorna o sender (participant), não group:<id>
    # conversation_contact_id = "group:120363000" é definido por _build_rows separadamente
    cid = resolve_contact_id(
        remote_jid="120363000@g.us",
        participant="5588888888888@s.whatsapp.net",
        raw_key=None,
        external_message_id="E1",
    )
    assert cid == "5588888888888"


# --- build_conversation_id ---


def test_conversation_id_format():
    cid = build_conversation_id("acc_01", "5599999999999@s.whatsapp.net")
    assert cid == "acc_01:5599999999999@s.whatsapp.net"


def test_conversation_id_group():
    cid = build_conversation_id("acc_01", "120363000@g.us")
    assert cid == "acc_01:120363000@g.us"


# --- is_useful_push_name ---


def test_push_name_useful_real_name():
    assert is_useful_push_name("João Silva") is True


def test_push_name_useful_business_name():
    assert is_useful_push_name("Transportadora Stack360Empresas") is True


def test_push_name_filters_voce():
    assert is_useful_push_name("Você") is False


def test_push_name_filters_voce_ascii():
    assert is_useful_push_name("Voce") is False


def test_push_name_filters_none():
    assert is_useful_push_name(None) is False


def test_push_name_filters_empty():
    assert is_useful_push_name("") is False


def test_push_name_filters_pure_number():
    assert is_useful_push_name("5599999999999") is False


def test_push_name_filters_jid_like():
    assert is_useful_push_name("5599999999999@s.whatsapp.net") is False


def test_push_name_filters_lid_number():
    # push_name de grupo com número lid (>12 dígitos)
    assert is_useful_push_name("149155674611828") is False


# --- extract_text (raw_message é o JSONB direto da mensagem) ---


def test_extract_text_conversation():
    assert extract_text({"conversation": "Olá, mundo!"}) == "Olá, mundo!"


def test_extract_text_extended():
    assert extract_text({"extendedTextMessage": {"text": "Texto longo"}}) == "Texto longo"


def test_extract_text_image_caption():
    assert extract_text({"imageMessage": {"caption": "Foto da reunião"}}) == "Foto da reunião"


def test_extract_text_video_caption():
    assert extract_text({"videoMessage": {"caption": "Vídeo"}}) == "Vídeo"


def test_extract_text_document_caption():
    assert extract_text({"documentMessage": {"caption": "Documento"}}) == "Documento"


def test_extract_text_document_filename_fallback():
    assert extract_text({"documentMessage": {"fileName": "contrato.pdf"}}) == "contrato.pdf"


def test_extract_text_contact_display_name():
    assert extract_text({"contactMessage": {"displayName": "João Silva"}}) == "João Silva"


def test_extract_text_none_for_empty():
    assert extract_text({}) is None
    assert extract_text(None) is None


def test_extract_text_protocol_message_returns_none():
    # mensagens de protocolo não têm texto útil
    assert extract_text({"protocolMessage": {"type": 0}}) is None


# --- parse_json_if_needed ---


def test_parse_json_dict_passthrough():
    d = {"key": "val"}
    assert parse_json_if_needed(d) == d


def test_parse_json_from_string():
    import json

    s = json.dumps({"key": "val"})
    assert parse_json_if_needed(s) == {"key": "val"}


def test_parse_json_none():
    assert parse_json_if_needed(None) is None


def test_parse_json_invalid_string_passthrough():
    assert parse_json_if_needed("not json") == "not json"
