#!/usr/bin/env python3
"""Experiment 113e -- registered single-change follow-up to exp 113d FAIL.

Diagnosis (artifacts/fable-bench113d-20260922/RESULTS.md, design doc 113d):
113d's fallback consumption gate stopped every genuine prefix answer but
over-abstained on legitimate fallback answers, because the gate's cue set
for a relation R only holds R's FORWARD surfaces (REL_CUES92 keys). Three
blind spots: (1) reversed-relation frames the parser itself uses to frame
facts -- author_of / written_by / founder_of / ... -- have NO entry in
REL_CUES92, so the gate deletes nothing and any leftover cue fires
(Fable-Edit reversal 35/50); (2) toy-family walked relations (mother, job,
pet, birth_year, ...) likewise have no entry (L5-Z1 52/60, P4 29/30);
(3) qualifier/descriptive leftovers (088 `position`, 096 `origin`,
"in 2019") -- out of scope for this change.

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to loop113d):

  The gate's cue set for R = every surface phrase the existing code tables
  -- the relation maps the parser itself uses to frame facts -- canonicalise
  to R OR to inverse(R), built mechanically below (function
  build_cue_sets()): REL_CUES92 (B92, itself B73.REL_MENTION_CUES +
  EXTRA_REL_CUES), LE.RELATION_MAP (fable_listening_english), the closed
  maps (fable_webred_frames.CLOSED_MAP, asserted equal to the relations.json
  closed_map that feeds D.CLASSES), and the inverse-relation tables (the
  parser's own B73.REV_OF_NOUNS / B73.REV_BY_VERBS plus the frozen wikidata
  INVERSE_TABLE). No hand-added words, no words taken from any benchmark
  item: every added cue is printed with its source table by --print-cues
  into fable_bench113e_added_cues.json. frame_consumes_question_113e() is
  otherwise 113c's frame_consumes_question() verbatim (same qualifier rule,
  same longest-first substring deletion, same entity-span deletion, same
  word-boundary single-word leftover test, same _DROP_CUES exemptions).

Concretely this means: a walked relation with no REL_CUES92 entry resolves
through the tables (author_of -> author via REV_OF_NOUNS; written_by ->
author via the REV_BY_VERBS verb "written" which is an author cue;
founded_by gains its verb "founded"; mother gains LE's own "mother/mom/mum"
plus the closed map; birth_year/pet/job gain at least their own
space-spelled surface, which the parser's FakeEars._relation rule maps back
to the snake key), and each relation additionally deletes the surfaces of
its declared inverse (wikidata edges that hit our vocabulary: creator <->
notable_work, capital <-> capital_of, officeholder <-> position_held,
manufacturer <-> product_or_material_produced, spouse <-> spouse).

No existing file is edited; everything new lives in this file.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop113e_agent.py --daemon --dir DIR \\
    --config artifacts/fable-bench113e-20260922/loop113e-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (cues + REV tables)
import fable_bench92_english_arm as B92  # noqa: E402 (REL_CUES92)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal)
import fable_listening_english as LE  # noqa: E402 (RELATION_MAP surfaces)
import fable_loop102_agent as L102  # noqa: E402 (fallback chain)
import fable_loop113_agent as L113  # noqa: E402 (CHAIN_MISS_TEXT)
import fable_loop113b_agent as L113B  # noqa: E402 (loop shape)
import fable_loop113c_agent as L113C  # noqa: E402 (gate logic + exemptions)
import fable_loop113d_agent as L113D  # noqa: E402 (router shape, subclassed)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples)
import fable_relcanon63_canon as RC63  # noqa: E402 (INVERSE_TABLE, read-only)
import fable_webred_frames as WF  # noqa: E402 (CLOSED_MAP, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker)
    HardGate46Sleeper, NotebookThinker)


def norm_rel(name: object) -> str:
    """Relation-name key: lowercase, whitespace runs -> single underscore."""
    return "_".join(str(name).strip().lower().split())


def norm_surf(surface: object) -> str:
    """Surface-phrase key: lowercase, whitespace runs -> single space."""
    return " ".join(str(surface).strip().lower().split())


def _own_surfaces(node: str) -> set[str]:
    """The relation's own spellings (snake + space-spelled).

    Mechanical fixed rule (underscores <-> spaces), no benchmark input: it is
    the parser's own canonicalisation (cf. FakeEars._relation, which maps the
    space-spelled surface back to the snake key). Guarantees every walked
    relation deletes at least its own mention.
    """
    out = {node, node.replace("_", " ")}
    return {s for s in out if s}


def build_cue_sets() -> tuple[dict[str, frozenset[str]],
                              dict[str, list[str]],
                              dict[str, dict[str, str]],
                              dict[str, str]]:
    """Mechanically build the 113e cue sets from the code tables only.

    Returns (CUES, ADDED, SOURCES, COMP):
      CUES[node] = frozenset of every surface phrase the tables canonicalise
        to a relation in node's inverse-equivalence component.
      ADDED[node] = sorted(CUES[node] - REL_CUES92[node]) for nodes that are
        REL_CUES92 keys (the per-relation added words for the artifact).
      SOURCES[node] = {cue: source-table tag} for audit.
      COMP[node] = component root for the skip-set (walked components).
    """
    base: dict[str, set[str]] = {}
    for rel, cues in B92.REL_CUES92.items():
        node = norm_rel(rel)
        for cue in cues:
            c = norm_surf(cue)
            if c:
                base.setdefault(node, set()).add(c)
    le_cues: dict[str, set[str]] = {}
    for surface, value in LE.RELATION_MAP.items():
        s = norm_surf(surface)
        if s:
            le_cues.setdefault(norm_rel(value), set()).add(s)
    closed_cues: dict[str, set[str]] = {}
    for webred_name, closed_name in WF.CLOSED_MAP.items():
        s = norm_surf(webred_name)
        if s:
            closed_cues.setdefault(norm_rel(closed_name), set()).add(s)
    try:
        rel_json = json.loads(
            (SCRIPTS.parent / "data" / "open" / "webred" / "frames"
             / "relations.json").read_text(encoding="utf-8"))
        meta_closed = dict(rel_json.get("closed_map") or {})
        assert meta_closed == dict(WF.CLOSED_MAP), (
            "relations.json closed_map drifted from CLOSED_MAP: "
            f"{sorted(set(meta_closed.items()) ^ set(WF.CLOSED_MAP.items()))[:6]}")
    except AssertionError:
        raise
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"cannot verify closed maps: {exc!r}")
    # Union-find over relation-name nodes for the inverse edges.
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    edges: list[list[str]] = []
    rev_cues: dict[str, set[str]] = {}
    for noun, key in B73.REV_OF_NOUNS.items():
        n, k = norm_rel(noun), norm_rel(key)
        s = norm_surf(noun)
        if s:
            rev_cues.setdefault(k, set()).add(s)
        union(n, k)
        edges.append([f"REV_OF:{noun}", n, k])
    for verb, key in B73.REV_BY_VERBS.items():
        # The verb surface is a cue of the _by key itself (a surface the
        # table canonicalises to R), but a shared verb is NOT an inverse
        # declaration: no edge is added here (e.g. "founded" must NOT merge
        # founded_by with location_of_formation; they are different
        # relations). Edges come only from declared inverse pairs.
        k = norm_rel(key)
        s = norm_surf(verb)
        if s:
            rev_cues.setdefault(k, set()).add(s)
    for wname, edge in (RC63.INVERSE_TABLE or {}).items():
        try:
            inv = edge["inverse_name"]
        except (KeyError, TypeError):
            continue
        a, b = norm_rel(wname), norm_rel(inv)
        union(a, b)
        edges.append([f"WIKIDATA:{wname}", a, b])
    members: dict[str, set[str]] = {}
    for node in (set(base) | set(le_cues) | set(closed_cues)
                 | set(rev_cues) | set(parent)):
        members.setdefault(find(node), set()).add(node)
    cues: dict[str, frozenset[str]] = {}
    sources: dict[str, dict[str, str]] = {}
    for root, comp in members.items():
        merged: set[str] = set()
        src: dict[str, str] = {}
        for m in sorted(comp):
            for tag, table in (("REL_CUES92", base), ("LE", le_cues),
                               ("CLOSED_MAP", closed_cues),
                               ("REV", rev_cues)):
                for c in sorted(table.get(m, ())):
                    if c not in src:
                        src[c] = f"{tag}:{m}"
                    merged.add(c)
            for c in sorted(_own_surfaces(m)):
                if c not in src:
                    src[c] = f"OWN:{m}"
                merged.add(c)
        for m in comp:
            cues[m] = frozenset(merged)
            sources[m] = dict(src)
    added: dict[str, list[str]] = {}
    for rel in B92.REL_CUES92:
        node = norm_rel(rel)
        extra = sorted(set(cues.get(node, ())) - base.get(node, set()))
        if extra:
            added[rel] = extra
    # Nodes the tables know that REL_CUES92 never keyed (reversal/toy walked
    # relations): report their full derived cue set as added.
    for node in sorted(cues):
        if node not in {norm_rel(r) for r in B92.REL_CUES92}:
            if cues[node]:
                added.setdefault(f"~{node}", sorted(cues[node]))
    comp_of = {node: find(node) for node in
               (set(base) | set(le_cues) | set(closed_cues)
                | set(rev_cues) | set(parent))}
    return cues, added, sources, comp_of


CUES113E, ADDED113E, SOURCES113E, COMP113E = build_cue_sets()


def _rebuild_edges_for_artifact() -> list[list[str]]:
    out: list[list[str]] = []
    for noun, key in B73.REV_OF_NOUNS.items():
        out.append(["REV_OF_NOUNS", str(noun), str(key)])
    for verb, key in B73.REV_BY_VERBS.items():
        out.append(["REV_BY_VERBS", str(verb), str(key)])
    for wname, edge in (RC63.INVERSE_TABLE or {}).items():
        try:
            out.append(["WIKIDATA_INVERSE", str(wname),
                        str(edge["inverse_name"])])
        except (KeyError, TypeError):
            continue
    return out


CUE_EDGES113E = _rebuild_edges_for_artifact()

# 113c exemptions reused byte-for-byte.
_DROP_CUES = L113C._DROP_CUES
_WORD_RES = L113C._WORD_RES
_word_re = L113C._word_re
_norm_q = L113C._norm_q
has_trailing_qualifier = L113C.has_trailing_qualifier


def cue_set_for(walked_relation: object) -> frozenset[str]:
    """Cue set for one walked relation name (R or inverse(R) surfaces)."""
    node = norm_rel(walked_relation)
    hit = CUES113E.get(node)
    if hit:
        return hit
    return frozenset(_own_surfaces(node))


def frame_consumes_question_113e(
        question: str, rels: list[str],
        triples: list[tuple[str, str, str]] | None = None) -> bool:
    """113c's frame_consumes_question with the 113e cue sets.

    Steps identical to 113c (trailing-year qualifier -> False; delete every
    occurrence of the walked relations' own mention cues longest-first by
    SUBSTRING; delete entity-mention spans longest-first; any OTHER
    relation's cue still matching the remainder -> False; else True) except:
    (a) each walked relation deletes cue_set_for(rel), i.e. the surfaces of
    R and of inverse(R) from the code tables; (b) the leftover scan uses the
    component cue set of each REL_CUES92 key and skips every key whose
    component intersects the walked set.
    """
    q = _norm_q(question)
    if has_trailing_qualifier(question):
        return False
    walked = [str(r) for r in (rels or [])]
    if not walked:
        return False
    walked_nodes = {norm_rel(r) for r in walked}
    walked_cues: set[str] = set()
    for rel in walked:
        walked_cues |= set(cue_set_for(rel))
    work = q
    for cue in sorted(walked_cues, key=len, reverse=True):
        if cue:
            work = work.replace(cue, " ")
    if triples:
        names = sorted({str(s) for s, _, _ in triples}
                       | {str(o) for _, _, o in triples},
                       key=len, reverse=True)
        for name in names:
            n = " ".join(str(name).split()).lower()
            if n:
                work = work.replace(n, " ")
    skip_roots = {COMP113E.get(node, node) for node in walked_nodes}
    for rel in B92.REL_CUES92:
        node = norm_rel(rel)
        if node in walked_nodes or COMP113E.get(node, node) in skip_roots:
            continue
        for cue in CUES113E.get(node, ()):
            c = cue
            if c in _DROP_CUES:
                continue
            if " " in c:
                if c in work:
                    return False
            elif _word_re(c).search(work):
                return False
    return True


frame_consumes_question = frame_consumes_question_113e


class Loop113eEars(L113D.Loop113dEars):
    """Loop113dEars with the 113e inverse-expanded consumption gate.

    Routing identical to 113d (composer branches + guarded loop102 fallback);
    every frame_consumes_question() call now uses the 113e cue sets. Teach
    path and all non-ask actions inherit 113d byte-identical.
    """

    name = "loop113e-gate-inverse-cues"

    def _fallback_guarded(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        actions = L102.Loop102Ears.hear(self, turn)
        if text and text.rstrip().endswith("?") and self.nb is not None:
            triples = L90.notebook_triples(self.nb)
            for act in actions:
                if act.get("act") != "ask":
                    continue
                rels = list(act.get("relations") or (
                    [act["relation"]] if act.get("relation") else []))
                if not rels:
                    continue
                if not frame_consumes_question_113e(text, rels, triples):
                    self.last_stage, self.last_score = (
                        "loop113e-fallback-partial", 1.0)
                    return [{"act": "clarify",
                              "text": L113.CHAIN_MISS_TEXT}]
        return actions

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?"):
            if L102.is_hearsay(text):  # F1 preserved on questions
                self.last_stage, self.last_score = "loop113e-hearsay", 1.0
                return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
            if self.nb is None:
                return self._delegate(turn)
            triples = L90.notebook_triples(self.nb)
            frame = B92.compose_n_hop(text, triples)
            if frame is not None:
                if frame_consumes_question_113e(text, list(frame[1]),
                                                triples):
                    hit = L113.compound_subject_hit(triples, frame[0],
                                                    list(frame[1]))
                    if hit is None:
                        self.last_stage, self.last_score = (
                            "loop113e-nhop", 1.0)
                        return [{"act": "ask", "name": frame[0],
                                 "relations": list(frame[1]),
                                 "stage": "loop113e"}]
                    self.last_stage, self.last_score = (
                        "loop113e-compound-guard", 1.0)
                    return [{"act": "clarify",
                              "text": L113.CHAIN_MISS_TEXT}]
                self.last_stage, self.last_score = (
                    "loop113e-partial", 1.0)
                return self._fallback_guarded(turn)
            frame2 = B73.compose_question(text, triples)
            if frame2 is not None:
                if (L113.is_explicit_question(text)
                        and frame_consumes_question_113e(
                            text, list(frame2[1]), triples)):
                    self.last_stage, self.last_score = (
                        "loop113e-explicit", 1.0)
                    return [{"act": "ask", "name": frame2[0],
                             "relations": list(frame2[1]),
                             "stage": "loop113e"}]
                if not L113.is_explicit_question(text):
                    self.last_stage, self.last_score = (
                        "loop113e-nonexplicit", 1.0)
                    return [{"act": "clarify",
                              "text": L113.CHAIN_MISS_TEXT}]
                self.last_stage, self.last_score = (
                    "loop113e-partial", 1.0)
                return self._fallback_guarded(turn)
            return self._fallback_guarded(turn)
        return super().hear(turn)


class Loop113eAgentLoop(L113B.Loop113bAgentLoop):
    """Loop113bAgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG113E: dict = copy.deepcopy(L113D.DEFAULT_CONFIG113D)
DEFAULT_CONFIG113E["ears"]["stand_in"] = (
    "Loop113eEars (113d router + 113e consumption gate: the cue set for R "
    "is every surface phrase the code tables -- REL_CUES92, "
    "LE.RELATION_MAP, the closed maps, the inverse-relation tables -- "
    "canonicalise to R or to inverse(R), built mechanically with no "
    "hand-added words; a fallback ask whose frame leaves relation words / "
    "qualifiers unconsumed becomes the honest abstain instead of a prefix "
    "answer) over Loop102Ears pre-filter over Loop96Ears = GuardedEars91 "
    "over ChainEars(bench73 template + FakeEars templates); teach path "
    "identical to loop102")
DEFAULT_CONFIG113E["daemon"]["module"] = "Loop113eDaemon (this file)"


def build_agent113e(cfg: dict | None = None) -> Loop113eAgentLoop:
    """Build the loop113b agent shape with Loop113eEars on the question side."""
    cfg = dict(DEFAULT_CONFIG113E, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop113eAgentLoop(
        state_dir, ears=Loop113eEars(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    return loop


class Loop113eDaemon(L113D.Loop113dDaemon):
    """Loop113dDaemon shape with the loop113e agent inside (mailbox identical)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent113e(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon113e(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop113eDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def cmd_print_cues(path: str) -> int:
    payload = {
        "how": ("cue set for R = every surface phrase REL_CUES92, "
                "LE.RELATION_MAP, CLOSED_MAP (+relations.json closed_map, "
                "asserted equal), B73.REV_OF_NOUNS / B73.REV_BY_VERBS and "
                "the wikidata INVERSE_TABLE canonicalise to R or inverse(R); "
                "plus each node's own snake/space spellings (fixed rule). "
                "No hand-added words; no benchmark words."),
        "n_nodes": len(CUES113E),
        "cues": {k: sorted(v) for k, v in sorted(CUES113E.items())},
        "added_vs_relcues92": {k: v for k, v in sorted(ADDED113E.items())},
        "cue_sources": {k: dict(sorted(v.items()))
                        for k, v in sorted(SOURCES113E.items())},
        "inverse_edges": sorted(CUE_EDGES113E),
    }
    Path(path).write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    n_added = sum(len(v) for v in ADDED113E.values())
    print(f"nodes={len(CUES113E)} relations_with_added={len(ADDED113E)} "
          f"added_cues={n_added} -> {path}")
    return 0


def cmd_selftest(_args) -> int:
    fails: list[str] = []

    def check(cond: bool, tag: str) -> None:
        print(("ok  " if cond else "FAIL"), tag, flush=True)
        if not cond:
            fails.append(tag)

    triples = [("Oaken Melodies", "author_of", "Marisol Underbough"),
               ("Elke", "mother", "Mira"), ("Mira", "spouse", "Jon"),
               ("Mira", "birth_year", "2019")]
    # Reversal frames the parser uses: gate must now consume (113d: False).
    check(frame_consumes_question_113e("Who is the author of Oaken Melodies?",
                                       ["author_of"], triples),
          "rev-author_of-consumes")
    check(frame_consumes_question_113e("Who written by Oaken Melodies?",
                                       ["written_by"], triples),
          "rev-written_by-consumes")
    check(frame_consumes_question_113e("Who is the founder of Silver Feasts?",
                                       ["founder_of"], triples),
          "rev-founder_of-consumes")
    # Toy-family walked relations gain table surfaces / own spellings.
    check(frame_consumes_question_113e("Who is Elke's mother's husband?",
                                       ["mother", "husband"], triples),
          "toy-mother-husband-consumes")
    check(frame_consumes_question_113e("Who is Mira's birth year?",
                                       ["birth_year"], triples),
          "toy-birth_year-consumes")
    # Genuine prefixes must STILL abstain (113d fixes hold).
    check(not frame_consumes_question_113e(
        "What is the language of the country of citizenship of "
        "the spouse of CM Punk?", ["spouse", "country_of_citizenship"],
        triples), "prefix-language-still-prefix")
    check(not frame_consumes_question_113e(
        "What is the country of origin of Boris Vilkitsky, in terms of "
        "citizenship, that has a notable founder?",
        ["country_of_citizenship", "founded_by"], triples),
          "edit096-origin-still-prefix")
    check(not frame_consumes_question_113e(
        "Who holds the chairperson position at the university where C. "
        "Douglas Dillon received their education?",
        ["educated_at", "chairperson"], triples),
          "edit088-position-still-prefix")
    check(not frame_consumes_question_113e("What is Mira's city in 2019?",
                                           ["city"], triples),
          "qualifier-still-prefix")
    # Sanity: exact short frames still consume; empty rels never consume.
    check(frame_consumes_question_113e("Who is C00's capital?",
                                       ["capital"], None),
          "exact-2hop-consumes")
    check(not frame_consumes_question_113e("Who is C00's capital?", [],
                                           None),
          "empty-rels-false")
    # Daemon shape: the 113d crash attribute exists before any sealing use.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as tmp:
        d = Loop113eDaemon(tmp, cfg={"sleep_threshold": 10 ** 9},
                           idle_seconds=30.0)
        check(float(d.idle_seconds) == 30.0, "daemon-idle_seconds")
    print("SELFTEST", "PASS" if not fails else f"FAIL {fails}", flush=True)
    return 1 if fails else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 113e inverse-cue loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop113d)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG113E to PATH and exit")
    parser.add_argument("--print-cues", default=None,
                        help="write cue-set audit JSON to PATH and exit")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG113E)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    if args.print_cues:
        return cmd_print_cues(args.print_cues)

    if args.selftest:
        return cmd_selftest(args)

    cfg = copy.deepcopy(DEFAULT_CONFIG113E)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon113e(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent113e(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
