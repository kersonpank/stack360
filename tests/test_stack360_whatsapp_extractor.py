"""Testes puros do extractor de WhatsApp (sem banco).

Cobrem especialmente a garantia de privacidade (texto da mensagem nunca
entra no evento de interação) e o encadeamento extração -> evento.
"""
import dataclasses
from datetime import datetime, timezone

from app.stack360.projection.envelope import SourceEnvelope
from app.stack360.projection.extractors.whatsapp_message import (
    extract,
    is_our_number,
    normalize_jid_to_e164,
    resolve_subject_jid,
)
from app.stack360.projection.readers.whatsapp_legacy import ENVELOPE_TYPE


def _envelope(**content_overrides) -> SourceEnvelope:
    content = dict(
        external_message_id="ext-1",
        source_account_id="acc-1",
        instance_name="mgsuporte",
        whatsapp_message_id="wa-1",
        remote_jid="5511999998888@s.whatsapp.net",
        participant=None,
        from_me=False,
        push_name="Fulano",
        message_type="conversation",
        raw_message=None,
    )
    content.update(content_overrides)
    return SourceEnvelope(
        source_key="mgsuporte",
        envelope_type=ENVELOPE_TYPE,
        external_key=content["whatsapp_message_id"],
        content=content,
        captured_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )


def _with_text(text: str, **overrides) -> SourceEnvelope:
    return _envelope(raw_message={"conversation": text}, **overrides)


class TestNormalizeJid:
    def test_simple_number(self):
        assert normalize_jid_to_e164("5511999998888@s.whatsapp.net") == "+5511999998888"

    def test_none(self):
        assert normalize_jid_to_e164(None) is None


class TestResolveSubject:
    def test_individual_uses_remote_jid(self):
        content = {"remote_jid": "5511999998888@s.whatsapp.net", "participant": None}
        assert resolve_subject_jid(content) == "5511999998888@s.whatsapp.net"

    def test_group_uses_participant_not_group(self):
        content = {"remote_jid": "120363000@g.us", "participant": "5511988887777@s.whatsapp.net"}
        assert resolve_subject_jid(content) == "5511988887777@s.whatsapp.net"


class TestFilters:
    def test_broadcast_generates_no_events(self):
        envelope = _envelope(remote_jid="status@broadcast")
        assert extract(envelope) == []

    def test_old_timestamp_generates_no_events(self):
        envelope = dataclasses.replace(_envelope(), captured_at=datetime(1970, 1, 1, tzinfo=timezone.utc))
        assert extract(envelope) == []

    def test_reaction_generates_no_events(self):
        envelope = _envelope(message_type="reactionMessage")
        assert extract(envelope) == []


class TestInteractionPrivacy:
    def test_interaction_never_contains_text(self):
        envelope = _with_text("meu CNPJ é 12.345.678/0001-99 pode confirmar?")
        events = extract(envelope)
        interaction = next(e for e in events if e.event_type.startswith("interaction."))
        serialized = str(interaction.data)
        assert "texto" not in interaction.data
        assert "text" not in interaction.data
        assert "12.345.678" not in serialized

    def test_interaction_has_source_ref_for_traceability(self):
        envelope = _envelope()
        events = extract(envelope)
        interaction = next(e for e in events if e.event_type.startswith("interaction."))
        assert interaction.data["source_ref"] == "mgsuporte:wa-1"

    def test_sent_message_direction(self):
        envelope = _envelope(from_me=True)
        events = extract(envelope)
        interaction = next(e for e in events if e.event_type.startswith("interaction."))
        assert interaction.event_type == "interaction.message_sent"
        assert interaction.data["direction"] == "outbound"


class TestExtractionPromotion:
    def test_third_party_cnpj_stays_weak_only(self):
        envelope = _with_text("Preciso de cotação pro CNPJ 12.345.678/0001-99 do destinatário")
        events = extract(envelope)
        types = [e.event_type for e in events]
        assert "observation.recorded" in types
        assert "identity.observed" not in types

    def test_self_declared_cnpj_promotes(self):
        envelope = _with_text("Bom dia, meu CNPJ é 12.345.678/0001-99")
        events = extract(envelope)
        identity_events = [e for e in events if e.event_type == "identity.observed"]
        assert len(identity_events) == 1
        idents = {i.type: i.value for i in identity_events[0].subject.identities}
        assert idents.get("cnpj") == "12345678000199"

    def test_self_declared_generic_webmail_does_not_promote(self):
        envelope = _with_text("meu e-mail é fulano@gmail.com")
        events = extract(envelope)
        assert all(e.event_type != "identity.observed" for e in events)
        assert any(e.event_type == "observation.recorded" for e in events)

    def test_self_declared_corporate_email_promotes(self):
        envelope = _with_text("meu e-mail é compras@clientereal.com.br")
        events = extract(envelope)
        assert any(e.event_type == "identity.observed" for e in events)

    def test_our_number_generates_no_extraction_events(self):
        envelope = _with_text("meu CNPJ é 12.345.678/0001-99", remote_jid="5599992027458@s.whatsapp.net")
        events = extract(envelope)
        # só a interação (o número é nosso) — zero observation/identity
        assert [e.event_type for e in events] == ["interaction.message_received"]

    def test_no_text_generates_only_interaction(self):
        envelope = _envelope()
        events = extract(envelope)
        assert [e.event_type for e in events] == ["interaction.message_received"]


class TestOurNumber:
    def test_known_instance_number(self):
        assert is_our_number("+5599992027458") is True

    def test_customer_number(self):
        assert is_our_number("+5511999998888") is False
