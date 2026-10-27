"""Fast CPU contracts for the frozen-weight wire query-rule replay (scripts/premonition_wire_replay.py).

Covers: W bit-identity with the unwrapped wire at BOTH call sites, the WG real-fetch guard (including a
NULL fetch that must NOT open it), the WGC cap arithmetic and its zero-norm bypass, ratio/near-zero
handling, the wire-direction transport formula, panel determinism and refusals, the protected historical
directory, label separation, unchanged weights, the resumable reuse key, and every branch of the table's
guard-signal / no-harm / eta rules on synthetic rows.

Every fixture is a freshly built UNTRAINED wire model (with W_r and the gate given small nonzero random
values so the residual is actually active) on an 8-world panel.  No training, no GPU, no network, no test
split, no checkpoint of the real rosters is loaded.

    PY -B tests/test_premonition_wire_replay.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_wire_replay as WR  # noqa: E402

CHECKS = 0


def check(name, cond):
    global CHECKS
    assert bool(cond), name
    CHECKS += 1
    print("PASS " + name, flush=True)


def refuses(name, call):
    try:
        call()
    except SystemExit:
        check(name, True)
        return
    check(name, False)


def build_fixture(seed: int, work: Path):
    """An untrained wire model with an ACTIVE residual, saved in the gpu_port blob format."""
    import torch
    from dataclasses import asdict
    import premonition_relation_shortcut as RS
    model = RS.build("bypass-k1", seed, 0.2, shortcut=True)
    generator = torch.Generator().manual_seed(seed + 977)
    with torch.no_grad():
        model.rel_query.weight.copy_(torch.randn(model.rel_query.weight.shape, generator=generator) * 0.05)
        model.rel_gate.weight.copy_(torch.randn(model.rel_gate.weight.shape, generator=generator) * 0.05)
        model.rel_gate.bias.fill_(0.3)
    model.eval()
    folder = work / "ckpt"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "fixture-s0-1.pt"
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "arm": "bypass-k1",
                "identity": {"note": "untrained test fixture"}, "seed": seed, "no_step_emb": False,
                "ordered_evidence": False, "relation_shortcut": True, "key_pool": False, "width": None,
                "model_class": type(model).__name__,
                "writer_class": type(model.writer).__name__ if model.writer is not None else None,
                "lr_cooldown": 0.0}, path)
    return model, path


def main() -> int:
    started = time.perf_counter()
    WR.L.bootstrap()
    import torch
    torch.set_num_threads(2)
    import premonition_first_card_probe as P
    import premonition_handoff_diag as H
    spec = WR.L.spec()

    tmp = tempfile.TemporaryDirectory(prefix="wire-replay-test-")
    work = Path(tmp.name)

    # ------------------------------------------------------------------ 1. panels
    before_suite = WR.directory_sha256(WR.HISTORICAL_SUITE)
    panels_dir = work / "panels"
    manifest = WR.generate_panels(panels_dir, worlds=8, quiet=True)
    check("the panel seed string is distinct from every historical panel namespace",
          WR.PANEL_NAMESPACE == "premonition-wire-replay-20260919-v1"
          and "pairsuite" not in WR.PANEL_NAMESPACE and "handoff" not in WR.PANEL_NAMESPACE
          and manifest["rng_namespace"] == WR.PANEL_NAMESPACE)
    check("the manifest records a sha256 for every panel file",
          sorted(manifest["panels"]) == sorted(WR.PANELS)
          and all(WR.sha256_file(panels_dir / info["file"]) == info["sha256"]
                  for info in manifest["panels"].values())
          and manifest["panel_content_sha256"] == WR.sha256_json(
              {n: manifest["panels"][n]["sha256"] for n in WR.PANELS}))
    second = WR.generate_panels(work / "panels2", worlds=8, quiet=True)
    check("panels are deterministic from the seed string alone",
          second["panel_content_sha256"] == manifest["panel_content_sha256"])
    refuses("panels refuses to overwrite an existing directory",
            lambda: WR.generate_panels(panels_dir, worlds=8, quiet=True))
    refuses("every output path inside the historical pair suite is refused",
            lambda: WR.guard_output(WR.HISTORICAL_SUITE / "panels"))
    refuses("the historical pair-suite directory itself is refused",
            lambda: WR.guard_output(WR.HISTORICAL_SUITE))
    matched = WR.load_panel("matched", panels_dir, manifest)
    check("the matched panel carries six questions per world after one shared story prefix",
          matched["n"] == 8 and len(matched["chunks"][0]["meta"]) == 48
          and [m["question"] for m in matched["chunks"][0]["meta"][:6]] == list(WR.MATCHED_QUESTIONS)
          and len({m["asker"] for m in matched["chunks"][0]["meta"][:6]}) == 1
          and len({m["friend"] for m in matched["chunks"][0]["meta"][:6]}) == 1)
    metas = matched["chunks"][0]["meta"]
    check("each question sits at its canonical slot and all six share one story and one store",
          all(m["slot"] == (WR.TWO_HOP_SLOT if m["hops"] == 2 else WR.ONE_HOP_SLOT) for m in metas)
          and all(m["question_line"] == m["story_lines"] + (2 if m["hops"] == 2 else 0)
                  for m in metas)
          and len({m["story_lines"] for m in metas[:6]}) == 1
          and "MEASURED DEVIATION" in manifest["layout_note"])
    two_hop_rows = [q for q, m in enumerate(metas) if m["hops"] == 2]
    one_hop_rows = [q for q, m in enumerate(metas) if m["hops"] == 1]
    twin = WR.load_panel("c4", panels_dir, manifest)
    check("the twin panels use the existing pair-suite edit semantics",
          twin["kind"] == "pair" and twin["edit"] == "link" and twin["n"] == 8
          and all("answer_a" in m and "answer_b" in m for m in twin["chunks"][0]["meta"]))
    check("the historical pair-suite directory is unchanged by panel generation",
          WR.directory_sha256(WR.HISTORICAL_SUITE) == before_suite)

    # ------------------------------------------------------------------ 2. the fixture and variant W
    model, ckpt = build_fixture(0, work)
    fingerprint = P.fingerprint(model)
    check("the fixture's residual is actually active (nonzero W_r and gate)",
          float(model.rel_query.weight.norm()) > 0 and float(model.rel_gate.weight.norm()) > 0
          and float(model.rel_gate.bias) != 0.0)
    batch = H._strip_labels(matched["chunks"][0]["a"])
    with torch.no_grad():
        bare = WR.replay(model, batch, WR.NullRule(), capture=False)
        native = H.run_condition(model, batch, H.FieldView(batch, spec), "U",
                                 [m["key_a"] for m in matched["chunks"][0]["meta"]])
        with WR.QueryRule(model, "W", spec) as rule_w:
            wrapped = WR.replay(model, batch, rule_w, capture=True)
        calls_w = {int(c["step"]): c for c in wrapped["calls"]}
    check("variant W is bit-identical to the unwrapped wire (answers, fetched cards and scores)",
          torch.equal(wrapped["tokens"], bare["tokens"]) and torch.equal(wrapped["cards"], bare["cards"])
          and torch.equal(wrapped["fetched"], bare["fetched"])
          and wrapped["digests"] == bare["digests"] == native["digests"]
          and torch.equal(wrapped["cards"], native["cards"]))
    check("observation-only telemetry changes nothing and the parity check agrees",
          WR.observation_parity(model, matched, spec)["pass"]
          and P.fingerprint(model) == fingerprint)
    check("the _recall call site uses the same rule and is excluded from telemetry",
          WR.recall_excluded(model, matched, spec)["pass"])

    # the wrapper must cover BOTH call sites: _recall's query changes with the variant
    def recall_query(variant):
        """The query `_recall` hands to store.ask, captured by spying on the store (not the model)."""
        from premonition.model import _norm
        with torch.no_grad(), WR.QueryRule(model, variant, spec) as rule:
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            mentions = model._mentions(batch)
            episode = model._start(batch, hidden, store, mentions)
            everyone = torch.arange(batch.q_visit.shape[0])
            rule.begin_step(0)
            rows, _h, _a, _s = model._step(episode, everyone, 0, store)
            q0 = model.heads.query(_norm(rows[:, model._register_base])).clone()
            seen = {}
            original = store.ask

            def spy(query, *args, **kwargs):
                seen["q"] = query.clone()
                return original(query, *args, **kwargs)

            store.ask = spy
            gold, _t, _m = store.gold(matched["chunks"][0]["a"].gold_lines, batch.q_visit, batch.q_line)
            model._recall(store, episode, everyone, rows, gold)
            store.ask = original
            return seen["q"], q0

    q_recall_w, q0_recall = recall_query("W")
    q_recall_wg, _ = recall_query("WG")
    check("_recall uses the variant's query rule too (W and WG differ there before any real fetch)",
          not torch.equal(q_recall_w, q_recall_wg)
          and torch.allclose(q_recall_wg[two_hop_rows], q0_recall[two_hop_rows], atol=1e-7))

    # ------------------------------------------------------------------ 3. the WG guard
    with torch.no_grad():
        with WR.QueryRule(model, "WG", spec) as rule_g:
            guarded = WR.replay(model, batch, rule_g, capture=True)
        calls_g = {int(c["step"]): c for c in guarded["calls"]}
    two_hop, one_hop = two_hop_rows, one_hop_rows
    check("WG: the residual is EXACTLY zero on a LINK question before any real fetch",
          all(float(calls_g[0]["applied"][q]) == 0.0 for q in two_hop)
          and all(not bool(calls_g[0]["h"][q]) for q in two_hop)
          and all(float(calls_w[0]["applied"][q]) > 0.0 for q in two_hop))
    check("WG: one-hop questions keep the residual active at request 1",
          all(bool(calls_g[0]["h"][q]) for q in one_hop)
          and all(float(calls_g[0]["applied"][q]) > 0.0 for q in one_hop)
          and all(torch.equal(calls_g[0]["delta"][q], calls_w[0]["delta"][q]) for q in one_hop))
    opened = [q for q in two_hop if bool(calls_g[1]["h"][q])]
    check("WG: the guard opens after a real fetch and the residual becomes nonzero there",
          opened and all(float(calls_g[1]["applied"][q]) > 0.0 for q in opened)
          and all(bool(guarded["states"][1]["fetched"][q, :-1].any()) for q in opened))
    check("m uses real-card columns only: the guard matches fetched[:, :store.null].any(1)",
          all(bool(calls_g[step]["m"][q])
              == bool(guarded["states"][step]["fetched"][q, :guarded["store_lines"]].any())
              for step in (0, 1, 2) for q in range(len(metas))))

    # a constructed NULL fetch must NOT open the guard
    with torch.no_grad(), WR.QueryRule(model, "WG", spec) as rule_n:
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        mentions = model._mentions(batch)
        episode = model._start(batch, hidden, store, mentions)
        everyone = torch.arange(batch.q_visit.shape[0])
        null_only = torch.full((batch.q_visit.shape[0], 1), store.null, dtype=torch.long)
        model._insert(episode, store, everyone, null_only)
        rule_n.begin_step(0)
        model._step(episode, everyone, 0, store)
        null_call = rule_n.calls[-1]
        counted = episode.count.clone()
    check("a NULL fetch does not open the guard, although episode.count counts it",
          all(not bool(null_call["h"][q]) for q in two_hop)
          and all(float(null_call["applied"][q]) == 0.0 for q in two_hop)
          and int(counted.min()) >= 1 and bool(episode.fetched[:, :store.null].any().item()) is False
          and bool(episode.fetched[:, store.null].all().item()))

    # ------------------------------------------------------------------ 4. the WGC cap
    with torch.no_grad():
        for variant, eta in (("WGC25", 0.25), ("WGC50", 0.50)):
            with WR.QueryRule(model, variant, spec) as rule_c:
                capped = WR.replay(model, batch, rule_c, capture=True)
            calls_c = {int(c["step"]): c for c in capped["calls"]}
            within = all(float(calls_c[s]["applied"][q]) <= eta * float(calls_c[s]["a"][q]) + 1e-6
                         for s in calls_c for q in range(len(metas)))
            equals_gv = all(
                abs(float(calls_c[s]["applied"][q]) - float(calls_c[s]["b"][q])) < 1e-6
                for s in calls_c for q in range(len(metas))
                if bool(calls_c[s]["h"][q]) and float(calls_c[s]["b"][q]) <= eta * float(calls_c[s]["a"][q]))
            check(f"{variant}: ||applied residual|| <= eta*||q0|| always, and equals g*v below the cap",
                  within and equals_gv)
            check(f"{variant}: the cap is applied to g*v, not to v alone",
                  all(float(calls_c[s]["applied"][q]) <= float(calls_c[s]["b"][q]) + 1e-6
                      for s in calls_c for q in range(len(metas)) if bool(calls_c[s]["h"][q])))

    vector = torch.tensor([[3.0, 4.0], [0.0, 0.0], [0.6, 0.8]])
    clipped, factor = WR.clip_to(vector, torch.tensor([[2.0], [1.0], [5.0]]))
    check("clip arithmetic matches hand computation, including the zero vector",
          abs(float(clipped[0].norm()) - 2.0) < 1e-6 and abs(float(factor[0]) - 0.4) < 1e-6
          and float(clipped[1].norm()) == 0.0 and float(factor[1]) == 0.0
          and torch.allclose(clipped[2], vector[2]) and float(factor[2]) == 1.0
          and not bool(torch.isnan(clipped).any()) and not bool(torch.isinf(clipped).any()))

    class _Ep:
        pass

    zero_register = torch.zeros(2, model.config.d_model)
    episode_fake = _Ep()
    episode_fake.rel_token = torch.tensor([spec.relation(0), spec.relation(1)])
    episode_fake.wire_replay_link = torch.tensor([False, False])
    episode_fake.fetched = torch.zeros(2, 5, dtype=torch.bool)
    with torch.no_grad():
        with WR.QueryRule(model, "WGC25", spec) as rule_z:
            model.heads.query.weight.zero_()
            model.heads.query.bias.zero_()
            out_zero = rule_z._query(zero_register, episode_fake, torch.arange(2), step=0)
        with WR.QueryRule(model, "WG", spec) as rule_z2:
            out_wg = rule_z2._query(zero_register, episode_fake, torch.arange(2), step=0)
        model.load_state_dict(torch.load(ckpt, weights_only=False)["state_dict"])
    check("WGC bypasses the addition when ||q0|| is at or below the store normalization epsilon",
          float(out_zero.norm()) == 0.0 and float(out_wg.norm()) > 0.0
          and WR.STORE_NORM_EPS == 1e-12 and P.fingerprint(model) == fingerprint)

    telemetry = WR.Telemetry()
    telemetry.add("x", 1, {"a": 0.0, "b": 0.0, "cos": float("nan"), "g": 0.5, "v_norm": 0.0,
                           "applied": 0.0, "h": True, "m": False, "capped": False, "ask": True,
                           "card_class": "link", "correct_link_history": False})
    telemetry.add("x", 1, {"a": 2.0, "b": 1.0, "cos": 0.5, "g": 0.5, "v_norm": 1.0, "applied": 1.0,
                           "h": True, "m": True, "capped": False, "ask": False,
                           "card_class": "answer", "correct_link_history": True})
    cell = telemetry.report()["x|request1"]
    check("near-zero q0 and tiny residuals are counted, never turned into a finite ratio",
          cell["counts"]["near_zero_q0"] == 1 and cell["counts"]["tiny_residual"] == 1
          and cell["counts"]["ratio_undefined"] == 1 and cell["ratio_b_over_a"]["n"] == 1
          and cell["ratio_b_over_a"]["median"] == 0.5 and cell["cos_q0_gv"]["n"] == 1
          and sum(cell["ratio_b_over_a"]["hist"].values()) >= 1)

    # ------------------------------------------------------------------ 5. transport
    with torch.no_grad():
        relation_tokens = torch.tensor([spec.relation(2), spec.relation(0)])
        projected = model.rel_query(model.embed(relation_tokens))
        d_wire = projected[0] - projected[1]
        gate = 0.37
        q_wire = torch.randn(model.config.key_dim, generator=torch.Generator().manual_seed(5))
        hand = (q_wire + gate * d_wire) / (q_wire + gate * d_wire).norm()
        got, norm, ok = WR._unit(q_wire + gate * d_wire)
    check("uW_transport = normalize(qW_p + g_p*(W_r E[2] - W_r E[p])) matches a hand computation",
          ok and torch.allclose(got, hand, atol=1e-6) and abs(float(got.norm()) - 1.0) < 1e-6)
    tiny_unit, tiny_norm, tiny_ok = WR._unit(torch.zeros(4))
    check("a displacement below 1e-6 is marked undefined instead of being normalised",
          not tiny_ok and tiny_norm == 0.0 and float(tiny_unit.norm()) == 0.0)

    import premonition_ovn_retrieval as R
    plain = R.build("bypass-k1", 1, 0.2)
    plain.eval()
    refuses("a plain checkpoint never receives a wire vector (only variant W is defined for it)",
            lambda: WR.QueryRule(plain, "WG", spec))
    with torch.no_grad(), WR.QueryRule(plain, "W", spec) as rule_p:
        plain_res = WR.replay(plain, batch, rule_p, capture=True)
    check("a plain model records q0 telemetry with a zero residual and no wire insertion",
          plain_res["calls"] and all(not c["residual"] for c in plain_res["calls"])
          and all(float(c["b"].max()) == 0.0 for c in plain_res["calls"])
          and not hasattr(plain, "_shortcut_query"))

    # ------------------------------------------------------------------ 6. a whole checkpoint row
    root = work / "out"
    row = WR.run_checkpoint(ckpt, panels_dir, manifest, spec)
    check("the row carries every required block and the weights are unchanged",
          row["wire"] and row["variants"] == list(WR.VARIANTS)
          and set(row) >= {"telemetry", "cached_state_intervention", "variant_replays", "twins",
                           "transport", "integrity", "reuse_key"}
          and row["integrity"]["weights_unchanged"]
          and row["integrity"]["weights_fingerprint_before"] == fingerprint
          and row["integrity"]["all_pass"])
    check("every variant produced whole-episode results on all three panels",
          all(v in row["variant_replays"] for v in WR.VARIANTS)
          and all(v in row["twins"]["c4"] and v in row["twins"]["c5"] for v in WR.VARIANTS)
          and all(row["twins"]["c4"][v]["units"] == 8 for v in WR.VARIANTS))
    check("labels are stripped: perturbing them changes nothing the model sees",
          row["integrity"]["label_perturbation"]["pass"]
          and row["integrity"]["observation_only_parity"]["pass"]
          and row["integrity"]["episode_isolation"]["pass"])
    check("WG equals W on one-hop questions by construction (no LINK token, so h is always 1)",
          row["variant_replays"]["W"]["answers"]["one_hop_r2_correct"]
          == row["variant_replays"]["WG"]["answers"]["one_hop_r2_correct"])
    check("the transport block reports both p contrasts with their coverage",
          sorted(row["transport"]) == ["0", "1"]
          and all(row["transport"][p]["worlds"] == 8 for p in ("0", "1"))
          and all("unconditional_coverage" in row["transport"][p] for p in ("0", "1")))
    check("the cached-state intervention scored the unchanged query and both caps",
          any(k.endswith("|native") for k in row["cached_state_intervention"])
          and any(k.endswith("|cap0.25") for k in row["cached_state_intervention"])
          and any(k.endswith("|cap0.50") for k in row["cached_state_intervention"]))

    root.mkdir(parents=True, exist_ok=True)
    (root / "rows.jsonl").write_text(json.dumps(row) + "\n")
    key = WR.reuse_key(row["sha256"], WR.sha256_file(panels_dir / "manifest.json"), list(WR.VARIANTS))
    check("an identical reuse key finds the finished row",
          str(Path(ckpt).resolve()) in WR.finished_rows(root / "rows.jsonl", key))
    check("changing the script hash or the panel manifest hash forces a recompute",
          not WR.finished_rows(root / "rows.jsonl", dict(key, script_sha256="different"))
          and not WR.finished_rows(root / "rows.jsonl",
                                   dict(key, panel_manifest_sha256="different"))
          and not WR.finished_rows(root / "rows.jsonl", dict(key, variants=["W"])))
    check("the historical pair-suite directory is unchanged after a full checkpoint replay",
          WR.directory_sha256(WR.HISTORICAL_SUITE) == before_suite)
    tmp.cleanup()
    return CHECKS, started


def table_rules() -> None:
    """Every PASS / FAIL / INCONCLUSIVE branch of the table, on synthetic rows."""
    def synthetic(seed, wire=True, **counts):
        base = {"one_hop_r2": 250, "heldout_native": 200, "c4_joint": 240, "c5_joint": 240,
                "first_link": 250, "endpoint_num": 200, "endpoint_den": 200, "max_ratio": 0.1}
        out = {}
        for variant in (WR.VARIANTS if wire else ("W",)):
            values = dict(base)
            values.update(counts.get(variant, {}))
            out[variant] = values
        row = {"name": f"x-s{seed}-1", "ckpt": f"/x/x-s{seed}-1.pt", "seed": seed, "wire": wire,
               "worlds": WR.WORLDS, "full_size": True, "variants": list(out),
               "integrity": {"all_pass": True},
               "variant_replays": {}, "twins": {"c4": {}, "c5": {}}, "transport": {}}
        for variant, values in out.items():
            row["variant_replays"][variant] = {
                "answers": {"one_hop_r2_correct": values["one_hop_r2"], "one_hop_r2_n": WR.WORLDS,
                            "two_hop_heldout_correct": values["heldout_native"],
                            "two_hop_heldout_n": WR.WORLDS},
                "first_request_correct_link": {"two_hop_heldout_correct_link": values["first_link"]},
                "endpoint_given_correct_link": {
                    "two_hop_heldout_endpoint_at_request2": values["endpoint_num"],
                    "two_hop_heldout_denominator": values["endpoint_den"]},
                "applied_ratio_when_h1": {"n": 100, "max": values["max_ratio"]}}
            row["twins"]["c4"][variant] = {"joint_correct": values["c4_joint"]}
            row["twins"]["c5"][variant] = {"joint_correct": values["c5_joint"]}
        return row

    seeds = list(range(40))
    passers = [1, 3, 6, 9, 10, 11, 12, 13, 15, 17, 18, 23, 24, 25, 27, 31, 34, 35, 36, 37, 39]

    good = {s: synthetic(s, WG={"first_link": 250, "heldout_native": 260}) for s in seeds}
    for s in WR.GUARD_SEEDS:
        good[s] = synthetic(s, W={"heldout_native": 100, "first_link": 0},
                            WG={"heldout_native": 200, "first_link": 250},
                            WGC25={"heldout_native": 200, "first_link": 250},
                            WGC50={"heldout_native": 200, "first_link": 250})
    signal = WR.guard_signal(good, WR.WORLDS)
    check("guard signal PASSes when both seeds clear first-LINK and the 20-point answer gain",
          signal["verdict"] == "PASS"
          and all(signal["seeds"][s]["verdict"] == "PASS" for s in WR.GUARD_SEEDS))
    weak = dict(good)
    weak[14] = synthetic(14, W={"heldout_native": 100}, WG={"heldout_native": 140, "first_link": 250})
    check("guard signal FAILs when the answer gain is below 20 points",
          WR.guard_signal(weak, WR.WORLDS)["verdict"] == "FAIL")
    few = dict(good)
    few[30] = synthetic(30, W={"heldout_native": 100}, WG={"heldout_native": 200, "first_link": 243})
    check("guard signal FAILs when first-LINK is 243/256, one short of the mark",
          WR.guard_signal(few, WR.WORLDS)["verdict"] == "FAIL")
    check("a missing seed or a short panel is INCONCLUSIVE, not a pass",
          WR.guard_signal({s: r for s, r in good.items() if s != 14}, WR.WORLDS)["verdict"]
          == "INCONCLUSIVE"
          and WR.guard_signal(good, 64)["verdict"] == "INCONCLUSIVE")

    check("no-harm PASSes when nothing loses more than 5/256",
          WR._screen(good, passers, "W", "WG", WR.WORLDS)["verdict"] == "PASS")
    harmed = dict(good)
    harmed[passers[0]] = synthetic(passers[0], WG={"c4_joint": 234})
    screen = WR._screen(harmed, passers, "W", "WG", WR.WORLDS)
    check("no-harm FAILs on a 6/256 loss in a single G passer's c4 cell",
          screen["verdict"] == "FAIL" and screen["passer_failures"][passers[0]] == {"c4_joint": 6})
    # every G passer loses exactly the allowed 5/256; the non-passers lose 30 each, so the equally
    # weighted all-40 mean is 16.875/256 and the screen must still fail
    mean_bad = {s: synthetic(s, WG={"heldout_native": 195 if s in passers else 170}) for s in seeds}
    mean_screen = WR._screen(mean_bad, passers, "W", "WG", WR.WORLDS)
    check("no-harm FAILs on the equally weighted all-40 mean even with no single passer over the limit",
          mean_screen["verdict"] == "FAIL" and mean_screen["passer_failures"] == {}
          and mean_screen["mean_failures"] == {"heldout_native": 16.875})
    check("an incomplete roster is INCONCLUSIVE",
          WR._screen({s: good[s] for s in seeds[:10]}, passers, "W", "WG", WR.WORLDS)["verdict"]
          == "INCONCLUSIVE")

    row1 = {s: synthetic(s, WG={"max_ratio": 0.2}) for s in seeds}
    decision = WR.eta_decision(row1, passers, WR.WORLDS)
    check("eta table row 1: every applied ratio <= .25 and .25 eligible -> eta = 0.25",
          decision["decision_row"] == "row 1" and decision["chosen_eta"] == 0.25
          and decision["caps"]["WGC25"]["verdict"] == "ELIGIBLE")
    row2 = {s: synthetic(s, WG={"max_ratio": 0.8}) for s in seeds}
    check("eta table row 2: some ratios exceed .25 but .25 is eligible -> eta = 0.25",
          WR.eta_decision(row2, passers, WR.WORLDS)["decision_row"] == "row 2")
    row3 = {s: synthetic(s, WG={"max_ratio": 0.8}, WGC25={"c5_joint": 230}) for s in seeds}
    third = WR.eta_decision(row3, passers, WR.WORLDS)
    check("eta table row 3: .25 fails and .50 is eligible -> eta = 0.50",
          third["decision_row"] == "row 3" and third["chosen_eta"] == 0.50
          and third["caps"]["WGC25"]["verdict"] == "NOT_ELIGIBLE")
    row4 = {s: synthetic(s, WG={"max_ratio": 0.8}, WGC25={"c5_joint": 230},
                         WGC50={"c4_joint": 230}) for s in seeds}
    fourth = WR.eta_decision(row4, passers, WR.WORLDS)
    check("eta table row 4: neither cap qualifies -> no cap is selected",
          fourth["decision_row"] == "row 4" and fourth["chosen_eta"] == "no cap selected"
          and fourth["verdict"] == "FAIL")
    endpoint_bad = {s: synthetic(s, WGC25={"endpoint_num": 190}, WGC50={"endpoint_num": 190})
                    for s in seeds}
    check("a >5/256 loss in correct-LINK-conditioned endpoint selection blocks eligibility "
          "when there are at least 128 such states",
          WR.eta_decision(endpoint_bad, passers, WR.WORLDS)["caps"]["WGC25"]["verdict"]
          == "NOT_ELIGIBLE")
    thin = {s: synthetic(s, W={"endpoint_den": 100}, WG={"endpoint_den": 100, "endpoint_num": 100},
                         WGC25={"endpoint_den": 100, "endpoint_num": 10},
                         WGC50={"endpoint_den": 100, "endpoint_num": 10}) for s in seeds}
    check("that screen is skipped where fewer than 128 such states exist, and is reported as skipped",
          WR.eta_decision(thin, passers, WR.WORLDS)["caps"]["WGC25"]["verdict"] == "ELIGIBLE"
          and all(v["screened"] is False for v in
                  WR.eta_decision(thin, passers, WR.WORLDS)["caps"]["WGC25"][
                      "correct_link_conditioned_endpoint"].values()))

    plain_row = synthetic(7, wire=False)
    plain_row["transport"] = {
        p: {"matched_subset": 200, "unconditional_coverage": 0.78,
            "C_cos_d1_d2": {"median": 0.95}, "R_norm_ratio": {"median": 1.0},
            "candidates": {
                "u_donor": {"n": 200, "counts": {"ungated_top1_endpoint": 200}},
                "native_u2_heldout": {"n": 200, "counts": {"ask_gated_endpoint": 20,
                                                           "class_asker_same_rel": 10}},
                "u_transport": {"n": 200, "counts": {"ask_gated_endpoint": 120,
                                                     "class_asker_same_rel": 11}}}}
        for p in ("0", "1")}
    plains = {s: json.loads(json.dumps(plain_row)) for s in range(33)}
    for s, r in plains.items():
        r["seed"] = s
    flags = WR.plain_measurement_flags(plains, list(range(33)))
    check("[14] interpretation: 33 strong seeds give the A-first flag",
          flags["flag"] == "A_FIRST" and flags["tally"]["A_first"] == 33)
    weak_native = json.loads(json.dumps(plain_row))
    for p in ("0", "1"):
        weak_native["transport"][p]["R_norm_ratio"] = {"median": 0.1}
        weak_native["transport"][p]["C_cos_d1_d2"] = {"median": -0.1}
        weak_native["transport"][p]["candidates"]["u_transport"]["counts"]["ask_gated_endpoint"] = 25
    keepers = {s: json.loads(json.dumps(weak_native)) for s in range(33)}
    check("[14] interpretation: a good donor with an absent native contrast gives keep-B",
          WR.plain_measurement_flags(keepers, list(range(33)))["flag"] == "KEEP_B")
    poor = json.loads(json.dumps(plain_row))
    for p in ("0", "1"):
        poor["transport"][p]["candidates"]["u_donor"]["counts"]["ungated_top1_endpoint"] = 40
    neither = {s: json.loads(json.dumps(poor)) for s in range(33)}
    check("[14] interpretation: a donor that cannot select the endpoint supports neither mechanism",
          WR.plain_measurement_flags(neither, list(range(33)))["flag"] == "SUPPORT_NEITHER_YET")
    thin_cov = json.loads(json.dumps(plain_row))
    for p in ("0", "1"):
        thin_cov["transport"][p]["matched_subset"] = 40
    low = {s: json.loads(json.dumps(thin_cov)) for s in range(33)}
    check("[14] interpretation: low matched coverage is inconclusive, never A-first",
          WR.plain_measurement_flags(low, list(range(33)))["flag"] == "INCONCLUSIVE")


if __name__ == "__main__":
    total, clock = main()
    table_rules()
    print(f"ALL {CHECKS} CHECKS PASSED in {time.perf_counter() - clock:.1f} s", flush=True)
    raise SystemExit(0)
