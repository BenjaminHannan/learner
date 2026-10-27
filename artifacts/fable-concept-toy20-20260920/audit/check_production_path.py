"""Agent 3 / ruling C11: exercise the REAL production fit and predict paths.

Byte agreement on the full-history fixture (the builder's own
`verify_tokenization_against-agent1`) shows that the two tokenizers agree on the
ONE sequence shape where every transition is observed.  It says nothing about the
forecast paths, which are the paths every registered query actually takes.  This
file checks those paths, structurally AND operationally:

  A  loader     - the registered production loader, its C11 guard, audit keys
  B  prefixes   - nested support prefixes and the 3:1 fit/selection split
  C  query      - query index, endpoint gather, serialized padding
  D  blanking   - forecast OBSERVED tokens carry no information, proved by
                  perturbation through the real forward pass
  E  predict    - the real `run_predict_agent1` entry point, end to end

Learner-touching work runs on `fixture-v1.1` ONLY (families o and c, no M).  The
calibration worlds are read for index/role structure alone - no parameters, no
forward pass, no scoring - which the pilot rules permit.

NO PREDICTION VALUES ARE PUBLISHED.  Group D and E report only equality,
inequality, finiteness and shape.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys

import numpy as np
import torch

ART = pathlib.Path(__file__).resolve().parents[1]
REPO = ART.parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fable_concepttoy20_models as M  # noqa: E402

FIXTURE = ART / "fixture-v1.1" / "public"
CALIB = ART / "calibration-v1.1" / "public"
SCRATCH = pathlib.Path(__file__).resolve().parent / "_scratch_production_path"

RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})


def world_ids(root: pathlib.Path) -> list[str]:
    index = json.loads((root / "worlds.json").read_text())
    return [w["world_public_id"] for w in index["worlds"]]


# ---------------------------------------------------------------- A. loader
def group_a() -> None:
    worlds = world_ids(FIXTURE)
    check("A0 fixture exposes two worlds", len(worlds) == 2, str(worlds))

    # A1 the registered loader reads the serialized layout with the DEFAULT flag.
    episodes = M.load_world_support(FIXTURE, worlds[0])
    check(
        "A1 load_world_support default (allow_semantic_fixture=False) reads serialized layout",
        len(episodes) == 8 and episodes.properties.shape[1:] == (M.N_OBJECTS, M.N_PROPERTIES),
        f"episodes={len(episodes)} properties={tuple(episodes.properties.shape)}",
    )

    # A2 the C11 guard actually refuses a directory without the serialized file.
    SCRATCH.mkdir(parents=True, exist_ok=True)
    empty = SCRATCH / "empty_world"
    empty.mkdir(exist_ok=True)
    try:
        M.load_world_support(SCRATCH, "empty_world")
        check("A2 C11 guard refuses a non-serialized directory", False, "no exception raised")
    except ValueError as exc:
        check("A2 C11 guard refuses a non-serialized directory", "C11" in str(exc), str(exc)[:80])

    # A3 no registered driver reaches the semantic adapter.
    tree = ast.parse((SCRIPTS / "fable_concepttoy20_models.py").read_text())
    offenders = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if fn.name not in {"run_fit", "run_predict", "run_predict_agent1", "main"}:
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            target = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if target != "load_world_support":
                continue
            for kw in node.keywords:
                if kw.arg == "allow_semantic_fixture" and not (
                    isinstance(kw.value, ast.Constant) and kw.value.value is False
                ):
                    offenders.append(f"{fn.name}:{node.lineno}")
            if len(node.args) >= 3:
                offenders.append(f"{fn.name}:{node.lineno} positional third arg")
    check(
        "A3 run_fit/run_predict/main never enable the semantic-fixture adapter",
        not offenders,
        str(offenders),
    )

    # A4 audit keys: the models side delegates to the public loader and matches
    #    the frozen audit_keys.json byte for byte.
    loader = M.public_loader()
    check("A4a public loader imports", loader is not None, "")
    check(
        "A4b models AUDIT_KEY_FORMAT is the canonical spelling",
        M.AUDIT_KEY_FORMAT == "{world_public_id}-fit{episode_index:04d}h{horizon}e{endpoint}",
        M.AUDIT_KEY_FORMAT,
    )
    total = mismatch = 0
    for world in worlds:
        keys = json.loads((FIXTURE / world / "audit_keys.json").read_text())
        for row in keys:
            total += 1
            built = M.audit_key(world, row["episode_index"], row["horizon"], row["endpoint"])
            if built != row["audit_id"]:
                mismatch += 1
    check("A4c every frozen audit key reproduces via models.audit_key", mismatch == 0,
          f"{total - mismatch}/{total} equal")


# -------------------------------------------------------------- B. prefixes
def _prefix_facts(root: pathlib.Path, world: str, budgets: list[int]) -> dict:
    episodes = M.load_world_support(root, world)
    sets, roles = [], []
    for b in budgets:
        p = M.prefix_episodes(episodes, b)
        idx = sorted(int(v) for v in p.episode_index)
        sets.append(idx)
        fit, sel = M.split_roles(p)
        roles.append((len(fit), len(sel), sorted(int(v) for v in sel.episode_index)))
    return {"sets": sets, "roles": roles, "n": len(episodes)}


def group_b() -> None:
    # Fixture has 8 support episodes -> rungs 32 and 64 only.
    facts = _prefix_facts(FIXTURE, world_ids(FIXTURE)[0], [32, 64])
    check("B1 fixture prefix sizes are 4 and 8", [len(s) for s in facts["sets"]] == [4, 8],
          str([len(s) for s in facts["sets"]]))
    check("B2 fixture prefixes are nested", set(facts["sets"][0]) <= set(facts["sets"][1]), "")
    check("B3 fixture prefix is a contiguous index prefix",
          facts["sets"][0] == list(range(4)) and facts["sets"][1] == list(range(8)), "")
    check("B4 fixture 3:1 split puts selection at index 3 of every group of four",
          facts["roles"][0][2] == [3] and facts["roles"][1][2] == [3, 7],
          str([r[2] for r in facts["roles"]]))

    # Calibration: structure only.  No parameters, no forward pass, no scoring.
    budgets = list(M.BUDGETS)
    bad_nest = bad_split = bad_size = 0
    worlds = world_ids(CALIB)
    for world in worlds:
        f = _prefix_facts(CALIB, world, budgets)
        if [len(s) for s in f["sets"]] != [b // 8 for b in budgets]:
            bad_size += 1
        for i in range(len(budgets) - 1):
            if not set(f["sets"][i]) <= set(f["sets"][i + 1]):
                bad_nest += 1
        for i, b in enumerate(budgets):
            expected = list(range(3, b // 8, 4))
            if f["roles"][i][2] != expected:
                bad_split += 1
    check("B5 all 12 calibration worlds: rung sizes 4/8/16/32/64", bad_size == 0, f"{bad_size} bad")
    check("B6 all 12 calibration worlds: every rung nests in the next", bad_nest == 0, f"{bad_nest} bad")
    check("B7 all 12 calibration worlds: 3:1 split at index 3 mod 4 inside every rung",
          bad_split == 0, f"{bad_split} bad")


# ----------------------------------------------------------------- C. query
def group_c() -> None:
    worlds = world_ids(FIXTURE)
    bad_index = bad_pad_file = bad_pad_tensor = bad_endpoint_type = 0
    checked = 0
    for world in worlds:
        d = FIXTURE / world
        for stem, n_name, idx_name in (
            ("query", "query_n_records", "query_index"),
            ("audit", "audit_n_records", "audit_index"),
        ):
            recs = np.load(d / f"{stem}_records.npy")
            n = np.load(d / f"{n_name}.npy")
            idx = np.load(d / f"{idx_name}.npy")
            checked += recs.shape[0]
            if not np.array_equal(idx, n - 1):
                bad_index += 1
            for r in range(recs.shape[0]):
                if recs.shape[1] > int(n[r]) and np.abs(recs[r, int(n[r]):, :]).max() != 0.0:
                    bad_pad_file += 1
                row = recs[r, int(idx[r])]
                if row[M.SLICE_RECORD_TYPE][M.RECORD_TYPE_QUERY] != 1.0:
                    bad_endpoint_type += 1
                if row[M.SLICE_PRESENT].max() != 0.0 or row[M.SLICE_SENSOR].max() != 0.0:
                    bad_endpoint_type += 1

    check("C1 query_index / audit_index equal n_records - 1", bad_index == 0, f"{bad_index} bad")
    check("C2 serialized rows at index >= n_records are all-zero (SCHEMA 2.3.1)",
          bad_pad_file == 0, f"{bad_pad_file} bad of {checked} rows")
    check("C3 the endpoint row is a QUERY with sensor=0 and present=0",
          bad_endpoint_type == 0, f"{bad_endpoint_type} bad of {checked} rows")

    # C4 the loader's own padded tensor agrees with the file and the index.
    for world in worlds:
        ids, records, endpoint, features = M.load_queries_agent1(FIXTURE / world)
        n = np.load(FIXTURE / world / "query_n_records.npy")
        idx = np.load(FIXTURE / world / "query_index.npy")
        if records.shape[1] != M.FIXED_SEQUENCE_LENGTH:
            bad_pad_tensor += 1
        if not torch.equal(endpoint, torch.tensor(np.asarray(idx), dtype=torch.int64)):
            bad_pad_tensor += 1
        for r in range(records.shape[0]):
            if records[r, int(n[r]):, :].abs().max().item() != 0.0:
                bad_pad_tensor += 1
    check("C4 loader pads to 17 rows with zeros and endpoint == query_index",
          bad_pad_tensor == 0, f"{bad_pad_tensor} bad")
    check("C5 record_ids count matches the 96-target panel",
          len(ids) == 96 and len(set(ids)) == 96, f"{len(ids)} ids")

    # C6 OPERATIONAL: padding beyond the endpoint cannot reach a prediction.
    world = worlds[0]
    ids, records, endpoint, features = M.load_queries_agent1(FIXTURE / world)
    n = np.load(FIXTURE / world / "query_n_records.npy")
    for arm in ("G", "T"):
        params = {k: torch.tensor(v, dtype=torch.float32)[None, ...]
                  for k, v in M.initial_parameters(arm, world, 0).items()}
        with torch.no_grad():
            base = M.forward(arm, params, records.unsqueeze(0), endpoint, features)
            poisoned = records.clone()
            for r in range(poisoned.shape[0]):
                poisoned[r, int(n[r]):, :] = 7.5
            after = M.forward(arm, params, poisoned.unsqueeze(0), endpoint, features)
        check(f"C6 arm {arm}: poisoning every padded row leaves predictions bit-identical",
              torch.equal(base, after), "")
        check(f"C7 arm {arm}: all 96 predictions are finite",
              bool(torch.isfinite(base).all()), f"shape={tuple(base.shape)}")


# -------------------------------------------------------------- D. blanking
def group_d() -> None:
    """The decisive group: forecast OBSERVED tokens must carry no information."""
    world = world_ids(FIXTURE)[0]
    episodes = M.load_world_support(FIXTURE, world)
    count = len(episodes)

    # D1/D2 structural, across a grid of (prefix, horizon) forecast shapes.
    bad_blank = bad_prefix = bad_endpoint = bad_tail = 0
    shapes = 0
    for prefix in range(0, M.N_TRANSITIONS):
        for horizon in (1, 2, 4):
            if prefix + horizon > M.N_TRANSITIONS:
                continue
            shapes += 1
            p = torch.full((count,), prefix, dtype=torch.int64)
            h = torch.full((count,), horizon, dtype=torch.int64)
            recs, end = M.build_sequences(episodes, p, h)
            total = prefix + horizon
            for n in range(count):
                if int(end[n]) != 1 + 2 * (total - 1):
                    bad_endpoint += 1
                for t in range(total):
                    obs_at = 2 + 2 * t
                    if t == total - 1:
                        # The target OBSERVED record is never built.
                        if obs_at < M.FIXED_SEQUENCE_LENGTH and (
                            recs[n, obs_at, M.SLICE_RECORD_TYPE].abs().sum().item() != 0.0
                        ):
                            bad_tail += 1
                        continue
                    sensor = recs[n, obs_at, M.SLICE_SENSOR].item()
                    present = recs[n, obs_at, M.SLICE_PRESENT].item()
                    if t >= prefix:  # forecast region
                        if sensor != 0.0 or present != 0.0:
                            bad_blank += 1
                    else:  # real prefix
                        want_p = float(episodes.sensor_present[n, t])
                        want_s = float(episodes.sensor[n, t]) * want_p
                        if present != want_p or sensor != want_s:
                            bad_prefix += 1
    check("D1 forecast OBSERVED tokens are blank (sensor=0, present=0) on every shape",
          bad_blank == 0, f"{bad_blank} bad over {shapes} (prefix,horizon) shapes")
    check("D2 prefix OBSERVED tokens carry the real masked measurement",
          bad_prefix == 0, f"{bad_prefix} bad")
    check("D3 endpoint is the final QUERY at 1+2*(prefix+horizon-1)", bad_endpoint == 0,
          f"{bad_endpoint} bad")
    check("D4 the target OBSERVED record is never constructed", bad_tail == 0, f"{bad_tail} bad")

    # D5/D6/D7 OPERATIONAL: perturb the sensor stream and watch the real forward
    # pass.  Future observations must not move a prediction; past ones must.
    prefix, horizon = 3, 4
    p = torch.full((count,), prefix, dtype=torch.int64)
    h = torch.full((count,), horizon, dtype=torch.int64)
    features = M.build_query_features(
        episodes.properties,
        torch.zeros((count,), dtype=torch.int64),
        torch.ones((count,), dtype=torch.int64),
    )
    recs, end = M.build_sequences(episodes, p, h)

    def perturbed(lo: int, hi: int) -> Episodes:  # type: ignore[name-defined]
        e = episodes.select(torch.arange(count))
        e.sensor[:, lo:hi] = e.sensor[:, lo:hi] + 13.0
        e.sensor_present[:, lo:hi] = 1.0
        return e

    for arm in ("G", "T"):
        params = {k: torch.tensor(v, dtype=torch.float32)[None, ...]
                  for k, v in M.initial_parameters(arm, world, 0).items()}
        with torch.no_grad():
            base = M.forward(arm, params, recs.unsqueeze(0), end, features)

            fut_recs, fut_end = M.build_sequences(perturbed(prefix, M.N_TRANSITIONS), p, h)
            fut = M.forward(arm, params, fut_recs.unsqueeze(0), fut_end, features)

            tgt_recs, tgt_end = M.build_sequences(
                perturbed(prefix + horizon - 1, prefix + horizon), p, h)
            tgt = M.forward(arm, params, tgt_recs.unsqueeze(0), tgt_end, features)

            past_recs, past_end = M.build_sequences(perturbed(0, prefix), p, h)
            past = M.forward(arm, params, past_recs.unsqueeze(0), past_end, features)

        check(f"D5 arm {arm}: perturbing the whole forecast sensor stream changes nothing",
              torch.equal(base, fut), "")
        check(f"D6 arm {arm}: perturbing the target transition's sensor changes nothing",
              torch.equal(base, tgt), "")
        check(f"D7 arm {arm}: perturbing the OBSERVED prefix does change predictions",
              not torch.equal(base, past), "")


# --------------------------------------------------------------- E. predict
def group_e() -> None:
    world = world_ids(FIXTURE)[0]
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = []
    for arm in ("G", "T"):
        params = {k: torch.tensor(v, dtype=torch.float32)[None, ...]
                  for k, v in M.initial_parameters(arm, world, 0).items()}
        ckpt = SCRATCH / f"audit_untrained_{arm}.pt"
        torch.save({"format": "ct20-phaseA-checkpoint-v1", "arm": arm, "world_id": world,
                    "seed": 0, "parameters": params}, ckpt)
        dest = SCRATCH / f"predictions_{arm}.json"
        first = M.run_predict_agent1(str(ckpt), str(FIXTURE / world), str(dest))
        second = M.run_predict_agent1(str(ckpt), str(FIXTURE / world), str(dest))
        ids = json.loads((FIXTURE / world / "query_record_ids.json").read_text())
        if isinstance(ids, dict):
            ids = ids.get("record_ids", ids.get("ids"))
        ids = [str(v) for v in ids]
        payload = json.loads(dest.read_text())
        check(f"E1 arm {arm}: run_predict_agent1 returns one value per frozen record id",
              sorted(first) == sorted(ids), f"{len(first)} values, {len(ids)} ids")
        check(f"E2 arm {arm}: every prediction is finite",
              all(np.isfinite(v) for v in first.values()), "")
        check(f"E3 arm {arm}: the entry point is deterministic across two runs",
              all(first[k] == second[k] for k in first), "")
        check(f"E4 arm {arm}: the written file carries only public fields",
              set(payload) == {"contract_version", "arm", "checkpoint", "predictions"},
              str(sorted(payload)))
        out.append(arm)
    check("E5 both arms ran the real predict entry point", out == ["G", "T"], str(out))


def main() -> int:
    group_a()
    group_b()
    group_c()
    group_d()
    group_e()
    failed = [r for r in RESULTS if r["status"] != "PASS"]
    summary = {
        "source_sha256": M.source_hash(),
        "fixture": str(FIXTURE),
        "total": len(RESULTS),
        "passed": len(RESULTS) - len(failed),
        "failed": len(failed),
        "results": RESULTS,
    }
    dest = pathlib.Path(__file__).resolve().parent / "production_path_results.json"
    dest.write_text(json.dumps(summary, indent=2))
    for r in RESULTS:
        print(f"[{r['status']}] {r['check']}" + (f"  ({r['detail']})" if r["detail"] else ""))
    print(f"\n{summary['passed']}/{summary['total']} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
