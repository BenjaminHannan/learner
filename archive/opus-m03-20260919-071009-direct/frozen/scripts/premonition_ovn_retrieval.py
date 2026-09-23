"""Overnight experiment 2 (run ovn-20260918-235851): can EVIDENCE-SUPERVISED retrieval do the choosing and the
chaining, one card per ASK, while the answer path only reads?

Same frozen source and ladder data as experiment 1 (scripts/premonition_ovn_ladder.py). D's own curriculum and all
four losses (MiniTrainer: gold -> teacher -> own; L_ask uses the oracle evidence lines, a privilege D already has and
C* shares in the spec). Arms differ in ONE thing each:
  bypass-k1  D-card-bypass, top_k = 1, no teacher distractors  (retrieval chooses; the reader reads 1-2 cards)
  bypass-k4  D-card-bypass, D's default top_k = 4 and 1-2 teacher distractors (the milestone-2 configuration)
  noask      D-noask: same reader / Think / decoder, no store (the full-history memory control)
max_loops = 4 for every arm (a 2-hop question needs 2 reads = 3 loops). Hard 30-minute experiment ledger.

    PY -B scripts/premonition_ovn_retrieval.py train --arm bypass-k1 --steps 1500
    PY -B scripts/premonition_ovn_retrieval.py eval --ckpt <name> [--test]
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import itertools
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L  # noqa: E402

OUT = L.ROOT / "artifacts" / f"opus-{L.RUN}" / "exp2"
CAP_SECONDS = 30 * 60
MAX_LOOPS = 4
ARMS = {"bypass-k1": {"variant": "D", "bypass": True, "top_k": 1, "distractors": (0, 0)},
        "bypass-k4": {"variant": "D", "bypass": True, "top_k": 4, "distractors": (1, 2)},
        "noask": {"variant": "D-noask", "bypass": False, "top_k": 4, "distractors": (1, 2)}}


def ledger_seconds() -> float:
    path = OUT / "ledger.jsonl"
    return 0.0 if not path.exists() else sum(json.loads(l)["seconds"] for l in path.read_text().splitlines() if l)


def ledger_add(entry: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "ledger.jsonl").open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


def config_for(arm: str, early_ans: float = 0.2):
    from premonition.config import MiniConfig
    a = ARMS[arm]
    return MiniConfig.preset(a["variant"], "tiny", vocab_size=L.spec().vocab_size, window=64, top_k=a["top_k"],
                             distractors=a["distractors"], max_loops=MAX_LOOPS, early_ans=early_ans)


def build(arm: str, seed: int, early_ans: float = 0.2):
    import torch
    from premonition import answer_path
    from premonition.model import PremonitionMini
    torch.manual_seed(seed)
    base = PremonitionMini(config_for(arm, early_ans))
    return answer_path.from_base(answer_path.CARD_BYPASS, base) if ARMS[arm]["bypass"] else base


def own_fixed(model, batch, loops: int, *, no_cards: bool = False):
    """[Q] correct, [Q] every gold card fetched: own retrieval for exactly `loops` loops (HALT ignored); after
    loop t < loops the model's ASK (logit > 0) fetches its top-k, so at most loops - 1 reads."""
    import torch
    from learnlab.core import IGNORE_INDEX
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    if store is not None and no_cards:
        store = replace(store, valid=torch.zeros_like(store.valid))
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    for step in range(loops):
        rows, halt, ask, scores = model._step(episode, everyone, step, store)
        if store is not None and step + 1 < loops:
            cards = store.top(scores, model.config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
            model._insert(episode, store, everyone, cards)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    ok = torch.tensor([tokens[q, :int(lengths[q])].tolist() == batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
                       for q in range(batch.answer.shape[0])])
    if store is None:
        return ok, torch.zeros_like(ok)
    gold = batch.gold_lines
    fetched = episode.fetched.gather(1, gold.clamp_min(0)) | (gold < 0)
    return ok, fetched.all(1)


def gold_read(model, batch, loops: int):
    """Pure reading: the question's gold cards preloaded, `loops` fixed loops, NO further fetches."""
    import torch
    from learnlab.core import IGNORE_INDEX
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    if store is not None:
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        width = min(gold.shape[1], 2)
        preload = torch.where(gold, torch.arange(gold.shape[1]), torch.full_like(gold, -1, dtype=torch.long)
                              ).topk(width, 1).values
        model._insert(episode, store, everyone, preload)
    for step in range(loops):
        model._step(episode, everyone, step, store)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    ok = torch.tensor([tokens[q, :int(lengths[q])].tolist() == batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
                       for q in range(batch.answer.shape[0])])
    return ok, torch.ones_like(ok)


def by_hop(items, fn) -> dict:
    import torch
    oks, golds, hops, held = [], [], [], []
    for item in items:
        ok, got = fn(item[0])
        oks.append(ok)
        golds.append(got)
        hops.append(item[2])
        held.append(item[0].slices["heldout"])
    ok, got, hop, held = torch.cat(oks), torch.cat(golds), torch.cat(hops), torch.cat(held)
    out = {}
    for name, mask in (("one_hop", hop == 1), ("two_hop_trained_rel", (hop == 2) & ~held),
                       ("two_hop_heldout_rel", (hop == 2) & held)):
        k, n, g = int(ok[mask].sum()), int(mask.sum()), int(got[mask].sum())
        out[name] = {"correct": k, "n": n, "acc": round(k / max(n, 1), 4), "wilson95": L.wilson(k, n),
                     "all_gold_fetched": g}
    return out


def evaluate(model, items, *, full: bool = True) -> dict:
    import torch
    from premonition.train import validate
    was = model.training
    model.eval()
    out = {}
    with torch.no_grad():
        for k in ((2, 3, 4) if full else (3,)):
            out[f"fixed_K{k}"] = by_hop(items, lambda b, k=k: own_fixed(model, b, k))
        if full:
            out["gold_read_K2_no_fetch"] = by_hop(items, lambda b: gold_read(model, b, 2))
            if model.config.store:
                out["fixed_K3_cards_removed"] = by_hop(items, lambda b: own_fixed(model, b, 3, no_cards=True))
            v = validate(model, [item[0] for item in items], gold_cards=bool(model.config.store))
            keep = ("questions", "accuracy", "accuracy_gold_cards", "gold_recall_at_4", "gold_any_at_4",
                    "random_recall_at_4", "asked_rate", "loops_mean", "halt_rate", "loops_mean_gold_cards")
            out["learned_halting"] = {k: v.get(k) for k in keep}
            out["learned_halting"]["slices"] = v.get("slices")
    model.train(was)
    return out


def cmd_train(args) -> None:
    import torch
    from premonition import answer_path
    from premonition.train import MiniTrainer, budget_for_steps, mini_train_config
    spent = ledger_seconds()
    remaining = CAP_SECONDS - spent - args.reserve
    if remaining <= 30:
        raise SystemExit(f"experiment-2 budget exhausted ({spent:.1f} s)")
    started = time.perf_counter()
    name = args.name or f"{args.arm}-s{args.seed}-{args.steps}"
    model = build(args.arm, args.seed, args.early_ans)
    from premonition.train import Curriculum
    curriculum = Curriculum(gold_until=args.gold_until, teacher_until=args.teacher_until, ramp_until=args.ramp_until)
    trainer = MiniTrainer(model, mini_train_config(lr=args.lr, warmup_steps=args.warmup, log_every=50, eval_every=0),
                          "cpu", flop_budget=1.0, seed=args.seed, curriculum=curriculum)
    stream = (item[0] for item in L.checked_train())
    head = [next(stream) for _ in range(2)]
    trainer.calibrate(head)
    trainer.flop_budget = budget_for_steps(trainer, head, args.steps)
    curve = []
    report = trainer.train(itertools.chain(head, stream), max_seconds=remaining - (time.perf_counter() - started),
                           on_log=lambda e: curve.append({k: e.get(k) for k in (
                               "step", "phase", "p_own", "loss", "lm", "ask", "ans", "halt", "gold_recall_at_4",
                               "answer_acc", "loops_per_question", "halt_rate")}))
    train_seconds = time.perf_counter() - started
    for entry in curve[::max(1, len(curve) // 8)] + curve[-1:]:
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in entry.items()}), flush=True)
    validation = L.load_split("validation")
    result = {"name": name, "arm": args.arm, "arm_settings": {k: list(v) if isinstance(v, tuple) else v
                                                              for k, v in ARMS[args.arm].items()},
              "max_loops": MAX_LOOPS, "seed": args.seed, "steps_requested": args.steps,
              "curriculum": {"gold_until": args.gold_until, "teacher_until": args.teacher_until,
                             "ramp_until": args.ramp_until},
              "train_report": {k: v for k, v in report.items() if isinstance(v, (int, float, str, bool, type(None)))},
              "curve": curve, "validation": evaluate(model, validation)}
    seconds = time.perf_counter() - started
    (OUT / "ckpt").mkdir(parents=True, exist_ok=True)
    path = OUT / "ckpt" / f"{name}.pt"
    ident = (answer_path.identity(answer_path.CARD_BYPASS, model.config) if ARMS[args.arm]["bypass"]
             else {"variant": model.config.variant, "purpose": "diagnostic"})
    ident = {**ident, "arm": args.arm, "privilege": "L_ask trained on oracle evidence lines (as D)"}
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "arm": args.arm, "identity": ident,
                "seed": args.seed}, path)
    result.update(seconds_train=round(train_seconds, 2), seconds_total=round(seconds, 2), identity=ident,
                  ckpt=str(path.relative_to(L.ROOT)), ckpt_sha256=L.sha256(path), command=" ".join(sys.argv))
    (OUT / "runs").mkdir(exist_ok=True)
    (OUT / "runs" / f"{name}.json").write_text(json.dumps(result, indent=1, default=str))
    ledger_add({"kind": "train+eval", "name": name, "seconds": round(seconds, 2)})
    show(result["validation"])
    print(f"done {name}: train {train_seconds:.1f} s, total {seconds:.1f} s; experiment-2 ledger "
          f"{ledger_seconds():.1f} / {CAP_SECONDS} s", flush=True)


def show(ev: dict) -> None:
    for key, value in ev.items():
        if key == "learned_halting":
            print(key, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in value.items()
                                   if k != "slices"}))
            print("   slices", json.dumps({k: (v["n"], round(v["accuracy"], 4)) for k, v in (value["slices"] or {}).items()}))
        else:
            print(key, " ".join(f"{h}={v['correct']}/{v['n']}(gold {v['all_gold_fetched']})" for h, v in value.items()))


def load(name: str):
    import torch
    from premonition import answer_path
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    blob = torch.load(OUT / "ckpt" / f"{name}.pt", weights_only=False)
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    model = (answer_path.CardBypassMini if ARMS[blob["arm"]]["bypass"] else PremonitionMini)(config)
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model, blob


def cmd_eval(args) -> None:
    import torch
    started = time.perf_counter()
    model, blob = load(args.ckpt)
    split = "test" if args.test else "validation"
    path = OUT / ("tests" if args.test else "eval") / f"{args.ckpt}.json"
    if args.test and path.exists():
        raise SystemExit("already scored on the test split")
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "split": split,
              "scores": evaluate(model, L.load_split(split), full=True)}
    if args.causal:
        report["causal_two_hop_K3"] = {}
        with torch.no_grad():
            for kind, pairs in L.paired_two_hop(256).items():
                n = both = moved = 0
                for a, b, firsts in pairs:
                    pa = own_first_token(model, a[0], 3)[firsts]
                    pb = own_first_token(model, b[0], 3)[firsts]
                    ta, tb = a[0].answer[firsts, 0], b[0].answer[firsts, 0]
                    n += len(firsts)
                    both += int(((pa == ta) & (pb == tb)).sum())
                    moved += int((pa != pb).sum())
                report["causal_two_hop_K3"][kind] = {"pairs": n, "both_correct": both, "wilson95_both": L.wilson(both, n),
                                                     "prediction_changed": moved,
                                                     "expected": "stay" if kind == "tempting" else "change"}
    report["seconds"] = round(time.perf_counter() - started, 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, default=str))
    ledger_add({"kind": "test-eval" if args.test else "eval", "name": args.ckpt, "seconds": report["seconds"]})
    show(report["scores"])
    if args.causal:
        print(json.dumps(report["causal_two_hop_K3"]))


def own_first_token(model, batch, loops: int):
    import torch
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    for step in range(loops):
        rows, halt, ask, scores = model._step(episode, everyone, step, store)
        if store is not None and step + 1 < loops:
            model._insert(episode, store, everyone,
                          store.top(scores, model.config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1))
    tokens, _ = model._greedy(batch, episode, mentions, None)
    return tokens[:, 0]


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    train = sub.add_parser("train")
    train.add_argument("--arm", choices=sorted(ARMS), required=True)
    train.add_argument("--steps", type=int, default=1500)
    train.add_argument("--seed", type=int, default=0)
    train.add_argument("--lr", type=float, default=1e-3)
    train.add_argument("--warmup", type=int, default=100)
    train.add_argument("--reserve", type=float, default=30.0)
    train.add_argument("--name")
    train.add_argument("--gold-until", type=float, default=0.05)
    train.add_argument("--early-ans", type=float, default=0.2, help="L_ans weight before every gold card is fetched")
    train.add_argument("--teacher-until", type=float, default=0.30)
    train.add_argument("--ramp-until", type=float, default=0.60)
    ev = sub.add_parser("eval")
    ev.add_argument("--ckpt", required=True)
    ev.add_argument("--test", action="store_true")
    ev.add_argument("--causal", action="store_true")
    args = parser.parse_args()
    L.bootstrap()
    import torch
    torch.set_num_threads(8)
    {"train": cmd_train, "eval": cmd_eval}[args.cmd](args)


if __name__ == "__main__":
    main()
