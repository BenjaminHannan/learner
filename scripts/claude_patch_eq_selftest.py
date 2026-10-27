#!/usr/bin/env python3
"""Self-tests for the patch race on the equal-practice ruler; writes selftest.json.

No practice result and no maze panel is scored (one smoke maze outside every panel is made).
  1. sizes: patch 1,652,767 stored numbers vs the ruler loop's 1,645,726 (within 2%)
  2. zero patch = the ordinary loop: 48-round outputs equal the patch core with no patch,
     and the fresh-arm learner leaves bit-identical weights to the harness learner
     (claude_fewex_bench.Learner) on the same batches and sleep
  3. a write changes only the two patch buffers, keeps the bound, and scoring never
     changes the patch
  4. loop_ep state dicts load into the ruler's loop class with equal outputs
  5. both practice arms draw identical episodes and round schedules
  6. one-step fp32 gradients: every matrix nonzero (patch via two differentiable writes;
     loop_ep including one second-order episode)
  7. smoke rung through the harness's own batches(): 512 writes and exactly 2,048 updates;
     a sleep of 512 updates ends with the patch removed
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402
import claude_fewex_net as FN  # noqa: E402
import claude_patch_eq_fresh as FR  # noqa: E402
import claude_patch_eq_plugin as P  # noqa: E402
import claude_patch_eq_practice as Q  # noqa: E402
import claude_patch_net as C  # noqa: E402


def same_params(a, b):
    sa, sb = a.state_dict(), b.state_dict()
    return sa.keys() == sb.keys() and all(torch.equal(sa[k], sb[k]) for k in sa)


def smoke_mazes(n, seed=5):
    _, banned = D.panels()
    rng, seen = random.Random(99100 + seed), set()
    return [D.unique_maze(rng, 9, banned, seen) for _ in range(n)]


def main(out, smoke_rung):
    res, t_start = {}, time.monotonic()
    torch.manual_seed(0)
    pn = P.Net("loop")
    loop = FN.Net("loop")
    res["sizes"] = {"patch_stored_numbers": pn.weight_count(),
                    "patch_parameters": sum(p.numel() for p in pn.parameters()),
                    "patch_buffers": pn.patch_a.numel() + pn.patch_b.numel(),
                    "loop": loop.weight_count(),
                    "relative_to_loop": (pn.weight_count() - loop.weight_count()) / loop.weight_count()}
    assert res["sizes"]["patch_stored_numbers"] == 1652767 and res["sizes"]["loop"] == 1645726
    assert abs(res["sizes"]["relative_to_loop"]) <= .02

    mazes = smoke_mazes(64)
    rng = random.Random(3)
    sums = [D.E.make_sum(rng, 4) for _ in range(8)]
    # 2a. zero patch forward == patch core with no patch at all
    core = C.Net("patch")
    core.load_state_dict({k: v for k, v in pn.state_dict().items() if not k.startswith("patch_")})
    t, s, _ = P.tensors(mazes[:8])
    with torch.no_grad():
        cells, stops = pn(t, s)
        ref_p, ref_q = C.Net.loop_rounds(core, t, s, 48, None)
        ours_p, ours_q = pn.infer_rounds(t, s, 48)
    e, (dr, dc) = core.embed(t, s)
    h = torch.zeros_like(e)
    diff = 0.0
    with torch.no_grad():
        for r in range(48):
            h = core.step(h, e, dr, dc, None)
            diff = max(diff, float((core.read(h)[0] - cells[r]).abs().max()))
    res["zero_patch_forward"] = {"max_abs_logit_diff_48_rounds": diff,
                                 "predictions_equal": bool(torch.equal(ref_p, ours_p)),
                                 "stop_probs_equal": bool(torch.equal(ref_q, ours_q))}
    assert diff == 0.0 and res["zero_patch_forward"]["predictions_equal"]

    # 2b. fresh learner == harness learner (same frozen writer parts), batches and sleep
    torch.manual_seed(900000)
    fresh = FR.Net("loop")
    torch.manual_seed(900000)
    fresh_same = P.Net("loop")
    res["fresh_init_equals_plugin_init"] = same_params(fresh, fresh_same)
    assert res["fresh_init_equals_plugin_init"]
    ours = FR.Learner(copy.deepcopy(fresh), 1e-3)
    ref_net = copy.deepcopy(fresh)
    for name, p in ref_net.named_parameters():
        if name.startswith(P.WRITER_PARTS):
            p.requires_grad_(False)
    B.N = FR
    ref = B.Learner(ref_net, 1e-3)
    for i in range(3):
        ours.maze_batch(mazes[32 * (i % 2):32 * (i % 2) + 32][:16])
        ref.maze_batch(mazes[32 * (i % 2):32 * (i % 2) + 32][:16])
    replay = {"sums4": sums, "grids5": [D.latin_legend(rng, 5) for _ in range(8)]}
    B.SLEEP_STEPS, keep = 3, B.SLEEP_STEPS
    P.SLEEP_STEPS, keep_p = 3, P.SLEEP_STEPS
    ours.sleep(mazes[:8], 7, replay)
    ref.sleep(mazes[:8], 7, replay)
    B.SLEEP_STEPS, P.SLEEP_STEPS = keep, keep_p
    frozen_unchanged = all(torch.equal(dict(fresh.named_parameters())[n], p)
                           for n, p in ours.net.named_parameters() if n.startswith(P.WRITER_PARTS))
    res["fresh_learner_equals_harness_learner"] = {
        "bit_identical_after_3_batches_and_3_sleep_updates": same_params(ours.net, ref.net),
        "writer_rank_slots_gate_unchanged": frozen_unchanged,
        "patch_zero": bool(ours.net.patch_a.abs().sum() == 0 and ours.net.patch_b.abs().sum() == 0),
        "writes": ours.writes, "updates": ours.steps}
    assert all(v for k, v in res["fresh_learner_equals_harness_learner"].items() if k not in ("writes", "updates"))
    assert ours.writes == 0

    # 3. a write touches only the buffers; bound; scoring leaves the patch alone
    B.N = P
    before = {k: v.clone() for k, v in pn.state_dict().items()}
    rounds = pn.write_batch(mazes[:32])
    after = pn.state_dict()
    changed = sorted(k for k in after if not torch.equal(before[k], after[k]))
    bound = max(float(pn.patch_a.abs().max()), float(pn.patch_b.abs().max()))
    snap = (pn.patch_a.clone(), pn.patch_b.clone())
    first = B.score(pn, mazes[32:64], 16)
    second = B.score(pn, list(reversed(mazes[32:64])), 16)
    res["write"] = {"changed_entries": changed, "max_abs_coefficient": bound,
                    "bound": C.SLOT_LIMIT, "own_halt_rounds_total": rounds,
                    "scoring_left_patch_unchanged": bool(torch.equal(snap[0], pn.patch_a)
                                                         and torch.equal(snap[1], pn.patch_b)),
                    "score_order_invariant": first == second}
    assert changed == ["patch_a", "patch_b"] and bound <= C.SLOT_LIMIT + 1e-7
    assert res["write"]["scoring_left_patch_unchanged"] and res["write"]["score_order_invariant"]

    # 4. loop_ep checkpoints load into the ruler's loop with equal outputs
    torch.manual_seed(1)
    cl = C.Net("loop")
    fl = FN.Net("loop")
    fl.load_state_dict(cl.state_dict(), strict=True)
    with torch.no_grad():
        a = C.Net.loop_rounds(cl, t, s, 48)
        b = fl.loop_rounds(t, s, 48)
        la = cl.loop_train(t, s, 5, 3)[-1][0]
        lb = fl.loop_train(t, s, 5, 3)[-1][0]
    res["loop_ep_state_dict"] = {"strict_load": True, "predictions_equal_48_rounds": bool(torch.equal(a[0], b[0])),
                                 "max_abs_logit_diff_8_rounds": float((la - lb).abs().max())}
    assert res["loop_ep_state_dict"]["max_abs_logit_diff_8_rounds"] < 1e-3

    # 5. identical episodes and schedules for both arms (3 episodes each, same seeds)
    ban = Q.banned_inputs()
    draws = {}
    for arm in Q.ARMS:
        torch.manual_seed(0)
        net = Q.make_net(arm)
        ep_rng, ep_rr = random.Random(Q.EPISODE_DATA_SEED), random.Random(Q.EPISODE_ROUND_SEED)
        patch = net.stored_patch() if arm == "patch" else None
        ops = Q.new_ops()
        seen = []
        for _ in range(3):
            probe = random.Random()
            probe.setstate(ep_rng.getstate())
            order, sup, qs = Q.episode_items(probe, ban)
            seen.append([Q.PD.fingerprint(it) for g in sup + qs for it in g])
            obj, patch = Q.episode(arm, net, patch, ep_rng, ep_rr, ban, ops)
            obj.backward()
            if patch is not None:
                patch = patch.detach()
        draws[arm] = {"items": seen, "data_rng": ep_rng.getstate(), "round_rng": ep_rr.getstate(),
                      "ops": ops}
    assert draws["patch"]["items"] == draws["loop_ep"]["items"]
    assert draws["patch"]["data_rng"] == draws["loop_ep"]["data_rng"]
    assert draws["patch"]["round_rng"] == draws["loop_ep"]["round_rng"]
    res["episodes_identical_across_arms"] = {
        "episodes": 3, "items_per_episode": len(draws["patch"]["items"][0]),
        "distinct_items_per_episode": [len(set(x)) for x in draws["patch"]["items"]],
        "same_items": True, "same_rng_states_after": True, "ops": {a: draws[a]["ops"] for a in draws}}
    assert all(n == 20 for n in res["episodes_identical_across_arms"]["distinct_items_per_episode"])

    # 6. gradients
    B.N = P
    torch.manual_seed(0)
    gnet = P.Net("loop")
    gc_patch = B.gradient_check(gnet, 0)
    B.N = FN
    gc_loop = B.gradient_check(FN.Net("loop"), 0)
    torch.manual_seed(0)
    ml = C.Net("loop")
    ops = Q.new_ops()
    obj, _ = Q.episode("loop_ep", ml, None, random.Random(11), random.Random(12), ban, ops)
    obj.backward()
    missing = [n for n, p in ml.named_parameters() if p.ndim == 2 and (p.grad is None or not bool((p.grad != 0).any()))]
    torch.manual_seed(0)
    pl = P.Net("loop")
    obj, _ = Q.episode("patch", pl, pl.stored_patch(), random.Random(11), random.Random(12), ban, Q.new_ops())
    obj.backward()
    missing_p = [n for n, p in pl.named_parameters() if p.ndim == 2 and (p.grad is None or not bool((p.grad != 0).any()))]
    res["gradients"] = {"patch_harness_check": gc_patch, "loop_harness_check": gc_loop,
                        "loop_ep_second_order_episode_missing": missing,
                        "patch_episode_missing": missing_p}
    assert gc_patch["nonzero_all"] and gc_loop["nonzero_all"] and not missing and not missing_p

    # 7. smoke rung and sleep, through the harness's own batches() at k=1
    if smoke_rung:
        B.N = P
        torch.manual_seed(0)
        base = P.Net("loop")
        learner = P.Learner(copy.deepcopy(base), 1e-3)
        t0 = time.monotonic()
        for batch in EQ.batches(mazes[:1], 1, 0):
            learner.maze_batch(batch)
        rung_seconds = time.monotonic() - t0
        sleeper = P.Learner(copy.deepcopy(learner.net), 1e-3)
        written = float(sleeper.net.patch_a.abs().sum())
        secs = sleeper.sleep(mazes[:1], 64, D.replay_old())
        res["smoke_rung"] = {"k": 1, "batches": EQ.N_BATCHES, "writes": learner.writes,
                             "updates": learner.steps, "expected_updates": EQ.N_UPDATES,
                             "own_halt_write_rounds": learner.write_rounds,
                             "write_seconds": learner.write_seconds, "rung_seconds": rung_seconds,
                             "patch_abs_sum_before_sleep": written, "sleep_updates": sleeper.steps,
                             "sleep_seconds": secs,
                             "patch_zero_after_sleep": bool(sleeper.net.patch_a.abs().sum() == 0
                                                            and sleeper.net.patch_b.abs().sum() == 0)}
        assert learner.steps == EQ.N_UPDATES == 2048 and learner.writes == 512
        assert sleeper.steps == 512 and res["smoke_rung"]["patch_zero_after_sleep"] and written > 0
    res.update({"passed": True, "torch": torch.__version__, "threads": torch.get_num_threads(),
                "device": "cpu", "dtype": "float32", "autocast": False,
                "seconds": time.monotonic() - t_start, "utc": Q.utc()})
    B.dump(out, res)
    print(json.dumps({k: res[k] for k in ("sizes", "zero_patch_forward", "write", "passed")}, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--no-smoke-rung", action="store_true")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    main(a.out, not a.no_smoke_rung)
