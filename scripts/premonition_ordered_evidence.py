"""Ordered evidence supervision (Claude, 2026-09-19) -- ADDITIVE screen-2 variant.

The frozen model supervises retrieval with a SET target over every gold card not yet fetched, and its
teacher inserts up to top_k RANDOM needed gold cards. For a two-hop question "a LINK r?" that means the
step-0 target already contains the answer card A(friend, r), which cannot be identified before the friend
is known, and with top_k = 1 the teacher hands over the answer card first about half the time.

This module subclasses `answer_path.CardBypassMini` (the class arm `bypass-k1` uses) and restricts, at
every loop, BOTH the set cross-entropy target AND the teacher's choice to the NEXT REACHABLE gold card:
the first not-yet-fetched gold line in `batch.gold_lines` order. On this data gold_lines[q, 0] is the link
card and gold_lines[q, 1] the answer card for two-hop questions; one-hop questions have a single gold line
and are unchanged. Everything else is identical to the frozen forward: the ASK BCE target is still "ask
while ANY gold card is missing", HALT, L_ans, L_lm, distractors, own/teacher mixing, curriculum, optimiser
and data are untouched. This uses the oracle's hop ORDER during training only -- a disclosed extra
privilege on top of the oracle evidence lines D already trains on. Nothing changes at inference: no new
parameters, no new buffers, the state_dict is identical to the baseline's.

`forward` below is the frozen `PremonitionMini.forward` (archive/opus-ovn-20260918-235851/frozen/
premonition/model.py lines 503-630) copied verbatim, with every changed line marked "EDITED". With
`ordered_evidence = False` the copy runs the frozen code path exactly (the parity test checks this).

    PY -B scripts/premonition_ordered_evidence.py --self-check
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

torch = None
F = None
MODES = None
set_cross_entropy = None
IGNORE_INDEX = None
_CLASS = None


def _imports() -> None:
    """Pull the frozen names into this module's globals (only valid after L.bootstrap())."""
    global torch, F, MODES, set_cross_entropy, IGNORE_INDEX
    import torch as _torch
    import torch.nn.functional as _F
    from learnlab.core import IGNORE_INDEX as _ignore
    from premonition.model import MODES as _MODES
    from premonition.store import set_cross_entropy as _sce
    torch, F, MODES, set_cross_entropy, IGNORE_INDEX = _torch, _F, _MODES, _sce, _ignore


# ------------------------------------------------------------------ ordering helpers (new)
def _ordered_columns(gold_lines, gold, told):
    """[Q, L + 1] long: the store columns of a question's gold cards IN gold_lines ORDER, -1 padding.

    A gold line that `CardStore.gold` could not map is dropped (it is not in G either); a question that was
    never told gets the single NULL column, which is exactly what G holds for it.
    """
    null = gold.shape[1] - 1
    safe = gold_lines.clamp(0, max(null - 1, 0))
    mapped = (gold_lines >= 0) & (gold_lines < null) & gold.gather(1, safe)
    cols = torch.where(mapped, safe, torch.full_like(safe, -1))
    tail = torch.where(told, torch.full_like(told, -1, dtype=torch.long),
                       torch.full_like(told, null, dtype=torch.long)).unsqueeze(1)
    return torch.cat([cols, tail], dim=1)


def _next_needed(cols, fetched, need):
    """[n, width] bool with a single True: the first column of `cols` not yet fetched (none -> all False)."""
    avail = (cols >= 0) & ~fetched.gather(1, cols.clamp_min(0))
    first = avail.to(torch.float32).argmax(1, keepdim=True)
    chosen = cols.gather(1, first).clamp_min(0)
    out = torch.zeros_like(need)
    out.scatter_(1, chosen, avail.any(1, keepdim=True))
    return out


def ordered_class():
    """The CardBypassMini subclass; built on first use so it sees the frozen package."""
    global _CLASS
    if _CLASS is not None:
        return _CLASS
    _imports()
    from premonition import answer_path

    class OrderedCardBypassMini(answer_path.CardBypassMini):
        """D-card-bypass with ordered evidence supervision (training only)."""

        ordered_evidence = True

        def forward(self, *args, **kwargs):
            # EDITED: identical to answer_path.CardBypassMini.forward, around the copied body below.
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
            metrics: dict[str, torch.Tensor] = {}
            if weights is None:
                weights = {"lm": config.w_lm, "ask": config.w_ask, "ans": config.w_ans, "halt": config.w_halt}
                if mode == "gold":
                    weights.update(ask=0.0, halt=0.0)
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
            order_cols = None                                              # EDITED (ordered evidence)
            if store is not None:
                gold, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
                metrics["gold_missing"] = missing.sum()
                if self.ordered_evidence:                                  # EDITED (ordered evidence)
                    order_cols = _ordered_columns(batch.gold_lines, gold, told)   # EDITED
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
                    scale = torch.ones_like(per_question)
                ans_terms.append(scale * per_question)
                halt_terms.append(F.binary_cross_entropy_with_logits(halt, correct, reduction="none"))
                if step == 0:
                    metrics["answer_acc_first"] = correct.mean().detach()
                last = n_loops[index] == step + 1
                if last.any():
                    metrics.setdefault("_final", []).append(correct[last].detach())
                if store is None:
                    continue
                # L_ask: set cross-entropy over G minus F, plus BCE on the ASK logit.
                need = gold[index] & ~episode.fetched[index]
                asks = need.any(1)
                bce_terms.append(F.binary_cross_entropy_with_logits(ask, asks.float(), reduction="none"))
                # EDITED (ordered evidence): the SET target is the next reachable gold card only.
                target_set = need if order_cols is None else _next_needed(
                    order_cols[index], episode.fetched[index], need)
                if asks.any():
                    set_terms.append(set_cross_entropy(scores[asks], target_set[asks]))   # EDITED: target_set
                if step == 0:
                    metrics["recall_at_k"] = self._recall(store, episode, index, rows, gold).detach()
                # Fetch for the next loop.
                going = n_loops[index] > step + 1
                if mode == "gold" or not going.any():
                    continue
                # EDITED (ordered evidence): teacher picks from target_set (== need when ordering is off).
                cards = self._teacher_cards(store, episode, index, target_set, gold[index], generator)
                if mode == "own" and p_own > 0:
                    own = store.top(scores.detach(), config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
                    own = F.pad(own, (0, cards.shape[1] - own.shape[1]), value=-1)
                    pick = torch.rand(index.numel(), device=device, generator=generator) < p_own
                    cards = torch.where(pick.unsqueeze(1), own, cards)
                cards = cards.masked_fill(~going.unsqueeze(1), -1)
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



    _CLASS = OrderedCardBypassMini
    return _CLASS


def build(arm: str, seed: int, early_ans: float = 0.2, ordered: bool = True):
    """R.build for `arm`, but with the ordered-evidence subclass; same init, same state_dict."""
    _imports()
    from premonition.model import PremonitionMini
    if not R.ARMS[arm]["bypass"]:
        raise SystemExit("ordered evidence is only wired for the card-bypass arms")
    torch.manual_seed(seed)
    base = PremonitionMini(R.config_for(arm, early_ans))
    model = ordered_class()(base.config)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    if missing or unexpected:
        raise RuntimeError(f"ordered variant state mismatch {missing} / {unexpected}")
    model.ordered_evidence = bool(ordered)
    return model


if __name__ == "__main__":
    L.bootstrap()
    sys.path.insert(0, str(L.ROOT / "tests"))
    from test_premonition_ordered_evidence import main as _main
    raise SystemExit(_main())
