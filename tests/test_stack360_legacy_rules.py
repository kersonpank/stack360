"""Testes de `app/stack360/projection/legacy_rules.py`.

Cobrem especialmente os casos de PROMOÇÃO vs NÃO-PROMOÇÃO de identidade
(regra corrigida pelo usuário: CNPJ/e-mail citado em conversa é sempre
fraco; só autodeclaração explícita promove) — são os testes mais
importantes desta fase, porque uma regra errada aqui contamina o backfill
inteiro.
"""
from app.stack360.projection import legacy_rules as r


def test_extract_cnpjs_basic():
    assert r.extract_cnpjs("CNPJ 12.345.678/0001-99 da empresa") == ["12.345.678/0001-99"]


def test_extract_emails_basic():
    assert r.extract_emails("meu contato é joao@exemplo.com.br obrigado") == ["joao@exemplo.com.br"]


def test_cnpj_root():
    assert r.cnpj_root("12.345.678/0001-99") == "12345678"
    assert r.cnpj_root("12.345.678/0002-70") == "12345678"  # mesma raiz, filial diferente
    assert r.cnpj_root("invalido") is None


class TestSelfDeclaredCnpj:
    def test_self_declaration_promotes(self):
        text = "Bom dia, meu CNPJ é 12.345.678/0001-99, pode confirmar a cotação?"
        assert r.detect_self_declared_cnpjs(text) == ["12.345.678/0001-99"]

    def test_third_party_mention_does_not_promote(self):
        # Quem pede frete cita CNPJ de remetente/destinatário/tomador — não é autodeclaração.
        text = "Preciso de uma cotação pro CNPJ 12.345.678/0001-99 do destinatário"
        assert r.detect_self_declared_cnpjs(text) == []

    def test_operational_mention_does_not_promote(self):
        text = "A nota fiscal saiu no CNPJ 98.765.432/0001-10 ontem"
        assert r.detect_self_declared_cnpjs(text) == []

    def test_nosso_variant_promotes(self):
        text = "Nosso CNPJ: 11.222.333/0001-44 pra emissão da nota"
        assert r.detect_self_declared_cnpjs(text) == ["11.222.333/0001-44"]


class TestSelfDeclaredEmail:
    def test_self_declaration_promotes(self):
        text = "Pode mandar por aqui, meu e-mail é compras@clienteX.com.br"
        assert r.detect_self_declared_emails(text) == ["compras@clienteX.com.br"]

    def test_third_party_mention_does_not_promote(self):
        text = "Manda a cotação pro email financeiro@outraempresa.com deles"
        assert r.detect_self_declared_emails(text) == []


class TestGenericWebmail:
    def test_gmail_is_generic(self):
        assert r.is_generic_webmail("fulano@gmail.com") is True

    def test_corporate_domain_is_not_generic(self):
        assert r.is_generic_webmail("compras@clientereal.com.br") is False

    def test_self_declared_gmail_still_flagged_generic(self):
        # mesmo autodeclarado, webmail genérico nunca deve promover (checado pelo chamador
        # usando is_generic_webmail junto de detect_self_declared_emails)
        text = "meu e-mail é fulano@gmail.com"
        declared = r.detect_self_declared_emails(text)
        assert declared == ["fulano@gmail.com"]
        assert r.is_generic_webmail(declared[0]) is True


class TestMessageFilters:
    def test_broadcast_excluded(self):
        assert r.is_conversational_message("conversation", "status@broadcast") is False

    def test_newsletter_excluded(self):
        assert r.is_conversational_message("conversation", "123@newsletter") is False

    def test_reaction_excluded(self):
        assert r.is_conversational_message("reactionMessage", "5511999998888@s.whatsapp.net") is False

    def test_protocol_excluded(self):
        assert r.is_conversational_message("protocolMessage", "5511999998888@s.whatsapp.net") is False

    def test_normal_text_included(self):
        assert r.is_conversational_message("conversation", "5511999998888@s.whatsapp.net") is True

    def test_group_jid_detected(self):
        assert r.is_group_jid("120363000@g.us") is True
        assert r.is_group_jid("5511999998888@s.whatsapp.net") is False

    def test_lid_detected(self):
        assert r.is_lid("123456@lid") is True
        assert r.is_lid("5511999998888@s.whatsapp.net") is False


class TestIntentsAndVehicles:
    def test_detect_intents_cotacao(self):
        assert "cotacao" in r.detect_intents("Preciso de uma cotação urgente")

    def test_detect_vehicle_types(self):
        assert "carreta" in r.detect_vehicle_types("Tenho uma carreta disponível")

    def test_detect_fretebras(self):
        assert r.detect_fretebras("confere em www.fretebras.com.br/anuncio") != []


class TestAffiliation:
    def test_self_declared_affiliation(self):
        assert r.detect_self_declared_affiliation("Bom dia, aqui é da TSM") == "TSM"

    def test_no_affiliation_mentioned(self):
        assert r.detect_self_declared_affiliation("Bom dia, tudo certo?") is None
