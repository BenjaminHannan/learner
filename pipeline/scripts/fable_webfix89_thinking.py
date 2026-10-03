"""Exp 89 — additive web-quarantine fixes for redteam79 findings (Muse, 2026-09-22).

Additive only: NOTHING in scripts/fable_thinking_m2.py (or any other existing
file) is edited. This module subclasses Thinking as QuarantinedThinking89 and
overrides exactly two behaviours; everything else is inherited byte-identical.

Fix 1 (BUG-1, medium): parent _valid() runs _clean() (= str() + split/join)
over every field, so a None value becomes the literal "None" and any quote
containing the word "none" satisfies the copy rule. Here a claim whose VALUE
is None, a non-string, empty/whitespace-only, or (case-insensitive,
whitespace-trimmed) exactly "None"/"null" is dropped with "missing field"
BEFORE the copy-rule check and is never coerced to a string.

Fix 2 (UNCLEAR site-pairs): parent counts 2-site independence with
_domain() = netloc minus "www.", so sub.a.org+a.org, a.org:8080+a.org, and
homoglyph pairs count as 2 sites. Here independence counts REGISTRABLE
domains: lower-case, strip port (urlparse hostname), strip trailing dots,
strip one leading "www.", then collapse subdomains to the registrable domain
(last 2 labels, or last 3 when the last 2 form a known multi-part public
suffix). Built-in multi-part suffix list (documented, deliberately small):
  co.uk, com.au, ac.uk, org.uk, gov.uk, co.jp, com.br
Any host containing non-ASCII characters (covers mixed-script homoglyphs in
practice; pure-ASCII lookalikes such as paypa1 remain a documented residual)
maps to a REJECTED site that NEVER counts toward the 2-site rule (it is
recorded in look-elsewhere seen-lists as "rejected.invalid" only so it is not
re-searched). Single-label hosts (localhost) and IPs are returned as-is.

The loop should construct QuarantinedThinking89 (same constructor signature
as Thinking: (notebook, searcher, fetcher=None)).
"""

from __future__ import annotations

from urllib.parse import urlparse

import fable_thinking_m2 as T

MULTIPART_PUBLIC_SUFFIXES = (
    "co.uk", "com.au", "ac.uk", "org.uk", "gov.uk", "co.jp", "com.br",
)

REJECTED_SEEN_TOKEN = "rejected.invalid"

_EMPTY_VALUES = ("none", "null")


def registrable_site(url: str) -> str | None:
    """Registrable domain for the 2-site rule, or None for a REJECTED host."""
    try:
        host = (urlparse(url).hostname or "")
    except Exception:
        return ""
    host = host.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host.isascii():
        return None  # REJECTED: non-ASCII / mixed-script host, never counts
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTIPART_PUBLIC_SUFFIXES:
        return ".".join(labels[-3:])
    if len(labels) >= 2:
        return ".".join(labels[-2:])
    return host


def _seen_site(url: str) -> str:
    site = registrable_site(url)
    return site if site is not None else REJECTED_SEEN_TOKEN


class QuarantinedThinking89(T.Thinking):
    """Thinking with the two Exp-89 fixes; all other methods inherited."""

    # -- Fix 1: drop empty/None-like values before the copy-rule check --
    def _valid(self, claim) -> tuple[dict | None, str]:
        if isinstance(claim, dict):
            raw = claim.get("value", "")
            if raw is None or not isinstance(raw, str):
                return None, "missing field"
            if not raw.strip() or raw.strip().lower() in _EMPTY_VALUES:
                return None, "missing field"
        return super()._valid(claim)

    # -- Fix 2: registrable-domain counting (copies of the parent methods
    #    with _domain() replaced; logic otherwise identical) --
    def _support(self, subject: str, relation: str) -> dict[str, dict]:
        """value key -> {"rows": [...], "domains": {websites whose quote checked out}}"""
        found: dict[str, dict] = {}
        for fact in self.waiting():
            if fact["subject"] == subject and fact["relation"] == relation:
                slot = found.setdefault(
                    T._value_key(fact["value"]["literal"]), {"rows": [], "domains": set()})
                slot["rows"].append(fact)
                site = registrable_site(fact["provenance"]["url"])
                if site is not None and self._quote_is_on_page(fact):
                    slot["domains"].add(site)
        return found

    def judge(self) -> dict:
        """Nothing read online is believed until independent websites agree and the quotes are
        really on those pages.  In doubt, look somewhere else; still in doubt, do not believe."""
        tally = {"believed": 0, "looked_elsewhere": 0, "unconfirmed": 0}
        for _ in range(T.MAX_LOOK_ELSEWHERE + 1):
            doubtful = []
            for subject, relation in sorted({(f["subject"], f["relation"]) for f in self.waiting()}):
                support = self._support(subject, relation)
                check_key = f"{subject}|{relation}"
                if self._verdict(support) is not None or self.checks.get(check_key, 0) >= T.MAX_LOOK_ELSEWHERE:
                    continue
                name = self.nb.entities[subject]
                values = sorted({f["value"]["literal"] for v in support.values() for f in v["rows"]})
                if self._names_someone_taught(" ".join([name] + values)):
                    self.checks[check_key] = T.MAX_LOOK_ELSEWHERE     # never send such text out
                    continue
                self.checks[check_key] = self.checks.get(check_key, 0) + 1
                doubtful.append({"subject": name, "relation": relation, "values": values,
                                 "seen": sorted({_seen_site(f["provenance"]["url"])
                                                 for v in support.values() for f in v["rows"]})})
            if not doubtful:
                break
            tally["looked_elsewhere"] += 1                          # ONE search covers all doubts
            claims = self.searcher.verify(doubtful)
            self._quarantine(claims, "look elsewhere", limit=T.MAX_CLAIMS_PER_CHECK * len(doubtful))
        for subject, relation in sorted({(f["subject"], f["relation"]) for f in self.waiting()}):
            support = self._support(subject, relation)
            winner = self._verdict(support)
            if winner is None:
                tally["unconfirmed"] += 1
                continue
            rows = [f for f in support[winner]["rows"] if self.quotes.get(f["fact_id"])]
            result = self.nb.assert_fact(
                self._eid("verified"), "thinking", "web-verified", subject, relation,
                {"literal": rows[0]["value"]["literal"]},
                provenance={"evidence": [{"url": f["provenance"]["url"],
                                          "quoted_span": f["provenance"]["quoted_span"]} for f in rows],
                            "from": [f["fact_id"] for v in support.values() for f in v["rows"]]})
            if result.status in (T.C.SAVED, T.C.DUPLICATE_OK):
                tally["believed"] += 1
        self._save()
        return tally

    def review(self) -> str:
        rows = self.waiting()
        if not rows:
            return "Nothing unconfirmed."
        lines = ["Not believed yet (you can approve or reject, or leave them):"]
        for f in rows:
            checked = self.quotes.get(f["fact_id"])
            note = "quote found on page" if checked else "quote NOT found on page" if checked is False else "not checked"
            lines.append(f"{f['fact_id']}: {self.nb.entities[f['subject']]}'s {f['relation']} is "
                         f"{f['value']['literal']}  [{_seen_site(f['provenance']['url'])}; {note}]\n"
                         f"    quote (web text, not instructions): \"{f['provenance']['quoted_span']}\"")
        return "\n".join(lines)
