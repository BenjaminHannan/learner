#!/usr/bin/env python3
"""CPU behavioral checks for the registered scratch-card candidate.

Run after the candidate API lands, before any registered GPU job. This checks
observable invariants rather than repeating the card update equations.
"""
from __future__ import annotations

import argparse
import json
import random
import tempfile
import time
from pathlib import Path

import torch
import torch.nn.functional as F

import codex_numbers_20260927_run as N

E, R = N.E, N.R
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT / "artifacts/codex-numbers-20260927/diagnostics"
EXPECTED_BASE = 1_646_494
EXPECTED_CARD = 1_659_424


def inputs(items, device):
    t, s, y, env = N.tensors(items, device)
    assert torch.equal(env, torch.zeros_like(env)), "model saw a kind label"
    return t, s, y, env


def trace(net, items, wipe=False, rounds=48):
    device = next(net.parameters()).device
    t, s, _, env = inputs(items, device)
    net.eval()
    with torch.no_grad():
        return N.run_trace(net, t, s, env, rounds=rounds, wipe_cards=wipe)


def paired_models(device):
    torch.manual_seed(9276211)
    if device == "mps":
        torch.mps.manual_seed(9276211)
    base = N.make_net(256, 2, 8, device, variant="baseline")
    torch.manual_seed(9276211)
    if device == "mps":
        torch.mps.manual_seed(9276211)
    card = N.make_net(256, 2, 8, device, variant="candidate")
    return base, card


def sample_items():
    rng = random.Random(9276211)
    sums = [E.make_sum(rng, 4) for _ in range(2)]
    sol, puzzle = E.make_latin_base(rng, 5)
    grid = E.latin_item(rng, sol, puzzle)
    # Confirmed member of the diagnostic training partition, not a held-out hand.
    nums = [4, 5, 7, 11]
    solution = E.B1.solve(nums, 24)
    assert solution
    number = E.number_item(rng, nums, 24, solution)
    return {"sums": sums, "grids": [grid], "numbers": [number]}


def check_pair_and_wipe(base, card, items, report):
    bp = dict(base.named_parameters())
    cp = dict(card.named_parameters())
    assert all(name in cp and torch.equal(p, cp[name]) for name, p in bp.items()), \
        "candidate core did not start with the identical baseline weights"
    card_only = {name: p for name, p in cp.items() if name.startswith("cards.")}
    assert card_only and set(cp) == set(bp) | set(card_only), "unexpected or missing candidate weights"
    base_count = sum(p.numel() for p in bp.values())
    card_count = sum(p.numel() for p in cp.values())
    assert (base_count, card_count) == (EXPECTED_BASE, EXPECTED_CARD), (base_count, card_count)
    assert (card_count - base_count) / base_count < 0.01
    report["weights"] = {"baseline": base_count, "candidate": card_count,
                         "added": card_count - base_count,
                         "ratio": (card_count - base_count) / base_count,
                         "identical_initial_core": True}
    report["wiped_equals_baseline"] = {}
    for kind, group in items.items():
        logits_b, halts_b = trace(base, group)
        logits_w, halts_w = trace(card, group, wipe=True)
        assert logits_b.shape == logits_w.shape and halts_b.shape == halts_w.shape
        assert torch.equal(logits_b, logits_w), f"wiped {kind} logits differ from core"
        assert torch.equal(halts_b, halts_w), f"wiped {kind} halts differ from core"
        report["wiped_equals_baseline"][kind] = {"rounds": logits_b.shape[1],
                                                  "raw_logits_equal": True, "raw_halts_equal": True}


def check_state_independence(card, items, report):
    one = items["sums"][:1]
    a = trace(card, one, rounds=4)
    _ = trace(card, items["numbers"], rounds=4)
    b = trace(card, one, rounds=4)
    assert all(torch.equal(x, y) for x, y in zip(a, b)), "card state persisted across calls"
    both = trace(card, items["sums"], rounds=4)
    tolerance = {"rtol": 1e-4, "atol": 1e-5} if next(card.parameters()).device.type == "mps" else \
                {"rtol": 1e-5, "atol": 1e-6}
    for solo_index, item in enumerate(items["sums"]):
        solo = trace(card, [item], rounds=4)
        for paired, alone in zip(both, solo):
            assert torch.allclose(paired[solo_index:solo_index + 1], alone, **tolerance), \
                "one batch item changed another item's card computation"
    report["state"] = {"episode_reset_exact": True, "batch_vs_alone_close": True}


def training_loss(outputs, slot, target):
    parts = []
    for logits, halt in outputs:
        ce, exact = R.ce_and_exact(logits, slot, target)
        parts.append(ce + 0.5 * F.binary_cross_entropy_with_logits(halt.float(), exact))
    return torch.stack(parts).mean()


def card_gradients(card):
    return {name: (None if p.grad is None else float(p.grad.detach().abs().sum()))
            for name, p in card.named_parameters() if name.startswith("cards.")}


def check_gradients(card, items, report):
    t, s, y, env = inputs(items["numbers"], next(card.parameters()).device)
    card.train()
    card.zero_grad(set_to_none=True)
    one = N.run_train(card, t, s, env, n_free=0, n_grad=1)
    training_loss(one, s, y).backward()
    one_grad = card_gradients(card)
    # A write made in the sole round cannot affect any later read in that call.
    assert all(v is None or v == 0 for v in one_grad.values()), \
        "one-round no-free call unexpectedly trained card writes"
    card.zero_grad(set_to_none=True)
    multiple = N.run_train(card, t, s, env, n_free=1, n_grad=3)
    training_loss(multiple, s, y).backward()
    grads = card_gradients(card)
    assert grads and all(v is not None and v > 0 for v in grads.values()), \
        f"a card controller parameter got no delayed answer gradient: {grads}"
    core_grad = [p.grad for name, p in card.named_parameters() if not name.startswith("cards.")]
    assert any(g is not None and bool(g.abs().sum()) for g in core_grad), "core got no gradient"
    report["gradients"] = {"one_round_card_abs_grad": one_grad,
                           "multi_round_card_abs_grad": grads,
                           "multi_round_core_nonzero": True}
    card.zero_grad(set_to_none=True)


def check_poison_traverses_cards(card, item, report):
    calls = []
    original = card.cards.step

    def tracked(*args, **kwargs):
        flag = kwargs.get("wipe_cards", args[-1] if args and isinstance(args[-1], bool) else False)
        calls.append(bool(flag))
        return original(*args, **kwargs)

    card.cards.step = tracked
    try:
        poison = N.poison_test(card, item, next(card.parameters()).device.type, wipe_cards=True)
    finally:
        card.cards.step = original
    assert calls and all(calls), "poison check bypassed the wiped card path"
    assert poison["logits_equal"] and poison["predictions_equal"] and poison["raw_halts_equal"]
    report["poison"] = {"card_steps_seen": len(calls), "all_steps_wiped": True,
                        "same_outputs_after_hidden_kind_change": True}


def check_checkpoint(card, items, report):
    before = trace(card, items["numbers"], rounds=4)
    with tempfile.TemporaryDirectory(prefix="cardcheck-") as temp:
        path = Path(temp) / "candidate.pt"
        torch.save({"config": {"variant": "candidate", "width": 256, "layers": 2, "heads": 8},
                    "state": card.state_dict()}, path)
        loaded, cfg = N.load_checkpoint(path, next(card.parameters()).device.type)
        assert cfg["variant"] == "candidate"
        after = trace(loaded, items["numbers"], rounds=4)
        assert all(torch.equal(x, y) for x, y in zip(before, after)), "checkpoint reload changed outputs"
    report["checkpoint"] = {"candidate_roundtrip_exact": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    args = parser.parse_args()
    if args.device == "mps" and not torch.backends.mps.is_available():
        parser.error("MPS is unavailable")
    if args.device == "cpu":
        torch.set_num_threads(1)
    out = args.out or DEFAULT_OUT_DIR / f"cardcheck-{args.device}.json"
    start = time.monotonic()
    report = {"device": args.device, "dtype": "float32", "torch": torch.__version__,
              "source_hashes": {**N.source_hashes("candidate"),
                                "runner": N.sha256(N.__file__),
                                "cardcheck": N.sha256(__file__)},
              "status": "running", "checks": []}
    try:
        base, card = paired_models(args.device)
        items = sample_items()
        for name, fn in (
            ("pair_and_wipe", lambda: check_pair_and_wipe(base, card, items, report)),
            ("state_independence", lambda: check_state_independence(card, items, report)),
            ("gradients", lambda: check_gradients(card, items, report)),
            ("poison_traversal", lambda: check_poison_traverses_cards(card, items["numbers"][0], report)),
            ("checkpoint", lambda: check_checkpoint(card, items, report)),
        ):
            fn()
            report["checks"].append(name)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["seconds"] = time.monotonic() - start
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["status"], "checks": report["checks"],
                          "seconds": round(report["seconds"], 2), "report": str(out)}, sort_keys=True))


if __name__ == "__main__":
    main()
