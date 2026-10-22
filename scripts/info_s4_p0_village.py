"""S4-P0: how many eligible cards name a question's person in the village data (data only, $0, no model).

For every evaluation question, count the ELIGIBLE cards (the store's own rule, `CardStore.eligible`) whose
`line_ents` intersect the entity ids that occur in the question span. The question's entities are the tokens
`vocab_size <= t < vocab_size + N_ENT` in `tokens[q_visit, q_span[0]:q_span[1]]` (the same convention as
`premonition.model._mentions`). No training, no model, no GPU, no network.

Village batches come from the label-free v2 visit cache that D is trained and evaluated on:
`premonition.data.build_cache(..., regime="label-free")` over the `validation` split (the repo's standard eval
split: `train_d` and `evaluate_d_checkpoint` default to it). No built village cache exists in this checkout, so
the shards are generated procedurally with `learnlab.village.shards.write_shards` (seed 0, the same generator and
seed convention as the other builds), the name detector is fitted on the generated `train` shards, and the
contender tokenizer is `data/tokenizer/premonition-tok-v2-fallback.json` (7,068 ids, the one the identity guard
requires for primary reports).

The far-fact toy is the sanity check: `toy_set(ToySpec(), 16, 16, 303)` with `train.label_free`, which the S4
card reports as mean 2.29 candidates and ceiling 0.485.

    python3 -B scripts/info_s4_p0_village.py --work <scratch dir> --train-visits 512 --valid-visits 1024 --workers 4
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any, Callable, Optional, Sequence

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learnlab.tokenizer import Tokenizer                            # noqa: E402
from learnlab.village.names import all_names                        # noqa: E402
from learnlab.village.shards import write_shards                    # noqa: E402
from premonition import data as pdata                               # noqa: E402
from premonition import preprocess                                  # noqa: E402
from premonition.batch import N_ENT, VisitBatch                     # noqa: E402
from premonition.config import VOCAB_V2                             # noqa: E402
from premonition.store import CardStore                             # noqa: E402
from premonition.toy import ToySpec, toy_set                        # noqa: E402
from premonition.train import label_free                            # noqa: E402

TOKENIZER = "data/tokenizer/premonition-tok-v2-fallback.json"
OUT = ROOT / "artifacts/claude-infoconstraints-20261018/s4-p0-village"
BINS = [str(i) for i in range(9)] + ["9-16", "17+"]


# ----------------------------------------------------------------- the count


def _bin(n: int) -> str:
    if n <= 8:
        return str(n)
    return "9-16" if n <= 16 else "17+"


def count_batch(batch: VisitBatch, vocab_size: int) -> dict[str, torch.Tensor]:
    """Per-question counts for one batch (rows = the batch's questions, in order).

    The store is built from the batch exactly as the model builds it (`CardStore.write`), so `valid` and
    `ents` are the store's own; the keys and values are dummies because only eligibility and entities are read.
    """
    visits, _ = batch.tokens.shape
    lines = batch.line_start.shape[1]
    questions = batch.q_visit.shape[0]
    gen = torch.Generator().manual_seed(0)
    store = CardStore.write(torch.randn(visits, lines, 4, generator=gen), torch.zeros(visits, lines, 1), batch,
                            torch.randn(4, generator=gen), torch.zeros(1))
    # Eligibility with no fetched mask and no wipe floor: the first ASK of an unwiped episode.
    eligible = store.eligible(batch.q_visit, batch.q_line)[:, :lines]

    # Card entities as a multi-hot over N_ENT (-1 padding goes to a dropped column).
    idx = store.ents.clone()
    idx[idx < 0] = N_ENT
    cards = torch.zeros(visits, lines, N_ENT + 1).scatter_(2, idx, 1.0)[..., :N_ENT]
    card_has_entity = cards.sum(-1) > 0                                     # [B, L]

    # Question entities: entity tokens inside the question span [start, "[answer]" + 1).
    qent = torch.zeros(questions, N_ENT)
    for q in range(questions):
        v = int(batch.q_visit[q])
        start, end = int(batch.q_span[q, 0]), int(batch.q_span[q, 1])
        toks = batch.tokens[v, start:end]
        ids = toks[(toks >= vocab_size) & (toks < vocab_size + N_ENT)] - vocab_size
        qent[q, ids] = 1.0

    shared = torch.einsum("qe,qle->ql", qent, cards[batch.q_visit]) > 0      # card names a question entity
    matched = eligible & shared
    target, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
    gold_real = target[:, :lines]                                           # gold cards in the candidate space
    gold_cards = cards[batch.q_visit.unsqueeze(1), batch.gold_lines.clamp_min(0)]   # [Q, G, N_ENT], direct
    gold_named_each = ((gold_cards * qent.unsqueeze(1)).sum(-1) > 0) & (batch.gold_lines >= 0)
    return {
        "n": matched.sum(1),                                                # (a) eligible cards naming the person
        "n_fact_lines": (matched & card_has_entity[batch.q_visit]).sum(1),  # (b) same, restricted to fact lines
        "eligible": eligible.sum(1),
        "eligible_with_entity": (eligible & card_has_entity[batch.q_visit]).sum(1),
        "question_entities": qent.sum(1).long(),
        "told": told,
        "gold_count": (batch.gold_lines >= 0).sum(1),
        "gold_named": gold_named_each.any(1),                               # (c) some gold card names the person
        "gold_hits": (gold_real & matched).sum(1),                          # |G intersect M| for told questions
        "gold_eligible": gold_real.sum(1),                                  # |G| (all gold cards are eligible)
        "gold_missing": missing,                                            # store.gold check: must be all zero
    }


def merge(parts: Sequence[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    return {key: torch.cat([part[key] for part in parts]) for key in parts[0]}


# ----------------------------------------------------------------- summaries


def _quantile(xs: Sequence[float], q: float) -> float:
    if not xs:
        return float("nan")
    ordered = sorted(xs)
    position = q * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def describe(values: Sequence[int]) -> dict[str, Any]:
    """n, mean, median, p90, max, the share at least 8, and the histogram (1..8, 9-16, 17+ and 0 apart)."""
    if not values:
        return {"n": 0}
    xs = [int(v) for v in values]
    histogram = {name: 0 for name in ["0"] + BINS}
    for x in xs:
        histogram[_bin(x)] += 1
    return {
        "n": len(xs), "mean": sum(xs) / len(xs), "median": float(statistics.median(xs)),
        "p90": _quantile(xs, 0.9), "min": min(xs), "max": max(xs),
        "share_ge_8": sum(x >= 8 for x in xs) / len(xs), "zeros": histogram["0"],
        "histogram": histogram,
    }


def ceilings(n: Sequence[int], hits: Sequence[int], gold: Sequence[int], eligible: Sequence[int],
             gold_eligible: Sequence[int]) -> dict[str, Any]:
    """Told questions only. `hits` = |gold cards intersect matched cards|, so hits / n is the chance that a
    uniform pick from the entity-matched eligible cards is a gold card (rank 1 of "filter by entity, then
    uniform"; for one gold card it is 1 / n). The baseline is a uniform pick from all eligible cards, and the
    fallback rule picks uniformly from all eligible cards when no eligible card names the person."""
    matched = [h / m for m, h in zip(n, hits) if h > 0]
    single = [1 / m for m, h, g in zip(n, hits, gold) if h > 0 and g == 1]
    everything = [h / m if m > 0 else 0.0 for m, h in zip(n, hits)]
    fallback = [(h / m) if m > 0 else (ge / e if e > 0 else 0.0)
                for m, h, e, ge in zip(n, hits, eligible, gold_eligible)]
    baseline = [ge / e if e > 0 else 0.0 for e, ge in zip(eligible, gold_eligible)]
    return {
        "gold_matched_questions": len(matched),
        "ceiling_E_h_over_n_given_gold_matched": sum(matched) / len(matched) if matched else float("nan"),
        "ceiling_E_1_over_n_single_gold_given_matched": sum(single) / len(single) if single else float("nan"),
        "single_gold_matched_questions": len(single),
        "ceiling_E_h_over_n_all_told_zero_when_no_match": sum(everything) / len(everything) if everything else float("nan"),
        "ceiling_fallback_to_all_eligible_when_no_match": sum(fallback) / len(fallback) if fallback else float("nan"),
        "baseline_uniform_over_all_eligible_cards": sum(baseline) / len(baseline) if baseline else float("nan"),
    }


def per_question(parts: dict[str, torch.Tensor], ids: Sequence[str]) -> list[dict[str, Any]]:
    rows = []
    for i, qid in enumerate(ids):
        rows.append({"id": qid, "n": int(parts["n"][i]), "n_fact_lines": int(parts["n_fact_lines"][i]),
                     "eligible": int(parts["eligible"][i]), "told": bool(parts["told"][i]),
                     "gold_count": int(parts["gold_count"][i]), "gold_named": bool(parts["gold_named"][i]),
                     "gold_hits": int(parts["gold_hits"][i]), "question_entities": int(parts["question_entities"][i])})
    return rows


def report(parts: dict[str, torch.Tensor]) -> dict[str, Any]:
    n = parts["n"].tolist()
    told = parts["told"].tolist()
    told_n = [m for m, t in zip(n, told) if t]
    told_hits = [h for h, t in zip(parts["gold_hits"].tolist(), told) if t]
    told_gold = [g for g, t in zip(parts["gold_count"].tolist(), told) if t]
    not_told_n = [m for m, t in zip(n, told) if not t]
    told_named = [bool(g) for g, t in zip(parts["gold_named"].tolist(), told) if t]
    single = [g == 1 for g in told_gold]
    named_n = [m for m, g, t in zip(n, parts["gold_named"].tolist(), told) if t and g]
    return {
        "a_all_eligible_cards_naming_person": describe(n),
        "b_fact_lines_only_naming_person": describe(parts["n_fact_lines"].tolist()),
        "b_equals_a_everywhere": bool(torch.equal(parts["n"], parts["n_fact_lines"])),
        "eligible_cards_any_entity_or_not": describe(parts["eligible"].tolist()),
        "question_entities_per_question": describe(parts["question_entities"].tolist()),
        "told_questions": describe(told_n),
        "told_gold_lines_per_question": describe(told_gold),
        "told_single_gold_share": sum(single) / len(single) if single else float("nan"),
        "c_told_gold_card_names_a_question_entity_share": (sum(told_named) / len(told_named)) if told_named else float("nan"),
        "c_told_gold_card_names_person_candidate_counts": describe(named_n),
        "d_not_told_questions": describe(not_told_n),
        "told_questions_naming_a_person": describe([m for m, t, e in zip(n, told, parts["question_entities"].tolist()) if t and e > 0]),
        "told_questions_naming_a_person_gold_named_share": (
            sum(1 for g, t, e in zip(parts["gold_named"].tolist(), told, parts["question_entities"].tolist()) if t and e > 0 and g)
            / max(1, sum(1 for t, e in zip(told, parts["question_entities"].tolist()) if t and e > 0))),
        "told_questions_naming_no_person_in_question": sum(1 for e, t in zip(parts["question_entities"].tolist(), told) if t and e == 0),
        "told_questions_naming_no_person_share": (sum(1 for e, t in zip(parts["question_entities"].tolist(), told) if t and e == 0) / max(1, sum(told))),
        "ceilings_told": ceilings(told_n, told_hits, told_gold,
                                  [e for e, t in zip(parts["eligible"].tolist(), told) if t],
                                  [g for g, t in zip(parts["gold_eligible"].tolist(), told) if t]),
        "gold_missing_from_store_total": int(parts["gold_missing"].sum()),
    }


# ----------------------------------------------------------------- toy and village


def toy_check(log: Callable[[str], None]) -> dict[str, Any]:
    spec = ToySpec()
    batches = [label_free(b) for b in toy_set(spec, 16, 16, 303)]
    parts = merge([count_batch(b, spec.vocab_size) for b in batches])
    result = report(parts)
    mean = result["a_all_eligible_cards_naming_person"]["mean"]
    ceiling = result["ceilings_told"]["ceiling_E_1_over_n_single_gold_given_matched"]
    result["expected_from_s4_card"] = {"mean": 2.29, "ceiling": 0.485}
    result["matches_expected"] = bool(abs(mean - 2.29) < 0.01 and abs(ceiling - 0.485) < 0.005)
    result["questions"] = int(parts["n"].shape[0])
    result["batches"] = len(batches)
    log(f"toy: questions {result['questions']}, mean {mean:.4f} (expect 2.29), ceiling {ceiling:.4f} "
        f"(expect 0.485), matches {result['matches_expected']}")
    return result


def build_village(work: Path, args: argparse.Namespace, log: Callable[[str], None]) -> dict[str, Any]:
    started = time.perf_counter()
    for split, count in (("train", args.train_visits), ("validation", args.valid_visits)):
        write_shards(split, count, work, args.workers, seed=args.seed, visits_per_shard=args.visits_per_shard,
                     verbose=False)
    log(f"shards: train {args.train_visits}, validation {args.valid_visits} visits under {work} "
        f"({time.perf_counter() - started:.1f}s)")
    tokenizer = Tokenizer.load(ROOT / TOKENIZER)
    if tokenizer.vocab_size != VOCAB_V2:
        raise ValueError(f"tokenizer has {tokenizer.vocab_size} ids, expected {VOCAB_V2}")
    detector = pdata.fit_detector(work / "train", workers=1)
    names = all_names()
    misses = [name for name in names if not detector.is_name(name)]
    log(f"detector {detector.digest[:12]}: pool names it misses {len(misses)} of {len(names)}")
    cache = pdata.build_cache(work / "validation", tokenizer, detector, regime=preprocess.LABEL_FREE)
    log(f"cache validation [label-free]: {len(cache)} visits, {len(cache.question_ids)} questions, "
        f"{int(cache.lengths.sum())} tokens; stats {json.dumps(cache.info['stats'], sort_keys=True)}")
    batches = list(pdata.batches(cache, args.max_tokens))
    vocab = tokenizer.vocab_size
    names_lower = {name.lower() for name in names}
    parts_list, label_free_same, leaked, label_free_error = [], True, 0, None
    for batch in batches:
        parts = count_batch(batch, vocab)
        parts_list.append(parts)
        # Name check: no pool name may be spelled out in a question span (that would be an unpointerized entity).
        for q in range(batch.q_visit.shape[0]):
            v = int(batch.q_visit[q])
            start, end = int(batch.q_span[q, 0]), int(batch.q_span[q, 1])
            toks = [int(t) for t in batch.tokens[v, start:end].tolist() if not vocab <= t < vocab + N_ENT]
            words = {w.lower() for w in re.findall(r"[A-Za-z]+", tokenizer.decode(toks))}
            leaked += bool(words & names_lower)
        try:
            again = count_batch(label_free(batch), vocab)
            label_free_same &= bool(torch.equal(again["n"], parts["n"]))
        except ValueError as error:
            label_free_error = str(error)
    merged = merge(parts_list)
    ids = [qid for batch in batches for qid in batch.question_ids]
    result = {
        "visits": len(cache), "questions": len(ids), "batches": len(batches), "max_tokens": args.max_tokens,
        "tokens": int(cache.lengths.sum()), "vocab_size": vocab, "n_ent": N_ENT,
        "tokenizer": {"path": TOKENIZER, "sha256": tokenizer.digest, "vocab_size": vocab},
        "detector_digest": detector.digest, "pool_names_missed_by_detector": len(misses),
        "preprocess": preprocess.identity(preprocess.LABEL_FREE),
        "cache_stats": cache.info["stats"],
        "question_spans_with_spelled_pool_name": leaked,
        "label_free_train_rule_leaves_counts_unchanged": label_free_same,
        "label_free_train_rule_error": label_free_error,
        "report": report(merged),
        "build_seconds": time.perf_counter() - started,
    }
    result["per_question"] = per_question(merged, ids)
    rep = result["report"]
    log(f"village: questions {len(ids)} (told {rep['told_questions']['n']}), mean n {rep['told_questions']['mean']:.3f}, "
        f"median {rep['told_questions']['median']}, p90 {rep['told_questions']['p90']}, max {rep['told_questions']['max']}, "
        f"share >=8 {rep['told_questions']['share_ge_8']:.4f}")
    log(f"village ceilings (told): {json.dumps(rep['ceilings_told'], sort_keys=True)}")
    log(f"village not told: {json.dumps(rep['d_not_told_questions'], sort_keys=True)}")
    log(f"checks: spelled pool names in spans {leaked}; label_free rule leaves counts unchanged {label_free_same}; "
        f"gold missing from store {rep['gold_missing_from_store_total']}; b equals a {rep['b_equals_a_everywhere']}")
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--work", type=Path, default=OUT / "build",
                        help="where the generated village shards, detector and cache go (not committed)")
    parser.add_argument("--out", type=Path, default=OUT, help="summary.json, run.log, per-question file")
    parser.add_argument("--train-visits", type=int, default=512)
    parser.add_argument("--valid-visits", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--visits-per-shard", type=int, default=256)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=16_384)
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    log_path = args.out / "run.log"
    log_path.write_text("", encoding="utf-8")

    def log(message: str) -> None:
        print(message, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    log(f"command: python3 -B {Path(__file__).relative_to(ROOT)} " + " ".join(sys.argv[1:] if argv is None else argv))
    started = time.perf_counter()
    toy = toy_check(log)
    village = build_village(args.work, args, log)
    rule = (
        "A card is one non-question line with a card end inside the batch (CardStore.write, "
        "premonition/store.py:54-70: valid = card_end on a non-question line with line_start >= 0). A question on "
        "line q_line sees the cards with line index < q_line (CardStore.eligible: valid[q_visit] & line < q_line, "
        "premonition/store.py:83-100), no wipe floor, no fetched mask (the first ASK). NULL is not counted. A card "
        "names the question's person when its line_ents (store.ents, entity ids) intersect the entity ids in "
        "tokens[q_visit, q_span[0]:q_span[1]] (tokens vocab_size <= t < vocab_size + 16). Gold: store.gold, "
        "premonition/store.py:142-161; gold named is checked directly from gold_lines and line_ents."
    )
    summary = {
        "task": "S4-P0 village candidate count", "script": str(Path(__file__).relative_to(ROOT)),
        "argv": sys.argv[1:] if argv is None else list(argv),
        "split": "validation (the repo's standard eval split)", "regime": "label-free v2 cache (pdata.build_cache)",
        "eligibility_rule": rule, "toy_sanity": toy, "village": {k: v for k, v in village.items() if k != "per_question"},
        "generated_build": {"seed": args.seed, "train_visits": args.train_visits,
                            "valid_visits": args.valid_visits, "visits_per_shard": args.visits_per_shard,
                            "note": "procedurally generated from seed; no on-disk village build exists in this checkout"},
        "runtime_seconds": time.perf_counter() - started,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=float) + "\n",
                                           encoding="utf-8")
    (args.out / "village_per_question.json").write_text(
        json.dumps(village["per_question"], separators=(",", ":")) + "\n", encoding="utf-8")
    log(f"wrote {args.out / 'summary.json'} and {args.out / 'village_per_question.json'} "
        f"({time.perf_counter() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
