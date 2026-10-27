"""Milestone-3 continuation 3: address-keyed evidence selection vs the pooled card (answer-only choosing).

Declared diagnostic (full_verdict: false): synthetic-vocabulary toy ladder, legacy toy label-free rule, supplied
gold-evidence cards (privileged, identical for every arm), nothink+qread decode, H1 OFF, model defaults unchanged.
The variant (premonition/address_reader.py, default off) gets EXPLICIT STRUCTURAL HELP: a parse of the synthetic line
layout (token 1 person, token 2 relation/LINK) whose input embeddings form the cards' selection keys.

Arms (seeds 0 and 1, predeclared):
  pooled   answer-original-s{0,1}: completed milestone-3 controls (not retrained); scores from milestone 3, actual
           outputs from the direct-reader continuation (artifacts/.../direct/outputs).
  address  answer-address-s{0,1}: the pooled build + the address projection (dedicated init generator; the shared
           weights and the global random stream are identical), trained by premonition_pool_controls.answer_loop
           (same frozen stream, 600 gold-only then all supplied cards, 2000 steps, answer CE, card-order generator).
Also reported descriptively: the direct-reader arms answer-direct-s{0,1}.

Shared ledger artifacts/opus-m03-20260919-071009/ledger.jsonl, cap AMENDED 1800 -> 2100 s (BUDGET_AMENDMENT; all
earlier charges kept; frozen baseline sources untouched; sealed prefix verified). Training runs
ONLY if the complete two-seed comparison fits after calibration; otherwise the dry run records the extra compute
needed and nothing is trained. Outputs: artifacts/opus-m03-20260919-071009/address/.

    PY -B scripts/premonition_address_keys.py freeze | check --tests ... | dry | train --seed S | eval --ckpt N
    [--split test] | compare
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
OUT = M3_OUT / "address"
DIRECT_ARCHIVE = ROOT / "archive" / f"opus-{M3}-direct"
ARCHIVE = ROOT / "archive" / f"opus-{M3}-address"
NEW_MODULES = ("premonition/address_reader.py",)
HARNESS = "scripts/premonition_address_keys.py"
REUSED = ("scripts/premonition_direct_reader.py", "scripts/premonition_pool_controls.py",
          "scripts/premonition_ovn_ladder.py", "scripts/premonition_ovn_retrieval.py", "premonition/direct_reader.py")
SEEDS = (0, 1)
POOLED = {0: "answer-original-s0", 1: "answer-original-s1"}
DIRECT = {0: "answer-direct-s0", 1: "answer-direct-s1"}
ADDRESS = {seed: f"answer-address-s{seed}" for seed in SEEDS}
ARM = "nothink+qread+addresskeys"
RESERVE = 30.0
THREADS = 8
CAP_SECONDS = 2100.0
BUDGET_AMENDMENT = {"from": 1800.0, "to": CAP_SECONDS, "charged_before": 1569.21, "at": "2026-09-19 09:16 EDT",
                    "by": "user instruction (Ben/Astra): extend the shared local-compute cap, keep all charged time",
                    "enforced_by": "this harness (premonition_pool_controls.CAP_SECONDS stays 1800 in the frozen source)"}
TEST_LABEL = ("PREVIOUSLY CONSULTED test split (ladder test consulted overnight; triplet test consulted in milestone 3 "
              "for the pooled arms and in the direct-reader continuation): descriptive only, never used for decisions")
D = H = L = R = None


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=str))


def freeze() -> None:
    """archive/opus-<M3>-address/frozen = the direct-reader snapshot (byte-identical) + the address module + this
    harness."""
    sums = (DIRECT_ARCHIVE / "FROZEN.SHA256SUMS").read_text().splitlines()
    bad = [n for d, n in (line.split(None, 1) for line in sums) if sha256(DIRECT_ARCHIVE / "frozen" / n) != d]
    if bad:
        raise SystemExit(f"direct-reader snapshot changed: {bad}")
    frozen = ARCHIVE / "frozen"
    if frozen.exists():
        shutil.rmtree(frozen)
    shutil.copytree(DIRECT_ARCHIVE / "frozen", frozen)
    for rel in NEW_MODULES + (HARNESS,):
        (frozen / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, frozen / rel)
    names = sorted(str(p.relative_to(frozen)) for p in frozen.rglob("*") if p.is_file())
    (ARCHIVE / "FROZEN.SHA256SUMS").write_text("".join(f"{sha256(frozen / n)}  ./{n}\n" for n in names))
    write_json(ARCHIVE / "FROZEN-NOTES.json", {
        "continuation_of": M3, "files": len(names), "base": f"archive/opus-{M3}-direct/frozen (byte-identical copy)",
        "added": list(NEW_MODULES + (HARNESS,)),
        "live_differs_from_frozen": [n for n in names if (ROOT / n).exists() and sha256(ROOT / n) != sha256(frozen / n)]})
    print(f"frozen {len(names)} files")


def bootstrap() -> None:
    global D, H, L, R
    frozen = ARCHIVE / "frozen"
    sums = (ARCHIVE / "FROZEN.SHA256SUMS").read_text().splitlines()
    bad = [n for d, n in (line.split(None, 1) for line in sums) if sha256(frozen / n) != d]
    if bad:
        raise SystemExit(f"frozen source changed: {bad}")
    for rel in NEW_MODULES + (HARNESS,) + REUSED:
        if sha256(ROOT / rel) != sha256(frozen / rel):
            raise SystemExit(f"live {rel} differs from the frozen copy: re-freeze (and journal it) first")
    sys.path.insert(0, str(frozen))
    import premonition
    import learnlab
    for module in (premonition, learnlab):
        if not Path(module.__file__).resolve().is_relative_to(frozen.resolve()):
            raise SystemExit(f"{module.__name__} imported from {module.__file__}")
    sys.path.insert(1, str(ROOT / "scripts"))
    import premonition_direct_reader as direct
    import premonition_ovn_ladder as ladder
    import premonition_ovn_retrieval as retrieval
    import premonition_pool_controls as pool_controls
    D, H, L, R = direct, pool_controls, ladder, retrieval
    H.L, H.R = L, R
    D.H, D.L, D.R = H, L, R
    D.check_ledger_prefix()
    import torch
    torch.set_num_threads(THREADS)


def charge(kind: str, name: str, seconds: float, **extra) -> None:
    H.ledger_add(f"address-{kind}", name, seconds, continuation="address-keys", **extra)


def left() -> float:
    return CAP_SECONDS - H.ledger_seconds()


def require(estimate: float, reserve: float = RESERVE) -> None:
    if left() - reserve < estimate:
        raise SystemExit(f"refused: needs ~{estimate:.0f} s, {left():.1f} s left under the amended {CAP_SECONDS:.0f} s cap "
                         f"with a {reserve:.0f} s reserve")


def build_address(seed: int):
    """The pooled build (seeded base, then the variant, then the base weights) + the address projection from its
    dedicated generator; strict apart from the two new tensors."""
    import torch
    from premonition.address_reader import AddressKeyedQReadMini
    from premonition.model import PremonitionMini
    config = H.answer_config()
    torch.manual_seed(seed)
    base = PremonitionMini(config)
    model = AddressKeyedQReadMini(config)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    if unexpected or sorted(missing) != ["address.bias", "address.weight"]:
        raise RuntimeError(f"address build: state mismatch {missing} {unexpected}")
    model.reset_address(seed)
    model._nothink = True
    return model


def ckpt_path(name: str) -> Path:
    return OUT / "ckpt" / f"{name}.pt"


def load_address(name: str):
    import torch
    from premonition.address_reader import AddressKeyedQReadMini
    from premonition.config import MiniConfig
    path = ckpt_path(name)
    blob = torch.load(path, weights_only=False)
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    if asdict(config) != asdict(H.answer_config()):
        raise SystemExit(f"{name}: checkpoint config differs from the answer protocol")
    model = AddressKeyedQReadMini(config)
    model.load_state_dict(blob["state_dict"])
    model._nothink = True
    model.eval()
    return model, {"kind": "answer", "reader": "address", "seed": blob["seed"], "sha256": sha256(path),
                   "file": str(path.relative_to(ROOT))}


def identity(model) -> dict:
    from premonition import address_reader
    return {**H.identity("answer", "original", model), "arm": ARM, "reader": address_reader.identity(model.config)}


# ----------------------------------------------------------------------------- commands
def cmd_check(args) -> None:
    started = time.perf_counter()
    run = subprocess.run([sys.executable, "-B", "-m", "unittest", *args.tests], cwd=ROOT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
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


def cmd_dry(args) -> None:
    """Dry-forward validation + matched step timing on throwaway copies (nothing saved, outputs not inspected beyond
    finiteness/identity checks); writes the complete-comparison estimate, whether it fits, and the shortfall."""
    import torch
    from learnlab.readonly import read_only
    require(40, reserve=RESERVE)
    started = time.perf_counter()
    report = {}
    try:
        pooled, address = H.build("answer", "original", 0), build_address(0)
        item = L.load_split("validation")[0]
        for model in (pooled, address):
            model.eval()
            with read_only(model):
                L.predictions(model, item, cards="all", seed=99)
            model.train()
        with torch.no_grad():
            none = [L.predictions(m, item, cards="none", seed=99)[0] for m in (pooled, address)]
        report["no_cards_decode_identical_at_init"] = bool(torch.equal(none[0], none[1]))
        loss = L.loss_of(address, item, ARM, torch.Generator().manual_seed(1))
        loss.backward()
        grads = {n: p.grad for n, p in address.named_parameters()}
        report["init_loss"] = round(float(loss.detach()), 4)
        report["address_grad_finite_nonzero"] = bool(torch.isfinite(grads["address.weight"]).all()
                                                     and float(grads["address.weight"].abs().max()) > 0)
        timings = {}
        for name, model, arm in (("pooled", H.build("answer", "original", 0), "nothink+qread"),
                                 ("address", build_address(0), ARM)):
            stream, gen = L.checked_train(), torch.Generator().manual_seed(5000)
            D.timed_steps(model, stream, gen, "gold", 2, arm)
            timings[name] = {"gold": D.timed_steps(model, stream, gen, "gold", 8, arm),
                             "all": D.timed_steps(model, stream, gen, "all", 8, arm)}
            t0 = time.perf_counter()
            L.ladder_scores(model, L.load_split("validation")[:H.ANSWER["eval_batches"]])
            timings[name]["in_training_eval"] = time.perf_counter() - t0
        a = H.ANSWER
        modelled = {k: t["gold"] * a["gold_steps"] + t["all"] * (a["steps"] - a["gold_steps"])
                    + t["in_training_eval"] * (a["steps"] // a["eval_every"]) for k, t in timings.items()}
        measured = {"pooled_m03_slowest": 161.49, "direct_s0": 174.49, "direct_s1": 170.74}
        ratio = modelled["address"] / modelled["pooled"]
        train_each = max(modelled["address"], max(measured.values()) * ratio) * 1.10
        package = {"train_address_s0": train_each, "train_address_s1": train_each,
                   "validation_eval_x2": 2 * 7.5 * 1.2, "test_eval_x2": 2 * 3.6 * 1.2, "compare": 5.0,
                   "saving_reserve": RESERVE}
    except BaseException as error:
        charge("failed-dry", "dry-forward + calibration", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    need = sum(package.values())
    remaining = left() - seconds
    report.update(seconds_per_step={k: {p: round(v, 4) for p, v in t.items()} for k, t in timings.items()},
                  modelled_training={k: round(v, 1) for k, v in modelled.items()}, measured_training=measured,
                  address_over_pooled=round(ratio, 3), package={k: round(v, 1) for k, v in package.items()},
                  total_needed=round(need, 1), left_after_dry=round(remaining, 1), fits=bool(need <= remaining),
                  additional_needed=round(max(0.0, need - remaining), 1), dry_seconds=round(seconds, 2))
    if (OUT / "dry.json").exists():
        previous = OUT / f"dry-before-{time.strftime('%H%M%S')}.json"
        (OUT / "dry.json").rename(previous)
        report["previous_estimate"] = str(previous.relative_to(ROOT))
    report["cap_seconds"] = CAP_SECONDS
    write_json(OUT / "dry.json", report)
    charge("dry", "dry-forward validation + matched step timing (throwaway copies)", seconds, fits=report["fits"],
           needed=round(need, 1), additional_needed=report["additional_needed"])
    print(json.dumps(report, indent=1))


def cmd_train(args) -> None:
    import torch
    seed, name = args.seed, ADDRESS[args.seed]
    if ckpt_path(name).exists():
        raise SystemExit(f"{name} exists; never retrained")
    dry = json.loads((OUT / "dry.json").read_text())
    if not dry["fits"]:
        raise SystemExit(f"the complete comparison did not fit at calibration (needs {dry['additional_needed']} s "
                         "more): training refused")
    package = dry["package"]
    estimate = package[f"train_address_s{seed}"]
    rest = sum(v for k, v in package.items() if k not in {f"train_address_s{s}" for s in SEEDS if s <= seed})
    if left() < estimate + rest:
        raise SystemExit(f"refused: {name} needs ~{estimate:.0f} + {rest:.0f} s; {left():.1f} s left")
    started = time.perf_counter()
    deadline = started + (left() - rest)
    try:
        model = build_address(seed)
        history, stopped = H.answer_loop(model, ARM, seed, steps=H.ANSWER["steps"], deadline=deadline)
    except BaseException as error:
        charge("failed-train", name, time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    path = ckpt_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "kind": "answer",
                "reader": "address", "seed": seed, "identity": identity(model)}, path)
    write_json(OUT / "runs" / f"{name}.json", {
        "name": name, "arm": ARM, "seed": seed, "protocol": H.ANSWER, "stopped": stopped, "seconds": round(seconds, 2),
        "history": history, "identity": identity(model), "ckpt": str(path.relative_to(ROOT)),
        "ckpt_sha256": sha256(path), "matched_control": POOLED[seed],
        "command": f"scripts/premonition_address_keys.py train --seed {seed}"})
    charge("train", name, seconds, stopped=stopped, steps=history[-1]["step"] if history else 0)
    print(f"{name}: stopped {stopped} after {history[-1]['step'] if history else 0} steps, {seconds:.1f} s")


def cmd_eval(args) -> None:
    from learnlab.readonly import read_only
    split, name = args.split, args.ckpt
    path = OUT / ("eval" if split == "validation" else "tests") / f"{name}.json"
    if path.exists():
        raise SystemExit(f"{name} already scored on {split}; never rescored")
    require(15, reserve=5)
    started = time.perf_counter()
    try:
        model, info = load_address(name)
        with read_only(model):
            scores = H.evaluate_answer(model, split)
            out = D.outputs(model, split)
    except BaseException as error:
        charge("failed-eval", f"{name} {split}", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    order = D._slice_order(out)
    consistent = {}
    for cards, labels in (("gold", ("read", "read", "read")), ("all", ("choose", "combine", "combine"))):
        joined = "".join(scores["ladder"][f"{lab}:{s}"]["bits"] for lab, s in
                         zip(labels, ("one_hop", "two_hop_trained_rel", "two_hop_heldout_rel")))
        consistent[cards] = "".join(out["bits"][f"{cards}_correct"][i] for i in order) == joined
    write_json(path, {"ckpt": name, **info, "split": split, "read_only": "learnlab.readonly.read_only",
                      "scores": scores, "outputs_summary": out["summary"], "outputs_match_ladder_bits": consistent,
                      "seconds": round(seconds, 2)})
    write_json(OUT / "outputs" / f"{name}-{split}.json", out)
    charge("test-eval" if split == "test" else "eval", name, seconds, outputs_consistent=all(consistent.values()))
    print(name, split, json.dumps(out["summary"]), consistent, f"({seconds:.1f} s)")
    if not all(consistent.values()):
        raise SystemExit("saved outputs disagree with the ladder correctness bits")


def cmd_compare(args) -> None:
    """Paired address - pooled (and, descriptively, address - direct) per seed; predeclared choosing and binding
    rules; the unchanged gate (reported; H1 stays OFF)."""
    import torch
    require(10, reserve=5)
    runs = {}
    for seed in SEEDS:                                    # both runs must have completed before any verdict
        path = OUT / "runs" / f"{ADDRESS[seed]}.json"
        run = json.loads(path.read_text()) if path.exists() else {}
        runs[seed] = {"stopped": run.get("stopped"), "steps": run["history"][-1]["step"] if run.get("history") else 0}
        if runs[seed] != {"stopped": "steps", "steps": H.ANSWER["steps"]}:
            raise SystemExit(f"no verdict: {ADDRESS[seed]} did not complete {H.ANSWER['steps']} steps ({runs[seed]})")
    started = time.perf_counter()
    boot = lambda a, b, c: H.paired_bootstrap(a.float(), b.float(), c, resamples=10000, alpha=0.01)
    result = {"rules": {"choosing": "better iff paired lower bound of (address - pooled) choose:one_hop > 0 on BOTH "
                                    "seeds (validation); worse iff upper bound < 0 on both; else inconclusive",
                        "binding": "same rule on triplets relevant_both_correct",
                        "decisions": "validation only"}, "runs_completed": runs, "test_label": TEST_LABEL,
              "budget_amendment": BUDGET_AMENDMENT, "splits": {}}
    for split, folder in (("validation", "eval"), ("test", "tests")):
        if not all((OUT / folder / f"{ADDRESS[s]}.json").exists() for s in SEEDS):
            continue
        groups = D.clusters(split)
        rows = []
        for seed in SEEDS:
            mine = json.loads((OUT / folder / f"{ADDRESS[seed]}.json").read_text())["scores"]
            for label, control in (("pooled", json.loads((M3_OUT / folder / f"{POOLED[seed]}.json").read_text())),
                                   ("direct", json.loads((D.OUT / folder / f"{DIRECT[seed]}.json").read_text()))):
                ctrl = control["scores"]
                for metric in ("read:one_hop", "choose:one_hop", "combine:two_hop_trained_rel",
                               "combine:two_hop_heldout_rel"):
                    a, b = H.unbits(mine["ladder"][metric]["bits"]), H.unbits(ctrl["ladder"][metric]["bits"])
                    rows.append({"seed": seed, "vs": label, "metric": f"ladder/{metric}", "address": int(a.sum()),
                                 "control": int(b.sum()), "n": len(a), **boot(a, b, groups["slice"][metric.split(":")[1]])})
                for metric in ("x_correct", "v_correct", "invariant_both_correct", "relevant_both_correct",
                               "prediction_changed_on_relevant"):
                    a, b = H.unbits(mine["triplets"][metric]["bits"]), H.unbits(ctrl["triplets"][metric]["bits"])
                    rows.append({"seed": seed, "vs": label, "metric": f"triplets/{metric}", "address": int(a.sum()),
                                 "control": int(b.sum()), "n": len(a), **boot(a, b, torch.arange(len(a)))})
        verdict = {}
        for key, metric in (("choosing", "ladder/choose:one_hop"), ("binding", "triplets/relevant_both_correct")):
            sel = [r for r in rows if r["vs"] == "pooled" and r["metric"] == metric]
            verdict[key] = ("better" if all(r["lower"] > 0 for r in sel) else
                            "worse" if all(r["upper"] < 0 for r in sel) else "inconclusive")
        result["splits"][split] = {"rows": rows, "verdicts": verdict}
    if "validation" in result["splits"]:
        gate, per = H.GATE, {}
        for seed in SEEDS:
            s = json.loads((OUT / "eval" / f"{ADDRESS[seed]}.json").read_text())["scores"]["ladder"]
            per[seed] = {"read1": s["read:one_hop"]["correct"], "choose_point": s["choose:one_hop"]["point"],
                         "choose_lower": s["choose:one_hop"]["lower"]}
        result["gate"] = {"rule": gate, "per_seed": per,
                          "reading_ok": all(v["read1"] >= gate["reading_one_hop_min"] for v in per.values()),
                          "identity_path_ok": all(v["choose_lower"] > gate["choose_lower_bound_above"] for v in per.values()),
                          "choosing_still_weak": any(v["choose_point"] < gate["choose_point_below_on_some_seed"]
                                                     for v in per.values()),
                          "h1": "OFF regardless of the gate"}
        result["gate"]["would_pass"] = all(result["gate"][k] for k in ("reading_ok", "identity_path_ok",
                                                                         "choosing_still_weak"))
    seconds = time.perf_counter() - started
    write_json(OUT / "compare.json", result)
    charge("analysis", "paired address vs pooled/direct, gate report", seconds)
    for split, block in result["splits"].items():
        print(f"== {split}: {block['verdicts']}")
        for r in block["rows"]:
            print(f"s{r['seed']} vs {r['vs']:6} {r['metric']:40} {r['address']:4} {r['control']:4} /{r['n']:3} "
                  f"{r['point']:+.4f} [{r['lower']:+.4f}, {r['upper']:+.4f}]")
    print(json.dumps(result.get("gate"), indent=1))


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
    ev.add_argument("--ckpt", required=True, choices=sorted(ADDRESS.values()))
    ev.add_argument("--split", default="validation", choices=("validation", "test"))
    sub.add_parser("compare")
    args = parser.parse_args()
    if args.command == "freeze":
        return freeze()
    bootstrap()
    {"check": cmd_check, "dry": cmd_dry, "train": cmd_train, "eval": cmd_eval, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
