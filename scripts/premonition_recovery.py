"""Opt-in card recovery candidates; preserves the hash-checked historical implementation.

Implements the pooled request contract in design/v3/07-final-resolution.md.
The independent switches are separate key pooling, pooled address selectors, and
score-only straight-through (ST) answer credit. These are candidates, not a claim
that reliability or held-out composition is solved. No relation location or role
label is supplied to the selectors. Legacy evidence supervision remains disclosed.

Call L.bootstrap() before build/load; run this file with --help for the CPU/CUDA
runner. Only validation is loaded. Existing checkpoints and reports are untouched.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L
import premonition_ovn_retrieval as R
import premonition_softread as S

_CLASS = None
FORMAT = "premonition-recovery-v1"


def recovery_class():
    global _CLASS
    if _CLASS is not None:
        return _CLASS
    import torch
    from torch import nn
    import torch.nn.functional as F
    from premonition.model import _norm

    class AddressSelectors(nn.Module):
        def __init__(self, config):
            super().__init__()
            d = config.d_model
            self.queries = nn.ModuleList(nn.Linear(d, d, bias=False) for _ in range(2))
            self.keys = nn.ModuleList(nn.Linear(d, d, bias=False) for _ in range(2))
            self.nulls = nn.ModuleList(nn.Linear(d, 1) for _ in range(2))
            self.compose = nn.Linear(2 * d, config.key_dim)
            for layer in self.modules():
                if isinstance(layer, nn.Linear):
                    nn.init.normal_(layer.weight, std=0.02)
                    if layer.bias is not None:
                        nn.init.zeros_(layer.bias)

        def forward(self, register, candidates, valid, *, hard=False):
            contents = torch.cat([candidates.float(), torch.zeros_like(candidates[:, :1])], 1)
            reads, attention = [], []
            for query, key, null in zip(self.queries, self.keys, self.nulls):
                scores = torch.einsum("nd,nrd->nr", query(register).float(), key(candidates).float())
                scores = (scores / math.sqrt(register.shape[-1])).masked_fill(~valid, -torch.inf)
                scores = torch.cat([scores, null(register).float()], 1)
                weight = scores.softmax(1)
                if hard:
                    weight = F.one_hot(weight.argmax(1), weight.shape[1]).float()
                reads.append(torch.einsum("nr,nrd->nd", weight, contents))
                attention.append(weight)
            return F.normalize(self.compose(torch.cat(reads, -1)).float(), dim=-1), torch.stack(attention, 1)

    class RecoveryMini(S.softread_class()):
        def __init__(self, config, *, request="legacy", score_only_st=False):
            if request not in ("legacy", "pooled"):
                raise ValueError("request must be legacy or pooled")
            if not config.store or not config.cards or config.registers < 2:
                raise ValueError("recovery requires a card store and at least two registers")
            super().__init__(config)
            self.request_mode = request
            self.score_only_st = bool(score_only_st)
            self.answer_grad = self.score_only_st
            self.hard_selectors = False
            if request == "pooled":
                self.heads.address = AddressSelectors(config)

        def _start(self, batch, hidden, store, mentions):
            episode = super()._start(batch, hidden, store, mentions)
            if self.request_mode == "pooled":
                # Original contextual question states, before row-type additions or Think.
                pos = batch.q_span[:, 1, None] - self.config.question_rows
                pos = pos + torch.arange(self.config.question_rows, device=hidden.device)
                episode.request_question = hidden[batch.q_visit[:, None], pos.clamp_min(0)].float()
                episode.request_valid = episode.valid[:, :self.config.question_rows].clone()
                episode.request_cards = torch.zeros_like(episode.inserted)
            return episode

        def _insert(self, episode, store, index, cards):
            if self.request_mode != "pooled":
                return super()._insert(episode, store, index, cards)
            # Use the same ring positions as the ordinary workspace, but preserve raw
            # pooled values (without age/type additions, binding, or Think mutation).
            real = cards >= 0
            order = real.long().cumsum(1) - 1
            position = (episode.count[index, None] + order) % self.config.card_rows
            values, _, _ = store.gather(cards, episode.q_visit[index])
            if self.insert_mode == "st":
                soft_value, _ = self._soft_parts(store, episode, index)
                values = values.float() + (soft_value - soft_value.detach())[:, None]
            super()._insert(episode, store, index, cards)
            owner = index[:, None].expand_as(cards)
            episode.request_cards = episode.request_cards.index_put(
                (owner[real], position[real]), values.float()[real])

        def _request(self, episode, index, rows):
            candidates = torch.cat([episode.request_question[index], episode.request_cards[index]], 1)
            valid = torch.cat([episode.request_valid[index], episode.valid[index, self._card_slice]], 1)
            register = _norm(rows[:, self._register_base + 1])
            return self.heads.address(register, candidates, valid, hard=self.hard_selectors)

        def _step(self, episode, index, step, store):
            if self.request_mode == "legacy":
                return super()._step(episode, index, step, store)
            self._reading = (episode, index)
            rows = self.think(episode.x[index], episode.valid[index], step)
            episode.x = episode.x.index_copy(0, index, rows.to(episode.x.dtype))
            control = _norm(rows[:, self._register_base])
            halt = self.heads.halt(control).squeeze(-1).float()
            ask = self.heads.ask(control).squeeze(-1).float()
            query, _ = self._request(episode, index, rows)
            scores = store.ask(query, episode.q_visit[index], episode.q_line[index],
                               self.heads.log_kappa.exp(), self.think.age_bias,
                               episode.fetched[index], questions=index)
            return rows, halt, ask, scores

        def _recall(self, store, episode, index, rows, gold):
            if self.request_mode == "legacy":
                return super()._recall(store, episode, index, rows, gold)
            told = gold[index, :store.null].any(1)
            if not told.any():
                return rows.new_zeros(())
            query, _ = self._request(episode, index, rows)
            scores = store.ask(query, episode.q_visit[index], episode.q_line[index],
                               self.heads.log_kappa.exp(), self.think.age_bias, questions=index)
            top = store.top(scores, self.config.top_k)
            hit = (gold[index].gather(1, top.clamp_min(0)) & (top >= 0)).sum(1).float()
            return (hit / gold[index].sum(1).clamp_min(1))[told].mean()

        def _soft_parts(self, store, episode, index):
            if not self.score_only_st or self.insert_mode != "st":
                return super()._soft_parts(store, episode, index)
            # A biased surrogate for retrieval scores only: no EXTRA gradient to
            # fetched values or the age embeddings through the soft companion.
            if self._ins_scores is None:
                raise RuntimeError("score-only ST needs the preceding retrieval scores")
            weight = self._ins_scores.float().softmax(1)
            values = torch.cat([store.values[episode.q_visit[index]].float(),
                                store.null_value.float().expand(index.numel(), 1, -1)], 1).detach()
            value = torch.einsum("nl,nld->nd", weight, values)
            return value, torch.zeros_like(value)

    _CLASS = RecoveryMini
    return _CLASS


def build(seed=0, *, request="legacy", key_pool=False, score_only_st=False):
    base = R.build("bypass-k1", seed)
    model = recovery_class()(base.config, request=request, score_only_st=score_only_st)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    expected = [name for name in model.state_dict() if name.startswith("heads.address.")]
    if sorted(missing) != sorted(expected) or unexpected:
        raise RuntimeError(f"unexpected recovery state mismatch: {missing} / {unexpected}")
    if key_pool:
        import premonition_key_pool as KP
        KP.apply_key_pool(model)
    model.recovery_options = dict(request=request, key_pool=bool(key_pool), score_only_st=bool(score_only_st))
    return model


def load(path):
    import torch
    blob = torch.load(path, map_location="cpu", weights_only=False)
    return from_blob(blob), blob


def from_blob(blob):
    from premonition.config import MiniConfig
    if blob.get("format") != FORMAT:
        raise ValueError("not a recovery checkpoint")
    options = blob["recovery_options"]
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    model = recovery_class()(config, request=options["request"], score_only_st=options["score_only_st"])
    if options["key_pool"]:
        import premonition_key_pool as KP
        KP.apply_key_pool(model)
    model.load_state_dict(blob["state_dict"], strict=True)
    model.recovery_options = dict(options)
    model.eval()
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", choices=("legacy", "pooled"), default="legacy")
    parser.add_argument("--key-pool", action="store_true")
    parser.add_argument("--score-only-st", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--data-seed", type=int, help="independent training-world stream; omitted uses historical stream")
    parser.add_argument("--steps", type=int, required=True, help="maximum actual optimizer updates")
    parser.add_argument("--flop-budget", type=float, help="shared cap for matched-compute comparisons")
    parser.add_argument("--max-seconds", type=float, default=1200)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--skip-eval", action="store_true")
    parser.add_argument("--out", type=Path, required=True, help="new output directory; never overwrites a run")
    args = parser.parse_args()
    if args.steps < 1 or args.threads < 1 or not 0 < args.max_seconds <= 1200:
        parser.error("positive steps/threads and a training cap of 1..1200 seconds are required")
    if args.flop_budget is not None and (not math.isfinite(args.flop_budget) or args.flop_budget <= 0):
        parser.error("--flop-budget must be finite and positive")
    if args.out.exists():
        parser.error("--out already exists; choose a new run directory")
    L.bootstrap()
    import torch
    import premonition_gpu_port as G
    from premonition.train import Curriculum, budget_for_steps, mini_train_config
    torch.set_num_threads(args.threads)
    args.out.mkdir(parents=True)
    started = time.perf_counter()
    (args.out / "manifest.json").write_text(json.dumps(dict(
        format=FORMAT, status="started", arguments=vars(args)), indent=2, default=str) + "\n")
    model = build(args.seed, request=args.request, key_pool=args.key_pool, score_only_st=args.score_only_st)
    curriculum = Curriculum(gold_until=0.10, teacher_until=0.1833, ramp_until=0.2667)
    trainer = G.make_trainer_class(False)(model, mini_train_config(lr=1e-3, warmup_steps=100,
                                                               log_every=50, eval_every=0),
                                         args.device, flop_budget=1.0, seed=args.seed, curriculum=curriculum)
    if args.data_seed is None:
        stream = (item[0] for item in L.checked_train())
    else:
        from premonition import toy_ladder
        from premonition.train import label_free
        rng = random.Random(args.data_seed)
        stream = (label_free(toy_ladder.make(L.spec(), L.VISITS, rng, training=True,
                                            prefix=f"recovery-{args.data_seed}")[0]) for _ in itertools.count())
    head = [next(stream) for _ in range(2)]
    trainer.calibrate(head)
    trainer.flop_budget = args.flop_budget or budget_for_steps(trainer, head, args.steps)
    curve = []
    report = trainer.train(itertools.chain(head, stream), max_steps=args.steps,
                           max_seconds=args.max_seconds, on_log=curve.append)
    model.to("cpu").float()
    blob = dict(format=FORMAT, config=asdict(model.config), state_dict=model.state_dict(),
                recovery_options=model.recovery_options, seed=args.seed, data_seed=args.data_seed,
                arm="bypass-k1", model_class=type(model).__name__, key_pool=args.key_pool,
                steps_done=trainer.step)
    S.save_atomic(blob, args.out / "model.pt")
    validation = None if args.skip_eval else R.evaluate(model, L.load_split("validation"))
    hard_validation = None
    if validation is not None and args.request == "pooled":
        model.hard_selectors = True
        try:
            hard_validation = R.evaluate(model, L.load_split("validation"))
        finally:
            model.hard_selectors = False
    completed = (trainer.step == args.steps if args.flop_budget is None else
                 report["stop"].startswith("flop budget") and report["budget_ok"])
    import premonition_key_pool as KP
    sources = (Path(__file__).resolve(), Path(S.__file__), Path(G.__file__), Path(KP.__file__),
               Path(R.__file__), Path(L.__file__), L.ARCHIVE / "FROZEN.SHA256SUMS")
    result = dict(format=FORMAT, status="complete" if completed else "incomplete",
                  recovery_options=model.recovery_options, seed=args.seed, data_seed=args.data_seed,
                  steps_requested=args.steps, steps_done=trainer.step, report=report,
                  flop_budget=trainer.flop_budget, curriculum=asdict(curriculum), curve=curve,
                  parameters=model.num_parameters(), validation=validation,
                  hard_selector_validation=hard_validation,
                  oracle_use=S.oracle_use("baseline", True),
                  supplied_relation_location=False,
                  request_candidate_rows=model.config.question_rows + model.config.cards + 1
                      if args.request == "pooled" else 0,
                  extra_saved_candidate_bytes_per_question=(
                      4 * model.config.d_model * (model.config.question_rows + model.config.cards)
                      + model.config.question_rows) if args.request == "pooled" else 0,
                  soft_companion_access="all eligible cards on each ST insertion" if args.score_only_st else None,
                  seconds_total=time.perf_counter() - started,
                  source_sha256={str(p.relative_to(L.ROOT)): L.sha256(p) for p in sources},
                  checkpoint_sha256=L.sha256(args.out / "model.pt"),
                  reliability_claim=False)
    (args.out / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (args.out / "manifest.json").write_text(json.dumps(dict(
        format=FORMAT, status=result["status"], arguments=vars(args), result="result.json"),
        indent=2, default=str) + "\n")
    print(json.dumps(dict(steps_done=trainer.step, stop=report["stop"], out=str(args.out)), indent=2))
    return 0 if completed else 2


if __name__ == "__main__":
    raise SystemExit(main())
