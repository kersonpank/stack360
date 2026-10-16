"""Régua de validação — roda UMA VEZ, fora do worker contínuo.

Não é gate de aprovação (o gate real é a amostra humana, ver docs/
projection-whatsapp.md). Serve só pra achar o que a reextração do bruto
deixa escapar, comparando contra `contact_evidence`/`opportunities`/
`contacts.nome_atual` do legado — ferramentas de medição, nunca escrita
no canônico.

Uso:
    python -m app.stack360.projection.validate_against_legacy \
        --legacy-database-url postgresql://... --limit 200
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from typing import Optional

from sqlalchemy import text

from app.stack360.projection import legacy_rules as rules
from app.stack360.projection.extractors.whatsapp_message import _message_text as _extract_text
from app.stack360.projection.readers.base import readonly_engine as legacy_engine

log = logging.getLogger("stack360.projection.validate_against_legacy")


def _digits(value: Optional[str]) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def recall_check(legacy_url: str, limit: int = 200) -> dict:
    eng = legacy_engine(legacy_url)
    try:
        with eng.connect() as conn:
            evidence_rows = conn.execute(
                text(
                    """
                    SELECT contact_id, evidence_type, value
                    FROM contact_evidence
                    WHERE evidence_type IN ('cnpj', 'email')
                    ORDER BY contact_id
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()

            contacts_rows = conn.execute(
                text("SELECT contact_id, nome_atual, telefone FROM contacts WHERE nome_atual IS NOT NULL LIMIT :limit"),
                {"limit": limit},
            ).mappings().all()

        legacy_by_contact: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"cnpj": set(), "email": set()})
        for row in evidence_rows:
            legacy_by_contact[row["contact_id"]][row["evidence_type"]].add(row["value"])

        found_cnpj = 0
        total_cnpj = 0
        found_email = 0
        total_email = 0
        misses: list[dict] = []

        for contact_id, values in legacy_by_contact.items():
            phone_digits = _digits(contact_id)
            if not phone_digits:
                continue
            with eng.connect() as conn:
                msgs = conn.execute(
                    text(
                        """
                        SELECT raw_message FROM raw_evolution_messages
                        WHERE remote_jid LIKE :p OR participant LIKE :p
                        LIMIT 500
                        """
                    ),
                    {"p": f"{phone_digits}%"},
                ).scalars().all()

            combined_text = " ".join(filter(None, (_extract_text(m) for m in msgs)))
            fresh_cnpjs = {rules.normalize_cnpj_digits(c) for c in rules.extract_cnpjs(combined_text)}
            fresh_emails = {e.lower() for e in rules.extract_emails(combined_text)}

            for cnpj in values["cnpj"]:
                total_cnpj += 1
                if rules.normalize_cnpj_digits(cnpj) in fresh_cnpjs:
                    found_cnpj += 1
                else:
                    misses.append({"contact_id": contact_id, "type": "cnpj", "value": cnpj})

            for email in values["email"]:
                total_email += 1
                if email.lower() in fresh_emails:
                    found_email += 1
                else:
                    misses.append({"contact_id": contact_id, "type": "email", "value": email})

        name_diffs = []
        for row in contacts_rows:
            phone_digits = _digits(row["contact_id"])
            if not phone_digits:
                continue
            with eng.connect() as conn:
                push_names = conn.execute(
                    text(
                        """
                        SELECT DISTINCT push_name FROM raw_evolution_messages
                        WHERE (remote_jid LIKE :p OR participant LIKE :p) AND push_name IS NOT NULL
                        LIMIT 5
                        """
                    ),
                    {"p": f"{phone_digits}%"},
                ).scalars().all()
            if push_names and row["nome_atual"] not in push_names:
                name_diffs.append(
                    {"contact_id": row["contact_id"], "legacy_nome": row["nome_atual"], "push_names": list(push_names)}
                )

        report = {
            "cnpj_recall": f"{found_cnpj}/{total_cnpj}" if total_cnpj else "n/a",
            "email_recall": f"{found_email}/{total_email}" if total_email else "n/a",
            "misses_sample": misses[:30],
            "name_diffs_sample": name_diffs[:30],
            "name_diffs_total": len(name_diffs),
        }
        return report
    finally:
        eng.dispose()


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="app.stack360.projection.validate_against_legacy")
    p.add_argument(
        "--legacy-database-url", default=None,
        help="default: env LEGACY_WHATSAPP_DATABASE_URL (NÃO use DATABASE_URL — no container api"
        " essa var já é o Postgres do próprio Stack360)",
    )
    p.add_argument("--limit", type=int, default=200)
    args = p.parse_args(argv)

    import os

    legacy_url = args.legacy_database_url or os.environ.get("LEGACY_WHATSAPP_DATABASE_URL")
    if not legacy_url:
        sys.exit("faltou --legacy-database-url ou env LEGACY_WHATSAPP_DATABASE_URL")

    report = recall_check(legacy_url, limit=args.limit)
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
