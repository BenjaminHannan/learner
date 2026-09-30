"""Actual sparse attention checkpoint readiness prerequisite, watcher only.

Fitting is TRAIN-only, no core/sleep optimization. Full fresh inputs freeze
before collection; primary head fixed before DEV. Independent audit required.
Default --check uses stdlib only; never starts training.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT / "artifacts/sol-stop-20260929"
REVIEW = ROOT / "reviews/premonition-moe-2026-09-29"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open("x") as f:
        f.write(json.dumps(data, indent=2, allow_nan=False)+"\n")


def check(phase):
    spec = json.loads((OWN / "READINESS-SPEC-v2.json").read_text())
    for rel, expected in spec["files"].items():
        if sha(ROOT / rel) != expected:
            raise ValueError("READINESS-SEAL-MISMATCH: " + rel)
    if phase == "source":
        manifest = spec["source"]
    else:
        # This future file must be independently sealed BEFORE awake scoring.
        path = OWN / "awake-prerequisite.json"
        seal = OWN / "awake-prerequisite.sha256"
        if not path.exists() or not seal.exists() or sha(path) != seal.read_text().strip():
            raise ValueError("awake exact-checkpoint manifest/seal missing; source does not authorize sleep")
        manifest = json.loads(path.read_text())
    if manifest["phase"] != phase or set(manifest["seeds"]) != {"0", "1"}:
        raise ValueError("both actual phase/source seeds required")
    for seed, arms in manifest["seeds"].items():
        if set(arms) != {"candidate", "dense"}:
            raise ValueError("candidate and dense checkpoints required")
        for arm, info in arms.items():
            if sha(ROOT / info["checkpoint"]) != info["sha256"]:
                raise ValueError(f"actual {phase} checkpoint changed: s{seed} {arm}")
    return spec, manifest


def runtime():
    global torch, F, N, S, E, A, LatentStopController, FinalStateAdapter, module_hash, assert_parity
    import torch
    from torch.nn import functional as F
    sys.path.insert(0, str(REVIEW))
    import claude_fewex_net as N
    import claude_rsn358a_envs as E
    import real_screen as S
    from sol_spatial_attention_core import load_bundle as A
    from sol_stop_adapter import LatentStopController, FinalStateAdapter, module_hash, assert_parity
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def identity(kind, item):
    if kind.startswith("mazes"):
        from spatial_screen import transform
        return min(S.D.layout_key(transform(item, reflection, turns))
                   for reflection in (False, True) for turns in range(4))
    return json.dumps((item.tokens, item.slot), separators=(",", ":"))


def freeze_inputs(phase, spec):
    # Deterministic historical DEV regeneration for exclusions ONLY.
    seen = set()
    for seed in (0, 1):
        panel, train, replay, _ = S.make_development(seed, 64)
        for kind, group in panel.items():
            seen.update(identity(kind, x) for x in group)
        seen.update(identity("mazes9", x) for x in train)
        for kind, group in replay.items():
            seen.update(identity(kind, x) for x in group)
    rng = random.Random(spec["data_seed"] + (0 if phase == "source" else 1000))
    kinds = ["sums4", "grids5"] + (["mazes9"] if phase == "awake" else [])
    result = {split: {} for split in ("TRAIN", "cal", "noise", "DEV")}
    def group(kind, n):
        rows = []
        for _ in range(100000):
            x = (E.make_sum(rng, 4) if kind == "sums4" else
                 S.D.latin_legend(rng, 5) if kind == "grids5" else
                 S.D.unique_maze(rng, int(kind[5:]), set(), set()))
            key = identity(kind, x)
            if key not in seen:
                seen.add(key); rows.append(x)
            if len(rows) == n:
                return rows
        raise RuntimeError("fresh draw limit reached, do not change RNG")
    for split, n in (("TRAIN", 32), ("cal", 16), ("noise", 16), ("DEV", 24)):
        for kind in kinds:
            result[split][kind] = group(kind, n)
    if phase == "awake":
        result["DEV"]["mazes11"] = group("mazes11", 24)
    raw = {split: {kind: [{"tokens": x.tokens, "slot": x.slot, "target": x.target} for x in rows]
                   for kind, rows in groups.items()} for split, groups in result.items()}
    return result, raw


def correctness(kind, items, prediction):
    if kind == "sums4":
        return torch.tensor([E.check(x, row.reshape_as(torch.tensor(x.tokens)).tolist())
                             for x, row in zip(items, prediction)], dtype=torch.bool)
    _, slots, targets = N.tensors(items)
    return ((prediction == targets.flatten(1)) | ~slots.flatten(1).bool()).all(1)


def collect(core, groups):
    fs, labels, work = [], [], []
    with torch.no_grad():
        for kind, items in groups.items():
            for begin in range(0, len(items), 8):
                rows = items[begin:begin+8]; tokens, slots, _ = N.tensors(rows)
                e, offsets = core.embed(tokens, slots); h = torch.zeros_like(e)
                f, correct = [], []
                for _ in range(48):
                    h = core.step(h, e, *offsets)
                    f.append(h.float().mean(1))
                    lg, _ = core.read(h)
                    correct.append(correctness(kind, rows, lg.argmax(-1)))
                fs.append(torch.stack(f, 1).flatten(0,1))
                ys = torch.stack(correct, 1).long()
                labels.append(ys.flip(1).cummin(1).values.flip(1).flatten().float())
                work.append({"kind": kind, "rows": len(rows), "physical_row_rounds": 48*len(rows),
                             "recurrent_tokens": tokens.shape[1]*tokens.shape[2]})
    return torch.cat(fs), torch.cat(labels), work


def fit(fs, ys, seed):
    torch.manual_seed(seed)
    head = LatentStopController()
    head.mean.copy_(fs.mean(0)); head.scale.copy_(fs.std(0, unbiased=False).clamp_min(.05))
    optimizer = torch.optim.AdamW(head.parameters(), lr=.001, betas=(.9,.95), weight_decay=.1)
    rng = torch.Generator().manual_seed(seed+1)
    for _ in range(256):
        ids = torch.randint(len(fs), (256,), generator=rng)
        loss = F.binary_cross_entropy_with_logits(head(fs[ids, None]), ys[ids])
        optimizer.zero_grad(set_to_none=True); loss.backward(); optimizer.step()
    head.eval().requires_grad_(False)
    return head


def calibrate(head, fs, ys):
    with torch.no_grad():
        # collect concatenates complete item48 trajectories, including geometries.
        probability = head(fs[:, None]).sigmoid().reshape(-1,48)
    targets = ys.reshape(-1,48).bool()
    raw = []
    chosen = None
    for threshold in (.5,.75,.9,.95,.99,1.):
        fire = probability > threshold
        stop = fire.any(1); first = fire.long().argmax(1)
        unsafe = int((stop & ~targets[torch.arange(len(first)), first]).sum())
        raw.append({"threshold": threshold, "unsafe": unsafe, "stops": int(stop.sum())})
        if chosen is None and unsafe == 0:
            chosen = threshold
    return chosen, raw


def score(adapter, kind, items, policy, threshold, cap=48, parity=False):
    # Preserve the published inherited reference independently of fitted head threshold.
    threshold = .5 if policy == "original_guarded" else threshold
    correct, rounds, stops, sizes, work, predictions = [], [], [], [], [], []
    for begin in range(0, len(items), 8):
        rows = items[begin:begin+8]; t,s,_ = N.tensors(rows)
        result = adapter.execute(t,s,policy=policy,cap=cap,threshold=threshold)
        if parity:
            reference = adapter.execute(t,s,policy=policy,cap=cap,threshold=threshold,compact=False)
            assert_parity(result, reference)
        correct.extend(correctness(kind, rows, result.audit.predictions).tolist())
        predictions.extend(result.audit.predictions.tolist())
        rounds.extend(result.audit.rounds.tolist()); stops.extend(result.audit.stopped.tolist())
        sizes.append(result.audit.executed_batch_sizes); work.append(result.audit.work)
    return {"exact": sum(correct), "n": len(items), "correct": correct, "rounds": rounds,
            "stopped": stops, "physical_sizes": sizes, "physical_row_rounds": sum(sum(x) for x in sizes),
            "selected_row_rounds": sum(rounds), "work": work, "predictions": predictions,
            "all_batch_exact_latent_prediction_depth_stop_parity": parity}


def run(phase, spec, manifest, out):
    out.mkdir(parents=True, exist_ok=False)
    runtime()
    start = time.monotonic()
    save(out / "reservation.json", {"phase": phase, "checkpoint_manifest": manifest,
         "spec_sha256": sha(OWN / "READINESS-SPEC-v2.json"), "accepted_stop_ready": False})
    data, raw = freeze_inputs(phase, spec)
    save(out / "frozen-inputs.json", raw)  # BEFORE ALL collection/scoring
    save(out / "input-seal.json", {"sha256": sha(out / "frozen-inputs.json"),
         "label_origin": "symbolic-code-generated", "frozen_before_collection": True})
    adapters, noise = {}, {}
    for seed in (0, 1):
        for arm in ("candidate", "dense"):
            checkpoint = ROOT / manifest["seeds"][str(seed)][arm]["checkpoint"]
            if arm == "candidate":
                core, metadata = A(checkpoint)
                if phase == "awake" and metadata.get("phase") != "awake":
                    raise ValueError("awake bundle has wrong phase")
            else:
                core = N.Net("loop")
                core.load_state_dict(torch.load(checkpoint,map_location="cpu",weights_only=True))
            core.eval().requires_grad_(False); before = module_hash(core)
            fs, ys, collected = collect(core, data["TRAIN"])
            cf, cy, cal_work = collect(core, data["cal"])
            reps = []
            for rep in (0,1):
                head = fit(fs,ys,spec["fit_seed"]+100*seed+rep)
                threshold, calibration = calibrate(head,cf,cy)
                adapter = FinalStateAdapter(core,head,controller_input="latent")
                rows = {kind:score(adapter,kind,items,"learned",threshold) for kind,items in data["noise"].items()}
                reps.append((adapter,threshold,rows))
                tag = f"s{seed}-{arm}-rep{rep}"
                torch.save({"state_dict":head.state_dict(), "width":256,"hidden":32,
                            "threshold":threshold,"core_sha256":before,"phase":phase,
                            "checkpoint_sha256":sha(checkpoint), "training_origin":"symbolic-code-generated",
                            "accepted_stop_ready":False},out/f"{tag}-head.pt")
                save(out/f"{tag}-TRAIN.json", {"calibration":calibration,"threshold":threshold,
                    "noise_raw":rows,"collection":collected,"calibration_collection":cal_work,
                    "fit_updates":256,"fit_batch":256,"fit_seed":spec["fit_seed"]+100*seed+rep,
                    "positive_TRAIN_labels":int(ys.sum()),"TRAIN_labels":len(ys),
                    "core_sha256_before_after":before,"head_sha256":module_hash(head)})
            for kind in data["noise"]:
                first, second = reps[0][2][kind], reps[1][2][kind]
                fraction = abs(first["physical_row_rounds"]-second["physical_row_rounds"])/(first["n"]*48)
                noise[f"s{seed}-{arm}-{kind}"] = {"accuracy_count_noise":abs(first["exact"]-second["exact"]),
                    "work_fraction_noise":fraction,"work_bar":max(.01,2*fraction+1/(first["n"]*48)),
                    "provenance":[f"s{seed}-{arm}-rep0-TRAIN.json",f"s{seed}-{arm}-rep1-TRAIN.json"]}
            if module_hash(core)!=before: raise AssertionError("frozen core changed in TRAIN fitting")
            adapters[(seed,arm)] = reps[0][:2]+(before,)
            if time.monotonic()-start>3600: raise TimeoutError("60min phase cap; no resume")
    save(out/"measured-noise.json",noise)  # BEFORE ANY DEV scoring
    eligibility = {}
    for (seed,arm),(adapter,threshold,before) in adapters.items():
        eligibility[f"s{seed}-{arm}"] = {}
        for kind,items in data["DEV"].items():
            rows={policy:score(adapter,kind,items,policy,threshold,parity=True)
                  for policy in ("learned","guarded","original_guarded")}
            rows.update({f"fixed{depth}":score(adapter,kind,items,"fixed",threshold,cap=depth) for depth in (16,48)})
            best=max(rows[p]["exact"] for p in ("guarded","original_guarded","fixed16","fixed48"))
            guarded=rows["guarded"]["physical_row_rounds"]
            reduction=(guarded-rows["learned"]["physical_row_rounds"])/guarded
            key=f"s{seed}-{arm}-{kind if kind!='mazes11' else 'mazes9'}"
            bar=noise[key]["work_bar"]
            fires_correct=any(x and y for x,y in zip(rows["learned"]["stopped"],rows["learned"]["correct"]))
            eligible=(rows["learned"]["exact"]>=best and fires_correct and reduction>bar)
            if kind.startswith("mazes") and max(rows["fixed16"]["exact"],rows["fixed48"]["exact"])<1:
                eligible=False
            save(out/f"s{seed}-{arm}-{kind}-DEV.json",{"rows":rows,"work_reduction":reduction,
                 "noise_bar":bar,"higher_control_exact":best,"local_gate_eligible":eligible,
                 "accepted_stop_ready":False,"stage_proof_status":"NOT SHOWN"})
            eligibility[f"s{seed}-{arm}"][kind]=eligible
            if module_hash(adapter.program)!=before: raise AssertionError("core changed in DEV")
        if time.monotonic()-start>3600: raise TimeoutError("60min phase cap; no resume/rescore")
    candidate=all(all(eligibility[f"s{s}-candidate"].values()) for s in (0,1))
    save(out/"readiness.json",{"phase":phase,"local_candidate_gate_eligible":candidate,
        "per_seed_arm_kind":eligibility,"accepted_stop_ready":False,"stage_proof_status":"NOT SHOWN",
        "next_dependency":"independent raw+marks recount, then exact awake gate before any sleep" if phase=="source" else
                          "independent awake raw+marks recount and idle/interrupt/retention prerequisites before sleep",
        "reasoner_updates":0,"sleep_updates":0,"torch_version":torch.__version__,"seconds":time.monotonic()-start})


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=("source","awake"),default="source")
    parser.add_argument("--run",action="store_true",help="Mac watcher ONLY")
    parser.add_argument("--out")
    args=parser.parse_args(); spec,manifest=check(args.phase)
    if args.run:
        run(args.phase,spec,manifest,Path(args.out) if args.out else OWN/f"readiness-{args.phase}-v2")
    else:
        print(json.dumps({"phase":args.phase,"exact_checkpoints_present":True,"training_executed":False,
                          "accepted_stop_ready":False,"stage_proof_status":"NOT SHOWN"}))
