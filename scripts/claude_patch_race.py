#!/usr/bin/env python3
"""Legacy nine-rung few-example driver; fail closed after ruler revision.

This script never edits the ruler. Published baseline validity, source gates,
and a committed race seal are required before adaptation or holdout scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import torch

import claude_patch_practice as P

ROOT, OUT = P.ROOT, P.OUT
RULER = ROOT / "artifacts/claude-fewex-20260927"
MARKS_COMMIT = "3acb5d18a"
RULER_COMMIT = "aeb524cd0"  # upstream registered pre-maze corrections 1–3
BASELINE_SOURCE_STEPS = 12000
SOURCE_GUARD_SEED = 9233000  # ruler SOURCE_SEED + 300, ADDENDUM-3
ARMS = ("patch", "loop_meta", "plain", "loop")
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384, 65536)
LOCKED = tuple("artifacts/claude-fewex-20260927/" + name for name in
    ("PROTOCOL.md", "PASSMARKS.md", "RACE-PASSMARKS.md", "ADDENDUM-1.md", "ADDENDUM-2.md", "ADDENDUM-3.md")) + tuple("scripts/" + name for name in
    ("claude_fewex_bench.py", "claude_fewex_data.py", "claude_fewex_net.py", "claude_fewex_source_qualify.py"))


class NotReady(RuntimeError):
    pass


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def committed(path):
    rel = str(Path(path).relative_to(ROOT))
    try:
        return git("show", "HEAD:" + rel) == Path(path).read_bytes()
    except subprocess.CalledProcessError:
        return False


def verify_locked():
    # The equal-practice ruler superseded this nine-rung harness and F_all.
    # A future source-eligible patch needs a separately sealed F_eq driver;
    # the original failed practice gate cannot be bypassed here.
    if (RULER / "ADDENDUM-4.md").exists() or (RULER / "RACE-ADDENDUM-1.md").exists():
        raise NotReady("equal-practice ruler supersedes this nine-rung driver; use a newly sealed F_eq race driver")
    for rel in LOCKED:
        expected = git("show", f"{RULER_COMMIT}:{rel}")
        if (ROOT / rel).read_bytes() != expected:
            raise NotReady(f"locked ruler source differs from its seal: {rel}")
    if P.sha(ROOT / "scripts/claude_rsn358a_envs.py") != "af350749936eaa084af696cf191c9111cc3aaf03594cd84e8827ba883c9b54d0":
        raise NotReady("ruler environment dependency differs from its seal")
    if P.sha(ROOT / "scripts/claude_rsn358m_maze.py") != "99c0b77c13deb32a146abda79784157c6bbad3745a9fa0a65840a12d27ad99bc":
        raise NotReady("ruler maze dependency differs from its seal")


def baseline_validity(out):
    """Recount V1–V3 from committed ruler raw JSON, never its narrative verdict."""
    verify_locked()
    paths = [p.decode() for p in git("ls-files", "-z", "artifacts/claude-fewex-20260927").split(b"\0") if p]
    sources, adaptations, evidence, superseded = {}, {}, {}, {}
    for path in paths:
        if not path.endswith(("/source.json", "/adapt.json")):
            continue
        raw = git("show", "HEAD:" + path)
        row = json.loads(raw)
        arm, seed = row.get("arm"), row.get("seed")
        if arm not in ("loop", "plain") or seed not in (0, 1):
            continue
        if path.endswith("/source.json") and not (
                row.get("source_steps") == BASELINE_SOURCE_STEPS and row.get("source_batch") == 64 and
                row.get("source_guard_seed") == SOURCE_GUARD_SEED):
            superseded[path] = {"sha256": hashlib.sha256(raw).hexdigest(),
                "source_steps": row.get("source_steps"), "source_guard_seed": row.get("source_guard_seed"),
                "old": row.get("old"), "reason": "not the ADDENDUM-3 qualified baseline recipe"}
            continue
        dest = sources if path.endswith("/source.json") else adaptations
        key = (arm, seed) if dest is sources else (arm, seed, row.get("init"))
        if key in dest and dest[key] != row:
            raise NotReady(f"ambiguous published ruler records for {key}")
        dest[key] = row
        evidence[path] = hashlib.sha256(raw).hexdigest()
    expected_source = {(a, s) for a in ("loop", "plain") for s in (0, 1)}
    expected_adapt = {(a, s, i) for a in ("loop", "plain") for s in (0, 1) for i in ("pre", "fresh")}
    v1 = v2 = v3 = None
    ladder = {}
    if expected_source <= sources.keys():
        v1 = all(all(row["old"][k]["n"] == 200 and row["old"][k]["right"] >= 190
                     for k in ("sums4", "grids5")) for row in sources.values())
        v2 = all(row["gradient_check"]["nonzero_all"] is True and row["gradient_check"]["missing_both"] == []
                 and row["gradient_check"].get("matrix_count", 0) > 0
                 for row in sources.values())
    if expected_adapt <= adaptations.keys():
        for key in sorted(expected_adapt):
            row = adaptations[key]
            mid = sum(row["rungs"][str(k)]["9"]["n"] == 300 and
                      30 < row["rungs"][str(k)]["9"]["right"] < 270 for k in RUNGS)
            ladder[str(key)] = mid
        v3 = any(n >= 3 for n in ladder.values())
    status = "pass" if v1 is True and v2 is True and v3 is True else \
             "inconclusive" if any(v is False for v in (v1, v2, v3)) else "waiting"
    result = {"utc": P.utc(), "status": status, "V1": v1, "V2": v2, "V3": v3,
        "midrange_rungs": ladder, "published_source_records": len(sources),
        "published_adapt_records": len(adaptations), "raw_sha256": evidence,
        "qualified_source_steps": BASELINE_SOURCE_STEPS, "qualified_source_guard_seed": SOURCE_GUARD_SEED,
        "superseded_source_records": superseded,
        "read_at_commit": git("rev-parse", "HEAD").decode().strip()}
    P.save(out / "BASELINE-VALIDITY.json", result)
    return result


def own_readiness(out):
    P.verify_seal(out)
    path = out / "PRACTICE-GATES.json"
    if not path.exists():
        raise NotReady("wider-practice jobs have not completed")
    if not json.loads(path.read_text())["passed"]:
        raise NotReady("wider-practice gate failed; no design race")
    subprocess.run([sys.executable, "-B", str(ROOT / "scripts/claude_patch_recount.py")], check=True)
    recount = json.loads((out / "BLIND-RECOUNT.json").read_text())
    if recount["practice_gate"]["status"] != "pass":
        raise NotReady("independent raw practice recount did not pass")
    return json.loads((out / "QUALIFIED-SEAL.json").read_text())["kinds"]


def plugin(arm, init="pre", telemetry=None):
    os.environ["CLAUDE_PATCH_CORE"] = "patch" if arm == "patch" else "loop"
    os.environ["CLAUDE_PATCH_INIT"] = init
    if telemetry is None:
        os.environ.pop("CLAUDE_PATCH_TELEMETRY", None)
    else:
        os.environ["CLAUDE_PATCH_TELEMETRY"] = str(telemetry)
    name = "claude_patch_plugin"
    return importlib.reload(sys.modules[name]) if name in sys.modules else importlib.import_module(name)


def external_arm(arm):
    return "plain" if arm == "plain" else "loop"


def source_dir(out, arm, seed):
    return out / "race/sources" / f"{arm}-seed{seed}"


def job_dir(out, arm, seed, init):
    return out / "race" / f"{arm}-seed{seed}-{init}"


def jobs():
    return [(arm, seed, init) for seed in (0, 1) for arm in ARMS
            for init in (("pre", "fresh") if arm == "patch" else ("pre",))]


def prepare(out):
    verify_locked()
    kinds = own_readiness(out)
    if not committed(out / "ADDENDUM-wide-practice.md"):
        raise NotReady("wide-practice addendum must be committed first")
    import claude_fewex_bench as H
    for logical_seed, source_seed in enumerate(P.SEEDS):
        for arm in ARMS:
            original = out / f"{arm}-{source_seed}"
            dest = source_dir(out, arm, logical_seed)
            digest = P.sha(original / "final.pt")
            if (dest / "source.json").exists():
                previous = json.loads((dest / "source.json").read_text())
                if previous["source_checkpoint_sha256"] != digest or P.sha(dest / "source.pt") != previous["export_sha256"]:
                    raise NotReady("source export provenance changed")
                continue
            record = json.loads((original / "result.json").read_text())
            saved = torch.load(original / "final.pt", map_location="cpu", weights_only=False)
            N = plugin(arm)
            H.N = N
            net = N.Net(external_arm(arm))
            net.core.load_state_dict(saved["state"])
            if arm == "patch":
                net.set_patch(saved["patch"])
            fixed_counts = {str(d): sum(record["dev"][k]["fixed_right"][str(d)] for k in kinds)
                            for d in H.DEPTHS} if arm != "plain" else {}
            fixed = max(H.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d)) if arm != "plain" else 1
            old = {k: H.score(net, values, fixed) for k, values in H.D.old_panels(SOURCE_GUARD_SEED).items()}
            # The ruler requests a CPU fp32 V2 check even though user-authorized
            # training/inference run on the available local GPU.
            net.to("cpu")
            gc = H.gradient_check(net, logical_seed)
            net.to(P.device())
            if not gc["nonzero_all"] or any(row["n"] != 200 or row["right"] < 190 for row in old.values()):
                P.save(dest / "ineligible.json", {"old": old, "gradient_check": gc})
                raise NotReady(f"ruler source guard or CPU gradients failed for {arm} seed {logical_seed}")
            sweep = H.source_plain_lr_sweep(net, logical_seed) if arm == "plain" else None
            dest.mkdir(parents=True, exist_ok=True)
            torch.save({k: v.detach().cpu() for k, v in net.state_dict().items()}, dest / "source.pt")
            P.save(dest / "source.json", {"arm": external_arm(arm), "experiment_arm": arm,
                "seed": logical_seed, "source_seed": source_seed, "source_steps": P.STEPS,
                "source_batch": P.BATCH, "source_episode_steps": P.EPISODES, "source_guard_seed": SOURCE_GUARD_SEED,
                "weights": net.weight_count(), "persistent_coefficients": net.weight_count(),
                "fast_coefficients": 4096 if arm == "patch" else 0,
                "fixed_depth": fixed, "fixed_source_dev": fixed_counts,
                "plain_lr_sweep": sweep, "gradient_check": gc, "old": old,
                "source_checkpoint_sha256": digest, "export_sha256": P.sha(dest / "source.pt"),
                "train_seconds": record["training_seconds"], "operations": record["operations"],
                "matrix_operations": record["matrix_operations"], "device": P.device(),
                "torch": torch.__version__, "dtype": "float32", "utc": P.utc()})
    # A source export/seal is safe before the baseline finishes. Maze runs are not.
    for seed in (0, 1):
        patch_source = json.loads((source_dir(out, "patch", seed) / "source.json").read_text())
        loop_source = json.loads((source_dir(out, "loop_meta", seed) / "source.json").read_text())
        if any(patch_source["old"][k]["right"] < loop_source["old"][k]["right"] - 6
               for k in ("sums4", "grids5")):
            raise NotReady(f"patch exceeds original three-point source deficit in seed {seed}")
    files = [ROOT / rel for rel in LOCKED]
    files += [ROOT / "scripts" / f"claude_patch_{x}.py" for x in ("plugin", "race", "race_report")]
    files += [out / "ADDENDUM-wide-practice.md", out / "CANDIDATE-SEAL.json", out / "QUALIFIED-SEAL.json", out / "PRACTICE-GATES.json"]
    files += list((out / "race/sources").glob("*/source.json"))
    # Store checkpoint digests without committing large duplicate exports.
    files += list((out / "race/sources").glob("*/source.pt"))
    seal = {"utc": P.utc(), "ruler_seal_commit": RULER_COMMIT, "marks_seal_commit": MARKS_COMMIT, "kinds": kinds,
        "race_seeds": [0, 1], "source_seeds": list(P.SEEDS),
        "files": {str(p.relative_to(ROOT)): P.sha(p) for p in sorted(files)}}
    if (out / "RACE-SEAL.json").exists():
        old = json.loads((out / "RACE-SEAL.json").read_text())
        if old["files"] != seal["files"]:
            raise NotReady("race registration already exists with different sources")
    else:
        P.save(out / "RACE-SEAL.json", seal)


def race_ready(out):
    P.verify_seal(out)
    verify_locked()
    if not (out / "RACE-SEAL.json").exists() or not committed(out / "RACE-SEAL.json"):
        raise NotReady("prepare and commit the race seal before any adaptation")
    seal = json.loads((out / "RACE-SEAL.json").read_text())
    for rel, digest in seal["files"].items():
        if P.sha(ROOT / rel) != digest:
            raise NotReady(f"race seal mismatch: {rel}")
    validity = baseline_validity(out)
    if validity["status"] != "pass":
        raise NotReady(f"baseline ruler is {validity['status']}; V1–V3 must pass before any design race")


def call_harness(command, out, arm, seed, init):
    dest = job_dir(out, arm, seed, init)
    dest.mkdir(parents=True, exist_ok=True)
    source = json.loads((source_dir(out, arm, seed) / "source.json").read_text())
    env = dict(os.environ, CLAUDE_PATCH_CORE="patch" if arm == "patch" else "loop",
        CLAUDE_PATCH_INIT=init, CLAUDE_PATCH_COMMAND=command,
        CLAUDE_PATCH_TELEMETRY=str(dest / f"{command}-telemetry.jsonl"),
        CLAUDE_PATCH_RAW_PREDICTIONS=str(dest / f"{command}-predictions.jsonl.gz"),
        CLAUDE_PATCH_FIXED_DEPTH=str(source["fixed_depth"]))
    args = [sys.executable, "-B", str(ROOT / "scripts/claude_fewex_bench.py"), command,
        "--plugin", "claude_patch_plugin", "--arm", external_arm(arm), "--seed", str(seed),
        "--init", init, "--source", str(source_dir(out, arm, seed)), "--out", str(dest), "--threads", "2"]
    with (dest / f"{command}.log").open("ab", buffering=0) as log:
        subprocess.run(args, env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def supplementary_old(out, arm, seed, init):
    import claude_fewex_bench as H
    H.N = plugin(arm, init)
    dest = job_dir(out, arm, seed, init)
    if (dest / "wide-old.json").exists():
        return
    panels, _ = P.read_panels(out)
    result = {}
    for stage in ("k0", "k64", "k65536", "sleep64", "sleep64k"):
        net = H.load_model(dest / f"{stage}.pt", external_arm(arm))
        patch = net.patch_state if arm == "patch" else None
        if stage.startswith("sleep") and patch is not None and any(bool((x != 0).any()) for x in patch):
            raise RuntimeError("sleep checkpoint still contains an active patch")
        result[stage] = P.evaluate(net.core, panels["verify"], P.device(), patch, dest / f"{stage}-wide-raw.jsonl")
    P.save(dest / "wide-old.json", result)
    if arm == "patch":
        panel, banned = H.D.panels()
        support, _ = H.D.supports(seed, banned)
        src = json.loads((source_dir(out, arm, seed) / "source.json").read_text())
        before = H.load_model(dest / "k0.pt", external_arm(arm))
        after = H.load_model(dest / "k64.pt", external_arm(arm))
        P.save(dest / "support-fit.json", {"before64": H.score(before, support, src["fixed_depth"]),
                                           "after64": H.score(after, support, src["fixed_depth"])})


def dev(out):
    race_ready(out)
    for arm, seed, init in jobs():
        dest = job_dir(out, arm, seed, init)
        if not (dest / "adapt.json").exists():
            if any(dest.glob("k*.pt")):
                raise NotReady(f"partial dev branch needs explicit recovery, not silent restart: {dest}")
            call_harness("adapt", out, arm, seed, init)
        supplementary_old(out, arm, seed, init)
    midrange = {}
    for arm, seed, init in jobs():
        if arm == "loop":
            continue  # additional reference does not rescue the primary ladder
        row = json.loads((job_dir(out, arm, seed, init) / "adapt.json").read_text())
        midrange[f"{arm}-{seed}-{init}"] = sum(30 < row["rungs"][str(k)]["9"]["right"] < 270
                                                   and row["rungs"][str(k)]["9"]["n"] == 300 for k in RUNGS)
    P.save(out / "RACE-V3.json", {"utc": P.utc(), "passed": any(n >= 3 for n in midrange.values()),
                                 "midrange_rungs": midrange, "no_retuning": True})
    P.save(out / "DEV-CHECKPOINTS.json", {"utc": P.utc(), "files": {
        str(p.relative_to(ROOT)): P.sha(p) for a, s, i in jobs()
        for p in sorted(job_dir(out, a, s, i).glob("*.pt"))}})


def holdout(out):
    race_ready(out)
    if not (out / "RACE-V3.json").exists() or not json.loads((out / "RACE-V3.json").read_text())["passed"]:
        raise NotReady("registered dev ladder validity did not pass; holdout forbidden")
    if any(not (job_dir(out, a, s, i) / "adapt.json").exists() for a, s, i in jobs()):
        raise NotReady("all dev branches must finish before any holdout")
    if not committed(out / "DEV-CHECKPOINTS.json") or not committed(out / "RACE-V3.json"):
        raise NotReady("commit the dev checkpoint manifest and V3 decision before holdout")
    for rel, digest in json.loads((out / "DEV-CHECKPOINTS.json").read_text())["files"].items():
        if P.sha(ROOT / rel) != digest:
            raise NotReady(f"dev checkpoint changed before holdout: {rel}")
    for arm, seed, init in jobs():
        dest = job_dir(out, arm, seed, init)
        result = dest / "holdout.json"
        attempt = dest / "HOLDOUT-ATTEMPT.json"
        if result.exists():
            if not attempt.exists():
                raise NotReady(f"holdout result lacks one-shot attempt provenance: {dest}")
            continue
        if attempt.exists() or (dest / "holdout-predictions.jsonl.gz").exists():
            raise NotReady(f"interrupted holdout attempt; automatic repetition forbidden: {dest}")
        # Exclusive creation records the attempt before any model sees a
        # holdout input. A missing final JSON never permits an automatic retry.
        with attempt.open("x") as handle:
            json.dump({"utc": P.utc(), "status": "started", "arm": arm, "seed": seed, "init": init,
                "dev_manifest_sha256": P.sha(out / "DEV-CHECKPOINTS.json")}, handle, indent=2)
        call_harness("holdout", out, arm, seed, init)
        P.save(attempt, {"utc": P.utc(), "status": "completed", "arm": arm, "seed": seed, "init": init,
            "dev_manifest_sha256": P.sha(out / "DEV-CHECKPOINTS.json"), "result_sha256": P.sha(result)})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("baseline", "prepare", "dev", "holdout", "report"))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.out = args.out.resolve()
    torch.set_num_threads(2)
    try:
        if args.command == "baseline":
            validity = baseline_validity(args.out)
            P.save(args.out / "RACE-STATUS.json", {"utc": P.utc(), "status": "baseline_" + validity["status"],
                "reason": "Published ruler V1–V3 audit; own practice gates are independently required."})
            print(json.dumps(validity))
        elif args.command == "prepare":
            prepare(args.out)
        elif args.command == "dev":
            dev(args.out)
        elif args.command == "holdout":
            holdout(args.out)
        else:
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/claude_patch_race_report.py"),
                            "--out", str(args.out)], check=True)
    except NotReady as exc:
        P.save(args.out / "RACE-STATUS.json", {"utc": P.utc(), "status": "not_ready", "reason": str(exc)})
        print(f"Not ready: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
