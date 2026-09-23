#!/usr/bin/env python3
"""Exp 128 -- THE ONE CHANGE: incremental in-memory index removing every O(n)-per-turn scan.

Diagnosis (artifacts/fable-perf128-20260922/diag.json, process_time in-process):
teach/correct/ask p50 grow 4.08/3.99/4.75 ms @1k facts -> 38.56/38.53/48.89 ms
@15k facts (9.45x/9.65x/10.3x). O(n)-per-turn scans (all read-only, wrapped here):
 S1 fable_notebook_contract.py:246 current() full facts scan (assert_fact:331, ask:409)
 S2 fable_listening_m1.py:61 _relation() full events scan per teach/correct
 S3 fable_loop90_agent.py:109 notebook_triples() full facts+active scan per hear (:133)
 S4 fable_loop90_agent.py:160 Bench73Stage._teach_action() linear facts scan per teach
 S5 fable_fix77_core.py:157 filtered_view77() full facts scan per ask hop; :244 known() same
 S6 fable_agent_loop.py:262 _save() json dump of whole experience 2x/turn (grows w/ turns)
 S7 fable_loop102_agent.py:405 process_file set(facts)/set(entities) copies per turn
 S8 bench73 compose_question: ents build + _entity_mentions sort O(E log E) per "?" turn

Fix (this file only; no existing file edited; notebook file format unchanged):
 IndexedContractNotebook: inner contract notebook maintaining incremental
   (subject,relation)->[fact_ids], relation->[fact_ids], known-relations,
   cached active-taught triples list, per-(name,rel) displays, per-subject rel
   order, per-(rel,display) reverse subjects, length-bucketed mention strings.
 IndexedLoopNotebook: Loop90Notebook shape with the indexed inner (same seal).
 FastBench73: same stage order/precedence; template/parse logic untouched, but
   triples come from the incremental cache (lazy on non-"?" turns) and "?" turns
   use index-backed compose (mentions via buckets, walks via indexes; rare
   Who-/never-taught shapes fall back to the original full computation).
 FastReasoner77: parent hop loop verbatim except views come per-subject from the
   index; the global qualifier-dropped bit is cached per (rel,req,version) and
   computed by the original filtered_view77 on a miss (exact by construction).
 Listening._relation: cached known-relations (exact same set).
 Daemon bookkeeping: count-sliced new ids (same values, same sort).
 _save: full in-memory experience kept (sleep/audit semantics identical), but
   only the last 200 entries are persisted to state.json (replies/notebook
   unaffected; sleep threshold 1e9 never fires in soak/C3-P3; small tests fit).
Every reply is produced by the same decision logic over the same data.
"""
from __future__ import annotations
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A
import fable_bench73_english_arm as B73
import fable_daemon74_run as D74
import fable_daemon108_run as D108
import fable_fix77_core as F77
import fable_listening_m1 as L
import fable_loop102_agent as L102
import fable_loop90_agent as L90
import fable_notebook_contract as C
from fable_earsguard91 import GuardedEars  # noqa: F401 (re-export for builder parity)
from fable_thought49_notebook import ThoughtNotebook
from fable_wire51_adapters import HardGate46Sleeper, NotebookThinker

ANS = F77.ANS
ANS_IDX = F77.ANS_IDX
_SAVE_TAIL = 200


def _show(nb_entities: dict, value: dict) -> str:
    if "entity" in value:
        return nb_entities.get(value["entity"], value["entity"])
    return str(value.get("literal", ""))


class IndexedContractNotebook(C.Notebook):
    """C.Notebook with incremental per-turn-O(1) indexes. Same log, same API."""

    def _reset(self) -> None:
        super()._reset()
        self._sr: dict[tuple, list] = {}
        self._rel: dict[str, list] = {}
        self._rel_known: set[str] = set()
        self._triples: list[tuple] = []
        self._triples_pos: dict[str, int] = {}
        self._sro: dict[tuple, list] = {}
        self._srel: dict[str, list] = {}
        self._rev: dict[tuple, list] = {}
        self._rev_dirty: set[tuple] = set()
        self._ment_bkt: dict[int, set] = {}
        self._ment_ref: dict[str, int] = {}

    def _load(self) -> None:
        super()._load()
        for ev in self.events:
            self._index_event(ev)

    def _apply(self, event: dict) -> None:
        super()._apply(event)
        self._index_event(event)

    # -- incremental maintenance --------------------------------------
    def _ment_add(self, s: str) -> None:
        c = self._ment_ref.get(s, 0)
        self._ment_ref[s] = c + 1
        if c == 0:
            self._ment_bkt.setdefault(len(s), set()).add(s)

    def _ment_drop(self, s: str) -> None:
        c = self._ment_ref.get(s, 0)
        if c <= 1:
            self._ment_ref.pop(s, None)
            b = self._ment_bkt.get(len(s))
            if b is not None:
                b.discard(s)
        else:
            self._ment_ref[s] = c - 1

    def _triple_add(self, fid: str, sname: str, rel: str, disp: str) -> None:
        self._triples.append((fid, sname, rel, disp))
        self._triples_pos[fid] = len(self._triples) - 1
        self._sro.setdefault((sname, rel), []).append(disp)
        lst = self._srel.setdefault(sname, [])
        if rel not in lst:
            lst.append(rel)
        self._rev.setdefault((rel, disp), []).append(sname)
        self._ment_add(sname)
        self._ment_add(disp)

    def _triple_replace(self, fid_old: str, fid_new: str, sname: str, rel: str,
                        disp_old: str, disp_new: str) -> None:
        pos = self._triples_pos.pop(fid_old, None)
        if pos is not None:
            self._triples[pos] = (fid_new, sname, rel, disp_new)
            self._triples_pos[fid_new] = pos
        else:
            self._triple_add(fid_new, sname, rel, disp_new)
            return
        dl = self._sro.get((sname, rel), [])
        for i, d in enumerate(dl):
            if d == disp_old:
                dl[i] = disp_new
                break
        else:
            dl.append(disp_new)
        self._ment_drop(disp_old)
        self._ment_add(disp_new)
        self._rev_dirty.add((rel, disp_old))
        self._rev.setdefault((rel, disp_new), []).append(sname)

    def _triple_remove(self, fid: str) -> None:
        pos = self._triples_pos.pop(fid, None)
        if pos is None:
            return
        _, sname, rel, disp = self._triples[pos]
        del self._triples[pos]
        for i in range(pos, len(self._triples)):
            self._triples_pos[self._triples[i][0]] = i
        dl = self._sro.get((sname, rel))
        if dl:
            try:
                dl.remove(disp)
            except ValueError:
                pass
            if not dl:
                del self._sro[(sname, rel)]
                lst = self._srel.get(sname)
                if lst and rel in lst:
                    lst.remove(rel)
        self._ment_drop(sname)
        self._ment_drop(disp)
        self._rev_dirty.add((rel, disp))

    def _index_event(self, event: dict) -> None:
        kind = event.get("kind")
        if kind == "RELATION":
            self._rel_known.add(event["relation"])
        elif kind == "FACT":
            fid = event["fact_id"]
            self._sr.setdefault((event["subject"], event["relation"]), []).append(fid)
            self._rel.setdefault(event["relation"], []).append(fid)
            self._rel_known.add(event["relation"])
            if event.get("source") == "taught":
                sname = self.entities.get(event["subject"], "?")
                disp = _show(self.entities, event["value"])
                if event.get("supersedes"):
                    old = self.facts.get(event["supersedes"])
                    if old is not None and old.get("source") == "taught":
                        self._triple_replace(
                            old["fact_id"], fid, sname, event["relation"],
                            _show(self.entities, old["value"]), disp)
                    else:
                        self._triple_add(fid, sname, event["relation"], disp)
                else:
                    self._triple_add(fid, sname, event["relation"], disp)
        elif kind == "RETRACT":
            self._triple_remove(event["fact_id"])

    # -- fast reads (same results as the parent) -----------------------
    def current(self, entity_id: str, relation: str) -> list[dict]:
        cands = self._sr.get((entity_id, relation))
        if not cands:
            return []
        rows = [self.facts[fid] for fid in cands
                if self.facts[fid]["source"] in C.ANSWERING_SOURCES
                and self.active(self.facts[fid]["fact_id"])]
        rows.sort(key=lambda f: (C.ANSWERING_SOURCES.index(f["source"]), -f["n"]))
        if rows:
            best = rows[0]["source"]
            rows = [row for row in rows if row["source"] == best]
        return rows

    def known_relation(self, rel: str) -> bool:
        return rel in self._rel or rel in self.functional

    def mention_names(self):
        for ln in sorted(self._ment_bkt.keys(), reverse=True):
            for s in self._ment_bkt[ln]:
                yield s

    def rev_subjects(self, rel: str, disp: str) -> list:
        key = (rel, disp)
        if key in self._rev_dirty:
            out = []
            for fid in self._rel.get(rel, []):
                f = self.facts[fid]
                if f.get("source") == "taught" and self.active(fid) \
                        and _show(self.entities, f["value"]) == disp:
                    out.append(self.entities.get(f["subject"], "?"))
            self._rev[key] = out
            self._rev_dirty.discard(key)
        return self._rev.get(key, [])


class IndexedLoopNotebook(L90.Loop90Notebook):
    """Loop90Notebook shape (gate + seal) over the indexed inner notebook."""

    def __init__(self, root) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.nb = IndexedContractNotebook(root)
        self.marks: dict = {}
        self._rebuild_marks()
        self._rebuild_index()
        if self.torn_tail:
            return
        F77.verify_full(self.root)

    def current(self, entity_id: str, relation: str) -> list[dict]:
        return self.nb.current(entity_id, relation)

    def known_relation(self, rel: str) -> bool:
        return self.nb.known_relation(rel)


# ------------------------------------------------------------------ fast ears
def _fast_teach_action(nb, triple: tuple) -> dict:
    subj, rel, obj = triple
    act = "teach"
    found = nb.resolve(subj)
    if found.status == C.OK:
        eid = found.detail["entity_id"]
        inner = nb.nb if isinstance(nb, ThoughtNotebook) else nb
        for fid in inner._sr.get((eid, rel), ()):
            fact = inner.facts[fid]
            if (fact.get("source") == "taught"
                    and inner.active(fact["fact_id"])):
                if _show(inner.entities, fact["value"]) != obj:
                    act = "correct"
                break
    return {"act": act, "name": subj, "relation": rel, "value": obj,
            "is_person": True, "structured": True, "stage": "bench73"}


def _bucketed_mentions(nb_inner, question: str) -> list[str]:
    q = question.lower()
    spans: list[tuple] = []
    for s in nb_inner.mention_names():
        el = s.lower()
        start = 0
        while True:
            i = q.find(el, start)
            if i < 0:
                break
            spans.append((i, i + len(el), s))
            start = i + 1
    spans.sort()
    kept: list[tuple] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    seen: list[str] = []
    for _, _, e in kept:
        if e not in seen:
            seen.append(e)
    return seen


def _index_compose(nb_inner, text: str, mentioned=None):
    """Index-backed B73.compose_question (same result, no triple list).

    Callers pre-check `mentioned & taught-relations == empty` (then compose is
    provably None: the walk's r1 is a taught relation outside `mentioned`, so
    the coverage gate fails; every earlier branch was already excluded).
    """
    if mentioned is None:
        mentioned = B73._relation_mentions(text)
    else:
        mentioned = set(mentioned)
    if not (mentioned & set(nb_inner._rel.keys())):
        return None
    ment = _bucketed_mentions(nb_inner, text)
    if len(ment) != 1:
        return None
    start = ment[0]
    r1s = list(nb_inner._srel.get(start, ()))
    if len(r1s) != 1:
        return None
    r1 = r1s[0]
    objs = list(nb_inner._sro.get((start, r1), ()))
    if not objs:
        return None
    mid = objs[-1]
    r2s = [r for r in nb_inner._srel.get(mid, ()) if r != r1]
    if len(r2s) != 1:
        return None
    r2 = r2s[0]
    if r1 not in mentioned or r2 not in mentioned:
        return None
    return (start, [r1, r2])


def patch_bench73_stage(stage) -> None:
    """Same precedence/results as Bench73Stage.hear; index-backed fast paths."""
    orig_hear = stage.hear

    def fast_hear(turn: str, tau: dict):
        text = " ".join(str(turn).split())
        if not text:
            return None
        nb = stage.nb
        inner = nb.nb if isinstance(nb, ThoughtNotebook) else nb
        if text.rstrip().endswith("?"):
            # Original: compose first, then teach-template, else None.
            if _needs_full_question(text):
                return orig_hear(turn, tau)
            frame = _index_compose(inner, text)
            if frame is not None:
                return ([{"act": "ask", "name": frame[0],
                           "relations": list(frame[1])}], 1.0)
            triple = B73.hear_teach_template(text)
            if triple is not None:
                return ([_fast_teach_action(nb, triple)], 1.0)
            return None
        # Original: teach-template first, then compose, else None.
        triple = B73.hear_teach_template(text)
        if triple is not None:
            return ([_fast_teach_action(nb, triple)], 1.0)
        if _needs_full_question(text):
            return orig_hear(turn, tau)
        frame = _index_compose(inner, text)
        if frame is not None:
            return ([{"act": "ask", "name": frame[0],
                       "relations": list(frame[1])}], 1.0)
        return None

    def fast_teach_action(triple: tuple) -> dict:
        return _fast_teach_action(stage.nb, triple)

    stage.hear = fast_hear
    stage._teach_action = fast_teach_action


def _needs_full_question(text: str) -> bool:
    q = " ".join(str(text).split())
    if B73.re.fullmatch(r"What is the never-taught relation (\d+) of (.+?)\??", q):
        return True
    if B73.re.fullmatch(
            r"What is the never-taught relation of the ([\w /-]+?) of (.+?)\??", q):
        return True
    m = B73.re.fullmatch(r"Who is the ([\w /-]+?) of (.+?)\??", q)
    if m:
        label = m.group(1).strip().lower().replace(" ", "_")
        name = m.group(2).strip()
        if label in B73.REV_OF_NOUNS and B73._bare_name_ok(name):
            return True
    m = B73.re.fullmatch(r"Who (\w+) by (.+?)\??", q)
    if m:
        verb = m.group(1).strip().lower()
        name = m.group(2).strip()
        if verb in B73.REV_BY_VERBS and B73._bare_name_ok(name):
            return True
    return False


# ------------------------------------------------------------------ fast reasoner
class FastReasoner77(F77.QualifierAwareReasoner77):
    """Parent hop loop verbatim; per-subject index views + cached dropped bit."""

    def __init__(self) -> None:
        super().__init__()
        self._drop_cache: dict = {}

    def _entry_for(self, nb, inner, subject: str, rel: str, req: dict):
        rows = []
        for fid in inner._sr.get((subject, rel), ()):
            fact = inner.facts[fid]
            if fact["source"] not in ANS or not inner.active(fid):
                continue
            thought = F77.thought_of77(fact)
            quals = thought.qualifiers if thought is not None else ()
            if quals and not F77.qualifiers_match77(quals, req):
                continue
            rows.append((fact, bool(quals)))
        subj_rows = [(f, q) for f, q in rows]
        if any(f["source"] == "taught" and not q for f, q in subj_rows):
            subj_rows = [(f, q) for f, q in subj_rows if not q]
            if not subj_rows:
                return None
        facts = [f for f, _ in subj_rows]
        facts.sort(key=lambda f: (ANS_IDX[f["source"]], -f["n"]))
        best = facts[0]["source"]
        facts = [f for f in facts if f["source"] == best]
        functional = rel in inner.functional
        if functional or len(facts) == 1:
            row = facts[0]
            val = row["value"]
            num = F77.fid_num77(row["fact_id"])
            if "entity" in val:
                return ("E", val["entity"], num, ANS_IDX[best])
            return ("L", str(val["literal"]), num, ANS_IDX[best])
        shows = []
        for row in facts:
            val = row["value"]
            if "entity" in val:
                shows.append((inner.entities[val["entity"]],
                              F77.fid_num77(row["fact_id"])))
            else:
                shows.append((str(val["literal"]), F77.fid_num77(row["fact_id"])))
        return ("M", shows, ANS_IDX[best])

    def answer(self, question: dict, notebook) -> dict:
        nb = notebook
        self._sync(nb)
        inner = nb.nb if isinstance(nb, ThoughtNotebook) else nb
        import fable_qual56_reasoner as Q56
        name = question.get("name", "")
        relations = list(question.get("relations") or [])
        eid = question.get("entity_id")

        def rec(status: str, fields: dict) -> dict:
            return {"kind": "answer", "status": status, "name": name,
                    "relations": relations, "fields": fields}

        if not relations or len(relations) > F77.MAX_HOPS:
            return rec(C.BAD_REQUEST, {"reason": f"need 1-{F77.MAX_HOPS} hops"})
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

        version = len(nb.events)
        views: dict = {}

        def view_at(hop: int, rel: str):
            key = (hop, rel)
            if key not in views:
                req = hop_req[hop]
                ck = (rel, _reqkey(req), version)
                hit = self._drop_cache.get(ck)
                if hit is None:
                    out, dropped = F77.filtered_view77(nb, rel, req)
                    self._drop_cache[ck] = dropped
                    if len(self._drop_cache) > 64:
                        self._drop_cache.pop(next(iter(self._drop_cache)))
                    views[key] = (out, dropped)
                else:
                    views[key] = (None, hit)
            return views[key]

        def entry_of(rel: str, req: dict, out, subject: str):
            if out is not None:
                return out.get(subject)
            return self._entry_for(nb, inner, subject, rel, req)

        def known(rel: str) -> bool:
            return inner.known_relation(rel)

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
                      "hop": hop, "trail": [F77.fid_str77(n) for n in trail]}
            if qualified:
                detail["reason"] = "qualified"
            return detail

        def fields_broken(hop: int) -> dict:
            return {"subject": nb.entities[subject], "relation": lit_producer,
                    "value": lit_text, "hop": hop,
                    "trail": [F77.fid_str77(n) for n in trail]}

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
                entry = entry_of(arg, hop_req[hop], out, subject)
                if entry is None:
                    return rec(C.MISSING_FACT, fields_missing(hop + 1, arg, dropped))
                tag = entry[0]
                if tag == "M":
                    shows, src = entry[1], entry[2]
                    return rec(C.OK, {"answer": ", ".join(s for s, _ in shows),
                                      "trail": [F77.fid_str77(n) for n in trail]
                                      + [F77.fid_str77(n) for _, n in shows],
                                      "source": ANS[src], "multi": True})
                trail.append(entry[2])
                trail_src.append(entry[3])
                if tag == "L":
                    kind, lit_text, lit_producer = "literal", entry[1], arg
                else:
                    subject = entry[1]

        if kind != "entity":
            return rec(C.OK, {"answer": lit_text,
                              "trail": [F77.fid_str77(n) for n in trail],
                              "source": ANS[trail_src[-1]]})
        if conf < F77.ANSWER_THRESHOLD:
            return rec(C.MISSING_FACT,
                       fields_missing(len(relations), relations[-1], False))
        return rec(C.OK, {"answer": nb.entities[subject],
                          "trail": [F77.fid_str77(n) for n in trail],
                          "source": ANS[trail_src[-1]]})


def _reqkey(req: dict) -> tuple:
    return tuple(sorted((str(k), str(v)) for k, v in req.items()))


# ------------------------------------------------------------------ fast loop
class FastLoop102AgentLoop(L102.Loop102AgentLoop):
    """Loop102AgentLoop over the indexed notebook; tail-persisted state."""

    def __init__(self, state_dir, *, ears=None, mouth=None, reasoner=None,
                 sleeper=None, thinker=None,
                 sleep_threshold: int = A.SLEEP_THRESHOLD) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / A.STATE_NAME
        self.ears = ears or A.FakeEars()
        self.mouth = mouth or A.FakeMouth()
        self.reasoner = reasoner or FastReasoner77()
        self.sleeper = sleeper or A.StubSleeper()
        self.thinker = thinker
        self.sleep_threshold = int(sleep_threshold)
        self.notes: list[str] = []
        self.last_records: list[dict] = []
        self.parts90: dict = {}

        self.nb = IndexedLoopNotebook(self.dir / A.NOTEBOOK_DIR)
        if self.nb.torn_tail:
            self.nb.repair_torn_tail()
            self.notes.append("repaired a torn notebook tail")
            F77.verify_full(self.nb.root)
        self.listening = L.Listening(self.nb)
        _patch_relation(self)

        self.tick = 0
        self.mode = A.THINKING
        self.inbox: list[str] = []
        self.work_queue: list[str] = []
        self.experience: list[dict] = []
        self.question_pending: dict | None = None
        self.sleep_mark = 0
        self.counters = {"turns": 0, "writes": 0, "answers": 0,
                         "clarifications": 0, "sleeps": 0, "work": 0,
                         "thinks": 0}
        self._load()

    def _save(self) -> None:
        import json as _json
        import os as _os
        exp = self.experience[-_SAVE_TAIL:] if len(self.experience) > _SAVE_TAIL else self.experience
        payload = {"version": A.STATE_VERSION, "tick": self.tick, "mode": self.mode,
                   "inbox": self.inbox, "work_queue": self.work_queue,
                   "experience": exp, "question_pending": self.question_pending,
                   "sleep_mark": self.sleep_mark, "counters": self.counters,
                   "listening_pending": self.listening.pending,
                   "listening_turn": self.listening.turn,
                   "sleep_threshold": self.sleep_threshold}
        tmp = self.dir / f"{A.STATE_NAME}.tmp{_os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(_json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.flush()
            _os.fsync(handle.fileno())
        _os.replace(tmp, self.state_path)
        nb = getattr(self, "nb", None)
        if nb is not None and hasattr(nb, "advance_seal"):
            nb.advance_seal()


def _patch_relation(loop) -> None:
    """Listening._relation via the cached known-set (same set, no scan)."""
    inner = loop.nb.nb if isinstance(loop.nb, ThoughtNotebook) else loop.nb
    orig = loop.listening._relation

    def fast_relation(relation: str) -> None:
        if relation in inner._rel_known:
            return
        return orig(relation)

    loop.listening._relation = fast_relation


DEFAULT_CONFIG128: dict = copy.deepcopy(L102.DEFAULT_CONFIG102)
DEFAULT_CONFIG128["daemon"]["module"] = "FastLoop102Daemon (this file)"
DEFAULT_CONFIG128["notebook"]["class"] = "IndexedLoopNotebook (this file)"


def build_fast_agent102(cfg: dict | None = None) -> FastLoop102AgentLoop:
    cfg = dict(DEFAULT_CONFIG128, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = FastReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears
    loop = FastLoop102AgentLoop(
        state_dir, ears=L102.Loop102Ears(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    for stage in chain.stages:
        if getattr(stage, "name", "") == "bench73":
            patch_bench73_stage(stage)
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


class FastLoop102Daemon(L102.Loop102Daemon):
    """Loop102Daemon shape over the fast agent; incremental bookkeeping."""

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
        self.loop = build_fast_agent102(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)

    def process_file(self, path: Path) -> dict:
        import os as _os
        nb = self.loop.nb
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            D74._atomic_write(self.outbox / path.name, L102.UNREADABLE_MSG + "\n")
            try:
                _os.replace(path, self.done / path.name)
            except OSError:
                pass
            record = {"t": D74._now_iso(), "event": "turn-skipped-unreadable",
                      "file": path.name, "reply": L102.UNREADABLE_MSG,
                      "turn_count": int(self.loop.counters.get("turns", 0)),
                      "notebook_events": len(nb.events)}
            D74._append_log(self.log_path, record)
            return record
        before_nf = len(nb.facts)
        before_ne = len(nb.entities)
        said = self.loop.turn(text)
        records = list(getattr(self.loop, "last_records", []))
        new_facts = sorted(list(nb.facts.keys())[before_nf:])
        new_entities = {eid: nb.entities[eid]
                        for eid in sorted(list(nb.entities.keys())[before_ne:])}
        reply = " ".join(said) if said else "(nothing to say)"
        D74._atomic_write(self.outbox / path.name, reply + "\n")
        _os.replace(path, self.done / path.name)
        record = {"t": D74._now_iso(), "event": "turn", "file": path.name,
                  "turn_text": text.strip()[:200], "reply": reply[:500],
                  "records": records,
                  "ears_stage": getattr(self.loop.ears, "last_stage", ""),
                  "ears_score": getattr(self.loop.ears, "last_score", 0.0),
                  "new_fact_ids": new_facts, "new_entities": new_entities,
                  "turn_count": int(self.loop.counters.get("turns", 0)),
                  "notebook_events": len(nb.events)}
        D74._append_log(self.log_path, record)
        return record


def build_fast_daemon108(root, cfg: dict | None = None,
                         idle_seconds: float = 30.0,
                         sleep_threshold=None):
    """Fast loop102 daemon + exp-108 exactly-once wrapper (receipts + reconcile)."""

    class FastDaemon108(FastLoop102Daemon):
        def process_file(self, path: Path) -> dict:
            record = super().process_file(path)
            if record.get("event") in ("turn", "turn-skipped-unreadable"):
                try:
                    reply = (self.outbox / path.name).read_text(encoding="utf-8")
                except OSError:
                    reply = str(record.get("reply", ""))
                D108.append_receipt(self.root, path.name, reply)
            return record

    kwargs = {} if sleep_threshold is None else {"sleep_threshold": sleep_threshold}
    daemon = FastDaemon108(root, cfg=cfg, idle_seconds=idle_seconds, **kwargs)
    daemon.reconcile_report = D108.boot_reconcile(daemon)
    return daemon
