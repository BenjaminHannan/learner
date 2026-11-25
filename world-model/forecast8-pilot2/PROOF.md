# Forecast 8 Rel-PER Second-Pilot Proof

## Scope and stop point

- Built and pinned only. NO pilot/real-data training, MPS run, scored Rank 8 run, or real-data model evaluation was launched.
- CPU tests used synthetic data only. They include pilot 1's tiny synthetic training-loop checks and one tiny synthetic checkpoint/metadata check.
- No dev or sealed data path is used. No lock was taken or modified. No secret, SSH-key, Keychain, auth, environment, or private data was read.
- `forecast8-pilot/` and `forecast7/` are unchanged. M1 writes are under `forecast8-pilot2/`; M3 writes are under `~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p2/`.
- Pilot 1's `pilot_data/` is reused by path: M1 `forecast8-pilot2/pilot_data -> ../forecast8-pilot/pilot_data`; M3 `wm8p2/pilot_data -> ../wm8p/pilot_data`.
- M3 transfer used `scp -p` for regular files only, followed by creation of the relative `pilot_data` symlink. No data file was copied.

## Plan pin recorded before any run

Command:

```bash
shasum -a 256 PILOT2-PLAN.md
```

Output:

```text
7ef97f2f9974e5c085b0ec05815ed817375dd26ebe69e1c6a019f5e30cee3f7d  PILOT2-PLAN.md
```

The P1/P2/P3 block and exact P2 computation in `PILOT2-PLAN.md` are copied verbatim from pilot 1. The plan also contains the design's four-part falsifier, numerical limits, decision rule, and the note `a miss = Rel-PER 2 of 3`.

## Diff vs pilot 1

Command, run from `forecast8-pilot2/`:

```bash
diff -ruN --exclude=pilot_data --exclude=PROOF.md --exclude=PILOT-PLAN.md --exclude=train_v7.diff ../forecast8-pilot .
```

Pilot 1's superseded `PILOT-PLAN.md` and Rank-7 `train_v7.diff` are intentionally not copied into pilot 2. `diff` returned `1` for differences; the guarded wrapper returned `0`.

````diff
diff -ruN --exclude=pilot_data --exclude=PROOF.md --exclude=PILOT-PLAN.md --exclude=train_v7.diff ../forecast8-pilot/PILOT2-PLAN.md ./PILOT2-PLAN.md
--- ../forecast8-pilot/PILOT2-PLAN.md	1969-12-31 19:00:00
+++ ./PILOT2-PLAN.md	2026-11-25 05:32:36
@@ -0,0 +1,74 @@
+# Forecast 8 Rel-PER Second-Pilot Plan
+
+Status: PINNED BEFORE ANY PILOT-2 TRAINING. This pilot is UNSCORED. No Rank 8 training is authorized by this file.
+
+## Fixed second-pilot protocol
+
+- Outcome: decide whether one domain-general sampler adjustment can keep Rel-PER's rare-event gains while restoring the wall gate.
+- Single adjustment: change Rel-PER from 50% uniform / 50% prioritised to 75% uniform / 25% prioritised. Everything else remains exactly as pilot 1.
+- Reuse pilot 1's `pilot_data/` by path. The driver accepts no data-path override and verifies both NPZ SHA-256 values before every launch.
+- Train file: `train_worlds_3000_3071.npz`, worlds `3000..3071`, SHA-256 `e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f`.
+- Eval file: `eval_worlds_3072_3079.npz`, worlds `3072..3079`, SHA-256 `545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c`.
+- No dev or sealed data is used. The held-out 8 pilot worlds never enter training, sampler priorities, action means, event-labeller fitting, optimizer, or scorer baselines.
+- Seeds `7` and `8` only. Four serial runs in balanced order: `s7_uniform`, `s7_relper_u75`, `s8_relper_u75`, `s8_uniform`, under a fresh `runs/` root.
+- Arms are `uniform` and `relper_u75`. The driver maps `relper_u75` to trainer `--sampler relper --uniform-mix 0.75`. Uniform runs omit `--uniform-mix`, retaining pilot 1's default `0.5` behaviour and command path.
+- Trainer default `--uniform-mix 0.5` reproduces pilot-1 Rel-PER probabilities exactly. Pilot 2 uses `p_j = 0.75/N + 0.25 * (r_j + 1e-6)^0.7 / sum_k((r_k + 1e-6)^0.7)`.
+- Keep the existing action-normalised priority, cap, exponent, epsilon, EMA, refresh cadence, replacement sampling, unweighted loss, architecture, optimizer, schedule, data, scorer, rollout, and event labeller unchanged. The event labeller remains diagnostic/logging-only and never affects `p_j`.
+- Rank 7 architecture/config: `R7conv`, `n_history=2`, two-frame input, `reencode`, batch `64`, AdamW `lr=3e-4`, `wd=1e-4`, `w_lat=0.05`, grad clip `1.0`, warmup+cosine, unweighted loss.
+- Budget: `3000` steps per run and `--max-minutes 6.5`. An incomplete run fails loudly and is not saved or scored.
+- Pinned `model_v7.py`, `scorer.py`, and `withlock.sh` hashes remain unchanged. Every M3 MPS run goes through the existing `withlock.sh`; the driver never reads or manipulates the lock directly.
+- The P1/P2/P3 gate and summary logic are unchanged from pilot 1. In the verbatim block below, pilot 1's label `relper` means this pilot's `relper_u75` arm.
+
+## Pre-registered pilot marks
+
+P1: relper action-5 std ratio >= 0.30 on BOTH seeds (k1, under the ec44cdca std computation on the pilot eval split).
+
+P2: wake vs stay-asleep separation: relper's mean predicted brightness change on 8→9 wake windows exceeds stay-asleep windows by >= 3x the uniform arm's gap, on both seeds (define it exactly, data-derived).
+
+P3: no regression: relper k1 E/B <= uniform + 0.005, k3 <= uniform + 0.008, wall mean_err <= uniform + 0.005, on both seeds.
+
+All three must hold. Any miss means NO scored Rank 8, and the conv line parks at 2/3 (recorded as unscored).
+
+Exact P2 computation:
+
+- `dBright_i = mean((pred_k1_i - x_t_i)[:, :12])` over terrain rows, columns, and RGB.
+- `G_arm = mean(dBright_i | wake_e89) - mean(dBright_i | sleep_stay)` on the fixed 8-world eval split.
+- P2 passes for a seed iff both groups are nonempty and `G_relper >= 3 * G_uniform`.
+
+P1 reads `k1.std_ratio_by_action["5"].ratio`. P3 reads `k1.E_over_B`, `k3.E_over_B`, and `k1.block_open.model.mean_err`.
+
+`diag_non_wake_interactions.asleep_all.R2` is reported as `diag_aslR2` for each arm and seed as a pre-registered DIAGNOSTIC only, never as a gate.
+
+## Numerical second-pilot limits
+
+| Seed | P1 action-5 std | P2 wake gap | P3 k1 E/B max | P3 k3 E/B max | P3 wall max |
+|---|---:|---:|---:|---:|---:|
+| 7 | `>= 0.30` | `>= 0.003285568` | `<= 0.302498862` | `<= 0.416700799` | `<= 0.065448336` |
+| 8 | `>= 0.30` | `>= 0.002440902` | `<= 0.295619094` | `<= 0.407272043` | `<= 0.054507881` |
+
+## Second-pilot falsifier
+
+**Any** of the following on **either** seed proves the adjustment wrong:
+
+1. P1 is below `0.30`.
+2. P2 is below `3 * G_uniform`, or either P2 group is empty.
+3. P3 k1, k3, or wall exceeds its same-seed allowance.
+4. A run is incomplete, invalid, leaks held-out worlds into training, or touches dev/sealed data.
+
+Decision rule:
+
+- Any miss → **NO scored Rank 8**.
+- A second pilot miss records **Rel-PER 2 of 3** and parks this sampler line; it does not spend the scored last strike.
+- All three marks on both seeds → eligible for the lead's separate scored-Rank-8 decision, not an automatic scored run.
+
+a miss = Rel-PER 2 of 3
+
+## Exact launch
+
+Lead only, on M3:
+
+```bash
+~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p2/pilot_driver.py
+```
+
+The driver writes `runs/pilot_summary.json`. `GO_SCORED_RANK8` requires P1, P2, and P3 on both seeds; otherwise it exits nonzero with `NO_SCORED_RANK8`. A pass only establishes eligibility for the lead's separate scored-Rank-8 decision.
diff -ruN --exclude=pilot_data --exclude=PROOF.md --exclude=PILOT-PLAN.md --exclude=train_v7.diff ../forecast8-pilot/pilot_driver.py ./pilot_driver.py
--- ../forecast8-pilot/pilot_driver.py	2026-11-25 04:26:27
+++ ./pilot_driver.py	2026-11-25 05:30:41
@@ -11,17 +11,20 @@
 import scorer
 
 HERE = Path(__file__).resolve().parent
-TRAIN_PATH = HERE.parent / "wm5" / "data" / "train_dn.npz"
-TRAIN_SHA256 = "4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6"
+TRAIN_FILE = "train_worlds_3000_3071.npz"
+EVAL_FILE = "eval_worlds_3072_3079.npz"
+TRAIN_SHA256 = "e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f"
+EVAL_SHA256 = "545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c"
 TRAIN_WORLDS = tuple(range(3000, 3072))
 EVAL_WORLDS = tuple(range(3072, 3080))
 PYTHON = Path.home() / "learner-ops" / "m3-torch" / ".venv" / "bin" / "python"
 STEPS = 3000
 MAX_MINUTES = 6.5
+RELPER_UNIFORM_MIX = 0.75
 RUN_SPECS = (
     (7, "uniform"),
-    (7, "relper"),
-    (8, "relper"),
+    (7, "relper_u75"),
+    (8, "relper_u75"),
     (8, "uniform"),
 )
 
@@ -69,55 +72,45 @@
     }
 
 
+def verify_pinned_data(train_path: Path, eval_path: Path) -> tuple[str, str]:
+    train_sha = sha256_file(train_path)
+    eval_sha = sha256_file(eval_path)
+    if train_sha != TRAIN_SHA256:
+        raise ValueError(f"pinned pilot train SHA {train_sha} != {TRAIN_SHA256}")
+    if eval_sha != EVAL_SHA256:
+        raise ValueError(f"pinned pilot eval SHA {eval_sha} != {EVAL_SHA256}")
+    return train_sha, eval_sha
+
+
 def prepare_data(data_dir: Path) -> tuple[Path, Path, dict]:
-    source = TRAIN_PATH.resolve(strict=True)
-    source_sha = sha256_file(source)
-    if source_sha != TRAIN_SHA256:
-        raise ValueError(f"pinned train source SHA {source_sha} != {TRAIN_SHA256}")
-    with np.load(source, allow_pickle=False) as loaded:
-        full = {key: loaded[key] for key in loaded.files}
-    if np.unique(full["world_id"]).astype(int).tolist() != list(TRAIN_WORLDS + EVAL_WORLDS):
-        raise ValueError("pinned train source world set changed")
-    train = subset_by_worlds(full, TRAIN_WORLDS)
-    evaluation = subset_by_worlds(full, EVAL_WORLDS)
+    train_path = (data_dir / TRAIN_FILE).resolve(strict=True)
+    eval_path = (data_dir / EVAL_FILE).resolve(strict=True)
+    train_sha, eval_sha = verify_pinned_data(train_path, eval_path)
+    with np.load(train_path, allow_pickle=False) as loaded:
+        train = {key: loaded[key] for key in loaded.files}
+    with np.load(eval_path, allow_pickle=False) as loaded:
+        evaluation = {key: loaded[key] for key in loaded.files}
     if set(np.unique(train["world_id"])) & set(np.unique(evaluation["world_id"])):
         raise ValueError("pilot train/eval world overlap")
-    data_dir.mkdir(parents=True, exist_ok=True)
-    train_path = data_dir / "train_worlds_3000_3071.npz"
-    eval_path = data_dir / "eval_worlds_3072_3079.npz"
-    manifest_path = data_dir / "manifest.json"
-    for path, split, worlds in (
-        (train_path, train, TRAIN_WORLDS),
-        (eval_path, evaluation, EVAL_WORLDS),
-    ):
-        if path.exists():
-            with np.load(path, allow_pickle=False) as existing:
-                existing_split = {key: existing[key] for key in existing.files}
-            validate_split(existing_split, worlds)
-        else:
-            np.savez(path, **split)
     manifest = {
-        "source_path": str(source),
-        "source_sha256": source_sha,
+        "train_path": str(train_path),
+        "eval_path": str(eval_path),
         "train": validate_split(train, TRAIN_WORLDS),
         "eval": validate_split(evaluation, EVAL_WORLDS),
-        "train_file_sha256": sha256_file(train_path),
-        "eval_file_sha256": sha256_file(eval_path),
+        "train_file_sha256": train_sha,
+        "eval_file_sha256": eval_sha,
         "steps": STEPS,
         "max_minutes": MAX_MINUTES,
         "expected_total_minutes": [24.0, 27.0],
     }
-    if manifest_path.exists():
-        old = json.loads(manifest_path.read_text())
-        if old.get("source_sha256") != source_sha or old.get("train_file_sha256") != manifest["train_file_sha256"]:
-            raise ValueError("existing pilot data manifest does not match pinned source")
-    else:
-        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
     return train_path, eval_path, manifest
 
 
 def build_run_command(seed: int, sampler: str, train_path: Path, eval_path: Path, out_dir: Path, log_path: Path) -> list[str]:
-    return [
+    if sampler not in ("uniform", "relper_u75"):
+        raise ValueError(f"unknown pilot-2 arm {sampler!r}")
+    trainer_sampler = "uniform" if sampler == "uniform" else "relper"
+    command = [
         str(HERE / "withlock.sh"),
         str(log_path),
         str(PYTHON),
         "-B",
         "-u",
         str(HERE / "train_v7.py"),
         "--size", "R7conv",
         "--n-history", "2",
         "--rollout", "reencode",
-        "--sampler", sampler,
+        "--sampler", trainer_sampler,
         "--device", "mps",
         "--steps", str(STEPS),
         "--batch", "64",
         "--lr", "3e-4",
         "--wd", "1e-4",
         "--w-lat", "0.05",
         "--seed", str(seed),
         "--max-minutes", str(MAX_MINUTES),
         "--save-forecasts",
         "--train-data", str(train_path),
         "--eval-data", str(eval_path),
         "--out", str(out_dir),
     ]
+    if trainer_sampler == "relper":
+        command.extend(["--uniform-mix", str(RELPER_UNIFORM_MIX)])
+    return command
 
 
 def load_run_score(out_dir: Path) -> dict:
@@ -188,7 +184,7 @@
     per_seed = {}
     for seed in (7, 8):
         uniform = load_run_score(run_root / f"s{seed}_uniform")
-        relper = load_run_score(run_root / f"s{seed}_relper")
+        relper = load_run_score(run_root / f"s{seed}_relper_u75")
         per_seed[str(seed)] = paired_metrics(uniform, relper)
     p1 = all(values["P1"] for values in per_seed.values())
     p2 = all(values["P2"] for values in per_seed.values())
@@ -237,6 +233,7 @@
         if (out_dir / "model.pt").exists():
             raise ValueError(f"refusing to overwrite existing pilot run {out_dir}")
         out_dir.mkdir(parents=True, exist_ok=True)
+        verify_pinned_data(train_path, eval_path)
         command = build_run_command(seed, sampler, train_path, eval_path, out_dir, log_path)
         print(f"[PILOT_RUN] {name}", flush=True)
         completed = subprocess.run(command, cwd=HERE, check=False)
diff -ruN --exclude=pilot_data --exclude=PROOF.md --exclude=PILOT-PLAN.md --exclude=train_v7.diff ../forecast8-pilot/test_pilot.py ./test_pilot.py
--- ../forecast8-pilot/test_pilot.py	2026-11-25 04:34:04
+++ ./test_pilot.py	2026-11-25 05:35:14
@@ -30,19 +30,36 @@
     return module
 
 
+def load_pilot1():
+    candidates = (
+        HERE.parent / "forecast8-pilot" / "train_v7.py",
+        HERE.parent / "wm8p" / "train_v7.py",
+    )
+    source = next(path for path in candidates if path.exists())
+    spec = importlib.util.spec_from_file_location("pilot1_train_for_equivalence", source)
+    module = importlib.util.module_from_spec(spec)
+    spec.loader.exec_module(module)
+    return module
+
+
 def test_1_pins_and_default_sampler():
     assert verify_pinned_scorer(HERE / "scorer.py") == "ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912"
     assert pilot.sha256_file(str(HERE / "model_v7.py")) == "c87f4110057bddaf4610c423e64c13dbe22f882aa9ea8dd53e4f3b57d7e67006"
     assert pilot.sha256_file(str(HERE / "withlock.sh")) == "77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa"
     tree = ast.parse((HERE / "train_v7.py").read_text())
     found = False
+    uniform_mix_found = False
     for node in ast.walk(tree):
         if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
             if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "--sampler":
                 defaults = {kw.arg: kw.value for kw in node.keywords}
                 assert isinstance(defaults["default"], ast.Constant) and defaults["default"].value == "uniform"
                 found = True
-    assert found
+            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "--uniform-mix":
+                defaults = {kw.arg: kw.value for kw in node.keywords}
+                assert isinstance(defaults["default"], ast.Constant) and defaults["default"].value == 0.5
+                uniform_mix_found = True
+    assert found and uniform_mix_found
 
 
 def test_2_uniform_byte_identical_20_steps():
@@ -86,18 +103,22 @@
 def test_3_relper_formula_distribution_and_determinism():
     copy_mse = np.array([0.0, 0.001, 0.01, 0.1, 0.002, 0.02], dtype=np.float64)
     actions = np.array([0, 0, 0, 1, 1, 1], dtype=np.int64)
-    sampler = pilot.RelPERSampler(copy_mse, actions, seed=7)
+    sampler = pilot.RelPERSampler(copy_mse, actions, seed=7, uniform_mix=0.5)
+    pilot1_sampler = load_pilot1().RelPERSampler(copy_mse, actions, seed=7)
     means = np.array([copy_mse[actions == a].mean() for a in actions])
     expected_r = np.minimum(copy_mse / (means + 1e-4), 20.0)
     weights = (expected_r + 1e-6) ** 0.7
     expected_p = 0.5 * (1.0 / len(copy_mse)) + 0.5 * weights / weights.sum()
-    np.testing.assert_allclose(sampler.relative_priority(), expected_r, rtol=0.0, atol=1e-15)
-    np.testing.assert_allclose(sampler.probabilities, expected_p, rtol=0.0, atol=1e-15)
+    np.testing.assert_array_equal(sampler.relative_priority(), expected_r)
+    np.testing.assert_array_equal(sampler.probabilities, expected_p)
+    np.testing.assert_array_equal(sampler.probabilities, pilot1_sampler.probabilities)
     assert np.isfinite(sampler.probabilities).all() and (sampler.probabilities >= 0.0).all()
     assert abs(float(sampler.probabilities.sum()) - 1.0) < 1e-12
     same = pilot.RelPERSampler(copy_mse, actions, seed=7)
     for _ in range(10):
-        assert np.array_equal(sampler.sample(32), same.sample(32))
+        draws = sampler.sample(32)
+        assert np.array_equal(draws, same.sample(32))
+        assert np.array_equal(draws, pilot1_sampler.sample(32))
     draws = sampler.sample(128)
     assert len(np.unique(draws)) < len(draws)
     old_error = sampler.ema_error.copy()
@@ -165,15 +186,26 @@
     assert "sealed_test.npz" not in source
     assert "../wm-harness" not in source
     command = pilot_driver.build_run_command(
-        7, "relper", Path("/tmp/pilot_train.npz"), Path("/tmp/pilot_eval.npz"),
+        7, "relper_u75", Path("/tmp/pilot_train.npz"), Path("/tmp/pilot_eval.npz"),
         Path("/tmp/pilot_out"), Path("/tmp/pilot.log"),
     )
     train_value = command[command.index("--train-data") + 1]
     eval_value = command[command.index("--eval-data") + 1]
     assert train_value == "/tmp/pilot_train.npz"
     assert eval_value == "/tmp/pilot_eval.npz"
+    assert command[command.index("--sampler") + 1] == "relper"
+    assert command[command.index("--uniform-mix") + 1] == "0.75"
     assert "--allow-sealed" not in command
     assert "--eval-only" not in command
+    uniform_command = pilot_driver.build_run_command(
+        7, "uniform", Path("/tmp/pilot_train.npz"), Path("/tmp/pilot_eval.npz"),
+        Path("/tmp/pilot_out"), Path("/tmp/pilot.log"),
+    )
+    assert uniform_command[uniform_command.index("--sampler") + 1] == "uniform"
+    assert "--uniform-mix" not in uniform_command
+    assert pilot_driver.RUN_SPECS == (
+        (7, "uniform"), (7, "relper_u75"), (8, "relper_u75"), (8, "uniform"),
+    )
 
 
 def make_event_split():
@@ -294,6 +326,134 @@
     assert report["selftest"] == "ALL_PASS"
     model = SpatialWorldModelV7(size="R7conv", n_history=2)
     assert model.param_counts()["model_total"] == 2_693_059
+
+
+def test_11_relper_uniform_mix_075():
+    copy_mse = np.array([0.0, 0.001, 0.01, 0.1, 0.002, 0.02], dtype=np.float64)
+    actions = np.array([0, 0, 0, 1, 1, 1], dtype=np.int64)
+    sampler = pilot.RelPERSampler(copy_mse, actions, seed=8, uniform_mix=0.75)
+    priority = sampler.relative_priority()
+    weights = (priority + 1e-6) ** 0.7
+    expected_p = 0.75 / len(copy_mse) + 0.25 * weights / weights.sum()
+    np.testing.assert_allclose(sampler.probabilities, expected_p, rtol=0.0, atol=1e-15)
+    assert sampler.uniform_mix == 0.75
+    assert abs(float(sampler.probabilities.sum()) - 1.0) < 1e-12
+    sampler.update(np.array([1, 3], dtype=np.int64), np.array([0.5, 0.125], dtype=np.float64))
+    sampler.refresh()
+    weights = (sampler.relative_priority() + 1e-6) ** 0.7
+    expected_p = 0.75 / len(copy_mse) + 0.25 * weights / weights.sum()
+    np.testing.assert_allclose(sampler.probabilities, expected_p, rtol=0.0, atol=1e-15)
+    for invalid in (-0.01, 1.01, float("nan")):
+        try:
+            pilot.RelPERSampler(copy_mse, actions, seed=8, uniform_mix=invalid)
+        except ValueError:
+            pass
+        else:
+            raise AssertionError(f"invalid uniform_mix accepted: {invalid}")
+
+
+def test_12_driver_verifies_both_pinned_npz_hashes():
+    old_train_sha = pilot_driver.TRAIN_SHA256
+    old_eval_sha = pilot_driver.EVAL_SHA256
+    try:
+        with tempfile.TemporaryDirectory() as temp_dir:
+            root = Path(temp_dir)
+            train = scorer.make_synthetic_split(list(pilot_driver.TRAIN_WORLDS), 8, seed=7)
+            evaluation = scorer.make_synthetic_split(list(pilot_driver.EVAL_WORLDS), 8, seed=8)
+            train_path = root / pilot_driver.TRAIN_FILE
+            eval_path = root / pilot_driver.EVAL_FILE
+            np.savez(train_path, **train)
+            np.savez(eval_path, **evaluation)
+            pilot_driver.TRAIN_SHA256 = pilot_driver.sha256_file(train_path)
+            pilot_driver.EVAL_SHA256 = pilot_driver.sha256_file(eval_path)
+            returned_train, returned_eval, manifest = pilot_driver.prepare_data(root)
+            assert returned_train == train_path.resolve()
+            assert returned_eval == eval_path.resolve()
+            assert manifest["train_file_sha256"] == pilot_driver.TRAIN_SHA256
+            assert manifest["eval_file_sha256"] == pilot_driver.EVAL_SHA256
+            train_bytes = train_path.read_bytes()
+            eval_bytes = eval_path.read_bytes()
+            train_path.write_bytes(train_bytes + b"corrupt-train")
+            try:
+                pilot_driver.verify_pinned_data(train_path, eval_path)
+            except ValueError as exc:
+                assert "train SHA" in str(exc)
+            else:
+                raise AssertionError("corrupt train NPZ passed the hash guard")
+            train_path.write_bytes(train_bytes)
+            eval_path.write_bytes(eval_bytes + b"corrupt-eval")
+            try:
+                pilot_driver.prepare_data(root)
+            except ValueError as exc:
+                assert "eval SHA" in str(exc)
+            else:
+                raise AssertionError("corrupt eval NPZ passed the hash guard")
+    finally:
+        pilot_driver.TRAIN_SHA256 = old_train_sha
+        pilot_driver.EVAL_SHA256 = old_eval_sha
+
+
+def test_13_summary_loads_relper_u75_runs():
+    score = {
+        "k1": {
+            "std_ratio_by_action": {"5": {"ratio": 0.30}},
+            "E_over_B": 0.25,
+            "block_open": {"model": {"mean_err": 0.04}},
+        },
+        "k3": {"E_over_B": 0.38},
+        "pilot_event_diagnostics": {"wake_e89_minus_stay_asleep_dBright": 0.03},
+        "diag_non_wake_interactions": {"asleep_all": {"R2": 0.1}},
+    }
+    seen = []
+    original = pilot_driver.load_run_score
+
+    def fake_load(out_dir):
+        seen.append(out_dir.name)
+        result = json.loads(json.dumps(score))
+        if "relper_u75" in out_dir.name:
+            result["pilot_event_diagnostics"]["wake_e89_minus_stay_asleep_dBright"] = 0.09
+        return result
+
+    try:
+        pilot_driver.load_run_score = fake_load
+        with tempfile.TemporaryDirectory() as temp_dir:
+            with contextlib.redirect_stdout(io.StringIO()):
+                summary = pilot_driver.summarize(Path(temp_dir))
+            assert summary["all_three_hold"]
+            assert json.loads((Path(temp_dir) / "pilot_summary.json").read_text()) == summary
+    finally:
+        pilot_driver.load_run_score = original
+    assert seen == ["s7_uniform", "s7_relper_u75", "s8_uniform", "s8_relper_u75"]
+
+
+def test_14_uniform_mix_cli_metadata():
+    train = scorer.make_synthetic_split([0, 1, 2], 20, seed=7)
+    evaluation = scorer.make_synthetic_split([4000, 4001], 20, seed=8)
+    old_argv = sys.argv
+    try:
+        with tempfile.TemporaryDirectory() as temp_dir:
+            root = Path(temp_dir)
+            train_path = root / "train.npz"
+            eval_path = root / "eval.npz"
+            out_dir = root / "out"
+            np.savez(train_path, **train)
+            np.savez(eval_path, **evaluation)
+            sys.argv = [
+                "train_v7.py", "--size", "tiny", "--n-history", "2", "--device", "cpu",
+                "--steps", "1", "--batch", "4", "--max-minutes", "0", "--skip-disk-check",
+                "--sampler", "relper", "--uniform-mix", "0.75", "--train-data", str(train_path),
+                "--eval-data", str(eval_path), "--out", str(out_dir),
+            ]
+            with contextlib.redirect_stdout(io.StringIO()):
+                pilot.main()
+            checkpoint = torch.load(out_dir / "model.pt", map_location="cpu", weights_only=False)
+            assert checkpoint["meta"]["relper_config"]["uniform_mix"] == 0.75
+            assert checkpoint["meta"]["relper_config"]["priority_mix"] == 0.25
+            score = json.loads((out_dir / "score_dev_reencode.json").read_text())
+            assert score["relper_config"]["uniform_mix"] == 0.75
+            assert score["relper_config"]["priority_mix"] == 0.25
+    finally:
+        sys.argv = old_argv
 
 
 if __name__ == "__main__":
diff -ruN --exclude=pilot_data --exclude=PROOF.md --exclude=PILOT-PLAN.md --exclude=train_v7.diff ../forecast8-pilot/train_v7.py ./train_v7.py
--- ../forecast8-pilot/train_v7.py	2026-11-25 04:33:33
+++ ./train_v7.py	2026-11-25 05:29:52
@@ -85,7 +85,11 @@
 
 
 class RelPERSampler:
-    def __init__(self, copy_mse: np.ndarray, actions: np.ndarray, seed: int):
+    def __init__(self, copy_mse: np.ndarray, actions: np.ndarray, seed: int, uniform_mix: float = 0.5):
+        uniform_mix = float(uniform_mix)
+        if not math.isfinite(uniform_mix) or not 0.0 <= uniform_mix <= 1.0:
+            raise ValueError(f"uniform_mix must be finite and in [0, 1], got {uniform_mix}")
+        self.uniform_mix = uniform_mix
         self.copy_mse = np.asarray(copy_mse, dtype=np.float64).copy()
         self.actions = np.asarray(actions, dtype=np.int64).copy()
         if self.copy_mse.shape != self.actions.shape or len(self.actions) == 0:
@@ -107,7 +111,7 @@
         priority = self.relative_priority()
         weights = (priority + 1e-6) ** 0.7
         n = len(weights)
-        return 0.5 * (1.0 / n) + 0.5 * (weights / weights.sum())
+        return self.uniform_mix * (1.0 / n) + (1.0 - self.uniform_mix) * (weights / weights.sum())
 
     def sample(self, batch_size: int) -> np.ndarray:
         return self.rng.choice(len(self.actions), size=batch_size, replace=True, p=self.probabilities)
@@ -755,6 +759,7 @@
     ap.add_argument("--n-history", type=int, choices=(1, 2), default=2)
     ap.add_argument("--rollout", choices=ROLLOUT_MODES, default="reencode")
     ap.add_argument("--sampler", choices=("uniform", "relper"), default="uniform")
+    ap.add_argument("--uniform-mix", type=float, default=0.5)
     ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
     ap.add_argument("--train-data", default="../wm5/data/train_dn.npz")
     ap.add_argument("--eval-data", default="../wm-harness/data/heldout.npz")
@@ -832,7 +837,7 @@
     copy_mse, action_ids = transition_copy_mse(tr, xi1, ai1)
     event_labeller = fit_event_labeller(tr)
     train_events = label_transition_events(tr, event_labeller)
-    priority_tracker = RelPERSampler(copy_mse, action_ids, args.seed)
+    priority_tracker = RelPERSampler(copy_mse, action_ids, args.seed, uniform_mix=args.uniform_mix)
 
     train_meta = {
         "arch": expected_arch,
@@ -841,8 +846,8 @@
         "rollout_mode": args.rollout,
         "sampler": args.sampler,
         "relper_config": {
-            "uniform_mix": 0.5,
-            "priority_mix": 0.5,
+            "uniform_mix": float(args.uniform_mix),
+            "priority_mix": 1.0 - float(args.uniform_mix),
             "alpha": 0.7,
             "cap": 20.0,
             "action_epsilon": 1e-4,
````

The only trainer functional change is the configurable mixture and its metadata. The driver changes implement pilot-2 arm naming, 75/25 Rel-PER invocation, pilot-1 data reuse, and both hash guards. The paired gate/summary logic is unchanged apart from loading the `s*_relper_u75` directories.

Pilot 1 source hashes remain exactly as pinned in its proof:

```text
3c14e0a7b785ccd73de0f6f1711144562bfcbbcc188fdb552340f091db47da3c  forecast8-pilot/train_v7.py
e44c3ec12d34268e5c24ad9cb35e23bab292c03087f8624cb53d251a77f9ec1d  forecast8-pilot/pilot_driver.py
75a06ef37f7201e8ef47dcd34eb94d3801fef43782cf563a85a4af2480ebf2d3  forecast8-pilot/test_pilot.py
4dd22636c4a8fc9e6d5a76f70e7e65243c234678f1e64203c78009ecb88bc3e9  forecast8-pilot/PILOT-PLAN.md
c87f4110057bddaf4610c423e64c13dbe22f882aa9ea8dd53e4f3b57d7e67006  forecast8-pilot/model_v7.py
ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912  forecast8-pilot/scorer.py
77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa  forecast8-pilot/withlock.sh
```

## CPU tests

### M1

Command:

```bash
~/learner-ops/p2venv/bin/python -B -u test_pilot.py
```

Final output:

```text
{
  "selftest": "ALL_PASS",
  "scorer_version": "forecast7-v2-rung1-n200_or_neff10",
  "check1_perfect_E": {
    "1": 0.0,
    "3": 0.0,
    "5": 0.0
  },
  "check1_verdict": "PASS",
  "check1_rung1_verdict": "PASS",
  "check1_block_open": {
    "model_mean_err": 0.0,
    "copy_mean_err": 0.5,
    "sos_mean_err": 0.5132075471698113,
    "act_mean_err": 0.5,
    "true_open": 210,
    "true_blocked": 159
  },
  "check2_zero_diff_from_copy": {
    "1": 0.0,
    "3": 0.0,
    "5": 0.0
  },
  "check2_zero_pcs90_pred": 1,
  "check2_zero_copy_ness": 0.0,
  "check2_zero_verdict": "FAIL",
  "check2_zero_rung1_verdict": "FAIL",
  "check3_drift_bias": {
    "1": 0.010000000000000009,
    "3": 0.030000000000000013,
    "5": 0.05000000000000001
  },
  "check3_drift_rmse": {
    "1": 0.010000000000000007,
    "3": 0.030000000000000016,
    "5": 0.05000000000000001
  },
  "check4_proves_wrong": true,
  "check4_verdict": "FAIL",
  "check5_bugA10_verdict": "FAIL"
}
PASS: test_10_scorer_and_architecture_unchanged
PASS: test_11_relper_uniform_mix_075
PASS: test_12_driver_verifies_both_pinned_npz_hashes
PASS: test_13_summary_loads_relper_u75_runs
PASS: test_14_uniform_mix_cli_metadata
PASS: test_1_pins_and_default_sampler
PASS: test_2_uniform_byte_identical_20_steps
PASS: test_3_relper_formula_distribution_and_determinism
PASS: test_4_relper_has_no_extra_forward_passes
PASS: test_5_heldout_worlds_never_enter_training
PASS: test_6_driver_cannot_reach_other_eval_paths
PASS: test_7_event_labeller_and_exact_p2_metric
PASS: test_8_paired_gate_boundaries
PASS: test_9_distribution_refreshes_every_25_steps_in_real_loop
ALL 14 PILOT TESTS PASSED
EXIT=0
```

The first M1 run exited `1` because the new summary-path test incorrectly supplied equal uniform/Rel-PER wake gaps, so P2 correctly evaluated false. The failing evidence was:

```text
PASS: test_12_driver_verifies_both_pinned_npz_hashes
...
"P2_both_seeds": false,
"all_three_hold": false,
"decision": "NO_SCORED_RANK8"
Traceback (most recent call last):
  File "test_pilot.py", line 419, in test_13_summary_loads_relper_u75_runs
    assert summary["all_three_hold"]
AssertionError
EXIT=1
```

The fixture was corrected to supply a 3x Rel-PER wake gap, and the full suite was rerun to the passing output above.

### M3 CPU under nice

Command:

```bash
ssh m3 'nice -n 10 ~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p2/test_pilot.py'
```

Output:

```text
{
  "selftest": "ALL_PASS",
  "scorer_version": "forecast7-v2-rung1-n200_or_neff10",
  "check1_perfect_E": {
    "1": 0.0,
    "3": 0.0,
    "5": 0.0
  },
  "check1_verdict": "PASS",
  "check1_rung1_verdict": "PASS",
  "check1_block_open": {
    "model_mean_err": 0.0,
    "copy_mean_err": 0.5,
    "sos_mean_err": 0.5132075471698113,
    "act_mean_err": 0.5,
    "true_open": 210,
    "true_blocked": 159
  },
  "check2_zero_diff_from_copy": {
    "1": 0.0,
    "3": 0.0,
    "5": 0.0
  },
  "check2_zero_pcs90_pred": 1,
  "check2_zero_copy_ness": 0.0,
  "check2_zero_verdict": "FAIL",
  "check2_zero_rung1_verdict": "FAIL",
  "check3_drift_bias": {
    "1": 0.010000000000000009,
    "3": 0.030000000000000013,
    "5": 0.05000000000000001
  },
  "check3_drift_rmse": {
    "1": 0.010000000000000007,
    "3": 0.030000000000000016,
    "5": 0.05000000000000001
  },
  "check4_proves_wrong": true,
  "check4_verdict": "FAIL",
  "check5_bugA10_verdict": "FAIL"
}
PASS: test_10_scorer_and_architecture_unchanged
PASS: test_11_relper_uniform_mix_075
PASS: test_12_driver_verifies_both_pinned_npz_hashes
PASS: test_13_summary_loads_relper_u75_runs
PASS: test_14_uniform_mix_cli_metadata
PASS: test_1_pins_and_default_sampler
PASS: test_2_uniform_byte_identical_20_steps
PASS: test_3_relper_formula_distribution_and_determinism
PASS: test_4_relper_has_no_extra_forward_passes
PASS: test_5_heldout_worlds_never_enter_training
PASS: test_6_driver_cannot_reach_other_eval_paths
PASS: test_7_event_labeller_and_exact_p2_metric
PASS: test_8_paired_gate_boundaries
PASS: test_9_distribution_refreshes_every_25_steps_in_real_loop
ALL 14 PILOT TESTS PASSED
EXIT=0
```

Coverage includes exact array equality between `--uniform-mix 0.5` and pilot 1's Rel-PER probabilities and sampled draws; the exact 75/25 probability formula before and after refresh; invalid-mixture rejection; uniform batch/loss/metric/parameter identity over 20 optimizer steps; no extra forward passes; duplicate EMA updates; 25-step refresh in the real synthetic loop; held-out-world exclusion; driver path isolation; both corrupt-NPZ hash failures; exact P2 computation and gate boundaries; pilot-2 run naming; CLI metadata `0.75/0.25`; pinned scorer/model/lock hashes; and the full scorer self-test.

## Real pilot-data preparation, no training

Command:

```bash
ssh m3 'nice -n 10 ~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p2/pilot_driver.py --prepare-only'
```

Output:

```text
[PILOT_DATA] {"eval": {"actions": 2800, "frames": 2817, "k1_windows": 2800, "worlds": [3072, 3073, 3074, 3075, 3076, 3077, 3078, 3079]}, "eval_file_sha256": "545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c", "eval_path": "<m3-project>/PROBLEM-7/wm8p/pilot_data/eval_worlds_3072_3079.npz", "expected_total_minutes": [24.0, 27.0], "max_minutes": 6.5, "steps": 3000, "train": {"actions": 25200, "frames": 25382, "k1_windows": 25200, "worlds": [3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009, 3010, 3011, 3012, 3013, 3014, 3015, 3016, 3017, 3018, 3019, 3020, 3021, 3022, 3023, 3024, 3025, 3026, 3027, 3028, 3029, 3030, 3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038, 3039, 3040, 3041, 3042, 3043, 3044, 3045, 3046, 3047, 3048, 3049, 3050, 3051, 3052, 3053, 3054, 3055, 3056, 3057, 3058, 3059, 3060, 3061, 3062, 3063, 3064, 3065, 3066, 3067, 3068, 3069, 3070, 3071]}, "train_file_sha256": "e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f", "train_path": "<m3-project>/PROBLEM-7/wm8p/pilot_data/train_worlds_3000_3071.npz"}
[PILOT] PREPARE_ONLY_NO_TRAINING
EXIT=0
```

The resolved paths point into pilot 1's `wm8p/pilot_data/`; no pilot-2 data copy or rewrite occurred.

## Final hashes

Identical on M1 `forecast8-pilot2/` and M3 `wm8p2/`:

```text
c87f4110057bddaf4610c423e64c13dbe22f882aa9ea8dd53e4f3b57d7e67006  model_v7.py
ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912  scorer.py
77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa  withlock.sh
99ea9e45d8ae1dfdf6254fb0e5e313146723e63acc932a90539100a9f6f647b1  train_v7.py
3edeff5c3200c5dc53032d6229da3db648e6b7bb6e587a09d0d08e61fc2c177c  pilot_driver.py
19a23dfc40c1cfd40f02331533704fc5054cc6fbb733877ab77919de2eccfb8a  test_pilot.py
7ef97f2f9974e5c085b0ec05815ed817375dd26ebe69e1c6a019f5e30cee3f7d  PILOT2-PLAN.md
```

Reused pilot-1 data hashes:

```text
e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f  pilot_data/train_worlds_3000_3071.npz
545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c  pilot_data/eval_worlds_3072_3079.npz
```

No lint or typecheck command is configured in the pilot directories; the provided CPU test suite is the verification command.

## Exact pilot-2 launch command

Lead only, on M3:

```bash
~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p2/pilot_driver.py
```

The driver rechecks both data hashes before every launch, then runs `s7_uniform`, `s7_relper_u75`, `s8_relper_u75`, `s8_uniform` serially through `withlock.sh`, 3,000 steps each, `--max-minutes 6.5`. Rel-PER runs receive `--uniform-mix 0.75`; uniform runs omit the flag and retain pilot 1's default. It writes `runs/pilot_summary.json` and exits nonzero on any P1/P2/P3 miss.
