#!/usr/bin/env python3
"""Experiment 50: the Experiment-44 reasoner running on the REAL notebook contract.

WHAT THIS IS
  Experiment 44 proved the skills+router reasoner on a toy village (a plain dict).  Here the
  SAME mechanism answers questions against ``fable_notebook_contract.Notebook`` -- E-IDs with
  ambiguous aliases, an open growing relation set, source-tagged facts, and question frames
  ``{name, relations, entity_id?}`` exactly as the ears produce them.

  REASONER PROTOCOL (scripts/fable_agent_loop.py)::

      answer(question, notebook) -> {'kind':'answer', 'status', 'name', 'relations', 'fields'}

  with the contract's discrete statuses OK / MISSING_FACT / BROKEN_CHAIN / AMBIGUOUS /
  UNKNOWN_ENTITY (plus BAD_REQUEST for bad hop counts), field-for-field identical to
  ``Notebook.ask`` -- the registered parity mark requires 100% agreement.

  SKILLS  = per-relation lookup views, built LAZILY from the notebook's current view:
            only active facts whose source is in the contract's ANSWERING_SOURCES
            (proposed / web-quarantine never answer), sorted best-source-first exactly as
            ``Notebook.current`` does.  Nothing is trained; the notebook is the index.
  ROUTER  = base relation tokens route IDENTITY (skill r = lookup r) -- given by hand,
            because the relation vocabulary is open and hundreds of relations will never be
            seen in training.  Learned WORDS route through the Exp-44 3-stage router over
            [keep + the 8 core skills] (27 numbers per word), installed by the Exp-46 recipe
            (robust loss eps=0.10, harden to argmax +/-30 after every fold fit and the
            refit, 4-fold CV gate OOF >= 0.80, refit agreement >= 0.90, base unchanged,
            reload identical).
  HOP LOOP = hard-coded, one routed stage-set per token, halt when the token tape is
            empty; ANSWER_THRESHOLD 0.9; never guesses.  A relation token the reasoner does
            not know at all (not declared, no facts of any source, not a learned word)
            abstains with MISSING_FACT -- never a guessed entity.

STAGES
  --selftest           mini notebook: every status, reasoner == contract, unknown abstain
  --stage scale        notebooks of (60|600|6000) x (8|80|500); 300 frames per cell
                       compared against Notebook.ask (must agree 100%); time/memory;
                       unknown-relation abstention probe
  --stage sleep        real training notebook per seed; install 3 words x 20 taught
                       episodes with the Exp-46 recipe; 60-start audit per install
                       against the true walk; base/reload/dense-answer wiring checks
  --stage score        marks table from runs/*.json (post-run reporting)

Additive, offline, CPU, one thread.  Imports fable_notebook_contract, fable_reasoner44,
fable_noisyteacher45, fable_hardgate46 READ-ONLY (45/46 patch 44 in-process; that chain is
the registered Exp-46 recipe we deliberately reuse).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import resource
import shutil
import sys
import time
import tracemalloc
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C                          # noqa: E402

# ----------------------------------------------------------------- given by hand
ANSWER_THRESHOLD = 0.9
MAX_HOPS = C.MAX_HOPS                                        # 8, from the contract
ANS = C.ANSWERING_SOURCES                                    # taught | inferred | sleep-derived | web-verified
ANS_IDX = {s: i for i, s in enumerate(ANS)}

CORE8 = ("mother", "father", "spouse", "boss", "best_friend", "neighbour", "doctor", "teacher")
N_STAGES = 3
N_OPTIONS = 1 + len(CORE8)                                   # keep + 8 skills = 9 -> 27 numbers/word

WORDS = (
    ("maternal_grandmother", ("mother", "mother")),
    ("boss_of_spouse", ("spouse", "boss")),
    ("doctor_of_mothers_friend", ("mother", "best_friend", "doctor")),
)
WORD_NAMES = tuple(w for w, _ in WORDS)
WORD_CHAINS = tuple(c for _, c in WORDS)

# parity category mix; registered 300 -> these exact integers (dev scales proportionally)
PARITY_CATS = (
    ("ok_entity", 100), ("ok_literal", 25), ("missing", 40), ("broken", 25),
    ("ambiguous", 20), ("unknown_entity", 20), ("multi", 20), ("source_filter", 20),
    ("eid", 15), ("junk", 15),
)
UNK_PER_CELL = 10                                             # unknown-relation abstention frames per cell
EPISODES = 20
SEEDS = (4131, 4132, 4133)
DEV_SEED = 9999
GRID = tuple((n, r) for n in (60, 600, 6000) for r in (8, 80, 500))
SPECIAL = ("city", "friend", "hobby")                         # literal / multi-valued relations
MISSING_RATE = 0.15
TRAIN_N = 60
DEFAULT_SCRATCH = Path(os.environ.get(
    "FABLE_R50_SCRATCH",
    "/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/fable-reasoner50"))


def sha_tag(*parts) -> int:
    h = hashlib.sha256("/".join(str(p) for p in ("reasoner50",) + parts).encode()).digest()
    return int.from_bytes(h[:8], "big")


def rng_for(*parts) -> random.Random:
    return random.Random(sha_tag(*parts))


def script_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def fid_str(num: int) -> str:
    return f"F{num:05d}"


def fid_num(fid: str) -> int:
    return int(fid[1:])


# =============================================================== the reasoner
class RelationView:
    """One relation's lookup matrix, built from the notebook's current view.

    ``out[subject_eid]`` is one of
        ("E", target_eid, fact_num, src_idx)     single entity-valued row
        ("L", text,       fact_num, src_idx)     single literal row
        ("M", [(show, fact_num), ...], src_idx)  non-functional multi row (contract answers OK)
    absent = no answering fact (MISSING).  Rows are selected exactly as
    ``Notebook.current`` selects them: active, answering source only, best source first,
    newest first within a source; functional relations (or single rows) take rows[0].
    """

    __slots__ = ("rel", "out", "functional")

    def __init__(self, nb, rel: str, bucket_ids) -> None:
        self.rel = rel
        self.functional = rel in nb.functional
        by_subj: dict[str, list[str]] = {}
        for fid in bucket_ids:
            fact = nb.facts[fid]
            if fact["source"] in ANS and nb.active(fid):
                by_subj.setdefault(fact["subject"], []).append(fid)
        out: dict[str, tuple] = {}
        for subj, fids in by_subj.items():
            rows = [nb.facts[f] for f in fids]
            rows.sort(key=lambda f: (ANS_IDX[f["source"]], -f["n"]))
            best = rows[0]["source"]
            rows = [r for r in rows if r["source"] == best]
            src = ANS_IDX[best]
            if self.functional or len(rows) == 1:
                row = rows[0]
                val = row["value"]
                num = fid_num(row["fact_id"])
                if "entity" in val:
                    out[subj] = ("E", val["entity"], num, src)
                else:
                    out[subj] = ("L", str(val["literal"]), num, src)
            else:
                shows = []
                for row in rows:
                    val = row["value"]
                    if "entity" in val:
                        shows.append((nb.entities[val["entity"]], fid_num(row["fact_id"])))
                    else:
                        shows.append((str(val["literal"]), fid_num(row["fact_id"])))
                out[subj] = ("M", shows, src)
        self.out = out


class FableReasoner50:
    """The Reasoner Protocol: answer(question, notebook) -> record with a discrete status."""

    def __init__(self) -> None:
        self.words: dict[str, list[list[float]]] = {}   # word -> [3][9] hardened logits
        self._version: int | None = None
        self._bucket: dict[str, list[str]] | None = None
        self._views: dict[str, RelationView] = {}

    # ------------------------------------------------------------- cache mgmt
    def _sync(self, nb) -> None:
        version = len(nb.events)
        if version != self._version:
            self._version = version
            self._bucket = None
            self._views = {}

    def _buckets(self, nb) -> dict[str, list[str]]:
        if self._bucket is None:
            bucket: dict[str, list[str]] = {}
            for fid, fact in nb.facts.items():
                bucket.setdefault(fact["relation"], []).append(fid)
            self._bucket = bucket
        return self._bucket

    def _view(self, nb, rel: str) -> RelationView | None:
        view = self._views.get(rel)
        if view is None:
            bucket = self._buckets(nb).get(rel)
            if bucket is None and rel not in nb.functional:
                return None                       # unknown relation: caller abstains
            view = RelationView(nb, rel, bucket or [])
            self._views[rel] = view
        return view

    def warm(self, nb, relations) -> None:
        """Build the bucket index + every requested relation view (one-time cost)."""
        self._sync(nb)
        self._buckets(nb)
        for rel in relations:
            if rel not in self.words:
                self._view(nb, rel)

    def cache_bytes(self) -> int:
        total = 0
        if self._bucket is not None:
            total += sys.getsizeof(self._bucket)
            for k, v in self._bucket.items():
                total += sys.getsizeof(k) + sys.getsizeof(v) + 8 * len(v)
        for rel, view in self._views.items():
            total += sys.getsizeof(rel) + sys.getsizeof(view) + sys.getsizeof(view.out)
            for k, entry in view.out.items():
                total += sys.getsizeof(k) + sys.getsizeof(entry)
                if entry[0] == "M":
                    total += sys.getsizeof(entry[1])
                    total += sum(sys.getsizeof(pair) + sys.getsizeof(pair[0]) for pair in entry[1])
        for w, logits in self.words.items():
            total += sys.getsizeof(w) + sys.getsizeof(logits)
            total += sum(sys.getsizeof(row) for row in logits)
        return total

    # ------------------------------------------------------------ learned words
    def load_word(self, word: str, logits) -> None:
        if word not in WORD_NAMES:
            raise ValueError(f"unknown word {word}")
        self.words[word] = [list(map(float, row)) for row in logits]

    @staticmethod
    def stage_options(logits: list[list[float]]) -> list[tuple[str, str, float]]:
        """[(kind, arg, weight)] -- kind in {'keep','skill'}, weight = softmax prob of argmax.

        Installed words are hardened (+/-30), so argmax weight ~1.0; a soft word contributes
        only its argmax-path mass, and mass below the 0.9 threshold forces abstention.
        """
        out = []
        for row in logits:
            m = max(row)
            exps = [math.exp(x - m) for x in row]
            s = sum(exps)
            k = max(range(len(row)), key=lambda i: row[i])
            if k == 0:
                out.append(("keep", "", exps[k] / s))
            else:
                out.append(("skill", CORE8[k - 1], exps[k] / s))
        return out

    def _stages(self, tok: str, nb) -> list[tuple[str, str, float]] | None:
        """Stage expansion for one question token; None = unknown relation (abstain)."""
        if tok in self.words:
            return self.stage_options(self.words[tok])
        if tok in self._buckets(nb) or tok in nb.functional:
            return [("skill", tok, 1.0)]
        return None

    # -------------------------------------------------------------- the hop loop
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

        if eid is None:
            found = nb.resolve(name)
            if found.status != C.OK:
                return rec(found.status, dict(found.detail))
            eid = found.detail["entity_id"]
        elif eid not in nb.entities:
            return rec(C.BAD_REQUEST, {"reason": "unknown entity id"})

        trail: list[int] = []
        trail_src: list[int] = []
        subject = eid
        kind = "entity"
        lit_text = lit_producer = None
        conf = 1.0

        def fields_missing(hop: int, rel: str) -> dict:
            return {"subject": nb.entities[subject], "relation": rel,
                    "hop": hop, "trail": [fid_str(n) for n in trail]}

        def fields_broken(hop: int) -> dict:
            return {"subject": nb.entities[subject], "relation": lit_producer,
                    "value": lit_text, "hop": hop, "trail": [fid_str(n) for n in trail]}

        for hop, tok in enumerate(relations):
            if kind != "entity":
                return rec(C.BROKEN_CHAIN, fields_broken(hop))          # hop = detection index, as the contract
            stages = self._stages(tok, nb)
            if stages is None:
                return rec(C.MISSING_FACT, fields_missing(hop + 1, tok))  # never guess an unknown relation
            for opt, arg, weight in stages:
                if kind != "entity":
                    return rec(C.BROKEN_CHAIN, fields_broken(hop))
                if opt == "keep":
                    continue
                conf *= weight
                view = self._view(nb, arg)
                if view is None:
                    return rec(C.MISSING_FACT, fields_missing(hop + 1, arg))
                entry = view.out.get(subject)
                if entry is None:
                    return rec(C.MISSING_FACT, fields_missing(hop + 1, arg))
                tag = entry[0]
                if tag == "M":
                    shows, src = entry[1], entry[2]
                    return rec(C.OK, {"answer": ", ".join(s for s, _ in shows),
                                      "trail": [fid_str(n) for n in trail] + [fid_str(n) for _, n in shows],
                                      "source": ANS[src], "multi": True})
                trail.append(entry[2])
                trail_src.append(entry[3])
                if tag == "L":
                    kind, lit_text, lit_producer = "literal", entry[1], arg
                else:
                    subject = entry[1]

        if kind != "entity":
            return rec(C.OK, {"answer": lit_text, "trail": [fid_str(n) for n in trail],
                              "source": ANS[trail_src[-1]]})
        if conf < ANSWER_THRESHOLD:
            return rec(C.MISSING_FACT, fields_missing(len(relations), relations[-1]))
        return rec(C.OK, {"answer": nb.entities[subject], "trail": [fid_str(n) for n in trail],
                          "source": ANS[trail_src[-1]]})


# =============================================================== frame helpers
def contract_answer(frame: dict, nb) -> dict:
    """The contract's own hop loop, wrapped in the same record shape."""
    result = nb.ask(frame.get("name", ""), list(frame.get("relations") or []),
                    entity_id=frame.get("entity_id"))
    return {"kind": "answer", "status": result.status, "name": frame.get("name", ""),
            "relations": list(frame.get("relations") or []), "fields": dict(result.detail)}


def view_walk_view(reasoner: FableReasoner50, nb, start: str, rels) -> str | None:
    """Ground-truth chain over the notebook's answering view: final entity or None.

    Learned words expand to their DEFINED chain (maternal_grandmother = mother->mother) --
    so a mis-routed install cannot make a probe agree with itself; plain relations are
    single skill lookups.  Literal or missing at any point -> None.
    """
    cur = start
    for rel in rels:
        if rel in WORD_NAMES:
            rel_chain: tuple = WORD_CHAINS[WORD_NAMES.index(rel)]
        else:
            rel_chain = (rel,)
        for arg in rel_chain:
            view = reasoner._view(nb, arg)
            entry = None if view is None else view.out.get(cur)
            if entry is None or entry[0] != "E":
                return None
            cur = entry[1]
    return cur


def true_word_walk(reasoner, nb, start: str, chain) -> str | None:
    """The word's DEFINED chain (maternal_grandmother = mother->mother) over the view."""
    cur = start
    for rel in chain:
        view = reasoner._view(nb, rel)
        entry = None if view is None else view.out.get(cur)
        if entry is None or entry[0] != "E":
            return None
        cur = entry[1]
    return cur


# =============================================================== scale stage
def _emit_factory(events: list, prev: list):
    def emit(ev: dict) -> None:
        ev = dict(ev, n=len(events) + 1, prev=prev[0], v=C.FORMAT_VERSION)
        line = json.dumps(ev, sort_keys=True, ensure_ascii=False)
        events.append(line)
        prev[0] = hashlib.sha256(line.encode("utf-8")).hexdigest()
    return emit


def generate_cell(n: int, r: int, root: Path) -> dict:
    """Bulk-write a contract events.jsonl for one grid cell (no per-event fsync), then load."""
    rng = rng_for("cell", n, r)
    root.mkdir(parents=True, exist_ok=True)
    events: list[str] = []
    emit = _emit_factory(events, ["0" * 64])

    n_main = r - len(SPECIAL)
    assert n_main >= 1
    main_rels = [f"rel_{i}" for i in range(n_main)]
    for rel in main_rels:
        emit({"kind": "RELATION", "event_id": f"rel-{rel}", "relation": rel, "functional": True})
    emit({"kind": "RELATION", "event_id": "rel-city", "relation": "city", "functional": True})
    emit({"kind": "RELATION", "event_id": "rel-friend", "relation": "friend", "functional": False})
    emit({"kind": "RELATION", "event_id": "rel-hobby", "relation": "hobby", "functional": False})

    names = [f"P{i:05d}" for i in range(n)]
    for i in range(0, n - 1, 50):            # duplicate names -> AMBIGUOUS, but n stays n
        names[i + 1] = names[i]
    for i in range(n):
        emit({"kind": "ENTITY", "event_id": f"ent-{i}", "entity_id": f"E{i + 1:04d}", "name": names[i]})
    for i in range(0, n, 25):                # aliases
        emit({"kind": "ALIAS", "event_id": f"al-{i}", "entity_id": f"E{i + 1:04d}",
              "alias": f"nick{i}"})

    eids = [f"E{i + 1:04d}" for i in range(n)]
    fact_count = 0
    proposed_pairs: list[tuple[str, str]] = []
    taught_sample: list[tuple[str, str, str, int]] = []      # (subj, rel, tgt, fact_num)

    def fact(subj, rel, value, source="taught", actor="listening", **extra) -> int:
        nonlocal fact_count
        fact_count += 1
        ev = {"kind": "FACT", "event_id": f"fact-{fact_count}", "fact_id": fid_str(fact_count),
              "actor": actor, "source": source, "subject": subj, "relation": rel,
              "value": value, "supersedes": None, "raw": None, "rule_id": None,
              "deps": [], "provenance": None}
        ev.update(extra)
        emit(ev)
        return fact_count

    for rel in main_rels:
        for eid in eids:
            if rng.random() < MISSING_RATE:
                if len(proposed_pairs) < 40:
                    proposed_pairs.append((eid, rel))
                continue
            tgt = eids[rng.randrange(n)]
            while tgt == eid:
                tgt = eids[rng.randrange(n)]
            num = fact(eid, rel, {"entity": tgt})
            if len(taught_sample) < 200:
                taught_sample.append((eid, rel, tgt, num))

    for i, eid in enumerate(eids):                            # city: literal values, 20%
        if i % 5 == 0:
            fact(eid, "city", {"literal": f"City{rng.randrange(1000)}"})
    for i, eid in enumerate(eids):                            # friend/hobby: multi-valued, 10%
        if i % 10 == 0:
            for rel in ("friend", "hobby"):
                seen: set = set()
                for _ in range(2):
                    tgt = eids[rng.randrange(n)]
                    while tgt in seen or tgt == eid:
                        tgt = eids[rng.randrange(n)]
                    seen.add(tgt)
                    fact(eid, rel, {"entity": tgt})

    for subj, rel in proposed_pairs[:20]:                     # source filter: only non-answering rows
        if rng.random() < 0.5:
            fact(subj, rel, {"entity": eids[rng.randrange(n)]}, source="proposed", actor="working")
        else:
            fact(subj, rel, {"literal": "quarantined"}, source="web-quarantine", actor="thinking",
                 provenance={"url": "https://example.org/x", "quoted_span": "span"})

    for j, (subj, rel, old_tgt, num) in enumerate(taught_sample[:50]):   # corrections supersede
        if j % 5 == 4:
            continue
        tgt = eids[rng.randrange(n)]
        while tgt == old_tgt:
            tgt = eids[rng.randrange(n)]
        fact_count += 1
        ev = {"kind": "FACT", "event_id": f"fact-c-{fact_count}", "fact_id": fid_str(fact_count),
              "actor": "listening", "source": "taught", "subject": subj, "relation": rel,
              "value": {"entity": tgt}, "supersedes": fid_str(num), "raw": None,
              "rule_id": None, "deps": [], "provenance": None}
        emit(ev)

    for subj, rel, _tgt, num in taught_sample[95:105]:        # a few retractions
        emit({"kind": "RETRACT", "event_id": f"ret-{num}", "fact_id": fid_str(num),
              "actor": "listening", "reason": "dev retraction"})

    t0 = time.time()
    path = root / C.LOG_NAME
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(events) + "\n")
    write_s = time.time() - t0
    t0 = time.time()
    nb = C.Notebook(root)
    load_s = time.time() - t0
    return {"facts": len(nb.facts), "events": len(nb.events), "write_s": round(write_s, 2),
            "load_s": round(load_s, 2), "file_mb": round(path.stat().st_size / 1e6, 1),
            "proposed_pairs": proposed_pairs[:20]}


def cat_counts(total: int) -> dict[str, int]:
    raw = {name: max(1, round(total * share / 300)) for name, share in PARITY_CATS}
    while sum(raw.values()) > total:
        biggest = max(raw, key=lambda k: raw[k])
        if raw[biggest] <= 1:
            break
        raw[biggest] -= 1
    while sum(raw.values()) < total:
        raw[max(PARITY_CATS, key=lambda t: t[1])[0]] += 1
    return raw


def alias_of(nb, eid: str) -> str | None:
    """A unique alias for eid (not its display name), if one exists."""
    norm_display = " ".join(nb.entities[eid].strip().lower().split())
    for alias, ids in nb.aliases.items():
        if ids == [eid] and alias != norm_display:
            return alias
    return None


def sample_parity(nb, reasoner: FableReasoner50, tag: str, n: int, r: int,
                  total: int, proposed_pairs) -> list[dict]:
    rng = rng_for("parity", tag, n, r, total)
    counts = cat_counts(total)
    eids = list(nb.entities)
    names = list(nb.entities.values())
    ambiguous_names = sorted({key for key, ids in nb.aliases.items() if len(ids) > 1})
    plain_rels = [f"rel_{i}" for i in range(r - len(SPECIAL))]
    all_rels = plain_rels + list(SPECIAL)
    entity_values = set(names)

    def frame(name, rels, entity_id=None):
        f = {"name": name, "relations": rels}
        if entity_id is not None:
            f["entity_id"] = entity_id
        return f

    def gen(cat: str) -> dict | None:
        k = rng.randrange(len(eids))
        eid = eids[k]
        nm = nb.entities[eid]
        if cat == "ok_entity":
            rels = [plain_rels[rng.randrange(len(plain_rels))] for _ in range(rng.randint(1, 3))]
            if rng.random() < 0.3:
                al = alias_of(nb, eid)
                if al:
                    nm = al
            if rng.random() < 0.5:
                return frame(nm, rels)
            return frame(nm, rels, entity_id=eid)
        if cat == "ok_literal":
            rels = [plain_rels[rng.randrange(len(plain_rels))] for _ in range(rng.randint(0, 2))] + ["city"]
            return frame(nm, rels, entity_id=eid)
        if cat == "missing":
            rels = [all_rels[rng.randrange(len(all_rels))] for _ in range(rng.randint(1, 3))]
            if rng.random() < 0.5:
                return frame(nm, rels, entity_id=eid)
            return frame(nm, rels)
        if cat == "broken":
            return frame(nm, ["city"] + [all_rels[rng.randrange(len(all_rels))]
                                         for _ in range(rng.randint(1, 2))], entity_id=eid)
        if cat == "ambiguous":
            if not ambiguous_names:
                return None
            key = ambiguous_names[rng.randrange(len(ambiguous_names))]
            return frame(key, [all_rels[rng.randrange(len(all_rels))]])
        if cat == "unknown_entity":
            return frame(f"Ghost{rng.randrange(10 ** 9)}",
                         [all_rels[rng.randrange(len(all_rels))] for _ in range(rng.randint(1, 3))])
        if cat == "multi":
            rel = rng.choice(("friend", "hobby"))
            rels = [rel] + ([all_rels[rng.randrange(len(all_rels))]] if rng.random() < 0.5 else [])
            return frame(nm, rels, entity_id=eid)
        if cat == "source_filter":
            if not proposed_pairs:
                return None
            subj, rel = proposed_pairs[rng.randrange(len(proposed_pairs))]
            return frame(nb.entities.get(subj, subj), [rel], entity_id=subj)
        if cat == "eid":
            rels = [plain_rels[rng.randrange(len(plain_rels))] for _ in range(rng.randint(1, 3))]
            return frame(nm, rels, entity_id=eid)
        if cat == "junk":
            jname = names[rng.randrange(len(names))] if rng.random() < 0.5 else f"Nobody{rng.randrange(10 ** 6)}"
            rels = [all_rels[rng.randrange(len(all_rels))] for _ in range(rng.randint(1, 3))]
            if rng.random() < 0.3:
                return frame(jname, rels, entity_id=eid)
            return frame(jname, rels)
        raise AssertionError(cat)

    def accept(cat: str, pred: dict) -> bool:
        st = pred["status"]
        fields = pred["fields"]
        if cat == "ok_entity":
            return st == C.OK and "multi" not in fields and fields.get("answer") in entity_values
        if cat == "eid":
            return st in (C.OK, C.MISSING_FACT, C.BROKEN_CHAIN)
        if cat == "ok_literal":
            return st == C.OK and "multi" not in fields and fields.get("answer") not in entity_values
        if cat == "missing":
            return st == C.MISSING_FACT
        if cat == "broken":
            return st == C.BROKEN_CHAIN
        if cat == "ambiguous":
            return st == C.AMBIGUOUS
        if cat == "unknown_entity":
            return st == C.UNKNOWN_ENTITY
        if cat == "multi":
            return st == C.OK and fields.get("multi") is True
        if cat == "source_filter":
            return st == C.MISSING_FACT and not fields.get("trail")
        if cat == "junk":
            return True
        raise AssertionError(cat)

    frames: list[dict] = []
    for cat, want in counts.items():
        got, trials = 0, 0
        while got < want:
            trials += 1
            if trials > 200 * want + 5000:
                raise RuntimeError(f"could not sample {cat}={want} in cell ({n},{r}) tag={tag}: got {got}")
            cand = gen(cat)
            if cand is None:
                continue
            if accept(cat, reasoner.answer(cand, nb)):
                frames.append(cand)
                got += 1
    if len(frames) != total:
        raise AssertionError((len(frames), total))
    rng.shuffle(frames)
    return frames


def stage_scale(tag: str, total: int, out: Path, scratch: Path) -> None:
    report = {"tag": tag, "questions_per_cell": total, "cells": [], "script_sha256": script_sha()}
    maxrss_peak = 0.0
    for n, r in GRID:
        cell_dir = scratch / f"cell-{n}-{r}"
        if cell_dir.exists():
            shutil.rmtree(cell_dir)
        meta = generate_cell(n, r, cell_dir)
        nb = C.Notebook(cell_dir)
        if len(nb.entities) != n:
            raise AssertionError((len(nb.entities), n))

        sampler = FableReasoner50()                       # shapes the sample; not the measured one
        frames = sample_parity(nb, sampler, tag, n, r, total, meta["proposed_pairs"])
        del sampler
        relations_in_play = sorted({rel for f in frames for rel in f["relations"]})

        timed = FableReasoner50()
        tracemalloc.start()
        t0 = time.time()
        timed.warm(nb, relations_in_play)
        index_s = time.time() - t0
        cache_bytes = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        agree, disagreements = 0, []
        ms_r, ms_c = [], []
        status_counts: dict[str, int] = {}
        for frame in frames:
            t0 = time.perf_counter()
            mine = timed.answer(frame, nb)
            ms_r.append((time.perf_counter() - t0) * 1000)
            t0 = time.perf_counter()
            theirs = contract_answer(frame, nb)
            ms_c.append((time.perf_counter() - t0) * 1000)
            status_counts[mine["status"]] = status_counts.get(mine["status"], 0) + 1
            if mine == theirs:
                agree += 1
            elif len(disagreements) < 5:
                disagreements.append({"frame": frame, "reasoner": mine, "contract": theirs})

        unk_agree = 0
        for k in range(UNK_PER_CELL):
            frame = {"name": nb.entities[f"E{k + 1:04d}"], "relations": [f"never_taught_rel_{k}"],
                     "entity_id": f"E{k + 1:04d}"}
            mine = timed.answer(frame, nb)
            theirs = contract_answer(frame, nb)
            if mine == theirs and mine["status"] == C.MISSING_FACT:
                unk_agree += 1
            elif len(disagreements) < 5:
                disagreements.append({"frame": frame, "reasoner": mine, "contract": theirs})

        cell = {"n": n, "r": r,
                **{k: meta[k] for k in ("facts", "events", "write_s", "load_s", "file_mb")},
                "frames": total, "agree": agree,
                "status_counts": dict(sorted(status_counts.items())),
                "unknown_abstain": {"frames": UNK_PER_CELL, "agree_missing": unk_agree},
                "reasoner_ms": round(sum(ms_r) / len(ms_r), 4),
                "contract_ms": round(sum(ms_c) / len(ms_c), 3),
                "index_build_s": round(index_s, 3), "cache_bytes": cache_bytes,
                "disagreements": disagreements}
        report["cells"].append(cell)
        maxrss_peak = max(maxrss_peak, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 3))
        print(json.dumps({"cell": f"{n}x{r}", "agree": f"{agree}/{total}",
                          "unk": f"{unk_agree}/{UNK_PER_CELL}",
                          "ms": cell["reasoner_ms"], "contract_ms": cell["contract_ms"],
                          "cache_mb": round(cache_bytes / 1e6, 1)}), flush=True)
        del nb, timed
        shutil.rmtree(cell_dir, ignore_errors=True)

    report["maxrss_gb"] = round(maxrss_peak, 2)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scale.json").write_text(json.dumps(report, indent=1))
    total_frames = sum(c["frames"] for c in report["cells"])
    total_agree = sum(c["agree"] for c in report["cells"])
    total_unk = sum(c["unknown_abstain"]["agree_missing"] for c in report["cells"])
    print(json.dumps({"stage": "scale", "agree": f"{total_agree}/{total_frames}",
                      "unknown_abstain": f"{total_unk}/{UNK_PER_CELL * len(GRID)}"}))


# =============================================================== sleep stage
def build_training_notebook(root: Path, seed: int):
    """A REAL contract notebook: 60 entities, the 8 core relations, ~15% missing facts."""
    if root.exists():
        shutil.rmtree(root)
    nb = C.Notebook(root)
    rng = rng_for("train-nb", seed)
    for rel in CORE8:
        nb.declare_relation(f"rel-{rel}", rel, True)
    eids = []
    for i in range(TRAIN_N):
        res = nb.new_entity(f"ent-{i}", f"T{seed % 10000:04d}_person_{i:03d}")
        eids.append(res.detail["entity_id"])
    k = 0
    for rel in CORE8:
        for eid in eids:
            if rng.random() < MISSING_RATE:
                continue
            tgt = eids[rng.randrange(TRAIN_N)]
            while tgt == eid:
                tgt = eids[rng.randrange(TRAIN_N)]
            k += 1
            res = nb.assert_fact(f"fact-{k}", "listening", "taught", eid, rel, {"entity": tgt})
            if res.status != C.SAVED:
                raise RuntimeError(res)
    return nb


def village_from_notebook(nb, reasoner: FableReasoner50):
    """Exp-44 Village adapter over the contract notebook's answering view (entity IDs as names)."""
    import fable_reasoner44 as R44
    eids = sorted(nb.entities)
    facts = {}
    for rel in CORE8:
        view = reasoner._view(nb, rel)
        for subj, entry in view.out.items():
            if entry[0] == "E":
                facts[(subj, rel)] = entry[1]
    return R44.Village(tuple(eids), facts)


def sample_resolvable_frames(nb, reasoner, rng, count, lengths, force_word=None):
    """(frame, target_eid) pairs of chains that resolve through the view."""
    eids = list(nb.entities)
    out: list[tuple[dict, str]] = []
    trials = 0
    while len(out) < count:
        trials += 1
        if trials > 400 * count:
            raise RuntimeError("could not sample resolvable frames")
        start = eids[rng.randrange(len(eids))]
        rels = [CORE8[rng.randrange(len(CORE8))] for _ in range(lengths[rng.randrange(len(lengths))])]
        if force_word is not None:
            pos = rng.randrange(len(rels) + 1)
            rels = rels[:pos] + [force_word] + rels[pos:]
        target = view_walk_view(reasoner, nb, start, rels)
        if target is None:
            continue
        out.append(({"name": nb.entities[start], "relations": rels, "entity_id": start}, target))
    return out


def install_word(reasoner: FableReasoner50, base_state, w: int, eps, v, m, seed: int,
                 nb, probe_frames, before: list, out: Path, tag: str) -> dict:
    """The Exp-46 recipe: robust+hardened fold fits, 4-fold CV gate, refit, save/reload, audit."""
    import torch
    import fable_reasoner44 as R44

    t0 = time.time()
    word = R44.WORD_NAMES[w]
    people = sorted({e.start for e in eps})
    rng_for("folds", w, tag, seed).shuffle(people)
    fold_of = {p: i % R44.FOLDS for i, p in enumerate(people)}
    oof: dict[int, dict] = {t: {} for t in R44.CHECKPOINTS}
    oof_nll: dict[int, float] = {t: 0.0 for t in R44.CHECKPOINTS}
    for f in range(R44.FOLDS):
        held = [e for e in eps if fold_of[e.start] == f]
        train = [e for e in eps if fold_of[e.start] != f]
        if not held or not train:
            continue
        _, saved = R44.fit_word(base_state, w, train, v, m, max(R44.CHECKPOINTS), seed,
                                f"{tag}/w{w}/fold{f}", R44.CHECKPOINTS)
        probe = R44.Reasoner()
        probe.load_state_dict(base_state)
        held_idx = [i for i, e in enumerate(eps) if fold_of[e.start] == f]
        for t in R44.CHECKPOINTS:
            probe.words[w].data.copy_(saved[t])
            for i, p in zip(held_idx, R44.predict(probe, v, m, held)):
                oof[t][i] = p
            oof_nll[t] += R44.word_nll(probe, v, m, held) * len(held)
    want = [e.answer if e.answer is not None else R44.UNKNOWN for e in eps]
    table = {t: {"match": sum(oof[t].get(i) == want[i] for i in range(len(eps))) / len(eps),
                 "nll": oof_nll[t] / len(eps)} for t in R44.CHECKPOINTS}
    rec: dict = {"word": word, "episodes": len(eps),
                 "distinct_people": len({e.start for e in eps}),
                 "cv_table": {str(t): {k: round(val, 5) for k, val in row.items()}
                              for t, row in table.items()}}
    eligible = [t for t in R44.CHECKPOINTS if table[t]["match"] >= R44.CV_FLOOR]
    if not eligible:
        rec.update(installed=False, reason=f"no checkpoint reached {R44.CV_FLOOR} OOF exact match",
                   seconds=round(time.time() - t0, 1))
        return rec
    best = min(table[t]["nll"] for t in eligible)
    chosen = min(t for t in eligible if table[t]["nll"] <= best + 1e-9)
    model, _ = R44.fit_word(base_state, w, eps, v, m, chosen, seed, f"{tag}/w{w}/refit")
    refit_pred = R44.predict(model, v, m, eps)
    agreement = sum(refit_pred[i] == oof[chosen][i] for i in range(len(eps))) / len(eps)
    logits = model.words[w].detach().tolist()
    routed_chain = [(("keep",) + CORE8)[max(range(len(row)), key=lambda i: row[i])] for row in logits]

    path = out / f"word-seed{seed}-{word}.pt"
    torch.save({"word": word, "logits": torch.tensor(logits)}, path)
    loaded = torch.load(path, map_location="cpu", weights_only=True)

    # candidate installed: base probe through the PROTOCOL must be identical
    held = reasoner.words.get(word)
    reasoner.load_word(word, logits)
    base_unchanged = [reasoner.answer(f, nb) for f in probe_frames] == before

    # 60 word frames, used for the reload check and (if installed) the audit
    word_frames = [{"name": nb.entities[eid], "relations": [word], "entity_id": eid}
                   for eid in sorted(nb.entities)]
    fresh = FableReasoner50()
    fresh.load_word(word, loaded["logits"].tolist())
    reload_identical = all(fresh.answer(f, nb) == reasoner.answer(f, nb)
                           for f in probe_frames + word_frames)

    installed = bool(agreement >= R44.AGREEMENT_FLOOR and base_unchanged and reload_identical)
    rec.update(chosen_updates=chosen, refit_agreement=round(agreement, 5),
               seen_accuracy=round(sum(a == b for a, b in zip(refit_pred, want)) / len(eps), 5),
               base_unchanged=base_unchanged, reload_identical=reload_identical,
               installed=installed, routed_chain=routed_chain,
               seconds=round(time.time() - t0, 1), path=str(path))

    if not installed:                                   # never leave an ungated word loaded
        if held is None:
            reasoner.words.pop(word, None)
        else:
            reasoner.words[word] = held
        return rec

    # ---- 60-start audit against the true walk, through the PROTOCOL
    audit_disagree = 0
    audit_rows = []
    audit_eps = []
    for eid in sorted(nb.entities):
        target = true_word_walk(reasoner, nb, eid, R44.WORD_CHAINS[w])
        frame = {"name": nb.entities[eid], "relations": [word], "entity_id": eid}
        mine = reasoner.answer(frame, nb)
        if target is None:
            ok_row = mine["status"] == C.MISSING_FACT
        else:
            ok_row = mine["status"] == C.OK and mine["fields"].get("answer") == nb.entities[target]
        if not ok_row:
            audit_disagree += 1
            if len(audit_rows) < 5:
                audit_rows.append({"eid": eid, "target": target, "got": mine})
        audit_eps.append(R44.Question(eid, (R44.R + w,), target))

    dense_model = R44.Reasoner()
    dense_model.load_state_dict(base_state)
    dense_model.words[w].data.copy_(torch.tensor(logits))
    dense_pred = R44.predict(dense_model, v, m, audit_eps)
    name_to_eid = {nb.entities[e]: e for e in nb.entities}
    dense_disagree = 0
    for q, d in zip(audit_eps, dense_pred):
        frame = {"name": nb.entities[q.start], "relations": [word], "entity_id": q.start}
        mine = reasoner.answer(frame, nb)
        if mine["status"] == C.OK:                    # protocol says display name, dense says E-id
            dense_ok = d != R44.UNKNOWN and name_to_eid.get(mine["fields"].get("answer")) == d
        else:
            dense_ok = d == R44.UNKNOWN
        if not dense_ok:
            dense_disagree += 1
    rec.update(audit_disagree_of_60=audit_disagree, dense_answer_disagree_of_60=dense_disagree,
               audit_examples=audit_rows)
    return rec


def stage_sleep(seed: int, out: Path, scratch: Path) -> None:
    import torch
    import fable_reasoner44 as R44
    import fable_hardgate46   # noqa: F401  -- installs the Exp-46 recipe onto R44 (robust + harden)

    torch.set_num_threads(1)
    out.mkdir(parents=True, exist_ok=True)
    nb = build_training_notebook(scratch / f"train-nb-{seed}", seed)
    reasoner = FableReasoner50()
    reasoner.warm(nb, CORE8)

    v = village_from_notebook(nb, reasoner)
    m = R44.notebook_matrices(v)

    # base router: identity, hardened, given by hand (open relation vocabulary)
    base = R44.Reasoner()
    with torch.no_grad():
        base.token_logits.fill_(-30.0)
        base.token_logits.fill_diagonal_(30.0)
    base_state = base.state_dict()

    # base probe through the protocol: must be untouched by any install
    rng = rng_for("probe", seed)
    probe_pairs = sample_resolvable_frames(nb, reasoner, rng, 100, (1, 2, 3))
    probe_frames = [f for f, _ in probe_pairs]
    before = [reasoner.answer(f, nb) for f in probe_frames]
    base_probe_acc = sum(
        1 for (f, tgt), ans in zip(probe_pairs, before)
        if ans["status"] == C.OK and ans["fields"]["answer"] == nb.entities[tgt]) / len(probe_pairs)

    report: dict = {"seed": seed, "episodes": EPISODES,
                    "base_probe_accuracy": round(base_probe_acc, 4),
                    "words": {}, "script_sha256": script_sha()}
    t0 = time.time()
    for word in WORD_NAMES:
        w = WORD_NAMES.index(word)
        eps, _ = R44.make_episodes(v, w, EPISODES, seed, "true")
        report["words"][word] = install_word(reasoner, base_state, w, eps, v, m, seed, nb,
                                             probe_frames, before, out, "true")
    report["all_words_installed"] = all(r.get("installed") for r in report["words"].values())

    after = [reasoner.answer(f, nb) for f in probe_frames]
    report["base_probe_unchanged_after_all"] = after == before

    # reload everything from disk into a fresh reasoner
    fresh = FableReasoner50()
    for word in WORD_NAMES:
        rec = report["words"][word]
        if rec.get("installed"):
            loaded = torch.load(rec["path"], map_location="cpu", weights_only=True)
            fresh.load_word(word, loaded["logits"].tolist())
    report["combined_reload_identical"] = all(
        fresh.answer(f, nb) == reasoner.answer(f, nb) for f in probe_frames)

    # reuse: a slept word inside a longer chain, through the protocol (recorded)
    reuse_rng = rng_for("reuse", seed)
    reuse_hits = reuse_total = 0
    for w, word in enumerate(WORD_NAMES):
        if not report["words"][word].get("installed"):
            continue
        for frame, tgt in sample_resolvable_frames(nb, reasoner, reuse_rng, 40, (1, 2), force_word=word):
            reuse_total += 1
            ans = reasoner.answer(frame, nb)
            if ans["status"] == C.OK and ans["fields"]["answer"] == nb.entities[tgt]:
                reuse_hits += 1
    report["reuse"] = {"frames": reuse_total,
                       "accuracy": round(reuse_hits / reuse_total, 4) if reuse_total else None}
    report["sleep_seconds"] = round(time.time() - t0, 1)
    (out / f"sleep-seed{seed}.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({"stage": "sleep", "seed": seed,
                      "installed": {w: report["words"][w].get("installed") for w in WORD_NAMES},
                      "audit": {w: report["words"][w].get("audit_disagree_of_60") for w in WORD_NAMES},
                      "dense": {w: report["words"][w].get("dense_answer_disagree_of_60") for w in WORD_NAMES},
                      "base_unchanged": report["base_probe_unchanged_after_all"],
                      "reload": report["combined_reload_identical"],
                      "reuse": report["reuse"]["accuracy"],
                      "seconds": report["sleep_seconds"]}))


# =============================================================== score + selftest
def stage_score(out: Path) -> None:
    scale = json.loads((out / "scale.json").read_text())
    frames = sum(c["frames"] for c in scale["cells"])
    agree = sum(c["agree"] for c in scale["cells"])
    unk_f = sum(c["unknown_abstain"]["frames"] for c in scale["cells"])
    unk_a = sum(c["unknown_abstain"]["agree_missing"] for c in scale["cells"])
    statuses_ok = all(all(c["status_counts"].get(s, 0) >= 1 for s in
                          (C.OK, C.MISSING_FACT, C.BROKEN_CHAIN, C.AMBIGUOUS, C.UNKNOWN_ENTITY))
                      for c in scale["cells"])
    print(f"S1 parity: {agree}/{frames} agree; all-5-statuses present: {statuses_ok}")
    print(f"S2 unknown-relation abstain: {unk_a}/{unk_f}")
    for c in scale["cells"]:
        print(f"  {c['n']}x{c['r']}: agree {c['agree']}/{c['frames']}  "
              f"reasoner {c['reasoner_ms']}ms  contract {c['contract_ms']}ms  "
              f"cache {round(c['cache_bytes'] / 1e6, 1)}MB  index {c['index_build_s']}s")
    installs = audits = denses = 0
    for seed in SEEDS:
        path = out / f"sleep-seed{seed}.json"
        if not path.exists():
            print(f"MISSING {path}")
            continue
        rep = json.loads(path.read_text())
        for rec in rep["words"].values():
            installs += int(bool(rec.get("installed")))
            audits += int(rec.get("audit_disagree_of_60") or 0)
            denses += int(rec.get("dense_answer_disagree_of_60") or 0)
        print(f"seed {seed}: installed {sum(bool(r.get('installed')) for r in rep['words'].values())}/3 "
              f"audit_wrong {sum(int(r.get('audit_disagree_of_60') or 0) for r in rep['words'].values())} "
              f"dense_disagree {sum(int(r.get('dense_answer_disagree_of_60') or 0) for r in rep['words'].values())} "
              f"base_unchanged {rep['base_probe_unchanged_after_all']} "
              f"reload {rep['combined_reload_identical']} reuse {rep['reuse']['accuracy']}")
    print(f"D1 installs: {installs}/9   D2 audit wrong: {audits}/540   "
          f"D3 dense-vs-protocol disagree: {denses}/540")


def selftest() -> int:
    import tempfile
    failures = []
    with tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parent)) as tmp:
        nb = C.Notebook(Path(tmp) / "nb")
        nb.declare_relation("r-mother", "mother", True)
        nb.declare_relation("r-city", "city", True)
        nb.declare_relation("r-friend", "friend", False)
        ids = {name: nb.new_entity(f"e-{name}", name).detail["entity_id"]
               for name in ("Mira", "Tom", "Ana")}
        mira2 = nb.new_entity("e-mira2", "Mira").detail["entity_id"]
        nb.add_alias("al1", ids["Tom"], "Tommy")
        nb.assert_fact("f1", "listening", "taught", ids["Mira"], "mother", {"entity": ids["Ana"]})
        nb.assert_fact("f2", "listening", "taught", ids["Ana"], "city", {"literal": "Porto"})
        nb.assert_fact("f3", "listening", "taught", ids["Mira"], "city", {"literal": "Lisbon"})
        nb.assert_fact("f4", "listening", "taught", ids["Tom"], "friend", {"entity": ids["Ana"]})
        nb.assert_fact("f5", "listening", "taught", ids["Tom"], "friend", {"entity": ids["Mira"]})
        nb.assert_fact("f6", "creative", "proposed", ids["Ana"], "mother", {"entity": ids["Tom"]})
        nb.assert_fact("f7", "thinking", "web-quarantine", ids["Ana"], "city", {"literal": "Madrid"},
                       provenance={"url": "https://x.org", "quoted_span": "s"})
        nb.assert_fact("f9", "listening", "taught", mira2, "city", {"literal": "Oslo"})
        nb.add_alias("al2", mira2, "Mira K")

        reasoner = FableReasoner50()
        frames = [
            {"name": "Mira", "relations": ["mother"]},                          # OK entity
            {"name": "Mira", "relations": ["mother", "city"]},                  # OK literal final
            {"name": "Mira", "relations": ["city", "mother"]},                  # BROKEN_CHAIN
            {"name": "Ana", "relations": ["mother"]},                           # MISSING (proposed only)
            {"name": "Mira", "relations": ["city"]},                            # OK literal
            {"name": "Mira", "relations": []},                                  # BAD_REQUEST
            {"name": "Ghost", "relations": ["mother"]},                         # UNKNOWN_ENTITY
            {"name": "Tommy", "relations": ["friend"]},                         # alias -> OK multi
            {"name": "Mira", "relations": ["friend"]},                          # MISSING
            {"name": "nobody", "relations": ["mother"], "entity_id": ids["Mira"]},
            {"name": "x", "relations": ["mother"], "entity_id": "E9999"},       # BAD_REQUEST
            {"name": "Mira K", "relations": ["city"]},                          # alias -> OK Oslo
            {"name": "Mira", "relations": ["mother", "never_taught_rel"]},      # unknown mid-chain
            {"name": "Mira", "relations": ["mother"] * 9},                      # 9 hops -> BAD_REQUEST
            {"name": "Ana", "relations": ["city", "mother", "city"]},           # BROKEN at hop 2
            {"name": "Mira", "relations": ["mother", "city"]},
        ]
        for frame in frames:
            mine, theirs = reasoner.answer(frame, nb), contract_answer(frame, nb)
            if mine != theirs:
                failures.append({"frame": frame, "reasoner": mine, "contract": theirs})
        n_compared = len(frames)

        # cache invalidation: a new write must be visible to the next answer
        nb.assert_fact("f10", "listening", "taught", ids["Ana"], "friend", {"entity": ids["Tom"]},
                       correction=True)
        frame = {"name": "Ana", "relations": ["friend"]}
        mine, theirs = reasoner.answer(frame, nb), contract_answer(frame, nb)
        n_compared += 1
        if mine != theirs or mine["fields"].get("answer") != "Tom":
            failures.append({"frame": frame, "reasoner": mine, "contract": theirs, "note": "cache"})

        # unknown relation abstains with MISSING and never invents an answer
        abst = reasoner.answer({"name": "Tom", "relations": ["never_taught_rel"]}, nb)
        n_compared += 1
        if abst["status"] != C.MISSING_FACT or "answer" in abst["fields"] or \
                abst != contract_answer({"name": "Tom", "relations": ["never_taught_rel"]}, nb):
            failures.append({"abstain": abst})

        # AMBIGUOUS on the shared name
        amb = reasoner.answer({"name": "Mira", "relations": ["city"]}, nb)
        n_compared += 1
        if amb["status"] != C.AMBIGUOUS or amb != contract_answer(
                {"name": "Mira", "relations": ["city"]}, nb):
            failures.append({"ambiguous": amb})

    for f in failures:
        print(json.dumps(f, default=str)[:500])
    print(f"selftest: {n_compared} frames compared, {len(failures)} disagreements")
    print("SELFTEST", "PASS" if not failures else "FAIL")
    return 0 if not failures else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Experiment 50: reasoner on the real notebook contract")
    p.add_argument("--stage", choices=("scale", "sleep", "score", "selftest"))
    p.add_argument("--seed", type=int)
    p.add_argument("--tag", default="reg", help="scale sampling tag: reg (registered) or dev")
    p.add_argument("--questions", type=int, default=300, help="frames per cell (registered 300)")
    p.add_argument("--out", type=Path)
    p.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    a = p.parse_args()
    if a.stage == "selftest":
        return selftest()
    if a.stage == "score":
        if a.out is None:
            p.error("--out required")
        stage_score(a.out)
        return 0
    if a.out is None:
        p.error("--out required")
    a.scratch.mkdir(parents=True, exist_ok=True)
    if a.stage == "scale":
        stage_scale(a.tag, a.questions, a.out, a.scratch)
    else:
        if a.seed is None:
            p.error("--seed required for sleep")
        stage_sleep(a.seed, a.out, a.scratch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
