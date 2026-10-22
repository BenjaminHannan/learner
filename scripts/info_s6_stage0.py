"""S6 Stage 0 (design/info-constraints/S6-STAGE0-CARD.md): D + S2 + S5 vs D + S2 + S5 + `ask_ent_match`, far-fact
toy, tiny.

$0 CPU. Stage 1: the S2 protocol (800 gold-only steps), kappa_d and kappa_a frozen at 0. Stage 2: 1,600 teacher steps
(default loss weights, generator 2000 + seed); the scalars in their own group at lr 1e-2, each clipped on its own.
Primary: first-ASK gold rank-1 (the S4 runner's `first_ask`). Readings reuse the S2 and S4 runners. `summarize`
applies card §5-§7.

    python3 -B scripts/info_s6_stage0.py run --arm treated --seed 0
    python3 -B scripts/info_s6_stage0.py summarize
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import time

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from premonition import train as ptrain                                     # noqa: E402
from premonition.config import MiniConfig                                   # noqa: E402
from premonition.model import PremonitionMini                               # noqa: E402
from premonition.toy import ToySpec, toy_set, toy_stream                     # noqa: E402
from premonition.train import label_free                                    # noqa: E402


def _runner(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S2 = _runner("info_s2_stage0")
S4 = _runner("info_s4_stage0")

OUT = ROOT / "artifacts/claude-infoconstraints-20261018/s6-stage0"
STAGE1, STAGE2, EVERY, LOOPS, LR, LR_KAPPA, WARMUP = 800, 1600, 400, S2.LOOPS, S2.LR, 1e-2, S2.WARMUP
SEEDS, CHANCE = (0, 1, 2), 1 / 16
SCALARS = ("dec_kappa", "ask_kappa")


def shared_digest(model: PremonitionMini) -> str:
    digest = hashlib.sha256()
    for name, param in sorted(model.named_parameters()):
        if name not in SCALARS:
            digest.update(name.encode())
            digest.update(param.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def train(arm: str, seed: int, threads: int, test: list):
    torch.set_num_threads(threads)
    spec = ToySpec()
    torch.manual_seed(seed)
    config = MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64, decoder_raw_cards=True,
                               dec_ent_match=True, ask_ent_match=arm == "treated")
    model = PremonitionMini(config)
    scalars = [p for n, p in model.named_parameters() if n in SCALARS]
    for kappa in scalars:
        kappa.requires_grad_(False)                                 # stage 1: frozen at 0 (card §3)
    shared = [p for n, p in model.named_parameters() if n not in SCALARS]
    optimizer = torch.optim.AdamW(
        [{"params": [p for p in shared if p.dim() >= 2], "weight_decay": 0.1},
         {"params": [p for p in shared if p.dim() < 2], "weight_decay": 0.0}],
        lr=LR, betas=(0.9, 0.99), eps=1e-8)
    stream = (label_free(b) for b in toy_stream(spec, S2.VISITS, S2.TRAIN_SEED))
    teacher = torch.Generator().manual_seed(2000 + seed)
    record = {"history": [], "progress": [], "finite": True, "first_stage2_grads": None}
    started = time.perf_counter()
    for step in range(STAGE1 + STAGE2):
        if step == STAGE1:
            record["stage1_digest"] = shared_digest(model)
            record["stage1_acc_gold"] = S2.score(model, test, card=True)["acc"]
            for kappa in scalars:
                kappa.requires_grad_(True)
            optimizer.add_param_group({"params": scalars, "lr": LR_KAPPA, "weight_decay": 0.0})
        for group in optimizer.param_groups[:2]:
            group["lr"] = LR * min(1.0, (step + 1) / WARMUP)
        batch = next(stream)
        if step < STAGE1:
            loss = model.forward(batch, mode="gold", loops=LOOPS, weights={"ans": 1.0})["ans"]
        else:
            loss = model.forward(batch, mode="teacher", generator=teacher)["loss"]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if step == STAGE1:                                          # before clipping (card §4)
            record["first_stage2_grads"] = {n: None if p.grad is None else float(p.grad)
                                            for n, p in model.named_parameters() if n in SCALARS}
        record["finite"] &= all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in model.parameters())
        torch.nn.utils.clip_grad_norm_(shared, 1.0)                 # shared weights only; each scalar on its own
        for kappa in scalars:
            if kappa.grad is not None:
                torch.nn.utils.clip_grad_norm_([kappa], 1.0)
        optimizer.step()
        done = step + 1
        if done % 100 == 0 or step == 0:
            record["history"].append({"step": done, "loss": round(float(loss.detach()), 4),
                                      **{n: round(float(p.detach()), 4) for n, p in model.named_parameters()
                                         if n in SCALARS},
                                      "seconds": round(time.perf_counter() - started, 1)})
            print(json.dumps(record["history"][-1]), flush=True)
        if done > STAGE1 and (done - STAGE1) % EVERY == 0:
            ask = S4.first_ask(model, test)
            record["progress"].append({"stage2_step": done - STAGE1, "rank1": ask["rank1"],
                                       "acc_gold": S2.score(model, test, card=True)["acc"]})
    record["steps_run"] = done
    record["seconds"] = time.perf_counter() - started
    return model, record


def question_entities(model: PremonitionMini, batch) -> torch.Tensor:
    """[Q, n_ent] bool: S5's question-span set, the same `_mentions(batch, start)` the model uses."""
    return model._mentions(batch, batch.q_span[:, 0])


@torch.no_grad()
def own_detail(model: PremonitionMini, batches: list) -> dict:
    """Card §4: own-retrieval answers (`model.answer`, no wipe) overall and by n_q, the number of eligible real
    cards naming a question entity (1, 2, >= 3); real fetches per question; the share of told questions whose gold
    card has m = 0."""
    was = model.training
    model.eval()
    rows = []
    gold_zero = told = 0
    for batch in batches:
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        names = question_entities(model, batch)
        ents = store.ents[batch.q_visit]                                             # [Q, L, E]
        match = (names.unsqueeze(1).expand(-1, ents.shape[1], -1).gather(2, ents.clamp_min(0))
                 & (ents >= 0)).any(2)                                               # [Q, L]
        eligible = store.eligible(batch.q_visit, batch.q_line)[:, :store.null]
        n_q = (match & eligible).sum(1)
        gold_line = batch.gold_lines[:, 0]
        has_gold = gold_line >= 0
        told += int(has_gold.sum())
        gold_zero += int((has_gold & ~match.gather(1, gold_line.clamp_min(0).unsqueeze(1)).squeeze(1)).sum())
        answers = model.answer(batch)
        hit, _ = ptrain.judge(answers, batch, eos=model.config.eos_id)
        fetched = answers.fetched[:, :store.null].sum(1)
        for q in range(batch.q_visit.shape[0]):
            rows.append({"correct": bool(hit[q]), "n_q": int(n_q[q]), "fetched": int(fetched[q])})
    model.train(was)

    def acc(sub):
        return {"n": len(sub), "acc": sum(r["correct"] for r in sub) / len(sub) if sub else None}
    return {"own_acc": acc(rows)["acc"], "n": len(rows),
            "by_n_q": {"1": acc([r for r in rows if r["n_q"] == 1]), "2": acc([r for r in rows if r["n_q"] == 2]),
                       "3+": acc([r for r in rows if r["n_q"] >= 3]), "0": acc([r for r in rows if r["n_q"] == 0])},
            "fetches_mean": statistics.fmean(r["fetched"] for r in rows),
            "fetch_any_share": sum(r["fetched"] > 0 for r in rows) / len(rows),
            "gold_m0_share": gold_zero / max(told, 1), "told": told}


def cmd_run(args) -> None:
    test = [label_free(b) for b in toy_set(ToySpec(), S2.TEST_BATCHES, S2.VISITS, S2.TEST_SEED)]
    model, record = train(args.arm, args.seed, args.threads, test)
    result = {"arm": args.arm, "seed": args.seed, "threads": args.threads, "torch": torch.__version__, **record,
              "ask": S4.first_ask(model, test), "own": own_detail(model, test),
              "gold": S2.score(model, test, card=True), "nocard": S2.score(model, test, card=False),
              "d2": S2.distract(model, test, 2, True), "kappa_d": float(model.dec_kappa.detach()),
              "kappa_a": float(model.ask_kappa.detach()) if args.arm == "treated" else None}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.arm}-seed{args.seed}.json").write_text(json.dumps(result, indent=1))
    a, o = result["ask"], result["own"]
    print(f"{args.arm} seed {args.seed}: rank1 {a['rank1']:.4f} recall4 {a['recall4']:.4f} own {o['own_acc']:.4f} "
          f"gold {result['gold']['acc']:.4f} d2 {result['d2']['acc']:.4f} nocard {result['nocard']['acc']:.4f} "
          f"kappa_d {result['kappa_d']:.3f} kappa_a {result['kappa_a']} fetches {o['fetches_mean']:.2f} "
          f"| {record['seconds']:.0f} s")


def cmd_summarize(args) -> None:
    """Card §5-§7, verbatim."""
    runs, missing = {}, []
    for arm in ("control", "treated"):
        for seed in SEEDS:
            path = OUT / f"{arm}-seed{seed}.json"
            if path.exists():
                runs[(arm, seed)] = json.loads(path.read_text())
            else:
                missing.append(path.name)
    if missing:
        summary = {"verdict": "INCOMPLETE", "missing": missing}
    else:
        rows = []
        for seed in SEEDS:
            c, t = runs[("control", seed)], runs[("treated", seed)]
            grad_a = t["first_stage2_grads"]["ask_kappa"]
            void = {"control_gold_lt_95_after_stage1": c["stage1_acc_gold"] < 0.95,
                    "control_gold_lt_90_after_stage2": c["gold"]["acc"] < 0.90,
                    "control_one_distinct_d2": c["d2"]["distinct_256"] == 1,
                    "control_kappa_d_lt_1": c["kappa_d"] < 1.0,
                    "control_d2_lt_75": c["d2"]["acc"] < 0.75,
                    "stage1_digests_differ": c["stage1_digest"] != t["stage1_digest"],
                    "kappa_a_grad_lt_1e-3": grad_a is None or abs(grad_a) < 1e-3,
                    "gold_m0_gt_1pct": t["own"]["gold_m0_share"] > 0.01,
                    "control_never_fetches": c["own"]["fetch_any_share"] == 0}
            rows.append({"seed": seed, "void": any(void.values()), "void_reasons": void,
                         "d": t["ask"]["rank1"] - c["ask"]["rank1"], "a": t["own"]["own_acc"] - c["own"]["own_acc"],
                         "control": {"rank1": c["ask"]["rank1"], "recall4": c["ask"]["recall4"],
                                     "own": c["own"]["own_acc"], "d2": c["d2"]["acc"], "kappa_d": c["kappa_d"],
                                     "fetches": c["own"]["fetches_mean"]},
                         "treated": {"rank1": t["ask"]["rank1"], "recall4": t["ask"]["recall4"],
                                     "own": t["own"]["own_acc"], "gold": t["gold"]["acc"],
                                     "nocard": t["nocard"]["acc"], "d2": t["d2"]["acc"],
                                     "distinct_d2": t["d2"]["distinct_256"], "kappa_d": t["kappa_d"],
                                     "kappa_a": t["kappa_a"], "fetches": t["own"]["fetches_mean"]},
                         "complete": all(x["finite"] and x["steps_run"] == STAGE1 + STAGE2 for x in (c, t))})
        valid = [r for r in rows if not r["void"]]
        every_complete = all(r["complete"] for r in rows)
        detail = {"rows": rows, "every_run_complete": every_complete}
        if len(valid) < 2:
            summary = {"verdict": "INCONCLUSIVE", "why": "fewer than 2 valid seeds", **detail}
        else:
            d, a = [r["d"] for r in valid], [r["a"] for r in valid]
            mean, mean_a = statistics.fmean(d), statistics.fmean(a)
            bound = mean - 2 * statistics.stdev(d) / math.sqrt(len(d))
            tr = [r["treated"] for r in valid]
            marks = {
                "1_d_ge_15_every_seed": all(x >= 0.15 for x in d), "1_mean_minus_2se_gt_0": bound > 0,
                "2_treated_recall4_ge_0.85": all(x["recall4"] >= 0.85 for x in tr),
                "3_own_d_ge_10_every_seed": all(x >= 0.10 for x in a),
                "4_gold_ge_95": all(x["gold"] >= 0.95 for x in tr),
                "4_nocard_le_9.25": all(x["nocard"] <= CHANCE + 0.03 for x in tr),
                "4_distinct_gt_1": all(x["distinct_d2"] > 1 for x in tr),
                "4_d2_ge_control_minus_3": all(r["treated"]["d2"] >= r["control"]["d2"] - 0.03 for r in valid),
                "4_finite_complete": every_complete}
            not_engaged = any(x["kappa_a"] < 1.0 for x in tr)
            fail = mean <= 0.03 or mean_a <= 0 or not_engaged
            wrong_rank = sum(abs(r["d"]) <= 0.03 and r["treated"]["kappa_a"] >= 1.0 for r in valid) >= 2
            wrong_link = (marks["1_d_ge_15_every_seed"] and marks["1_mean_minus_2se_gt_0"]
                          and sum(x <= 0.03 for x in a) >= 2)
            wrong = wrong_rank or wrong_link
            verdict = "FAIL" if fail or wrong else ("PASS" if all(marks.values()) else "INCONCLUSIVE")
            notes = []
            if not_engaged:
                notes.append("not engaged (treated kappa_a < 1.0 on a valid seed)")
            if wrong_link:
                notes.append("fetch is not the binding link")
            summary = {"verdict": verdict, "mean_d": mean, "mean_minus_2se": bound, "mean_a": mean_a,
                       "marks": marks, "fail_rule": fail, "proves_wrong_rank": wrong_rank,
                       "proves_wrong_link": wrong_link, "notes": notes, **detail}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--arm", choices=("control", "treated"), required=True)
    run.add_argument("--seed", type=int, required=True)
    run.add_argument("--threads", type=int, default=1)
    sub.add_parser("summarize")
    args = parser.parse_args()
    {"run": cmd_run, "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    main()
