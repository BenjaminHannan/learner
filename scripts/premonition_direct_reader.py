"""Milestone-3 CONTINUATION: direct contextual-state reader vs the pooled card (answer-only choosing).

Declared diagnostic (NOT full-v2, NOT a primary verdict; full_verdict: false): synthetic-vocabulary toy ladder
(declared exception to the v2 tokenizer rule), legacy toy label-free rule (premonition.train.label_free via
L.label_free_item), supplied gold-evidence cards (privileged), nothink+qread decode, H1 OFF.

Arms (seeds 0 and 1, predeclared):
  pooled  answer-original-s{0,1}: the COMPLETED milestone-3 pooled controls (s0 = overnight exp1 checkpoint, replay
          verified exact in milestone 3; s1 = milestone-3 run). Same frozen code path, same build, data stream,
          optimizer, schedule, CE and card-order generator as below; not retrained.
  direct  answer-direct-s{0,1}: premonition/direct_reader.DirectReaderQReadMini, built exactly like the pooled arm
          (identical initial weights and random stream; no new parameters) and trained by the SAME function
          (premonition_pool_controls.answer_loop: 600 gold-only then all supplied cards, 2000 steps, answer CE).
The only difference: the decoder reads the selected lines' contextual token states (same reader pass) instead of
one pooled row per line (see premonition/direct_reader.py).

ONE shared ledger: artifacts/opus-m03-20260919-071009/ledger.jsonl (cap 1800 s, append-only; the sealed milestone-3
prefix is verified on every command). Everything executed here is charged: checks, dry-forward calibration, training,
evaluation, card-removal outputs, analysis and failures. Outputs: artifacts/opus-m03-20260919-071009/direct/.

    PY -B scripts/premonition_direct_reader.py freeze
    PY -B scripts/premonition_direct_reader.py check --tests tests.test_premonition_direct_reader
    PY -B scripts/premonition_direct_reader.py dry
    PY -B scripts/premonition_direct_reader.py train --seed 0
    PY -B scripts/premonition_direct_reader.py eval --ckpt answer-direct-s0 [--split test]
    PY -B scripts/premonition_direct_reader.py compare
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
M3 = "m03-20260919-071009"
M3_OUT = ROOT / "artifacts" / f"opus-{M3}"
M3_ARCHIVE = ROOT / "archive" / f"opus-{M3}"
OUT = M3_OUT / "direct"
ARCHIVE = ROOT / "archive" / f"opus-{M3}-direct"
NEW_MODULES = ("premonition/direct_reader.py",)
HARNESS = "scripts/premonition_direct_reader.py"
REUSED_HARNESSES = ("scripts/premonition_pool_controls.py", "scripts/premonition_ovn_ladder.py",
                    "scripts/premonition_ovn_retrieval.py")
SEALED_LEDGER = {"rows": 27, "sha256": "6a53be97243d2d82ca7a3bc2daad677d1809f58c700f1eb69e7189706f0872b7"}
SEEDS = (0, 1)
POOLED = {0: "answer-original-s0", 1: "answer-original-s1"}
DIRECT = {seed: f"answer-direct-s{seed}" for seed in SEEDS}
ARM = "nothink+qread+directread"
OUTPUT_SEED = {"validation": 99, "test": 7}          # = premonition_pool_controls.evaluate_answer's ladder seeds
RESERVE = 30.0
THREADS = 8
H = L = R = None


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=str))


# ----------------------------------------------------------------------------- freeze / bootstrap
def freeze() -> None:
    """archive/opus-<M3>-direct/frozen = milestone 3's frozen snapshot (byte-identical) + the direct-reader module
    + this harness."""
    sums = (M3_ARCHIVE / "FROZEN.SHA256SUMS").read_text().splitlines()
    bad = [n for d, n in (line.split(None, 1) for line in sums) if sha256(M3_ARCHIVE / "frozen" / n) != d]
    if bad:
        raise SystemExit(f"milestone-3 snapshot changed: {bad}")
    frozen = ARCHIVE / "frozen"
    if frozen.exists():
        shutil.rmtree(frozen)
    shutil.copytree(M3_ARCHIVE / "frozen", frozen)
    for rel in NEW_MODULES + (HARNESS,):
        (frozen / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, frozen / rel)
    names = sorted(str(p.relative_to(frozen)) for p in frozen.rglob("*") if p.is_file())
    (ARCHIVE / "FROZEN.SHA256SUMS").write_text("".join(f"{sha256(frozen / n)}  ./{n}\n" for n in names))
    live_diff = [n for n in names if (ROOT / n).exists() and sha256(ROOT / n) != sha256(frozen / n)]
    write_json(ARCHIVE / "FROZEN-NOTES.json", {
        "continuation_of": M3, "files": len(names), "base": f"archive/opus-{M3}/frozen (byte-identical copy)",
        "added": list(NEW_MODULES + (HARNESS,)), "live_differs_from_frozen": live_diff})
    print(f"frozen {len(names)} files; live differs: {live_diff}")


def check_ledger_prefix() -> None:
    lines = (M3_OUT / "ledger.jsonl").read_bytes().splitlines(keepends=True)
    prefix = b"".join(lines[:SEALED_LEDGER["rows"]])
    if hashlib.sha256(prefix).hexdigest() != SEALED_LEDGER["sha256"]:
        raise SystemExit("the sealed milestone-3 ledger prefix changed")


def bootstrap() -> None:
    global H, L, R
    frozen = ARCHIVE / "frozen"
    sums = (ARCHIVE / "FROZEN.SHA256SUMS").read_text().splitlines()
    bad = [n for d, n in (line.split(None, 1) for line in sums) if sha256(frozen / n) != d]
    if bad:
        raise SystemExit(f"frozen source changed: {bad}")
    for rel in NEW_MODULES + (HARNESS,) + REUSED_HARNESSES:
        if sha256(ROOT / rel) != sha256(frozen / rel):
            raise SystemExit(f"live {rel} differs from the frozen copy: re-freeze (and journal it) first")
    check_ledger_prefix()
    sys.path.insert(0, str(frozen))
    import premonition
    import learnlab
    for module in (premonition, learnlab):
        if not Path(module.__file__).resolve().is_relative_to(frozen.resolve()):
            raise SystemExit(f"{module.__name__} imported from {module.__file__}")
    sys.path.insert(1, str(ROOT / "scripts"))
    import premonition_pool_controls as pool_controls
    import premonition_ovn_ladder as ladder
    import premonition_ovn_retrieval as retrieval
    H, L, R = pool_controls, ladder, retrieval
    H.L, H.R = L, R
    import torch
    torch.set_num_threads(THREADS)


def charge(kind: str, name: str, seconds: float, **extra) -> None:
    H.ledger_add(f"direct-{kind}", name, seconds, continuation="direct-reader", **extra)


def left() -> float:
    return H.CAP_SECONDS - H.ledger_seconds()


# ----------------------------------------------------------------------------- models
def build_direct(seed: int):
    """H.build('answer', 'original', seed) with the direct-reader class: seeded base, then the variant, then the base
    weights (identical weights and random stream; strict load: no new parameters)."""
    import torch
    from premonition.direct_reader import DirectReaderQReadMini
    from premonition.model import PremonitionMini
    config = H.answer_config()
    torch.manual_seed(seed)
    base = PremonitionMini(config)
    model = DirectReaderQReadMini(config)
    model.load_state_dict(base.state_dict())
    model._nothink = True
    return model


def direct_identity(model) -> dict:
    from premonition import direct_reader
    return {**H.identity("answer", "original", model), "arm": ARM, "reader": direct_reader.identity(model.config)}


def ckpt_path(name: str) -> Path:
    return OUT / "ckpt" / f"{name}.pt"


def load_any(name: str):
    """(model, info): direct checkpoints from this continuation, pooled ones through milestone 3's loader."""
    import torch
    from premonition.config import MiniConfig
    from premonition.direct_reader import DirectReaderQReadMini
    if name not in DIRECT.values():
        model, info = H.load(name)
        return model, {**info, "reader": "pooled"}
    path = ckpt_path(name)
    blob = torch.load(path, weights_only=False)
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    if asdict(config) != asdict(H.answer_config()):
        raise SystemExit(f"{name}: checkpoint config differs from the answer protocol")
    model = DirectReaderQReadMini(config)
    model.load_state_dict(blob["state_dict"])
    model._nothink = True
    model.eval()
    return model, {"kind": "answer", "writer": "original", "reader": "direct", "seed": blob["seed"],
                   "sha256": sha256(path), "file": str(path.relative_to(ROOT)), "reused": False}


# ----------------------------------------------------------------------------- commands
def cmd_check(args) -> None:
    started = time.perf_counter()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    run = subprocess.run([sys.executable, "-B", "-m", "unittest", *args.tests], cwd=ROOT, env=env,
                         capture_output=True, text=True)
    seconds = time.perf_counter() - started
    log = OUT / "checks" / f"{time.strftime('%H%M%S')}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"$ unittest {' '.join(args.tests)}\n{run.stdout}{run.stderr}")
    tail = (run.stdout + run.stderr).strip().splitlines()[-3:]
    charge("check", " ".join(args.tests), seconds, returncode=run.returncode, log=str(log.relative_to(ROOT)),
           result=" | ".join(tail))
    print(f"{seconds:.1f} s", "\n".join(tail))
    if run.returncode:
        print(run.stdout[-4000:], run.stderr[-4000:])
        raise SystemExit(run.returncode)


def timed_steps(model, stream, gen, cards: str, count: int, arm: str) -> float:
    import torch
    params, optimizer = H.optimizer_for(model)
    started = time.perf_counter()
    for _ in range(count):
        loss = L.loss_of(model, next(stream), arm, gen, cards=cards)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if not all(q.grad is None or bool(torch.isfinite(q.grad).all()) for q in params):
            raise SystemExit(f"non-finite gradient in the dry run ({arm}, {cards})")
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()
    return (time.perf_counter() - started) / count


def cmd_dry(args) -> None:
    """Dry-forward validation + calibration on THROWAWAY copies (nothing saved): memory sizes, finiteness, read-only
    decoding, then matched per-step timings of the pooled and direct arms on the same batches; writes the full-package
    estimate and whether it fits."""
    import torch
    from learnlab.readonly import read_only
    H.require(45, reserve=RESERVE)
    started = time.perf_counter()
    report = {}
    try:
        pooled, direct = H.build("answer", "original", 0), build_direct(0)
        item = L.load_split("validation")[0]
        eps = {}
        for name, model in (("pooled", pooled), ("direct", direct)):
            model.eval()
            with read_only(model):
                ep, _, _, _ = L.episode(model, item, cards="all", generator=torch.Generator().manual_seed(99),
                                        passes=0)
                first, ok = L.predictions(model, item, cards="all", seed=99)
            eps[name] = ep
            model.train()
        ep = eps["direct"]
        start, width = ep.direct_rows
        report["memory"] = {"pooled_rows": int(eps["pooled"].x.shape[1]), "direct_rows": int(ep.x.shape[1]),
                            "token_region": width, "valid_token_rows_mean": round(float(ep.valid[:, start:].sum(1)
                                                                                         .float().mean()), 2),
                            "valid_pooled_card_rows_mean": round(float(
                                eps["pooled"].valid[:, pooled._card_base:pooled._card_base + pooled.config.cards]
                                .sum(1).float().mean()), 2)}
        with torch.no_grad():
            none = [L.predictions(m, item, cards="none", seed=99)[0] for m in (pooled, direct)]
        report["no_cards_decode_identical_at_init"] = bool(torch.equal(none[0], none[1]))
        loss = L.loss_of(direct, item, ARM, torch.Generator().manual_seed(1))
        report["init_loss_direct"] = round(float(loss), 4)
        timings = {}
        for name, model, arm in (("pooled", H.build("answer", "original", 0), "nothink+qread"),
                                 ("direct", build_direct(0), ARM)):
            stream, gen = L.checked_train(), torch.Generator().manual_seed(5000)
            timed_steps(model, stream, gen, "gold", 2, arm)                          # warm-up
            timings[name] = {"gold": timed_steps(model, stream, gen, "gold", 8, arm),
                             "all": timed_steps(model, stream, gen, "all", 8, arm)}
            t0 = time.perf_counter()
            L.ladder_scores(model, L.load_split("validation")[:H.ANSWER["eval_batches"]])
            timings[name]["in_training_eval"] = time.perf_counter() - t0
        report["seconds_per_step"] = {k: {p: round(v, 4) for p, v in t.items()} for k, t in timings.items()}
        a = H.ANSWER
        model_estimate = {k: t["gold"] * a["gold_steps"] + t["all"] * (a["steps"] - a["gold_steps"])
                          + t["in_training_eval"] * (a["steps"] // a["eval_every"]) for k, t in timings.items()}
        pooled_actual = 161.49         # slowest milestone-3 answer run (same loop and machine; conservative)
        ratio = model_estimate["direct"] / model_estimate["pooled"]
        train_each = max(model_estimate["direct"], pooled_actual * ratio) * 1.10
        eval_ratio = timings["direct"]["in_training_eval"] / timings["pooled"]["in_training_eval"]
        package = {
            "train_direct_s0": train_each, "train_direct_s1": train_each,
            "validation_eval_direct_x2": 2 * (5.6 * eval_ratio + 3.0 * eval_ratio) * 1.2,
            "validation_outputs_pooled_x2": 2 * 3.0 * 1.2,
            "test_eval_direct_x2": 2 * (2.5 * eval_ratio + 2.0 * eval_ratio) * 1.2,
            "test_outputs_pooled_x2": 2 * 2.0 * 1.2,
            "compare_analysis": 5.0, "saving_reserve": RESERVE}      # regression ran before calibration
        report["estimate"] = {"per_arm_training_model": {k: round(v, 1) for k, v in model_estimate.items()},
                              "pooled_actual_training": pooled_actual, "direct_over_pooled": round(ratio, 3),
                              "train_each_with_10pct_margin": round(train_each, 1),
                              "package": {k: round(v, 1) for k, v in package.items()}}
    except BaseException as error:
        charge("failed-dry", "dry-forward + calibration", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    need = sum(package.values())
    remaining = left() - seconds
    report["estimate"].update(total_needed=round(need, 1), left_after_dry=round(remaining, 1),
                              fits=bool(need <= remaining))
    report["dry_seconds"] = round(seconds, 2)
    write_json(OUT / "dry.json", report)
    charge("dry", "dry-forward validation + matched step timing (throwaway copies)", seconds,
           fits=report["estimate"]["fits"], needed=round(need, 1))
    print(json.dumps(report, indent=1))


def cmd_train(args) -> None:
    import torch
    seed = args.seed
    name = DIRECT[seed]
    if ckpt_path(name).exists():
        raise SystemExit(f"{name} exists; this continuation never retrains")
    dry = json.loads((OUT / "dry.json").read_text())
    if not dry["estimate"]["fits"]:
        raise SystemExit("the full package did not fit at calibration: training refused")
    package = dry["estimate"]["package"]
    estimate = package[f"train_direct_s{seed}"]
    rest = sum(v for k, v in package.items() if k not in {f"train_direct_s{s}" for s in SEEDS if s <= seed})
    if left() < estimate + rest:                                     # rest includes the saving reserve
        raise SystemExit(f"refused: {name} needs ~{estimate:.0f} s + {rest:.0f} s for the rest of the package; "
                         f"{left():.1f} s left")
    started = time.perf_counter()
    deadline = started + (left() - rest)                             # never eat into the rest of the package
    try:
        model = build_direct(seed)
        history, stopped = H.answer_loop(model, ARM, seed, steps=H.ANSWER["steps"], deadline=deadline)
    except BaseException as error:
        charge("failed-train", name, time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    path = ckpt_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "kind": "answer",
                "writer": "original", "reader": "direct", "seed": seed, "identity": direct_identity(model)}, path)
    write_json(OUT / "runs" / f"{name}.json", {
        "name": name, "arm": ARM, "seed": seed, "protocol": H.ANSWER, "stopped": stopped, "seconds": round(seconds, 2),
        "history": history, "identity": direct_identity(model), "ckpt": str(path.relative_to(ROOT)),
        "ckpt_sha256": sha256(path), "matched_control": POOLED[seed],
        "command": f"scripts/premonition_direct_reader.py train --seed {seed}"})
    charge("train", name, seconds, stopped=stopped, steps=history[-1]["step"] if history else 0)
    print(f"{name}: stopped {stopped} after {history[-1]['step'] if history else 0} steps, {seconds:.1f} s")


def outputs(model, split: str) -> dict:
    """Actual greedy token sequences per question under all / gold-only / no supplied cards (card orders and seeds as
    the ladder readout), with per-question correctness and removal-change flags."""
    import torch
    from learnlab.core import IGNORE_INDEX
    items = L.load_split(split)
    seed0 = OUTPUT_SEED[split]
    seq = {c: [] for c in ("all", "gold", "none")}
    ok = {c: [] for c in seq}
    hops, held, qids = [], [], []
    for i, item in enumerate(items):
        batch = item[0]
        targets = [row[row != IGNORE_INDEX].tolist() for row in batch.answer]
        for cards in seq:
            ep, _, _, _ = L.episode(model, item, cards=cards, generator=torch.Generator().manual_seed(seed0 + i),
                                    passes=0)
            tokens, lengths = model._greedy(batch, ep, model._mentions(batch), None)
            got = [tokens[q, :int(lengths[q])].tolist() for q in range(tokens.shape[0])]
            seq[cards] += got
            ok[cards] += [g == t for g, t in zip(got, targets)]
        hops += item[2].tolist()
        held += item[0].slices["heldout"].tolist()
        qids += list(batch.question_ids)
    slices = {"one_hop": [h == 1 for h in hops], "two_hop_trained_rel": [h == 2 and not x for h, x in zip(hops, held)],
              "two_hop_heldout_rel": [h == 2 and x for h, x in zip(hops, held)]}
    summary = {}
    for name, mask in slices.items():
        pick = [i for i, m in enumerate(mask) if m]
        entry = {"n": len(pick)}
        for cards in seq:
            entry[f"correct_{cards}"] = sum(ok[cards][i] for i in pick)
            entry[f"distinct_first_tokens_{cards}"] = len({tuple(seq[cards][i][:1]) for i in pick})
        entry["sequence_changed_all_vs_none"] = sum(seq["all"][i] != seq["none"][i] for i in pick)
        entry["sequence_changed_gold_vs_none"] = sum(seq["gold"][i] != seq["none"][i] for i in pick)
        entry["sequence_changed_all_vs_gold"] = sum(seq["all"][i] != seq["gold"][i] for i in pick)
        summary[name] = entry
    bits = {f"{c}_correct": "".join("1" if x else "0" for x in ok[c]) for c in seq}
    bits["changed_all_vs_none"] = "".join("1" if a != b else "0" for a, b in zip(seq["all"], seq["none"]))
    bits["changed_gold_vs_none"] = "".join("1" if a != b else "0" for a, b in zip(seq["gold"], seq["none"]))
    return {"summary": summary, "bits": bits, "sequences": seq, "question_ids": qids, "hops": hops, "heldout": held}


def cmd_eval(args) -> None:
    from learnlab.readonly import read_only
    split, name = args.split, args.ckpt
    folder = OUT / ("eval" if split == "validation" else "tests")
    path = folder / f"{name}.json"
    if path.exists():
        raise SystemExit(f"{name} already scored on {split}; never rescored")
    H.require(25, reserve=5)
    started = time.perf_counter()
    try:
        model, info = load_any(name)
        with read_only(model):
            scores = H.evaluate_answer(model, split) if info["reader"] == "direct" else None
            out = outputs(model, split)
    except BaseException as error:
        charge("failed-eval", f"{name} {split}", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    reference = None
    if scores is None:                                   # pooled control: milestone-3 scores, not recomputed
        ref_path = M3_OUT / ("eval" if split == "validation" else "tests") / f"{name}.json"
        reference = {"file": str(ref_path.relative_to(ROOT)), "sha256": sha256(ref_path)}
        ladder = json.loads(ref_path.read_text())["scores"]["ladder"]
    else:
        ladder = scores["ladder"]
    consistent = {}
    order = _slice_order(out)
    for cards, labels in (("gold", ("read", "read", "read")), ("all", ("choose", "combine", "combine"))):
        joined = "".join(ladder[f"{lab}:{s}"]["bits"] for lab, s in zip(labels, ("one_hop", "two_hop_trained_rel",
                                                                                  "two_hop_heldout_rel")))
        consistent[cards] = "".join(out["bits"][f"{cards}_correct"][i] for i in order) == joined
    write_json(path, {"ckpt": name, **info, "split": split, "read_only": "learnlab.readonly.read_only",
                      "scores": scores, "reference_scores": reference, "outputs_summary": out["summary"],
                      "outputs_match_ladder_bits": consistent, "seconds": round(seconds, 2)})
    write_json(OUT / "outputs" / f"{name}-{split}.json", out)
    charge("test-eval" if split == "test" else "eval", name, seconds, outputs_consistent=all(consistent.values()))
    print(name, split, json.dumps(out["summary"]), consistent, f"({seconds:.1f} s)")
    if not all(consistent.values()):
        raise SystemExit("saved outputs disagree with the ladder correctness bits")


def _slice_order(out) -> list:
    """Question indices in the ladder readout's concatenation order (one_hop, trained 2-hop, held-out 2-hop)."""
    hops, held = out["hops"], out["heldout"]
    return ([i for i, h in enumerate(hops) if h == 1] + [i for i, (h, x) in enumerate(zip(hops, held)) if h == 2
                                                          and not x]
            + [i for i, (h, x) in enumerate(zip(hops, held)) if h == 2 and x])


def clusters(split: str) -> dict:
    """Visit ids per question, in question order ('question') and in the ladder readout's slice order ('slice')."""
    import torch
    hops, held, visits = [], [], []
    for i, item in enumerate(L.load_split(split)):
        hops.append(item[2])
        held.append(item[0].slices["heldout"])
        visits.append(item[0].q_visit + i * int(item[0].tokens.shape[0]))
    hop, held, visit = (torch.cat(x) for x in (hops, held, visits))
    masks = {"one_hop": hop == 1, "two_hop_trained_rel": (hop == 2) & ~held, "two_hop_heldout_rel": (hop == 2) & held}
    return {"question": visit, "masks": masks, "slice": {k: visit[m] for k, m in masks.items()}}


def cmd_compare(args) -> None:
    """Paired direct - pooled per seed (visit- or triplet-clustered one-sided 99% bounds, 10,000 resamples), the
    predeclared choosing rule, the unchanged validation gate (reported only; H1 stays OFF) and removal changes."""
    import torch
    H.require(10, reserve=5)
    started = time.perf_counter()
    unbits, boot = H.unbits, lambda a, b, c: H.paired_bootstrap(a.float(), b.float(), c, resamples=10000, alpha=0.01)
    result = {"rule": "choosing: 'better' iff the paired lower bound of (direct - pooled) choose:one_hop > 0 on BOTH "
                      "seeds (validation); 'worse' iff the upper bound < 0 on both; else 'inconclusive'",
              "splits": {}, "gate": {}}
    for split in ("validation", "test"):
        folder = "eval" if split == "validation" else "tests"
        if not all((OUT / folder / f"{DIRECT[s]}.json").exists() for s in SEEDS):
            continue
        groups = clusters(split)
        rows = []
        for seed in SEEDS:
            pooled = json.loads((M3_OUT / folder / f"{POOLED[seed]}.json").read_text())["scores"]
            direct = json.loads((OUT / folder / f"{DIRECT[seed]}.json").read_text())["scores"]
            for metric in ("read:one_hop", "choose:one_hop", "read:two_hop_trained_rel", "combine:two_hop_trained_rel",
                           "read:two_hop_heldout_rel", "combine:two_hop_heldout_rel"):
                a, b = unbits(direct["ladder"][metric]["bits"]), unbits(pooled["ladder"][metric]["bits"])
                rows.append({"seed": seed, "metric": f"ladder/{metric}", "direct": int(a.sum()), "pooled": int(b.sum()),
                             "n": len(a), **boot(a, b, groups["slice"][metric.split(":")[1]])})
            for metric in ("x_correct", "u_correct", "v_correct", "invariant_both_correct", "relevant_both_correct",
                           "all_three_correct", "prediction_changed_on_relevant"):
                a, b = unbits(direct["triplets"][metric]["bits"]), unbits(pooled["triplets"][metric]["bits"])
                rows.append({"seed": seed, "metric": f"triplets/{metric}", "direct": int(a.sum()),
                             "pooled": int(b.sum()), "n": len(a), **boot(a, b, torch.arange(len(a)))})
            outs = {arm: json.loads((OUT / "outputs" / f"{name}-{split}.json").read_text())["bits"]
                    for arm, name in (("direct", DIRECT[seed]), ("pooled", POOLED[seed]))}
            for flag in ("changed_all_vs_none", "changed_gold_vs_none"):
                for slice_name, mask in groups["masks"].items():
                    a, b = unbits(outs["direct"][flag])[mask], unbits(outs["pooled"][flag])[mask]
                    rows.append({"seed": seed, "metric": f"removal/{flag}/{slice_name}", "direct": int(a.sum()),
                                 "pooled": int(b.sum()), "n": len(a), **boot(a, b, groups["question"][mask])})
            if split == "validation":
                result.setdefault("causal_two_hop_all_supplied", {})[f"s{seed}"] = {
                    "direct": direct["causal_two_hop_all_supplied"], "pooled": pooled["causal_two_hop_all_supplied"]}
        choose = [r for r in rows if r["metric"] == "ladder/choose:one_hop"]
        verdict = ("better" if all(r["lower"] > 0 for r in choose) else
                   "worse" if all(r["upper"] < 0 for r in choose) else "inconclusive")
        result["splits"][split] = {"rows": rows, "choosing_verdict": verdict}
    if "validation" in result["splits"]:
        gate = H.GATE
        per_seed = {}
        for seed in SEEDS:
            scores = json.loads((OUT / "eval" / f"{DIRECT[seed]}.json").read_text())["scores"]["ladder"]
            per_seed[seed] = {"read1": scores["read:one_hop"]["correct"], "choose_point": scores["choose:one_hop"]["point"],
                              "choose_lower": scores["choose:one_hop"]["lower"]}
        result["gate"] = {"rule": gate, "direct_per_seed": per_seed,
                          "reading_ok": all(v["read1"] >= gate["reading_one_hop_min"] for v in per_seed.values()),
                          "identity_path_ok": all(v["choose_lower"] > gate["choose_lower_bound_above"]
                                                  for v in per_seed.values()),
                          "choosing_still_weak": any(v["choose_point"] < gate["choose_point_below_on_some_seed"]
                                                     for v in per_seed.values()),
                          "h1": "OFF in this continuation regardless of the gate"}
        result["gate"]["would_pass"] = all(result["gate"][k] for k in ("reading_ok", "identity_path_ok",
                                                                         "choosing_still_weak"))
    flips = {}
    for arm in ("original", "mean", "two"):                              # Astra's reporting correction (m03 bits)
        scores = json.loads((M3_OUT / "eval" / f"retrieval-{arm}-s0.json").read_text())["scores"]
        entry = {}
        for s in ("one_hop", "two_hop_trained_rel", "two_hop_heldout_rel"):
            a = scores["own_fixed_K3"][s]["bits"]
            b = scores["own_fixed_K3_cards_removed"][s]["bits"]
            entry[s] = {"with_cards": a.count("1"), "cards_removed": b.count("1"),
                        "outcomes_changed": sum(x != y for x, y in zip(a, b))}
        flips[f"retrieval-{arm}-s0"] = entry
    result["m03_retrieval_removal_correctness_flips"] = {
        "note": "correctness bits only (m03 saved no sequences): unchanged totals do not prove identical answers",
        **flips}
    seconds = time.perf_counter() - started
    write_json(OUT / "compare.json", result)
    charge("analysis", "paired direct - pooled, gate report, removal changes", seconds)
    for split, block in result["splits"].items():
        print(f"== {split}: choosing {block['choosing_verdict']}")
        for r in block["rows"]:
            print(f"s{r['seed']} {r['metric']:44} direct {r['direct']:4} pooled {r['pooled']:4} /{r['n']:3} "
                  f"{r['point']:+.4f} [{r['lower']:+.4f}, {r['upper']:+.4f}]")
    print(json.dumps({k: v for k, v in result.items() if k not in ("splits",)}, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze")
    check = sub.add_parser("check")
    check.add_argument("--tests", nargs="+", required=True)
    sub.add_parser("dry")
    train = sub.add_parser("train")
    train.add_argument("--seed", type=int, choices=SEEDS, required=True)
    ev = sub.add_parser("eval")
    ev.add_argument("--ckpt", required=True, choices=sorted(set(POOLED.values()) | set(DIRECT.values())))
    ev.add_argument("--split", default="validation", choices=("validation", "test"))
    sub.add_parser("compare")
    args = parser.parse_args()
    if args.command == "freeze":
        return freeze()
    bootstrap()
    {"check": cmd_check, "dry": cmd_dry, "train": cmd_train, "eval": cmd_eval, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
