"""Testes puros de `app/stack360/projection/legacy_whatsapp.py` (sem banco).

Cobrem especialmente a garantia de privacidade (texto da mensagem nunca
entra no evento de interação) e o encadeamento extração -> evento.
"""
from datetime import datetime, timezone

from app.stack360.projection.legacy_whatsapp import (
    RawMessage,
    build_extraction_events,
    build_interaction_event,
    is_our_number,
    normalize_jid_to_e164,
    resolve_subject_jid,
    should_process,
)


def _msg(**overrides) -> RawMessage:
    base = dict(
        external_message_id="ext-1",
        source_account_id="acc-1",
        instance_name="mgsuporte",
        whatsapp_message_id="wa-1",
        remote_jid="5511999998888@s.whatsapp.net",
        participant=None,
        from_me=False,
        push_name="Fulano",
        message_type="conversation",
        message_datetime=datetime(2026, 10, 1, tzinfo=timezone.utc),
        loaded_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        raw_message=None,
        text=None,
    )
    base.update(overrides)
    return RawMessage(**base)


class TestNormalizeJid:
    def test_simple_number(self):
        assert normalize_jid_to_e164("5511999998888@s.whatsapp.net") == "+5511999998888"

    def test_none(self):
        assert normalize_jid_to_e164(None) is None


class TestResolveSubject:
    def test_individual_uses_remote_jid(self):
        msg = _msg(remote_jid="5511999998888@s.whatsapp.net")
        assert resolve_subject_jid(msg) == "5511999998888@s.whatsapp.net"

    def test_group_uses_participant_not_group(self):
        msg = _msg(remote_jid="120363000@g.us", participant="5511988887777@s.whatsapp.net")
        assert resolve_subject_jid(msg) == "5511988887777@s.whatsapp.net"


class TestShouldProcess:
    def test_normal_message_processed(self):
        assert should_process(_msg()) is True

    def test_broadcast_skipped(self):
        assert should_process(_msg(remote_jid="status@broadcast")) is False

    def test_old_timestamp_skipped(self):
        assert should_process(_msg(message_datetime=datetime(1970, 1, 1, tzinfo=timezone.utc))) is False

    def test_reaction_skipped(self):
        assert should_process(_msg(message_type="reactionMessage")) is False


class TestInteractionPrivacy:
    def test_interaction_never_contains_text(self):
        msg = _msg(text="meu CNPJ é 12.345.678/0001-99 pode confirmar?")
        event = build_interaction_event(msg, "+5511999998888")
        serialized = str(event.data)
        assert "texto" not in event.data
        assert "text" not in event.data
        assert "12.345.678" not in serialized  # conteúdo da mensagem não vaza pro meta

    def test_interaction_has_source_ref_for_traceability(self):
        msg = _msg()
        event = build_interaction_event(msg, "+5511999998888")
        assert event.data["source_ref"] == "mgsuporte:ext-1"

    def test_sent_message_direction(self):
        msg = _msg(from_me=True)
        event = build_interaction_event(msg, "+5511999998888")
        assert event.event_type == "interaction.message_sent"
        assert event.data["direction"] == "outbound"


class TestExtractionPromotion:
    def test_third_party_cnpj_stays_weak_only(self):
        msg = _msg(text="Preciso de cotação pro CNPJ 12.345.678/0001-99 do destinatário")
        events = build_extraction_events(msg, "+5511999998888")
        types = [e.event_type for e in events]
        assert "observation.recorded" in types
        assert "identity.observed" not in types

    def test_self_declared_cnpj_promotes(self):
        msg = _msg(text="Bom dia, meu CNPJ é 12.345.678/0001-99")
        events = build_extraction_events(msg, "+5511999998888")
        identity_events = [e for e in events if e.event_type == "identity.observed"]
        assert len(identity_events) == 1
        idents = {i.type: i.value for i in identity_events[0].subject.identities}
        assert idents.get("cnpj") == "12345678000199"

    def test_self_declared_generic_webmail_does_not_promote(self):
        msg = _msg(text="meu e-mail é fulano@gmail.com")
        events = build_extraction_events(msg, "+5511999998888")
        assert all(e.event_type != "identity.observed" for e in events)
        assert any(e.event_type == "observation.recorded" for e in events)

    def test_self_declared_corporate_email_promotes(self):
        msg = _msg(text="meu e-mail é compras@clientereal.com.br")
        events = build_extraction_events(msg, "+5511999998888")
        assert any(e.event_type == "identity.observed" for e in events)

    def test_our_number_generates_no_events(self):
        msg = _msg(text="meu CNPJ é 12.345.678/0001-99")
        events = build_extraction_events(msg, "+5599992027458")  # número da própria instância
        assert events == []

    def test_no_text_generates_no_events(self):
        msg = _msg(text=None)
        assert build_extraction_events(msg, "+5511999998888") == []


class TestOurNumber:
    def test_known_instance_number(self):
        assert is_our_number("+5599992027458") is True

    def test_customer_number(self):
        assert is_our_number("+5511999998888") is False
