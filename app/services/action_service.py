from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.opportunity import Opportunity
from app.repositories.action_repository import ActionRepository

_OPEN_STATUSES = {"nova", "em_andamento"}
_COMMERCIAL_TIPOS = {"lead", "fornecedor"}
_COMMERCIAL_TAGS = {"cotacao", "frete", "carga", "cotação"}
_MOTORISTA_EVIDENCE = {"cidade_base", "rota", "veiculo", "veiculo_tipo", "carroceria", "tipo_veiculo"}
_COMMERCIAL_EVIDENCE = {"empresa", "cnpj", "origem", "destino", "contato_qualificado"}


def _score(contact: Contact, bonus: int = 0) -> Decimal:
    base = contact.score_oportunidade or Decimal(0)
    return min(Decimal(100), base + Decimal(bonus))


def _has_tag(contact: Contact, tag: str) -> bool:
    return bool(contact.tags and any(t.lower() == tag.lower() for t in contact.tags))


def _has_any_tag(contact: Contact, tags: set) -> bool:
    if not contact.tags:
        return False
    contact_tags_lower = {t.lower() for t in contact.tags}
    return bool(contact_tags_lower & {t.lower() for t in tags})


def _collect_rules(
    contact: Contact,
    opportunities: List[Opportunity],
    evidence_types: List[str],
) -> List[dict]:
    actions = []
    ev_set = {e.lower() for e in evidence_types}
    score_opp = contact.score_oportunidade or Decimal(0)
    now = datetime.now(tz=timezone.utc)

    # Rule 1: follow-up de cotação
    cotacao_opps = [
        o for o in opportunities
        if o.tipo_oportunidade == "cotacao_frete" and o.status in ("nova", "open")
    ]
    for opp in cotacao_opps:
        opp_score = opp.score or score_opp
        actions.append({
            "contact_id": contact.contact_id,
            "opportunity_id": opp.opportunity_id,
            "action_type": "followup_cotacao",
            "title": "Fazer follow-up de cotação",
            "description": "Revisar conversa e retomar atendimento comercial.",
            "priority_score": max(opp_score, score_opp),
            "reason": "Stakeholder possui oportunidade de cotação/frete em aberto.",
            "status": "nova",
            "source": "rules",
            "payload": {},
        })
        break  # one action per contact for this type

    # Rule 2: qualificar motorista
    if contact.tipo_relacionamento == "motorista":
        missing = _MOTORISTA_EVIDENCE - ev_set
        if missing:
            msgs_bonus = min(20, (contact.total_mensagens or 0) // 10)
            actions.append({
                "contact_id": contact.contact_id,
                "action_type": "qualificar_motorista",
                "title": "Qualificar motorista",
                "description": "Confirmar veículo, carroceria, cidade base, rotas de interesse e disponibilidade.",
                "priority_score": _score(contact, msgs_bonus),
                "reason": "Motorista detectado, mas perfil operacional ainda está incompleto.",
                "status": "nova",
                "source": "rules",
                "payload": {"missing_evidence": sorted(missing)},
            })

    # Rule 3: convidar motorista para plataforma
    has_fretebras = _has_tag(contact, "fretebras")
    has_motorista_parceiro_opp = any(o.tipo_oportunidade == "motorista_parceiro" for o in opportunities)
    if has_fretebras or has_motorista_parceiro_opp:
        actions.append({
            "contact_id": contact.contact_id,
            "action_type": "convidar_motorista_para_plataforma",
            "title": "Convidar motorista para plataforma de cargas",
            "description": "Validar interesse em receber cargas e completar cadastro operacional.",
            "priority_score": max(Decimal(70), score_opp),
            "reason": "Contato tem forte sinal de motorista/parceiro.",
            "status": "nova",
            "source": "rules",
            "payload": {"fretebras": has_fretebras, "motorista_parceiro_opp": has_motorista_parceiro_opp},
        })

    # Rule 4: pedir CNPJ
    tipo_is_commercial = contact.tipo_relacionamento in _COMMERCIAL_TIPOS
    has_commercial_tag = _has_any_tag(contact, _COMMERCIAL_TAGS)
    has_cnpj_evidence = "cnpj" in ev_set
    if (tipo_is_commercial or has_commercial_tag) and not has_cnpj_evidence:
        actions.append({
            "contact_id": contact.contact_id,
            "action_type": "pedir_cnpj",
            "title": "Solicitar CNPJ",
            "description": "Pedir CNPJ para qualificação comercial e cadastro.",
            "priority_score": score_opp,
            "reason": "Stakeholder tem sinal comercial, mas CNPJ não foi identificado.",
            "status": "nova",
            "source": "rules",
            "payload": {},
        })

    # Rule 5: completar dados comerciais
    if contact.tipo_relacionamento in _COMMERCIAL_TIPOS and contact.resumo_geral:
        missing_commercial = _COMMERCIAL_EVIDENCE - ev_set
        if missing_commercial:
            actions.append({
                "contact_id": contact.contact_id,
                "action_type": "completar_dados_comerciais",
                "title": "Completar dados comerciais",
                "description": "Validar empresa, papel do contato, origem/destino, volume e necessidade.",
                "priority_score": score_opp,
                "reason": "Contato possui sinais comerciais, mas dados de qualificação estão incompletos.",
                "status": "nova",
                "source": "rules",
                "payload": {"missing_evidence": sorted(missing_commercial)},
            })

    # Rule 6: reativar contato
    if score_opp >= 60 and contact.ultimo_contato_em:
        cutoff = now - timedelta(days=60)
        last = contact.ultimo_contato_em
        if last.tzinfo is None:
            from datetime import timezone as tz_
            last = last.replace(tzinfo=tz_.utc)
        if last < cutoff:
            actions.append({
                "contact_id": contact.contact_id,
                "action_type": "reativar_contato",
                "title": "Reativar contato",
                "description": "Retomar contato com stakeholder de alto potencial sem interação recente.",
                "priority_score": score_opp,
                "reason": "Alto potencial, mas sem interação recente.",
                "status": "nova",
                "source": "rules",
                "payload": {"ultimo_contato_em": contact.ultimo_contato_em.isoformat() if contact.ultimo_contato_em else None},
            })

    # Rule 7: revisar alto potencial
    if score_opp >= 80:
        actions.append({
            "contact_id": contact.contact_id,
            "action_type": "revisar_alto_potencial",
            "title": "Revisar stakeholder de alto potencial",
            "description": "Analisar histórico, oportunidades e próxima ação comercial.",
            "priority_score": score_opp,
            "reason": "Stakeholder com score de oportunidade elevado.",
            "status": "nova",
            "source": "rules",
            "payload": {},
        })

    return actions


class ActionService:
    def __init__(self, read_db: Session, write_db: Session):
        self.read_db = read_db
        self.write_db = write_db
        self.repo = ActionRepository(read_db, write_db)

    def run(
        self,
        limit: int = 100,
        dry_run: bool = False,
        contact_id: Optional[str] = None,
    ) -> dict:
        contacts = self.repo.get_contacts_for_action_generation(limit=limit, contact_id=contact_id)
        print(f"[actions] {len(contacts)} contact(s) selecionados para geração de ações.")

        total_inserted = 0
        total_updated = 0
        total_skipped = 0

        for contact in contacts:
            opportunities = self.repo.get_open_opportunities_for_contact(contact.contact_id)
            evidence_types = self.repo.get_evidence_types_for_contact(contact.contact_id)
            candidate_actions = _collect_rules(contact, opportunities, evidence_types)

            for action_data in candidate_actions:
                if dry_run:
                    existing = self.repo.get_open_action(action_data["contact_id"], action_data["action_type"])
                    verb = "UPDATE" if existing else "INSERT"
                    print(
                        f"  [DRY-RUN] {verb} contact={action_data['contact_id']} "
                        f"type={action_data['action_type']} "
                        f"priority={action_data['priority_score']}"
                    )
                    if verb == "INSERT":
                        total_inserted += 1
                    else:
                        total_updated += 1
                else:
                    result = self.repo.upsert_action(action_data)
                    if result == "inserted":
                        total_inserted += 1
                    elif result == "updated":
                        total_updated += 1

        if not dry_run:
            try:
                self.write_db.commit()
            except Exception as exc:
                self.write_db.rollback()
                raise exc

        return {
            "processed_contacts": len(contacts),
            "actions_inserted": total_inserted,
            "actions_updated": total_updated,
            "actions_skipped": total_skipped,
            "dry_run": dry_run,
        }
