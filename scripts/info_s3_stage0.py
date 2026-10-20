"""S3 Stage 0 (design/info-constraints/S3-STAGE0-CARD.md): D + S2 vs D + S2 + `card_address`, far-fact toy.

$0 CPU. Cell A is the S2 protocol (gold mode, answer loss only); its control must reproduce the filed S2 treated arm.
Cell B trains with the gold card + 2 shuffled fact cards (m02 "+distractors"). Readings reuse S2's runner
(`score`, `distract`), so they are the readings the filed S2 numbers came from. `summarize` applies card §5-§7.

    python3 -B scripts/info_s3_stage0.py run --cell B --arm treated --seed 0
    python3 -B scripts/info_s3_stage0.py summarize
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import time

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learnlab.core import IGNORE_INDEX                                      # noqa: E402
from premonition.config import MiniConfig                                   # noqa: E402
from premonition.model import PremonitionMini                               # noqa: E402
from premonition.toy import ToySpec, toy_set, toy_stream                     # noqa: E402
from premonition.train import label_free                                    # noqa: E402

_spec = importlib.util.spec_from_file_location("info_s2_stage0", ROOT / "scripts" / "info_s2_stage0.py")
S2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S2)

OUT = ROOT / "artifacts/claude-infoconstraints-20261018/s3-stage0"
S2_STAGE0 = ROOT / "artifacts/claude-infoconstraints-20261018/s2-stage0"
S2_DISTRACT = ROOT / "artifacts/claude-infoconstraints-20261018/s2-distract"
STEPS, LOOPS, LR, WARMUP = S2.STEPS, S2.LOOPS, S2.LR, S2.WARMUP
SEEDS, CHANCE = (0, 1, 2), 1 / 16


def config_for(arm: str, vocab: int) -> MiniConfig:
    return MiniConfig.preset("D", "tiny", vocab_size=vocab, window=64, decoder_raw_cards=True,
                             card_address=arm == "treated")


def distractor_loss(model: PremonitionMini, batch, generator: torch.Generator) -> torch.Tensor:
    """Cell B (m02 `arm_loss` "+distractors"): answer CE after each of LOOPS loops, averaged over loops."""
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    S2.preload_distractors(model, store, batch, episode, 2, generator)        # the S2 reading's own preload
    answer = batch.answer
    length = int((answer != IGNORE_INDEX).sum(1).max().item())
    targets = answer[:, :max(length, 1)]
    start = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1]
    inputs = torch.cat([start.unsqueeze(1), targets[:, :-1]], dim=1)
    inputs = inputs.masked_fill(inputs == IGNORE_INDEX, model.config.pad_id)
    keep = targets != IGNORE_INDEX
    everyone = torch.arange(batch.q_visit.shape[0], device=hidden.device)
    terms = []
    for step in range(LOOPS):
        rows, _, _, _ = model._step(episode, everyone, step, store)
        out = model._decode_logits(rows, episode.valid, inputs)
        terms.append(F.cross_entropy(F.linear(out[keep], model.embed.weight).float(), targets[keep]))
    return sum(terms) / len(terms)


def train(cell: str, arm: str, seed: int, threads: int):
    torch.set_num_threads(threads)
    spec = ToySpec()
    torch.manual_seed(seed)
    config = config_for(arm, spec.vocab_size)
    model = PremonitionMini(config)
    params = list(model.parameters())
    optimizer = torch.optim.AdamW(
        [{"params": [p for p in params if p.dim() >= 2], "weight_decay": 0.1},
         {"params": [p for p in params if p.dim() < 2], "weight_decay": 0.0}],
        lr=LR, betas=(0.9, 0.99), eps=1e-8)
    stream = (label_free(b) for b in toy_stream(spec, S2.VISITS, S2.TRAIN_SEED))
    generator = torch.Generator().manual_seed(1000 + seed)
    history, finite, started, steps_done = [], True, time.perf_counter(), 0
    for step in range(STEPS):
        for group in optimizer.param_groups:
            group["lr"] = LR * min(1.0, (step + 1) / WARMUP)
        batch = next(stream)
        if cell == "A":
            loss = model.forward(batch, mode="gold", loops=LOOPS, weights={"ans": 1.0})["ans"]
        else:
            loss = distractor_loss(model, batch, generator)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        finite &= all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in params)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()
        steps_done = step + 1
        if (step + 1) % 100 == 0 or step == 0:
            history.append({"step": step + 1, "loss": round(float(loss.detach()), 4),
                            "seconds": round(time.perf_counter() - started, 1)})
            print(json.dumps(history[-1]), flush=True)
    return model, history, finite, time.perf_counter() - started, steps_done


@torch.no_grad()
def pool_mass(model: PremonitionMini, batches: list) -> dict:
    """Card §4 diagnostic: softmax-pool mass on a fact line's token roles ("[world] ENT REL VAL f f\\n"; offset
    1 ENT, 2 REL, 3 VAL, the rest filler), for the writer pool and (S3) the address pool."""
    pools = {"writer": model.writer.pool}
    if model.config.card_address:
        pools["address"] = model.address.pool
    sums = {name: [0.0, 0.0, 0.0, 0.0] for name in pools}
    lines_seen = 0
    for batch in batches:
        hidden = model.read(batch)
        for b in range(batch.tokens.shape[0]):
            for line in range(batch.line_start.shape[1]):
                start = int(batch.line_start[b, line])
                if start < 0 or batch.line_is_question[b, line] or int(batch.line_ents[b, line, 0]) < 0:
                    continue
                span = (batch.line_of[b] == line).nonzero().squeeze(1)
                lines_seen += 1
                for name, pool in pools.items():
                    weight = torch.softmax(pool(hidden[b, span]).squeeze(-1).float(), 0)
                    offset = span - start
                    for role, at in enumerate((1, 2, 3)):
                        sums[name][role] += float(weight[offset == at].sum())
                    sums[name][3] += float(weight[(offset < 1) | (offset > 3)].sum())
    return {name: dict(zip(("ENT", "REL", "VAL", "other"), [v / max(lines_seen, 1) for v in values]))
            for name, values in sums.items()} | {"fact_lines": lines_seen}


def cmd_run(args) -> None:
    model, history, finite, seconds, steps_done = train(args.cell, args.arm, args.seed, args.threads)
    test = [label_free(b) for b in toy_set(ToySpec(), S2.TEST_BATCHES, S2.VISITS, S2.TEST_SEED)]
    result = {"cell": args.cell, "arm": args.arm, "seed": args.seed, "threads": args.threads,
              "steps_run": steps_done, "finite": finite, "seconds": seconds, "torch": torch.__version__,
              "parameters": model.num_parameters(), "card_address": model.config.card_address,
              "decoder_raw_cards": model.config.decoder_raw_cards, "history": history,
              "gold": S2.score(model, test, card=True), "nocard": S2.score(model, test, card=False),
              "d2": S2.distract(model, test, 2), "pool_mass": pool_mass(model, test[:4])}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"cell{args.cell}-{args.arm}-seed{args.seed}.json").write_text(json.dumps(result, indent=1))
    g, d2, nc = result["gold"], result["d2"], result["nocard"]
    print(f"cell {args.cell} {args.arm} seed {args.seed}: gold {g['acc']:.4f} d2 {d2['acc']:.4f} ({d2['correct']}) "
          f"nocard {nc['acc']:.4f} distinct gold/d2 {g['distinct_256']}/{d2['distinct_256']} | {seconds:.0f} s")


def cmd_summarize(args) -> None:
    """Card §5-§7, verbatim."""
    runs, missing = {}, []
    for cell in ("A", "B"):
        for arm in ("control", "treated"):
            for seed in SEEDS:
                path = OUT / f"cell{cell}-{arm}-seed{seed}.json"
                if path.exists():
                    runs[(cell, arm, seed)] = json.loads(path.read_text())
                else:
                    missing.append(path.name)
    if missing:
        summary = {"verdict": "INCOMPLETE", "missing": missing}
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
        print(json.dumps(summary, indent=1))
        return
    cells = {"A": [], "B": []}
    for cell in ("A", "B"):
        primary = "gold" if cell == "A" else "d2"
        for seed in SEEDS:
            c, t = runs[(cell, "control", seed)], runs[(cell, "treated", seed)]
            row = {"seed": seed, "void": c[primary]["distinct_256"] == 1,
                   "control": {k: c[k]["acc"] for k in ("gold", "d2", "nocard")},
                   "treated": {k: t[k]["acc"] for k in ("gold", "d2", "nocard")},
                   "d_d2": t["d2"]["acc"] - c["d2"]["acc"],
                   "treated_distinct_primary": t[primary]["distinct_256"],
                   "complete": all(x["finite"] and x["steps_run"] == STEPS for x in (c, t))}
            if cell == "A":                                   # §3 / §5: the control must be the filed S2 arm
                stage0, distract = S2_STAGE0 / f"treated-seed{seed}.json", S2_DISTRACT / f"treated-seed{seed}.json"
                present = stage0.exists() and distract.exists()           # amendment 2: absent filed S2 -> VOID
                filed = json.loads(stage0.read_text())["with_card"] if present else None
                filed_d2 = json.loads(distract.read_text())["d2"] if present else None
                row["reproduces_s2"] = (present and filed_d2 is not None     # an unread S2 arm cannot be matched
                                        and all(c["gold"][f] == filed[f] for f in ("correct", "distinct_256",
                                                                                 "distinct_1024"))
                                        and c["d2"]["correct"] == filed_d2["correct"])
                row["void"] = row["void"] or not row["reproduces_s2"]
            row["treated_address_mass_ent_rel"] = (t["pool_mass"]["address"]["ENT"]
                                                   + t["pool_mass"]["address"]["REL"])
            cells[cell].append(row)
    valid = {cell: [r for r in rows if not r["void"]] for cell, rows in cells.items()}
    every_run_complete = all(r["complete"] for rows in cells.values() for r in rows)
    detail = {"cells": cells, "every_run_complete": every_run_complete}
    if min(len(valid["A"]), len(valid["B"])) < 2:
        summary = {"verdict": "INCONCLUSIVE", "why": "a cell has fewer than 2 valid seeds", **detail}
        (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
        print(json.dumps(summary, indent=1))
        return
    b, a = valid["B"], valid["A"]
    d = [r["d_d2"] for r in b]
    mean = statistics.fmean(d)
    bound = mean - 2 * statistics.stdev(d) / math.sqrt(len(d))
    both = a + b
    marks = {
        "1_cellB_d_ge_15_every_seed": all(x >= 0.15 for x in d),
        "1_cellB_mean_minus_2se_gt_0": bound > 0,
        "2_cellB_treated_d2_ge_55_every_seed": all(r["treated"]["d2"] >= 0.55 for r in b),
        "3_treated_gold_ge_95_both_cells": all(r["treated"]["gold"] >= 0.95 for r in both),
        "4_treated_nocard_le_9.25_both_cells": all(r["treated"]["nocard"] <= CHANCE + 0.03 for r in both),
        "5_cellA_no_harm": sum(r["treated"]["d2"] < r["control"]["d2"] - 0.03 for r in a) < 2,
        "6_treated_distinct_gt_1": all(r["treated_distinct_primary"] > 1 for r in both),
        "6_every_run_complete": every_run_complete}
    fail = mean <= 0.03 or sum(r["treated"]["d2"] < 0.40 for r in b) >= 2
    wrong = sum(abs(x) <= 0.03 for x in d) >= 2 or not marks["4_treated_nocard_le_9.25_both_cells"]
    verdict = "FAIL" if fail or wrong else ("PASS" if all(marks.values()) else "INCONCLUSIVE")
    note = None
    if wrong and statistics.fmean(r["treated_address_mass_ent_rel"] for r in b) >= 0.5:
        note = "address exists, decoder does not use it (card §7; points at the decoder query, N16)"
    summary = {"verdict": verdict, "cellB_mean_d": mean, "cellB_mean_minus_2se": bound, "marks": marks,
               "fail_rule": fail, "proves_S3_wrong_rule": wrong, "note": note, **detail}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--cell", choices=("A", "B"), required=True)
    run.add_argument("--arm", choices=("control", "treated"), required=True)
    run.add_argument("--seed", type=int, required=True)
    run.add_argument("--threads", type=int, default=1)
    sub.add_parser("summarize")
    args = parser.parse_args()
    {"run": cmd_run, "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    main()
