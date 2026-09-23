"""Fast CPU contracts for the A3-teacher-delay-v2 evaluator.

Small testing-size panels, a freshly built UNTRAINED bypass-k1 checkpoint, no training, no GPU, no network,
no test split, and nothing written outside a temporary directory.  The historical suite in
artifacts/claude-pairsuite-20260919/ is hashed before and after and must be byte-identical.

    PY -B tests/test_premonition_teacher_delay_eval.py
"""
from dataclasses import asdict, replace as dc_replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_teacher_delay_eval as E  # noqa: E402

SIZE = 8                      # testing panel size (the CLI default stays at the registered 2048/1024/512)
EVAL_SEEDS = {0: 770_001, 1: 770_002}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guard_paths():
    """The historical pair-suite artifacts, wherever this checkout keeps them (never written by this test)."""
    candidates = [E.PS.OUT]
    extra = os.environ.get("PREMONITION_PAIRSUITE_GUARD")
    if extra:
        candidates.append(Path(extra))
    candidates.append(Path("/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts")
                      / "claude-pairsuite-20260919")
    for folder in candidates:
        if folder.exists():
            return folder, {p.name: sha(p) for p in sorted(folder.iterdir()) if p.is_file()}
    return None, {}


def write_plan(folder: Path) -> Path:
    plan = {"experiment_id": E.EXPERIMENT_ID, "pairs": []}
    for pair_id in (0, 1):
        plan["pairs"].append({
            "pair_id": pair_id, "init_seed": 900 + pair_id, "data_seed": 800 + pair_id,
            "eval_seed": EVAL_SEEDS[pair_id],
            "jobs": {"control": {"job_id": f"p{pair_id:03d}-control", "arm": "control"},
                     "delayed": {"job_id": f"p{pair_id:03d}-delayed", "arm": "delayed"}}})
    path = folder / "plan.json"
    path.write_text(json.dumps(plan, indent=1))
    return path


def write_job(plan_path: Path, plan: dict, pair_id: int, arm: str, *, status: str = "complete"):
    """An untrained bypass-k1 model saved in the gpu_port blob format, with this experiment's extra keys."""
    import torch
    pair = E.find_pair(plan, pair_id)
    job_id = pair["jobs"][arm]["job_id"]
    folder = E.job_dir(plan_path, job_id)
    folder.mkdir(parents=True, exist_ok=True)
    model = E.R.build("bypass-k1", int(pair["init_seed"]))
    blob = {"state_dict": model.state_dict(), "config": asdict(model.config), "arm": "bypass-k1",
            "identity": {"variant": model.config.variant, "purpose": "untrained test fixture"},
            "seed": int(pair["init_seed"]), "model_class": type(model).__name__,
            "experiment_id": E.EXPERIMENT_ID, "job_id": job_id, "pair_id": pair_id, "arm_name": arm,
            "init_seed": int(pair["init_seed"]), "data_seed": int(pair["data_seed"])}
    torch.save(blob, folder / "model.pt")
    record = {"job_id": job_id, "pair_id": pair_id, "arm": arm, "status": status,
              "ckpt_sha256": sha(folder / "model.pt")}
    if status != "complete":
        record["reason"] = "time stop before the FLOP budget (fixture)"
    (folder / "result.json").write_text(json.dumps(record, indent=1))
    return job_id, folder, model


def outputs_of(model, dataset, spec):
    """The model's generated answers for a native panel, as lists of token ids (side a)."""
    import torch
    out = []
    with torch.no_grad():
        for chunk in dataset["chunks"]:
            batch = E.H._strip_labels(chunk["a"])
            res = E.H.run_condition(model, batch, E.H.FieldView(batch, spec), E.CONDITION,
                                    [m["key_a"] for m in chunk["meta"]])
            out.extend([(res["tokens"][q, :int(res["lengths"][q])].tolist(), res["cards"][q].tolist())
                        for q in range(len(chunk["meta"]))])
    return out


def main() -> int:
    E.L.bootstrap()
    import torch
    torch.set_num_threads(2)
    checks = 0

    def check(label, ok):
        nonlocal checks
        assert bool(ok), label
        checks += 1
        print("PASS " + label, flush=True)

    guard_dir, guard_before = guard_paths()
    print(f"historical suite guard: {guard_dir if guard_dir else 'not present in this checkout'}", flush=True)
    spec = E.L.spec()
    tmp = Path(tempfile.mkdtemp(prefix="teacher-delay-eval-test-")).resolve()
    try:
        run_a, run_b = tmp / "runA", tmp / "runB"
        run_a.mkdir()
        run_b.mkdir()
        plan_a = write_plan(run_a)
        plan_b = write_plan(run_b)
        plan = json.loads(plan_a.read_text())
        sizes = {cell: SIZE for cell in E.PANELS}

        # ---------------------------------------------------------------- panels: freshness, pairing, refusal
        man0 = E.generate_panels(plan_a, 0, sizes=sizes, quiet=True)
        man1 = E.generate_panels(plan_a, 1, sizes=sizes, quiet=True)
        check("panels for two different pairs differ in every cell",
              all(man0["panels"][c]["sha256"] != man1["panels"][c]["sha256"] for c in E.PANELS))
        check("a pair's panels cover the six cells and the 512-world READS panel",
              tuple(man0["panels"]) == E.PANELS and E.FULL_N == {"c1": 2048, "c2": 2048, "c3": 2048,
                                                                 "c4": 1024, "c5": 1024, "c6": 1024,
                                                                 "reads": 512})
        help_text = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "premonition_teacher_delay_eval.py"),
             "panels", "--help"], capture_output=True, text=True).stdout
        check("the testing size parameter is hidden and the CLI default is the registered full size",
              "--testing-panel-size" not in help_text
              and inspect.signature(E.generate_panels).parameters["sizes"].default is None
              and man0["full_sizes"] == E.FULL_N
              and all(man0["panels"][c]["n"] == SIZE for c in E.PANELS) and not man0["full_size"])
        man0_again = E.generate_panels(plan_b, 0, sizes=sizes, quiet=True)
        check("panels regenerated from the same eval_seed are byte-identical",
              all(sha(E.panels_dir(plan_a, 0) / f"{c}.pt") == sha(E.panels_dir(plan_b, 0) / f"{c}.pt")
                  for c in E.PANELS)
              and man0["panel_content_sha256"] == man0_again["panel_content_sha256"])
        refused = False
        try:
            E.generate_panels(plan_a, 0, sizes=sizes, quiet=True)
        except SystemExit as error:
            refused = "refusing to overwrite" in str(error)
        check("panel generation refuses to overwrite an existing panel directory", refused)
        check("a panel manifest hashes every file and records the shared arms and the seed",
              all(sha(E.panels_dir(plan_a, 0) / f"{c}.pt") == man0["panels"][c]["sha256"] for c in E.PANELS)
              and man0["shared_by"] == ["control", "delayed"] and man0["eval_seed"] == EVAL_SEEDS[0]
              and man0["selector_policy"] == "not_applicable")

        # -------------------------------------------------------------------------- the two arms of one pair
        job_c, dir_c, model = write_job(plan_a, plan, 0, "control")
        job_d, dir_d, _ = write_job(plan_a, plan, 0, "delayed")
        job_p1, _, _ = write_job(plan_a, plan, 1, "control")
        job_bad, dir_bad, _ = write_job(plan_a, plan, 1, "delayed", status="incomplete")

        before_print = E.P.fingerprint(model)
        eval_c = E.score_job(plan_a, job_c, quiet=True)
        eval_d = E.score_job(plan_a, job_d, quiet=True)
        check("both arms of a pair are scored on the identical panel files",
              eval_c["panels"]["manifest_sha256"] == eval_d["panels"]["manifest_sha256"]
              and eval_c["panels"]["files"] == eval_d["panels"]["files"]
              and eval_c["panels"]["content_sha256"] == eval_d["panels"]["content_sha256"]
              == man0["panel_content_sha256"]
              and eval_c["panels"]["dir"] == eval_d["panels"]["dir"] == str(E.panels_dir(plan_a, 0)))
        check("a different pair is scored on its own panels",
              E.score_job(plan_a, job_p1, quiet=True)["panels"]["content_sha256"]
              != eval_c["panels"]["content_sha256"])
        check("the result carries one unit per world for every panel, in a shared order",
              all(len(eval_c["per_unit"][c]) == SIZE == len(eval_d["per_unit"][c]) for c in E.PANELS)
              and eval_c["status"] == "complete" and eval_c["selector_policy"] == "not_applicable"
              and eval_c["arm"] == "control" and eval_d["arm"] == "delayed" and eval_c["pair_id"] == 0)
        check("counts equal the sum of the per-unit vector on every panel",
              all(eval_c["counts"][c] == sum(eval_c["per_unit"][c]) for c in E.PANELS)
              and all(v in (0, 1) for c in E.PANELS for v in eval_c["per_unit"][c]))

        # ------------------------------------------------------------------------------- integrity records
        integrity = eval_c["integrity"]
        check("scoring leaves every weight and buffer unchanged",
              integrity["weights_unchanged"] and integrity["weights_fingerprint"] == before_print
              == E.P.fingerprint(model))
        check("world/episode isolation: a world scored alone equals the same world scored in its chunk",
              integrity["world_isolation"]["pass"] and integrity["world_isolation"]["worlds"] > 0
              and integrity["world_isolation"]["identical"] == integrity["world_isolation"]["worlds"])
        check("the label-perturbation check passes and is recorded",
              integrity["label_perturbation_identical"] and integrity["label_perturbation"]["pass"])
        check("native policy: condition U reproduces the frozen own_fixed(..., loops=4) exactly",
              integrity["own_fixed_parity"]["pass"]
              and integrity["own_fixed_parity"]["answers_equal"] == integrity["own_fixed_parity"]["questions"]
              and integrity["own_fixed_parity"]["fetched_lines_equal"]
              == integrity["own_fixed_parity"]["questions"])
        check("READS reproduces the frozen gold_read(..., loops=2) on fresh worlds",
              integrity["reads_parity_gold_read_K2"]["pass"]
              and integrity["reads_parity_gold_read_K2"]["units"] == SIZE)
        check("the integrity record names the checkpoint, panels, sources and execution config",
              integrity["checkpoint_sha256"] == sha(dir_c / "model.pt")
              and integrity["panels_manifest_sha256"] == sha(E.panels_dir(plan_a, 0) / "manifest.json")
              and "scripts/premonition_teacher_delay_eval.py" in integrity["evaluator_source_hashes"]
              and "scripts/premonition_first_card_probe.py" in integrity["loader_source_hashes"]
              and len(integrity["execution_config_sha256"]) == 64 and not integrity["panels_full_size"])

        # ------------------------------------------------------------------- native inference policy itself
        c1 = E.load_panel("c1", E.panels_dir(plan_a, 0), man0)
        with torch.no_grad():
            batch = E.H._strip_labels(c1["chunks"][0]["a"])
            res = E.H.run_condition(model, batch, E.H.FieldView(batch, spec), E.CONDITION,
                                    [m["key_a"] for m in c1["chunks"][0]["meta"]])
        check("the scoring path uses 4 fixed loops, the ASK gate and at most 3 requests",
              E.LOOPS == E.PS.LOOPS == 4 and E.REQUESTS == E.PS.REQUESTS == 3 and E.CONDITION == "U"
              and res["cards"].shape[1] == 3 and res["ask"].shape[1] == 3
              and bool(((res["cards"] < 0) | res["ask"]).all()))

        # ---------------------------------------------------------- labels are stripped before inference
        produced = outputs_of(model, c1, spec)
        scored = E.score_native_panel(model, c1, spec, diagnostics=False)
        relabelled = dict(c1, chunks=[])
        for chunk in c1["chunks"]:
            noisy = dc_replace(chunk["a"], answer=torch.full_like(chunk["a"].answer, 7),
                               gold_lines=torch.zeros_like(chunk["a"].gold_lines),
                               depth=torch.full_like(chunk["a"].depth, 3))
            meta = [dict(m) for m in chunk["meta"]]
            relabelled["chunks"].append({"a": noisy, "meta": meta})
        for i, (tokens, _cards) in enumerate(produced):        # the labels now say the model is right
            relabelled["chunks"][i // E.WORLDS_PER_CHUNK]["meta"][i % E.WORLDS_PER_CHUNK]["answer_a"] = tokens
        rescored = E.score_native_panel(model, relabelled, spec, diagnostics=False)
        check("perturbing the answer labels changes the score and nothing else",
              rescored["count"] == c1["n"] and rescored["count"] != scored["count"]
              and outputs_of(model, relabelled, spec) == produced)

        # -------------------------------------------------------------------------- twin units and cutoffs
        check("a twin pair counts only when both twins are correct",
              E.combine_units([1, 1, 0, 1], [1, 0, 1, 1], [True, True, True, True]) == [1, 0, 0, 1])
        check("the output-invariance cell also requires identical twin outputs",
              E.combine_units([1, 1, 1], [1, 1, 1], [True, False, True], invariant=True) == [1, 0, 1]
              and E.combine_units([1, 1, 1], [1, 1, 1], [True, False, True]) == [1, 1, 1])
        check("c6 is the only cell scored with the output-invariance rule",
              E.PANEL_CONFIG["c6"]["invariant"] and not any(E.PANEL_CONFIG[c]["invariant"]
                                                            for c in E.PANELS if c != "c6"))

        def flags(c1_count, c2_count=2048, c3_count=2048, others=1024):
            counts = {"c1": c1_count, "c2": c2_count, "c3": c3_count,
                      "c4": others, "c5": others, "c6": others}
            per_unit = {c: [1] * counts[c] + [0] * (E.FULL_N[c] - counts[c]) for c in E.CELLS}
            return E.gate_flags({c: sum(per_unit[c]) for c in E.CELLS})

        check("L_train needs c1 >= 1969 AND c2 >= 1969",
              flags(1969, 1969)["L_train"] and not flags(1968, 1969)["L_train"]
              and not flags(1969, 1968)["L_train"])
        check("G_pair needs all six published cutoffs",
              flags(1969, 1969, 1876, 945)["G_pair"] and not flags(1969, 1969, 1875, 945)["G_pair"]
              and not flags(1969, 1969, 1876, 944)["G_pair"] and E.CUTOFF == {"c1": 1969, "c2": 1969,
                                                                              "c3": 1876, "c4": 945,
                                                                              "c5": 945, "c6": 945})
        check("the fresh stuck flag is c1 < 1536/2048",
              flags(1535)["c1_stuck"] and not flags(1536)["c1_stuck"] and E.STUCK_CUTOFF == 1536)
        check("a G_pair pass does not require L_train to be read from anywhere else",
              flags(1969, 1969, 1876, 945)["L_train"] and not flags(1968, 1969, 1876, 945)["G_pair"])

        # --------------------------------------------------------------------------------- diagnostics
        diag = eval_c["diagnostics"]["c3"]
        check("c3 diagnostics report the first-request classes, asker_same_rel and the first-LINK rate",
              diag["questions"] == SIZE and "first_request_asker_same_rel" in diag
              and "first_link_card_rate_all_questions" in diag and "by_request" in diag
              and set(diag["by_request"]) == {"request1", "request2", "request3"}
              and sum(diag["by_request"]["request1"]["classes"].values()) == SIZE)

        # ------------------------------------------------------------------------------------ reuse key
        eval_path = dir_c / "eval.json"
        before_bytes = eval_path.read_bytes()
        again = E.score_job(plan_a, job_c, quiet=True)
        check("an identical reuse key allows reuse and rewrites nothing",
              again.get("reused") and again["counts"] == eval_c["counts"]
              and eval_path.read_bytes() == before_bytes)
        key = eval_c["reuse_key"]
        check("the reuse key is 09's complete tuple",
              set(key) == {"checkpoint_path", "checkpoint_sha256", "evaluation_manifest_sha256",
                           "evaluator_source_hashes", "loader_source_hashes", "selector_policy",
                           "execution_config_sha256"})
        for field in sorted(key):
            spoiled = dict(key)
            spoiled[field] = "different" if isinstance(key[field], str) else {"different": 1}
            allowed, _why = E.reuse_allowed(eval_c, spoiled)
            check(f"a changed reuse-key field forbids reuse ({field})", not allowed)
        check("reuse also requires a complete status and a passing integrity record",
              not E.reuse_allowed(dict(eval_c, status="failed"), key)[0]
              and not E.reuse_allowed(dict(eval_c, integrity=dict(eval_c["integrity"], all_pass=False)),
                                      key)[0]
              and E.reuse_allowed(eval_c, key)[0])
        spoiled_file = json.loads(before_bytes)
        spoiled_file["reuse_key"]["execution_config_sha256"] = "0" * 64
        eval_path.write_text(json.dumps(spoiled_file, indent=1))
        mismatched = eval_path.read_bytes()
        refused = False
        try:
            E.score_job(plan_a, job_c, quiet=True)
        except SystemExit as error:
            refused = "refusing to overwrite" in str(error)
        check("a mismatched reuse key refuses to overwrite the existing evaluation",
              refused and eval_path.read_bytes() == mismatched)
        eval_path.write_bytes(before_bytes)

        # ------------------------------------------------------------------------------- incomplete jobs
        bad = E.score_job(plan_a, job_bad, quiet=True)
        check("an incomplete training job is scored 'failed' with no fabricated counts",
              bad["status"] == "failed" and "counts" not in bad and "per_unit" not in bad
              and "not 'complete'" in bad["reason"] and bad["n"]["c1"] == SIZE
              and "counts" not in json.loads((dir_bad / "eval.json").read_text()))
        (dir_bad / "eval.json").unlink()
        (dir_bad / "model.pt").unlink()
        (dir_bad / "result.json").write_text(json.dumps({"job_id": job_bad, "status": "complete"}))
        missing = E.score_job(plan_a, job_bad, quiet=True)
        check("a missing checkpoint is a failure, not a zero score",
              missing["status"] == "failed" and "model.pt" in missing["reason"] and "counts" not in missing)

        # ------------------------------------------------------------------ nothing historical was touched
        guard_after, guard_now = guard_paths()
        check("the historical pair-suite artifacts are byte-identical before and after, and none was created",
              guard_after == guard_dir and guard_now == guard_before
              and (guard_dir is not None or not E.PS.OUT.exists()))
        check("every file this test created lives under its temporary plan directories",
              all(Path(p).resolve().is_relative_to(tmp) for p in
                  [eval_path, E.panels_dir(plan_a, 0), E.panels_dir(plan_b, 0), dir_d]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"ALL {checks} CHECKS PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
