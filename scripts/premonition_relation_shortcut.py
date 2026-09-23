"""Learned relation shortcut into the ASK query (Claude, 2026-09-19) -- ADDITIVE screen-3 variant.

Proposed by an outside reviewer. In the frozen model the retrieval query is

    q = W_q s,        s = norm(register 0)                  (model.py _step ~483-496, _recall ~656-666)

This module subclasses `answer_path.CardBypassMini` (the class arm `bypass-k1` uses) and replaces BOTH call
sites with

    q' = W_q s + sigmoid(w_g . s + b_g) * W_r E[REL]

where E[REL] is the model's own static token embedding (`self.embed.weight`) of the VISIBLE relation token
of the current question, `W_r` is `Linear(d_model -> key_dim, bias=False)` initialised to ZERO and the gate
`Linear(d_model -> 1)` has weight AND bias initialised to ZERO. At initialisation the query is therefore
EXACTLY the baseline's (W_r = 0), while gradients still reach W_r because sigmoid(0) = 0.5. The same path is
used for one-hop questions, two-hop questions and every loop. Keys, pooling, teacher order, losses,
retrieval rules, decoder, curriculum and optimiser are untouched.

New parameters at the tiny size (d_model = 128, key_dim = 64): 128*64 + 128 + 1 = 8,321.

DISCLOSED STRUCTURAL HINT: the relation token is read off the INPUT only. Questions are
"[question] ENT_e REL_r [answer] ..." (one-hop) and "[question] ENT_a LINK REL_r [answer] ..." (two-hop),
so the relation token is the token immediately before "[answer]", i.e. `batch.q_span[:, 1] - 2`
(`q_span[:, 1] - 1` is the "[answer]" token the frozen decoder already uses as its start token). No
simulator answer, no friend identity, no gold or need set is consulted. It is still a hint the baseline did
not get, and it is disclosed as such.

    PY -B scripts/premonition_relation_shortcut.py --self-check
    PY -B scripts/premonition_relation_shortcut.py --gates --ckpt-dir <dir> <name> [...]
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

torch = None
_norm = None
_CLASS = None

NEW_KEYS = ("rel_gate.bias", "rel_gate.weight", "rel_query.weight")


def _imports() -> None:
    """Pull the frozen names into this module's globals (only valid after L.bootstrap())."""
    global torch, _norm
    import torch as _torch
    from premonition.model import _norm as _n
    torch, _norm = _torch, _n


def relation_token_ids(batch):
    """[Q] the visible relation token of each question: the token just before "[answer]"."""
    return batch.tokens[batch.q_visit, batch.q_span[:, 1] - 2]


def shortcut_class():
    """The CardBypassMini subclass; built on first use so it sees the frozen package."""
    global _CLASS
    if _CLASS is not None:
        return _CLASS
    _imports()
    from premonition import answer_path
    from torch import nn

    class RelationShortcutCardBypassMini(answer_path.CardBypassMini):
        """D-card-bypass with a learned, gated relation-embedding shortcut into the ASK query."""

        relation_shortcut = True

        def __init__(self, config) -> None:
            super().__init__(config)
            # NEW (relation shortcut). Added AFTER PremonitionMini.__init__ has run reset_parameters(),
            # so the base model's RNG stream and initial values are untouched; both are then zeroed.
            self.rel_query = nn.Linear(config.d_model, config.key_dim, bias=False)
            self.rel_gate = nn.Linear(config.d_model, 1)
            self.zero_shortcut()
            self._gate_log = None

        def zero_shortcut(self) -> None:
            with torch.no_grad():
                self.rel_query.weight.zero_()
                self.rel_gate.weight.zero_()
                self.rel_gate.bias.zero_()

        # ------------------------------------------------------------------ the one change
        def _shortcut_query(self, register, episode, index, step=None):
            """W_q s  (+ gate * W_r E[REL] when the shortcut is on and the relation token is known)."""
            query = self.heads.query(register)
            rel = getattr(episode, "rel_token", None)
            if rel is None or not self.relation_shortcut:
                return query
            gate = torch.sigmoid(self.rel_gate(register))
            delta = self.rel_query(self.embed(rel[index]).to(register.dtype))
            if self._gate_log is not None:
                self._gate_log.append((int(step) if step is not None else -1,
                                       gate.detach().squeeze(-1).float().cpu()))
            return query + gate * delta

        def _start(self, batch, hidden, store, mentions):
            episode = super()._start(batch, hidden, store, mentions)
            episode.rel_token = relation_token_ids(batch)          # NEW (input structure only)
            return episode

        def _step(self, episode, index, step: int, store):
            """PremonitionMini._step (model.py 483-496) copied, with the query EDITED.

            The first line reproduces CardBypassMini._step, which records the episode for the decoder.
            """
            self._reading = (episode, index)
            rows = self.think(episode.x[index], episode.valid[index], step)
            episode.x = episode.x.index_copy(0, index, rows.to(episode.x.dtype))
            register = _norm(rows[:, self._register_base])
            halt = self.heads.halt(register).squeeze(-1).float()
            if store is None:
                return rows, halt, None, None
            ask = self.heads.ask(register).squeeze(-1).float()
            query = self._shortcut_query(register, episode, index, step)          # EDITED
            scores = store.ask(query, episode.q_visit[index], episode.q_line[index],
                               self.heads.log_kappa.exp(), self.think.age_bias,
                               episode.fetched[index], questions=index)
            return rows, halt, ask, scores

        def _recall(self, store, episode, index, rows, gold):
            """PremonitionMini._recall (model.py 656-666) copied, with the query EDITED."""
            told = gold[index][:, :store.null].any(1)
            if not told.any():
                return torch.zeros(())
            register = _norm(rows[:, self._register_base])
            query = self._shortcut_query(register, episode, index, None)          # EDITED
            scores = store.ask(query, episode.q_visit[index], episode.q_line[index],
                               self.heads.log_kappa.exp(), self.think.age_bias, questions=index)
            top = store.top(scores, self.config.top_k)
            hit = (gold[index].gather(1, top.clamp_min(0)) & (top >= 0)).sum(1).float()
            return (hit / gold[index].sum(1).clamp_min(1))[told].mean()

    _CLASS = RelationShortcutCardBypassMini
    return _CLASS


def build(arm: str, seed: int, early_ans: float = 0.2, shortcut: bool = True):
    """R.build for `arm`, but with the relation-shortcut subclass: base weights identical, 3 new zero tensors."""
    _imports()
    from premonition.model import PremonitionMini
    if not R.ARMS[arm]["bypass"]:
        raise SystemExit("the relation shortcut is only wired for the card-bypass arms")
    torch.manual_seed(seed)
    base = PremonitionMini(R.config_for(arm, early_ans))
    model = shortcut_class()(base.config)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    if sorted(missing) != sorted(NEW_KEYS) or unexpected:
        raise RuntimeError(f"relation-shortcut state mismatch {missing} / {unexpected}")
    model.zero_shortcut()                       # zero AFTER the base state_dict is loaded
    model.relation_shortcut = bool(shortcut)
    return model


# ------------------------------------------------------------------ gate / W_r reporting (eval only)
def gate_report(model, items) -> dict:
    """Mean sigmoid gate at loop 0 and loop 1 for one-hop and two-hop validation questions, plus |W_r|."""
    import premonition_first_card_probe as P
    stats = {"w_r_norm": float(model.rel_query.weight.norm()),
             "w_r_absmax": float(model.rel_query.weight.abs().max()),
             "gate_weight_norm": float(model.rel_gate.weight.norm()),
             "gate_bias": float(model.rel_gate.bias.item()),
             "gate_mean": {}}
    sums = {}
    with torch.no_grad():
        for batch, _supplied, hops in items:
            model._gate_log = []
            P.run(model, batch, hops, mode="own", loops=4)
            log = model._gate_log
            model._gate_log = None
            two = torch.tensor([int(h) == 2 for h in hops])
            for step, gate in log:
                if step not in (0, 1):
                    continue
                for label, mask in (("one_hop", ~two), ("two_hop", two)):
                    if not bool(mask.any()):
                        continue
                    key = f"loop{step}_{label}"
                    total, count = sums.get(key, (0.0, 0))
                    sums[key] = (total + float(gate[mask].sum()), count + int(mask.sum()))
    stats["gate_mean"] = {k: round(t / max(n, 1), 6) for k, (t, n) in sorted(sums.items())}
    stats["gate_n"] = {k: n for k, (_t, n) in sorted(sums.items())}
    return stats


def _gates_main(argv) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates", action="store_true")
    parser.add_argument("names", nargs="*")
    parser.add_argument("--ckpt-dir", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    L.bootstrap()
    _imports()
    import premonition_first_card_probe as P
    torch.set_num_threads(4)
    items = L.load_split("validation")
    out = {}
    for name in args.names:
        model, _blob = P.load_from(name, args.ckpt_dir)
        out[name] = gate_report(model, items)
        print(name, json.dumps(out[name]), flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
        print("wrote", args.out)
    return 0


if __name__ == "__main__":
    if "--gates" in sys.argv:
        raise SystemExit(_gates_main(sys.argv[1:]))
    L.bootstrap()
    sys.path.insert(0, str(L.ROOT / "tests"))
    from test_premonition_relation_shortcut import main as _main
    raise SystemExit(_main())
