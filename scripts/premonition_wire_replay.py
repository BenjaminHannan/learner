"""Frozen-weight wire query-rule replay (Claude, 2026-09-19) -- EVAL ONLY, additive, development diagnostic.

Implements design/v3/15-relation-fix-review.md "Ordered build sequence" item 1: additive passive
ratio/transport instrumentation plus a frozen-weight WG / WG+cap replay of the saved relation-shortcut
("wire") checkpoints, with the paired plain checkpoints carrying design/v3/14-relation-fix.md's original
d1 donor/transport assay only.  No training, no optimizer, no gradient step, no fitted probe, no GPU, no
network, no test split.  Nothing outside the output root given on the command line is written; no existing
file is edited and artifacts/claude-pairsuite-20260919/ is never touched or regenerated.

    W       q = q0 + g*v
    WG      q = q0 + h*g*v
    WGC(e)  q = q0 + h*clip(g*v, e*||q0||)          (addition bypassed when ||q0|| <= the store epsilon)

    q0 = heads.query(z),  v = W_r E[REL at q_span[:,1]-2],  g = sigmoid(rel_gate(z)),
    h  = (the question span shows no LINK token) OR m,   m = any(episode.fetched[:, :store.null])

`m` is the real-card mask: the NULL column is excluded and `episode.count` (which also counts NULL
insertions) is never used.  LINK detection reads the VISIBLE question span only -- a disclosed privileged
lexical parse, exactly as [15] specifies; no evaluator hop tag, gold line, true friend or answer is ever
consulted by the query rule.

Everything substantive is imported from the existing, already-executed source:

  scripts/premonition_relation_shortcut.py   the wire itself (subclass NOT modified; its `_shortcut_query`
                                             is temporarily re-bound on the instance, which covers BOTH the
                                             `_step` and the `_recall` call sites)
  scripts/premonition_pair_suite.py          fresh-world twin generators (`_make_pair`), edit semantics,
                                             joint-correct counting, `audit_set`, `own_fixed_parity`
  scripts/premonition_handoff_diag.py        label stripping, the visible-field view, the native condition U
                                             (4 fixed loops, ASK gate, hard top-1, at most 3 requests,
                                             HALT ignored) and the label-perturbation check
  scripts/premonition_first_card_probe.py    checkpoint loader (`load_from`), weight fingerprint, fetch
                                             classes (`classify`)

THIS IS A DEVELOPMENTAL DIAGNOSTIC.  It is not G_pair, not a certification and not a training result.

    PY -B scripts/premonition_wire_replay.py panels --out ROOT/panels [--worlds 256]
    PY -B scripts/premonition_wire_replay.py run --ckpt-dir DIR [--ckpt-dir DIR] --root ROOT
                                                 [--workers N] [--limit K]
    PY -B scripts/premonition_wire_replay.py table --root ROOT --out ROOT/summary
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_first_card_probe as P  # noqa: E402
import premonition_handoff_diag as H  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_pair_suite as PS  # noqa: E402
import premonition_relation_shortcut as RS  # noqa: E402

SOURCE = Path(__file__).resolve()
EVALUATOR_VERSION = "premonition-wire-replay-v1"
DEFAULT_ROOT = L.ROOT / "artifacts" / "claude-wire-replay-20260919"

# Never write here, and never regenerate it.
PROTECTED = (L.ROOT / "artifacts" / "claude-pairsuite-20260919",)
HISTORICAL_SUITE = PROTECTED[0]
WIRE_CKPT_DIR = L.ROOT / "artifacts" / "claude-keypool-relcut-20260919" / "control" / "ckpt"
PLAIN_CKPT_DIR = L.ROOT / "artifacts" / "claude-keypool-20260919" / "control" / "ckpt"

# The panel seed string.  Distinct from every earlier panel namespace (the historical suite uses
# "premonition-pairsuite-<cell>-<seed>-<i>"; the handoff sets use "premonition-handoff-..."; the
# teacher-delay panels use "premonition-teacher-delay-v2-panel|...").
PANEL_NAMESPACE = "premonition-wire-replay-20260919-v1"

LOOPS = PS.LOOPS                     # 4 fixed loops, HALT ignored
REQUESTS = PS.REQUESTS               # at most 3 requests
CONDITION = PS.CONDITION             # "U": native hard top-1 with the ASK gate, no eligibility mask
WORLDS = 256
MATCHED_WORLDS_PER_CHUNK = 8         # 8 worlds x 6 question variants = 48 visits per chunk
TWIN_WORLDS_PER_CHUNK = 32

VARIANTS = ("W", "WG", "WGC25", "WGC50")
ETA = {"W": None, "WG": None, "WGC25": 0.25, "WGC50": 0.50}
CAPS = (0.25, 0.50)                  # the only two caps considered; no outcome-driven expansion

# torch.nn.functional.normalize's default eps, which is what CardStore.ask applies to the query.
STORE_NORM_EPS = 1e-12
NEAR_ZERO = 1e-6                     # "near-zero q0" / "tiny residual" reporting threshold
R_BINS = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.0, 1.5, 2.0, 4.0)

# The six question variants of one matched world: same asker a, same friend b, same complete causal
# pre-question story prefix, same store content; only the question line differs.
MATCHED_QUESTIONS = ("two_hop_r0", "two_hop_r1", "two_hop_r2",
                     "one_hop_r0", "one_hop_r1", "one_hop_r2")
HELDOUT_QUESTION = "two_hop_r2"
PRACTISED_QUESTIONS = ("two_hop_r0", "two_hop_r1")
ONE_HOP_QUESTIONS = ("one_hop_r0", "one_hop_r1", "one_hop_r2")
PANELS = ("matched", "c4", "c5")
# The canonical slot of each question kind inside the generator's fixed question block
# (the generator always emits one-hop, one-hop, two-hop, two-hop).
ONE_HOP_SLOT = 1
TWO_HOP_SLOT = 3
LAYOUT_NOTE = (
    "MEASURED DEVIATION from [14]: the saved wire checkpoints switch on the question's SLOT in the "
    "visit's fixed question block rather than on the visible LINK token -- in a 16-world probe of "
    "relcutlong-s1-12000 a two-hop question at slot 1 or 2 fetched the correct LINK 0/16 times and a "
    "one-hop question at slot 3 or 4 fetched its gold card 0/16 times, while both work at their "
    "canonical slots; long-s0-12000 is far less slot-sensitive. Each question is therefore placed at "
    "its canonical slot: one-hop donors at slot 1 (prefix = the story), two-hop questions at slot 3 "
    "(prefix = the story plus that world's own two generator one-hop questions, fixed once and shared "
    "by all three two-hop variants). The story, the world and the pre-question STORE are identical "
    "across all six episodes; question lines never become cards and carry no answer after label_free.")

PANEL_CONFIG = {
    "matched": {"kind": "single", "edit": None, "invariant": False, "token_diffs": None,
                "title": "matched six-question worlds: native two-hop a LINK r and one-hop donor b r, "
                         "r = 0,1,2, after the same complete causal pre-question prefix"},
    "c4": {"kind": "pair", "edit": "link", "invariant": False, "token_diffs": 1,
           "title": "held-out changed-link twin pair (pair-suite edit semantics, joint-correct counting)"},
    "c5": {"kind": "pair", "edit": "endpoint", "invariant": False, "token_diffs": 2,
           "title": "held-out changed-endpoint-value twin pair (inventory-preserving swap)"},
}

SKIPPED = [
    "no training, no optimizer, no gradient step and no fitted probe of any kind",
    "no fresh trained WG/WGC arm: this is the frozen-weight replay only (build-sequence item 1)",
    "no G_pair cells c1/c2/c6 and no READS: this panel is a development diagnostic, not the gate",
    "no escape-timing statistic: final checkpoints cannot establish plateau-time residual magnitudes",
    "the cached-state cap intervention caps the NATIVE W residual (no guard); whole-episode WG/WGC "
    "replays are reported separately, because a changed first fetch changes later states",
]
NOT_A_CLAIM = ("developmental diagnostic on frozen historical checkpoints; NOT G_pair, NOT a "
               "certification, NOT a training result, and nothing causal about training escapes")


# ------------------------------------------------------------------------------------------- utilities
def sha256_file(path) -> str:
    return H.sha256_file(Path(path))


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def read_json(path) -> dict:
    return json.loads(Path(path).read_text())


def directory_sha256(folder) -> str:
    """A stable digest of every file under `folder` (name + bytes), for before/after protection checks."""
    digest = hashlib.sha256()
    for path in sorted(Path(folder).rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(folder)).encode())
            digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def guard_output(path) -> Path:
    """Refuse any output path inside a protected historical directory."""
    resolved = Path(path).expanduser().resolve()
    for root in PROTECTED:
        if resolved == root.resolve() or resolved.is_relative_to(root.resolve()):
            raise SystemExit(f"refusing to write inside the protected historical directory {root}: {resolved}")
    return resolved


def frozen_source(name: str) -> Path:
    return L.ARCHIVE / "frozen" / "premonition" / name


def source_hashes() -> dict:
    out = {"scripts/premonition_wire_replay.py": sha256_file(SOURCE),
           "scripts/premonition_pair_suite.py": sha256_file(Path(PS.__file__).resolve()),
           "scripts/premonition_handoff_diag.py": sha256_file(H.SOURCE),
           "scripts/premonition_first_card_probe.py": sha256_file(Path(P.__file__).resolve()),
           "scripts/premonition_relation_shortcut.py": sha256_file(Path(RS.__file__).resolve()),
           "scripts/premonition_ovn_ladder.py": sha256_file(Path(L.__file__).resolve())}
    for name in ("model.py", "store.py", "toy_ladder.py", "train.py", "answer_path.py", "config.py",
                 "batch.py"):
        out[f"frozen/premonition/{name}"] = sha256_file(frozen_source(name))
    return out


def _quantile(values: list, q: float) -> float:
    """Nearest-rank quantile of an already sorted list (no interpolation, no numpy)."""
    if not values:
        return float("nan")
    k = max(0, min(len(values) - 1, int(math.ceil(q * len(values))) - 1))
    return values[k]


class Dist:
    """A plain list of samples with medians / p90 / p95 / max and an optional fixed-bin histogram."""

    def __init__(self, bins=None):
        self.values: list = []
        self.bins = bins

    def add(self, x) -> None:
        self.values.append(float(x))

    def extend(self, xs) -> None:
        self.values.extend(float(x) for x in xs)

    def summary(self) -> dict:
        n = len(self.values)
        if n == 0:
            return {"n": 0}
        ordered = sorted(self.values)
        out = {"n": n, "min": round(ordered[0], 8), "median": round(_quantile(ordered, 0.5), 8),
               "p90": round(_quantile(ordered, 0.90), 8), "p95": round(_quantile(ordered, 0.95), 8),
               "max": round(ordered[-1], 8), "mean": round(sum(ordered) / n, 8)}
        if self.bins:
            hist = {}
            for i, low in enumerate(self.bins):
                high = self.bins[i + 1] if i + 1 < len(self.bins) else float("inf")
                label = f"[{low:g},{high:g})" if high != float("inf") else f"[{low:g},inf)"
                hist[label] = sum(1 for x in ordered if low <= x < high)
            hist["below_first_bin"] = sum(1 for x in ordered if x < self.bins[0])
            out["hist"] = hist
        return out


# --------------------------------------------------------------------------------- matched-panel worlds
def _fact_lines(spec, lines) -> dict:
    """{('attr', e, r): line index, ('link', e): line index} parsed from the VISIBLE story lines."""
    from premonition.batch import N_ENT
    from premonition.toy_ladder import WORLD
    where = {}
    for k, line in enumerate(lines):
        if line.question or len(line.tokens) < 4 or line.tokens[0] != WORLD:
            continue
        entity = line.tokens[1] - spec.vocab_size
        middle = line.tokens[2]
        if not (0 <= entity < N_ENT):
            continue
        if middle == spec.link:
            where[("link", entity)] = k
        elif spec.relation(0) <= middle < spec.relation(0) + spec.relations:
            where[("attr", entity, middle - spec.relation(0))] = k
    return where


def _question_line(spec, rng, *, subject: int, relation: int, value: int, gold: tuple, hops: int):
    """One question line in the generator's own fixed grammar; `assemble` reads the layout back out."""
    from premonition.toy_ladder import ANSWER, FEEDBACK, Line, NEWLINE, QUESTION
    if hops == 2:
        ask = [QUESTION, spec.vocab_size + subject, spec.link, spec.relation(relation), ANSWER]
    else:
        ask = [QUESTION, spec.vocab_size + subject, spec.relation(relation), ANSWER]
    filler = spec.filler(rng.randrange(spec.fillers))
    return Line(ask + [spec.value(value), FEEDBACK, filler, NEWLINE], question=True, ents=(subject,),
                answer=[spec.value(value)], gold=gold, supplied=(), hops=hops, relation=relation)


def _make_matched_world(spec, rng):
    """One world: the complete causal story prefix, a fixed asker a, its friend b, and the six questions.

    MEASURED DEVIATION from [14]'s "same complete causal pre-question prefix".  The saved wire
    checkpoints switch on the question's SLOT in the visit's fixed question block, not on the visible
    LINK token: at slots 1-2 a two-hop question is answered as if it were one-hop (0/16 correct first
    cards in a probe of relcutlong-s1-12000), and at slots 3-4 a one-hop question is answered as if it
    were two-hop (0/16).  The paired plain checkpoints are far less slot-sensitive.  Every question is
    therefore placed at the CANONICAL slot the generator uses for its hop type: one-hop donors at slot 1
    (prefix = the story), two-hop questions at slot 3 (prefix = the story plus this world's own two
    generator one-hop questions, fixed once and shared by all three two-hop variants).  The story, the
    world and therefore the pre-question STORE are identical across all six episodes -- question lines
    never become cards -- and the two extra prefix question lines carry no answer after `label_free`.
    """
    from premonition import toy_ladder
    rejections = Counter()
    while True:
        lines, world, _plan = toy_ladder.visit(spec, rng, training=False)
        story = [line for line in lines if not line.question]
        prefix = [line for line in lines if line.question and line.hops == 1][:TWO_HOP_SLOT - 1]
        if len(prefix) != TWO_HOP_SLOT - 1:
            rejections["not_enough_one_hop_prefix_questions"] += 1
            continue
        where = _fact_lines(spec, story)
        asker = rng.choice(world.ents)
        friend = world.friend[asker]
        needed = [("link", asker)] + [("attr", friend, r) for r in range(spec.relations)] \
            + [("attr", asker, r) for r in range(spec.relations)]
        if any(key not in where for key in needed):
            rejections["missing_fact_line"] += 1
            continue
        if friend == asker:
            rejections["self_friend"] += 1
            continue
        questions = {}
        for r in range(spec.relations):
            value = world.attr[(friend, r)]
            questions[f"two_hop_r{r}"] = _question_line(
                spec, rng, subject=asker, relation=r, value=value, hops=2,
                gold=(where[("link", asker)], where[("attr", friend, r)]))
            questions[f"one_hop_r{r}"] = _question_line(
                spec, rng, subject=friend, relation=r, value=value, hops=1,
                gold=(where[("attr", friend, r)],))
        facts = {"asker": asker, "friend": friend, "link_line": where[("link", asker)],
                 "endpoint_line": {str(r): where[("attr", friend, r)] for r in range(spec.relations)},
                 "asker_attr_line": {str(r): where[("attr", asker, r)] for r in range(spec.relations)},
                 "value": {str(r): world.attr[(friend, r)] for r in range(spec.relations)},
                 "story_lines": len(story)}
        return story, prefix, questions, facts, rejections


def panel_rng(panel: str, index: int) -> random.Random:
    """Panel content is a pure function of (namespace, panel, index).  No path, no checkpoint, no clock."""
    return random.Random(f"{PANEL_NAMESPACE}|{panel}|{index}")


def build_matched_panel(n: int, spec) -> dict:
    """256 matched worlds, six independently reset question episodes each (one question per visit)."""
    from premonition import toy_ladder
    from premonition.train import label_free
    rejections, worlds = Counter(), []
    for i in range(int(n)):
        story, prefix, questions, facts, rej = _make_matched_world(spec, panel_rng("matched", i))
        rejections.update(rej)
        worlds.append((story, prefix, questions, facts, i))
    chunks = []
    for start in range(0, len(worlds), MATCHED_WORLDS_PER_CHUNK):
        block = worlds[start:start + MATCHED_WORLDS_PER_CHUNK]
        rows = []
        for story, prefix, questions, facts, index in block:
            for name in MATCHED_QUESTIONS:
                head = list(story) + (list(prefix) if name.startswith("two_hop") else [])
                rows.append(head + [questions[name]])
        full = label_free(toy_ladder.assemble(spec, rows, prefix=f"matched-{start}")[0])
        keep, meta = [], []
        for v, (story, _prefix, _questions, facts, index) in enumerate(block):
            for k, name in enumerate(MATCHED_QUESTIONS):
                visit = v * len(MATCHED_QUESTIONS) + k
                target_line = len(rows[visit]) - 1
                found = ((full.q_visit == visit) & (full.q_line == target_line)).nonzero()
                if found.shape[0] != 1:
                    raise SystemExit("matched: the target question was not assembled exactly once")
                q = int(found[0])
                keep.append(q)
                hops = 2 if name.startswith("two_hop") else 1
                relation = int(name[-1])
                meta.append({
                    "index": index, "visit": visit, "question": name, "hops": hops,
                    "relation": relation, "slot": TWO_HOP_SLOT if hops == 2 else ONE_HOP_SLOT,
                    "question_line": target_line, "story_lines": facts["story_lines"],
                    "subject": facts["asker"] if hops == 2 else facts["friend"],
                    "asker": facts["asker"], "friend": facts["friend"],
                    "dest_a": facts["friend"] if hops == 2 else -1,
                    "link_line": facts["link_line"],
                    "endpoint_line": facts["endpoint_line"][str(relation)],
                    "asker_attr_line": facts["asker_attr_line"][str(relation)],
                    "value_a": facts["value"][str(relation)],
                    "answer_a": full.answer[q][full.answer[q] != -100].tolist(),
                    "gold_a": [x for x in full.gold_lines[q].tolist() if x >= 0],
                    "key_a": f"matched|{index}|{name}"})
        # the six episodes of a world must share ONE identical causal story and therefore one store
        for v in range(len(block)):
            base = v * len(MATCHED_QUESTIONS)
            story_lines = block[v][3]["story_lines"]
            head = int(full.line_start[base, story_lines])
            for k in range(len(MATCHED_QUESTIONS)):
                visit = base + k
                if int(full.line_start[visit, story_lines]) != head or not bool(
                        (full.tokens[base, :head] == full.tokens[visit, :head]).all()):
                    raise SystemExit("matched: the six episodes do not share one causal story prefix")
        chunk = H._keep_questions(full, keep)
        if int(chunk.q_visit.shape[0]) != len(meta):
            raise SystemExit("matched: one scored question per visit is required")
        if chunk.q_visit.tolist() != list(range(len(meta))):
            raise SystemExit("matched: the kept questions do not follow visit order")
        chunks.append({"a": chunk, "meta": meta})
    return {"name": "matched", "kind": "single", "n": int(n), "questions": list(MATCHED_QUESTIONS),
            "slots": {"one_hop": ONE_HOP_SLOT, "two_hop": TWO_HOP_SLOT},
            "layout_note": LAYOUT_NOTE, "chunks": chunks,
            "rejections": dict(sorted(rejections.items())),
            "worlds_per_chunk": MATCHED_WORLDS_PER_CHUNK, "rng_namespace": PANEL_NAMESPACE}


def build_twin_panel(name: str, n: int, spec) -> dict:
    """256 held-out twin pairs with the existing pair-suite edit semantics and joint-correct counting."""
    from premonition import toy_ladder
    from premonition.train import label_free
    cfg = PANEL_CONFIG[name]
    rejections, target_values, worlds = Counter(), Counter(), []
    for i in range(int(n)):
        lines_a, lines_b, line, facts, rej = PS._make_pair(spec, panel_rng(name, i), cfg["edit"])
        rejections.update(rej)
        target_values[facts["value_a"]] += 1
        target_values[facts["value_b"]] += 1
        worlds.append((lines_a, lines_b, line, facts, i))
    chunks = []
    for start in range(0, len(worlds), TWIN_WORLDS_PER_CHUNK):
        block = worlds[start:start + TWIN_WORLDS_PER_CHUNK]
        rows = {"a": [w[0] for w in block], "b": [w[1] for w in block]}
        full = {s: label_free(toy_ladder.assemble(spec, rows[s], prefix=f"{name}-{s}-{start}")[0])
                for s in ("a", "b")}
        if full["a"].tokens.shape != full["b"].tokens.shape:
            raise SystemExit(f"{name}: the twins have different token shapes")
        differing = (full["a"].tokens != full["b"].tokens).sum(1).tolist()
        if differing != [cfg["token_diffs"]] * len(block):
            raise SystemExit(f"{name}: twins differ in {sorted(set(differing))} visible tokens, "
                             f"expected {cfg['token_diffs']}")
        keep, meta = {"a": [], "b": []}, []
        for v, (_la, _lb, line, facts, index) in enumerate(block):
            row = {"index": index, "visit": v, "line": line, "hops": 2, **facts}
            for s in ("a", "b"):
                q = int(((full[s].q_visit == v) & (full[s].q_line == line)).nonzero()[0])
                keep[s].append(q)
                row[f"answer_{s}"] = full[s].answer[q][full[s].answer[q] != -100].tolist()
                row[f"gold_{s}"] = [x for x in full[s].gold_lines[q].tolist() if x >= 0]
                row[f"key_{s}"] = f"{name}|{index}|{s}"
            meta.append(row)
        chunk = {s: H._keep_questions(full[s], keep[s]) for s in ("a", "b")}
        chunk["meta"] = meta
        chunks.append(chunk)
    return {"name": name, "kind": "pair", "n": int(n), "edit": cfg["edit"], "invariant": False,
            "chunks": chunks, "rejections": dict(sorted(rejections.items())),
            "target_value_counts": {str(k): v for k, v in sorted(target_values.items())},
            "worlds_per_chunk": TWIN_WORLDS_PER_CHUNK, "rng_namespace": PANEL_NAMESPACE}


def generate_panels(out_dir, worlds: int = WORLDS, *, quiet: bool = False) -> dict:
    """Write the three panels and their manifest of file hashes.  Refuses an existing directory."""
    import torch
    folder = guard_output(out_dir)
    if folder.exists():
        raise SystemExit(f"refusing to overwrite existing panels: {folder}")
    spec = L.spec()
    started = time.perf_counter()
    folder.mkdir(parents=True)
    manifest = {"evaluator_version": EVALUATOR_VERSION, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "written_before_any_model_was_loaded": True, "rng_namespace": PANEL_NAMESPACE,
                "panel_content_is_a_pure_function_of": ["rng_namespace", "panel", "world index"],
                "worlds": int(worlds), "full_size": int(worlds) == WORLDS,
                "generator_sources": {
                    "scripts/premonition_wire_replay.py": sha256_file(SOURCE),
                    "scripts/premonition_pair_suite.py": sha256_file(Path(PS.__file__).resolve()),
                    "scripts/premonition_handoff_diag.py": sha256_file(H.SOURCE),
                    "frozen/premonition/toy_ladder.py": sha256_file(frozen_source("toy_ladder.py"))},
                "spec": {k: getattr(spec, k) for k in ("entities", "relations", "values", "fillers",
                                                       "distractors", "gap", "one_hop", "two_hop",
                                                       "heldout_relation")},
                "loops": LOOPS, "requests": REQUESTS, "condition": CONDITION,
                "matched_questions": list(MATCHED_QUESTIONS), "variants": list(VARIANTS),
                "question_slots": {"one_hop": ONE_HOP_SLOT, "two_hop": TWO_HOP_SLOT},
                "layout_note": LAYOUT_NOTE,
                "eta_grid": list(CAPS), "store_norm_eps": STORE_NORM_EPS,
                "labels": "every label stays in the evaluator meta; the model is only ever handed "
                          "premonition_handoff_diag._strip_labels(batch)",
                "not_a_claim": NOT_A_CLAIM, "skipped": SKIPPED, "panels": {}}
    for name in PANELS:
        t0 = time.perf_counter()
        data = (build_matched_panel(worlds, spec) if name == "matched"
                else build_twin_panel(name, worlds, spec))
        # the matched panel scores six questions per world, so the audit's unit denominator is the
        # question count, not the world count
        audit = PS.audit_set(dict(data, n=data["n"] * len(MATCHED_QUESTIONS)) if name == "matched"
                             else data, spec)
        if audit["interpreter"]["accuracy"] != 1.0:
            raise SystemExit(f"{name}: the deterministic interpreter does not answer every example "
                             f"({audit['interpreter']['single_answer']}/{audit['interpreter']['answers']}); "
                             f"first failures {audit['interpreter']['failures']}")
        path = folder / f"{name}.pt"
        torch.save(data, path)
        manifest["panels"][name] = {
            "title": PANEL_CONFIG[name]["title"], "kind": data["kind"], "n": data["n"],
            "edit": PANEL_CONFIG[name]["edit"], "file": path.name, "sha256": sha256_file(path),
            "bytes": path.stat().st_size, "rejections": data["rejections"], "audit": audit,
            "seconds": round(time.perf_counter() - t0, 2)}
        if not quiet:
            print(f"{name:8s} {data['n']:5d} units  interpreter "
                  f"{audit['interpreter']['unit_accuracy']:.4f}  rejections {data['rejections']}  "
                  f"{time.perf_counter() - t0:.1f}s", flush=True)
    manifest["panel_content_sha256"] = sha256_json(
        {name: manifest["panels"][name]["sha256"] for name in PANELS})
    manifest["seconds"] = round(time.perf_counter() - started, 2)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if not quiet:
        print(f"wrote {folder / 'manifest.json'}  sha256 {sha256_file(folder / 'manifest.json')}  "
              f"content {manifest['panel_content_sha256'][:16]}  {manifest['seconds']}s", flush=True)
    return manifest


def load_panel(name: str, folder, manifest: dict):
    import torch
    info = manifest["panels"][name]
    path = Path(folder) / info["file"]
    if sha256_file(path) != info["sha256"]:
        raise SystemExit(f"{path} changed since the panel manifest was written")
    return torch.load(path, weights_only=False)


# ------------------------------------------------------------------------------------ the query variants
def link_flags(batch, spec):
    """[Q] bool: the VISIBLE question span shows a LINK token (the disclosed privileged lexical parse).

    Identical to premonition_handoff_diag.FieldView.q_has_link; no evaluator hop tag is consulted.
    """
    import torch
    span = batch.q_span
    width = batch.tokens.shape[1]
    span_width = int((span[:, 1] - span[:, 0]).max())
    pos = span[:, 0].unsqueeze(1) + torch.arange(span_width)
    inside = pos < span[:, 1].unsqueeze(1)
    tokens = torch.where(inside, batch.tokens[batch.q_visit.unsqueeze(1), pos.clamp(0, width - 1)],
                         torch.full_like(pos, -1))
    return (tokens == spec.link).any(1)


def clip_to(vector, radius):
    """clip(v, R) = v * min(1, R / ||v||) for ||v|| > 0; clip(0, R) = 0.  No clamped divisor is ever used."""
    import torch
    norm = vector.norm(dim=-1, keepdim=True)
    positive = norm > 0
    safe = torch.where(positive, norm, torch.ones_like(norm))
    factor = torch.where(positive,
                         torch.minimum(torch.ones_like(norm), radius / safe),
                         torch.zeros_like(norm))
    return vector * factor, factor


class QueryRule:
    """Temporarily replaces the wire's query computation at BOTH call sites (`_step` and `_recall`).

    `scripts/premonition_relation_shortcut.py` is never edited: `_shortcut_query` is re-bound on THIS
    instance for the duration of the context and deleted afterwards, exactly as
    `premonition_handoff_diag.traced_own_fixed` wraps `_insert`.  `_start` is wrapped additively (it only
    attaches the visible LINK flags) and `_recall` is wrapped additively (it only marks the diagnostic
    call so its query never enters the telemetry).

    Variant "W" reproduces the saved wire bit-for-bit: the same `q0 + g*v` expression in the same order.
    """

    def __init__(self, model, variant: str, spec, *, record: bool = True):
        if variant not in VARIANTS:
            raise ValueError(f"unknown variant {variant!r}")
        self.model = model
        self.variant = variant
        self.eta = ETA[variant]
        self.spec = spec
        self.record = bool(record)
        self.wire = hasattr(model, "_shortcut_query")
        if not self.wire and variant != "W":
            raise SystemExit("a plain checkpoint carries no relation residual; only variant W is defined "
                             "for it (no wire vector is ever inserted into a plain model)")
        self.calls: list = []
        self.step = None
        self._in_recall = False
        self._entered = False

    # ----------------------------------------------------------------- context management
    def __enter__(self):
        model = self.model
        self._orig_start = model._start
        self._orig_recall = model._recall
        spec = self.spec

        def start(batch, hidden, store, mentions):
            episode = self._orig_start(batch, hidden, store, mentions)
            episode.wire_replay_link = link_flags(batch, spec)
            return episode

        def recall(store, episode, index, rows, gold):
            self._in_recall = True
            try:
                return self._orig_recall(store, episode, index, rows, gold)
            finally:
                self._in_recall = False

        model._start = start
        model._recall = recall
        if self.wire:
            self._orig_query = model._shortcut_query
            model._shortcut_query = self._query
        else:
            self._handle = model.heads.query.register_forward_hook(self._plain_hook)
        self._entered = True
        return self

    def __exit__(self, *exc):
        model = self.model
        del model._start
        del model._recall
        if self.wire:
            del model._shortcut_query
        else:
            self._handle.remove()
        self._entered = False
        return False

    # ----------------------------------------------------------------- recording
    def begin_step(self, step) -> None:
        self.step = step

    def take(self) -> list:
        calls, self.calls = self.calls, []
        return calls

    def _plain_hook(self, _module, _inputs, output):
        """A plain checkpoint has no residual: record q0 only, and never during a diagnostic `_recall`."""
        import torch
        if not self.record or self._in_recall or self.step is None:
            return
        q0 = output.detach()
        zero = torch.zeros(q0.shape[0])
        self.calls.append({"step": int(self.step), "q0": q0, "delta": torch.zeros_like(q0),
                           "query": q0, "a": q0.norm(dim=-1), "b": zero.clone(),
                           "cos": torch.full_like(zero, float("nan")), "g": torch.full_like(zero, float("nan")),
                           "v_norm": zero.clone(), "h": torch.ones(q0.shape[0], dtype=torch.bool),
                           "m": torch.zeros(q0.shape[0], dtype=torch.bool),
                           "applied": zero.clone(), "capped": torch.zeros(q0.shape[0], dtype=torch.bool),
                           "residual": False})

    # ----------------------------------------------------------------- the one change
    def _query(self, register, episode, index, step=None):
        """The wire's `_shortcut_query`, with the addition replaced by this variant's rule."""
        import torch
        model = self.model
        q0 = model.heads.query(register)
        rel = getattr(episode, "rel_token", None)
        if rel is None or not model.relation_shortcut:
            return q0
        gate = torch.sigmoid(model.rel_gate(register))                                   # [n, 1]
        v = model.rel_query(model.embed(rel[index]).to(register.dtype))                  # [n, k]
        gv = gate * v
        ones = torch.ones(gv.shape[0], dtype=torch.bool, device=gv.device)
        if self.variant == "W":
            delta, h, capped = gv, ones, torch.zeros_like(ones)
        else:
            link = episode.wire_replay_link[index]
            # the real-card mask: every store column EXCEPT the NULL column (never episode.count)
            real = episode.fetched[index][:, :-1].any(1)
            h = (~link) | real
            factor_h = h.unsqueeze(1).to(gv.dtype)
            if self.eta is None:
                delta, capped = gv * factor_h, torch.zeros_like(ones)
            else:
                norm_q0 = q0.norm(dim=-1, keepdim=True)
                clipped, factor = clip_to(gv, self.eta * norm_q0)
                delta = clipped * factor_h
                capped = (factor.squeeze(-1) < 1.0) & h
                bypass = (norm_q0 <= STORE_NORM_EPS)          # the store's normalization epsilon
                delta = torch.where(bypass, torch.zeros_like(delta), delta)
                capped = capped & ~bypass.squeeze(-1)
        query = q0 + delta
        if self.record and not self._in_recall and step is not None:
            with torch.no_grad():
                norm_q0 = q0.norm(dim=-1)
                norm_gv = gv.norm(dim=-1)
                good = (norm_q0 > 0) & (norm_gv > 0)
                dot = (q0 * gv).sum(-1)
                cos = torch.where(good, dot / torch.where(good, norm_q0 * norm_gv,
                                                          torch.ones_like(dot)),
                                  torch.full_like(dot, float("nan")))
                self.calls.append({"step": int(step), "q0": q0.detach(), "delta": delta.detach(),
                                   "query": query.detach(), "a": norm_q0.detach(), "b": norm_gv.detach(),
                                   "cos": cos.detach(), "g": gate.detach().squeeze(-1),
                                   "v_norm": v.detach().norm(dim=-1), "h": h.detach(),
                                   "m": (episode.fetched[index][:, :-1].any(1)).detach(),
                                   "applied": delta.detach().norm(dim=-1), "capped": capped.detach(),
                                   "residual": True})
        return query


# ------------------------------------------------------------------------------------- native replay
def replay(model, batch, rule, *, capture: bool = False) -> dict:
    """The native condition U (4 fixed loops, ASK gate, hard top-1, <= 3 requests, HALT ignored).

    Substantively identical to premonition_handoff_diag.run_condition(..., "U"); `capture` additionally
    keeps the frozen per-request state (scores, fetched mask, ASK) for cached-state interventions.
    """
    import torch
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    cards, asks, states, digests = [], [], [], []
    for step in range(LOOPS):
        rule.begin_step(step)
        rows, halt, ask, scores = model._step(episode, everyone, step, store)
        if step + 1 >= LOOPS:
            break
        digests.append(H._digest(scores))
        top = store.top(scores, model.config.top_k)
        picked = top.masked_fill((ask <= 0).unsqueeze(1), -1)
        if capture:
            states.append({"step": step, "scores": scores.detach().clone(),
                           "fetched": episode.fetched.detach().clone(),
                           "ask": (ask > 0).detach().clone(),
                           "ungated_top1": top[:, 0].detach().clone()})
        cards.append(picked[:, 0].detach().clone())
        asks.append((ask > 0).detach().clone())
        model._insert(episode, store, everyone, picked)
    rule.begin_step(None)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    return {"tokens": tokens, "lengths": lengths, "store": store, "store_lines": store.lines,
            "cards": torch.stack(cards, 1), "ask": torch.stack(asks, 1), "states": states,
            "calls": rule.take(), "fetched": episode.fetched.detach().clone(),
            "digests": digests, "q_visit": batch.q_visit, "q_line": batch.q_line}


class NullRule:
    """No wrapper at all: the unwrapped model, used for the observation-only parity check."""

    def begin_step(self, step) -> None:
        self.step = step

    def take(self) -> list:
        return []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def score_query(model, store, query, q_visit, q_line, fetched, questions):
    """CardStore.ask with identical keys, eligibility, age bias and temperature; only the query changes."""
    return store.ask(query, q_visit, q_line, model.heads.log_kappa.exp(), model.think.age_bias,
                     fetched, questions=questions)


def correctness(result, answers):
    import torch
    tokens, lengths = result["tokens"], result["lengths"]
    return torch.tensor([tokens[q, :int(lengths[q])].tolist() == answers[q] for q in range(len(answers))])


# -------------------------------------------------------------------------------- card classification
def one_hop_class(tokens, subject: int, relation_token: int, link_id: int, vocab: int) -> str:
    """Fetch classes for a one-hop donor question `b r` (the two-hop classes need a distinct asker)."""
    subj, middle = tokens[1] - vocab, tokens[2]
    if middle == link_id:
        return "own_link" if subj == subject else "other_link"
    if subj == subject:
        return "answer" if middle == relation_token else "subject_other_rel"
    return "other_same_rel" if middle == relation_token else "other_other_rel"


def card_class(batch, spec, q: int, line: int, meta: dict, store_lines: int) -> str:
    if line < 0:
        return "no_request"
    if line >= store_lines:
        return "null_card"
    visit = int(batch.q_visit[q])
    start = int(batch.line_start[visit, line])
    tokens = batch.tokens[visit, start:start + 4].tolist()
    relation_token = spec.relation(int(meta["relation"]))
    if int(meta["hops"]) == 2:
        return P.classify(tokens, int(meta["asker"]), int(meta["friend"]), relation_token,
                          spec.link, spec.vocab_size)
    return one_hop_class(tokens, int(meta["subject"]), relation_token, spec.link, spec.vocab_size)


def margin_of(scores_row, target: int):
    """(score[target] - best other eligible score, eligible?) at one frozen state; -inf handled."""
    best_other = float("-inf")
    target_score = float(scores_row[target])
    for i in range(len(scores_row)):
        if i == target:
            continue
        value = float(scores_row[i])
        if value > best_other:
            best_other = value
    if target_score == float("-inf"):
        return None, False
    if best_other == float("-inf"):
        return None, True
    return target_score - best_other, True


# --------------------------------------------------------------------------------------- accumulators
def question_stratum(meta: dict, spec) -> str:
    if int(meta["hops"]) == 1:
        return f"one_hop_r{int(meta['relation'])}"
    return ("two_hop_heldout" if int(meta["relation"]) == spec.heldout_relation
            else "two_hop_practised")


STRATA = ("one_hop_r0", "one_hop_r1", "one_hop_r2", "two_hop_practised", "two_hop_heldout")


class Telemetry:
    """Passive per-request telemetry, by stratum and scheduled request opportunity (1, 2, 3)."""

    def __init__(self):
        self.cells: dict = {}

    def cell(self, stratum: str, opportunity: int) -> dict:
        key = f"{stratum}|request{opportunity}"
        if key not in self.cells:
            self.cells[key] = {
                "stratum": stratum, "opportunity": opportunity, "count": 0,
                "a_norm_q0": Dist(), "b_norm_gv": Dist(), "ratio": Dist(R_BINS), "cos_q0_gv": Dist(),
                "gate": Dist(), "v_norm": Dist(), "applied_norm": Dist(),
                "counts": Counter()}
        return self.cells[key]

    def add(self, stratum: str, opportunity: int, row: dict) -> None:
        cell = self.cell(stratum, opportunity)
        cell["count"] += 1
        cell["a_norm_q0"].add(row["a"])
        cell["b_norm_gv"].add(row["b"])
        if not math.isnan(row["g"]):
            cell["gate"].add(row["g"])
        cell["v_norm"].add(row["v_norm"])
        cell["applied_norm"].add(row["applied"])
        if not math.isnan(row["cos"]):
            cell["cos_q0_gv"].add(row["cos"])
        near_zero = row["a"] < NEAR_ZERO
        tiny = row["b"] < NEAR_ZERO
        if near_zero:
            cell["counts"]["near_zero_q0"] += 1
        if tiny:
            cell["counts"]["tiny_residual"] += 1
        if near_zero or tiny:
            cell["counts"]["ratio_undefined"] += 1           # never manufactured by clamped division
        else:
            cell["ratio"].add(row["b"] / row["a"])
        cell["counts"]["ask_on" if row["ask"] else "ask_off"] += 1
        cell["counts"][f"selected_{row['card_class']}"] += 1
        cell["counts"]["guard_open_h1" if row["h"] else "guard_closed_h0"] += 1
        cell["counts"]["real_fetch_history" if row["m"] else "no_real_fetch_history"] += 1
        cell["counts"]["correct_link_history" if row["correct_link_history"] else
                       "no_correct_link_history"] += 1
        cell["counts"]["capped" if row["capped"] else "uncapped"] += 1

    def report(self) -> dict:
        out = {}
        for key, cell in sorted(self.cells.items()):
            out[key] = {"stratum": cell["stratum"], "opportunity": cell["opportunity"],
                        "count": cell["count"], "counts": dict(sorted(cell["counts"].items())),
                        "a_norm_q0": cell["a_norm_q0"].summary(),
                        "b_norm_gv": cell["b_norm_gv"].summary(),
                        "ratio_b_over_a": cell["ratio"].summary(),
                        "cos_q0_gv": cell["cos_q0_gv"].summary(),
                        "gate": cell["gate"].summary(), "v_norm": cell["v_norm"].summary(),
                        "applied_norm": cell["applied_norm"].summary()}
        return out


class Intervention:
    """Cached-state cap intervention at the frozen native W states: same keys, eligibility, ages, ASK."""

    def __init__(self):
        self.cells: dict = {}

    def cell(self, stratum: str, opportunity: int, label: str) -> dict:
        key = f"{stratum}|request{opportunity}|{label}"
        if key not in self.cells:
            self.cells[key] = {"stratum": stratum, "opportunity": opportunity, "condition": label,
                               "count": 0, "endpoint_margin": Dist(), "counts": Counter()}
        return self.cells[key]

    def add(self, stratum: str, opportunity: int, label: str, *, margin, eligible: bool,
            top1_changed, cap_active, top1_is_endpoint: bool) -> None:
        cell = self.cell(stratum, opportunity, label)
        cell["count"] += 1
        if margin is not None:
            cell["endpoint_margin"].add(margin)
        cell["counts"]["endpoint_eligible" if eligible else "endpoint_not_eligible"] += 1
        cell["counts"]["endpoint_margin_undefined" if margin is None else "endpoint_margin_defined"] += 1
        if top1_changed is not None:
            cell["counts"]["top1_changed" if top1_changed else "top1_same"] += 1
        if cap_active is not None:
            cell["counts"]["cap_active" if cap_active else "cap_inactive"] += 1
        cell["counts"]["top1_is_endpoint" if top1_is_endpoint else "top1_not_endpoint"] += 1

    def report(self) -> dict:
        return {key: {"stratum": c["stratum"], "opportunity": c["opportunity"],
                      "condition": c["condition"], "count": c["count"],
                      "counts": dict(sorted(c["counts"].items())),
                      "endpoint_margin": c["endpoint_margin"].summary()}
                for key, c in sorted(self.cells.items())}


class VariantStats:
    """Whole-episode replay outcomes for one query rule over the matched panel."""

    def __init__(self):
        self.answers = Counter()             # f"{stratum}_n" / f"{stratum}_correct"
        self.classes = {}                    # (stratum, opportunity) -> Counter
        self.link_first = Counter()          # stratum -> count of correct LINK at opportunity 1
        self.endpoint_given_link = Counter()  # stratum -> numerator / denominator
        self.guard = Counter()               # guard-opening events
        self.guard_detail = Counter()        # (opportunity, first card class, decoy available)
        self.applied_ratio_h1 = Dist(R_BINS)
        self.applied_ratio_all = Dist(R_BINS)

    def class_cell(self, stratum: str, opportunity: int) -> Counter:
        return self.classes.setdefault(f"{stratum}|request{opportunity}", Counter())

    def report(self) -> dict:
        return {"answers": dict(sorted(self.answers.items())),
                "request_classes": {k: dict(sorted(v.items())) for k, v in sorted(self.classes.items())},
                "first_request_correct_link": dict(sorted(self.link_first.items())),
                "endpoint_given_correct_link": dict(sorted(self.endpoint_given_link.items())),
                "guard_openings": dict(sorted(self.guard.items())),
                "guard_opening_detail": dict(sorted(self.guard_detail.items())),
                "applied_ratio_when_h1": self.applied_ratio_h1.summary(),
                "applied_ratio_all_states": self.applied_ratio_all.summary()}


# ------------------------------------------------------------------------------- matched-panel scoring
def _calls_by_step(calls: list) -> dict:
    return {int(c["step"]): c for c in calls}


def score_matched_variant(model, panel, spec, rule, stats: VariantStats, *, capture: bool,
                          telemetry: Telemetry = None, intervention: Intervention = None,
                          transport=None):
    """One whole-episode pass over the matched panel under `rule`.  Optionally the passive instruments."""
    import torch
    for chunk in panel["chunks"]:
        metas = chunk["meta"]
        batch = H._strip_labels(chunk["a"])                 # the model only ever sees the diary
        res = replay(model, batch, rule, capture=capture)
        ok = correctness(res, [m["answer_a"] for m in metas])
        cards = res["cards"]
        asks = res["ask"]
        calls = _calls_by_step(res["calls"])
        store_lines = res["store_lines"]
        classes = [[card_class(batch, spec, q, int(cards[q, step]), metas[q], store_lines)
                    for step in range(REQUESTS)] for q in range(len(metas))]
        for q, meta in enumerate(metas):
            stratum = question_stratum(meta, spec)
            stats.answers[f"{stratum}_n"] += 1
            stats.answers[f"{stratum}_correct"] += int(ok[q])
            link_line = int(meta["link_line"])
            endpoint_line = int(meta["endpoint_line"])
            first_link = int(meta["hops"]) == 2 and int(cards[q, 0]) == link_line
            if int(meta["hops"]) == 2:
                stats.link_first[f"{stratum}_n"] += 1
                stats.link_first[f"{stratum}_correct_link"] += int(first_link)
                if first_link:
                    stats.endpoint_given_link[f"{stratum}_denominator"] += 1
                    stats.endpoint_given_link[f"{stratum}_endpoint_at_request2"] += int(
                        int(cards[q, 1]) == endpoint_line)
            for step in range(REQUESTS):
                stats.class_cell(stratum, step + 1)[classes[q][step]] += 1
            # guard openings: the first opportunity at which h = 1 on a LINK question
            if int(meta["hops"]) == 2:
                opened = None
                for step in range(REQUESTS):
                    call = calls.get(step)
                    if call is None or not call["residual"]:
                        continue
                    if bool(call["h"][q]):
                        opened = step + 1
                        break
                label = "never" if opened is None else f"opportunity{opened}"
                stats.guard[f"{stratum}_{label}"] += 1
                if opened is not None and opened > 1:
                    # CardStore.eligible drops previously fetched real cards, so the asker decoy
                    # A(a, r) is still available exactly when it has not been taken yet
                    taken = [int(cards[q, s]) for s in range(opened - 1)]
                    decoy = int(meta["asker_attr_line"]) not in taken
                    stats.guard_detail[
                        f"{stratum}|{label}|first={classes[q][0]}|asker_decoy_"
                        f"{'available' if decoy else 'consumed'}"] += 1
            for step in range(REQUESTS):
                call = calls.get(step)
                if call is None or not call["residual"]:
                    continue
                a, b = float(call["a"][q]), float(call["b"][q])
                if a >= NEAR_ZERO and b >= NEAR_ZERO:
                    stats.applied_ratio_all.add(b / a)
                    if bool(call["h"][q]):
                        stats.applied_ratio_h1.add(float(call["applied"][q]) / a)
        if telemetry is not None:
            _add_telemetry(telemetry, spec, metas, calls, res, classes, cards)
        if intervention is not None:
            _cached_state_caps(model, spec, metas, batch, res, intervention)
        if transport is not None:
            _transport_chunk(model, spec, metas, batch, res, transport)


def _add_telemetry(telemetry: Telemetry, spec, metas, calls, res, classes, cards) -> None:
    """Passive telemetry at each scheduled request opportunity; `_recall` calls are never recorded."""
    # always publish these two strata, so an empty one is visibly zero rather than absent
    telemetry.cell("heldout_request2_all", 2)
    telemetry.cell("heldout_request2_correct_link_first", 2)
    for q, meta in enumerate(metas):
        stratum = question_stratum(meta, spec)
        link_line = int(meta["link_line"])
        correct_link = False
        for step in range(REQUESTS):
            call = calls.get(step)
            if call is None:
                continue
            row = {"a": float(call["a"][q]), "b": float(call["b"][q]), "cos": float(call["cos"][q]),
                   "g": float(call["g"][q]), "v_norm": float(call["v_norm"][q]),
                   "applied": float(call["applied"][q]), "h": bool(call["h"][q]),
                   "m": bool(call["m"][q]), "capped": bool(call["capped"][q]),
                   "ask": bool(res["ask"][q, step]), "card_class": classes[q][step],
                   "correct_link_history": correct_link}
            telemetry.add(stratum, step + 1, row)
            if stratum == "two_hop_heldout" and step == 1:
                telemetry.add("heldout_request2_all", 2, row)
                if correct_link:
                    telemetry.add("heldout_request2_correct_link_first", 2, row)
            if int(meta["hops"]) == 2 and int(cards[q, step]) == link_line:
                correct_link = True


def _cached_state_caps(model, spec, metas, batch, res, intervention: Intervention) -> None:
    """Score the unchanged query and caps 0.25 / 0.50 at the SAME frozen states."""
    import torch
    calls = _calls_by_step(res["calls"])
    store = res["store"]
    everyone = torch.arange(len(metas))
    for state in res["states"]:
        step = state["step"]
        call = calls.get(step)
        if call is None or not call["residual"]:
            return                                     # a plain checkpoint carries no residual
        native = state["scores"]
        q0, delta = call["q0"], call["delta"]
        gv = delta                                      # under W the applied residual is exactly g*v
        conditions = {"native": (native, None, None)}
        for cap in CAPS:
            clipped, factor = clip_to(gv, cap * q0.norm(dim=-1, keepdim=True))
            bypass = q0.norm(dim=-1, keepdim=True) <= STORE_NORM_EPS
            capped_query = q0 + torch.where(bypass, torch.zeros_like(clipped), clipped)
            scores = score_query(model, store, capped_query, res["q_visit"], res["q_line"],
                                 state["fetched"], everyone)
            conditions[f"cap{cap:.2f}"] = (scores, (factor.squeeze(-1) < 1.0), None)
        native_top1 = native.argmax(1)
        for label, (scores, cap_active, _unused) in conditions.items():
            top1 = scores.argmax(1)
            for q, meta in enumerate(metas):
                stratum = question_stratum(meta, spec)
                endpoint = int(meta["endpoint_line"])
                margin, eligible = margin_of(scores[q].tolist(), endpoint)
                intervention.add(
                    stratum, step + 1, label, margin=margin, eligible=eligible,
                    top1_changed=None if label == "native" else bool(top1[q] != native_top1[q]),
                    cap_active=None if cap_active is None else bool(cap_active[q]),
                    top1_is_endpoint=bool(int(top1[q]) == endpoint))


# ------------------------------------------------------------------------------------ transport assay
TRANSPORT_CANDIDATES = ("native_u2_heldout", "u_transport", "uW_transport", "u_donor")


def _new_transport_cell() -> dict:
    return {"worlds": 0, "unmatched": 0, "matched": 0, "invalid_transport": 0,
            "d1_norm": Dist(), "d2_norm": Dist(), "dW_norm": Dist(), "C_cos_d1_d2": Dist(),
            "R_norm_ratio": Dist(), "undefined_d1": 0, "undefined_d2": 0,
            "wire_displacement_norm": Dist(), "wire_displacement_cos_d1": Dist(),
            "candidates": {}}


def _transport_candidate(cell: dict, name: str) -> dict:
    if name not in cell["candidates"]:
        cell["candidates"][name] = {"n": 0, "counts": Counter(), "endpoint_margin": Dist(),
                                    "relation_margin_heldout_vs_practised": Dist()}
    return cell["candidates"][name]


def _unit(vector, eps: float = NEAR_ZERO):
    """(unit vector, norm, defined?) -- a norm below `eps` is reported undefined, never normalised."""
    norm = float(vector.norm())
    if norm < eps:
        return vector, norm, False
    return vector / norm, norm, True


def _transport_chunk(model, spec, metas, batch, res, transport: dict) -> None:
    """[14] MEASUREMENT plus [15] "Candidate A and the requested wire-direction transport", per chunk."""
    import torch
    calls = _calls_by_step(res["calls"])
    if 0 not in calls or 1 not in calls:
        return
    store = res["store"]
    cards = res["cards"]
    state = res["states"][1]                                   # the second scheduled opportunity
    heldout = int(spec.heldout_relation)
    idx = {(int(m["index"]), m["question"]): q for q, m in enumerate(metas)}
    worlds = sorted({int(m["index"]) for m in metas})
    wire = bool(calls[1]["residual"]) and hasattr(model, "rel_query")
    dW = {}
    if wire:
        with torch.no_grad():
            for p in (0, 1):
                tokens = torch.tensor([spec.relation(heldout), spec.relation(p)])
                projected = model.rel_query(model.embed(tokens))
                dW[p] = projected[0] - projected[1]
    for p in (0, 1):
        cell = transport.setdefault(str(p), _new_transport_cell())
        rows, queries, extras = [], {name: [] for name in TRANSPORT_CANDIDATES}, []
        for world in worlds:
            cell["worlds"] += 1
            row_p = idx[(world, f"two_hop_r{p}")]
            row_2 = idx[(world, f"two_hop_r{heldout}")]
            donor_p = idx[(world, f"one_hop_r{p}")]
            donor_2 = idx[(world, f"one_hop_r{heldout}")]
            meta2 = metas[row_2]
            link_line = int(meta2["link_line"])
            # ONLY the matched subset: both native variants fetched the correct LINK at opportunity 1
            if int(cards[row_p, 0]) != link_line or int(cards[row_2, 0]) != link_line:
                cell["unmatched"] += 1
                continue
            u2_p, _n, ok_a = _unit(calls[1]["query"][row_p])
            u2_2, _n, ok_b = _unit(calls[1]["query"][row_2])
            u1_p, _n, ok_c = _unit(calls[0]["query"][donor_p])
            u1_2, _n, ok_d = _unit(calls[0]["query"][donor_2])
            if not (ok_a and ok_b and ok_c and ok_d):
                cell["invalid_transport"] += 1
                continue
            cell["matched"] += 1
            d1, n1, ok1 = _unit(u1_2 - u1_p)
            d2, n2, ok2 = _unit(u2_2 - u2_p)
            cell["d1_norm"].add(n1)
            cell["d2_norm"].add(n2)
            if not ok1:
                cell["undefined_d1"] += 1
            if not ok2:
                cell["undefined_d2"] += 1
            if ok1 and ok2:
                cell["C_cos_d1_d2"].add(float((d1 * d2).sum()))
                cell["R_norm_ratio"].add(n2 / n1)
            transported, tn, ok_t = _unit(u2_p + (u1_2 - u1_p))
            if not ok_t:
                cell["invalid_transport"] += 1
                continue
            row_queries = {"native_u2_heldout": u2_2, "u_transport": transported, "u_donor": u1_2}
            if wire:
                gate_p = float(calls[1]["g"][row_p])
                qW_p = calls[1]["query"][row_p]
                base, _n, _ok = _unit(qW_p)
                wired, _wn, ok_w = _unit(qW_p + gate_p * dW[p])
                cell["dW_norm"].add(float(dW[p].norm()))
                if ok_w:
                    displacement = wired - base
                    cell["wire_displacement_norm"].add(float(displacement.norm()))
                    if ok1 and float(displacement.norm()) >= NEAR_ZERO:
                        unit_disp = displacement / displacement.norm()
                        cell["wire_displacement_cos_d1"].add(float((unit_disp * d1).sum()))
                    row_queries["uW_transport"] = wired
            rows.append(row_2)
            extras.append({"world": world, "meta": meta2,
                           "relation_lines": [int(metas[idx[(world, f"two_hop_r{r}")]]["endpoint_line"])
                                              for r in range(spec.relations)]})
            for name in TRANSPORT_CANDIDATES:
                queries[name].append(row_queries.get(name))
        if not rows:
            continue
        index = torch.tensor(rows, dtype=torch.long)
        native_selection = cards[index, 1]
        ask = state["ask"][index]
        for name in TRANSPORT_CANDIDATES:
            vectors = queries[name]
            if any(v is None for v in vectors):
                continue
            matrix = torch.stack(vectors)
            scores = score_query(model, store, matrix, res["q_visit"][index], res["q_line"][index],
                                 state["fetched"][index], index)
            slot = _transport_candidate(cell, name)
            top1 = scores.argmax(1)
            for j, extra in enumerate(extras):
                meta = extra["meta"]
                endpoint = int(meta["endpoint_line"])
                slot["n"] += 1
                ungated = int(top1[j])
                gated = ungated if bool(ask[j]) else -1
                slot["counts"]["ungated_top1_endpoint" if ungated == endpoint
                               else "ungated_top1_other"] += 1
                slot["counts"]["ask_gated_endpoint" if gated == endpoint
                               else ("ask_gated_no_request" if gated < 0 else "ask_gated_other")] += 1
                row_scores = scores[j].tolist()
                klass = card_class(batch, spec, rows[j],
                                   ungated if ungated < res["store_lines"] else -1, meta,
                                   res["store_lines"]) if ungated < res["store_lines"] else "null_card"
                slot["counts"][f"class_{klass}"] += 1
                margin, eligible = margin_of(row_scores, endpoint)
                if margin is not None:
                    slot["endpoint_margin"].add(margin)
                else:
                    slot["counts"]["endpoint_margin_undefined"] += 1
                if not eligible:
                    slot["counts"]["endpoint_not_eligible"] += 1
                lines = extra["relation_lines"]
                values = [row_scores[line] for line in lines]
                if all(value != float("-inf") for value in values):
                    others = [values[r] for r in range(len(values)) if r != heldout]
                    slot["relation_margin_heldout_vs_practised"].add(values[heldout] - max(others))
                else:
                    slot["counts"]["relation_margin_undefined"] += 1
                if name == "native_u2_heldout":
                    slot["counts"]["matches_native_selection"] += int(gated == int(native_selection[j]))


def transport_report(transport: dict) -> dict:
    out = {}
    for p, cell in sorted(transport.items()):
        block = {"p": int(p), "worlds": cell["worlds"], "matched_subset": cell["matched"],
                 "unmatched_native_link": cell["unmatched"],
                 "invalid_or_near_zero": cell["invalid_transport"],
                 "unconditional_coverage": (round(cell["matched"] / cell["worlds"], 6)
                                            if cell["worlds"] else None),
                 "undefined_d1": cell["undefined_d1"], "undefined_d2": cell["undefined_d2"],
                 "d1_norm": cell["d1_norm"].summary(), "d2_norm": cell["d2_norm"].summary(),
                 "dW_norm": cell["dW_norm"].summary(),
                 "C_cos_d1_d2": cell["C_cos_d1_d2"].summary(),
                 "R_norm_ratio": cell["R_norm_ratio"].summary(),
                 "wire_displacement_norm": cell["wire_displacement_norm"].summary(),
                 "wire_displacement_cos_d1": cell["wire_displacement_cos_d1"].summary(),
                 "candidates": {}}
        for name, slot in sorted(cell["candidates"].items()):
            block["candidates"][name] = {
                "n": slot["n"], "counts": dict(sorted(slot["counts"].items())),
                "endpoint_margin": slot["endpoint_margin"].summary(),
                "relation_margin_heldout_vs_practised":
                    slot["relation_margin_heldout_vs_practised"].summary()}
        out[str(p)] = block
    return out


# ---------------------------------------------------------------------------------- twin-panel scoring
def score_twin_panel(model, panel, spec, rule) -> dict:
    """c4 / c5 under one query rule: both twins must be correct for the pair to count."""
    import torch
    single = {"a": 0, "b": 0}
    joint = 0
    identical = 0
    total = 0
    for chunk in panel["chunks"]:
        metas = chunk["meta"]
        got = {}
        produced = {}
        for side in ("a", "b"):
            batch = H._strip_labels(chunk[side])
            res = replay(model, batch, rule, capture=False)
            got[side] = correctness(res, [m[f"answer_{side}"] for m in metas])
            produced[side] = [res["tokens"][q, :int(res["lengths"][q])].tolist()
                              for q in range(len(metas))]
            single[side] += int(got[side].sum())
        for q in range(len(metas)):
            total += 1
            joint += int(bool(got["a"][q]) and bool(got["b"][q]))
            identical += int(produced["a"][q] == produced["b"][q])
    return {"n": int(panel["n"]), "units": total, "joint_correct": joint,
            "single_correct": single, "identical_answers": identical}


# ------------------------------------------------------------------------------------------- integrity
def observation_parity(model, panel, spec) -> dict:
    """Variant W with the wrapper installed must be bit-identical to the UNWRAPPED model."""
    import torch
    chunk = panel["chunks"][0]
    metas = chunk["meta"]
    batch = H._strip_labels(chunk["a"])
    keys = [m["key_a"] for m in metas]
    with torch.no_grad():
        plain = H.run_condition(model, batch, H.FieldView(batch, spec), CONDITION, keys)
        bare = replay(model, batch, NullRule(), capture=False)
        with QueryRule(model, "W", spec) as rule:
            wrapped = replay(model, batch, rule, capture=True)
    same = (bool(torch.equal(wrapped["tokens"], plain["tokens"]))
            and bool(torch.equal(wrapped["cards"], plain["cards"]))
            and bool(torch.equal(wrapped["fetched"], bare["fetched"]))
            and wrapped["digests"] == plain["digests"] == bare["digests"])
    return {"questions": int(batch.q_visit.shape[0]), "answers_and_cards_identical": bool(
        torch.equal(wrapped["tokens"], plain["tokens"]) and torch.equal(wrapped["cards"], plain["cards"])),
        "scores_identical": wrapped["digests"] == plain["digests"],
        "unwrapped_reference": "premonition_handoff_diag.run_condition(..., 'U')",
        "pass": bool(same)}


def recall_excluded(model, panel, spec) -> dict:
    """A diagnostic `_recall` must never enter the telemetry."""
    import torch
    chunk = panel["chunks"][0]
    batch = H._strip_labels(chunk["a"])
    with torch.no_grad(), QueryRule(model, "W", spec) as rule:
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        mentions = model._mentions(batch)
        episode = model._start(batch, hidden, store, mentions)
        everyone = torch.arange(batch.q_visit.shape[0])
        rule.begin_step(0)
        rows, _halt, _ask, _scores = model._step(episode, everyone, 0, store)
        before = len(rule.calls)
        gold, _told, _missing = store.gold(chunk["a"].gold_lines, batch.q_visit, batch.q_line)
        model._recall(store, episode, everyone, rows, gold)
        after = len(rule.calls)
    return {"telemetry_calls_before_recall": before, "after_recall": after,
            "pass": bool(before == after and before == 1)}


def label_perturbation(model, panel, spec, variants) -> dict:
    """Perturbing the evaluator's labels must change nothing the model sees, under every variant."""
    import torch
    from dataclasses import replace as dc_replace
    chunk = panel["chunks"][0]
    batch = chunk["a"]
    blind = H._strip_labels(batch)
    noisy = H._strip_labels(dc_replace(
        batch, answer=torch.full_like(batch.answer, 7), gold_lines=torch.zeros_like(batch.gold_lines),
        depth=torch.full_like(batch.depth, 3),
        question_ids=[f"perturbed-{i}" for i in range(batch.q_visit.shape[0])],
        slices={"bogus": torch.ones(batch.q_visit.shape[0], dtype=torch.bool)}))
    same = True
    with torch.no_grad():
        for variant in variants:
            with QueryRule(model, variant, spec) as rule:
                a = replay(model, blind, rule, capture=False)
            with QueryRule(model, variant, spec) as rule:
                b = replay(model, noisy, rule, capture=False)
            same &= bool(torch.equal(a["tokens"], b["tokens"]))
            same &= bool(torch.equal(a["cards"], b["cards"]))
            same &= a["digests"] == b["digests"]
    return {"variants": list(variants), "identical": bool(same), "pass": bool(same),
            "design": "the model is only ever handed premonition_handoff_diag._strip_labels(batch)"}


def episode_isolation(model, panel, spec, variant: str, *, sample: int = 4) -> dict:
    """Scoring one world's question alone must give the same answer and the same fetches."""
    import torch
    chunk = panel["chunks"][0]
    metas = chunk["meta"]
    blind = H._strip_labels(chunk["a"])
    same = total = 0
    with torch.no_grad():
        with QueryRule(model, variant, spec) as rule:
            full = replay(model, blind, rule, capture=False)
        for q in range(min(sample, len(metas))):
            alone = PS._single_visit(blind, int(blind.q_visit[q]), q)
            with QueryRule(model, variant, spec) as rule:
                part = replay(model, alone, rule, capture=False)
            total += 1
            same += int(full["tokens"][q].tolist() == part["tokens"][0].tolist()
                        and full["cards"][q].tolist() == part["cards"][0].tolist())
    return {"worlds": total, "identical": same, "variant": variant, "pass": bool(same == total)}


# --------------------------------------------------------------------------------- one frozen checkpoint
def reuse_key(checkpoint_sha: str, manifest_sha: str, variants) -> dict:
    return {"checkpoint_sha256": checkpoint_sha, "panel_manifest_sha256": manifest_sha,
            "script_sha256": sha256_file(SOURCE), "variants": list(variants),
            "evaluator_version": EVALUATOR_VERSION}


def run_checkpoint(path: Path, folder: Path, manifest: dict, spec) -> dict:
    """Every panel and every instrument for one frozen checkpoint.  -> one JSON row."""
    import torch
    path = Path(path)
    name = path.stem
    started = time.perf_counter()
    digest = sha256_file(path)
    model, blob = P.load_from(name, path.parent)
    model.eval()
    before = P.fingerprint(model)
    wire = bool(blob.get("relation_shortcut")) or hasattr(model, "_shortcut_query")
    variants = list(VARIANTS) if wire else ["W"]
    manifest_sha = sha256_file(folder / "manifest.json")
    matched = load_panel("matched", folder, manifest)
    telemetry, intervention, transport = Telemetry(), Intervention(), {}
    variant_stats, twins = {}, {}
    with torch.no_grad():
        for variant in variants:
            stats = VariantStats()
            first = variant == "W"
            with QueryRule(model, variant, spec) as rule:
                score_matched_variant(
                    model, matched, spec, rule, stats, capture=first,
                    telemetry=telemetry if first else None,
                    intervention=(intervention if (first and wire) else None),
                    transport=transport if first else None)
            variant_stats[variant] = stats.report()
        for panel_name in ("c4", "c5"):
            panel = load_panel(panel_name, folder, manifest)
            twins[panel_name] = {}
            for variant in variants:
                with QueryRule(model, variant, spec) as rule:
                    twins[panel_name][variant] = score_twin_panel(model, panel, spec, rule)
        integrity = {
            "observation_only_parity": observation_parity(model, matched, spec),
            "recall_excluded_from_telemetry": recall_excluded(model, matched, spec),
            "label_perturbation": label_perturbation(model, matched, spec, variants),
            "episode_isolation": episode_isolation(model, matched, spec, variants[-1]),
            "own_fixed_parity": PS.own_fixed_parity(model, matched, spec)}
    after = P.fingerprint(model)
    integrity["weights_fingerprint_before"] = before
    integrity["weights_fingerprint_after"] = after
    integrity["weights_unchanged"] = bool(before == after)
    integrity["source_hashes"] = source_hashes()
    integrity["panel_manifest_sha256"] = manifest_sha
    integrity["panel_content_sha256"] = manifest.get("panel_content_sha256")
    integrity["all_pass"] = bool(
        integrity["weights_unchanged"] and integrity["observation_only_parity"]["pass"]
        and integrity["recall_excluded_from_telemetry"]["pass"]
        and integrity["label_perturbation"]["pass"] and integrity["episode_isolation"]["pass"]
        and integrity["own_fixed_parity"]["pass"])
    if not integrity["weights_unchanged"]:
        raise SystemExit(f"{name}: parameters changed during evaluation -- aborting")
    seed = None
    if "-s" in name:
        try:
            seed = int(name.split("-s")[1].split("-")[0])
        except (IndexError, ValueError):
            seed = None
    return {"evaluator_version": EVALUATOR_VERSION, "ckpt": str(path.resolve()),
            "dir": str(path.parent.resolve()), "name": name, "sha256": digest, "seed": seed,
            "train_seed": blob.get("seed"), "wire": wire, "variants": variants,
            "model_class": blob.get("model_class"), "key_pool": bool(blob.get("key_pool")),
            "parameters": int(sum(p.numel() for p in model.parameters())),
            "worlds": int(manifest["worlds"]), "full_size": bool(manifest.get("full_size")),
            "reuse_key": reuse_key(digest, manifest_sha, variants),
            "telemetry": telemetry.report(), "cached_state_intervention": intervention.report(),
            "variant_replays": variant_stats, "twins": twins,
            "transport": transport_report(transport),
            "integrity": integrity, "not_a_claim": NOT_A_CLAIM,
            "seconds": round(time.perf_counter() - started, 2)}


# ------------------------------------------------------------------------------------- run sub-command
_G: dict = {}


def _init_worker(payload: str) -> None:
    L.bootstrap()
    import torch
    torch.set_num_threads(1)
    info = json.loads(payload)
    _G["folder"] = Path(info["folder"])
    _G["manifest"] = info["manifest"]
    _G["spec"] = L.spec()


def _work(path_str: str) -> dict:
    try:
        return run_checkpoint(Path(path_str), _G["folder"], _G["manifest"], _G["spec"])
    except Exception as error:                                   # noqa: BLE001 - reported, never silent
        return {"ckpt": str(Path(path_str).resolve()), "name": Path(path_str).stem,
                "error": f"{type(error).__name__}: {error}"}


def finished_rows(rows_path: Path, key: dict) -> dict:
    """{ckpt path: row} for rows already written under an IDENTICAL reuse key."""
    if not rows_path.exists():
        return {}
    out = {}
    for line in rows_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "error" in row:
            continue
        old = row.get("reuse_key")
        if isinstance(old, dict) and all(old.get(k) == v for k, v in key.items()):
            out[row["ckpt"]] = row
    return out


def cmd_run(args) -> None:
    root = guard_output(args.root)
    folder = Path(args.panels).expanduser() if args.panels else root / "panels"
    if not (folder / "manifest.json").exists():
        raise SystemExit(f"no panel manifest at {folder / 'manifest.json'}; run `panels` first")
    manifest = read_json(folder / "manifest.json")
    manifest_sha = sha256_file(folder / "manifest.json")
    root.mkdir(parents=True, exist_ok=True)
    rows_path = root / "rows.jsonl"
    wanted = []
    for raw in args.ckpt_dir:
        directory = Path(raw).expanduser()
        if not directory.is_absolute():
            directory = L.ROOT / directory
        if not directory.exists():
            print(f"missing checkpoint directory, skipped: {directory}")
            continue
        found = sorted(directory.glob("*.pt"))
        if not found:
            print(f"no *.pt in {directory}, skipped")
            continue
        wanted.extend(found)
    if not wanted:
        print("nothing to replay")
        return
    todo = []
    skipped = 0
    for path in wanted:
        digest = sha256_file(path)
        variants = list(VARIANTS)                     # the widest key; a plain row records ["W"]
        keys = [reuse_key(digest, manifest_sha, variants), reuse_key(digest, manifest_sha, ["W"])]
        if any(finished_rows(rows_path, key).get(str(path.resolve())) for key in keys):
            skipped += 1
            continue
        todo.append(path)
    print(f"{len(wanted)} checkpoints found, {skipped} already complete under this reuse key, "
          f"{len(todo)} to do")
    if args.limit:
        todo = todo[:args.limit]
        print(f"--limit {args.limit}: replaying {len(todo)}")
    if not todo:
        return
    payload = json.dumps({"folder": str(folder), "manifest": manifest})
    workers = max(1, int(args.workers))
    started = time.perf_counter()
    completed = 0

    def record(row: dict) -> None:
        with rows_path.open("a") as handle:
            handle.write(json.dumps(row, default=str) + "\n")
        if "error" in row:
            print(f"{row['name']:26s} ERROR {row['error']}", flush=True)
            return
        held = row["variant_replays"]["W"]["answers"]
        print(f"{row['name']:26s} wire={row['wire']}  variants={','.join(row['variants'])}  "
              f"heldout W {held.get('two_hop_heldout_correct')}/{held.get('two_hop_heldout_n')}  "
              f"integrity={row['integrity']['all_pass']}  {row['seconds']:.1f}s", flush=True)

    if workers == 1:
        _init_worker(payload)
        for path in todo:
            record(_work(str(path)))
            completed += 1
            rate = (time.perf_counter() - started) / completed
            print(f"  [{completed}/{len(todo)}] {rate:.1f}s per checkpoint, "
                  f"{rate * (len(todo) - completed) / 60:.1f} min left", flush=True)
    else:
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=workers, initializer=_init_worker, initargs=(payload,)) as pool:
            for row in pool.imap_unordered(_work, [str(p) for p in todo]):
                record(row)
                completed += 1
                rate = (time.perf_counter() - started) / completed
                print(f"  [{completed}/{len(todo)}] {rate:.1f}s per checkpoint wall-clock, "
                      f"{rate * (len(todo) - completed) / 60:.1f} min left", flush=True)
    print(f"\nreplayed {completed} checkpoints in {time.perf_counter() - started:.1f}s with "
          f"{workers} worker(s); rows appended to {rows_path}")


# ----------------------------------------------------------------------------------- table sub-command
FOUR_CELLS = ("one_hop_r2", "heldout_native", "c4_joint", "c5_joint")
LOSS_LIMIT = 5                       # at most 5/256 in each cell, relative to the stated control
FIRST_LINK_MARK = 244                # >= 244/256 first-LINK in seeds 14 and 30
ANSWER_GAIN_MARK = 0.20              # >= 20 percentage points held-out native answer gain
GUARD_SEEDS = (14, 30)               # the two learned-but-G_pair-failing wire runs
ENDPOINT_STATE_FLOOR = 128           # the correct-LINK-conditioned screen needs >= 128 such states
A_FIRST_SEEDS = 22                   # at least 22 of the 33 fresh-learned plain seeds
A_FIRST_WORLDS = 128
FRESH_LEARNED = 1536                 # c1 >= 1536/2048 on the historical suite
EXPECTED_SEEDS = 40                  # the complete wire / plain shared-pooling rosters


def historical_strata(suite_rows: Path) -> dict:
    """The named descriptive strata, read (read-only) from the historical pair-suite rows."""
    wire, plain = {}, {}
    if not Path(suite_rows).exists():
        return {"available": False, "wire_g_passers": [], "wire_fresh_learned": [],
                "plain_fresh_learned": [], "note": f"missing {suite_rows}"}
    for line in Path(suite_rows).read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "error" in row or "counts" not in row:
            continue
        target = wire if row.get("dir") == str(WIRE_CKPT_DIR) else (
            plain if row.get("dir") == str(PLAIN_CKPT_DIR) else None)
        if target is None:
            continue
        target[row["name"]] = row
    def seeds(table, predicate):
        out = []
        for name, row in table.items():
            if not predicate(row):
                continue
            try:
                out.append(int(name.split("-s")[1].split("-")[0]))
            except (IndexError, ValueError):
                continue
        return sorted(out)
    return {"available": True, "source": str(suite_rows),
            "wire_g_passers": seeds(wire, lambda r: bool(r.get("G"))),
            "wire_fresh_learned": seeds(wire, lambda r: r["counts"]["c1_own_one_hop"] >= FRESH_LEARNED),
            "plain_fresh_learned": seeds(plain, lambda r: r["counts"]["c1_own_one_hop"] >= FRESH_LEARNED),
            "definitions": {"G passer": "historical pair-suite G == true on the wire control roster",
                            "fresh-learned": f"historical c1_own_one_hop >= {FRESH_LEARNED}/2048"}}


def variant_cells(row: dict, variant: str):
    """The four no-harm cells plus the guard/endpoint counters for one variant of one checkpoint."""
    block = row.get("variant_replays", {}).get(variant)
    if block is None:
        return None
    answers = block["answers"]
    link = block["first_request_correct_link"]
    endpoint = block["endpoint_given_correct_link"]
    twins = row.get("twins", {})
    return {
        "one_hop_r2": answers.get("one_hop_r2_correct"),
        "heldout_native": answers.get("two_hop_heldout_correct"),
        "c4_joint": (twins.get("c4", {}).get(variant) or {}).get("joint_correct"),
        "c5_joint": (twins.get("c5", {}).get(variant) or {}).get("joint_correct"),
        "first_link_heldout": link.get("two_hop_heldout_correct_link"),
        "endpoint_given_link": endpoint.get("two_hop_heldout_endpoint_at_request2"),
        "endpoint_given_link_denominator": endpoint.get("two_hop_heldout_denominator"),
        "applied_ratio_when_h1": block.get("applied_ratio_when_h1", {}),
    }


def _losses(base, treatment) -> dict:
    out = {}
    for cell in FOUR_CELLS:
        a, b = base.get(cell), treatment.get(cell)
        out[cell] = None if (a is None or b is None) else int(a) - int(b)
    return out


def _screen(rows_by_seed: dict, passers: list, base_variant: str, treatment: str, worlds: int,
            expected: int = EXPECTED_SEEDS) -> dict:
    """The relative no-harm screen: every passer <= LOSS_LIMIT per cell, and the all-seed mean too."""
    per_seed, missing = {}, []
    for seed, row in sorted(rows_by_seed.items()):
        base, treat = variant_cells(row, base_variant), variant_cells(row, treatment)
        if base is None or treat is None:
            missing.append(seed)
            continue
        per_seed[seed] = _losses(base, treat)
    usable = {s: v for s, v in per_seed.items() if all(x is not None for x in v.values())}
    mean = {cell: (round(sum(v[cell] for v in usable.values()) / len(usable), 4) if usable else None)
            for cell in FOUR_CELLS}
    passer_fail = {}
    for seed in passers:
        if seed not in usable:
            passer_fail[seed] = "missing"
            continue
        bad = {c: usable[seed][c] for c in FOUR_CELLS if usable[seed][c] > LOSS_LIMIT}
        if bad:
            passer_fail[seed] = bad
    mean_fail = {c: mean[c] for c in FOUR_CELLS if mean[c] is not None and mean[c] > LOSS_LIMIT}
    complete = (not missing and len(usable) == len(rows_by_seed) and len(usable) >= int(expected)
                and bool(passers) and all(seed in usable for seed in passers) and worlds == WORLDS)
    verdict = ("INCONCLUSIVE" if not complete else
               ("PASS" if not passer_fail and not mean_fail else "FAIL"))
    return {"base": base_variant, "treatment": treatment, "limit_per_cell": LOSS_LIMIT,
            "per_seed_loss": per_seed, "mean_loss_all_seeds": mean, "seeds_used": len(usable),
            "missing_seeds": missing, "passer_failures": passer_fail, "mean_failures": mean_fail,
            "complete": bool(complete), "verdict": verdict}


def guard_signal(rows_by_seed: dict, worlds: int) -> dict:
    out = {"mark_first_link": FIRST_LINK_MARK, "mark_answer_gain_points": ANSWER_GAIN_MARK * 100,
           "seeds": {}}
    verdicts = []
    for seed in GUARD_SEEDS:
        row = rows_by_seed.get(seed)
        if row is None:
            out["seeds"][seed] = {"verdict": "INCONCLUSIVE", "reason": "no row for this seed"}
            verdicts.append("INCONCLUSIVE")
            continue
        base, treat = variant_cells(row, "W"), variant_cells(row, "WG")
        if base is None or treat is None or worlds != WORLDS:
            out["seeds"][seed] = {"verdict": "INCONCLUSIVE",
                                  "reason": "missing variant or panel is not full size"}
            verdicts.append("INCONCLUSIVE")
            continue
        first_link = treat["first_link_heldout"]
        gain = (int(treat["heldout_native"]) - int(base["heldout_native"])) / worlds
        ok = bool(first_link is not None and first_link >= FIRST_LINK_MARK and gain >= ANSWER_GAIN_MARK)
        out["seeds"][seed] = {
            "WG_first_link_heldout": first_link, "W_first_link_heldout": base["first_link_heldout"],
            "W_heldout_native": base["heldout_native"], "WG_heldout_native": treat["heldout_native"],
            "answer_gain_points": round(gain * 100, 4),
            "verdict": "PASS" if ok else "FAIL"}
        verdicts.append("PASS" if ok else "FAIL")
    out["verdict"] = ("INCONCLUSIVE" if "INCONCLUSIVE" in verdicts else
                      ("PASS" if all(v == "PASS" for v in verdicts) else "FAIL"))
    out["rule"] = (f"separately in wire seeds {list(GUARD_SEEDS)}: WG first-LINK >= "
                   f"{FIRST_LINK_MARK}/{WORLDS} AND held-out native answer gain >= "
                   f"{ANSWER_GAIN_MARK * 100:.0f} points versus W")
    return out


def eta_decision(rows_by_seed: dict, passers: list, worlds: int) -> dict:
    """[15] Attack 2's eligibility rule relative to UNCAPPED WG, then the four-row decision table."""
    out = {"rule": "eligibility is relative to uncapped WG; the grid is exactly {0.25, 0.50}",
           "caps": {}}
    for variant, eta in (("WGC25", 0.25), ("WGC50", 0.50)):
        screen = _screen(rows_by_seed, passers, "WG", variant, worlds)
        endpoint = {}
        for seed in passers:
            row = rows_by_seed.get(seed)
            if row is None:
                endpoint[seed] = "missing"
                continue
            base, treat = variant_cells(row, "WG"), variant_cells(row, variant)
            if base is None or treat is None:
                endpoint[seed] = "missing"
                continue
            states = base.get("endpoint_given_link_denominator")
            if states is None or states < ENDPOINT_STATE_FLOOR:
                endpoint[seed] = {"states": states, "screened": False}
                continue
            loss = int(base["endpoint_given_link"]) - int(treat["endpoint_given_link"])
            endpoint[seed] = {"states": states, "screened": True, "loss": loss,
                              "ok": bool(loss <= LOSS_LIMIT)}
        endpoint_fail = {s: v for s, v in endpoint.items()
                         if v == "missing" or (isinstance(v, dict) and v.get("screened")
                                               and not v.get("ok"))}
        verdict = ("INCONCLUSIVE" if screen["verdict"] == "INCONCLUSIVE" else
                   ("ELIGIBLE" if screen["verdict"] == "PASS" and not endpoint_fail else "NOT_ELIGIBLE"))
        out["caps"][variant] = {"eta": eta, "no_harm_screen": screen,
                                "correct_link_conditioned_endpoint": endpoint,
                                "endpoint_failures": endpoint_fail, "verdict": verdict}
    ratios = []
    for row in rows_by_seed.values():
        block = (row.get("variant_replays", {}).get("WG") or {}).get("applied_ratio_when_h1") or {}
        if block.get("n"):
            ratios.append(block["max"])
    all_within = bool(ratios) and max(ratios) <= 0.25
    e25 = out["caps"]["WGC25"]["verdict"]
    e50 = out["caps"]["WGC50"]["verdict"]
    if "INCONCLUSIVE" in (e25, e50) or not ratios:
        chosen, reason, rowid = None, "invalid or incomplete measurement", "row 4 (inconclusive)"
        decision = "INCONCLUSIVE"
    elif all_within and e25 == "ELIGIBLE":
        chosen, rowid, decision = 0.25, "row 1", "PASS"
        reason = "all applied ratios on relevant WG states are <= .25 and .25 is eligible; clipping is " \
                 "inactive there -- the numerical boundary is checked explicitly below"
    elif e25 == "ELIGIBLE":
        chosen, rowid, decision = 0.25, "row 2", "PASS"
        reason = "some ratios exceed .25 but .25 is eligible; a large dose was not necessary for the " \
                 "measured outputs"
    elif e50 == "ELIGIBLE":
        chosen, rowid, decision = 0.50, "row 3", "PASS"
        reason = "0.25 failed and 0.50 is eligible, explicitly relinquishing the .25 geometric bound"
    else:
        chosen, rowid, decision = None, "row 4", "FAIL"
        reason = "neither cap qualifies: no cap is selected; defer WGC and original B"
    out["max_applied_ratio_over_seeds"] = (max(ratios) if ratios else None)
    out["all_applied_ratios_within_0.25"] = all_within
    out["boundary_at_exactly_0.25"] = sum(
        1 for row in rows_by_seed.values()
        for block in [(row.get("variant_replays", {}).get("WG") or {}).get("applied_ratio_when_h1") or {}]
        if block.get("n") and block.get("max") == 0.25)
    out["decision_row"] = rowid
    out["chosen_eta"] = chosen if chosen is not None else (
        "no cap selected" if decision == "FAIL" else None)
    out["reason"] = reason
    out["verdict"] = decision
    return out


def plain_measurement_flags(plain_rows: dict, fresh_learned: list) -> dict:
    """[14] MEASUREMENT interpretation flags for the plain d1 donor/transport assay."""
    per_seed, tally = {}, Counter()
    for seed, row in sorted(plain_rows.items()):
        transport = row.get("transport") or {}
        entry = {"in_fresh_learned_stratum": seed in fresh_learned, "p": {}}
        donor_ok, cov_ok, contrast_ok, transport_ok, decoy_ok, weak_native = True, True, True, True, True, True
        for p in ("0", "1"):
            cell = transport.get(p)
            if cell is None:
                entry["p"][p] = {"available": False}
                donor_ok = cov_ok = contrast_ok = transport_ok = decoy_ok = False
                weak_native = False
                continue
            n = cell["matched_subset"]
            cands = cell["candidates"]
            def rate(name, key):
                block = cands.get(name)
                if not block or not block["n"]:
                    return None
                return block["counts"].get(key, 0) / block["n"]
            donor = rate("u_donor", "ungated_top1_endpoint")
            native_gated = rate("native_u2_heldout", "ask_gated_endpoint")
            transported = rate("u_transport", "ask_gated_endpoint")
            decoy_native = rate("native_u2_heldout", "class_asker_same_rel")
            decoy_transport = rate("u_transport", "class_asker_same_rel")
            median_c = (cell["C_cos_d1_d2"] or {}).get("median")
            median_r = (cell["R_norm_ratio"] or {}).get("median")
            gain = None if (native_gated is None or transported is None) else transported - native_gated
            rise = None if (decoy_native is None or decoy_transport is None) else \
                decoy_transport - decoy_native
            entry["p"][p] = {"available": True, "matched_subset": n,
                             "coverage": cell["unconditional_coverage"],
                             "donor_endpoint_top1": None if donor is None else round(donor, 6),
                             "native_ask_gated_endpoint": None if native_gated is None
                             else round(native_gated, 6),
                             "transport_ask_gated_endpoint": None if transported is None
                             else round(transported, 6),
                             "transport_gain_points": None if gain is None else round(gain * 100, 4),
                             "asker_decoy_rise_points": None if rise is None else round(rise * 100, 4),
                             "median_C": median_c, "median_R": median_r}
            cov_ok &= bool(n >= A_FIRST_WORLDS)
            donor_ok &= bool(donor is not None and donor >= 0.95)
            contrast_ok &= bool(median_c is not None and median_c >= 0.9
                                and median_r is not None and 0.5 <= median_r <= 2.0)
            transport_ok &= bool(gain is not None and gain >= 0.20)
            decoy_ok &= bool(rise is not None and rise <= 0.02)
            weak_native &= bool(median_r is not None and median_r < 0.25
                                or (median_c is not None and median_c <= 0))
        if seed in fresh_learned:
            if cov_ok and donor_ok and contrast_ok and transport_ok and decoy_ok:
                entry["flag"] = "A_first"
            elif donor_ok and weak_native:
                entry["flag"] = "keep_B"
            elif not donor_ok or (donor_ok and not transport_ok and not weak_native):
                entry["flag"] = "neither"
            else:
                entry["flag"] = "inconclusive"
            tally[entry["flag"]] += 1
        else:
            entry["flag"] = "outside_the_fresh_learned_stratum"
        per_seed[seed] = entry
    overall = "INCONCLUSIVE"
    if tally["A_first"] >= A_FIRST_SEEDS:
        overall = "A_FIRST"
    elif tally["keep_B"] >= A_FIRST_SEEDS:
        overall = "KEEP_B"
    elif tally["neither"] >= A_FIRST_SEEDS:
        overall = "SUPPORT_NEITHER_YET"
    return {"rule": f"[14] MEASUREMENT: at least {A_FIRST_SEEDS} of the fresh-learned plain seeds, each "
                    f"with >= {A_FIRST_WORLDS} matched worlds for BOTH p values",
            "fresh_learned_seeds": fresh_learned, "tally": dict(sorted(tally.items())),
            "per_seed": per_seed, "flag": overall}


def cmd_table(args) -> None:
    root = Path(args.root).expanduser().resolve()
    out_dir = guard_output(args.out) if args.out else guard_output(root / "summary")
    rows_path = root / "rows.jsonl"
    if not rows_path.exists():
        raise SystemExit(f"no rows at {rows_path}; run `run` first")
    rows, errors = {}, []
    for line in rows_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "error" in row:
            errors.append({"name": row.get("name"), "error": row["error"]})
            continue
        rows[row["ckpt"]] = row                       # the last complete row for a checkpoint wins
    wire_rows, plain_rows, other = {}, {}, {}
    for row in rows.values():
        seed = row.get("seed")
        target = wire_rows if row.get("wire") else plain_rows
        if seed is None:
            other[row["name"]] = row
            continue
        target[seed] = row
    worlds = min([row["worlds"] for row in rows.values()], default=0)
    full_size = all(bool(row.get("full_size")) for row in rows.values()) and worlds == WORLDS
    integrity_ok = all(row["integrity"]["all_pass"] for row in rows.values())
    strata = historical_strata(HISTORICAL_SUITE / "rows.jsonl")
    # the FULL expected passer roster: a missing passer makes every screen inconclusive, never a pass
    passers = list(strata["wire_g_passers"])
    report = {
        "evaluator_version": EVALUATOR_VERSION, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": str(root), "not_a_claim": NOT_A_CLAIM, "skipped": SKIPPED,
        "rows": {"wire": len(wire_rows), "plain": len(plain_rows), "unattributed": len(other),
                 "errors": errors},
        "worlds_per_panel": worlds, "full_size_panels": bool(full_size),
        "all_integrity_checks_passed": bool(integrity_ok),
        "strata": strata,
        "expected_seeds_per_roster": EXPECTED_SEEDS,
        "strata_present": {"wire_G_passers_with_rows": [s for s in passers if s in wire_rows],
                           "wire_G_passers_expected": strata["wire_g_passers"],
                           "wire_seeds_with_rows": sorted(wire_rows),
                           "plain_seeds_with_rows": sorted(plain_rows)},
        "guard_mechanism_signal": guard_signal(wire_rows, worlds),
        "no_harm_WG_vs_W": _screen(wire_rows, passers, "W", "WG", worlds),
        "eta_decision": eta_decision(wire_rows, passers, worlds),
        "plain_d1_assay": plain_measurement_flags(
            plain_rows, [s for s in strata["plain_fresh_learned"] if s in plain_rows]),
        "per_seed_counts": {
            "wire": {seed: {v: variant_cells(row, v) for v in row["variants"]}
                     for seed, row in sorted(wire_rows.items())},
            "plain": {seed: {v: variant_cells(row, v) for v in row["variants"]}
                      for seed, row in sorted(plain_rows.items())}},
    }
    if not (full_size and integrity_ok):
        for key in ("guard_mechanism_signal", "no_harm_WG_vs_W"):
            report[key]["verdict"] = "INCONCLUSIVE"
            report[key]["inconclusive_reason"] = ("panels are not full size" if not full_size
                                                  else "an integrity check failed")
        report["eta_decision"]["verdict"] = "INCONCLUSIVE"
        report["eta_decision"]["chosen_eta"] = None
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(report, indent=1, default=str))
    text = render_table(report)
    (out_dir / "summary.txt").write_text(text + "\n")
    print(text)
    print(f"\nwrote {out_dir / 'summary.json'} and {out_dir / 'summary.txt'}")


def render_table(report: dict) -> str:
    lines = ["premonition wire-replay summary", "=" * 78,
             f"THIS IS A {NOT_A_CLAIM.upper()}", "",
             f"rows: {report['rows']['wire']} wire, {report['rows']['plain']} plain, "
             f"{len(report['rows']['errors'])} errors; worlds per panel "
             f"{report['worlds_per_panel']}; full size {report['full_size_panels']}; "
             f"integrity all pass {report['all_integrity_checks_passed']}",
             f"strata: wire G passers {report['strata']['wire_g_passers']}",
             f"        wire fresh-learned {report['strata']['wire_fresh_learned']}",
             f"        plain fresh-learned {report['strata']['plain_fresh_learned']}", ""]
    guard = report["guard_mechanism_signal"]
    lines += [f"1. guard mechanism signal  -> {guard['verdict']}", f"   {guard['rule']}"]
    for seed, block in guard["seeds"].items():
        if "reason" in block:
            lines.append(f"   seed {seed}: {block['verdict']} ({block['reason']})")
        else:
            lines.append(f"   seed {seed}: {block['verdict']}  WG first-LINK "
                         f"{block['WG_first_link_heldout']} (W {block['W_first_link_heldout']})  "
                         f"held-out native W {block['W_heldout_native']} -> WG "
                         f"{block['WG_heldout_native']}  gain {block['answer_gain_points']} points")
    screen = report["no_harm_WG_vs_W"]
    lines += ["", f"2. no-harm screen, WG versus W  -> {screen['verdict']}",
              f"   every historical G passer and the all-seed mean lose at most {LOSS_LIMIT}/"
              f"{report['worlds_per_panel']} in each of {', '.join(FOUR_CELLS)}",
              f"   mean loss over all seeds: {screen['mean_loss_all_seeds']}",
              f"   passer failures: {screen['passer_failures'] or 'none'}",
              f"   mean failures:   {screen['mean_failures'] or 'none'}",
              "   per-seed loss (W - WG), every seed reported:"]
    for seed, loss in sorted(screen["per_seed_loss"].items()):
        lines.append(f"     seed {seed:>3}: " + "  ".join(f"{c}={loss[c]}" for c in FOUR_CELLS))
    eta = report["eta_decision"]
    lines += ["", f"3. eta decision  -> {eta['verdict']}  chosen eta: {eta['chosen_eta']}",
              f"   {eta['decision_row']}: {eta['reason']}",
              f"   max applied ratio on relevant WG states: {eta['max_applied_ratio_over_seeds']}  "
              f"(all within .25: {eta['all_applied_ratios_within_0.25']}; exactly-.25 boundary rows: "
              f"{eta['boundary_at_exactly_0.25']})"]
    for variant, block in eta["caps"].items():
        lines.append(f"   {variant} (eta {block['eta']}): {block['verdict']}   "
                     f"no-harm {block['no_harm_screen']['verdict']}, mean loss "
                     f"{block['no_harm_screen']['mean_loss_all_seeds']}, endpoint failures "
                     f"{block['endpoint_failures'] or 'none'}")
    plain = report["plain_d1_assay"]
    lines += ["", f"4. plain d1 donor/transport assay  -> {plain['flag']}", f"   {plain['rule']}",
              f"   tally over the fresh-learned stratum: {plain['tally']}",
              "   per-seed (p=0 / p=1): matched, donor top-1, median C, median R, transport gain pp, "
              "decoy rise pp"]
    for seed, entry in sorted(plain["per_seed"].items()):
        parts = []
        for p in ("0", "1"):
            cell = entry["p"].get(p, {})
            if not cell.get("available"):
                parts.append(f"p{p}: n/a")
                continue
            parts.append(f"p{p}: {cell['matched_subset']}, {cell['donor_endpoint_top1']}, "
                         f"{cell['median_C']}, {cell['median_R']}, {cell['transport_gain_points']}, "
                         f"{cell['asker_decoy_rise_points']}")
        lines.append(f"     seed {seed:>3} [{entry['flag']}]  " + " | ".join(parts))
    lines += ["", "every seed above is reported; nothing is dropped.  Low coverage, an invalid "
                  "denominator or a failed integrity check is INCONCLUSIVE, never a pass."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------- main
def cmd_panels(args) -> None:
    generate_panels(args.out, worlds=int(args.worlds))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    panels = sub.add_parser("panels", help="build the three manifest-fixed panels (no model is loaded)")
    panels.add_argument("--out", required=True)
    panels.add_argument("--worlds", type=int, default=WORLDS)
    run = sub.add_parser("run", help="replay every *.pt of the given directories under every variant")
    run.add_argument("--ckpt-dir", action="append", required=True)
    run.add_argument("--root", required=True)
    run.add_argument("--panels", default=None, help="panel directory (default: ROOT/panels)")
    run.add_argument("--workers", type=int, default=1)
    run.add_argument("--limit", type=int, default=0)
    table = sub.add_parser("table", help="apply the pre-fixed decision rules to the written rows")
    table.add_argument("--root", required=True)
    table.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    if args.cmd == "table":                       # stdlib only: no torch, no frozen package, no model
        cmd_table(args)
        return 0
    L.bootstrap()
    import torch
    torch.set_num_threads(1 if args.cmd == "run" else 2)
    {"panels": cmd_panels, "run": cmd_run}[args.cmd](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
