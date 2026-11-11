"""S4 Stage 0 (design/info-constraints/S4-STAGE0-CARD.md): D + S2 vs D + S2 + `ent_key`, far-fact toy.

$0 CPU. Stage 1 is the S2 protocol (gold mode, answer loss only, 800 steps), where D + S2 reads; stage 2 is 400 teacher
steps (default loss weights), which train the ASK ranking. Primary readout: first-ASK gold rank-1. Readings reuse the
S2 runner. `summarize` applies card §5-§7.

    python3 -B scripts/info_s4_stage0.py run --arm treated --seed 0
    python3 -B scripts/info_s4_stage0.py summarize
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
from premonition.model import PremonitionMini, _norm                         # noqa: E402
from premonition.toy import ToySpec, toy_set, toy_stream                     # noqa: E402
from premonition.train import label_free                                    # noqa: E402

_spec = importlib.util.spec_from_file_location("info_s2_stage0", ROOT / "scripts" / "info_s2_stage0.py")
S2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S2)

OUT = ROOT / "artifacts/claude-infoconstraints-20261018/s4-stage0"
STAGE1, STAGE2, LOOPS, LR, WARMUP = 800, 400, S2.LOOPS, S2.LR, S2.WARMUP
SEEDS, CHANCE = (0, 1, 2), 1 / 16
S4_PARAMS = ("ent_query.weight", "ent_query.bias", "kappa_e")


def shared_digest(model: PremonitionMini) -> str:
    digest = hashlib.sha256()
    for name, param in sorted(model.named_parameters()):
        if name not in S4_PARAMS:
            digest.update(name.encode())
            digest.update(param.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def train(arm: str, seed: int, threads: int):
    torch.set_num_threads(threads)
    spec = ToySpec()
    torch.manual_seed(seed)
    config = MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64, decoder_raw_cards=True,
                               ent_key=arm == "treated")
    model = PremonitionMini(config)
    params = list(model.parameters())
    optimizer = torch.optim.AdamW(
        [{"params": [p for p in params if p.dim() >= 2], "weight_decay": 0.1},
         {"params": [p for p in params if p.dim() < 2], "weight_decay": 0.0}],
        lr=LR, betas=(0.9, 0.99), eps=1e-8)
    stream = (label_free(b) for b in toy_stream(spec, S2.VISITS, S2.TRAIN_SEED))
    teacher = torch.Generator().manual_seed(2000 + seed)
    history, finite, started, steps_done, digest = [], True, time.perf_counter(), 0, None
    for step in range(STAGE1 + STAGE2):
        for group in optimizer.param_groups:
            group["lr"] = LR * min(1.0, (step + 1) / WARMUP)
        batch = next(stream)
        if step < STAGE1:
            loss = model.forward(batch, mode="gold", loops=LOOPS, weights={"ans": 1.0})["ans"]
        else:
            loss = model.forward(batch, mode="teacher", generator=teacher)["loss"]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        finite &= all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in params)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()
        steps_done = step + 1
        if steps_done == STAGE1:
            digest = shared_digest(model)                       # card §5(iii): equal across arms
        if steps_done % 100 == 0 or step == 0:
            history.append({"step": steps_done, "loss": round(float(loss.detach()), 4),
                            "seconds": round(time.perf_counter() - started, 1)})
            print(json.dumps(history[-1]), flush=True)
    return model, history, finite, time.perf_counter() - started, steps_done, digest


@torch.no_grad()
def first_ask(model: PremonitionMini, batches: list) -> dict:
    """Card §4: first-ASK (loop 0, fresh episode) gold rank-1 among eligible real cards, recall@4; S4 diagnostics."""
    was = model.training
    model.eval()
    told = first = in4 = 0
    pi_question = []
    for batch in batches:
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        episode = model._start(batch, hidden, store, model._mentions(batch))
        everyone = torch.arange(batch.q_visit.shape[0])
        rows, _, _, scores = model._step(episode, everyone, 0, store)
        gold, told_q, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        real = scores[:, :store.null].float()
        eligible = store.eligible(batch.q_visit, batch.q_line)[:, :store.null]
        gold_real = gold[:, :store.null] & eligible
        best_gold = real.masked_fill(~gold_real, -math.inf).max(1).values
        best_wrong = real.masked_fill(~(eligible & ~gold_real), -math.inf).max(1).values
        top = store.top(scores, model.config.top_k)
        hit = (gold.gather(1, top.clamp_min(0)) & (top >= 0) & (top < store.null)).any(1)
        have = told_q & gold_real.any(1)
        told += int(have.sum())
        first += int((have & (best_gold > best_wrong)).sum())
        in4 += int((have & hit).sum())
        if model.config.ent_key:
            register = _norm(rows[:, model._register_base])
            logits = model.ent_query(register).float().masked_fill(~episode.mentions, -math.inf)
            pi = torch.softmax(logits, -1).nan_to_num(0.0)
            for q in range(batch.q_visit.shape[0]):
                start, end = (int(x) for x in batch.q_span[q])
                ents = {int(t) - model.config.vocab_size for t in batch.tokens[int(batch.q_visit[q]), start:end]
                        if int(t) >= model.config.vocab_size}
                pi_question.append(float(sum(pi[q, e] for e in ents)))
    model.train(was)
    out = {"told": told, "rank1": first / max(told, 1), "recall4": in4 / max(told, 1)}
    if model.config.ent_key:
        out["kappa_e"] = float(model.kappa_e)
        out["pi_on_question_entity"] = statistics.fmean(pi_question) if pi_question else None
    return out


@torch.no_grad()
def own_accuracy(model: PremonitionMini, batches: list) -> float:
    was = model.training
    model.eval()
    right = total = 0
    for batch in batches:
        hit, _ = ptrain.judge(model.answer(batch), batch, eos=model.config.eos_id)
        right += sum(hit)
        total += len(hit)
    model.train(was)
    return right / max(total, 1)


def cmd_run(args) -> None:
    model, history, finite, seconds, steps_done, digest = train(args.arm, args.seed, args.threads)
    test = [label_free(b) for b in toy_set(ToySpec(), S2.TEST_BATCHES, S2.VISITS, S2.TEST_SEED)]
    result = {"arm": args.arm, "seed": args.seed, "threads": args.threads, "steps_run": steps_done,
              "finite": finite, "seconds": seconds, "torch": torch.__version__, "stage1_shared_digest": digest,
              "parameters": model.num_parameters(), "ent_key": model.config.ent_key, "history": history,
              "ask": first_ask(model, test), "gold": S2.score(model, test, card=True),
              "nocard": S2.score(model, test, card=False), "d2_facts": S2.distract(model, test, 2, True),
              "own_acc": own_accuracy(model, test)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.arm}-seed{args.seed}.json").write_text(json.dumps(result, indent=1))
    a, g = result["ask"], result["gold"]
    print(f"{args.arm} seed {args.seed}: rank1 {a['rank1']:.4f} recall4 {a['recall4']:.4f} gold {g['acc']:.4f} "
          f"(distinct {g['distinct_256']}) nocard {result['nocard']['acc']:.4f} kappa_e {a.get('kappa_e')} "
          f"| {seconds:.0f} s")


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
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
        print(json.dumps(summary, indent=1))
        return
    rows = []
    for seed in SEEDS:
        c, t = runs[("control", seed)], runs[("treated", seed)]
        void = {"one_distinct": c["gold"]["distinct_256"] == 1, "control_cannot_read": c["gold"]["acc"] < 0.5,
                "stage1_differs": c["stage1_shared_digest"] != t["stage1_shared_digest"]}
        rows.append({"seed": seed, "void": any(void.values()), "void_reasons": void,
                     "control": {"rank1": c["ask"]["rank1"], "recall4": c["ask"]["recall4"],
                                 "gold": c["gold"]["acc"], "nocard": c["nocard"]["acc"]},
                     "treated": {"rank1": t["ask"]["rank1"], "recall4": t["ask"]["recall4"],
                                 "gold": t["gold"]["acc"], "nocard": t["nocard"]["acc"]},
                     "d": t["ask"]["rank1"] - c["ask"]["rank1"],
                     "treated_distinct": t["gold"]["distinct_256"], "kappa_e": t["ask"].get("kappa_e"),
                     "pi_on_question_entity": t["ask"].get("pi_on_question_entity"),
                     "complete": all(x["finite"] and x["steps_run"] == STAGE1 + STAGE2 for x in (c, t))})
    valid = [r for r in rows if not r["void"]]
    every_run_complete = all(r["complete"] for r in rows)
    detail = {"rows": rows, "every_run_complete": every_run_complete}
    if len(valid) < 2:
        summary = {"verdict": "INCONCLUSIVE", "why": "fewer than 2 valid seeds", **detail}
    else:
        d = [r["d"] for r in valid]
        mean = statistics.fmean(d)
        bound = mean - 2 * statistics.stdev(d) / math.sqrt(len(d))
        marks = {
            "1_d_ge_15_every_seed": all(x >= 0.15 for x in d),
            "1_mean_minus_2se_gt_0": bound > 0,
            "2_recall4_kept": all(r["treated"]["recall4"] >= r["control"]["recall4"] - 0.02 for r in valid),
            "3_reading_kept": all(r["treated"]["gold"] >= r["control"]["gold"] - 0.03 for r in valid),
            "4_nocard_le_9.25": all(r["treated"]["nocard"] <= CHANCE + 0.03 for r in valid),
            "5_treated_distinct_gt_1": all(r["treated_distinct"] > 1 for r in valid),
            "5_every_run_complete": every_run_complete}
        fail = mean <= 0.03
        wrong = sum(abs(x) <= 0.03 for x in d) >= 2
        verdict = "FAIL" if fail or wrong else ("PASS" if all(marks.values()) else "INCONCLUSIVE")
        notes = []
        if wrong and statistics.fmean(r["kappa_e"] for r in valid) < 0.5:
            notes.append("the mechanism was not engaged (kappa_e < 0.5)")
        if wrong and statistics.fmean(r["pi_on_question_entity"] for r in valid) > 0.8:
            notes.append("identity is in the score and still does not decide the rank")
        summary = {"verdict": verdict, "mean_d": mean, "mean_minus_2se": bound, "marks": marks, "fail_rule": fail,
                   "proves_S4_wrong_rule": wrong, "notes": notes, **detail}
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
