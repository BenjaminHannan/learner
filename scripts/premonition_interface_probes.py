"""Eval-only (Claude, 2026-09-19): three probes of the READER -> CARD -> THINK interface of the small card toy.

Toy ladder, synthetic vocabulary, ~80k parameters, VALIDATION split only, 30 saved 12,000-step checkpoints
(baseline arm `bypass-k1` and the relation-shortcut arm). No training, no edits to existing files. The model
weights are fingerprinted before and after every probe and asserted unchanged.

  Probe A  key stability under a value-only change. For every attribute line "[world] ENT_e REL_r VAL_v f?" a
           TWIN story is built that is identical except that this one line's value token is a different value
           id (chosen deterministically from a fixed seed). The twin is re-read from scratch and its cards
           rebuilt. Reported: cosine(original KEY, twin KEY) of the edited line, the same for unedited lines
           before it (a causal reader must give exactly 1) and after it, the same for the card VALUE, and the
           retrieval consequence on the matching one-hop question (does the model's own first request still
           rank the edited line's card first?).
  Probe B  role recoverability on link lines "[world] ENT_a LINK ENT_b f?". The SAME small linear read-out the
           person probe uses (softmax regression, trained on even validation visits, scored on odd ones) tries
           to name the SUBJECT a and, separately, the OBJECT b from six places: the reader state at token a,
           at LINK, at token b, at the line's last token, the card KEY and the card VALUE. (The pooled vector
           p is not stored, so the key and the value stand in for it.) Accuracy is reported 16-way and
           "in-story" (argmax restricted to the six people in that visit, chance about 1/6).
  Probe C  which paths carry the facts? Five conditions of the standard own-retrieval evaluation (fixed 4
           loops, premonition_ovn_retrieval.own_fixed's rules) on the same trained weights:
             C0 normal; C1 cards removed (only the NULL card can be fetched); C2 story-blind question rows
             (the 40 question rows are recomputed by running the reader on the QUESTION TOKENS ALONE, fresh
             recurrent state, no story tokens in the window, while the cards are still built from the normal
             full-story read); C3 both; C4 restoration (C3 -> restore the store must reproduce C2 bit-exactly,
             C1 -> restore the store must reproduce C0 bit-exactly).
           Answer changes between conditions are counted per question, not only accuracy totals.

A failed linear read-out means "this probe could not recover it from this vector with this read-out", never
"the information is absent". Every number here is a diagnostic on one toy, not a verdict.

    PY -B scripts/premonition_interface_probes.py [--probes abc] [--out DIR] [--names N ...]
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

EDIT_SEED = 20260919
HOPS = ("one_hop", "two_hop_trained_rel", "two_hop_heldout_rel")
MANIFEST = Path("artifacts") / "opus-ovn-20260918-235851" / "exp1" / "data" / "manifest.json"
NEEDED = ("premonition_first_card_probe.py", "premonition_person_probe.py", "premonition_ovn_retrieval.py")


def repo_root() -> Path:
    """The checkout that actually holds the frozen data, the checkpoints and the probe scripts this one reuses.

    `artifacts/` is git-ignored and several sibling probes are untracked, so a git worktree of this repo has
    only part of what is needed; the working root is then the main checkout further up the path.
    """
    here = Path(__file__).resolve().parents[1]
    for candidate in (here, *here.parents):
        if (candidate / MANIFEST).exists() and all((candidate / "scripts" / n).exists() for n in NEEDED):
            return candidate
    raise SystemExit(f"cannot find {MANIFEST} plus {NEEDED} at or above {here}")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_first_card_probe as P  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_person_probe as PP  # noqa: E402

L = P.L


def use_repo_root(root: Path) -> None:
    """Point the ladder harness at `root` (it derives its paths from its own file location)."""
    L.ROOT = root
    L.ARCHIVE = root / "archive" / f"opus-{L.RUN}"
    L.OUT = root / "artifacts" / f"opus-{L.RUN}" / "exp1"


def arms(root: Path) -> dict:
    """The 30 saved 12,000-step checkpoints. `stuck` = one-hop own retrieval < 384/512 (given)."""
    return {
        "baseline": {"dir": root / "artifacts" / "claude-long-20260919" / "ckpt",
                     "name": lambda s: f"long-s{s}-12000", "seeds": tuple(range(15)),
                     "stuck": (0, 8, 12, 13)},
        "shortcut": {"dir": root / "artifacts" / "claude-relcut-long-20260919" / "ckpt",
                     "name": lambda s: f"relcutlong-s{s}-12000", "seeds": tuple(range(15)),
                     "stuck": (1, 2, 6, 7, 8, 9, 14)},
    }


def checkpoints(root: Path) -> list[dict]:
    out = []
    for arm, info in arms(root).items():
        for seed in info["seeds"]:
            out.append({"arm": arm, "seed": seed, "name": info["name"](seed), "dir": str(info["dir"]),
                        "group": "stuck" if seed in info["stuck"] else "learned"})
    return out


# --------------------------------------------------------------------------------------------- line structure
def line_kind(batch, spec, visit: int, line: int) -> str:
    """'attr' | 'link' | 'filler' | 'question' | 'none' for one line of one visit, from the visible tokens only.

    A story line is "[world] <subject> <relation|LINK> <value|object> <filler*> \\n" for facts and links and
    "[world] <filler+> \\n" for fillers, so the second token decides.
    """
    start = int(batch.line_start[visit, line])
    if start < 0:
        return "none"
    if bool(batch.line_is_question[visit, line]):
        return "question"
    subject = int(batch.tokens[visit, start + 1]) - spec.vocab_size
    if subject < 0:
        return "filler"
    middle = int(batch.tokens[visit, start + 2])
    if middle == spec.link:
        return "link"
    if spec.relation(0) <= middle < spec.relation(spec.relations):
        return "attr"
    return "filler"


def lines_of_kind(batch, spec, kind: str) -> list[list[int]]:
    """Per visit, the line indices of that kind, in story order."""
    visits, lines = batch.line_start.shape
    return [[line for line in range(lines) if line_kind(batch, spec, v, line) == kind] for v in range(visits)]


# --------------------------------------------------------------------------------------------- probe A plumbing
def replacement_value(spec, old: int, *, key: str, seed: int = EDIT_SEED) -> int:
    """A different value id, chosen deterministically from `seed` and `key` (never equal to `old`)."""
    digest = hashlib.blake2s(f"{seed}|{key}".encode(), digest_size=8).digest()
    offset = 1 + int.from_bytes(digest, "big") % (spec.values - 1)
    return (old + offset) % spec.values


def twin_batch(batch, spec, edits: list[tuple[int, int]], *, tag: str, seed: int = EDIT_SEED):
    """A copy of `batch` in which, for each (visit, line) in `edits`, ONLY that attribute line's value token is
    replaced by a different value id. Returns (twin, [(visit, line, position, old_v, new_v)]).

    Every other field of the batch is positional (line_of, line_start, card_end, lm_mask, q_span, line_ents)
    and is therefore unchanged by a value swap; line lengths are identical. NOTE: `batch.answer` still holds
    the ORIGINAL gold value, so a twin's answer labels for questions about the edited (e, r) are stale --
    probe A never scores answers, only keys, values and which card is requested.
    """
    tokens = batch.tokens.clone()
    done = []
    for visit, line in edits:
        start = int(batch.line_start[visit, line])
        position = start + 3
        old = int(batch.tokens[visit, position]) - spec.value(0)
        if not 0 <= old < spec.values:
            raise ValueError(f"line {line} of visit {visit} has no value token at +3")
        new = replacement_value(spec, old, key=f"{tag}|{visit}|{line}", seed=seed)
        tokens[visit, position] = spec.value(new)
        done.append((visit, line, position, old, new))
    if not done:
        return batch, done
    assert int((tokens != batch.tokens).sum()) == len(done), "a twin changed more than one token per edit"
    return replace(batch, tokens=tokens), done


# ------------------------------------------------------------------------------------ probe C plumbing (C1/C2/C4)
def ablate_cards(store):
    """C1: a store in which no fact card is eligible. NULL stays eligible -- it is not a line of the story but
    a parameter of the card writer, and `CardStore.eligible` always keeps its column."""
    import torch
    return replace(store, valid=torch.zeros_like(store.valid))


def question_local_index(batch, rows_q: int):
    """[Q, rows_q] long: for each of the model's question rows, its offset inside the question span.

    `PremonitionMini._start` fills the question rows from absolute token positions `end - rows_q + j` and marks
    them valid where that is >= `start`; the offset is therefore `(end - start) - rows_q + j`, negative exactly
    where the row is invalid.
    """
    import torch
    start, end = batch.q_span[:, 0], batch.q_span[:, 1]
    j = torch.arange(rows_q, device=start.device)
    return (end - start).unsqueeze(1) - rows_q + j


def question_tokens_only(batch, pad_id: int):
    """[Q, Lmax] long: each question's own span tokens at positions 0.., PAD after. Right padding cannot reach
    earlier positions: the reader is causal (minGRU scan, block-local causal attention)."""
    import torch
    start, end = batch.q_span[:, 0], batch.q_span[:, 1]
    span = end - start
    width = int(span.max())
    j = torch.arange(width, device=start.device)
    inside = j.unsqueeze(0) < span.unsqueeze(1)
    gathered = batch.tokens[batch.q_visit.unsqueeze(1),
                            (start.unsqueeze(1) + j).clamp(max=batch.tokens.shape[1] - 1)]
    return torch.where(inside, gathered, torch.full_like(gathered, pad_id))


def story_blind_question_hidden(model, batch):
    """[Q, Lmax, d] reader states of each question read ALONE: fresh recurrent state, rope positions from 0,
    no story token anywhere in the attention window."""
    return model.reader(model.embed(question_tokens_only(batch, model.config.pad_id)))


def question_rows_from_story(model, batch, hidden):
    """[Q, Lmax, d] the SAME gather, but from the normal full-story read: passing this to `set_question_rows`
    must leave the episode unchanged (the plumbing test of the index arithmetic)."""
    import torch
    start = batch.q_span[:, 0]
    width = int((batch.q_span[:, 1] - start).max())
    j = torch.arange(width, device=start.device)
    return hidden[batch.q_visit.unsqueeze(1), (start.unsqueeze(1) + j).clamp(max=hidden.shape[1] - 1)].float()


def question_row_valid(batch, rows_q):
    """[Q, rows_q] bool: the question rows `_start` marks valid (position >= the span's start). The rest are
    padding rows that every attention mask in Think and in the decoder excludes."""
    return question_local_index(batch, rows_q) >= 0


def set_question_rows(model, batch, episode, source):
    """Overwrite the episode's VALID question rows from `source` [Q, Lmax, d] (indexed by offset inside the
    span), exactly as `_start` builds them; padding rows are left as they were. Returns the previous rows so
    the edit can be undone bit-exactly."""
    import torch
    from premonition.model import ROW_QUESTION
    rows_q = model.config.question_rows
    local = question_local_index(batch, rows_q)
    rows = source[torch.arange(source.shape[0], device=source.device).unsqueeze(1), local.clamp_min(0)].float()
    rows = rows + model.think.row_type.weight[ROW_QUESTION].float()
    previous = episode.x[:, :rows_q].clone()
    x = episode.x.clone()
    x[:, :rows_q] = torch.where((local >= 0).unsqueeze(-1), rows, previous)
    episode.x = x
    return previous


def restore_question_rows(episode, previous) -> None:
    x = episode.x.clone()
    x[:, :previous.shape[1]] = previous
    episode.x = x


def condition(model, batch, loops: int = 4, *, no_cards: bool = False, story_blind: bool = False,
              restore_cards: bool = False, restore_question: bool = False, spy: dict | None = None):
    """`premonition_ovn_retrieval.own_fixed`'s evaluation with the probe-C interventions.

    no_cards         C1: the store offers only the NULL card.
    story_blind      C2: the question rows come from reading the question tokens alone.
    restore_cards    C4: ablate the store and then put the real one back (exercises the ablation code).
    restore_question C4: apply the story-blind rows and then undo them.
    `spy` (optional) collects intermediate tensors for the unit tests.
    Returns (ok [Q] bool, answers [Q, max_answer] long, all_gold_fetched [Q] bool, fetched [Q, L+1] bool).
    """
    import torch
    from learnlab.core import IGNORE_INDEX
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    if store is not None:
        if no_cards:
            store = ablate_cards(store)
        elif restore_cards:                      # ablate, then restore: the C4 round trip
            store = replace(ablate_cards(store), valid=store.valid)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    if spy is not None:
        spy["question_rows_before"] = episode.x[:, :model.config.question_rows].clone()
    if story_blind or restore_question:
        previous = set_question_rows(model, batch, episode, story_blind_question_hidden(model, batch))
        if restore_question:
            restore_question_rows(episode, previous)
    if spy is not None:
        spy["question_rows_after"] = episode.x[:, :model.config.question_rows].clone()
        spy["store"] = store
        spy["requests"] = []
    everyone = torch.arange(batch.q_visit.shape[0])
    for step in range(loops):
        rows, halt, ask, scores = model._step(episode, everyone, step, store)
        if store is not None and step + 1 < loops:
            cards = store.top(scores, model.config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
            if spy is not None:
                spy["requests"].append(cards.clone())
            model._insert(episode, store, everyone, cards)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    gold_ids = [batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist() for q in range(batch.answer.shape[0])]
    ok = torch.tensor([tokens[q, :int(lengths[q])].tolist() == gold_ids[q] for q in range(len(gold_ids))])
    answers = torch.where(torch.arange(tokens.shape[1]).unsqueeze(0) < lengths.unsqueeze(1), tokens,
                          torch.full_like(tokens, model.config.pad_id))
    if spy is not None:
        spy["episode"] = episode
    if store is None:
        return ok, answers, torch.zeros_like(ok), None
    gold = batch.gold_lines
    fetched = episode.fetched.gather(1, gold.clamp_min(0)) | (gold < 0)
    return ok, answers, fetched.all(1), episode.fetched


def hop_masks(hops, batch) -> dict:
    held = batch.slices["heldout"]
    return {"one_hop": hops == 1, "two_hop_trained_rel": (hops == 2) & ~held,
            "two_hop_heldout_rel": (hops == 2) & held}


def answer_frequency_chance(items) -> dict:
    """Per question type: the validation answer distribution and the best constant-answer accuracy -- the real
    chance level for a model that has lost every story-derived path. It is 1/16 only if answers are uniform."""
    from learnlab.core import IGNORE_INDEX
    counts = {h: Counter() for h in HOPS}
    for batch, _, hops in items:
        masks = hop_masks(hops, batch)
        for q in range(batch.answer.shape[0]):
            ids = tuple(batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist())
            for h in HOPS:
                if bool(masks[h][q]):
                    counts[h][ids] += 1
    out = {}
    for h in HOPS:
        n = sum(counts[h].values())
        k = counts[h].most_common(1)[0][1] if n else 0
        out[h] = {"n": n, "distinct_answers": len(counts[h]), "most_common_count": k,
                  "best_constant_answer_acc": round(k / max(n, 1), 4),
                  "uniform_1_over_16": round(1.0 / 16, 4)}
    return out


# --------------------------------------------------------------------------------------------- the three probes
def probe_a(model, items, spec) -> dict:
    """Key/value stability under a value-only edit, plus the retrieval consequence."""
    import torch
    import torch.nn.functional as F
    places = ("edited", "prev_line", "next_line", "before_mean", "after_mean")
    cos = {f"{side}_{where}": [] for side in ("key", "value") for where in places}
    worst_before = {"key": 1.0, "value": 1.0}
    n_edits = 0
    with torch.no_grad():
        for index, (batch, supplied, hops) in enumerate(items):
            tag = f"b{index}"
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            attrs = lines_of_kind(batch, spec, "attr")
            cards = [[line for line in range(batch.line_start.shape[1]) if bool(store.valid[v, line])]
                     for v in range(batch.line_start.shape[0])]
            for slot in range(max(len(a) for a in attrs)):
                edits = [(v, attrs[v][slot]) for v in range(len(attrs)) if slot < len(attrs[v])]
                twin, done = twin_batch(batch, spec, edits, tag=tag)
                twin_store = model.build_store(model.read(twin), twin)
                for visit, line, _, _, _ in done:
                    n_edits += 1
                    for side, a, b in (("key", store.keys, twin_store.keys),
                                       ("value", store.values, twin_store.values)):
                        def same(i, a=a, b=b, visit=visit):
                            return float(F.cosine_similarity(a[visit, i].float(), b[visit, i].float(), dim=0))
                        cos[f"{side}_edited"].append(same(line))
                        before = [same(i) for i in cards[visit] if i < line]
                        after = [same(i) for i in cards[visit] if i > line]
                        if before:
                            cos[f"{side}_prev_line"].append(before[-1])
                            cos[f"{side}_before_mean"].append(sum(before) / len(before))
                            worst_before[side] = min(worst_before[side], min(before))
                        if after:
                            cos[f"{side}_next_line"].append(after[0])
                            cos[f"{side}_after_mean"].append(sum(after) / len(after))
    report = {"n_edited_lines": n_edits,
              "cosine": {k: {"mean": round(sum(v) / len(v), 6), "min": round(min(v), 6),
                             "max": round(max(v), 6), "n": len(v)} for k, v in cos.items() if v},
              "causal_selfcheck_min_cosine_before_edit": {k: round(v, 9) for k, v in worst_before.items()}}
    for side in ("key", "value"):
        values = cos[f"{side}_edited"]
        report["cosine"][f"{side}_edited"]["frac_ge_0.99"] = round(
            sum(1 for c in values if c >= 0.99) / max(len(values), 1), 4)
    report["retrieval_consequence_one_hop"] = probe_a_retrieval(model, items, spec)
    return report


def first_request(model, batch):
    """[Q] line index of the model's own first request (ungated top-1 eligible card; `store.lines` = NULL,
    -1 = nothing eligible) and [Q] bool whether it actually asked (ASK logit > 0)."""
    import torch
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    rows, halt, ask, scores = model._step(episode, torch.arange(batch.q_visit.shape[0]), 0, store)
    return store.top(scores, 1)[:, 0], ask > 0


def probe_a_retrieval(model, items, spec) -> dict:
    """For each one-hop question, edit ITS gold line's value and ask whether the model's own first request still
    ranks that line's card first."""
    import torch
    hit_original = hit_twin = changed = asked_original = asked_twin = n = 0
    with torch.no_grad():
        for index, (batch, supplied, hops) in enumerate(items):
            base_top, base_ask = first_request(model, batch)
            per_visit: dict[int, list[int]] = {}
            for q in (hops == 1).nonzero().flatten().tolist():
                per_visit.setdefault(int(batch.q_visit[q]), []).append(q)
            for slot in range(max(len(v) for v in per_visit.values())):
                group = [(v, qs[slot]) for v, qs in per_visit.items() if slot < len(qs)]
                edits = [(v, int(batch.gold_lines[q, 0])) for v, q in group]
                twin, _ = twin_batch(batch, spec, edits, tag=f"b{index}")
                twin_top, twin_ask = first_request(model, twin)
                for v, q in group:
                    gold = int(batch.gold_lines[q, 0])
                    n += 1
                    hit_original += int(int(base_top[q]) == gold)
                    hit_twin += int(int(twin_top[q]) == gold)
                    changed += int(int(base_top[q]) != int(twin_top[q]))
                    asked_original += int(bool(base_ask[q]))
                    asked_twin += int(bool(twin_ask[q]))
    return {"n_questions": n, "top1_is_gold_original": hit_original, "top1_is_gold_twin": hit_twin,
            "top1_changed_identity": changed, "asked_original": asked_original, "asked_twin": asked_twin,
            "note": "ungated top-1 of the eligible cards at loop 0; the ASK gate is counted separately"}


def probe_b(model, items, spec) -> dict:
    """Subject / object recoverability on link lines, from six places."""
    import torch
    n_ent = model.config.n_ent
    sources = ("state_subject_token", "state_link_token", "state_object_token", "state_line_end",
               "card_key", "card_value")
    feats = {s: [] for s in sources}
    subject, obj, fold, visit_id = [], [], [], []
    present: dict[int, torch.Tensor] = {}
    base = 0
    with torch.no_grad():
        for batch, supplied, hops in items:
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            entity = batch.tokens - spec.vocab_size
            is_entity = (entity >= 0) & (entity < n_ent)
            for v in range(batch.line_start.shape[0]):
                here = torch.zeros(n_ent, dtype=torch.bool)
                here[entity[v][is_entity[v]]] = True
                present[base + v] = here
            for v, lines in enumerate(lines_of_kind(batch, spec, "link")):
                for line in lines:
                    if not bool(store.valid[v, line]):
                        continue
                    start = int(batch.line_start[v, line])
                    last = start + int(store.line_len[v, line]) - 1
                    feats["state_subject_token"].append(hidden[v, start + 1].float())
                    feats["state_link_token"].append(hidden[v, start + 2].float())
                    feats["state_object_token"].append(hidden[v, start + 3].float())
                    feats["state_line_end"].append(hidden[v, last].float())
                    feats["card_key"].append(store.keys[v, line].float())
                    feats["card_value"].append(store.values[v, line].float())
                    subject.append(int(batch.tokens[v, start + 1]) - spec.vocab_size)
                    obj.append(int(batch.tokens[v, start + 3]) - spec.vocab_size)
                    fold.append((base + v) % 2)
                    visit_id.append(base + v)
            base += batch.line_start.shape[0]
    f = torch.tensor(fold)
    mask = torch.stack([present[i] for i in visit_id])
    report = {"n_link_lines": len(subject), "n_train": int((f == 0).sum()), "n_test": int((f == 1).sum()),
              "classes": n_ent, "people_per_story": int(mask[0].sum()),
              "chance_in_story": round(1.0 / int(mask[0].sum()), 4), "read_out": {}}
    for source in sources:
        x = torch.stack(feats[source])
        entry = {"dim": int(x.shape[1])}
        for role, labels in (("subject", subject), ("object", obj)):
            y = torch.tensor(labels)
            acc16, in_story = PP.readout(x[f == 0], y[f == 0], x[f == 1], y[f == 1], mask[f == 1], n_ent)
            entry[role] = {"acc16": acc16, "acc_in_story": in_story}
        report["read_out"][source] = entry
    return report


CONDITIONS = {"C0_normal": {}, "C1_cards_removed": {"no_cards": True},
              "C2_story_blind_question": {"story_blind": True},
              "C3_both": {"no_cards": True, "story_blind": True},
              "C4a_from_C3_restore_store": {"story_blind": True, "restore_cards": True},
              "C4b_from_C1_restore_store": {"restore_cards": True}}


def probe_c(model, items) -> dict:
    """C0..C4 with per-question answer bookkeeping."""
    import torch
    per = {name: {"ok": [], "answers": [], "gold": [], "fetched_real": []} for name in CONDITIONS}
    masks = {h: [] for h in HOPS}
    with torch.no_grad():
        for batch, supplied, hops in items:
            for h, m in hop_masks(hops, batch).items():
                masks[h].append(m)
            for name, kwargs in CONDITIONS.items():
                ok, answers, gold, fetched = condition(model, batch, 4, **kwargs)
                per[name]["ok"].append(ok)
                per[name]["answers"].append(answers)
                per[name]["gold"].append(gold)
                per[name]["fetched_real"].append(
                    fetched[:, :-1].any(1) if fetched is not None else torch.zeros_like(ok))
    masks = {h: torch.cat(v) for h, v in masks.items()}
    for name in per:
        for key in per[name]:
            per[name][key] = torch.cat(per[name][key])
    report = {"conditions": {}, "restoration": {}, "answer_changes": {}}
    for name in CONDITIONS:
        entry = {}
        for h in HOPS:
            m = masks[h]
            k, n = int(per[name]["ok"][m].sum()), int(m.sum())
            entry[h] = {"correct": k, "n": n, "acc": round(k / max(n, 1), 4), "wilson95": L.wilson(k, n),
                        "all_gold_fetched": int(per[name]["gold"][m].sum()),
                        "fetched_any_real_card": int(per[name]["fetched_real"][m].sum())}
        report["conditions"][name] = entry
    for label, a, b in (("C4a_equals_C2", "C4a_from_C3_restore_store", "C2_story_blind_question"),
                        ("C4b_equals_C0", "C4b_from_C1_restore_store", "C0_normal")):
        report["restoration"][label] = {
            "answers_bit_identical": bool(torch.equal(per[a]["answers"], per[b]["answers"])),
            "ok_bit_identical": bool(torch.equal(per[a]["ok"], per[b]["ok"])),
            "n_answers_differing": int((per[a]["answers"] != per[b]["answers"]).any(1).sum())}
    for x, y in (("C0_normal", "C1_cards_removed"), ("C0_normal", "C2_story_blind_question"),
                 ("C0_normal", "C3_both"), ("C1_cards_removed", "C3_both"),
                 ("C2_story_blind_question", "C3_both")):
        differ = (per[x]["answers"] != per[y]["answers"]).any(1)
        flips = {}
        for h in HOPS:
            m = masks[h]
            flips[h] = {"answer_changed": int(differ[m].sum()), "n": int(m.sum()),
                        "correct_to_wrong": int((per[x]["ok"] & ~per[y]["ok"])[m].sum()),
                        "wrong_to_correct": int((~per[x]["ok"] & per[y]["ok"])[m].sum())}
        report["answer_changes"][f"{x}__vs__{y}"] = flips
    return report


# --------------------------------------------------------------------------------------------- driver
def slot_and_register_audit(model, items) -> dict:
    """Code-level check behind the C2/C3 claim about the non-question think rows: the entity-slot CONTENT and
    the register CONTENT are parameters only (no story tensor enters them), while the slot VALIDITY mask is
    story-derived (`_mentions` counts entity tokens), so C2/C3 do not cut that one channel."""
    import torch
    config = model.config
    with torch.no_grad():
        batch = items[0][0]
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        mentions = model._mentions(batch)
        episode = model._start(batch, hidden, store, mentions)
        slots = episode.x[:, config.question_rows:config.question_rows + config.slots]
        want = (model.embed.weight[config.vocab_size:config.vocab_size + config.n_ent].float()
                + model.think.row_type.weight[1].float())
        regs = episode.x[:, config.question_rows + config.slots + config.cards:]
        want_regs = model.think.register.weight.float() + model.think.row_type.weight[3].float()
        blank = replace(batch, tokens=torch.zeros_like(batch.tokens))
        other = model._start(blank, model.read(blank), store, mentions)
    return {"slot_rows_are_entity_embeddings_only": bool(torch.allclose(slots, want.expand_as(slots))),
            "register_rows_are_parameters_only": bool(torch.allclose(regs, want_regs.expand_as(regs))),
            "slot_rows_unchanged_when_story_tokens_are_zeroed":
                bool(torch.equal(slots, other.x[:, config.question_rows:config.question_rows + config.slots])),
            "slot_validity_mask_is_story_derived": True,
            "entities_marked_present_per_question": sorted(set(mentions.sum(1).tolist())),
            "n_ent": config.n_ent,
            "caveat": "C2/C3 leave the slot validity mask (which of the 16 entity ids occur in the visit) in "
                      "place, as specified; that channel carries the visit's cast, not its facts."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probes", default="abc")
    parser.add_argument("--out", default=None)
    parser.add_argument("--names", nargs="*", default=None, help="limit to these checkpoint names")
    parser.add_argument("--threads", type=int, default=6)
    args = parser.parse_args()
    root = ROOT
    use_repo_root(root)
    L.bootstrap()
    import torch
    torch.set_num_threads(args.threads)
    out = Path(args.out) if args.out else root / "artifacts" / "claude-interface-probes-20260919"
    out.mkdir(parents=True, exist_ok=True)
    spec = L.spec()
    items = L.load_split("validation")
    todo = [c for c in checkpoints(root) if args.names is None or c["name"] in args.names]
    header = {"split": "validation", "generated": time.strftime("%Y-%m-%d %H:%M:%S"), "repo_root": str(root),
              "note": "toy ladder, synthetic vocabulary, ~80k parameters, eval only; diagnostics, not verdicts",
              "edit_seed": EDIT_SEED, "loops": 4,
              "answer_frequency_chance": answer_frequency_chance(items), "checkpoints": todo}
    results = {p: {**header, "results": {}} for p in "abc" if p in args.probes}
    started = time.perf_counter()
    for c in todo:
        t0 = time.perf_counter()
        model, blob = P.load_from(c["name"], c["dir"])
        before = P.fingerprint(model)
        if "c" in results and "slot_and_register_audit" not in results["c"]:
            results["c"]["slot_and_register_audit"] = slot_and_register_audit(model, items)
        for probe, fn in (("a", lambda: probe_a(model, items, spec)),
                          ("b", lambda: probe_b(model, items, spec)),
                          ("c", lambda: probe_c(model, items))):
            if probe in results:
                results[probe]["results"][c["name"]] = {"arm": c["arm"], "seed": c["seed"],
                                                        "group": c["group"], **fn()}
        assert P.fingerprint(model) == before, f"{c['name']} changed during an eval-only probe"
        print(f"{c['name']} ({c['arm']}/{c['group']}) {time.perf_counter() - t0:.1f} s", flush=True)
    for probe, payload in results.items():
        payload["seconds"] = round(time.perf_counter() - started, 2)
        (out / f"probe_{probe}.json").write_text(json.dumps(payload, indent=1, default=str))
    print(f"total {time.perf_counter() - started:.1f} s -> {out}", flush=True)


if __name__ == "__main__":
    main()
