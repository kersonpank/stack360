"""
Enrichment Service v0.1 — rule-based semantic enrichment.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.enrichment.classifiers import build_tags, classify_tipo_relacionamento, should_update_tipo
from app.enrichment.evidence import build_evidence_rows
from app.enrichment.rules import (
    detect_fretebras,
    detect_intents,
    detect_roles,
    detect_vehicle_bodies,
    detect_vehicle_types,
    extract_cnpjs,
    extract_cpfs,
    extract_emails,
    extract_placas,
    extract_routes,
)
from app.enrichment.summarizer import (
    build_contact_summary,
    build_conversation_subject,
    build_conversation_summary,
)
from app.repositories.enrichment_repository import EnrichmentRepository
from app.repositories.evidence_repository import EvidenceRepository


_MAX_TIMELINE_EVENTS = 10


def _compute_score_oportunidade(
    intents: List[str], tags: List[str], total_messages: int, cnpjs: List[str],
    fretebras_detected: bool = False,
) -> int:
    score = 0
    if "cotacao" in intents:
        score += 20
    if any(i in intents for i in ["coleta", "frete", "carga"]):
        score += 20
    if "multicanal" in tags:
        score += 15
    if total_messages > 50:
        score += 15
    if cnpjs:
        score += 10
    if fretebras_detected:
        score += 35
    return min(score, 100)


def _compute_score_risco(intents: List[str]) -> int:
    score = 0
    if "reclamacao" in intents:
        score += 20
    if "atraso" in intents:
        score += 15
    return min(score, 100)


def _build_corpus(messages) -> str:
    """Concatenate message texts for extraction."""
    parts = [m.texto for m in messages if m.texto]
    return " ".join(parts)


def _build_timeline_events(
    contact_id: str,
    intents: List[str],
    tags: List[str],
    vehicle_types: List[str],
    vehicle_bodies: List[str],
    cnpjs: List[str],
    cpfs: List[str],
    placas: List[str],
    primeiro_contato_em,
    ultimo_contato_em,
    fretebras_detected: bool = False,
) -> List[Dict[str, Any]]:
    now = datetime.now(tz=timezone.utc)
    events = []

    if primeiro_contato_em:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "first_contact",
            "titulo": "Primeiro contato registrado",
            "descricao": None,
            "importancia": "low",
            "data_hora": primeiro_contato_em,
            "payload": {},
            "created_at": now,
        })

    if ultimo_contato_em:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "last_contact",
            "titulo": "Último contato registrado",
            "descricao": None,
            "importancia": "low",
            "data_hora": ultimo_contato_em,
            "payload": {},
            "created_at": now,
        })

    if "cotacao" in intents:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "quote_detected",
            "titulo": "Sinal de cotação detectado",
            "descricao": "Palavras-chave de cotação/orçamento identificadas",
            "importancia": "high",
            "data_hora": now,
            "payload": {"intents": intents},
            "created_at": now,
        })

    if vehicle_types or vehicle_bodies:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "vehicle_detected",
            "titulo": "Veículo mencionado",
            "descricao": f"Tipos: {', '.join((vehicle_types + vehicle_bodies)[:4])}",
            "importancia": "medium",
            "data_hora": now,
            "payload": {"vehicle_types": vehicle_types, "vehicle_bodies": vehicle_bodies},
            "created_at": now,
        })

    if cnpjs or cpfs or placas:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "document_detected",
            "titulo": "Documento detectado",
            "descricao": f"CNPJ:{len(cnpjs)} CPF:{len(cpfs)} Placa:{len(placas)}",
            "importancia": "medium",
            "data_hora": now,
            "payload": {"cnpjs": cnpjs[:3], "cpfs": cpfs[:3], "placas": placas[:3]},
            "created_at": now,
        })

    if "reclamacao" in intents:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "complaint_detected",
            "titulo": "Sinal de reclamação detectado",
            "descricao": None,
            "importancia": "high",
            "data_hora": now,
            "payload": {},
            "created_at": now,
        })

    if "multicanal" in tags:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "multichannel_detected",
            "titulo": "Contato multicanal detectado",
            "descricao": None,
            "importancia": "medium",
            "data_hora": now,
            "payload": {},
            "created_at": now,
        })

    if fretebras_detected:
        events.append({
            "contact_id": contact_id,
            "tipo_evento": "fretebras_detected",
            "titulo": "Fretebras.com detectado na conversa",
            "descricao": "Presença de link Fretebras indica alta probabilidade de motorista.",
            "importancia": "high",
            "data_hora": now,
            "payload": {},
            "created_at": now,
        })

    return events[:_MAX_TIMELINE_EVENTS]


def _build_opportunities(
    contact_id: str,
    intents: List[str],
    tipo_relacionamento: str,
    score_oportunidade: int,
    vehicle_types: List[str],
    vehicle_bodies: List[str],
    conversation_id: Optional[str],
) -> List[Dict[str, Any]]:
    now = datetime.now(tz=timezone.utc)
    opps = []

    if any(i in intents for i in ["cotacao", "frete", "coleta"]):
        opps.append({
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "tipo_oportunidade": "cotacao_frete",
            "descricao": "Interesse em cotação/frete detectado por análise de mensagens",
            "score": score_oportunidade,
            "status": "nova",
            "proxima_acao": "Revisar conversa e fazer follow-up comercial",
            "created_at": now,
            "updated_at": now,
        })

    if tipo_relacionamento == "motorista":
        v_info = ", ".join((vehicle_types + vehicle_bodies)[:2]) or "veículo não especificado"
        opps.append({
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "tipo_oportunidade": "motorista_parceiro",
            "descricao": f"Motorista identificado: {v_info}",
            "score": score_oportunidade,
            "status": "nova",
            "proxima_acao": "Validar veículo, cidade base e documentação",
            "created_at": now,
            "updated_at": now,
        })

    if tipo_relacionamento == "fornecedor":
        opps.append({
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "tipo_oportunidade": "fornecedor_potencial",
            "descricao": "Potencial fornecedor identificado por análise de mensagens",
            "score": score_oportunidade,
            "status": "nova",
            "proxima_acao": "Avaliar parceria e capacidade",
            "created_at": now,
            "updated_at": now,
        })

    return opps


class EnrichmentService:
    def __init__(self, read_db: Session, write_db: Session):
        self.read_db = read_db
        self.write_db = write_db
        self.repo = EnrichmentRepository(read_db, write_db)
        self.evidence_repo = EvidenceRepository(read_db, write_db)

    def run(
        self,
        limit: int = 100,
        dry_run: bool = False,
        contact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        contacts = self.repo.get_contacts_for_enrichment(limit=limit, contact_id=contact_id)
        print(f"[enrichment] {len(contacts)} contact(s) selecionados para enriquecimento.")

        processed = 0
        errors = 0

        for contact in contacts:
            try:
                self._enrich_contact(contact, dry_run=dry_run)
                if not dry_run:
                    self.write_db.commit()
                processed += 1
            except Exception as exc:
                errors += 1
                print(f"[enrichment] ERRO em {contact.contact_id}: {exc}")
                try:
                    self.read_db.rollback()
                except Exception:
                    pass
                try:
                    self.write_db.rollback()
                except Exception:
                    pass
                if not dry_run:
                    try:
                        self.repo.upsert_enrichment_state(
                            "contact", contact.contact_id,
                            {"status": "error", "error": str(exc)[:500],
                             "updated_at": datetime.now(tz=timezone.utc)}
                        )
                        self.write_db.commit()
                    except Exception:
                        pass

        return {"processed": processed, "errors": errors, "dry_run": dry_run, "total_selected": len(contacts)}

    def _enrich_contact(self, contact, dry_run: bool) -> None:
        cid = contact.contact_id
        messages = self.repo.get_messages_for_contact(cid)
        conversations = self.repo.get_conversations_for_contact(cid)
        source_accounts = self.repo.get_source_accounts_for_contact(cid)

        corpus = _build_corpus(messages)

        # -- Extract --
        cnpjs = extract_cnpjs(corpus)
        cpfs = extract_cpfs(corpus)
        placas = extract_placas(corpus)
        emails = extract_emails(corpus)
        vehicle_types = detect_vehicle_types(corpus)
        vehicle_bodies = detect_vehicle_bodies(corpus)
        intents = detect_intents(corpus)
        routes = extract_routes(corpus)
        roles = detect_roles(corpus, cid)
        fretebras_global = detect_fretebras(corpus)
        contact_fretebras_detected = bool(fretebras_global)

        total_messages = contact.total_mensagens or 0
        total_conversations = len(conversations)

        # -- Classify --
        current_tipo = contact.tipo_relacionamento or "desconhecido"
        new_tipo = classify_tipo_relacionamento(
            contact_id=cid,
            intents=intents,
            roles=roles,
            vehicle_types=vehicle_types,
            vehicle_bodies=vehicle_bodies,
            total_messages=total_messages,
            total_conversations=total_conversations,
            placas=placas,
            fretebras_detected=contact_fretebras_detected,
        )
        # Fretebras override: bypass normal specificity for desconhecido/lead/grupo
        # (but never downgrade cliente/fornecedor)
        if contact_fretebras_detected and not cid.startswith("group:") and current_tipo in {"desconhecido", "lead", "grupo"}:
            tipo = "motorista"
        elif should_update_tipo(current_tipo, new_tipo):
            tipo = new_tipo
        else:
            tipo = current_tipo

        tags = build_tags(
            contact_id=cid,
            intents=intents,
            roles=roles,
            vehicle_types=vehicle_types,
            vehicle_bodies=vehicle_bodies,
            cnpjs=cnpjs,
            cpfs=cpfs,
            placas=placas,
            source_accounts=source_accounts,
            existing_tags=contact.tags or [],
            tipo_relacionamento=tipo,
            fretebras_detected=contact_fretebras_detected,
        )

        score_op = _compute_score_oportunidade(intents, tags, total_messages, cnpjs, fretebras_detected=contact_fretebras_detected)
        score_ri = _compute_score_risco(intents)

        summary = build_contact_summary(
            contact_id=cid,
            total_messages=total_messages,
            total_conversations=total_conversations,
            tipo_relacionamento=tipo,
            intents=intents,
            tags=tags,
            vehicle_types=vehicle_types,
            vehicle_bodies=vehicle_bodies,
            fretebras_detected=contact_fretebras_detected,
        )

        # -- Per-conversation enrichment --
        all_evidence = []
        first_conv_id = conversations[0].conversation_id if conversations else None

        for conv in conversations:
            conv_messages = [m for m in messages if m.conversation_id == conv.conversation_id]
            conv_corpus = " ".join(m.texto for m in conv_messages if m.texto)
            conv_intents = detect_intents(conv_corpus) if conv_corpus else []
            conv_vehicle_types = detect_vehicle_types(conv_corpus) if conv_corpus else []
            conv_subject = build_conversation_subject(conv_intents, conv_vehicle_types)
            conv_summary = build_conversation_summary(
                conv.conversation_id, len(conv_messages), conv_intents
            )

            if dry_run:
                print(f"  [DRY-RUN] conv={conv.conversation_id} assunto={conv_subject!r}")
            else:
                self.repo.update_conversation(
                    conv.conversation_id,
                    {"assunto_principal": conv_subject, "resumo_conversa": conv_summary},
                )

            # Evidence per conversation
            conv_cnpjs = extract_cnpjs(conv_corpus)
            conv_cpfs = extract_cpfs(conv_corpus)
            conv_placas = extract_placas(conv_corpus)
            conv_emails = extract_emails(conv_corpus)
            conv_vt = detect_vehicle_types(conv_corpus)
            conv_vb = detect_vehicle_bodies(conv_corpus)
            conv_intents_full = detect_intents(conv_corpus)
            conv_roles = detect_roles(conv_corpus, cid)
            conv_routes = extract_routes(conv_corpus)
            conv_fretebras = detect_fretebras(conv_corpus)

            # Build fretebras payload: find first message with fretebras URL
            fretebras_payload = None
            if conv_fretebras:
                fb_msg = next(
                    (m for m in conv_messages if m.texto and detect_fretebras(m.texto)),
                    None,
                )
                fretebras_payload = {
                    "message_id": fb_msg.message_id if fb_msg else None,
                    "conversation_id": conv.conversation_id,
                    "enviada_por_mim": fb_msg.enviada_por_mim if fb_msg else None,
                }

            evidence_rows = build_evidence_rows(
                contact_id=cid,
                conversation_id=conv.conversation_id,
                cnpjs=conv_cnpjs,
                cpfs=conv_cpfs,
                placas=conv_placas,
                emails=conv_emails,
                vehicle_types=conv_vt,
                vehicle_bodies=conv_vb,
                intents=conv_intents_full,
                roles=conv_roles,
                routes=conv_routes,
                tipo_relacionamento=tipo,
                fretebras_matches=conv_fretebras or None,
                fretebras_payload=fretebras_payload,
            )
            all_evidence.extend(evidence_rows)

        if dry_run:
            print(f"  [DRY-RUN] contact={cid}")
            print(f"            tipo_relacionamento = {tipo}")
            print(f"            tags = {tags}")
            print(f"            score_op={score_op} score_ri={score_ri}")
            print(f"            intents = {intents}")
            print(f"            vehicles = {vehicle_types + vehicle_bodies}")
            print(f"            cnpjs={len(cnpjs)} cpfs={len(cpfs)} placas={len(placas)}")
            print(f"            evidence rows = {len(all_evidence)}")
            print(f"            summary = {summary[:120]!r}")
            print()
            return

        # -- Write contact --
        self.repo.update_contact(cid, {
            "tipo_relacionamento": tipo,
            "tags": tags,
            "resumo_geral": summary,
            "score_oportunidade": score_op,
            "score_risco": score_ri,
        })

        # -- Timeline events --
        current_count = self.repo.count_timeline_events(cid)
        events = _build_timeline_events(
            contact_id=cid,
            intents=intents,
            tags=tags,
            vehicle_types=vehicle_types,
            vehicle_bodies=vehicle_bodies,
            cnpjs=cnpjs,
            cpfs=cpfs,
            placas=placas,
            primeiro_contato_em=contact.primeiro_contato_em,
            ultimo_contato_em=contact.ultimo_contato_em,
            fretebras_detected=contact_fretebras_detected,
        )
        for ev in events:
            if current_count < _MAX_TIMELINE_EVENTS:
                self.repo.insert_timeline_event(ev)
                current_count += 1

        # -- Opportunities --
        opps = _build_opportunities(
            contact_id=cid,
            intents=intents,
            tipo_relacionamento=tipo,
            score_oportunidade=score_op,
            vehicle_types=vehicle_types,
            vehicle_bodies=vehicle_bodies,
            conversation_id=first_conv_id,
        )
        for opp in opps:
            self.repo.insert_opportunity(opp)

        # -- Evidence --
        self.evidence_repo.insert_deduped(all_evidence)

        # -- Enrichment state --
        last_msg_at = max((m.data_hora for m in messages if m.data_hora), default=None)
        self.repo.upsert_enrichment_state("contact", cid, {
            "last_enriched_at": datetime.now(tz=timezone.utc),
            "last_message_at": last_msg_at,
            "status": "done",
            "error": None,
            "updated_at": datetime.now(tz=timezone.utc),
        })
