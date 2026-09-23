"""D0/D1 handoff diagnostic (Claude, 2026-09-19) -- READ-ONLY, eval-only, frozen checkpoints.

Implements reviews/premonition-discovery-2026-09-19/protocol.md sections D0, D1 and the D2 seal, on fresh paired
worlds from the frozen toy-ladder family. No training, no fitted probes, no GPU, no network. Nothing outside
artifacts/claude-handoff-20260919/ is written.

Question: given the SAME first retrieved card, does using its visible destination as the next source fix answers
that the latent workspace gets wrong?  Primary contrast QD - Q on both-correct pair accuracy.

Conditions (eligibility masks only; scores of non-permitted REAL cards go to -inf, NULL always stays eligible):
  U   native fixed_K4 (premonition_ovn_retrieval.own_fixed(..., loops=4))
  Q   request 1 only: real fact cards whose parsed subject == the question subject
  D   request 2 only, only if the question shows LINK and the card ACTUALLY fetched first is a link card with a
      valid entity object: real fact cards whose parsed subject == that object
  QD  Q at request 1, D at request 2
  QW  Q, then the same request-2 gate on a different in-world entity (fixed hash of the neutral world index,
      excluding the selected destination)
  N   the same instrumentation with an all-eligible extra mask; must equal U exactly

    PY -B scripts/premonition_handoff_diag.py gen       # seeds + worlds + manifest (no model is loaded)
    PY -B scripts/premonition_handoff_diag.py d0
    PY -B scripts/premonition_handoff_diag.py d1
    PY -B scripts/premonition_handoff_diag.py d2 --confirm      # refuses unless D1 advanced
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace as dc_replace
import hashlib
import json
from pathlib import Path
import random
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_first_card_probe as P  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

OUT = L.ROOT / "artifacts" / "claude-handoff-20260919"
DATA = OUT / "data"
SOURCE = Path(__file__).resolve()

LOOPS = 4
REQUESTS = LOOPS - 1
WORLDS_PER_CHUNK = 16
CONDITIONS = ("U", "Q", "D", "QD", "QW", "N")
ONE_HOP_CONDITIONS = ("U", "Q", "QD", "N")

# Seeds fixed BEFORE any model is loaded; distinct per set.  Recorded in manifest.json.
SETS = {
    "dev":    {"seed": 20260919_0001, "pairs": 32,  "hops": 2, "edit": "link"},
    "d1":     {"seed": 20260919_0002, "pairs": 512, "hops": 2, "edit": "link"},
    "d2":     {"seed": 20260919_0003, "pairs": 512, "hops": 2, "edit": "link"},
    "onehop": {"seed": 20260919_0004, "pairs": 128, "hops": 1, "edit": "attr"},
}
PANELS = {
    "shortcut": (L.ROOT / "artifacts" / "claude-relcut-long-20260919", [f"relcutlong-s{s}-12000" for s in range(5)]),
    "baseline": (L.ROOT / "artifacts" / "claude-long-20260919", [f"long-s{s}-12000" for s in range(5)]),
}
STUCK = ("long-s0-12000", "relcutlong-s1-12000", "relcutlong-s2-12000")

# toy_ladder token constants (archive/.../frozen/premonition/toy_ladder.py line 38)
WORLD, QUESTION, ANSWER, NEWLINE = 3, 4, 5, 7
N_ENT = 16
KIND_NONE, KIND_ATTR, KIND_LINK = 0, 1, 2

SKIPPED = ["secondary cell: N=12 people", "secondary cell: three lookups", "secondary cell: gap=512",
           "full wipe/restore store-isolation check", "exact-code / soft-distribution control",
           "train-stream overlap reconstruction (overlap coverage: not checked)"]


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def fixed_hash(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


# --------------------------------------------------------------------------------------- fresh paired worlds
def _target_question(lines, hops: int, heldout: int):
    """Index of the scored question line: the first `hops`-hop question (2-hop must use the held-out relation)."""
    for k, line in enumerate(lines):
        if not line.question or line.hops != hops:
            continue
        if hops == 2 and line.relation != heldout:
            continue
        return k
    return None


def _make_pair(spec, rng, hops: int, edit: str):
    """One world pair, by rejection sampling.  -> (lines_a, lines_b, target_line, facts, rejections).

    hops == 2 / edit == 'link': the queried person's friend becomes another valid person whose target value
    DIFFERS; every other fact is fixed.  hops == 1 / edit == 'attr': the queried (person, relation) value
    changes; every other fact is fixed.
    """
    from premonition import toy_ladder
    rejections = Counter()
    while True:
        lines, world, plan = toy_ladder.visit(spec, rng, training=False)
        k = _target_question(lines, hops, spec.heldout_relation)
        if k is None:
            rejections["no_target_question"] += 1
            continue
        q = lines[k]
        a, r = q.ents[0], q.relation
        edited = deepcopy(world)
        if edit == "link":
            b = world.friend[a]
            options = [x for x in world.ents if x not in (a, b) and world.attr[(x, r)] != world.attr[(b, r)]]
            if not options:
                rejections["no_alternative_friend"] += 1
                continue
            new_b = rng.choice(options)
            edited.friend[a] = new_b
            facts = {"subject": a, "relation": r, "dest_a": b, "dest_b": new_b,
                     "value_a": world.attr[(b, r)], "value_b": world.attr[(new_b, r)]}
        else:
            options = [v for v in range(spec.values) if v != world.attr[(a, r)]]
            new_v = rng.choice(options)
            edited.attr[(a, r)] = new_v
            facts = {"subject": a, "relation": r, "dest_a": -1, "dest_b": -1,
                     "value_a": world.attr[(a, r)], "value_b": new_v}
        new_lines, _, _ = toy_ladder.visit(spec, rng, training=False, world=edited, plan=plan)
        if _target_question(new_lines, hops, spec.heldout_relation) != k:
            rejections["replay_moved_the_question"] += 1
            continue
        if new_lines[k].answer[0] == lines[k].answer[0]:
            rejections["target_value_unchanged"] += 1
            continue
        return lines, new_lines, k, facts, rejections


def _keep_questions(batch, index):
    """A VisitBatch with only the questions in `index` (the diary, its lines and every card are untouched)."""
    import torch
    idx = torch.tensor(index, dtype=torch.long)
    return dc_replace(
        batch, q_visit=batch.q_visit[idx], q_line=batch.q_line[idx], q_span=batch.q_span[idx],
        answer=batch.answer[idx], gold_lines=batch.gold_lines[idx], depth=batch.depth[idx],
        question_ids=[batch.question_ids[i] for i in index],
        slices=({k: v[idx] for k, v in batch.slices.items()} if batch.slices else None))


def _strip_labels(batch):
    """The same inputs with every evaluator label removed: the model can only ever see the diary."""
    import torch
    from learnlab.core import IGNORE_INDEX
    return dc_replace(
        batch, answer=torch.full_like(batch.answer, IGNORE_INDEX), gold_lines=torch.full_like(batch.gold_lines, -1),
        depth=torch.zeros_like(batch.depth), question_ids=[f"blind-{i}" for i in range(batch.q_visit.shape[0])],
        slices=None)


def generate_set(kind: str, *, spec=None):
    """-> {"chunks": [{"a": batch, "b": batch, "meta": [...]}], "rejections": {...}, ...}.  Model-free."""
    import torch
    from premonition import toy_ladder
    from premonition.train import label_free
    spec = spec or L.spec()
    cfg = SETS[kind]
    rejections, chunks, endpoint_values = Counter(), [], Counter()
    pairs = []
    for i in range(cfg["pairs"]):
        rng = random.Random(f"premonition-handoff-{kind}-{cfg['seed']}-{i}")
        lines_a, lines_b, line, facts, rej = _make_pair(spec, rng, cfg["hops"], cfg["edit"])
        rejections.update(rej)
        endpoint_values[facts["value_a"]] += 1
        endpoint_values[facts["value_b"]] += 1
        pairs.append((lines_a, lines_b, line, facts, i))
    for start in range(0, len(pairs), WORLDS_PER_CHUNK):
        block = pairs[start:start + WORLDS_PER_CHUNK]
        full_a = label_free(toy_ladder.assemble(spec, [p[0] for p in block], prefix=f"{kind}-a-{start}")[0])
        full_b = label_free(toy_ladder.assemble(spec, [p[1] for p in block], prefix=f"{kind}-b-{start}")[0])
        if not bool((full_a.tokens == full_b.tokens).sum(1).eq(full_a.tokens.shape[1] - 1).all()):
            raise SystemExit(f"{kind}: a pair differs in more than one visible token")
        keep_a, keep_b, meta = [], [], []
        for v, (_la, _lb, line, facts, index) in enumerate(block):
            qa = int(((full_a.q_visit == v) & (full_a.q_line == line)).nonzero()[0])
            qb = int(((full_b.q_visit == v) & (full_b.q_line == line)).nonzero()[0])
            keep_a.append(qa)
            keep_b.append(qb)
            meta.append({
                "pair": index, "visit": v, "line": line, "hops": cfg["hops"], **facts,
                "answer_a": full_a.answer[qa][full_a.answer[qa] != -100].tolist(),
                "answer_b": full_b.answer[qb][full_b.answer[qb] != -100].tolist(),
                "gold_a": [x for x in full_a.gold_lines[qa].tolist() if x >= 0],
                "gold_b": [x for x in full_b.gold_lines[qb].tolist() if x >= 0],
                "key_a": f"{kind}|{index}|a", "key_b": f"{kind}|{index}|b"})
        chunks.append({"a": _keep_questions(full_a, keep_a), "b": _keep_questions(full_b, keep_b), "meta": meta})
    return {"kind": kind, "seed": cfg["seed"], "pairs": cfg["pairs"], "hops": cfg["hops"], "edit": cfg["edit"],
            "chunks": chunks, "rejections": dict(sorted(rejections.items())),
            "endpoint_value_counts": {str(k): v for k, v in sorted(endpoint_values.items())},
            "worlds_per_chunk": WORLDS_PER_CHUNK}


# --------------------------------------------------------------------------------- visible field extraction
class FieldView:
    """Disclosed parse of the VISIBLE card lines: subject at line offset 1, relation/LINK at 2, object at 3.

    Malformed lines and fillers are rejected (kind == KIND_NONE); no label, gold line or answer is consulted.
    """

    def __init__(self, batch, spec):
        import torch
        tokens, starts = batch.tokens, batch.line_start
        visits, width = tokens.shape
        lines = starts.shape[1]
        following = torch.cat([starts[:, 1:], torch.full_like(starts[:, :1], -1)], dim=1)
        ends = torch.where(following >= 0, following, batch.lengths.unsqueeze(1).expand(-1, lines))
        length = torch.where(starts >= 0, ends - starts, torch.zeros_like(starts))
        safe = starts.clamp(0, width - 4)
        t = [tokens.gather(1, safe + k) for k in range(4)]
        long_enough = (starts >= 0) & (length >= 5) & (starts + 3 < width)
        ok = long_enough & ~batch.line_is_question & (t[0] == WORLD)
        subj = t[1] - spec.vocab_size
        is_subject = ok & (subj >= 0) & (subj < N_ENT)
        rel = t[2] - spec.relation(0)
        is_attr = is_subject & (rel >= 0) & (rel < spec.relations)
        is_link = is_subject & (t[2] == spec.link)
        value = t[3] - spec.value(0)
        obj_ent = t[3] - spec.vocab_size
        attr_ok = is_attr & (value >= 0) & (value < spec.values)
        link_ok = is_link & (obj_ent >= 0) & (obj_ent < N_ENT)
        minus = torch.full_like(subj, -1)
        self.kind = torch.where(attr_ok, torch.full_like(subj, KIND_ATTR),
                                torch.where(link_ok, torch.full_like(subj, KIND_LINK),
                                            torch.full_like(subj, KIND_NONE)))
        self.subj = torch.where(attr_ok | link_ok, subj, minus)
        self.rel = torch.where(attr_ok, rel, minus)
        self.value = torch.where(attr_ok, value, minus)
        self.obj_ent = torch.where(link_ok, obj_ent, minus)
        self.is_fact = self.kind > 0
        # in-world entities per visit, from the visible cards only
        self.entities = [sorted({int(e) for e in self.subj[v][self.is_fact[v]].tolist()}) for v in range(visits)]
        # question layout
        span = batch.q_span
        w = int((span[:, 1] - span[:, 0]).max())
        pos = span[:, 0].unsqueeze(1) + torch.arange(w)
        inside = pos < span[:, 1].unsqueeze(1)
        qt = torch.where(inside, tokens[batch.q_visit.unsqueeze(1), pos.clamp(0, width - 1)],
                         torch.full_like(pos, -1))
        self.q_tokens = qt
        self.q_subject = qt[:, 1] - spec.vocab_size
        self.q_has_link = (qt == spec.link).any(1)
        self.q_rel = tokens[batch.q_visit, span[:, 1] - 2] - spec.relation(0)
        self.q_visit = batch.q_visit
        self.q_line = batch.q_line
        self.lines = lines


def subject_mask(fields, subject, store_lines: int):
    """[Q, L] bool: real fact cards of the question's visit whose parsed subject == `subject` [Q] (-1 = none)."""
    import torch
    ok = fields.is_fact[fields.q_visit] & (fields.subj[fields.q_visit] == subject.unsqueeze(1))
    ok &= subject.unsqueeze(1) >= 0
    if ok.shape[1] < store_lines:
        ok = torch.cat([ok, torch.zeros(ok.shape[0], store_lines - ok.shape[1], dtype=torch.bool)], 1)
    return ok[:, :store_lines]


def apply_mask(scores, permitted):
    """Eligibility mask only: non-permitted REAL cards go to -inf; the NULL column is never touched."""
    import torch
    out = scores.clone()
    real = out[:, :permitted.shape[1]]
    out[:, :permitted.shape[1]] = real.masked_fill(~permitted, float("-inf"))
    return out


def handoff_source(fields, first_cards, store_lines: int):
    """(active [Q] bool, source [Q] entity id).

    Active only when the question shows LINK and the card ACTUALLY fetched first is a link card with a valid
    entity object.  NULL, no request, a filler, an attribute card or a malformed line leave it inactive.
    """
    import torch
    real = (first_cards >= 0) & (first_cards < store_lines)
    idx = first_cards.clamp(0, max(store_lines - 1, 0))
    kind = fields.kind[fields.q_visit, idx]
    obj = fields.obj_ent[fields.q_visit, idx]
    active = fields.q_has_link & real & (kind == KIND_LINK) & (obj >= 0)
    return active, torch.where(active, obj, torch.full_like(obj, -1))


def wrong_source(fields, active, source, keys):
    """A different in-world entity per question, by a fixed hash of the neutral world key, excluding `source`."""
    import torch
    out = source.clone()
    for q in range(source.shape[0]):
        if not bool(active[q]):
            continue
        pool = [e for e in fields.entities[int(fields.q_visit[q])] if e != int(source[q])]
        out[q] = pool[fixed_hash(f"qw|{keys[q]}") % len(pool)] if pool else -1
    return out


# ------------------------------------------------------------------------------------ deterministic solver
def interpret(fields, q: int):
    """The exact tuple interpreter over the visible cards a question may see.  -> value index, or None."""
    v = int(fields.q_visit[q])
    limit = int(fields.q_line[q])
    subject, rel = int(fields.q_subject[q]), int(fields.q_rel[q])
    kinds = fields.kind[v][:limit].tolist()
    subj = fields.subj[v][:limit].tolist()
    rels = fields.rel[v][:limit].tolist()
    vals = fields.value[v][:limit].tolist()
    objs = fields.obj_ent[v][:limit].tolist()
    if bool(fields.q_has_link[q]):
        hops = [objs[i] for i in range(limit) if kinds[i] == KIND_LINK and subj[i] == subject]
        if len(hops) != 1:
            return None
        subject = hops[0]
    hit = [vals[i] for i in range(limit) if kinds[i] == KIND_ATTR and subj[i] == subject and rels[i] == rel]
    return hit[0] if len(hit) == 1 else None


def shortcut_strategies(fields, q: int, target: int) -> dict:
    """Question-blind modal value, relation-only and direct-question-subject shortcuts.

    Each is reported as a deterministic pick (modal, lowest value id breaks ties) and as the expected hit rate
    of a uniform draw among the candidate values.
    """
    v = int(fields.q_visit[q])
    limit = int(fields.q_line[q])
    subject, rel = int(fields.q_subject[q]), int(fields.q_rel[q])
    kinds = fields.kind[v][:limit].tolist()
    subj = fields.subj[v][:limit].tolist()
    rels = fields.rel[v][:limit].tolist()
    vals = fields.value[v][:limit].tolist()
    attrs = [i for i in range(limit) if kinds[i] == KIND_ATTR]
    pools = {"question_blind_modal": [vals[i] for i in attrs],
             "relation_only": [vals[i] for i in attrs if rels[i] == rel],
             "direct_question_subject": [vals[i] for i in attrs if subj[i] == subject and rels[i] == rel]}
    out = {}
    for name, pool in pools.items():
        if not pool:
            out[name] = (False, 0.0)
            continue
        counts = Counter(pool)
        best = max(counts.values())
        pick = min(k for k, c in counts.items() if c == best)
        out[name] = (pick == target, counts[target] / len(pool))
    return out


# ------------------------------------------------------------------------------------------- the conditions
def _digest(tensor) -> str:
    return sha256_bytes(tensor.detach().cpu().contiguous().numpy().tobytes())


def run_condition(model, batch, fields, condition: str, keys):
    """`own_fixed(..., loops=4)` with ONE extra eligibility mask.  Nothing else changes.

    Returns predictions and the full trace.  `batch` must already be label-free (`_strip_labels`).
    """
    import torch
    if condition not in CONDITIONS:
        raise ValueError(condition)
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    q_subject = fields.q_subject
    q_permitted = subject_mask(fields, q_subject, store.lines)
    all_permitted = torch.ones_like(q_permitted)
    trace = {"cards": [], "ask": [], "masked": [], "restricted": [], "selection_changed": [], "digests": []}
    first_cards = None
    handoff_active = torch.zeros(everyone.shape[0], dtype=torch.bool)
    handoff_src = torch.full_like(everyone, -1)
    for step in range(LOOPS):
        rows, halt, ask, scores = model._step(episode, everyone, step, store)
        if step + 1 >= LOOPS:
            break
        eligible_before = torch.isfinite(scores[:, :store.lines])
        permitted = None
        if condition == "N":
            permitted = all_permitted
        elif step == 0 and condition in ("Q", "QD", "QW"):
            permitted = q_permitted
        elif step == 1 and condition in ("D", "QD", "QW"):
            source = handoff_src if condition != "QW" else wrong_source(fields, handoff_active, handoff_src, keys)
            gate = subject_mask(fields, source, store.lines)
            permitted = torch.where(handoff_active.unsqueeze(1), gate, all_permitted)
        used = scores if permitted is None else apply_mask(scores, permitted)
        gated = store.top(used, model.config.top_k)
        cards = gated.masked_fill((ask <= 0).unsqueeze(1), -1)
        native = store.top(scores, model.config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
        eligible_after = torch.isfinite(used[:, :store.lines])
        trace["cards"].append(cards[:, 0].clone())
        trace["ask"].append((ask > 0).clone())
        trace["masked"].append(torch.tensor(permitted is not None).expand(everyone.shape[0]).clone())
        trace["restricted"].append((eligible_after.sum(1) < eligible_before.sum(1)).clone())
        trace["selection_changed"].append((cards[:, 0] != native[:, 0]).clone())
        trace["digests"].append(_digest(used))
        if step == 0:
            first_cards = cards[:, 0].clone()
            handoff_active, handoff_src = handoff_source(fields, first_cards, store.lines)
        model._insert(episode, store, everyone, cards)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    return {"tokens": tokens, "lengths": lengths, "store_lines": store.lines,
            "cards": torch.stack(trace["cards"], 1), "ask": torch.stack(trace["ask"], 1),
            "restricted": torch.stack(trace["restricted"], 1),
            "selection_changed": torch.stack(trace["selection_changed"], 1),
            "handoff_attempted": handoff_active, "handoff_source": handoff_src,
            "first_cards": first_cards, "digests": trace["digests"]}


def traced_own_fixed(model, batch, loops: int = LOOPS):
    """`R.own_fixed` itself, with the historical `_insert` wrapped so the fetched lines are recorded.

    The frozen function is untouched; only this instance's bound method is wrapped for the call.
    """
    import torch
    fetched = []
    original = model._insert

    def spy(episode, store, index, cards):
        fetched.append(cards[:, 0].clone())
        return original(episode, store, index, cards)

    model._insert = spy
    try:
        ok, gold = R.own_fixed(model, batch, loops)
    finally:
        del model._insert
    return ok, gold, torch.stack(fetched, 1)


def correctness(result, answers):
    """[Q] bool: the greedy answer equals the evaluator's held answer ids."""
    import torch
    tokens, lengths = result["tokens"], result["lengths"]
    return torch.tensor([tokens[q, :int(lengths[q])].tolist() == answers[q] for q in range(len(answers))])


# ------------------------------------------------------------------------------------------------ scoring
def dataset_audit(dataset, spec) -> dict:
    """Model-free: the exact tuple interpreter (must be 100%) and the three shortcut ceilings."""
    interp_ok = [0, 0]
    pair_interp = 0
    names = ("question_blind_modal", "relation_only", "direct_question_subject")
    det = {n: [0, 0] for n in names}
    exp = {n: 0.0 for n in names}
    pair_det = {n: 0 for n in names}
    pair_exp = {n: 0.0 for n in names}
    invalid = []
    for chunk in dataset["chunks"]:
        views = {side: FieldView(chunk[side], spec) for side in ("a", "b")}
        for q, meta in enumerate(chunk["meta"]):
            both, both_det, both_exp = True, {n: True for n in names}, {n: 1.0 for n in names}
            for side in ("a", "b"):
                target = meta[f"value_{side}"]
                got = interpret(views[side], q)
                interp_ok[1] += 1
                interp_ok[0] += int(got == target)
                if got != target:
                    invalid.append({"pair": meta["pair"], "side": side, "got": got, "want": target})
                    both = False
                for name, (hit, rate) in shortcut_strategies(views[side], q, target).items():
                    det[name][1] += 1
                    det[name][0] += int(hit)
                    exp[name] += rate
                    both_det[name] &= hit
                    both_exp[name] *= rate
            pair_interp += int(both)
            for name in names:
                pair_det[name] += int(both_det[name])
                pair_exp[name] += both_exp[name]
    pairs = dataset["pairs"]
    answers = interp_ok[1]
    return {"interpreter": {"single_answer": interp_ok[0], "n": answers,
                            "accuracy": round(interp_ok[0] / max(answers, 1), 6),
                            "both_correct_pairs": pair_interp, "pairs": pairs,
                            "pair_accuracy": round(pair_interp / max(pairs, 1), 6),
                            "failures": invalid[:8]},
            "shortcut_ceilings": {
                n: {"single_deterministic": round(det[n][0] / max(det[n][1], 1), 4),
                    "single_expected_uniform": round(exp[n] / max(det[n][1], 1), 4),
                    "pair_deterministic": round(pair_det[n] / max(pairs, 1), 4),
                    "pair_expected_uniform": round(pair_exp[n] / max(pairs, 1), 4)} for n in names}}


def score_set(model, dataset, conditions, spec) -> dict:
    """Run every condition over one dataset.  -> per-condition per-member arrays and per-pair both-correct."""
    import torch
    out = {c: {"correct": [], "first_card": [], "second_card": [], "ask": [], "restricted": [],
               "selection_changed": [], "handoff_attempted": [], "handoff_source": [], "pred_first": [],
               "digests": []} for c in conditions}
    audit = {"correct_first_link": [], "gold_link_line": [], "gold_answer_line": [], "pair_of": [], "side": []}
    with torch.no_grad():
        for chunk in dataset["chunks"]:
            metas = chunk["meta"]
            for side in ("a", "b"):
                batch = _strip_labels(chunk[side])
                fields = FieldView(batch, spec)
                keys = [m[f"key_{side}"] for m in metas]
                answers = [m[f"answer_{side}"] for m in metas]
                gold = [m[f"gold_{side}"] for m in metas]
                audit["gold_link_line"].append([g[0] if len(g) > 1 else -1 for g in gold])
                audit["gold_answer_line"].append([g[-1] for g in gold])
                audit["pair_of"].append([m["pair"] for m in metas])
                audit["side"].append([side] * len(metas))
                for cond in conditions:
                    res = run_condition(model, batch, fields, cond, keys)
                    ok = correctness(res, answers)
                    slot = out[cond]
                    slot["correct"].append(ok)
                    slot["first_card"].append(res["cards"][:, 0])
                    slot["second_card"].append(res["cards"][:, 1])
                    slot["ask"].append(res["ask"])
                    slot["restricted"].append(res["restricted"])
                    slot["selection_changed"].append(res["selection_changed"])
                    slot["handoff_attempted"].append(res["handoff_attempted"])
                    slot["handoff_source"].append(res["handoff_source"])
                    slot["pred_first"].append(res["tokens"][:, 0])
                    slot["digests"].append(res["digests"])
    merged = {}
    for cond, slot in out.items():
        merged[cond] = {k: ([d for row in v for d in row] if k == "digests" else torch.cat(v))
                        for k, v in slot.items()}
    link = torch.tensor([x for row in audit["gold_link_line"] for x in row])
    answer_line = torch.tensor([x for row in audit["gold_answer_line"] for x in row])
    pair_of = torch.tensor([x for row in audit["pair_of"] for x in row])
    for cond in merged:
        merged[cond]["correct_first_link"] = (merged[cond]["first_card"] == link) & (link >= 0)
        merged[cond]["correct_second_answer_card"] = merged[cond]["second_card"] == answer_line
    merged["_pair_of"] = pair_of
    merged["_gold_link_line"] = link
    merged["_gold_answer_line"] = answer_line
    return merged


def pair_both_correct(merged, cond):
    """[pairs] bool, in pair order: both members of the world pair answered correctly."""
    import torch
    pair_of, ok = merged["_pair_of"], merged[cond]["correct"]
    pairs = int(pair_of.max()) + 1
    out = torch.ones(pairs, dtype=torch.long)
    out.scatter_reduce_(0, pair_of, ok.long(), reduce="amin", include_self=True)
    return out.bool()


# ------------------------------------------------------------------------------------------------ analysis
def opportunity_audit(merged) -> dict:
    """(a)-(d) of the protocol, without changing denominators.  Gold evidence is used here, never in inference."""
    import torch
    pair_of = merged["_pair_of"]
    pairs = int(pair_of.max()) + 1
    q_ok = merged["Q"]["correct"]
    q_link = merged["Q"]["correct_first_link"]
    d_ready = merged["QD"]["handoff_attempted"]
    both_q = pair_both_correct(merged, "Q")
    wrong_all_eligible = torch.ones(pairs, dtype=torch.bool)
    wrong_all_bridged = torch.ones(pairs, dtype=torch.bool)
    has_wrong = torch.zeros(pairs, dtype=torch.bool)
    for i in range(q_ok.shape[0]):
        if bool(q_ok[i]):
            continue
        p = int(pair_of[i])
        has_wrong[p] = True
        wrong_all_eligible[p] &= bool(d_ready[i])
        wrong_all_bridged[p] &= bool(d_ready[i]) and bool(q_link[i])
    c = (has_wrong & wrong_all_eligible & ~both_q)
    d = (has_wrong & wrong_all_bridged & ~both_q)
    after_link = q_ok[q_link]
    link_pairs = torch.ones(pairs, dtype=torch.long)
    link_pairs.scatter_reduce_(0, pair_of, q_link.long(), reduce="amin", include_self=True)
    return {"a_q_first_link_correct_rate": round(float(q_link.float().mean()), 4),
            "a_q_first_link_correct_pairs": round(float(link_pairs.float().mean()), 4),
            "b_error_rate_given_correct_first_link": round(1.0 - float(after_link.float().mean())
                                                           if after_link.numel() else 0.0, 4),
            "b_n_correct_first_link": int(q_link.sum()),
            "c_wrong_members_all_d_eligible_frac_of_all_pairs": round(float(c.float().mean()), 4),
            "d_wrong_members_all_correct_bridge_frac_of_all_pairs": round(float(d.float().mean()), 4),
            "q_incorrect_pairs": int((~both_q).sum()), "pairs": pairs}


def bootstrap_delta(per_seed_pairs, resamples: int = 10000, seed: int = 20260919):
    """Paired world-cluster bootstrap.  `per_seed_pairs` is {seed: (b_qd [P] bool, b_q [P] bool)}.

    Worlds are resampled once per replicate and the SAME resample is applied to every training seed, so the
    equal-weight mean over seeds reduces to the mean over worlds of the per-world seed-averaged difference.
    """
    import torch
    g = torch.Generator().manual_seed(seed)
    diffs = torch.stack([(qd.float() - q.float()) for qd, q in per_seed_pairs.values()])   # [S, P]
    per_world = diffs.mean(0)
    pairs = per_world.shape[0]
    index = torch.randint(0, pairs, (resamples, pairs), generator=g)
    draws = per_world[index].mean(1)
    lower = float(draws.kthvalue(max(1, int(round(0.01 * resamples))))[0])
    upper = float(draws.kthvalue(max(1, int(round(0.99 * resamples))))[0])
    return {"resamples": resamples, "delta": round(float(per_world.mean()), 6),
            "one_sided_99_lower": round(lower, 6), "one_sided_99_upper": round(upper, 6),
            "bootstrap_mean": round(float(draws.mean()), 6), "bootstrap_sd": round(float(draws.std()), 6)}


def advancement(panel: dict, one_hop: dict, audit: dict) -> dict:
    """The five advancement conditions and the 'no useful handoff effect' rule, evaluated mechanically."""
    seeds = sorted(panel["per_seed"])
    b = {c: [panel["per_seed"][s][c] for s in seeds] for c in CONDITIONS}
    gains = [panel["per_seed"][s]["QD"] - panel["per_seed"][s]["Q"] for s in seeds]
    delta = panel["bootstrap"]["delta"]
    lower = panel["bootstrap"]["one_sided_99_lower"]
    upper = panel["bootstrap"]["one_sided_99_upper"]
    qd_minus_qw = sum(x - y for x, y in zip(b["QD"], b["QW"])) / len(seeds)
    one_hop_gap = [one_hop["per_seed"][s]["QD"] - one_hop["per_seed"][s]["Q"] for s in seeds]
    one_hop_q_loss = [one_hop["per_seed"][s]["U"] - one_hop["per_seed"][s]["Q"] for s in seeds]
    d_values = [audit[s]["d_wrong_members_all_correct_bridge_frac_of_all_pairs"] for s in seeds]
    mean_d = sum(d_values) / len(d_values)
    coverage = mean_d >= 0.15 and sum(x >= 0.15 for x in d_values) >= 2
    checks = {
        "1_primary_effect": {"pass": bool(delta >= 0.15 and lower > 0.05),
                             "delta": delta, "lower99": lower, "need": "delta >= 0.15 and lower99 > 0.05"},
        "2_seed_spread": {"pass": bool(sum(g >= 0.15 for g in gains) >= 2 and all(g >= -0.03 for g in gains)),
                          "gains": [round(g, 4) for g in gains],
                          "need": ">=2 seeds gain >=0.15 and no seed loses more than 0.03"},
        "3_quality": {"pass": bool(sum(x >= 0.80 for x in b["QD"]) >= 4),
                      "qd": [round(x, 4) for x in b["QD"]], "need": "QD >= 0.80 in >=4 of 5 seeds"},
        "4_controls": {"pass": bool(qd_minus_qw >= 0.15 and panel["n_equals_u"]
                                    and all(abs(x) < 1e-12 for x in one_hop_gap)
                                    and all(x <= 0.03 for x in one_hop_q_loss)),
                       "qd_minus_qw_mean": round(qd_minus_qw, 4), "n_equals_u": panel["n_equals_u"],
                       "one_hop_qd_minus_q": [round(x, 6) for x in one_hop_gap],
                       "one_hop_u_minus_q": [round(x, 4) for x in one_hop_q_loss],
                       "need": "QD-QW >= 0.15, N == U, one-hop QD-Q == 0, one-hop Q loses <= 0.03"},
        "5_fresh_confirmation": {"pass": None, "status": "NOT_RUN (D2 is sealed; run only if 1-4 pass)"},
    }
    decided = [v["pass"] for k, v in checks.items() if v["pass"] is not None]
    reject = bool(coverage and delta < 0.05 and upper < 0.10)
    verdict = ("PASS" if all(decided) else
               ("REJECT_NO_USEFUL_EFFECT" if reject else "INCONCLUSIVE"))
    return {"checks": checks, "adequate_coverage": bool(coverage), "mean_d": round(mean_d, 4),
            "d_per_seed": [round(x, 4) for x in d_values],
            "no_useful_effect_rule": {"pass": reject, "delta": delta, "upper99": upper,
                                      "need": "coverage and delta < 0.05 and upper99 < 0.10"},
            "verdict_d1": verdict,
            "note": "conditional on this fixed panel of five training replications; not a population claim"}


# -------------------------------------------------------------------------------------- two-edge fixture
class _Fixture:
    """A hand-built two-edge field view: L(a->b), L(c->d), A(b,r)=v1, A(d,r)=v2 (v1 != v2), A(a,r), filler."""

    LINES = 6
    A, B, C, D_ENT, OTHER = 0, 1, 2, 3, 4
    REL = 1
    V1, V2 = 5, 9

    def __init__(self):
        import torch
        kind = [KIND_LINK, KIND_LINK, KIND_ATTR, KIND_ATTR, KIND_ATTR, KIND_NONE]
        subj = [self.A, self.C, self.B, self.D_ENT, self.A, -1]
        obj = [self.B, self.D_ENT, -1, -1, -1, -1]
        val = [-1, -1, self.V1, self.V2, 3, -1]
        rel = [-1, -1, self.REL, self.REL, self.REL, -1]
        self.kind = torch.tensor([kind])
        self.subj = torch.tensor([subj])
        self.obj_ent = torch.tensor([obj])
        self.value = torch.tensor([val])
        self.rel = torch.tensor([rel])
        self.is_fact = self.kind > 0
        self.entities = [sorted({self.A, self.B, self.C, self.D_ENT, self.OTHER})]
        self.q_visit = torch.tensor([0, 0])          # q0: two-hop "a LINK r", q1: one-hop "a r"
        self.q_line = torch.tensor([self.LINES, self.LINES])
        self.q_subject = torch.tensor([self.A, self.A])
        self.q_has_link = torch.tensor([True, False])
        self.q_rel = torch.tensor([self.REL, self.REL])
        self.lines = self.LINES


def fixture_checks() -> dict:
    """Semantics of the masks, not model quality: two edges with different endpoint values, a wrong source,
    NULL, a non-link first card, a filler and no request."""
    import torch
    f = _Fixture()
    out = {}
    permitted = subject_mask(f, f.q_subject, f.LINES)
    out["q_mask_subject_a"] = permitted[0].nonzero().flatten().tolist()
    out["q_mask_subject_a_expected"] = [0, 4]
    absent = subject_mask(f, torch.tensor([f.OTHER, f.OTHER]), f.LINES)
    out["no_match_leaves_no_real_card"] = bool(~absent[0].any())
    scores = torch.tensor([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 0.5]])          # 6 real + NULL last
    masked = apply_mask(scores, permitted[:1])
    out["null_score_preserved"] = float(masked[0, -1]) == 0.5
    out["masked_real"] = [i for i in range(f.LINES) if masked[0, i] == float("-inf")]
    out["top1_after_q_mask"] = int(masked[0].argmax())
    empty = apply_mask(scores, absent[:1])
    out["no_match_top1_is_null"] = int(empty[0].argmax()) == f.LINES
    cases = {"correct_link": 0, "wrong_source_link": 1, "non_link_attribute": 4, "filler": 5,
             "null_card": f.LINES, "no_request": -1}
    out["handoff"] = {}
    for name, first in cases.items():
        active, src = handoff_source(f, torch.tensor([first, first]), f.LINES)
        out["handoff"][name] = {"two_hop_active": bool(active[0]), "two_hop_source": int(src[0]),
                                "one_hop_active": bool(active[1])}
    out["endpoint_values_differ"] = f.V1 != f.V2
    keys = ["fix|0|a", "fix|0|a"]
    active, src = handoff_source(f, torch.tensor([0, 0]), f.LINES)
    wrong = wrong_source(f, active, src, keys)
    out["qw_excludes_destination"] = int(wrong[0]) != int(src[0]) and int(wrong[0]) in f.entities[0]
    expect = (out["q_mask_subject_a"] == out["q_mask_subject_a_expected"]
              and out["no_match_leaves_no_real_card"] and out["null_score_preserved"]
              and out["masked_real"] == [1, 2, 3, 5] and out["top1_after_q_mask"] == 4
              and out["no_match_top1_is_null"]
              and out["handoff"]["correct_link"] == {"two_hop_active": True, "two_hop_source": f.B,
                                                     "one_hop_active": False}
              and out["handoff"]["wrong_source_link"]["two_hop_source"] == f.D_ENT
              and not out["handoff"]["non_link_attribute"]["two_hop_active"]
              and not out["handoff"]["filler"]["two_hop_active"]
              and not out["handoff"]["null_card"]["two_hop_active"]
              and not out["handoff"]["no_request"]["two_hop_active"]
              and out["endpoint_values_differ"] and out["qw_excludes_destination"])
    out["pass"] = bool(expect)
    return out


def field_extraction_check(dataset, spec) -> dict:
    """Every real card parses to the generator's fact; fillers never do; the question subject is read off
    the visible layout."""
    facts_expected = spec.entities * spec.relations + spec.entities
    bad = {"fact_card_count": 0, "gold_link": 0, "gold_answer": 0, "question_subject": 0,
           "question_relation": 0, "filler_parsed_as_fact": 0}
    cards = 0
    for chunk in dataset["chunks"]:
        for side in ("a", "b"):
            view = FieldView(chunk[side], spec)
            batch = chunk[side]
            for v in range(batch.tokens.shape[0]):
                n = int(view.is_fact[v].sum())
                cards += n
                bad["fact_card_count"] += int(n != facts_expected)
            for q, meta in enumerate(chunk["meta"]):
                bad["question_subject"] += int(int(view.q_subject[q]) != meta["subject"])
                bad["question_relation"] += int(int(view.q_rel[q]) != meta["relation"])
                gold = meta[f"gold_{side}"]
                vis = int(view.q_visit[q])
                if meta["hops"] == 2:
                    link = gold[0]
                    bad["gold_link"] += int(not (int(view.kind[vis, link]) == KIND_LINK
                                                 and int(view.subj[vis, link]) == meta["subject"]
                                                 and int(view.obj_ent[vis, link]) == meta[f"dest_{side}"]))
                    answer = gold[1]
                    bad["gold_answer"] += int(not (int(view.kind[vis, answer]) == KIND_ATTR
                                                   and int(view.subj[vis, answer]) == meta[f"dest_{side}"]
                                                   and int(view.rel[vis, answer]) == meta["relation"]
                                                   and int(view.value[vis, answer]) == meta[f"value_{side}"]))
                else:
                    answer = gold[0]
                    bad["gold_answer"] += int(not (int(view.kind[vis, answer]) == KIND_ATTR
                                                   and int(view.subj[vis, answer]) == meta["subject"]
                                                   and int(view.value[vis, answer]) == meta[f"value_{side}"]))
    return {"fact_cards_seen": cards, "fact_cards_expected_per_visit": facts_expected,
            "failures": bad, "pass": all(v == 0 for v in bad.values())}


# ------------------------------------------------------------------------------------- manifest and loading
def manifest_path() -> Path:
    return OUT / "manifest.json"


def cmd_gen(args) -> None:
    """Fresh worlds from seeds fixed in this file.  No checkpoint is loaded and no model is built."""
    import torch
    spec = L.spec()
    DATA.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    manifest = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "purpose": "D0/D1 handoff diagnostic; D2 sealed",
                "generator_sources": {
                    "scripts/premonition_handoff_diag.py": sha256_file(SOURCE),
                    "frozen/premonition/toy_ladder.py": sha256_file(
                        L.ARCHIVE / "frozen" / "premonition" / "toy_ladder.py")},
                "spec": {k: getattr(spec, k) for k in ("entities", "relations", "values", "fillers",
                                                       "distractors", "gap", "one_hop", "two_hop",
                                                       "heldout_relation")},
                "worlds_per_chunk": WORLDS_PER_CHUNK, "loops": LOOPS, "conditions": list(CONDITIONS),
                "sets": {}, "skipped": SKIPPED}
    for kind in SETS:
        data = generate_set(kind, spec=spec)
        path = DATA / f"{kind}.pt"
        torch.save(data, path)
        manifest["sets"][kind] = {
            "seed": data["seed"], "pairs": data["pairs"], "hops": data["hops"], "edit": data["edit"],
            "file": str(path.relative_to(L.ROOT)), "sha256": sha256_file(path),
            "rejections": data["rejections"], "endpoint_value_counts": data["endpoint_value_counts"],
            "scored": kind != "d2", "seal": "generated and hashed; scored only after D1 advances"
            if kind == "d2" else "scored"}
        print(f"{kind}: {data['pairs']} pairs, rejections {data['rejections']}", flush=True)
    manifest["seconds"] = round(time.perf_counter() - started, 2)
    manifest_path().parent.mkdir(parents=True, exist_ok=True)
    manifest_path().write_text(json.dumps(manifest, indent=1))
    print("wrote", manifest_path(), "sha256", sha256_file(manifest_path()))


def load_set(kind: str, manifest: dict):
    import torch
    info = manifest["sets"][kind]
    path = L.ROOT / info["file"]
    if sha256_file(path) != info["sha256"]:
        raise SystemExit(f"{path} changed since the manifest freeze")
    return torch.load(path, weights_only=False)


def checkpoints() -> list:
    """[(panel, name, path, run_json)] for the ten frozen 12k checkpoints."""
    out = []
    for panel, (root, names) in PANELS.items():
        for name in names:
            out.append((panel, name, root / "ckpt" / f"{name}.pt", root / "runs" / f"{name}.json"))
    return out


def load_checkpoint(name: str, ckpt: Path, run_json: Path) -> tuple:
    """The frozen model plus the integrity record the protocol asks for."""
    digest = sha256_file(ckpt)
    recorded = json.loads(run_json.read_text())
    if digest != recorded.get("ckpt_sha256"):
        raise SystemExit(f"{name}: checkpoint sha256 {digest} != run JSON {recorded.get('ckpt_sha256')}")
    model, blob = P.load_from(name, ckpt.parent)
    record = {"name": name, "ckpt_sha256": digest, "model_class": blob.get("model_class") or type(model).__name__,
              "relation_shortcut": bool(blob.get("relation_shortcut")), "seed": blob.get("seed"),
              "parameters": sum(p.numel() for p in model.parameters()),
              "historical_fixed_K4_heldout": recorded["validation"]["fixed_K4"]["two_hop_heldout_rel"],
              "stuck_run": name in STUCK}
    return model, record


# ------------------------------------------------------------------------------------------------------ D0
def parity_against_history(model, items) -> dict:
    """U must reproduce `premonition_ovn_retrieval.own_fixed(..., loops=4)`: answers AND fetched lines.

    The historical function is called unchanged; only this instance's `_insert` is wrapped to record.
    """
    import torch
    spec = L.spec()
    answers_equal = fetch_equal = questions = 0
    with torch.no_grad():
        for batch, _supplied, _hops in items:
            ok_hist, _gold, fetched_hist = traced_own_fixed(model, batch, LOOPS)
            blind = _strip_labels(batch)
            fields = FieldView(blind, spec)
            res = run_condition(model, blind, fields, "U", [f"parity|{i}" for i in range(blind.q_visit.shape[0])])
            gold = [batch.answer[q][batch.answer[q] != -100].tolist() for q in range(batch.answer.shape[0])]
            ok_mine = correctness(res, gold)
            answers_equal += int((ok_mine == ok_hist).sum())
            fetch_equal += int((res["cards"] == fetched_hist).all(1).sum())
            questions += int(ok_hist.shape[0])
    return {"questions": questions, "answers_equal": answers_equal, "fetched_lines_equal": fetch_equal,
            "pass": answers_equal == questions and fetch_equal == questions}


def filter_equivalence(model, items) -> dict:
    """Scoring only the target question of a visit must not change that question's prediction."""
    import torch
    spec = L.spec()
    same = total = 0
    with torch.no_grad():
        for batch, _supplied, _hops in items[:2]:
            blind = _strip_labels(batch)
            keep = [int(((blind.q_visit == v)).nonzero()[0]) for v in range(blind.tokens.shape[0])]
            full = run_condition(model, blind, FieldView(blind, spec), "Q",
                                 [f"eq|{i}" for i in range(blind.q_visit.shape[0])])
            sub = _keep_questions(blind, keep)
            part = run_condition(model, sub, FieldView(sub, spec), "Q", [f"eq|{i}" for i in keep])
            for j, q in enumerate(keep):
                total += 1
                same += int(full["tokens"][q].tolist() == part["tokens"][j].tolist()
                            and full["cards"][q].tolist() == part["cards"][j].tolist())
    return {"questions": total, "identical": same, "pass": same == total}


def label_perturbation_check(model, dataset, spec) -> dict:
    """Perturbing answers, gold lines, pair ids and slices must change nothing the model sees."""
    import torch
    chunk = dataset["chunks"][0]
    batch = chunk["a"]
    keys = [m["key_a"] for m in chunk["meta"]]
    blind = _strip_labels(batch)
    noisy = dc_replace(batch, answer=torch.full_like(batch.answer, 7),
                       gold_lines=torch.zeros_like(batch.gold_lines),
                       depth=torch.full_like(batch.depth, 3),
                       question_ids=[f"perturbed-{i}" for i in range(batch.q_visit.shape[0])],
                       slices={"bogus": torch.ones(batch.q_visit.shape[0], dtype=torch.bool)})
    noisy_blind = _strip_labels(noisy)
    same = True
    with torch.no_grad():
        for cond in CONDITIONS:
            a = run_condition(model, blind, FieldView(blind, spec), cond, keys)
            b = run_condition(model, noisy_blind, FieldView(noisy_blind, spec), cond, keys)
            same &= bool(torch.equal(a["tokens"], b["tokens"])) and bool(torch.equal(a["cards"], b["cards"]))
            same &= a["digests"] == b["digests"]
    return {"conditions": list(CONDITIONS), "identical": bool(same), "pass": bool(same),
            "design": "the model is only ever handed _strip_labels(batch); labels live in the evaluator meta"}


def cmd_d0(args) -> None:
    import torch
    torch.set_num_threads(4)
    spec = L.spec()
    manifest = json.loads(manifest_path().read_text())
    dev = load_set("dev", manifest)
    started = time.perf_counter()
    report = {"manifest_sha256": sha256_file(manifest_path()), "manifest_recorded_before_model_load": True,
              "imported_modules": {}, "dataset": dataset_audit(dev, spec),
              "field_extraction": field_extraction_check(dev, spec), "fixture": fixture_checks(),
              "checkpoints": {}, "skipped": SKIPPED}
    import premonition
    for module in ("premonition.model", "premonition.store", "premonition.toy_ladder", "premonition.train",
                   "premonition.answer_path"):
        path = Path(sys.modules[module].__file__) if module in sys.modules else None
        if path is None:
            __import__(module)
            path = Path(sys.modules[module].__file__)
        report["imported_modules"][module] = {"file": str(path), "sha256": sha256_file(path)}
    report["imported_modules"]["premonition"] = {"file": str(Path(premonition.__file__))}
    validation = L.load_split("validation")
    parity_names = ("long-s1-12000", "relcutlong-s0-12000")
    first_timing = None
    for panel, name, ckpt, run_json in checkpoints():
        model, record = load_checkpoint(name, ckpt, run_json)
        before = P.fingerprint(model)
        t0, rss0 = time.perf_counter(), peak_rss_bytes()
        merged = score_set(model, dev, CONDITIONS, spec)
        elapsed = time.perf_counter() - t0
        checks = {}
        equal = True
        for key in ("correct", "first_card", "ask", "restricted", "selection_changed", "handoff_attempted"):
            equal &= bool(torch.equal(merged["N"][key], merged["U"][key]))
        equal &= bool(torch.equal(merged["N"]["pred_first"], merged["U"]["pred_first"]))
        checks["n_equals_u"] = bool(equal)
        checks["q_qd_first_request_bit_identical"] = bool(
            merged["Q"]["digests"][0::REQUESTS] == merged["QD"]["digests"][0::REQUESTS]
            and torch.equal(merged["Q"]["first_card"], merged["QD"]["first_card"]))
        checks["q_qw_first_request_bit_identical"] = bool(
            merged["Q"]["digests"][0::REQUESTS] == merged["QW"]["digests"][0::REQUESTS])
        link_like = merged["QD"]["handoff_attempted"]
        first = merged["QD"]["first_card"]
        checks["handoff_only_on_link_cards"] = bool(int((link_like & (first < 0)).sum()) == 0)
        checks["q_first_link_rate"] = round(float(merged["Q"]["correct_first_link"].float().mean()), 4)
        checks["q_first_card_is_a_link"] = round(float(merged["Q"]["handoff_attempted"].float().mean()), 4)
        checks["u_first_link_rate"] = round(float(merged["U"]["correct_first_link"].float().mean()), 4)
        checks["pair_accuracy"] = {c: round(float(pair_both_correct(merged, c).float().mean()), 4)
                                   for c in CONDITIONS}
        if name in parity_names:
            checks["own_fixed_parity_validation"] = parity_against_history(model, validation)
            checks["question_filter_equivalence"] = filter_equivalence(model, validation)
        if first_timing is None:
            checks["label_perturbation"] = label_perturbation_check(model, dev, spec)
            first_timing = {"checkpoint": name, "dev_pairs": dev["pairs"],
                            "seconds_for_dev_all_conditions": round(elapsed, 3),
                            "seconds_per_prediction": round(elapsed / (2 * dev["pairs"] * len(CONDITIONS)), 5),
                            "peak_rss_bytes_before": rss0, "peak_rss_bytes_after": peak_rss_bytes()}
        after = P.fingerprint(model)
        if before != after:
            raise SystemExit(f"{name}: parameters changed during evaluation")
        record["weights_fingerprint"] = before
        record["weights_unchanged"] = True
        record["panel"] = panel
        record["checks"] = checks
        report["checkpoints"][name] = record
        print(f"{name:22s} N==U {checks['n_equals_u']}  Q/QD first request identical "
              f"{checks['q_qd_first_request_bit_identical']}  pair acc "
              f"{json.dumps(checks['pair_accuracy'])}", flush=True)
    per_prediction = first_timing["seconds_per_prediction"]
    report["timing"] = {**first_timing,
                        "extrapolated_d1_seconds": round(per_prediction * 2 * SETS["d1"]["pairs"]
                                                         * len(CONDITIONS) * 10, 1),
                        "extrapolated_one_hop_seconds": round(per_prediction * 2 * SETS["onehop"]["pairs"]
                                                              * len(ONE_HOP_CONDITIONS) * 10, 1),
                        "note": "measured on this Mac, CPU, torch.set_num_threads(4), another process may share it"}
    passes = [report["dataset"]["interpreter"]["accuracy"] == 1.0, report["field_extraction"]["pass"],
              report["fixture"]["pass"]]
    passes += [c["checks"]["n_equals_u"] and c["checks"]["q_qd_first_request_bit_identical"]
               for c in report["checkpoints"].values()]
    passes += [c["checks"]["own_fixed_parity_validation"]["pass"] for n, c in report["checkpoints"].items()
               if "own_fixed_parity_validation" in c["checks"]]
    passes += [c["checks"]["question_filter_equivalence"]["pass"] for n, c in report["checkpoints"].items()
               if "question_filter_equivalence" in c["checks"]]
    passes += [c["checks"]["label_perturbation"]["pass"] for c in report["checkpoints"].values()
               if "label_perturbation" in c["checks"]]
    report["pass"] = bool(all(passes))
    report["seconds"] = round(time.perf_counter() - started, 2)
    report["peak_rss_bytes"] = peak_rss_bytes()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "d0.json").write_text(json.dumps(report, indent=1, default=str))
    print("\nD0", "PASS" if report["pass"] else "FAIL", "-", report["seconds"], "s, peak RSS",
          report["peak_rss_bytes"], "bytes")
    print("interpreter", report["dataset"]["interpreter"]["accuracy"], "field extraction",
          report["field_extraction"]["pass"], "fixture", report["fixture"]["pass"])


# ------------------------------------------------------------------------------------------------------ D1
def _bits(mask) -> str:
    return "".join("1" if bool(x) else "0" for x in mask.tolist())


def compact_records(merged, cond) -> dict:
    return {"correct": _bits(merged[cond]["correct"]),
            "first_card": merged[cond]["first_card"].tolist(),
            "pred_first_token": merged[cond]["pred_first"].tolist(),
            "asked_request1": _bits(merged[cond]["ask"][:, 0]),
            "handoff_attempted": _bits(merged[cond]["handoff_attempted"]),
            "mask_restricted_request1": _bits(merged[cond]["restricted"][:, 0]),
            "mask_restricted_request2": _bits(merged[cond]["restricted"][:, 1]),
            "selection_changed_request2": _bits(merged[cond]["selection_changed"][:, 1]),
            "second_card": merged[cond]["second_card"].tolist(),
            "correct_first_link": _bits(merged[cond]["correct_first_link"]),
            "correct_second_answer_card": _bits(merged[cond]["correct_second_answer_card"])}


def panel_table(results: dict, conditions) -> dict:
    """Per-seed both-correct pair accuracy plus the secondary contrasts."""
    per_seed = {name: {c: round(float(results[name]["pairs"][c].float().mean()), 6) for c in conditions}
                for name in results}
    for name in results:
        per_seed[name]["single_answer"] = {c: round(float(results[name]["merged"][c]["correct"].float().mean()), 6)
                                           for c in conditions}
    return per_seed


def run_panel(spec, manifest, dataset, conditions, names_by_panel, report, tag) -> dict:
    """Score one dataset on every checkpoint, grouped by panel."""
    import torch
    out = {}
    for panel, name, ckpt, run_json in checkpoints():
        model, record = load_checkpoint(name, ckpt, run_json)
        before = P.fingerprint(model)
        t0 = time.perf_counter()
        merged = score_set(model, dataset, conditions, spec)
        after = P.fingerprint(model)
        if before != after:
            raise SystemExit(f"{name}: parameters changed during evaluation")
        pairs = {c: pair_both_correct(merged, c) for c in conditions}
        out[name] = {"panel": panel, "merged": merged, "pairs": pairs, "record": record,
                     "seconds": round(time.perf_counter() - t0, 2),
                     "n_equals_u": bool(torch.equal(merged["N"]["correct"], merged["U"]["correct"])
                                        and torch.equal(merged["N"]["first_card"], merged["U"]["first_card"])
                                        and torch.equal(merged["N"]["ask"], merged["U"]["ask"]))
                     if "N" in conditions else None}
        print(f"{tag} {name:22s} " + "  ".join(f"{c} {float(pairs[c].float().mean()):.4f}" for c in conditions),
              flush=True)
    return out


def cmd_d1(args) -> None:
    import torch
    torch.set_num_threads(4)
    spec = L.spec()
    manifest = json.loads(manifest_path().read_text())
    d0 = json.loads((OUT / "d0.json").read_text()) if (OUT / "d0.json").exists() else None
    if d0 is None or not d0.get("pass"):
        raise SystemExit("run d0 first and make it pass before scoring D1")
    primary = load_set("d1", manifest)
    one_hop = load_set("onehop", manifest)
    started = time.perf_counter()
    results = run_panel(spec, manifest, primary, CONDITIONS, PANELS, None, "d1")
    hop1 = run_panel(spec, manifest, one_hop, ONE_HOP_CONDITIONS, PANELS, None, "1hop")
    report = {"manifest_sha256": sha256_file(manifest_path()), "d0_pass": True,
              "source_sha256": sha256_file(SOURCE), "pairs": primary["pairs"],
              "predictions_per_checkpoint_condition": 2 * primary["pairs"],
              "dataset": dataset_audit(primary, spec), "one_hop_dataset": dataset_audit(one_hop, spec),
              "overlap_coverage": "not checked (train-stream fingerprint reconstruction skipped)",
              "skipped": SKIPPED, "panels": {}, "records": {}}
    for panel in PANELS:
        names = [n for n in results if results[n]["panel"] == panel]
        per_seed = {n: {c: round(float(results[n]["pairs"][c].float().mean()), 6) for c in CONDITIONS}
                    for n in names}
        per_seed_single = {n: {c: round(float(results[n]["merged"][c]["correct"].float().mean()), 6)
                               for c in CONDITIONS} for n in names}
        hop_seed = {n: {c: round(float(hop1[n]["pairs"][c].float().mean()), 6) for c in ONE_HOP_CONDITIONS}
                    for n in names}
        boot = bootstrap_delta({n: (results[n]["pairs"]["QD"], results[n]["pairs"]["Q"]) for n in names})
        boot_qw = bootstrap_delta({n: (results[n]["pairs"]["QD"], results[n]["pairs"]["QW"]) for n in names})
        boot_qu = bootstrap_delta({n: (results[n]["pairs"]["Q"], results[n]["pairs"]["U"]) for n in names})
        boot_du = bootstrap_delta({n: (results[n]["pairs"]["D"], results[n]["pairs"]["U"]) for n in names})
        audit = {n: opportunity_audit(results[n]["merged"]) for n in names}
        block = {"per_seed": per_seed, "per_seed_single_answer": per_seed_single,
                 "one_hop_per_seed": hop_seed, "bootstrap": boot,
                 "secondary": {"QD_minus_QW": boot_qw, "Q_minus_U": boot_qu, "D_minus_U": boot_du},
                 "opportunity_audit": audit,
                 "n_equals_u": all(results[n]["n_equals_u"] for n in names)
                 and all(hop1[n]["n_equals_u"] for n in names),
                 "stuck_runs_included": [n for n in names if n in STUCK],
                 "seconds": {n: results[n]["seconds"] for n in names}}
        block["advancement"] = advancement(block, {"per_seed": hop_seed}, audit)
        report["panels"][panel] = block
    for name in results:
        report["records"][name] = {c: compact_records(results[name]["merged"], c) for c in CONDITIONS}
        report["records"][name]["pair_of"] = results[name]["merged"]["_pair_of"].tolist()
        report["records"][name]["gold_link_line"] = results[name]["merged"]["_gold_link_line"].tolist()
        report["records"][name]["gold_answer_line"] = results[name]["merged"]["_gold_answer_line"].tolist()
    report["seconds"] = round(time.perf_counter() - started, 2)
    report["peak_rss_bytes"] = peak_rss_bytes()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "d1.json").write_text(json.dumps(report, indent=1, default=str))
    print_summary(report)


def print_summary(report: dict) -> None:
    for panel, block in report["panels"].items():
        print(f"\n=== {panel} panel: both-correct pair accuracy over {report['pairs']} fresh world pairs")
        head = "seed".ljust(22) + "".join(f"B({c})".rjust(10) for c in CONDITIONS) + "   QD-Q"
        print(head)
        for name, row in block["per_seed"].items():
            mark = " *stuck" if name in STUCK else ""
            print(name.ljust(22) + "".join(f"{row[c]:10.4f}" for c in CONDITIONS)
                  + f"{row['QD'] - row['Q']:8.4f}{mark}")
        b = block["bootstrap"]
        print(f"Delta = mean_s[B(QD)-B(Q)] = {b['delta']:.4f}   one-sided 99% lower {b['one_sided_99_lower']:.4f}"
              f"   upper {b['one_sided_99_upper']:.4f}   ({b['resamples']} paired world-cluster resamples)")
        print("secondary: Q-U", block["secondary"]["Q_minus_U"]["delta"], " D-U",
              block["secondary"]["D_minus_U"]["delta"], " QD-QW", block["secondary"]["QD_minus_QW"]["delta"])
        print("one-hop cell (128 pairs):", json.dumps(block["one_hop_per_seed"]))
        print("opportunity audit:")
        for name, a in block["opportunity_audit"].items():
            print(f"  {name:22s} (a) {a['a_q_first_link_correct_rate']:.4f}  (b) "
                  f"{a['b_error_rate_given_correct_first_link']:.4f}  (c) "
                  f"{a['c_wrong_members_all_d_eligible_frac_of_all_pairs']:.4f}  (d) "
                  f"{a['d_wrong_members_all_correct_bridge_frac_of_all_pairs']:.4f}")
        adv = block["advancement"]
        for key, check in adv["checks"].items():
            print(f"  {key:24s} {check['pass']}   {check.get('need', check.get('status', ''))}")
        print(f"  adequate coverage {adv['adequate_coverage']}   no-useful-effect rule "
              f"{adv['no_useful_effect_rule']['pass']}   VERDICT {adv['verdict_d1']}")
    print("\ninterpreter", report["dataset"]["interpreter"]["pair_accuracy"], "pair accuracy;",
          "shortcut ceilings", json.dumps(report["dataset"]["shortcut_ceilings"]))
    print("seconds", report["seconds"], "peak RSS bytes", report["peak_rss_bytes"])


def cmd_d2(args) -> None:
    if not args.confirm:
        raise SystemExit("D2 is sealed: pass --confirm, and only after D1 advances")
    d1 = json.loads((OUT / "d1.json").read_text()) if (OUT / "d1.json").exists() else None
    if d1 is None:
        raise SystemExit("D1 has not been scored")
    verdict = d1["panels"]["shortcut"]["advancement"]["verdict_d1"]
    if verdict != "PASS":
        raise SystemExit(f"refusing to score the sealed confirmation set: D1 verdict is {verdict}, not PASS")
    raise SystemExit("D2 scoring is intentionally not implemented in this build")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gen")
    sub.add_parser("d0")
    sub.add_parser("d1")
    two = sub.add_parser("d2")
    two.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    L.bootstrap()
    import torch
    torch.set_num_threads(4)
    {"gen": cmd_gen, "d0": cmd_d0, "d1": cmd_d1, "d2": cmd_d2}[args.cmd](args)


if __name__ == "__main__":
    main()
