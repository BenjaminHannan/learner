#!/usr/bin/env python3
"""Experiment 130 -- registered single-change follow-up to exp 115: grow ONE word slot.

Evidence from 115: sleep installs up to 3 new relations (one sleep or two, no
forgetting, 0 wrong, 15/15 probes) but relations 4 and 5 (boss_of_father,
teacher_of_spouse) cannot install because the reasoner (R44) has exactly 3
learned word slots, so no episodes queue and the model honestly abstains.

THE ONE CHANGE (everything else -- episode collection, gate, install check,
daemon wiring -- unchanged): when every word slot is taken, the sleep may ADD
one new word slot: grow the word/code table by one row, initialised by the
same rule the recipe uses for its existing slots (torch.zeros, exactly as
Reasoner.__init__ builds words), and train only the new row with the certified
recipe (robust loss eps=0.10, harden to argmax +/-30 after each fold fit and
the refit, 4-fold CV gate OOF >= 0.80, refit agreement >= 0.90, old skills
unchanged, reload identical). Every existing slot and skill weight is frozen
-- verified by hashing their tensors before/after each sleep.

Additive only (nothing outside this file is edited; everything else is
imported read-only and wrapped/subclassed):

  Sleep130Ears      Sleep115Ears with PERSON_HOPS extended to father/teacher
                    (the new chains' hops; same force-entity rule, rest passed
                    through untouched).
  Sleep130Reasoner  Sleep115Reasoner with the word table extended to WORDS130
                    (first 3 identical to 115; then boss_of_father,
                    teacher_of_spouse, then the G4 climb words). Queue rule,
                    sleep-derived marking, and trail heading are the 115 rule
                    verbatim. The live reasoner words dict is unbounded, so no
                    growth is needed there -- only the episode feed is widened.
  GrowModel         the R44 Reasoner maths with K word slots (K >= 3):
                    identical stage_table/effective/run_tape/predict/encode
                    formulae, generalised to K rows. K == 3 reproduces R44
                    exactly (asserted in the drive smoke).
  fit_word_grow / sleep_word_grow
                    the certified recipe on the new row only: same optimiser
                    (Adam, SLEEP_LR), batch, snapshots, robust loss, harden,
                    folds, floors, and gate order as R44.sleep_word via the
                    hardgate46 patch. All other rows require no grad.
  Sleep130Sleeper   Sleep115Sleeper: when every requested word has a free slot
                    (w < 3 and no grown slot exists) it delegates to the
                    115/wire57 _run_exp46 untouched (byte-identical path, the
                    G3 guarantee). Otherwise each new word is trained by
                    sleep_word_grow on a table grown by exactly one zero row,
                    with pre/post sha256 of every frozen tensor recorded in
                    the recipe row (frozen_ok). Bridge/report/persist extend
                    the 115 commit to WORDS130 (atomic multi-word file).
  Sleep130Daemon / build_agent130 / retrofit_sleep130
                    the 115 daemon shape with the 130 trio + per-turn sleep
                    logging (one log row per SLEEP tick).

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep130_agent.py --daemon --dir DIR --config CFG
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox helpers, read-only)
import fable_loop90_agent as L90  # noqa: E402 (loop90 build, read-only)
import fable_loop96_agent as L96  # noqa: E402 (loop96 build, read-only)
import fable_notebook_contract as C  # noqa: E402 (contract, read-only)
import fable_sleep115_agent as S115  # noqa: E402 (115 trio, read-only)
import fable_wire57_e2e as W57  # noqa: E402 (sparse-village sleeper, read-only)

# ---------------------------------------------------------------------------
# The extended word table. First 3 entries are 115 verbatim (G3 guarantee);
# entries 4-5 are the registered G1 targets; entries 6-11 are the
# unregistered G4 climb only. All chains use the 8 sealed R44 skills.
WORDS130 = (
    "maternal_grandmother",      # 0  mother+mother            [1,1]
    "boss_of_spouse",            # 1  spouse+boss              [3,4]
    "doctor_of_mothers_friend",  # 2  mother+best_friend+doc   [1,5,7]
    "boss_of_father",            # 3  father+boss              [2,4]
    "teacher_of_spouse",         # 4  spouse+teacher           [3,8]
    "mother_of_spouse",          # 5  spouse+mother            [3,1]  (G4)
    "boss_of_mother",            # 6  mother+boss              [1,4]  (G4)
    "teacher_of_father",         # 7  father+teacher           [2,8]  (G4)
    "doctor_of_spouse",          # 8  spouse+doctor            [3,7]  (G4)
    "father_of_mother",          # 9  mother+father            [1,2]  (G4)
    "doctor_of_boss",            # 10 boss+doctor              [4,7]  (G4)
    "teacher_of_mother",         # 11 mother+teacher           [1,8]  (G4)
)
CHAINS130 = (
    ("mother", "mother"),
    ("spouse", "boss"),
    ("mother", "best_friend", "doctor"),
    ("father", "boss"),
    ("spouse", "teacher"),
    ("spouse", "mother"),
    ("mother", "boss"),
    ("father", "teacher"),
    ("spouse", "doctor"),
    ("mother", "father"),
    ("boss", "doctor"),
    ("mother", "teacher"),
)
RELATIONS130 = S115.RELATIONS  # the 8 sealed skills, unchanged
EXPECTED_SKILLS130 = tuple(
    tuple(RELATIONS130.index(r) + 1 for r in c) for c in CHAINS130)
assert WORDS130[:3] == S115.WORDS
assert CHAINS130[:3] == S115.CHAINS
assert EXPECTED_SKILLS130[:3] == S115.EXPECTED_SKILLS
PERSON_HOPS130 = S115.PERSON_HOPS | {"father", "teacher"}
ASK130 = {w: w.replace("_", " ") for w in WORDS130}

WORD_FILE130 = "sleep130-words.json"
MARKER130 = "sleep130-SLEEPING"
REPORT_RELATION130 = "sleep_report"  # same contract relation as 115/52
SLEEP_ENTITY130 = "SLEEP130"
BASE_PT130 = S115.BASE_PT
N_BASE_SLOTS = 3  # sealed R44 N_WORDS; slots 0-2 train the 115 path


# ---------------------------------------------------------------------- ears
class Sleep130Ears(S115.Sleep115Ears):
    """115 ears with father/teacher added to the entity-valued teach rule."""

    def hear(self, turn: str) -> list[dict]:
        actions = self.inner.hear(turn)
        for action in actions:
            if (isinstance(action, dict)
                    and action.get("act") in ("teach", "correct")
                    and action.get("relation") in PERSON_HOPS130
                    and not action.get("is_person")):
                action["is_person"] = True
                self.forced += 1
        return actions


# ------------------------------------------------------------------ reasoner
class Sleep130Reasoner(S115.Sleep115Reasoner):
    """115 episode feed + marks over the extended word table (115 rule verbatim)."""

    WORDS = WORDS130
    CHAINS = CHAINS130

    def _queue130(self, word: str, w: int, name: str,
                  entity_id: str | None, notebook) -> None:
        start = entity_id
        if start is None:
            found = notebook.resolve(name)
            if found.status != C.OK:
                return
            start = found.detail["entity_id"]
        cur, ok = start, True
        for rel in CHAINS130[w]:
            rows = notebook.current(cur, rel)
            if len(rows) < 1 or "entity" not in rows[0]["value"]:
                ok = False
                break
            cur = rows[0]["value"]["entity"]
        if ok:
            self.episodes.append({"start": start, "word": w,
                                  "word_name": word, "answer": cur})

    def answer(self, question: dict, notebook) -> dict:
        relations = list(question.get("relations") or [])
        w = None
        if len(relations) == 1 and relations[0] in WORDS130:
            w = WORDS130.index(relations[0])
            self._queue130(relations[0], w, question.get("name", ""),
                           question.get("entity_id"), notebook)
        rec = self.inner.answer(question, notebook)
        if (w is not None and rec.get("status") == C.OK
                and self.installed(WORDS130[w])
                and rec.get("fields", {}).get("source") == "taught"):
            rec = dict(rec)
            fields = dict(rec.get("fields", {}))
            fields["source"] = "sleep-derived"
            trail = list(fields.get("trail", []))
            fid = self.report_fids.get(WORDS130[w])
            if fid and fid not in trail:
                trail = [fid] + trail
            fields["trail"] = trail
            fields["sleep_word"] = WORDS130[w]
            rec["fields"] = fields
        return rec


def check_word_logits130(logits, w: int) -> bool:
    """Hardened [3][9] rows: non-keep stages (row order) == chain skills."""
    try:
        if len(logits) != 3 or any(len(r) != 9 for r in logits):
            return False
        if not (0 <= w < len(EXPECTED_SKILLS130)):
            return False
        arg = [max(range(9), key=lambda i: r[i]) for r in logits]
        skills = [a for a in arg if a != 0]
        return skills == list(EXPECTED_SKILLS130[w])
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------- frozen hashing
def tensor_hash(t) -> str:
    import torch
    return hashlib.sha256(
        t.detach().to(torch.float32).cpu().numpy().tobytes()).hexdigest()


def state_hashes(state: dict, frozen_keys: list[str]) -> dict[str, str]:
    return {k: tensor_hash(state[k]) for k in frozen_keys if k in state}


# ------------------------------------------------- the growable R44 maths
def _r44():
    import fable_reasoner44 as R44
    import fable_hardgate46  # noqa: F401 -- installs the certified patch
    import fable_noisyteacher45 as N45
    return R44, N45


def grow_pad_stage(k: int) -> int:
    R44, _ = _r44()
    return R44.R + R44.STAGES * k


def encode_grow(R44, v, qs, k: int) -> tuple:
    import torch
    pad = grow_pad_stage(k)
    seqs = [[s for t in q.tokens for s in R44.token_stages(t)] for q in qs]
    length = max(len(s) for s in seqs)
    stages = torch.full((len(qs), length), pad, dtype=torch.long)
    for i, s in enumerate(seqs):
        stages[i, :len(s)] = torch.tensor(s, dtype=torch.long)
    starts = torch.tensor([v.idx[q.start] for q in qs], dtype=torch.long)
    targets = torch.tensor(
        [v.idx[q.answer] if q.answer is not None else v.n for q in qs],
        dtype=torch.long)
    return starts, stages, targets


class GrowModelMixin:
    """Identical maths to R44.Reasoner.stage_table/effective, K slots."""

    def stage_table(self):  # type: ignore[no-redef]
        import torch
        base = torch.cat(
            (torch.zeros(self._R, 1),
             self.token_logits.softmax(-1)), 1)
        words = torch.stack(
            [w.softmax(-1) for w in self.words]).reshape(
            len(self.words) * self._STAGES, self._R + 1)
        pad = torch.zeros(1, self._R + 1)
        pad[0, 0] = 1.0
        return torch.cat((base, words, pad), 0)

    def effective(self, m):  # type: ignore[no-redef]
        import torch
        return torch.einsum("sc,cij->sij", self.stage_table(), m)


def make_grow_model(R44, base_tensors: dict, k: int):
    """K-slot model loaded from base_tensors; new rows are pure zeros.

    Initialisation rule is the recipe's own: Reasoner.__init__ builds every
    word slot as torch.zeros(STAGES, R+1), so a grown row starts as zeros.
    """
    import torch
    from torch import nn

    class GrowReasoner(nn.Module, GrowModelMixin):
        def __init__(self) -> None:
            super().__init__()
            self._R = R44.R
            self._STAGES = R44.STAGES
            self.token_logits = nn.Parameter(
                torch.zeros(R44.R, R44.R))
            self.words = nn.ParameterList([
                nn.Parameter(torch.zeros(R44.STAGES, R44.R + 1))
                for _ in range(k)])

    model = GrowReasoner()
    with torch.no_grad():
        model.token_logits.copy_(base_tensors["token_logits"])
        for i in range(k):
            key = f"words.{i}"
            if key in base_tensors:
                model.words[i].copy_(base_tensors[key])
            # else: stays zeros = the recipe's own slot-init rule
    return model


def harden_grow(phi):
    import torch
    out = torch.full_like(phi, -30.0)
    out[torch.arange(phi.shape[0]), phi.argmax(-1)] = 30.0
    return out


def fit_word_grow(R44, N45, base_tensors: dict, k: int, w: int, eps, v, m,
                  updates: int, seed: int, tag: str, snapshots=()) -> tuple:
    """Certified fit on the new row only (robust loss + harden, like G.fit_word)."""
    import torch
    from torch import nn
    model = make_grow_model(R44, base_tensors, k)
    model.requires_grad_(False)
    model.words[w].requires_grad_(True)
    opt = torch.optim.Adam([model.words[w]], lr=R44.SLEEP_LR)
    saved = {0: model.words[w].detach().clone()} if 0 in snapshots else {}
    starts, stages, targets = encode_grow(R44, v, eps, k)
    batch = min(R44.SLEEP_BATCH, len(eps))
    for step in range(updates):
        rng = R44.make_rng(f"sleep/{tag}/{step}", seed)
        pick = torch.tensor([rng.randrange(len(eps)) for _ in range(batch)],
                            dtype=torch.long)
        x = R44.run_tape(model.effective(m), starts[pick], stages[pick], v.n)
        p = x.gather(1, targets[pick][:, None])
        loss = -((1 - N45.EPS) * p + N45.EPS / v.n).log().mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_([model.words[w]], 1.0)
        opt.step()
        if step + 1 in snapshots:
            saved[step + 1] = model.words[w].detach().clone()
    saved = {t: harden_grow(p) for t, p in saved.items()}
    with torch.no_grad():
        model.words[w].copy_(harden_grow(model.words[w].data))
    return model, saved


def predict_grow(R44, model, v, m, qs, chunk: int = 128) -> list:
    import torch
    k = len(model.words)
    with torch.inference_mode():
        e = model.effective(m)
        preds: list = []
        for i in range(0, len(qs), chunk):
            starts, stages, _ = encode_grow(R44, v, qs[i:i + chunk], k)
            preds.extend(R44.decode(v, R44.run_tape(e, starts, stages, v.n)))
    return preds


def word_nll_grow(R44, N45, model, v, m, eps) -> float:
    import torch
    k = len(model.words)
    with torch.inference_mode():
        starts, stages, targets = encode_grow(R44, v, eps, k)
        x = R44.run_tape(model.effective(m), starts, stages, v.n)
        p = x.gather(1, targets[:, None])
        return float(-((1 - N45.EPS) * p + N45.EPS / v.n).log().mean())


def sleep_word_grow(base_tensors: dict, k: int, w: int, eps, v, m, seed: int,
                    mode: str, before: list, probe_qs: list,
                    fresh_qs: list, out: Path, frozen_keys: list[str]) -> dict:
    """The certified gate on a grown table (same floors/order as R44.sleep_word).

    Trains only row w of a K-slot table (K = w + 1); every key in frozen_keys
    (skill weights + pre-existing slots) must be bit-identical afterwards.
    """
    import torch
    R44, N45 = _r44()
    t0 = time.time()
    word = WORDS130[w]
    pre_hash = state_hashes(base_tensors, frozen_keys)
    people = sorted({e.start for e in eps})
    R44.make_rng(f"folds/{w}/{mode}", seed).shuffle(people)
    fold_of = {p: i % R44.FOLDS for i, p in enumerate(people)}
    oof: dict = {t: {} for t in R44.CHECKPOINTS}
    oof_nll: dict = {t: [] for t in R44.CHECKPOINTS}
    for f in range(R44.FOLDS):
        held = [e for e in eps if fold_of[e.start] == f]
        train = [e for e in eps if fold_of[e.start] != f]
        if not held or not train:
            continue
        _, saved = fit_word_grow(R44, N45, base_tensors, k, w, train, v, m,
                                 max(R44.CHECKPOINTS), seed,
                                 f"{mode}/w{w}/fold{f}", R44.CHECKPOINTS)
        probe = make_grow_model(R44, base_tensors, k)
        held_idx = [i for i, e in enumerate(eps) if fold_of[e.start] == f]
        for t in R44.CHECKPOINTS:
            with torch.no_grad():
                probe.words[w].copy_(saved[t])
            for i, p in zip(held_idx, predict_grow(R44, probe, v, m, held)):
                oof[t][i] = p
            oof_nll[t].append(word_nll_grow(R44, N45, probe, v, m, held)
                              * len(held))
    want = [e.answer if e.answer is not None else R44.UNKNOWN for e in eps]
    table = {t: {"match": sum(oof[t].get(i) == want[i]
                              for i in range(len(eps))) / len(eps),
                  "nll": sum(oof_nll[t]) / len(eps)} for t in R44.CHECKPOINTS}
    rec: dict = {"word": word, "mode": mode, "episodes": len(eps),
                 "distinct_people": len({e.start for e in eps}),
                 "grew_slot": True, "slots": k,
                 "cv_table": {str(t): {kk: round(val, 5)
                                       for kk, val in row.items()}
                              for t, row in table.items()}}
    rec["oof_best"] = max(float(r["match"]) for r in table.values())
    eligible = [t for t in R44.CHECKPOINTS if table[t]["match"] >= R44.CV_FLOOR]
    if not eligible:
        rec.update(installed=False,
                   reason=f"no checkpoint reached {R44.CV_FLOOR} OOF exact match",
                   refit_agreement=None,
                   frozen_ok=pre_hash == state_hashes(base_tensors,
                                                      frozen_keys),
                   seconds=round(time.time() - t0, 1))
        return rec
    best = min(table[t]["nll"] for t in eligible)
    chosen = min(t for t in eligible if table[t]["nll"] <= best + 1e-9)
    model, _ = fit_word_grow(R44, N45, base_tensors, k, w, eps, v, m,
                             chosen, seed, f"{mode}/w{w}/refit")
    refit_pred = predict_grow(R44, model, v, m, eps)
    agreement = sum(refit_pred[i] == oof[chosen][i]
                    for i in range(len(eps))) / len(eps)
    after = predict_grow(R44, model, v, m, probe_qs)
    base_unchanged = after == before
    new_tensors: dict = dict(base_tensors)
    new_tensors[f"words.{w}"] = model.words[w].detach().clone()
    post_frozen = state_hashes(new_tensors, frozen_keys)
    frozen_ok = post_frozen == pre_hash
    path = out / f"word-seed{seed}-{mode}-{word}-ep{len(eps)}.pt"
    torch.save({"state": {kk: vv.cpu().clone()
                           for kk, vv in new_tensors.items()},
                "slots": k, "word": word, "grown": True}, path)
    reloaded_tensors = torch.load(path, map_location="cpu",
                                  weights_only=True)["state"]
    reloaded = make_grow_model(R44, reloaded_tensors, k)
    reloaded.eval()
    fresh_pred = predict_grow(R44, model, v, m, fresh_qs)
    reload_identical = (predict_grow(R44, reloaded, v, m, fresh_qs)
                        == fresh_pred)
    installed = bool(agreement >= R44.AGREEMENT_FLOOR and base_unchanged
                     and reload_identical and frozen_ok)
    if not installed:
        reasons = []
        if agreement < R44.AGREEMENT_FLOOR:
            reasons.append(f"refit agreement {agreement:.3f} < "
                           f"{R44.AGREEMENT_FLOOR}")
        if not base_unchanged:
            reasons.append("old skills changed")
        if not reload_identical:
            reasons.append("reload differs")
        if not frozen_ok:
            reasons.append("a frozen tensor moved")
        rec.update(installed=False, chosen_updates=chosen,
                   refit_agreement=agreement, reason="; ".join(reasons),
                   frozen_ok=frozen_ok,
                   seconds=round(time.time() - t0, 1))
        return rec
    p = model.words[w].detach().softmax(-1)
    rec.update(chosen_updates=chosen, installed=True,
               refit_agreement=agreement,
               reason=f"grew slot {w} (of {k}); frozen "
                      f"{len(post_frozen)} tensors bit-identical",
               frozen_ok=frozen_ok, frozen_hashes=post_frozen,
               routing=[[round(val, 4) for val in row] for row in p.tolist()],
               routing_names=("keep",) + RELATIONS130,
               routed_chain=[(("keep",) + RELATIONS130)[int(row.argmax())]
                             for row in p],
               seconds=round(time.time() - t0, 1))
    rec["new_tensors"] = new_tensors
    return rec


# ------------------------------------------------------------------- sleeper
class Sleep130Sleeper(S115.Sleep115Sleeper):
    """115 sleeper + grow-one-slot when every slot is taken (additive)."""

    def __init__(self, state_dir, reasoner=None, checkpoint=None, seed=1,
                 word_file: str = WORD_FILE130) -> None:
        super().__init__(state_dir, reasoner=reasoner,
                         checkpoint=checkpoint or str(BASE_PT130), seed=seed)
        self.word_path = Path(state_dir) / word_file
        self.marker_path = Path(state_dir) / MARKER130
        self.grown: dict | None = None  # slot tensors, in-memory serving copy

    # ------------------------------------------------------- grown state
    def _grown_tensors(self) -> dict:
        """Checkpoint skills + every installed slot as tensors (zeros for new)."""
        import torch
        if self.grown is not None:
            return self.grown
        R44, _ = _r44()
        torch.set_num_threads(1)
        base = torch.load(self.checkpoint, map_location="cpu",
                          weights_only=True)
        base = base["state"] if "state" in base else base
        tensors: dict = {"token_logits": base["token_logits"].clone()}
        for i in range(N_BASE_SLOTS):
            tensors[f"words.{i}"] = base[f"words.{i}"].clone()
        try:
            data = json.loads(self.word_path.read_text(encoding="utf-8"))
            words = data.get("words", {}) if isinstance(data, dict) else {}
        except (OSError, ValueError):
            words = {}
        for wname, rec in words.items():
            if wname in WORDS130 and isinstance(rec, dict):
                try:
                    tensors[f"words.{WORDS130.index(wname)}"] = torch.tensor(
                        rec["logits"], dtype=torch.float32)
                except (TypeError, ValueError, KeyError):
                    continue
        # live reasoner wins (same numbers; covers installs since last persist)
        try:
            live = getattr(getattr(self.reasoner, "inner", None), "words", {})
            for wname, logits in live.items():
                if wname in WORDS130:
                    tensors[f"words.{WORDS130.index(wname)}"] = torch.tensor(
                        logits, dtype=torch.float32)
        except (TypeError, ValueError):
            pass
        self.grown = tensors
        return tensors

    def n_slots(self) -> int:
        tensors = self._grown_tensors()
        ids = [int(k.split(".")[1]) for k in tensors if k.startswith("words.")]
        return max(ids) + 1 if ids else N_BASE_SLOTS

    # ------------------------------------------------------------- recipe
    def _run_exp46(self, notebook) -> dict:
        episodes = list(self.reasoner.episodes) if self.reasoner else []
        by_word: dict[int, list] = {}
        for ep in episodes:
            by_word.setdefault(int(ep["word"]), []).append(ep)
        if self.grown is None and all(w < N_BASE_SLOTS for w in by_word):
            # Every requested word has a free sealed slot (or nothing is
            # queued at all): the 115/wire57 path untouched, including its
            # kept-queued rule below MIN_EPISODES (G3 byte-identical
            # guarantee).
            return W57.SparseVillageSleeper._run_exp46(self, notebook)
        return self._run_exp46_grow(notebook, episodes, by_word)

    def _run_exp46_grow(self, notebook, episodes: list,
                        by_word: dict[int, list]) -> dict:
        import torch
        R44, _ = _r44()
        torch.set_num_threads(1)
        if len(episodes) < W57.SparseVillageSleeper.MIN_EPISODES:
            return {"attempted": False, "queued": len(episodes),
                    "reason": f"{len(episodes)} word episodes "
                              f"(< {W57.SparseVillageSleeper.MIN_EPISODES}); "
                              "kept queued, nothing to gate"}
        if self.reasoner is not None:
            self.reasoner.episodes.clear()
        village = W57.AD._village_from_notebook(R44, notebook)
        matrices = R44.notebook_matrices(village)
        base_tensors = dict(self._grown_tensors())
        out = self.state_dir / "sleep-checkpoints"
        out.mkdir(parents=True, exist_ok=True)
        base_model = make_grow_model(R44, base_tensors, self.n_slots())
        base_model.eval()
        probe = W57._best_effort_set(
            R44, village, "wire57/probe", self.seed, 64, (1, 2, 3))
        if not probe:
            return {"attempted": False,
                    "reason": "live village too sparse for any probe"}
        before = predict_grow(R44, base_model, village, matrices, probe)
        held = W57._best_effort_set(
            R44, village, "wire57/held", self.seed, 64, (1, 2, 3))
        results = []
        for w, eps_in in sorted(by_word.items()):
            wname = WORDS130[w] if 0 <= w < len(WORDS130) else None
            if wname is None:
                results.append({"word": f"word{w}", "episodes": len(eps_in),
                                "installed": False,
                                "oof_best": 0.0, "refit_agreement": None,
                                "reason": "unknown word (no chain defined)"})
                continue
            eps = [R44.Question(ep["start"], (R44.R + w,), ep["answer"])
                   for ep in eps_in]
            if w < self.n_slots():
                # Free slot on the current table: certified 115 path on a
                # K-slot model is still exact, but to keep the sealed words
                # bit-identical we route w < 3 with no grown slots through
                # the original R44.sleep_word.
                if self.grown is None and w < N_BASE_SLOTS:
                    base_state = torch.load(
                        self.checkpoint, map_location="cpu",
                        weights_only=True)
                    base_state = (base_state["state"]
                                  if "state" in base_state else base_state)
                    rec0 = R44.sleep_word(
                        base_state, w, eps, village, matrices, self.seed,
                        "wire57-live", before, probe, village, matrices,
                        held, out)
                    rec0["grew_slot"] = False
                    if rec0.get("installed"):
                        with torch.no_grad():
                            sd = torch.load(
                                sorted(out.glob(f"*{wname}-*.pt"),
                                       key=lambda p: p.stat().st_mtime)[-1],
                                map_location="cpu", weights_only=True)
                            key = f"words.{w}"
                            base_tensors[key] = sd[key].clone() \
                                if key in sd else sd["state"][key].clone()
                    results.append({
                        "word": wname, "episodes": len(eps),
                        "installed": bool(rec0.get("installed")),
                        "oof_best": max(
                            (float(vv["match"]) for vv in
                             rec0.get("cv_table", {}).values()), default=0.0),
                        "refit_agreement": rec0.get("refit_agreement"),
                        "reason": rec0.get("reason"),
                        "grew_slot": False})
                    continue
                k_here = self.n_slots()
                frozen = ["token_logits"] + [
                    f"words.{i}" for i in range(k_here) if i != w]
                rec = sleep_word_grow(dict(base_tensors), k_here, w, eps,
                                      village, matrices, self.seed,
                                      "wire57-live", before, probe, held,
                                      out, frozen)
            else:
                # No slot: grow the table by exactly one zero row.
                k = w + 1
                frozen = ["token_logits"] + [f"words.{i}" for i in range(w)]
                rec = sleep_word_grow(dict(base_tensors), k, w, eps,
                                      village, matrices, self.seed,
                                      "wire57-live", before, probe, held,
                                      out, frozen)
            if rec.get("installed"):
                # adopt the exact persisted row (what serving will load)
                with torch.no_grad():
                    sd = torch.load(
                        sorted(out.glob(f"*{wname}-*.pt"),
                               key=lambda p: p.stat().st_mtime)[-1],
                        map_location="cpu", weights_only=True)
                    state = sd.get("state", sd)
                    base_tensors[f"words.{w}"] = state[f"words.{w}"].clone()
                rec.pop("new_tensors", None)
            results.append({
                "word": wname, "episodes": len(eps),
                "installed": bool(rec.get("installed")),
                "oof_best": rec.get("oof_best", 0.0),
                "refit_agreement": rec.get("refit_agreement"),
                "reason": rec.get("reason"),
                "grew_slot": bool(rec.get("grew_slot")),
                "frozen_ok": rec.get("frozen_ok")})
        self.grown = base_tensors
        installed = sum(1 for r in results if r["installed"])
        self.installs += installed
        return {"attempted": True, "installed": installed, "words": results,
                "probe_size": len(probe), "held_size": len(held)}

    # ------------------------------------------------------- persistence
    def load_persisted(self) -> dict:
        """Boot-time load of the atomic multi-word file (WORDS130)."""
        try:
            data = json.loads(self.word_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict) or not isinstance(
                data.get("words"), dict):
            return {}
        good: dict = {}
        for wname, rec in data["words"].items():
            if wname not in WORDS130 or not isinstance(rec, dict):
                continue
            if not check_word_logits130(rec.get("logits"),
                                        WORDS130.index(wname)):
                continue
            try:
                self.reasoner.inner.words[wname] = [
                    [float(x) for x in row] for row in rec["logits"]]
                self.reasoner.report_fids[wname] = rec.get("report_fid")
                self.reasoner.install_episodes[wname] = int(
                    rec.get("episodes", 0))
            except (AttributeError, TypeError, ValueError):
                continue
            good[wname] = rec
        return {"words": good, "seed": data.get("seed")}

    def _commit_installs(self, notebook, recipe: dict) -> dict:
        words = recipe.get("words", []) if isinstance(recipe, dict) else []
        try:
            prior = json.loads(self.word_path.read_text(encoding="utf-8"))
            merged = dict(prior.get("words", {})) if isinstance(
                prior, dict) else {}
        except (OSError, ValueError):
            merged = {}
        per_word: dict = {}
        for rec in words:
            if not rec.get("installed"):
                continue
            wname = rec.get("word")
            if wname not in WORDS130:
                continue
            w = WORDS130.index(wname)
            bridged = self._commit_one(notebook, rec, w, wname, merged)
            per_word[wname] = bridged
        if per_word:
            payload = {"words": merged, "seed": self.seed}
            tmp = (self.word_path.parent
                   / f"{self.word_path.name}.tmp{os.getpid()}")
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.word_path)
        return per_word

    def _commit_one(self, notebook, rec: dict, w: int, wname: str,
                    merged: dict) -> dict:
        import torch
        torch.set_num_threads(1)
        ckpts = sorted(
            (self.state_dir / "sleep-checkpoints").glob(
                f"word-seed*-wire57-live-{wname}-ep*.pt"),
            key=lambda p: p.stat().st_mtime)
        if not ckpts:
            alt = sorted(
                (self.state_dir / "sleep-checkpoints").glob(f"*{wname}-*.pt"),
                key=lambda p: p.stat().st_mtime)
            ckpts = alt
        if not ckpts:
            return {"bridged": False, "reason": "no checkpoint file"}
        try:
            sd = torch.load(ckpts[-1], map_location="cpu", weights_only=True)
            state = sd.get("state", sd)
            logits = [[float(x) for x in row]
                      for row in state[f"words.{w}"].tolist()]
        except (OSError, ValueError, KeyError) as exc:
            return {"bridged": False,
                    "reason": f"checkpoint unreadable: {exc}"}
        if not check_word_logits130(logits, w):
            return {"bridged": False,
                    "reason": "logits fail the chain audit"}
        self.reasoner.inner.words[wname] = logits
        self.reasoner.install_episodes[wname] = int(rec.get("episodes", 0))
        try:
            if REPORT_RELATION130 not in notebook.functional:
                notebook.declare_relation("sleep130-rel-0",
                                          REPORT_RELATION130, False)
        except (AttributeError, TypeError):
            pass
        try:
            found = notebook.resolve(SLEEP_ENTITY130)
            if found.status == C.OK:
                sleep_eid = found.detail["entity_id"]
            else:
                made = notebook.new_entity("sleep130-ent-0", SLEEP_ENTITY130)
                sleep_eid = made.detail["entity_id"]
        except (AttributeError, TypeError, ValueError) as exc:
            return {"bridged": False, "reason": f"notebook error: {exc}"}
        summary = {"word": wname, "chain": list(CHAINS130[w]),
                   "episodes": rec.get("episodes"),
                   "oof_best": rec.get("oof_best"),
                   "refit_agreement": rec.get("refit_agreement"),
                   "routing": rec.get("reason"),
                   "grew_slot": bool(rec.get("grew_slot")),
                   "seed": self.seed}
        rep = notebook.assert_fact(
            f"sleep130-report-{self.seed}-{wname}", "sleep", "sleep-derived",
            sleep_eid, REPORT_RELATION130,
            {"literal": json.dumps(summary, sort_keys=True)},
            raw="sleep130 install report row")
        if rep.status not in (C.SAVED, C.DUPLICATE_OK):
            return {"bridged": False,
                    "reason": f"report row not stored: {rep.status}"}
        self.reasoner.report_fids[wname] = rep.detail.get("fact_id")
        merged[wname] = {"logits": logits,
                         "report_fid": self.reasoner.report_fids[wname],
                         "episodes": self.reasoner.install_episodes[wname],
                         "seed": self.seed}
        return {"bridged": True,
                "report_fid": self.reasoner.report_fids[wname],
                "episodes": self.reasoner.install_episodes[wname],
                "grew_slot": bool(rec.get("grew_slot"))}


# ------------------------------------------------------------------- retrofit
def retrofit_sleep130(loop, root, seed: int = 1,
                       checkpoint: str | None = None) -> Sleep130Reasoner:
    """Swap the loop96 ears/reasoner/sleeper for the sleep130 trio."""
    root = Path(root)
    ears = Sleep130Ears(loop.ears)
    wrapper = Sleep130Reasoner(loop.reasoner)
    sleeper = Sleep130Sleeper(root, reasoner=wrapper,
                              checkpoint=checkpoint or str(BASE_PT130),
                              seed=seed)
    loop.ears = ears
    loop.reasoner = wrapper
    loop.sleeper = sleeper
    try:
        loop.parts90["ears"] = ears
        loop.parts90["reasoner"] = wrapper
        loop.parts90["sleeper"] = sleeper
    except (AttributeError, TypeError):
        pass
    for stale in root.glob(f"{WORD_FILE130}.tmp*"):
        try:
            stale.unlink()
        except OSError:
            pass
    loaded = sleeper.load_persisted()
    sleeper.grown = None  # rebuilt lazily from checkpoint + live words
    loop.notes.append(
        "sleep130: words "
        f"{sorted(loaded.get('words', {})) if loaded else []} on boot")
    return wrapper


DEFAULT_CONFIG130: dict = copy.deepcopy(L96.DEFAULT_CONFIG96)
DEFAULT_CONFIG130["sleeper"]["stand_in"] = (
    "Sleep130Sleeper = 115 sleeper + grow-one-zero-slot when every slot is "
    "taken (certified recipe on the new row only; frozen tensors hashed); "
    "episode feed = Sleep130Reasoner (extended chains); ears = Sleep130Ears")
DEFAULT_CONFIG130["daemon"]["module"] = "Sleep130Daemon (this file)"


def build_agent130(cfg: dict | None = None, seed: int = 1,
                   checkpoint: str | None = None):
    cfg = dict(DEFAULT_CONFIG130, **(cfg or {}))
    loop = L96.build_agent96(cfg)
    retrofit_sleep130(
        loop, cfg.get("state_dir", "."),
        seed=int(cfg.get("sleep130_seed", cfg.get("sleep115_seed", seed))),
        checkpoint=cfg.get("sleep130_checkpoint",
                           cfg.get("sleep115_checkpoint", checkpoint)))
    loop.parts90["sleep130"] = {"words": list(WORDS130),
                                "chains": [list(c) for c in CHAINS130]}
    return loop


# -------------------------------------------------------------------- daemon
class Sleep130Daemon(L96.Loop96Daemon):
    """Loop96Daemon with the sleep130 trio + per-sleep logging."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 seed: int = 1) -> None:
        cfg = dict(cfg or {})
        seed = int(cfg.get("sleep130_seed",
                           cfg.get("sleep115_seed", seed)))
        L96.Loop96Daemon.__init__(self, root, cfg=cfg,
                                  idle_seconds=idle_seconds,
                                  sleep_threshold=sleep_threshold)
        retrofit_sleep130(self.loop, self.root, seed=seed,
                          checkpoint=cfg.get("sleep130_checkpoint",
                                             cfg.get("sleep115_checkpoint")))

    def process_file(self, path: Path) -> dict:
        import os as _os
        nb = self.loop.nb
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {"event": "turn-skipped", "file": path.name}
        before_facts = set(nb.facts)
        before_entities = set(nb.entities)
        sleeps_before = int(self.loop.counters.get("sleeps", 0))
        t0 = time.time()
        said = self.loop.turn(text)  # SLEEP fires inside here, on its own
        wall = round(time.time() - t0, 2)
        records = list(getattr(self.loop, "last_records", []))
        new_facts = sorted(set(nb.facts) - before_facts)
        new_entities = {eid: nb.entities[eid]
                        for eid in set(nb.entities) - before_entities}
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
                  "notebook_events": len(nb.events),
                  "turn_seconds": wall}
        D74._append_log(self.log_path, record)
        if int(self.loop.counters.get("sleeps", 0)) > sleeps_before:
            outcome = dict(
                getattr(self.loop.sleeper, "last_outcome", {}))
            queued = len(getattr(self.loop.reasoner, "episodes", []))
            installed_eps = sum(
                w.get("episodes", 0) for w in
                outcome.get("recipe", {}).get("words", []))
            D74._append_log(self.log_path, {
                "t": D74._now_iso(), "event": "sleep", "file": path.name,
                "turn_seconds": wall,
                "sleep_seconds": getattr(self.loop.sleeper,
                                         "sleep_seconds", 0.0),
                "accepted": outcome.get("accepted"),
                "recipe": outcome.get("recipe", {}),
                "bridge": outcome.get("bridge", {}),
                "episodes_at_sleep": queued + installed_eps})
        return record


def run_daemon130(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Sleep130Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 130 grow-a-slot sleep")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG130)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG130)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    cfg.setdefault("sleep130_seed", args.seed)

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon130(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent130(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
