#!/usr/bin/env python3
"""claude-numbers-diag (Helper T), part 3: run the FITTED memorising net (codex seed 9276193, 962/962 on practice)
on the 300 held-out 4-number hands (and its own 100 dev hands). CPU, 1 thread, no training, no file edits.
Loads the net with codex's own code (scripts/codex_numbers_20260927_run.py: load_checkpoint, run_trace, stop_round).

  python -B scripts/claude_numbers_diag_fitnet.py [--out artifacts/claude-numbers-diag-20260928/fitnet.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

import torch

torch.set_num_threads(1)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_numbers_diag_logs as D  # noqa: E402  (categorize, ROOT, E, L)
import claude_numbers_diag_answers as A  # noqa: E402  (remap, skeleton, stored_tokens)
import codex_numbers_20260927_run as C  # noqa: E402

E, L, ROOT = D.E, D.L, D.ROOT
FIT = ROOT / "codex-numbers-20260927/diagnostics/fit-baseline-s9276193"


@torch.no_grad()
def trace(net, items, bs=50):
    """per item: list of 48 predicted answer rows (7 tokens) and 48 halt probabilities"""
    net.eval()
    out = []
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, y, env = C.tensors(chunk, "cpu")
        lg, q = C.run_trace(net, t, s, env, C.TEST_ROUNDS)
        preds = lg.argmax(-1).tolist()
        halts = torch.sigmoid(q.float()).tolist()
        W = t.shape[2]
        for p, h in zip(preds, halts):
            out.append(([tuple(r[2 * W:2 * W + 7]) for r in p], h))
    return out


def analyse(name, items, tr, practice, ham_rng):
    manifest_prac = [(sorted(n), tuple(A.stored_tokens(n, t, s))) for n, t, s in practice]
    stored_set = {tok for _, tok in manifest_prac}
    skel_of = {tuple(sorted(n)): A.skeleton(A.stored_tokens(n, t, s)) for n, t, s in practice}
    cats, dists, hams = collections.Counter(), [], []
    verbatim = same_skel_nearest = same_as_nearest_remap = right_numbers = n_valid_at = 0
    fixed = {r: 0 for r in (1, 2, 4, 8, 16, 32, 48)}
    any_round = 0
    stops, own_valid = [], 0
    distinct_rounds = []
    rnd_sum = rnd_w2 = 0
    for it, (rows, halts) in zip(items, tr):
        nums, target = it.meta["nums"], it.meta["target"]
        valid = L.solutions_for(nums, target)
        stop = C.stop_round([list(r) for r in rows], halts)
        pred = list(rows[stop])
        c, dist, ham, common = D.categorize(pred, nums, target, valid)
        cats[c] += 1
        own_valid += c == "valid"
        if c == "wrong_value":
            dists.append(dist)
        hams.append(ham)
        right_numbers += common == 4
        stops.append(stop + 1)
        for r in fixed:
            fixed[r] += D.categorize(list(rows[r - 1]), nums, target, valid)[0] == "valid"
        any_round += any(D.categorize(list(r), nums, target, valid)[0] == "valid" for r in rows)
        distinct_rounds.append(len(set(rows)))
        h = sorted(nums)
        nearest = min(manifest_prac, key=lambda p: sum(abs(x - y) for x, y in zip(p[0], h)))
        remapped = A.remap(nearest[1], nearest[0], h)
        verbatim += tuple(pred) in stored_set
        same_as_nearest_remap += tuple(pred) == remapped
        same_skel_nearest += A.skeleton(tuple(pred)) == A.skeleton(nearest[1])
        # random control: one random well-formed answer with the right numbers
        rnd = ham_rng
        shapes = A.SHAPES
        order = nums[:]; rnd.shuffle(order); nx = iter(order)
        row = [E.VAL + next(nx) if c_ == "n" else rnd.choice(list(E.OPS.values())) for c_ in rnd.choice(shapes)]
        rh = min(sum(a != b for a, b in zip(row, v)) for v in valid)
        rnd_sum += rh; rnd_w2 += rh <= 2
    n = len(items)
    return {
        "panel": name, "n": n, "categories_at_own_stop": dict(cats),
        "answers_with_exactly_the_right_four_numbers": right_numbers,
        "wrong_value_answers": {"n": len(dists), "median_miss_from_target": sorted(dists)[len(dists) // 2] if dists else None,
                                "within_3": sum(d <= 3 for d in dists)},
        "mean_min_hamming_to_nearest_valid_answer_of_7": round(sum(hams) / n, 2),
        "answers_within_2": sum(h <= 2 for h in hams),
        "random_control_mean_min_hamming": round(rnd_sum / n, 2), "random_control_within_2": rnd_w2,
        "copy_checks": {"output_identical_to_a_stored_answer_of_some_practice_hand": verbatim,
                        "output_identical_to_nearest_practice_hand_answer_remapped_by_rank": same_as_nearest_remap,
                        "output_skeleton_equals_nearest_practice_hand_skeleton": same_skel_nearest},
        "right_after_n_rounds": {str(k): v for k, v in fixed.items()}, "right_at_own_stop": own_valid,
        "right_at_any_of_48_rounds": any_round, "mean_stop_round": round(sum(stops) / n, 2),
        "mean_distinct_answers_over_48_rounds": round(sum(distinct_rounds) / n, 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/claude-numbers-diag-20260928/fitnet.json")
    a = ap.parse_args()
    import random
    t0 = time.time()
    net, cfg = C.load_checkpoint(FIT / "final.pt", "cpu")
    four, _ = E.number_hands()
    manifest = json.loads((FIT / "devsplit_manifest.json").read_text())
    prac_hands = {tuple(h) for h in manifest["train_four_hands"]}
    practice = [r for r in four if tuple(r[0]) in prac_hands]           # the 962 hands this net practised on
    assert len(practice) == 962
    held300 = C.read_panel(ROOT / "codex-numbers-20260927/panels/numbers4.jsonl")
    dev100 = C.read_panel(FIT / "diagnostic-panels/dev_numbers4.jsonl")
    train962 = C.read_panel(FIT / "diagnostic-panels/train_numbers4.jsonl")
    res = {"net": "codex fit-baseline-s9276193/final.pt (width256, 2 layers, 60,000 steps, practice 962/962)",
           "checkpoint_config_width_layers": [cfg["width"], cfg["layers"]],
           "practice_hands_this_net_saw": len(practice)}
    for name, items in (("held_out_300", held300), ("dev_100", dev100), ("practice_962_sanity_first_150", train962[:150])):
        tr = trace(net, items)
        res[name] = analyse(name, items, tr, practice, random.Random(20260928))
        print(name, json.dumps(res[name]), flush=True)
    res["seconds"] = round(time.time() - t0)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
