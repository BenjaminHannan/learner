#!/usr/bin/env python3
"""Experiment 77: ADDITIVE fixes for the three confirmed redteam67 bugs.

Nothing here edits any existing file. The three unfixed modules
(fable_thought49_notebook, fable_qual56_reasoner, fable_notebook_contract)
are imported read-only and wrapped:

  (1) GatedThoughtNotebook(ThoughtNotebook) -- applies doc-56 rule 2 inside
      the qualifier gate: an unqualified taught row wins over qualified rows
      for the same subject+relation, so a qualified row answers only when
      the question carries a matching qualifier AND no unqualified taught
      row exists. This makes ThoughtNotebook.ask agree with
      QualifierAwareReasoner (redteam finding 1, critical).

  (2) QualifierAwareReasoner77 -- the qual56 hop loop with one change only:
      qualifier matching treats bool True/False and the strings
      "true"/"false" as equal, case-insensitively (redteam finding 2).
      Nothing else is new; the comparison for every other value is the
      parent's exact string equality.

  (3) verify_full(notebook_dir) + open_verified(...) (+ VerifiedNotebook)
      -- re-hash every events.jsonl line INCLUDING the tail. Middle-line
      edits are already caught by the successor's prev link; the tail has
      no successor, so a maintained sidecar digest (events.fix77.seal.json)
      records the last verified tail hash and any tail edit afterwards
      raises LogCorrupt (redteam finding 3).

Honesty note on (3): a last-line value edit that keeps valid JSON and a
valid prev link is byte-identical to a legitimately appended line, so no
pure function of events.jsonl alone can detect it. Tail-evidence therefore
needs one piece of external state (the sidecar). The trust model is the
same as the existing chain's: the FIRST seal must happen on a trusted
state; every later verify/open detects changes since. VerifiedNotebook
(C.Notebook subclass) maintains the sidecar on every append and verifies
on every clean open, so flows that write only through it are fully
tail-evident; open_verified() gives the same guarantee to any factory
(including the plain contract Notebook) provided it sealed the directory
before the tamper.

Plain software, offline, Mac CPU. No model, no training, no guessing.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only; never edited)
import fable_qual56_reasoner as Q56  # noqa: E402 (read-only; never edited)
import fable_reasoner50 as R50  # noqa: E402 (read-only; never edited)
from fable_thought49_notebook import ThoughtNotebook  # noqa: E402 (read-only)
from fable_thought49_schema import SchemaError, ThoughtV2, norm_relation  # noqa: E402

ANS = R50.ANS
ANS_IDX = R50.ANS_IDX
ANSWER_THRESHOLD = R50.ANSWER_THRESHOLD
MAX_HOPS = R50.MAX_HOPS

SEAL_NAME = "events.fix77.seal.json"


# ------------------------------------------------------------------ fix 1
class GatedThoughtNotebook(ThoughtNotebook):
    """ThoughtNotebook with doc-56 rule 2 in the gate.

    Only _gate is overridden. When the active rows for one hop contain an
    unqualified taught row, every qualified row is dropped -- even one the
    question's qualifiers would match -- because the unqualified claim is
    unconditional and always wins. Otherwise the parent gate runs unchanged.
    """

    def _gate(self, rows: list, required: dict):
        indexed = [(row, self._index_one(row["fact_id"])) for row in rows]

        def is_unqualified_taught(row: dict, thought) -> bool:
            if thought is None:
                # Foreign event (no v2 record): qualifier-free, answers as
                # before; counts as unqualified with its stored source.
                return row.get("source") == "taught"
            return thought.source == "taught" and not thought.qualifiers

        if any(is_unqualified_taught(row, th) for row, th in indexed):
            kept, dropped = [], False
            for row, th in indexed:
                if th is not None and th.qualifiers:
                    dropped = True
                    continue
                kept.append(row)
            return kept, dropped
        return super()._gate(rows, required)


# ------------------------------------------------------------------ fix 2
def value_equals77(row_value, provided) -> bool:
    """Qualifier value equality with the bool fix and nothing else new.

    Identical to qual56.value_equals except for boolean row values, where
    it uses ThoughtNotebook._value_matches' bool branch: a real bool must
    equal the stored boolean, and any other provided value compares
    case-insensitively against the stored "true"/"false" literal.
    """
    target = row_value.to_v1_value()
    if isinstance(provided, dict):
        return provided == target
    if "entity" in target:
        return str(provided) == target["entity"]
    if row_value.kind == "boolean":
        if isinstance(provided, bool):
            return provided is row_value.boolean
        return str(provided).strip().lower() == target.get("literal")
    return str(provided) == target["literal"]


def qualifiers_match77(qualifiers, required: dict) -> bool:
    """Same as qual56.qualifiers_match but via value_equals77."""
    if not required:
        return False
    need = {norm_relation(k): v for k, v in required.items()}
    for qual in qualifiers:
        key = norm_relation(qual.relation)
        if key not in need or not value_equals77(qual.value, need[key]):
            return False
    return True


def thought_of77(fact: dict):
    try:
        return ThoughtV2.from_v1(fact)
    except SchemaError:
        return None


def fid_num77(fid: str) -> int:
    return int(fid[1:])


def fid_str77(num: int) -> str:
    return f"F{num:05d}"


def filtered_view77(nb, rel: str, required: dict):
    """Same as qual56.filtered_view but via qualifiers_match77.

    Selection order unchanged: active + answering source only ->
    qualifier gate -> unqualified-taught priority (rule 2) -> best source
    first, newest within a source (contract order).
    """
    functional = rel in nb.functional
    kept_by_subj: dict[str, list[dict]] = {}
    dropped = False
    for fid, fact in nb.facts.items():
        if fact["relation"] != rel:
            continue
        if fact["source"] not in ANS or not nb.active(fid):
            continue
        thought = thought_of77(fact)
        quals = thought.qualifiers if thought is not None else ()
        if quals and not qualifiers_match77(quals, required):
            dropped = True
            continue
        kept_by_subj.setdefault(fact["subject"], []).append((fact, bool(quals)))
    out: dict[str, tuple] = {}
    for subj, rows in kept_by_subj.items():
        if any(f["source"] == "taught" and not q for f, q in rows):
            rows = [(f, q) for f, q in rows if not q]
            if not rows:
                dropped = True
                continue
        facts = [f for f, _ in rows]
        facts.sort(key=lambda f: (ANS_IDX[f["source"]], -f["n"]))
        best = facts[0]["source"]
        facts = [f for f in facts if f["source"] == best]
        src = ANS_IDX[best]
        if functional or len(facts) == 1:
            row = facts[0]
            val = row["value"]
            num = fid_num77(row["fact_id"])
            if "entity" in val:
                out[subj] = ("E", val["entity"], num, src)
            else:
                out[subj] = ("L", str(val["literal"]), num, src)
        else:
            shows = []
            for row in facts:
                val = row["value"]
                if "entity" in val:
                    shows.append((nb.entities[val["entity"]], fid_num77(row["fact_id"])))
                else:
                    shows.append((str(val["literal"]), fid_num77(row["fact_id"])))
            out[subj] = ("M", shows, src)
    return out, dropped


class QualifierAwareReasoner77(Q56.QualifierAwareReasoner):
    """QualifierAwareReasoner with bool qualifier equality fixed.

    Subclass-and-filter like the parent: answer() is the parent's hop loop
    verbatim except the per-hop views come from filtered_view77. Learned-word
    stage expansion reuses the parent's tables untouched.
    """

    def answer(self, question: dict, notebook) -> dict:
        nb = notebook
        self._sync(nb)
        name = question.get("name", "")
        relations = list(question.get("relations") or [])
        eid = question.get("entity_id")

        def rec(status: str, fields: dict) -> dict:
            return {"kind": "answer", "status": status, "name": name,
                    "relations": relations, "fields": fields}

        if not relations or len(relations) > MAX_HOPS:
            return rec(C.BAD_REQUEST, {"reason": f"need 1-{MAX_HOPS} hops"})
        try:
            hop_req = Q56.hop_requirements(relations, question.get("qualifiers"))
        except Q56.BadQualifiers:
            return rec(C.BAD_REQUEST, {
                "reason": "qualifiers must be None, a dict, or a list parallel to relations"})

        if eid is None:
            found = nb.resolve(name)
            if found.status != C.OK:
                return rec(found.status, dict(found.detail))
            eid = found.detail["entity_id"]
        elif eid not in nb.entities:
            return rec(C.BAD_REQUEST, {"reason": "unknown entity id"})

        views: dict[tuple, tuple] = {}

        def view_at(hop: int, rel: str):
            key = (hop, rel)
            if key not in views:
                views[key] = filtered_view77(nb, rel, hop_req[hop])
            return views[key]

        def known(rel: str) -> bool:
            for fid, fact in nb.facts.items():
                if fact["relation"] == rel:
                    return True
            return rel in nb.functional

        def stages(tok: str, hop: int):
            if tok in self.words:
                return self.stage_options(self.words[tok])
            if known(tok):
                return [("skill", tok, 1.0)]
            return None

        trail: list[int] = []
        trail_src: list[int] = []
        subject = eid
        kind = "entity"
        lit_text = lit_producer = None
        conf = 1.0

        def fields_missing(hop: int, rel: str, qualified: bool) -> dict:
            detail = {"subject": nb.entities[subject], "relation": rel,
                      "hop": hop, "trail": [fid_str77(n) for n in trail]}
            if qualified:
                detail["reason"] = "qualified"
            return detail

        def fields_broken(hop: int) -> dict:
            return {"subject": nb.entities[subject], "relation": lit_producer,
                    "value": lit_text, "hop": hop,
                    "trail": [fid_str77(n) for n in trail]}

        for hop, tok in enumerate(relations):
            if kind != "entity":
                return rec(C.BROKEN_CHAIN, fields_broken(hop))
            stage_list = stages(tok, hop)
            if stage_list is None:
                return rec(C.MISSING_FACT, fields_missing(hop + 1, tok, False))
            for opt, arg, weight in stage_list:
                if kind != "entity":
                    return rec(C.BROKEN_CHAIN, fields_broken(hop))
                if opt == "keep":
                    continue
                conf *= weight
                out, dropped = view_at(hop, arg)
                entry = out.get(subject)
                if entry is None:
                    return rec(C.MISSING_FACT, fields_missing(hop + 1, arg, dropped))
                tag = entry[0]
                if tag == "M":
                    shows, src = entry[1], entry[2]
                    return rec(C.OK, {"answer": ", ".join(s for s, _ in shows),
                                      "trail": [fid_str77(n) for n in trail]
                                      + [fid_str77(n) for _, n in shows],
                                      "source": ANS[src], "multi": True})
                trail.append(entry[2])
                trail_src.append(entry[3])
                if tag == "L":
                    kind, lit_text, lit_producer = "literal", entry[1], arg
                else:
                    subject = entry[1]

        if kind != "entity":
            return rec(C.OK, {"answer": lit_text,
                              "trail": [fid_str77(n) for n in trail],
                              "source": ANS[trail_src[-1]]})
        if conf < ANSWER_THRESHOLD:
            return rec(C.MISSING_FACT,
                       fields_missing(len(relations), relations[-1], False))
        return rec(C.OK, {"answer": nb.entities[subject],
                          "trail": [fid_str77(n) for n in trail],
                          "source": ANS[trail_src[-1]]})


# ------------------------------------------------------------------ fix 3
def _sha77(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln for ln in lines if ln.strip()]


def _read_seal(root: Path) -> dict | None:
    seal = root / SEAL_NAME
    if not seal.exists():
        return None
    try:
        data = json.loads(seal.read_text(encoding="utf-8"))
        if isinstance(data.get("n"), int) and isinstance(data.get("sha"), str):
            return data
    except (OSError, ValueError):
        pass
    return None


def _write_seal(root: Path, n: int, sha: str) -> None:
    (root / SEAL_NAME).write_text(
        json.dumps({"n": n, "sha": sha, "by": "fable_fix77"}, sort_keys=True)
        + "\n", encoding="utf-8")


def verify_full(notebook_dir) -> dict:
    """Re-hash every events.jsonl line INCLUDING the tail.

    Checks each line parses, each prev link matches the running sha (names
    the line number), the stored prefix seal still matches (catches edits
    at or before the sealed line), and -- when nothing was appended since
    the seal -- the current tail hash matches the sealed tail hash (catches
    last-line edits). A torn final line raises LogCorrupt: repair it with
    Notebook.repair_torn_tail() first, then verify again. On success the
    seal advances to the current tail and a record is returned.
    """
    root = Path(notebook_dir)
    path = root / C.LOG_NAME
    if not path.exists():
        _write_seal(root, 0, C.GENESIS)
        return {"lines": 0, "sealed": True, "note": "empty log sealed"}
    raw = path.read_text(encoding="utf-8").split("\n")
    if raw and raw[-1] == "":
        raw.pop()
    lines = [ln for ln in raw if ln.strip()]
    running = C.GENESIS
    for i, line in enumerate(lines):
        try:
            event = json.loads(line)
        except ValueError as exc:
            if i == len(lines) - 1:
                raise C.LogCorrupt(
                    f"line {i + 1}: torn tail (repair with repair_torn_tail first)") from exc
            raise C.LogCorrupt(f"line {i + 1}: {exc}") from exc
        try:
            prev = event["prev"]
        except (KeyError, TypeError) as exc:
            raise C.LogCorrupt(f"line {i + 1}: {exc}") from exc
        if prev != running:
            raise C.LogCorrupt(f"line {i + 1}: hash chain broken")
        running = _sha77(line)
    seal = _read_seal(root)
    if seal is not None:
        sealed_n = seal["n"]
        if sealed_n > len(lines):
            raise C.LogCorrupt(
                f"log truncated: sealed {sealed_n} lines, file has {len(lines)}")
        if sealed_n > 0 and _sha77(lines[sealed_n - 1]) != seal["sha"]:
            raise C.LogCorrupt(
                f"line {sealed_n}: tail/prefix edit detected against the seal")
        if sealed_n == len(lines) and running != seal["sha"]:
            raise C.LogCorrupt("last line edited: tail hash differs from the seal")
    _write_seal(root, len(lines), running)
    return {"lines": len(lines), "sealed": True, "tail": running[:16]}


def open_verified(notebook_dir, factory=None):
    """Verify the log (raises LogCorrupt on any edit incl. the tail), then
    load it with factory (default: the plain contract Notebook)."""
    verify_full(notebook_dir)
    return (factory or C.Notebook)(notebook_dir)


class VerifiedNotebook(C.Notebook):
    """The contract Notebook that maintains the fix-77 tail seal.

    Identical read/write semantics (same statuses, same torn-tail flag and
    repair flow); additionally every append advances the sidecar seal and
    every clean open verifies links plus the sealed tail, raising
    LogCorrupt on a last-line edit. A torn tail still loads with the flag
    set (legacy behaviour) instead of raising, so crash recovery is
    unchanged.
    """

    def __init__(self, root) -> None:
        super().__init__(root)
        if self.torn_tail:
            return
        verify_full(self.root)

    def _append(self, event: dict) -> None:
        super()._append(event)
        try:
            _write_seal(self.root, len(self.events), self.last_sha)
        except OSError:
            pass
