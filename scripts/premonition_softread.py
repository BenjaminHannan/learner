"""Two new retrieval-training arms (Claude, 2026-09-19) -- ADDITIVE variant module AND launcher.

Nothing existing is edited. The frozen snapshot under archive/opus-ovn-20260918-235851/frozen/ is the same
one `scripts/premonition_gpu_port.py` uses, and the data, optimiser and evaluation code are reused as they
are. This file adds one subclass of `answer_path.CardBypassMini` carrying two INDEPENDENT switches, plus a
launcher with the same flags as `premonition_gpu_port.py` (whose `main` parses its own arguments and cannot
take new ones without editing it, so the minimum -- trainer, curriculum and checkpoint plumbing -- is copied
here; `make_trainer_class` and the fp32-autocast handling are imported from it, not copied).

WHY. In the frozen model retrieval is a HARD, DETACHED top-k: `own = store.top(scores.detach(), k)` and
`_insert` writes `values + age + row_type` rows gathered by integer index. So the ANSWER loss never reaches
the query head, kappa, the age bias or the card keys: those learn only from L_ask, whose targets are the
simulator's gold evidence lines. The two arms probe that seam from opposite sides.

  --answer-grad        ONE change vs the baseline recipe. Every card row inserted AFTER a `_step` becomes
                       `row = hard_row + (soft - soft.detach())` with
                       `soft = softmax(scores) @ [card values ; null_value]` computed from the WITH-GRAD
                       scores of the step that preceded the insert. Forward values are bit-identical to the
                       baseline (the added term is exactly zero); backward, L_ans now reaches the query
                       head, kappa, the age bias and the card keys. Gold-phase preloads happen before any
                       step and stay plain. No new parameters; the state_dict is the baseline's, so every
                       existing eval script (e.g. premonition_first_card_probe.load_from) loads it unchanged.

  --soft-no-oracle     Can retrieval be learned from answers alone? NO simulator evidence label touches any
                       gradient: no gold phase, no teacher insertions, own picks from step 0 with
                       probability 1.0 (not the frozen Curriculum's 0.75 ceiling), w_ask = 0 (both the set
                       cross-entropy and the ASK BCE are gone), the `early_ans` down-weighting is off
                       (scale = 1.0 always, since it is gold-dependent), and the ASK DECISION IS FORCED ON
                       in training and in evaluation (the ASK head is untrained, so its logit is replaced
                       by a constant). During TRAINING the inserted row IS the soft mixture:
                       `softmax(scores) @ values` plus the softmax-weighted mixture of AGE embeddings plus
                       the usual ROW_CARD row-type embedding, one soft row per loop. The argmax card
                       (detached) is marked fetched so the next loop's read excludes it. Soft rows are NOT
                       bound into the entity slots (documented choice: a mixture has no single card
                       identity, and binding the argmax's entities would smuggle a hard decision into the
                       pointer slots). EVALUATION uses the standard HARD top-1 path -- literally
                       `premonition_ovn_retrieval.evaluate`, so the report schema is the baseline's -- and a
                       soft-read evaluation is reported alongside it under "soft_read", so the soft -> hard
                       gap is visible. L_halt stays (its target is answer correctness, not an evidence
                       label). Every logged step records recall@k of the argmax against gold (DIAGNOSTIC
                       ONLY -- computed under no_grad, gold never enters the loss), the softmax entropy of
                       the first ASK, and kappa.

`_insert` and the training `forward` below are the frozen bodies (model.py lines 446-481 and 503-630) copied
verbatim, with every changed line marked "EDITED". With both switches off the copies run the frozen code
path exactly; tests/test_premonition_softread.py checks that parity.

Two run-keeping features, both in this file only:

  --ckpt-every N (default 1000) writes a recoverable `<name>-step<K>.pt` every N steps -- an atomic write to
  a temporary name followed by a rename, so a reader never sees a partial file -- carrying the model, the
  optimizer state, the trainer's step / FLOPs / RNG state and `steps_requested`. Every intermediate state is
  kept (they are about 1 MB), so a later probe can watch the card-pooling weights move over training.
  --resume continues from the newest one, replaying the batch stream by skipping `trainer.step` items; the
  final `<name>.pt` and the result JSON are written exactly as before. The frozen trainer cannot do this
  without being edited (its only hooks are `on_log`, which fires every `log_every` steps, and `evaluate`,
  which runs under `read_only`), so the hook lives in this file's trainer subclass, in `_train_step`.

  Every result JSON and every checkpoint carries an `oracle_use` table: the four channels through which a
  simulator EVIDENCE label can reach a gradient here (see ORACLE_CHANNELS below), all four off for
  --soft-no-oracle and all four on for the baseline and --answer-grad. Ordinary answer supervision is listed
  separately and is NOT an evidence label.

    PY -B scripts/premonition_softread.py --arm bypass-k1 --steps 50 --device cpu --threads 2
    PY -B scripts/premonition_softread.py --answer-grad --steps 50
    PY -B scripts/premonition_softread.py --soft-no-oracle --steps 50
    PY -B scripts/premonition_softread.py --self-check     # runs tests/test_premonition_softread.py
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import itertools
import json
import os
from pathlib import Path
import platform
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_gpu_port as G  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

OUT = L.ROOT / "artifacts" / "claude-softread-20260919"

# The logit substituted for the ASK head's output when the decision is forced on. Large enough that
# `ask > 0` everywhere and sigmoid(ask) rounds to 1.0, small enough to stay finite in bf16.
FORCED_ASK_LOGIT = 20.0

# The soft-no-oracle curriculum: own mode from step 0 with p_own = 1.0, no gold and no teacher phase.
SOFT_CURRICULUM = dict(gold_until=0.0, teacher_until=0.0, ramp_until=0.0, p_own_max=1.0)

STEP_CKPT = re.compile(r"-step(\d+)\.pt$")

# Which channels of SIMULATOR EVIDENCE supervision each arm uses. The four channels are the only ways a
# gold evidence LINE can reach a gradient in this code base:
#   ask_set_target       the set cross-entropy target of L_ask is G minus F, the cards on the question's
#                        gold evidence lines that have not been fetched yet
#   teacher_insertions   the teacher hands the model gold cards (`_teacher_cards` draws from G minus F)
#   early_ans_weighting  L_ans is down-weighted by config.early_ans until every gold card is in hand
#   should_search_bce    the BCE target on the ASK logit is "at least one gold card is still missing"
# ORDINARY ANSWER SUPERVISION IS NOT ONE OF THESE: the answer text, the visit text and the
# answer-correctness HALT target are the task, not an evidence label, and every arm uses them.
ORACLE_CHANNELS = ("ask_set_target", "teacher_insertions", "early_ans_weighting", "should_search_bce")
ORACLE_USE = {
    "baseline": dict.fromkeys(ORACLE_CHANNELS, True),
    "answer-grad": dict.fromkeys(ORACLE_CHANNELS, True),
    "soft-no-oracle": dict.fromkeys(ORACLE_CHANNELS, False),
}
ORACLE_NOTE = ("answer supervision (the answer tokens for L_ans, the visit text for L_lm and "
               "answer-correctness for L_halt) is NOT an evidence label and is used by every arm")


def oracle_use(arm_tag: str, has_store: bool) -> dict:
    """The four-channel evidence-oracle table for a run, plus the separate answer-supervision note."""
    table = dict(ORACLE_USE[arm_tag])
    if not has_store:
        # The no-store control has no cards to retrieve, so no evidence channel exists at all.
        table = dict.fromkeys(ORACLE_CHANNELS, False)
    return {"channels": table, "any_evidence_label": any(table.values()),
            "answer_supervision": True, "answer_supervision_is_an_evidence_label": False,
            "note": ORACLE_NOTE + ("; this arm has no card store, so no evidence channel exists"
                                   if not has_store else "")}

torch = None
F = None
MODES = None
ROW_CARD = None
age_bucket = None
set_cross_entropy = None
IGNORE_INDEX = None
_CLASS = None


def _imports() -> None:
    """Pull the frozen names into this module's globals (only valid after L.bootstrap())."""
    global torch, F, MODES, ROW_CARD, age_bucket, set_cross_entropy, IGNORE_INDEX
    import torch as _torch
    import torch.nn.functional as _F
    from learnlab.core import IGNORE_INDEX as _ignore
    from premonition.model import MODES as _MODES, ROW_CARD as _row_card
    from premonition.store import age_bucket as _age_bucket, set_cross_entropy as _sce
    torch, F, MODES, ROW_CARD = _torch, _F, _MODES, _row_card
    age_bucket, set_cross_entropy, IGNORE_INDEX = _age_bucket, _sce, _ignore


# ----------------------------------------------------------------------------- the model
def softread_class():
    """The `CardBypassMini` subclass; built on first use so it sees the frozen package."""
    global _CLASS
    if _CLASS is not None:
        return _CLASS
    _imports()
    from premonition import answer_path
    from premonition.model import PremonitionMini

    class SoftInsertMixin(PremonitionMini):
        """`PremonitionMini._insert` with three row modes. Placed AFTER `CardBypassMini` in the MRO, so the
        bypass wrapper's book-keeping (`episode.inserted`) still runs first and then delegates here."""

        insert_mode = "hard"          # "hard" (frozen) | "st" (straight-through) | "soft" (mixture row)
        _ins_scores = None            # the WITH-GRAD scores of the step that preceded this insert

        # -------------------------------------------------------------- soft pieces (new)
        def _soft_parts(self, store, episode, index):
            """(value [n, d], age [n, d]): softmax(scores) mixtures of the card values and age embeddings.

            The softmax runs over every column of `scores` -- all eligible cards plus NULL; ineligible
            columns are -inf, so they carry exactly zero weight. NULL is always eligible, so no row is all
            -inf and the softmax cannot produce NaN.
            """
            scores = self._ins_scores
            if scores is None:
                raise RuntimeError("soft / straight-through inserts need the preceding step's scores")
            count = scores.shape[0]
            weight = torch.softmax(scores.float(), dim=1)                               # [n, L + 1]
            visit = episode.q_visit[index]
            values = torch.cat([store.values[visit].float(),
                                store.null_value.float().expand(count, 1, -1)], dim=1)   # [n, L + 1, d]
            value = torch.einsum("nl,nld->nd", weight, values)
            buckets = store.ages(episode.q_line[index], self.config.age_buckets)         # [n, L + 1]
            age = torch.einsum("nl,nld->nd", weight, self.think.age(buckets).float())
            return value, age

        def insert_with(self, episode, store, index, cards, scores, mode: str) -> None:
            """`self._insert(...)` with `mode` and `scores` in force for the duration of the call."""
            if mode not in ("hard", "st", "soft"):
                raise ValueError(f"unknown insert mode {mode!r}")
            was_mode, was_scores = self.insert_mode, self._ins_scores
            self.insert_mode, self._ins_scores = mode, scores
            try:
                self._insert(episode, store, index, cards)
            finally:
                self.insert_mode, self._ins_scores = was_mode, was_scores

        # -------------------------------------------------------------- frozen _insert, copied
        def _insert(self, episode, store, index, cards) -> None:
            """Append fetched cards (indices [n, K], -1 = none) as rows of questions `index`; bind slots."""
            config = self.config
            if cards.shape[1] > config.card_rows:
                raise ValueError(f"cannot insert {cards.shape[1]} cards into {config.card_rows} rows at once")
            real = cards >= 0
            if not real.any():
                return
            values, ents, lines = store.gather(cards, episode.q_visit[index])
            bucket = age_bucket(episode.q_line[index].unsqueeze(1) - lines, config.age_buckets)
            bucket = torch.where(lines >= 0, bucket, torch.zeros_like(bucket))
            rows = values.float() + self.think.age(bucket).float() \
                + self.think.row_type.weight[ROW_CARD].float()
            mode = self.insert_mode                                                      # EDITED
            if mode == "st":                                                             # EDITED
                # Straight-through: exactly zero in the forward pass, the mixture's gradient backwards.
                soft_value, _ = self._soft_parts(store, episode, index)                  # EDITED
                rows = rows + (soft_value - soft_value.detach()).unsqueeze(1)             # EDITED
            elif mode == "soft":                                                         # EDITED
                # The row IS the mixture: soft values + mixed age embedding + the ROW_CARD row type.
                soft_value, soft_age = self._soft_parts(store, episode, index)            # EDITED
                soft_row = soft_value + soft_age \
                    + self.think.row_type.weight[ROW_CARD].float()                        # EDITED
                rows = soft_row.unsqueeze(1).expand_as(rows)                              # EDITED
            order = real.long().cumsum(1) - 1
            position = self._card_base + (episode.count[index].unsqueeze(1) + order) % config.card_rows
            who = index.unsqueeze(1).expand_as(cards)
            episode.x = episode.x.index_put((who[real], position[real]), rows[real])
            episode.valid = episode.valid.index_put(
                (who[real], position[real]), torch.ones_like(position[real], dtype=torch.bool))
            episode.count = episode.count.index_add(0, index, real.long().sum(1))
            episode.fetched = episode.fetched.index_put(
                (who[real], cards[real]), torch.ones_like(cards[real], dtype=torch.bool))
            if self.think.binder is None:
                return
            if mode == "soft":                                                            # EDITED
                return          # a mixture has no single card identity: soft rows are not bound to slots
            for k in range(cards.shape[1]):
                ent = ents[:, k]                                                   # [n, E]
                repeat = (ent.unsqueeze(2) == ent.unsqueeze(1)).tril(-1).any(2)
                bind = (ent >= 0) & real[:, k:k + 1] & ~repeat
                if not bind.any():
                    continue
                slot = config.question_rows + ent.clamp_min(0)
                owner = index.unsqueeze(1).expand_as(ent)
                state = episode.x[owner[bind], slot[bind]]
                value = values[:, k].unsqueeze(1).expand(-1, ent.shape[1], -1)[bind]
                episode.x = episode.x.index_put((owner[bind], slot[bind]), self.think.bind(state, value))

    class SoftReadCardBypassMini(answer_path.CardBypassMini, SoftInsertMixin):
        """D-card-bypass with the straight-through answer gradient and/or the oracle-free soft-read arm.

        MRO: SoftReadCardBypassMini -> CardBypassMini -> SoftInsertMixin -> PremonitionMini, so
        `CardBypassMini._insert`'s `super()._insert` lands on the mixin's copy.
        """

        answer_grad = False
        soft_no_oracle = False
        force_ask = False

        def __init__(self, config) -> None:
            super().__init__(config)
            self.answer_grad = False
            self.soft_no_oracle = False
            self.force_ask = False
            self.insert_mode = "hard"
            self._ins_scores = None

        # ---------------------------------------------------------------- forced ASK
        def _step(self, episode, index, step, store):
            rows, halt, ask, scores = super()._step(episode, index, step, store)
            if self.force_ask and ask is not None:                                       # EDITED
                ask = torch.full_like(ask, FORCED_ASK_LOGIT)                             # EDITED
            return rows, halt, ask, scores

        # ---------------------------------------------------------------- frozen forward, copied
        def forward(self, *args, **kwargs):
            # EDITED: identical to answer_path.CardBypassMini.forward around the copied body below.
            try:
                return self._forward_impl(*args, **kwargs)
            finally:
                self._reading = None

        def _forward_impl(self, batch, mode: str = "teacher", p_own: float = 0.0,
                          loops=None, weights=None, generator=None) -> dict:
            """The four losses of design/06 §3 and their weighted sum under "loss".

            mode "gold": every gold card (NULL when never told) is loaded before loop 1; 2 loops.
            mode "teacher": after each loop, fetch up to top_k cards of G minus F plus 1-2 random
                distractors while G minus F is non-empty; ceil(|G| / 4) + 3 loops.
            mode "own": like "teacher", but each (question, loop) uses the model's own top-k
                (when its ASK logit > 0) with probability p_own; max_loops loops.
            `loops` overrides the loop count. Default weights come from the config, except
            that "gold" leaves out L_ask and L_halt (the 0-5% phase trains L_lm + L_ans only).
            """
            if mode not in MODES:
                raise ValueError(f"unknown mode {mode!r}; choose from {MODES}")
            config = self.config
            hidden = self.read(batch)
            l_lm = self.lm_loss(hidden, batch)
            store = self.build_store(hidden, batch)
            count = batch.q_visit.shape[0]
            zero = hidden.sum() * 0.0
            metrics: dict = {}
            if weights is None:
                weights = {"lm": config.w_lm, "ask": config.w_ask, "ans": config.w_ans, "halt": config.w_halt}
                if mode == "gold":
                    weights.update(ask=0.0, halt=0.0)
                if self.soft_no_oracle:                                                  # EDITED
                    weights.update(ask=0.0)          # EDITED: no evidence-label loss in this arm
            if count == 0:
                losses = {"lm": l_lm, "ask": zero, "ans": zero, "halt": zero}
                metrics["question_loops"] = torch.zeros((), dtype=torch.long)
                return {**losses, "loss": sum(weights[k] * v for k, v in losses.items()), "metrics": metrics}

            device = hidden.device
            episode = self._start(batch, hidden, store, self._mentions(batch))
            told_lines = (batch.gold_lines >= 0).sum(1).clamp_min(1)
            if loops is not None:
                n_loops = torch.full((count,), loops, dtype=torch.long, device=device)
            elif mode == "gold":
                n_loops = torch.full((count,), 2, dtype=torch.long, device=device)
            elif mode == "teacher":
                n_loops = (-(-told_lines // config.top_k) + 3).clamp_max(config.max_loops)
            else:
                n_loops = torch.full((count,), config.max_loops, dtype=torch.long, device=device)
            n_loops = n_loops.clamp(1, config.max_loops)

            gold = None
            diag_gold = None                                                             # EDITED
            if store is not None:
                if self.soft_no_oracle:                                                  # EDITED
                    # Gold is read for DIAGNOSTICS ONLY, under no_grad; `gold` stays None so nothing
                    # gold-derived can reach a loss term, a weighting or a gradient.
                    with torch.no_grad():                                                # EDITED
                        diag_gold, _, _ = store.gold(batch.gold_lines, batch.q_visit,    # EDITED
                                                     batch.q_line)                       # EDITED
                else:
                    gold, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
                    metrics["gold_missing"] = missing.sum()
                    if mode == "gold":
                        width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, config.card_rows)
                        preload = torch.where(gold, torch.arange(gold.shape[1], device=device),
                                              torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
                        self._insert(episode, store, torch.arange(count, device=device), preload)

            answer = batch.answer
            length = int((answer != IGNORE_INDEX).sum(1).max().item())
            targets = answer[:, :max(length, 1)]
            start_token = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1]
            inputs = torch.cat([start_token.unsqueeze(1), targets[:, :-1]], dim=1)
            inputs = inputs.masked_fill(inputs == IGNORE_INDEX, config.pad_id)

            ans_terms, halt_terms, set_terms, bce_terms = [], [], [], []
            pairs = 0
            for step in range(int(n_loops.max().item())):
                index = torch.nonzero(n_loops > step).squeeze(1)
                pairs += index.numel()
                rows, halt, ask, scores = self._step(episode, index, step, store)
                # L_ans (deep supervision) and the HALT target.
                hidden_ans = self._decode_logits(rows, episode.valid[index], inputs[index])
                target = targets[index]
                keep = target != IGNORE_INDEX
                logits = F.linear(hidden_ans[keep], self.embed.weight).float()
                owner = torch.nonzero(keep)[:, 0]
                token_ce = F.cross_entropy(logits, target[keep], reduction="none")
                per_question = torch.zeros(index.numel(), device=device).index_add(0, owner, token_ce)
                per_question = per_question / keep.sum(1).clamp_min(1)
                wrong = torch.zeros(index.numel(), device=device).index_add(
                    0, owner, (logits.argmax(-1) != target[keep]).float())
                correct = (wrong == 0).float()
                if gold is not None:
                    have_all = ~(gold[index] & ~episode.fetched[index]).any(1)
                    scale = torch.where(have_all, 1.0, config.early_ans)
                else:
                    scale = torch.ones_like(per_question)   # soft-no-oracle: the early_ans scale is 1.0
                ans_terms.append(scale * per_question)
                halt_terms.append(F.binary_cross_entropy_with_logits(halt, correct, reduction="none"))
                if step == 0:
                    metrics["answer_acc_first"] = correct.mean().detach()
                last = n_loops[index] == step + 1
                if last.any():
                    metrics.setdefault("_final", []).append(correct[last].detach())
                if store is None:
                    continue
                if self.soft_no_oracle:                                                  # EDITED
                    # ---- EDITED: the oracle-free arm. No L_ask at all; one SOFT row per loop; the ASK
                    # decision is forced on (self.force_ask), so there is no gate on the pick.
                    if step == 0:
                        with torch.no_grad():
                            metrics["recall_at_k"] = self._recall(
                                store, episode, index, rows, diag_gold).detach()
                            share = torch.softmax(scores.float(), dim=1)
                            metrics["ask_entropy"] = -(share * share.clamp_min(1e-12).log()).sum(1).mean()
                    going = n_loops[index] > step + 1
                    if not going.any():
                        continue
                    cards = store.top(scores.detach(), 1)       # argmax; detached -> hard book-keeping only
                    cards = cards.masked_fill(~going.unsqueeze(1), -1)
                    self.insert_with(episode, store, index, cards, scores, "soft")
                    continue
                # L_ask: set cross-entropy over G minus F, plus BCE on the ASK logit.
                need = gold[index] & ~episode.fetched[index]
                asks = need.any(1)
                bce_terms.append(F.binary_cross_entropy_with_logits(ask, asks.float(), reduction="none"))
                if asks.any():
                    set_terms.append(set_cross_entropy(scores[asks], need[asks]))
                if step == 0:
                    metrics["recall_at_k"] = self._recall(store, episode, index, rows, gold).detach()
                # Fetch for the next loop.
                going = n_loops[index] > step + 1
                if mode == "gold" or not going.any():
                    continue
                cards = self._teacher_cards(store, episode, index, need, gold[index], generator)
                if mode == "own" and p_own > 0:
                    own = store.top(scores.detach(), config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
                    own = F.pad(own, (0, cards.shape[1] - own.shape[1]), value=-1)
                    pick = torch.rand(index.numel(), device=device, generator=generator) < p_own
                    cards = torch.where(pick.unsqueeze(1), own, cards)
                cards = cards.masked_fill(~going.unsqueeze(1), -1)
                if self.answer_grad:                                                     # EDITED
                    self.insert_with(episode, store, index, cards, scores, "st")          # EDITED
                else:
                    self._insert(episode, store, index, cards)

            l_ans = torch.cat(ans_terms).sum() / pairs
            l_halt = torch.cat(halt_terms).mean()
            l_ask = zero
            if bce_terms:
                l_ask = torch.cat(bce_terms).mean()
                if set_terms:
                    l_ask = l_ask + torch.cat(set_terms).mean()
            final = metrics.pop("_final")
            metrics["answer_acc"] = torch.cat(final).mean()
            metrics["question_loops"] = torch.tensor(pairs)
            losses = {"lm": l_lm, "ask": l_ask, "ans": l_ans, "halt": l_halt}
            total = sum(weights.get(name, 0.0) * value for name, value in losses.items())
            return {**losses, "loss": total, "metrics": metrics}

    _CLASS = SoftReadCardBypassMini
    return _CLASS


def build(arm: str, seed: int, early_ans: float = 0.2, *, answer_grad: bool = False,
          soft_no_oracle: bool = False, force_ask=None):
    """`R.build`'s model for `arm`, as the soft-read subclass: same init, IDENTICAL state_dict.

    `force_ask` defaults to `soft_no_oracle` (that arm never trains the ASK head, so its decision is
    replaced by a constant in training and in evaluation).
    """
    _imports()
    from premonition.model import PremonitionMini
    if not R.ARMS[arm]["bypass"]:
        raise SystemExit("the soft-read arms are only wired for the card-bypass arms")
    torch.manual_seed(seed)
    base = PremonitionMini(R.config_for(arm, early_ans))
    model = softread_class()(base.config)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    if missing or unexpected:
        raise RuntimeError(f"soft-read variant state mismatch {missing} / {unexpected}")
    model.answer_grad = bool(answer_grad)
    model.soft_no_oracle = bool(soft_no_oracle)
    model.force_ask = bool(soft_no_oracle if force_ask is None else force_ask)
    return model


def load_from(name: str, ckpt_dir=None):
    """Rebuild a checkpoint written by this launcher, including its forced-ASK behaviour."""
    _imports()
    from premonition import answer_path
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    blob = torch.load(Path(ckpt_dir or (OUT / "ckpt")) / f"{name}.pt", weights_only=False)
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    if blob.get("answer_grad") or blob.get("soft_no_oracle"):
        model = softread_class()(config)
        model.answer_grad = bool(blob.get("answer_grad"))
        model.soft_no_oracle = bool(blob.get("soft_no_oracle"))
        model.force_ask = bool(blob.get("force_ask"))
    else:
        model = (answer_path.CardBypassMini if R.ARMS[blob["arm"]]["bypass"] else PremonitionMini)(config)
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model, blob


# ----------------------------------------------------------------------------- soft-read evaluation
def own_fixed_soft(model, batch, loops: int):
    """`R.own_fixed`, copied, but every fetch inserts the SOFT mixture row instead of the hard top-1.

    This is the training-time read, scored at evaluation time, so the soft -> hard gap is visible. The ASK
    gate is the model's (forced on for the soft-no-oracle arm, exactly as in training).
    """
    _imports()
    from learnlab.core import IGNORE_INDEX as _ignore
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    for step in range(loops):
        rows, halt, ask, scores = model._step(episode, everyone, step, store)
        if store is not None and step + 1 < loops:
            cards = store.top(scores, 1).masked_fill((ask <= 0).unsqueeze(1), -1)      # EDITED: one row
            model.insert_with(episode, store, everyone, cards, scores, "soft")         # EDITED: soft row
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    ok = torch.tensor([tokens[q, :int(lengths[q])].tolist()
                       == batch.answer[q][batch.answer[q] != _ignore].tolist()
                       for q in range(batch.answer.shape[0])])
    if store is None:
        return ok, torch.zeros_like(ok)
    gold = batch.gold_lines
    fetched = episode.fetched.gather(1, gold.clamp_min(0)) | (gold < 0)
    return ok, fetched.all(1)


def soft_read_report(model, items) -> dict:
    """`{"fixed_K2": ..., "fixed_K3": ..., "fixed_K4": ...}` scored with the soft read, by hop."""
    _imports()
    was = model.training
    model.eval()
    out = {}
    with torch.no_grad():
        for k in (2, 3, 4):
            out[f"fixed_K{k}"] = R.by_hop(items, lambda b, k=k: own_fixed_soft(model, b, k))
    model.train(was)
    return out


# ----------------------------------------------------------------------------- the trainer
def make_softread_trainer(base_cls):
    """`base_cls` (from `G.make_trainer_class`) with two additions the frozen trainer cannot give us without
    editing it: it remembers the last step's metrics (so the launcher can log the ASK entropy and the argmax
    recall, which the frozen `train()` record does not carry), and it calls `on_checkpoint(step)` every
    `ckpt_every` steps. The frozen `train()` only offers `on_log` (every `log_every` steps) and `evaluate`
    (which runs under `read_only`), so the hook lives in `_train_step`, which runs exactly once per step."""
    class SoftReadTrainer(base_cls):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.last_metrics: dict = {}
            self.ckpt_every = 0
            self.on_checkpoint = None
            self._pending_cost = 0.0

        def batch_cost(self, batch, plan):
            cost, loops = super().batch_cost(batch, plan)
            self._pending_cost = float(cost)     # the cost train() will add AFTER _train_step returns
            return cost, loops

        def _train_step(self, batch, *args, **kwargs):
            result = super()._train_step(batch, *args, **kwargs)
            self.last_metrics = result.get("metrics", {}) or {}
            if self.ckpt_every and self.on_checkpoint is not None and self.step % self.ckpt_every == 0:
                self.on_checkpoint(self.step, self.post_step_state(batch, result))
            return result

        def post_step_state(self, batch, result) -> dict:
            """`self.state_dict()` as it will be once the frozen `train()` loop finishes this iteration.

            `_train_step` increments `self.step` but the FLOP and token counters are added by `train()`
            AFTER it returns, so a checkpoint taken here would restore a trainer one step behind on the
            curriculum clock (`plan()` reads `flops / flop_budget`) -- which is exactly what made an early
            version of this resume drift into the wrong phase. The counters are reconstructed instead.
            """
            state = self.state_dict()
            state["flops"] = float(self.flops) + float(self._pending_cost)
            state["tokens"] = int(self.tokens) + int(batch.lengths.sum())
            state["padded_tokens"] = int(self.padded_tokens) + int(batch.tokens.numel())
            state["question_loops"] = int(self.question_loops) + int(result["metrics"]["question_loops"])
            state["questions"] = int(self.questions) + int(batch.q_visit.shape[0])
            return state

    return SoftReadTrainer


def latest_step_checkpoint(ckpt_dir, name: str):
    """(path, step) of the newest `<name>-step<K>.pt` under `ckpt_dir`, or (None, 0)."""
    best, best_step = None, 0
    for path in sorted(Path(ckpt_dir).glob(f"{name}-step*.pt")):
        match = STEP_CKPT.search(path.name)
        if match and int(match.group(1)) >= best_step:
            best, best_step = path, int(match.group(1))
    return best, best_step


def save_atomic(blob: dict, path: Path) -> Path:
    """torch.save to a temporary name in the same directory, then rename, so a reader never sees a partial
    file and an interrupted save cannot destroy an earlier checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-{}".format(os.getpid()))
    torch.save(blob, tmp)
    os.replace(tmp, path)
    return path


def run(args) -> dict:
    import torch as _torch
    from premonition import answer_path
    from premonition.train import Curriculum, budget_for_steps, mini_train_config
    _imports()

    if args.answer_grad and args.soft_no_oracle:
        raise SystemExit("--answer-grad and --soft-no-oracle are separate arms; run them one at a time")
    if args.device == "cuda" and not _torch.cuda.is_available():
        raise SystemExit("cuda requested but torch.cuda.is_available() is False")
    autocast_on = args.autocast == "on"
    arm_tag = ("answer-grad" if args.answer_grad else
               "soft-no-oracle" if args.soft_no_oracle else "baseline")
    name = args.name or "{}-{}-s{}-{}".format(arm_tag, args.arm, args.seed, args.steps)
    started = time.perf_counter()
    out_dir = Path(args.out).expanduser() if args.out else OUT

    early_ans = 1.0 if args.soft_no_oracle else args.early_ans
    if args.answer_grad or args.soft_no_oracle:
        model = build(args.arm, args.seed, early_ans, answer_grad=args.answer_grad,
                      soft_no_oracle=args.soft_no_oracle)
    else:
        model = R.build(args.arm, args.seed, early_ans)     # literally the baseline / noask control

    if args.soft_no_oracle:
        curriculum = Curriculum(**SOFT_CURRICULUM)
        recipe = dict(SOFT_CURRICULUM)
    else:
        curriculum = Curriculum(gold_until=args.gold_until, teacher_until=args.teacher_until,
                                ramp_until=args.ramp_until)
        recipe = dict(gold_until=args.gold_until, teacher_until=args.teacher_until,
                      ramp_until=args.ramp_until, p_own_max=curriculum.p_own_max)
    table = oracle_use(arm_tag, bool(model.config.store))

    cls = make_softread_trainer(G.make_trainer_class(autocast_on, args.lr_cooldown, args.steps))
    trainer = cls(model, mini_train_config(lr=args.lr, warmup_steps=args.warmup,
                                           log_every=args.log_every, eval_every=0),
                  args.device, flop_budget=1.0, seed=args.seed, curriculum=curriculum)
    stream = (item[0] for item in L.checked_train())
    head = [next(stream) for _ in range(2)]
    trainer.calibrate(head)                      # deterministic in the trainer's own fresh generator
    trainer.flop_budget = budget_for_steps(trainer, head, args.steps)

    def state_blob(step=None, trainer_state=None) -> dict:
        """The checkpoint blob. With `step` it also carries everything a resume needs."""
        blob = {"state_dict": model.state_dict(), "config": asdict(model.config), "arm": args.arm,
                "seed": args.seed, "training_arm": arm_tag,
                "answer_grad": bool(args.answer_grad),
                "soft_no_oracle": bool(args.soft_no_oracle),
                "force_ask": bool(getattr(model, "force_ask", False)),
                "model_class": type(model).__name__,
                "curriculum": recipe, "early_ans": early_ans,
                "steps_requested": int(args.steps),
                "oracle_use": table,
                "lr_cooldown": float(args.lr_cooldown)}
        if step is not None:
            blob.update(step=int(step), kind="periodic",
                        trainer_state=trainer.state_dict() if trainer_state is None else trainer_state,
                        optimizer_state=trainer.optimizer.state_dict())
        return blob

    def save_step(step: int, trainer_state) -> None:
        save_atomic(state_blob(step, trainer_state),
                    out_dir / "ckpt" / "{}-step{:06d}.pt".format(name, step))

    resumed_from = None
    skip = 0
    if args.resume:
        path, step = latest_step_checkpoint(out_dir / "ckpt", name)
        if path is None:
            print("no periodic checkpoint for {} yet: starting from scratch".format(name), flush=True)
        else:
            blob = _torch.load(path, weights_only=False)
            if int(blob.get("steps_requested", args.steps)) != int(args.steps):
                raise SystemExit("--resume needs the same --steps as the interrupted run "
                                 "({} in {})".format(blob.get("steps_requested"), path.name))
            model.load_state_dict(blob["state_dict"])       # in place: the optimizer keeps its parameters
            trainer.optimizer.load_state_dict(blob["optimizer_state"])
            trainer.load_state_dict(blob["trainer_state"])  # step, flops, tokens AND the RNG state
            skip = trainer.step
            resumed_from = str(path.name)
            print("resumed {} at step {} ({:.1f}% of the FLOP budget)".format(
                name, trainer.step, 100.0 * trainer.flops / trainer.flop_budget), flush=True)
    trainer.ckpt_every = max(0, int(args.ckpt_every))
    trainer.on_checkpoint = save_step if trainer.ckpt_every else None

    # One batch per step, in a fixed order, so a resume replays the stream by skipping `trainer.step` items.
    # (A run stopped by the FLOP budget consumes one extra, untrained batch, but nothing resumes from there.)
    batches = itertools.chain(head, stream)
    for _ in range(skip):
        next(batches)

    curve = []

    def on_log(entry) -> None:
        keep = {k: entry.get(k) for k in (
            "step", "phase", "p_own", "lr", "loss", "lm", "ask", "ans", "halt",
            "gold_recall_at_4", "answer_acc", "loops_per_question", "halt_rate")}
        extra = trainer.last_metrics or {}
        if "ask_entropy" in extra:
            keep["ask_entropy"] = float(extra["ask_entropy"])          # the window's LAST step
        if "recall_at_k" in extra:
            keep["argmax_recall_last_step"] = float(extra["recall_at_k"])
        kappa = getattr(model.heads, "log_kappa", None)    # None for the no-store control
        keep["kappa"] = None if kappa is None else float(kappa.detach().exp())
        curve.append(keep)
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v)
                          for k, v in keep.items()}), flush=True)

    train_started = time.perf_counter()
    report = trainer.train(batches, max_seconds=args.max_seconds, max_steps=args.max_steps, on_log=on_log)
    if args.device == "cuda":
        _torch.cuda.synchronize()
    train_seconds = time.perf_counter() - train_started
    steps_done = int(report.get("steps") or 0)
    steps_per_s = steps_done / max(train_seconds, 1e-9)
    print("TIMING {}: {} steps in {:.1f} s = {:.3f} steps/s (threads {})".format(
        name, steps_done, train_seconds, steps_per_s, args.threads), flush=True)

    peak_bytes = _torch.cuda.max_memory_allocated() if args.device == "cuda" else None
    model = model.to("cpu").float()

    validation = None
    soft_read = None
    if not args.skip_eval:
        items = L.load_split("validation")
        validation = R.evaluate(model, items)
        if args.soft_no_oracle:
            soft_read = soft_read_report(model, items)

    ident = (answer_path.identity(answer_path.CARD_BYPASS, model.config) if R.ARMS[args.arm]["bypass"]
             else {"variant": model.config.variant, "purpose": "diagnostic"})
    ident = dict(ident, arm=args.arm, training_arm=arm_tag)
    if args.answer_grad:
        ident = dict(ident, answer_grad=True,
                     privilege="L_ask trained on oracle evidence lines (as D)",
                     note="straight-through answer gradient: inserted card rows carry the soft mixture's "
                          "gradient (forward values unchanged), so L_ans also trains the query head, kappa, "
                          "the age bias and the card keys")
    elif args.soft_no_oracle:
        ident = dict(ident, soft_no_oracle=True,
                     privilege="NONE: no simulator evidence label reaches any gradient (w_ask = 0, no gold "
                               "phase, no teacher insertions, early_ans scale 1.0)",
                     note="training inserts the softmax mixture row (values + mixed age embedding); the "
                          "argmax card is marked fetched; soft rows are not bound to entity slots; the ASK "
                          "decision is forced on (logit {}) in training and in evaluation".format(
                              FORCED_ASK_LOGIT))
    else:
        ident = dict(ident, privilege="L_ask trained on oracle evidence lines (as D)",
                     note="matched baseline / no-store control through the soft-read launcher")

    (out_dir / "runs").mkdir(parents=True, exist_ok=True)
    path = save_atomic(dict(state_blob(), identity=ident, kind="final", step=trainer.step),
                       out_dir / "ckpt" / (name + ".pt"))
    periodic = sorted(p.name for p in (out_dir / "ckpt").glob(f"{name}-step*.pt"))
    result = {
        "name": name, "training_arm": arm_tag, "arm": args.arm,
        "arm_settings": {k: list(v) if isinstance(v, tuple) else v for k, v in R.ARMS[args.arm].items()},
        "max_loops": R.MAX_LOOPS, "seed": args.seed, "steps_requested": args.steps,
        "device": args.device, "autocast": "bf16" if autocast_on else "off",
        "threads": args.threads,
        "answer_grad": bool(args.answer_grad), "soft_no_oracle": bool(args.soft_no_oracle),
        "force_ask": bool(getattr(model, "force_ask", False)),
        "oracle_use": table,
        "lr_cooldown": float(args.lr_cooldown),
        "trainer_class": cls.__name__, "model_class": type(model).__name__,
        "curriculum": {**recipe, "early_ans": early_ans},
        "ckpt_every": int(args.ckpt_every), "resumed_from": resumed_from,
        "periodic_checkpoints": periodic, "max_steps": args.max_steps,
        "torch_version": _torch.__version__, "python": sys.version.split()[0],
        "platform": platform.platform(),
        "gpu_name": _torch.cuda.get_device_name(0) if args.device == "cuda" else None,
        "peak_gpu_allocated_bytes": peak_bytes,
        "train_report": {k: v for k, v in report.items()
                         if isinstance(v, (int, float, str, bool, type(None)))},
        "steps_done": steps_done, "steps_per_second": round(steps_per_s, 4),
        "curve": curve, "validation": validation, "soft_read": soft_read,
        "seconds_train": round(train_seconds, 2), "seconds_total": round(time.perf_counter() - started, 2),
        "identity": ident,
        "ckpt": str(path.relative_to(L.ROOT)) if L.ROOT in path.parents else str(path),
        "ckpt_sha256": L.sha256(path),
        "command": " ".join(sys.argv),
        "evaluated_on": None if args.skip_eval else "validation (CPU, premonition_ovn_retrieval.evaluate)",
    }
    (out_dir / "runs" / (name + ".json")).write_text(json.dumps(result, indent=1, default=str))
    if validation is not None:
        R.show(validation)
    if soft_read is not None:
        print("--- soft read (the training-time read, scored) ---", flush=True)
        R.show(soft_read)
    print("done {}: arm {} device {} train {:.1f} s, total {:.1f} s".format(
        name, arm_tag, args.device, train_seconds, result["seconds_total"]), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=sorted(R.ARMS), default="bypass-k1")
    parser.add_argument("--answer-grad", action="store_true",
                        help="straight-through answer gradient: card rows inserted after a step carry the "
                             "soft mixture's gradient (forward values are bit-identical to the baseline)")
    parser.add_argument("--soft-no-oracle", action="store_true",
                        help="no simulator evidence label in any gradient: no gold phase, no teacher, "
                             "p_own = 1.0 from step 0, w_ask = 0, early_ans scale 1.0, ASK forced on, and "
                             "soft mixture rows during training")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--autocast", choices=("on", "off"), default="off")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument("--name")
    parser.add_argument("--gold-until", type=float, default=0.05)
    parser.add_argument("--early-ans", type=float, default=0.2)
    parser.add_argument("--teacher-until", type=float, default=0.30)
    parser.add_argument("--ramp-until", type=float, default=0.60)
    parser.add_argument("--lr-cooldown", type=float, default=0.0)
    parser.add_argument("--max-steps", type=int, default=None,
                        help="stop after this many steps IN THIS PROCESS (the FLOP budget still comes from "
                             "--steps); used to interrupt a run on purpose")
    parser.add_argument("--ckpt-every", type=int, default=1000,
                        help="save a recoverable checkpoint every N steps as <name>-step<K>.pt (atomic "
                             "write + rename; every intermediate state is kept -- they are ~1 MB -- so "
                             "probes can watch the card-pooling weights move); 0 disables it")
    parser.add_argument("--resume", action="store_true",
                        help="continue from the newest <name>-step<K>.pt in the output directory (model, "
                             "optimizer, step, FLOPs spent, RNG state and the data stream position)")
    parser.add_argument("--skip-eval", action="store_true",
                        help="train only and report steps/second (timing mode; still writes the checkpoint)")
    parser.add_argument("--out", default=None,
                        help="output directory (default artifacts/claude-softread-20260919)")
    parser.add_argument("--self-check", action="store_true",
                        help="run tests/test_premonition_softread.py instead of training")
    args = parser.parse_args()
    L.bootstrap()
    if args.self_check:
        sys.path.insert(0, str(L.ROOT / "tests"))
        from test_premonition_softread import main as _main
        raise SystemExit(_main())
    import torch as _torch
    _torch.set_num_threads(args.threads)
    run(args)


if __name__ == "__main__":
    main()
