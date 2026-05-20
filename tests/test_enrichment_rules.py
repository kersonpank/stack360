"""
Tests for enrichment rules, classifiers, evidence builder, score functions, and LLM router.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/testdb")
os.environ.setdefault("API_ENV", "testing")
os.environ["NORMALIZER_SCHEDULER_ENABLED"] = "false"
os.environ["LLM_ENABLED"] = "false"

import pytest

from app.enrichment.rules import (
    detect_fretebras,
    extract_cnpjs,
    extract_cpfs,
    extract_placas,
    extract_emails,
    detect_vehicle_types,
    detect_vehicle_bodies,
    detect_intents,
    extract_routes,
)
from app.enrichment.classifiers import classify_tipo_relacionamento, build_tags
from app.enrichment.evidence import build_evidence_rows
from app.enrichment.llm_router import LLMRouter
from app.services.enrichment_service import _compute_score_oportunidade, _compute_score_risco


# ---------------------------------------------------------------------------
# 1. CNPJ detection
# ---------------------------------------------------------------------------

class TestExtractCnpjs:
    def test_detects_formatted_cnpj(self):
        result = extract_cnpjs("CNPJ 12.345.678/0001-95 emitido")
        assert "12.345.678/0001-95" in result

    def test_empty_on_no_match(self):
        assert extract_cnpjs("sem documento") == []


# ---------------------------------------------------------------------------
# 2. CPF detection
# ---------------------------------------------------------------------------

class TestExtractCpfs:
    def test_detects_formatted_cpf(self):
        result = extract_cpfs("CPF 123.456.789-09")
        assert "123.456.789-09" in result

    def test_cpf_regex_does_not_match_cnpj_digits(self):
        # A raw 14-digit CNPJ string should NOT be matched as a CPF
        result = extract_cpfs("12345678000195")
        assert result == []


# ---------------------------------------------------------------------------
# 3. Placa detection
# ---------------------------------------------------------------------------

class TestExtractPlacas:
    def test_detects_old_format(self):
        result = extract_placas("placa ABC-1234")
        assert len(result) > 0

    def test_detects_mercosul_format(self):
        result = extract_placas("placa ABC1D23")
        assert len(result) > 0

    def test_empty_on_no_match(self):
        assert extract_placas("sem placa") == []


# ---------------------------------------------------------------------------
# 4. Email detection
# ---------------------------------------------------------------------------

class TestExtractEmails:
    def test_detects_email(self):
        result = extract_emails("contato@empresa.com.br")
        assert result == ["contato@empresa.com.br"]

    def test_empty_on_no_match(self):
        assert extract_emails("sem email") == []


# ---------------------------------------------------------------------------
# 5. Vehicle detection
# ---------------------------------------------------------------------------

class TestDetectVehicles:
    def test_detects_carreta(self):
        result = detect_vehicle_types("tenho uma carreta disponível")
        assert "carreta" in result

    def test_detects_van(self):
        result = detect_vehicle_types("van disponível")
        assert "van" in result

    def test_detects_bau_and_refrigerado(self):
        result = detect_vehicle_bodies("baú refrigerado")
        # The regex lowercases; "baú" may appear as "baú" or "bau" depending on normalization
        found_bau = "baú" in result or "bau" in result
        assert found_bau, f"expected baú/bau in {result}"
        assert "refrigerado" in result

    def test_empty_on_no_vehicle(self):
        assert detect_vehicle_types("sem veículo") == []


# ---------------------------------------------------------------------------
# 6. Intent detection
# ---------------------------------------------------------------------------

class TestDetectIntents:
    def test_detects_cotacao(self):
        result = detect_intents("preciso de cotação urgente")
        assert "cotacao" in result

    def test_detects_coleta(self):
        result = detect_intents("temos coleta amanhã")
        assert "coleta" in result

    def test_detects_atraso(self):
        result = detect_intents("houve atraso na entrega")
        assert "atraso" in result

    def test_empty_on_no_intent(self):
        assert detect_intents("mensagem sem intenção") == []


# ---------------------------------------------------------------------------
# 7. Route detection
# ---------------------------------------------------------------------------

class TestExtractRoutes:
    def test_detects_de_para_route(self):
        result = extract_routes("de São Paulo para Curitiba")
        assert len(result) > 0
        first = result[0]
        assert "São Paulo" in first
        assert "Curitiba" in first

    def test_empty_on_no_route(self):
        assert extract_routes("sem rota") == []


# ---------------------------------------------------------------------------
# 8. classify_tipo_relacionamento
# ---------------------------------------------------------------------------

class TestClassifyTipoRelacionamento:
    def test_group_contact(self):
        result = classify_tipo_relacionamento(
            contact_id="group:abc",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            total_messages=0,
            total_conversations=0,
        )
        assert result == "grupo"

    def test_motorista_signal(self):
        result = classify_tipo_relacionamento(
            contact_id="5511999990000",
            intents=["motorista"],
            roles=["motorista"],
            vehicle_types=["truck"],
            vehicle_bodies=[],
            total_messages=5,
            total_conversations=1,
        )
        assert result == "motorista"

    def test_lead_signal(self):
        result = classify_tipo_relacionamento(
            contact_id="5511999990001",
            intents=["cotacao"],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            total_messages=2,
            total_conversations=1,
        )
        assert result == "lead"

    def test_cliente_recorrente_com_operacao(self):
        result = classify_tipo_relacionamento(
            contact_id="5511999990002",
            intents=["coleta"],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            total_messages=25,
            total_conversations=5,
        )
        assert result == "cliente"

    def test_unknown_fallback(self):
        result = classify_tipo_relacionamento(
            contact_id="5511999990003",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            total_messages=1,
            total_conversations=1,
        )
        assert result == "desconhecido"

    def test_group_contact_id_returns_grupo_not_group(self):
        result = classify_tipo_relacionamento(
            contact_id="group:120363000000000000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            total_messages=10,
            total_conversations=1,
        )
        assert result == "grupo"
        assert result != "group"

    def test_tipo_relacionamento_values_are_portuguese(self):
        valid_values = {"desconhecido", "lead", "motorista", "fornecedor", "cliente", "grupo"}
        test_cases = [
            ("group:abc", [], [], [], [], 0, 0),
            ("5511111111111", ["cotacao"], [], [], [], 2, 1),
            ("5511111111112", ["motorista"], ["motorista"], ["truck"], [], 5, 1),
            ("5511111111113", [], [], [], [], 1, 1),
            ("5511111111114", ["coleta"], [], [], [], 25, 5),
        ]
        for contact_id, intents, roles, vtypes, vbodies, msgs, convs in test_cases:
            result = classify_tipo_relacionamento(
                contact_id=contact_id,
                intents=intents,
                roles=roles,
                vehicle_types=vtypes,
                vehicle_bodies=vbodies,
                total_messages=msgs,
                total_conversations=convs,
            )
            assert result in valid_values, f"contact_id={contact_id}: got '{result}', not in {valid_values}"


# ---------------------------------------------------------------------------
# 9. build_tags
# ---------------------------------------------------------------------------

class TestBuildTags:
    def test_always_contains_whatsapp(self):
        tags = build_tags(
            contact_id="5511999990000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            cnpjs=[],
            cpfs=[],
            placas=[],
            source_accounts=["acc1"],
            existing_tags=[],
        )
        assert "whatsapp" in tags

    def test_multicanal_when_two_source_accounts(self):
        tags = build_tags(
            contact_id="5511999990000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            cnpjs=[],
            cpfs=[],
            placas=[],
            source_accounts=["acc1", "acc2"],
            existing_tags=[],
        )
        assert "multicanal" in tags

    def test_documento_and_cnpj_when_cnpj_present(self):
        tags = build_tags(
            contact_id="5511999990000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            cnpjs=["12.345.678/0001-95"],
            cpfs=[],
            placas=[],
            source_accounts=["acc1"],
            existing_tags=[],
        )
        assert "documento" in tags
        assert "cnpj" in tags

    def test_documento_and_placa_when_placa_present(self):
        tags = build_tags(
            contact_id="5511999990000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            cnpjs=[],
            cpfs=[],
            placas=["ABC-1234"],
            source_accounts=["acc1"],
            existing_tags=[],
        )
        assert "documento" in tags
        assert "placa" in tags

    def test_group_contact_gets_grupo_tag_not_group(self):
        tags = build_tags(
            contact_id="group:120363000000000000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            cnpjs=[],
            cpfs=[],
            placas=[],
            source_accounts=["acc1"],
            existing_tags=[],
        )
        assert "grupo" in tags
        assert "group" not in tags
        assert "whatsapp" in tags

    def test_no_tag_group_in_any_case(self):
        for contact_id in ["5511999990000", "group:abc123", "lid:xyz"]:
            tags = build_tags(
                contact_id=contact_id,
                intents=["cotacao"],
                roles=[],
                vehicle_types=[],
                vehicle_bodies=[],
                cnpjs=[],
                cpfs=[],
                placas=[],
                source_accounts=["acc1"],
                existing_tags=[],
            )
            assert "group" not in tags, f"contact_id={contact_id}: tag 'group' not allowed, got {tags}"


# ---------------------------------------------------------------------------
# 10. Score computation
# ---------------------------------------------------------------------------

class TestScoreComputation:
    def test_score_oportunidade_with_cotacao_multicanal_high_msgs_cnpj(self):
        # cotacao (+20), no coleta/frete/carga (+0), multicanal (+15),
        # total_messages=100 > 50 (+15), cnpjs non-empty (+10) = 60
        score = _compute_score_oportunidade(
            ["cotacao"],
            ["whatsapp", "multicanal"],
            100,
            ["12345678000195"],
        )
        assert score == 60

    def test_score_risco_reclamacao_and_atraso(self):
        score = _compute_score_risco(["reclamacao", "atraso"])
        assert score == 35  # 20 + 15

    def test_score_risco_empty_intents(self):
        score = _compute_score_risco([])
        assert score == 0


# ---------------------------------------------------------------------------
# 11. LLMRouter disabled
# ---------------------------------------------------------------------------

class TestLLMRouterDisabled:
    def test_enabled_returns_false(self):
        assert LLMRouter.enabled() is False

    def test_extract_structured_returns_none(self):
        assert LLMRouter.extract_structured("anything") is None

    def test_summarize_returns_none(self):
        assert LLMRouter.summarize("anything") is None


# ---------------------------------------------------------------------------
# 12. build_evidence_rows structure
# ---------------------------------------------------------------------------

class TestBuildEvidenceRows:
    def test_structure_and_cnpj_row(self):
        rows = build_evidence_rows(
            contact_id="5511999990000",
            conversation_id="acc:jid",
            cnpjs=["12.345.678/0001-95"],
            cpfs=[],
            placas=[],
            emails=[],
            vehicle_types=[],
            vehicle_bodies=[],
            intents=[],
            roles=[],
            routes=[],
            tipo_relacionamento="lead",
        )

        assert isinstance(rows, list)
        assert len(rows) >= 1

        expected_keys = {
            "contact_id",
            "conversation_id",
            "evidence_type",
            "evidence_value",
            "confidence",
            "source",
            "payload",
            "created_at",
        }
        for row in rows:
            assert expected_keys.issubset(row.keys()), f"Missing keys in row: {row.keys()}"

        cnpj_rows = [r for r in rows if r["evidence_type"] == "cnpj"]
        assert len(cnpj_rows) == 1
        assert cnpj_rows[0]["evidence_value"] == "12.345.678/0001-95"


# ---------------------------------------------------------------------------
# 13. Fretebras rule
# ---------------------------------------------------------------------------

class TestDetectFretebras:
    def test_detects_bare_domain(self):
        assert detect_fretebras("acesse fretebras.com para cadastro") != []

    def test_detects_www(self):
        assert detect_fretebras("em www.fretebras.com tem frete") != []

    def test_detects_br_tld(self):
        assert detect_fretebras("site fretebras.com.br disponível") != []

    def test_detects_https_url(self):
        matches = detect_fretebras("link: https://www.fretebras.com/cadastro")
        assert len(matches) > 0

    def test_no_match_on_unrelated_text(self):
        assert detect_fretebras("olá, preciso de frete para SP") == []

    def test_returns_deduplicated(self):
        text = "fretebras.com e fretebras.com novamente"
        matches = detect_fretebras(text)
        assert len(matches) == 1


class TestFretebrasClassifier:
    def test_fretebras_classifies_as_motorista(self):
        result = classify_tipo_relacionamento(
            contact_id="5511999990000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            total_messages=1,
            total_conversations=1,
            fretebras_detected=True,
        )
        assert result == "motorista"

    def test_fretebras_does_not_downgrade_cliente(self):
        result = classify_tipo_relacionamento(
            contact_id="5511999990000",
            intents=["coleta"],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            total_messages=25,
            total_conversations=5,
            fretebras_detected=True,
        )
        assert result == "cliente"

    def test_fretebras_confidence_tag_added(self):
        tags = build_tags(
            contact_id="5511999990000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            cnpjs=[],
            cpfs=[],
            placas=[],
            source_accounts=["acc1"],
            existing_tags=[],
            fretebras_detected=True,
        )
        assert "fretebras" in tags
        assert "motorista" in tags

    def test_fretebras_no_group_tag(self):
        tags = build_tags(
            contact_id="5511999990000",
            intents=[],
            roles=[],
            vehicle_types=[],
            vehicle_bodies=[],
            cnpjs=[],
            cpfs=[],
            placas=[],
            source_accounts=["acc1"],
            existing_tags=[],
            fretebras_detected=True,
        )
        assert "group" not in tags


class TestFretebrasEvidence:
    def _make_rows(self, fretebras_matches, extra_payload=None):
        return build_evidence_rows(
            contact_id="5511999990000",
            conversation_id="acc:jid",
            cnpjs=[],
            cpfs=[],
            placas=[],
            emails=[],
            vehicle_types=[],
            vehicle_bodies=[],
            intents=[],
            roles=[],
            routes=[],
            tipo_relacionamento="motorista",
            fretebras_matches=fretebras_matches,
            fretebras_payload=extra_payload,
        )

    def test_source_domain_evidence_created(self):
        rows = self._make_rows(["fretebras.com"])
        sd = [r for r in rows if r["evidence_type"] == "source_domain"]
        assert len(sd) == 1
        assert sd[0]["evidence_value"] == "fretebras"
        assert sd[0]["confidence"] == 0.98

    def test_role_motorista_evidence_created(self):
        rows = self._make_rows(["www.fretebras.com"])
        role_rows = [r for r in rows if r["evidence_type"] == "role" and r["evidence_value"] == "motorista"]
        assert len(role_rows) == 1
        assert role_rows[0]["confidence"] == 0.98

    def test_payload_contains_rule(self):
        rows = self._make_rows(["fretebras.com.br"])
        sd = [r for r in rows if r["evidence_type"] == "source_domain"][0]
        assert sd["payload"]["rule"] == "fretebras_domain_motorista"
        assert "motivo" in sd["payload"]

    def test_no_fretebras_evidence_when_no_match(self):
        rows = self._make_rows([])
        sd = [r for r in rows if r["evidence_type"] == "source_domain"]
        assert sd == []

    def test_no_duplicate_evidence_for_multiple_urls(self):
        rows = self._make_rows(["fretebras.com", "www.fretebras.com", "fretebras.com.br"])
        sd = [r for r in rows if r["evidence_type"] == "source_domain"]
        # build_evidence_rows produces 1 row; dedup happens in insert_deduped
        assert len(sd) == 1


class TestFretebrasScore:
    def test_score_increases_with_fretebras(self):
        base = _compute_score_oportunidade([], ["whatsapp"], 1, [])
        with_fb = _compute_score_oportunidade([], ["whatsapp"], 1, [], fretebras_detected=True)
        assert with_fb == base + 35

    def test_score_capped_at_100(self):
        score = _compute_score_oportunidade(
            ["cotacao", "coleta", "frete"],
            ["whatsapp", "multicanal"],
            100,
            ["12345678000195"],
            fretebras_detected=True,
        )
        assert score == 100
