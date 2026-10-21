"""Steal 6 diagnostic (design/steals-2026-10-17/SPEC.md): are ASK's raw key/query norms informative?

Flags off. QK-norm discards the norm of the pre-normalisation key ||W_k p|| and of the query; the question is
whether that norm carries signal (e.g. larger for the gold card) that normalisation would throw away. No trained
D checkpoint exists, so this measures (a) a fresh init and (b) tiny D after a short CPU run on the far-fact toy
(`premonition.train.train_toy`; seconds-scale, so it learns little: the recall/accuracy are reported with it).

For each question's own first ASK (loop 0, top_k by the model's own scores, whether or not the ASK logit fires),
fetched real cards are split into gold (correct) and non-gold (wrong). Logged per card: raw key norm, stored
key norm (1 by construction), value norm, raw query norm, cos, kappa * cos and the age-bias term; also how
often NULL is fetched. The unfetched eligible cards are logged too, as the baseline.

    python3 -B scripts/premonition_steals_qk_diagnostic.py [--steps 90] [--max-seconds 200]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from premonition import train as ptrain                                    # noqa: E402
from premonition.config import MiniConfig                                   # noqa: E402
from premonition.model import PremonitionMini, _norm                         # noqa: E402
from premonition.store import age_bucket                                    # noqa: E402
from premonition.toy import ToySpec, toy_set                                 # noqa: E402

OUT = Path("artifacts/claude-steals-20261017/qk-diagnostic.json")
FIELDS = ("raw_key_norm", "stored_key_norm", "value_norm", "raw_query_norm", "cos", "kappa_cos", "age_bias")


def summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    return {"count": len(values), "mean": statistics.fmean(values), "median": statistics.median(values),
            "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "min": min(values), "max": max(values)}


@torch.no_grad()
def first_ask(model: PremonitionMini, batches: list) -> dict:
    """Per-card quantities of every question's first-ASK top-k, grouped by correct / wrong, plus baselines."""
    config = model.config
    groups: dict[str, dict[str, list[float]]] = {
        name: {field: [] for field in FIELDS}
        for name in ("fetched_correct", "fetched_wrong", "eligible_gold", "eligible_nongold", "outranking_wrong")}
    paired: dict[str, list[float]] = {"raw_key_norm_gap": [], "cos_gap": [], "margin": []}
    stats = dict(questions=0, told=0, fetched_real=0, fetched_null=0, questions_with_null=0, questions_with_gold=0,
                 gold_in_top_k=0, gold_total=0, ranked=0, gold_first=0)
    raw_hook: dict[str, torch.Tensor] = {}
    handle = model.writer.key.register_forward_hook(lambda _m, _a, out: raw_hook.__setitem__("keys", out.detach()))
    try:
        for batch in batches:
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            raw_keys = raw_hook["keys"].float()                              # [B, L, dk] before normalisation
            episode = model._start(batch, hidden, store, model._mentions(batch))
            index = torch.arange(batch.q_visit.shape[0])
            rows, _, _, scores = model._step(episode, index, 0, store)
            register = _norm(rows[:, model._register_base])
            raw_query = model.heads.query(register).float()
            unit = F.normalize(raw_query, dim=-1)
            kappa = float(model.heads.log_kappa.exp())
            visit, line = episode.q_visit, episode.q_line
            cos = torch.einsum("nk,nlk->nl", unit, store.keys[visit])        # [Q, L] real cards
            bias = model.think.age_bias[age_bucket(line.unsqueeze(1) - torch.arange(store.lines),
                                                   config.age_buckets)]
            gold, told, _ = store.gold(batch.gold_lines, visit, line)
            eligible = store.eligible(visit, line)[:, :store.null]
            top = store.top(scores, config.top_k)                            # [Q, k]; NULL = store.null, -1 none
            fetched = torch.zeros_like(eligible)
            for k in range(top.shape[1]):
                real = (top[:, k] >= 0) & (top[:, k] < store.null)
                fetched[real, top[real, k]] = True
            stats["questions"] += index.numel()
            stats["told"] += int(told.sum())
            stats["fetched_real"] += int(fetched.sum())
            stats["fetched_null"] += int((top == store.null).sum())
            stats["questions_with_null"] += int((top == store.null).any(1).sum())
            real_gold = gold[:, :store.null] & told.unsqueeze(1)
            stats["gold_total"] += int(real_gold.sum())
            stats["gold_in_top_k"] += int((real_gold & fetched).sum())
            stats["questions_with_gold"] += int((real_gold & fetched).any(1).sum())
            quantities = {
                "raw_key_norm": raw_keys.norm(dim=-1)[visit], "stored_key_norm": store.keys.norm(dim=-1)[visit],
                "value_norm": store.values.float().norm(dim=-1)[visit],
                "raw_query_norm": raw_query.norm(dim=-1).unsqueeze(1).expand_as(cos),
                "cos": cos, "kappa_cos": kappa * cos, "age_bias": bias}
            # Rank view: with one gold card and top-4 fetches, 3 of 4 fetches are "wrong" by construction, so the
            # sharper question is which wrong cards OUTRANK the best gold card, and how they differ from it.
            score = scores[:, :store.null].float()
            have = (real_gold & eligible).any(1)
            gold_best = score.masked_fill(~(real_gold & eligible), float("-inf")).max(1).values
            wrong_ok = eligible & ~real_gold
            wrong_best, wrong_at = score.masked_fill(~wrong_ok, float("-inf")).max(1)
            outrank = wrong_ok & (score > gold_best.unsqueeze(1)) & have.unsqueeze(1)
            stats["ranked"] += int(have.sum())
            stats["gold_first"] += int((have & (gold_best > wrong_best)).sum())
            gold_at = score.masked_fill(~(real_gold & eligible), float("-inf")).argmax(1)
            rows_q = torch.nonzero(have & torch.isfinite(wrong_best)).squeeze(1)
            raw_norm = raw_keys.norm(dim=-1)[visit]
            paired["raw_key_norm_gap"] += (raw_norm[rows_q, wrong_at[rows_q]] - raw_norm[rows_q, gold_at[rows_q]]).tolist()
            paired["cos_gap"] += (cos[rows_q, wrong_at[rows_q]] - cos[rows_q, gold_at[rows_q]]).tolist()
            paired["margin"] += (gold_best[rows_q] - wrong_best[rows_q]).tolist()
            masks = {"fetched_correct": fetched & real_gold, "fetched_wrong": fetched & ~real_gold & told.unsqueeze(1),
                     "eligible_gold": eligible & real_gold, "eligible_nongold": eligible & ~real_gold & told.unsqueeze(1),
                     "outranking_wrong": outrank}
            for name, mask in masks.items():
                for field, value in quantities.items():
                    groups[name][field] += value[mask].tolist()
    finally:
        handle.remove()
    out = {"cards": {name: {field: summary(values) for field, values in fields.items()}
                     for name, fields in groups.items()}, "fetch": stats}
    out["fetch"]["null_fetch_rate_per_question"] = stats["questions_with_null"] / max(stats["questions"], 1)
    out["fetch"]["recall_at_k"] = stats["gold_in_top_k"] / max(stats["gold_total"], 1)
    out["fetch"]["gold_ranked_first"] = stats["gold_first"] / max(stats["ranked"], 1)
    out["paired_best_wrong_minus_gold"] = {name: summary(values) for name, values in paired.items()}
    out["kappa"] = float(model.heads.log_kappa.exp())
    return out


def report_line(label: str, result: dict) -> str:
    def cell(group: str, field: str) -> str:
        entry = result["cards"][group][field]
        return f"{entry['mean']:.3f}/{entry['median']:.3f}" if entry["count"] else "-"
    fetch = result["fetch"]
    lines = [f"[{label}] questions {fetch['questions']}, recall@k {fetch['recall_at_k']:.3f}, NULL in top-k for "
             f"{fetch['null_fetch_rate_per_question']:.1%} of questions, kappa {result['kappa']:.2f}",
             f"    {'mean/median':<18}" + "".join(f"{g:>20}" for g in result["cards"])]
    for field in FIELDS:
        lines.append(f"    {field:<18}" + "".join(f"{cell(g, field):>20}" for g in result["cards"]))
    counts = {g: result["cards"][g]["raw_key_norm"]["count"] for g in result["cards"]}
    lines.append(f"    {'count':<18}" + "".join(f"{counts[g]:>20}" for g in result["cards"]))
    pair = result["paired_best_wrong_minus_gold"]
    lines.append(f"    gold ranked first {fetch['gold_ranked_first']:.3f}; best wrong minus gold (mean/median): "
                 + ", ".join(f"{k} {v['mean']:.3f}/{v['median']:.3f}" for k, v in pair.items() if v["count"]))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--steps", type=int, default=90)
    parser.add_argument("--max-seconds", type=float, default=200.0)
    parser.add_argument("--visits", type=int, default=16)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    torch.set_num_threads(2)
    spec = ToySpec()
    evaluation = [ptrain.label_free(b) for b in toy_set(spec, 4, args.visits, args.seed + 1000)]

    torch.manual_seed(args.seed)
    fresh = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64))
    fresh.eval()
    results = {"spec": spec.__dict__, "config": "D tiny, window 64, every steal flag off",
               "init": first_ask(fresh, evaluation)}
    print(report_line("init", results["init"]), flush=True)

    started = time.perf_counter()
    trained = ptrain.train_toy("D", spec=spec, steps=args.steps, visits=args.visits, seed=args.seed,
                               eval_batches=4, log_every=10, max_seconds=args.max_seconds,
                               on_log=lambda record: print(ptrain.format_record(record), flush=True))
    seconds = time.perf_counter() - started
    model = trained["trainer"].model
    model.eval()
    validation = trained["validation"]
    results["trained"] = first_ask(model, evaluation)
    results["training"] = {
        "steps_requested": args.steps, "steps_run": trained["trainer"].step, "seconds": seconds,
        "max_seconds": args.max_seconds, "chance_accuracy": trained["chance"],
        "validation": {key: validation.get(key) for key in (
            "accuracy", "accuracy_gold_cards", "gold_recall_at_4", "gold_any_at_4", "random_recall_at_4",
            "asked_rate", "loops_mean", "halt_rate", "questions")}}
    print(report_line("trained", results["trained"]))
    print(json.dumps(results["training"], indent=1))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
