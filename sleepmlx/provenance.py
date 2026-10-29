"""Read-only research-note provenance audit. Attribution is not truth verification.

This module does not participate in training admission. Unknown historical notes
keep unknown origin; an unavailable ledger must never turn research into legacy.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from .lessons import read_notes

MAX_LEDGER_BYTES = 16 * 1024 * 1024
HASH = re.compile(r"^[a-f0-9]{64}$")


def fact_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _date(value):
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("invalid expiry")
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("invalid expiry")
    return value


def _prepare(row):
    if not isinstance(row.get("note_id"), str) or not row["note_id"] or not HASH.fullmatch(str(row.get("fact_sha256", ""))):
        raise ValueError("invalid note identity")
    if row.get("topic") is not None and not isinstance(row["topic"], str):
        raise ValueError("invalid note topic")
    if row.get("origin") != "learn-research" or not isinstance(row.get("context"), dict):
        raise ValueError("invalid research origin")
    context = row["context"]
    if not isinstance(context.get("run_id"), str) or not context["run_id"]:
        raise ValueError("missing run identity")
    for name in ("thread_id", "helper_id"):
        if context.get(name) is not None and not isinstance(context[name], str):
            raise ValueError("invalid context")
    attribution = row.get("attribution")
    if not isinstance(attribution, dict) or attribution.get("verified") is not False or attribution.get("status") not in ("attributed", "unattributed"):
        raise ValueError("invalid attribution")
    source = attribution.get("source")
    if attribution["status"] == "attributed":
        from urllib.parse import urlsplit
        if not isinstance(source, dict):
            raise ValueError("missing source")
        if not isinstance(source.get("url"), str):
            raise ValueError("invalid source URL")
        url = urlsplit(source["url"])
        if url.scheme not in ("http", "https") or not url.netloc or url.username or url.password:
            raise ValueError("invalid source URL")
        quote = source.get("quote")
        if not isinstance(quote, str) or not 12 <= len(quote.encode("utf-16-le")) // 2 <= 600 or source.get("quote_sha256") != fact_hash(quote):
            raise ValueError("invalid quote hash")
        if not HASH.fullmatch(str(source.get("visible_body_sha256", ""))) or not isinstance(source.get("read_id"), str):
            raise ValueError("invalid read identity")
        if type(source.get("page")) is not int or source["page"] < 1 or not isinstance(source.get("read_at"), str):
            raise ValueError("invalid read observation")
    elif source is not None:
        raise ValueError("unattributed source")
    _date(row.get("expires"))


def read_ledger(user_data: Path) -> dict:
    """Validate the entire append-only journal; damaged/unknown formats fail closed."""
    path = Path(user_data) / "memory-provenance.jsonl"
    try:
        with path.open("rb") as stream:
            body = stream.read(MAX_LEDGER_BYTES + 1)
    except FileNotFoundError:
        return {"status": "missing", "transactions": []}
    except OSError:
        return {"status": "unavailable", "transactions": []}
    try:
        if len(body) > MAX_LEDGER_BYTES or (body and not body.endswith(b"\n")):
            raise ValueError("oversized or incomplete ledger")
        prepared, committed = {}, set()
        for line in body.decode("utf-8").splitlines():
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("version") != 1 or not isinstance(row.get("tx_id"), str) or not row["tx_id"]:
                raise ValueError("invalid transaction")
            tx = row["tx_id"]
            if row.get("type") == "research-note-prepare":
                _prepare(row)
                if tx in prepared:
                    raise ValueError("duplicate transaction")
                prepared[tx] = row
            elif row.get("type") == "research-note-commit":
                if tx not in prepared or tx in committed or not isinstance(row.get("committed_at"), str):
                    raise ValueError("invalid commit")
                committed.add(tx)
            else:
                raise ValueError("unknown record type")
        return {"status": "ok", "transactions": [{**row, "committed": tx in committed} for tx, row in prepared.items()]}
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return {"status": "unavailable", "transactions": []}


def audit_notes(user_data: Path, *, today: str | None = None) -> dict:
    """Join note ID + exact stored text hash + topic. Never modifies files/policy."""
    current_date = _date(today) if today is not None else date.today().isoformat()
    ledger = read_ledger(user_data)
    rows = ledger["transactions"]
    notes = []
    for note in read_notes(user_data, exact_text=True):
        digest = fact_hash(note["text_exact"])
        topic = note["topic_exact"] or None
        versions = [r for r in rows if r["note_id"] == note["id"]]
        matches = [r for r in versions if r["fact_sha256"] == digest and r.get("topic") == topic]
        # A failed repeat must not erase an earlier committed record for the
        # same exact version. A prepared-only new body remains visibly pending.
        committed = [r for r in matches if r["committed"]]
        selected = (committed or matches or [None])[-1]
        if ledger["status"] == "unavailable":
            state = "unavailable"
        elif selected:
            state = selected["attribution"]["status"] if selected["committed"] else "pending"
        else:
            state = "stale" if versions else "legacy"
        notes.append({"id": note["id"], "fact_sha256": digest, "topic": topic,
                      "provenance_status": state, "origin": "learn-research" if versions else None,
                      "known_research": bool(versions), "verified": False,
                      "expires": selected.get("expires") if selected else None,
                      "expired": bool(selected and selected.get("expires") and selected["expires"] < current_date)})
    counts = dict(Counter(n["provenance_status"] for n in notes))
    return {"version": 1, "record_only": True, "eligibility_enforced": False,
            "support_status": "not_evaluated", "ledger_status": ledger["status"], "counts": counts,
            "known_research_count": sum(n["known_research"] for n in notes),
            "would_require_support_review": sum(n["known_research"] for n in notes),
            "would_require_provenance_repair": sum(n["provenance_status"] in ("pending", "stale", "unattributed", "unavailable") for n in notes),
            "notes": notes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user_data", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_notes(args.user_data), indent=2))


if __name__ == "__main__":
    main()
