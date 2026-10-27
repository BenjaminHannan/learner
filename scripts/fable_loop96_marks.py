#!/usr/bin/env python3
"""Experiment 96 marks L1..L6 (each writes JSON under the exp-96 artifact dir).

  L1  2 red-team-81 reproducers through the loop96 mailbox -> CLARIFY, 0
      writes; same 2 through loop90 -> the wrong write (before).
  L2  all 74 red-team-81 cases (SEQS imported from scripts/fable_redteam81_probe.py,
      never edited) through the loop96 agent AND the loop90 agent: 0 wrong
      writes on loop96; every differing case id listed.
  L3  the 3 red-team-67 BUG reproducers (fix77 F1 pattern, new driver) against
      the loop96 notebook + loop96 reasoner -> all fixed.
  L4  RT79-18 (BUG) + RT79-09/RT79-53 (UNCLEAR site pairs) with the loop96
      thinker class swapped in (new driver; probe file never edited) ->
      fixed / 1 site each, as exp 89 ruled.
  L5  loop90 marks Z1 (60/60) and Z2 (200/200, 0 wrong) re-run with the loop96
      agent unchanged.
  L6  kill -9 + restart seeds 1/2/3 (Z4 procedure) against the loop96 daemon.

Additive only: sealed artifacts are read, never written. Probes run via
imported case functions/builders; nothing outside this file is created.

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop96_marks.py --mark all
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (read-only)
import fable_bench65_notebook_arm as B65  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import fable_loop96_agent as L96  # noqa: E402 (this experiment's agent)
import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_turns84_run as T84  # noqa: E402 (read-only scoring)
from fable_earsguard91 import screen_value  # noqa: E402 (read-only)
from fable_redteam81_probe import SEQS  # noqa: E402 (read-only case list)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-loop96-20260921"
TURNS = ROOT / "data" / "open" / "turns84" / "turns.jsonl"
DATA200 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"

PY90 = [sys.executable, "-B", str(SCRIPTS / "fable_loop90_agent.py")]
PY96 = [sys.executable, "-B", str(SCRIPTS / "fable_loop96_agent.py")]

REPRODUCERS = [
    "Mira's city is Lisbon?",
    "Mira's city is Lisbon and Mira's pet is a cat.",
]


def show_value(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], f"?{value['entity']}")
    return str(value.get("literal"))


# ------------------------------------------------------------ mailbox helpers
def spawn(py, d: Path, cfg: dict, idle_seconds: float = 3600.0):
    d.mkdir(parents=True, exist_ok=True)
    cfg_path = d / "daemon-config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    (d / "STOP").unlink(missing_ok=True)
    (d / "heartbeat.json").unlink(missing_ok=True)
    (d / "daemon_status.json").unlink(missing_ok=True)
    log = open(d / "daemon.stdout.log", "w", encoding="utf-8")  # noqa: PTH123
    proc = subprocess.Popen(py + ["--daemon", "--dir", str(d),
                                  "--config", str(cfg_path),
                                  "--idle-seconds", str(idle_seconds)],
                            stdout=log, stderr=subprocess.STDOUT)
    proc._log = log  # type: ignore[attr-defined]
    deadline = time.time() + 180.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"daemon exited early: {proc.poll()}")
        if (d / "heartbeat.json").exists() and (d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("daemon did not write heartbeat/status in time")


def submit(d: Path, name: str, text: str) -> None:
    tmp = d / "inbox" / f"{name}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text if text.endswith("\n") else text + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, d / "inbox" / f"{name}.txt")


def wait_outbox(d: Path, name: str, timeout: float = 180.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        path = d / "outbox" / f"{name}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    raise RuntimeError(f"no outbox reply for {name} within {timeout}s")


def stop_daemon(proc, d: Path, timeout: float = 15.0) -> None:
    (d / "STOP").write_text("stop\n", encoding="utf-8")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    if proc.poll() is None:
        proc.kill()
        raise RuntimeError("daemon did not stop in time")
    proc._log.close()  # type: ignore[attr-defined]


def daemon_cfg96(state_dir: Path) -> dict:
    import copy
    cfg = copy.deepcopy(L96.DEFAULT_CONFIG96)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = 10 ** 9
    return cfg


def daemon_cfg90(state_dir: Path) -> dict:
    cfg = dict(L90.DEFAULT_CONFIG)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = 10 ** 9
    return cfg


# ------------------------------------------------------------------ L1
def run_l1(out: Path) -> dict:
    t0 = time.time()
    arms = []
    for tag, py, cfg_fn in (("loop90-before", PY90, daemon_cfg90),
                            ("loop96-after", PY96, daemon_cfg96)):
        rows = []
        # One fresh daemon per reproducer: the M1 doorway answers a second
        # teach of the same (subject, relation) with CONFLICT clarify, which
        # would hide the silent wrong write we are demonstrating.
        for i, turn in enumerate(REPRODUCERS):
            state = out / f"l1-daemon-{tag}-r{i + 1:02d}"
            if state.exists():
                shutil.rmtree(state)
            proc = spawn(py, state, cfg_fn(state))
            submit(state, "r", turn)
            wait_outbox(state, "r")
            stop_daemon(proc, state)
            log = [json.loads(line) for line in
                   (state / "daemon.log.jsonl").read_text(encoding="utf-8")
                   .splitlines() if line.strip()]
            turns = [e for e in log if e.get("event") == "turn"]
            assert len(turns) == 1, f"{tag} r{i}: got {len(turns)} entries"
            entry = turns[0]
            nb = C.Notebook(state / "notebook")
            records = entry.get("records", [])
            statuses = [r.get("status", r.get("kind")) for r in records]
            facts = [(fid, nb.facts[fid]["relation"],
                      show_value(nb, nb.facts[fid]["value"]))
                     for fid in entry.get("new_fact_ids", [])
                     if fid in nb.facts]
            entities = dict(entry.get("new_entities", {}))
            rows.append({"turn": turn, "reply": entry.get("reply"),
                         "statuses": statuses,
                         "new_facts": [[fid, rel, val]
                                       for fid, rel, val in facts],
                         "new_entities": entities})
        arms.append({"arm": tag, "rows": rows})
    before, after = arms
    l1_pass = True
    for b, a in zip(before["rows"], after["rows"]):
        # Before: exactly one new FACT row and its value has a corrupt shape
        # (a teach also creates the person entity, which is expected).
        b_ok = (len(b["new_facts"]) == 1
                and screen_value(b["new_facts"][0][2]) is not None)
        a_ok = (a["statuses"] == ["clarify"] and not a["new_facts"]
                and not a["new_entities"])
        b["before_shows_wrong_write"] = bool(b_ok)
        a["clarify_no_write"] = bool(a_ok)
        l1_pass = l1_pass and b_ok and a_ok
    rep = {"mark": "L1", "before": before, "after": after,
           "pass": bool(l1_pass), "seconds": round(time.time() - t0, 1)}
    (out / "l1-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"L1: before_writes={[len(r['new_facts']) for r in before['rows']]} "
          f"after={[(r['statuses'], len(r['new_facts'])) for r in after['rows']]} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ L2
def taught_facts(loop) -> int:
    return sum(1 for e in loop.nb.events
               if e["kind"] == "FACT" and e.get("source") == "taught")


def new_taught_literals(loop, before_ids: set) -> list[str]:
    rows = []
    for fid, f in loop.nb.facts.items():
        if fid in before_ids or f.get("source") != "taught":
            continue
        val = f.get("value", {})
        if isinstance(val, dict) and "entity" in val:
            rows.append(f"@{loop.nb.entities.get(val['entity'], val['entity'])}")
        else:
            rows.append(str(val.get("literal") if isinstance(val, dict) else val))
    return rows


def run_seq(factory, steps) -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="loop96_l2_") as folder:
        import copy
        loop = factory(folder)
        for st in steps:
            if st["turn"] == "__SETUP_SECOND_MIRA__":
                loop.nb.new_entity("setup-second-mira", "Mira")
                rows.append({"setup": True, "taught_delta": 0,
                             "new_literals": []})
                continue
            before_n = taught_facts(loop)
            before_ids = set(loop.nb.facts.keys())
            reply = " ".join(loop.turn(st["turn"]))
            delta = taught_facts(loop) - before_n
            statuses = (loop.experience[-1]["statuses"] if loop.experience
                        else [])
            rows.append({"setup": False, "turn": st["turn"],
                         "reply": reply, "statuses": statuses,
                         "taught_delta": delta,
                         "new_literals": new_taught_literals(loop, before_ids),
                         "nowrite": bool(st.get("nowrite"))})
    return rows


def fact90(folder) -> L90.Loop90AgentLoop:
    import copy
    cfg = copy.deepcopy(L90.DEFAULT_CONFIG)
    cfg["state_dir"] = folder
    cfg["sleep_threshold"] = 10 ** 9
    return L90.build_agent(cfg)


def fact96(folder) -> L90.Loop90AgentLoop:
    import copy
    cfg = copy.deepcopy(L96.DEFAULT_CONFIG96)
    cfg["state_dir"] = folder
    cfg["sleep_threshold"] = 10 ** 9
    return L96.build_agent96(cfg)


def run_l2(out: Path) -> dict:
    t0 = time.time()
    cases = []
    for seq_id, _desc, steps in SEQS:
        base = run_seq(fact90, steps)
        guarded = run_seq(fact96, steps)
        assert len(base) == len(guarded) == len(steps)
        for i, st in enumerate(steps):
            cid = f"{seq_id}-{i + 1:02d}"
            b, g = base[i], guarded[i]
            if st["turn"] == "__SETUP_SECOND_MIRA__":
                cases.append({"id": cid, "turn": st["turn"], "setup": True,
                              "changed": False, "wrong_write": False,
                              "wrong_detail": ""})
                continue
            changed = (b["reply"] != g["reply"]
                       or b["statuses"] != g["statuses"]
                       or b["taught_delta"] != g["taught_delta"])
            wrong_detail = []
            if g["nowrite"] and g["taught_delta"] > 0:
                wrong_detail.append(
                    f"wrote {g['taught_delta']} FACT(s) on a nowrite turn")
            for lit in g["new_literals"]:
                if lit.startswith("@"):
                    continue
                why = screen_value(lit)
                if why is not None:
                    wrong_detail.append(f"value {lit[:80]!r}: {why}")
            cases.append({"id": cid, "turn": st["turn"], "setup": False,
                          "base_reply": b["reply"],
                          "base_statuses": b["statuses"],
                          "base_delta": b["taught_delta"],
                          "loop96_reply": g["reply"],
                          "loop96_statuses": g["statuses"],
                          "loop96_delta": g["taught_delta"],
                          "changed": changed,
                          "wrong_write": bool(wrong_detail),
                          "wrong_detail": "; ".join(wrong_detail)})
    real = [c for c in cases if not c.get("setup")]
    changed = [c["id"] for c in real if c["changed"]]
    wrong = [c["id"] for c in real if c["wrong_write"]]
    rep = {"mark": "L2", "n": len(cases), "real": len(real),
           "changed_vs_loop90": changed, "wrong_writes": wrong,
           "pass": len(wrong) == 0,
           "seconds": round(time.time() - t0, 1), "cases": cases}
    (out / "l2-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    (out / "l2-cases.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cases) + "\n",
        encoding="utf-8")
    print(f"L2: n={len(cases)} changed={len(changed)} "
          f"wrong={len(wrong)} -> {'PASS' if rep['pass'] else 'FAIL'}")
    print(f"  changed={','.join(changed) or 'none'}")
    return rep


# ------------------------------------------------------------------ L3
def run_l3(out: Path) -> dict:
    t0 = time.time()
    import fable_fix77_core as F77  # noqa: E402 (read-only)
    from fable_thought49_schema import (  # noqa: E402 (read-only)
        Provenance, Qualifier, ThoughtV2, Value)
    rows = []

    with tempfile.TemporaryDirectory(prefix="loop96_l3r1_") as tmp:
        import copy
        cfg = copy.deepcopy(L96.DEFAULT_CONFIG96)
        cfg["state_dir"] = tmp
        loop = L96.build_agent96(cfg)
        tnb, nb = loop.nb, loop.nb.nb
        nb.declare_relation("r", "friend", False)
        t = nb.new_entity("e1", "Tom").detail["entity_id"]
        a = nb.new_entity("e2", "Ana").detail["entity_id"]
        m = nb.new_entity("e3", "Mira").detail["entity_id"]

        def mk(v, qs=()):
            return tnb.add_thought(ThoughtV2(
                subject=t, relation="friend", value=Value.of_entity(v),
                provenance=Provenance(document="d", sentence="s",
                                      claimed_by="taught"),
                qualifiers=qs, source="taught"), event_id="q" + v)

        assert mk(a).status == C.SAVED
        assert mk(m, (Qualifier("when", Value.of_date("2019")),)).status == C.SAVED
        gated = tnb.ask("Tom", ["friend"],
                        qualifiers={"when": "2019"}).detail.get("answer")
        r77 = loop.reasoner.answer(
            {"name": "Tom", "relations": ["friend"],
             "qualifiers": {"when": "2019"}}, nb)["fields"].get("answer")
        rows.append({"id": "R1", "gated": gated, "r77": r77,
                     "pass": gated == "Ana" == r77})

    with tempfile.TemporaryDirectory(prefix="loop96_l3r2_") as tmp:
        import copy
        cfg = copy.deepcopy(L96.DEFAULT_CONFIG96)
        cfg["state_dir"] = tmp
        loop = L96.build_agent96(cfg)
        tnb, nb = loop.nb, loop.nb.nb
        e = nb.new_entity("e", "Mira").detail["entity_id"]
        r = tnb.add_thought(ThoughtV2(
            subject=e, relation="city", value=Value.of_text("Lisbon"),
            provenance=Provenance(document="d", sentence="s",
                                  claimed_by="taught"),
            qualifiers=(Qualifier("open", Value.of_boolean(True)),),
            source="taught"), event_id="q")
        assert r.status == C.SAVED, r
        s_gated = tnb.ask("Mira", ["city"],
                          qualifiers={"open": True}).status
        rec = loop.reasoner.answer(
            {"name": "Mira", "relations": ["city"],
             "qualifiers": {"open": True}}, nb)
        ok = s_gated == C.OK and rec["status"] == C.OK
        spells = []
        for q in ({"open": "true"}, {"open": "TRUE"}, {"open": " True "}):
            got = loop.reasoner.answer(
                {"name": "Mira", "relations": ["city"],
                 "qualifiers": q}, nb)["status"]
            spells.append(got)
        got_false = loop.reasoner.answer(
            {"name": "Mira", "relations": ["city"],
             "qualifiers": {"open": False}}, nb)["status"]
        rows.append({"id": "R2", "gated": s_gated, "r77": rec["status"],
                     "spells": spells, "false": got_false,
                     "pass": bool(ok) and all(s == C.OK for s in spells)
                     and got_false == C.MISSING_FACT})

    with tempfile.TemporaryDirectory(prefix="loop96_l3r3_") as tmp:
        d = Path(tmp) / "nb"
        nb = L90.Loop90Notebook(d)  # the actual loop notebook class
        nb.declare_relation("r", "city", True)
        e = nb.new_entity("e", "Mira").detail["entity_id"]
        nb.assert_fact("f", "listening", "taught", e, "city",
                       {"literal": "Lisbon"})
        nb.advance_seal()
        F77.open_verified(d)  # seal the trusted state first
        p = d / "events.jsonl"
        lines = [ln for ln in p.read_text(encoding="utf-8").split("\n")
                 if ln.strip()]
        rec = json.loads(lines[-1])
        rec["value"] = {"literal": "HACKED"}
        lines[-1] = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            F77.open_verified(d)
            via_loader = "SILENT"
        except C.LogCorrupt as exc:
            via_loader = f"LogCorrupt: {exc}"
        try:
            L90.Loop90Notebook(d)
            via_loopnb = "SILENT"
        except C.LogCorrupt as exc:
            via_loopnb = f"LogCorrupt: {exc}"
        rows.append({"id": "R3", "via_open_verified": via_loader[:120],
                     "via_loop_notebook": via_loopnb[:120],
                     "pass": via_loader.startswith("LogCorrupt")
                     and via_loopnb.startswith("LogCorrupt")})

    rep = {"mark": "L3", "reproducers": rows,
           "pass": all(r["pass"] for r in rows) and len(rows) == 3,
           "seconds": round(time.time() - t0, 1)}
    (out / "l3-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"L3: {'/'.join(r['id'] + '=' + ('PASS' if r['pass'] else 'FAIL') for r in rows)} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ L4
def run_l4(out: Path) -> dict:
    t0 = time.time()
    import urllib.request
    real_urlopen = urllib.request.urlopen
    import fable_redteam79_probe as P79  # noqa: E402 (never edited)
    import fable_thinking_m2 as T  # noqa: E402 (read-only)
    try:
        with tempfile.TemporaryDirectory(prefix="loop96_l4_") as tmp:
            import copy
            cfg = copy.deepcopy(L96.DEFAULT_CONFIG96)
            cfg["state_dir"] = tmp
            probe_loop = L96.build_agent96(cfg)
            thinker_module = probe_loop.parts90.get("thinker_module")
            thinker_cls = type(probe_loop.parts90["thinker"].thinking) \
                if hasattr(probe_loop.parts90.get("thinker"), "thinking") \
                else None
            if thinker_cls is None:
                import fable_webfix89_thinking as W89mod  # noqa: E402
                thinker_cls = W89mod.QuarantinedThinking89
            want = {"rt09": None, "rt18": None, "rt53": None}
            builders = {"rt09": P79.rt09_domain_plus_subdomain,
                        "rt18": P79.rt18_none_value,
                        "rt53": P79.rt53_port_and_trailing_dot}
            P79.ROOT = Path(tmp) / "p79scratch"
            P79.ROOT.mkdir(parents=True, exist_ok=True)
            rows = []
            ORIGINAL = T.Thinking
            T.Thinking = thinker_cls  # runtime swap only, restored below
            try:
                for key, builder in builders.items():
                    cid, title, expected, fn = builder()
                    try:
                        observed, verdict, note = fn()
                    except Exception as exc:  # noqa: BLE001
                        observed, verdict, note = (
                            f"CRASH {type(exc).__name__}: {exc}", "BUG",
                            "crashed")
                    rows.append({"id": cid, "title": title,
                                 "observed": observed, "verdict": verdict,
                                 "note": note})
            finally:
                T.Thinking = ORIGINAL
            # X2-style site counts with the SAME class the loop96 wires.
            import fable_notebook_contract as Cn  # noqa: E402
            site_rows = []
            for tag, urls in (
                    ("RT79-09-subdomain",
                     ["https://a.example.org/x", "https://sub.a.example.org/y"]),
                    ("RT79-53-port",
                     ["https://a.example.org/x", "https://a.example.org:8080/y"])):
                sdir = Path(tmp) / tag
                sdir.mkdir(parents=True)
                nb = Cn.Notebook(str(sdir))
                claims = [{"subject": "Phobos", "relation": "orbits",
                           "value": "Mars", "url": u,
                           "quote": "Phobos orbits Mars indeed."} for u in urls]
                site = {u: "Phobos orbits Mars indeed." for u in urls}
                mind = thinker_cls(nb, T.FakeSearcher({"t": claims}),
                                   T.FakeFetcher(site))
                mind.assign("t")
                mind.think_once()
                subj = nb.resolve("Phobos").detail["entity_id"]
                sup = mind._support(subj, "orbits")
                sites = sorted({s for v in sup.values()
                                for s in v["domains"]})
                nv = sum(1 for f in nb.facts.values()
                         if f["source"] == "web-verified")
                site_rows.append({"pair": tag, "sites": sites,
                                  "n_sites": len(sites),
                                  "web_verified": nv})
    finally:
        urllib.request.urlopen = real_urlopen
    by_id = {r["id"]: r for r in rows}
    l4_pass = (by_id["RT79-18"]["verdict"] == "OK"
               and by_id["RT79-09"]["verdict"] == "OK"
               and by_id["RT79-53"]["verdict"] == "OK"
               and all(s["n_sites"] == 1 and s["web_verified"] == 0
                       for s in site_rows)
               and thinker_module == "fable_webfix89_thinking")
    rep = {"mark": "L4", "thinker_module": thinker_module,
           "thinker_class": getattr(thinker_cls, "__name__", str(thinker_cls)),
           "cases": rows, "site_counts": site_rows,
           "pass": bool(l4_pass), "seconds": round(time.time() - t0, 1)}
    (out / "l4-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"L4: thinker={rep['thinker_class']} "
          f"{[(r['id'], r['verdict']) for r in rows]} "
          f"sites={[(s['pair'], s['n_sites']) for s in site_rows]} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ L5 (Z1+Z2 with loop96)
def run_l5z1(out: Path) -> dict:
    t0 = time.time()
    rows = [json.loads(line) for line in TURNS.read_text(encoding="utf-8")
            .splitlines() if line.strip()]
    assert [r["n"] for r in rows] == list(range(1, 61))
    state = out / "l5z1-daemon"
    if state.exists():
        shutil.rmtree(state)
    proc = spawn(PY96, state, daemon_cfg96(state))
    for row in rows:
        submit(state, f"t{row['n']:03d}", row["turn"])
        wait_outbox(state, f"t{row['n']:03d}")
    stop_daemon(proc, state)
    log = [json.loads(line) for line in
           (state / "daemon.log.jsonl").read_text(encoding="utf-8")
           .splitlines() if line.strip()]
    turns = [e for e in log if e.get("event") == "turn"]
    assert len(turns) == 60, f"got {len(turns)} turn entries"
    nb = C.Notebook(state / "notebook")
    per_turn, wrong_total, match_total = [], 0, 0
    for row, entry in zip(rows, turns):
        n, exp = row["n"], row["expected"]
        records = entry.get("records", [])
        obs = T84.observed_status(records[0]) if len(records) == 1 else (
            "MULTI_RECORD" if records else "NO_RECORD")
        status_match = obs == exp["status"]
        wrong, detail = 0, []
        facts = [nb.facts[fid] for fid in entry.get("new_fact_ids", [])
                 if fid in nb.facts]
        entities = dict(entry.get("new_entities", {}))
        if exp["status"] == "SAVED":
            want = exp["write"]
            if not facts:
                wrong += 1
                detail.append("expected a write, no FACT row")
            for fact in facts:
                got = (nb.entities.get(fact["subject"], "?"),
                       fact["relation"], show_value(nb, fact["value"]))
                if got != (want["subject"], want["relation"], want["value"]):
                    wrong += 1
                    detail.append(f"FACT {fact['fact_id']}: got {got}")
            for eid, name in entities.items():
                if name not in set(exp.get("new_entities", [])):
                    wrong += 1
                    detail.append(f"unexpected ENTITY {eid}={name!r}")
        else:
            for fact in facts:
                wrong += 1
                detail.append(f"unexpected FACT {fact['fact_id']}")
            for eid, name in entities.items():
                wrong += 1
                detail.append(f"unexpected ENTITY {eid}={name!r}")
        wrong_total += wrong
        match_total += bool(status_match and not wrong)
        per_turn.append({"n": n, "turn": row["turn"],
                         "expected": exp["status"], "observed": obs,
                         "status_match": bool(status_match), "wrong": wrong,
                         "wrong_detail": detail,
                         "ears_stage": entry.get("ears_stage"),
                         "ears_score": entry.get("ears_score")})
    rep = {"mark": "L5-Z1", "turns": 60,
           "status_match": sum(t["status_match"] for t in per_turn),
           "wrong_writes": wrong_total,
           "all_match_no_wrong": match_total,
           "pass": wrong_total == 0 and match_total == 60,
           "seconds": round(time.time() - t0, 1), "per_turn": per_turn}
    (out / "l5z1-report.json").write_text(json.dumps(rep, indent=1),
                                          encoding="utf-8")
    print(f"L5-Z1: match={rep['status_match']}/60 wrong={wrong_total} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


def run_l5z2(out: Path) -> dict:
    t0 = time.time()
    import copy
    items = B65.load_items(DATA200)
    assert len(items) == 200, len(items)
    scratch = out / "l5z2-items"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    rows, wrong_total = [], 0
    stage_counts: dict[str, int] = {}
    for item in items:
        sdir = scratch / item["id"]
        cfg = copy.deepcopy(L96.DEFAULT_CONFIG96)
        cfg["state_dir"] = str(sdir)
        cfg["sleep_threshold"] = 10 ** 9
        loop = L96.build_agent96(cfg)
        teach_wrong = 0
        pending_hit = None
        for sent in [t["sentence_en"] for t in item["taught"]]:
            before = set(loop.nb.facts)
            loop.turn(sent)
            if loop.listening.pending is not None:
                pending_hit = sent
            new = [loop.nb.facts[f] for f in set(loop.nb.facts) - before]
            if len(new) > 1:
                teach_wrong += 1
            for fact in new:
                if fact.get("source") != "taught":
                    teach_wrong += 1
            key = getattr(loop.ears, "last_stage", "?")
            stage_counts[key] = stage_counts.get(key, 0) + 1
        q_before = set(loop.nb.facts)
        said = loop.turn(item["question"])
        q_new = [f for f in set(loop.nb.facts) - q_before]
        recs = list(loop.last_records) if hasattr(loop, "last_records") else []
        rec = recs[0] if recs else {}
        status = rec.get("status", "NO_RECORD")
        if q_new:
            teach_wrong += len(q_new)
        row = {"id": item["id"], "type": item["type"],
               "expected": item["expected"], "status": status,
               "teach_wrong": teach_wrong, "pending_hit": pending_hit,
               "question_wrote": len(q_new), "said": said}
        if rec.get("status") == C.OK:
            row["answer"] = rec.get("fields", {}).get("answer")
        if item["expected"] == "abstain":
            row["verdict"] = ("abstain_ok" if status in B65.ABSTAIN
                              else ("WRONG" if status == C.OK else "MISS"))
        else:
            golds = {B65.norm(g) for g in
                     item["gold"] + item.get("gold_aliases", [])}
            row["verdict"] = ("correct" if status == C.OK and B65.norm(
                rec.get("fields", {}).get("answer", "")) in golds
                else ("WRONG" if status == C.OK else "MISS"))
        if teach_wrong or pending_hit:
            row["verdict"] = ("WRONG" if row["verdict"] == "correct"
                              else row["verdict"]) if teach_wrong else \
                row["verdict"]
            if teach_wrong and row["verdict"] != "WRONG":
                row["verdict"] = "WRITE_FAULT"
        rows.append(row)
        wrong_total += (row["verdict"] == "WRONG") + (teach_wrong > 0)
    table = B65.score([{**r, "contract_status": r["status"],
                        "teach_notes": [], "ms": 0.0} for r in rows])
    rep = {"mark": "L5-Z2", "items": len(rows),
           "verdicts": {v: sum(1 for r in rows if r["verdict"] == v)
                        for v in ("correct", "abstain_ok", "WRONG", "MISS",
                                  "WRITE_FAULT")},
           "table": table, "ears_stages": stage_counts,
           "pass": all(r["verdict"] in ("correct", "abstain_ok")
                       for r in rows),
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "l5z2-report.json").write_text(json.dumps(rep, indent=1),
                                          encoding="utf-8")
    print(f"L5-Z2: {rep['verdicts']} stages={stage_counts} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ L6
def run_l6(out: Path) -> dict:
    from fable_daemon74_selftest import (  # noqa: E402 (helpers reused)
        check_answer, fact_name, fact_value)
    t0 = time.time()
    import copy
    per_seed = []
    for seed in (1, 2, 3):
        d = out / f"l6-daemon-s{seed}"
        if d.exists():
            shutil.rmtree(d)
        cfg = copy.deepcopy(L96.DEFAULT_CONFIG96)
        cfg["sleep_threshold"] = 10 ** 9
        proc = spawn(PY96, d, {**cfg, "state_dir": str(d)})
        names = [fact_name("D2", seed, i) for i in range(200)]
        values = [fact_value("D2", seed, i) for i in range(200)]
        for i, (name, value) in enumerate(zip(names, values)):
            submit(d, f"teach-{i:03d}", f"{name}'s city is {value}.")
        deadline = time.time() + 180.0
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("daemon died before the kill")
            if len(list((d / "outbox").glob("teach-*.txt"))) >= 5:
                break
            time.sleep(0.005)
        replied = sorted(p.name for p in (d / "outbox").glob("teach-*.txt"))
        proc.kill()  # kill -9 equivalent: no cleanup, torn tails possible
        proc.wait()
        proc._log.close()  # type: ignore[attr-defined]
        proc = spawn(PY96, d, {**cfg, "state_dir": str(d)})
        status = json.loads((d / "daemon_status.json").read_text(
            encoding="utf-8"))
        for i in range(200):
            wait_outbox(d, f"teach-{i:03d}")
        for i, name in enumerate(names):
            submit(d, f"ask-{i:03d}", f"What is {name}'s city?")
        correct = wrong = unanswered = 0
        for i, value in enumerate(values):
            verdict = check_answer(wait_outbox(d, f"ask-{i:03d}"), value,
                                   values)
            correct += verdict == "correct"
            wrong += verdict == "wrong"
            unanswered += verdict == "unanswered"
        stop_daemon(proc, d)
        nb = C.Notebook(d / "notebook")
        dupes = 0
        for name, value in zip(names, values):
            found = nb.resolve(name)
            assert found.status == C.OK, f"{name} missing after restart"
            rows = [r for r in nb.current(found.detail["entity_id"], "city")
                    if r["source"] == "taught"]
            same = [r for r in nb.facts.values()
                    if r.get("subject") == found.detail["entity_id"]
                    and r.get("relation") == "city"
                    and r.get("source") == "taught"
                    and r.get("value") == {"literal": value}]
            if len(rows) != 1 or len(same) != 1:
                dupes += 1
        chain_ok = (not nb.torn_tail) and status.get("boot_ok") is True
        torn_reported = status.get("torn_tail_found_and_repaired") is True or (
            d / "notebook" / "torn-tail.txt").exists()
        passed = ((chain_ok or torn_reported) and correct == 200
                  and wrong == 0 and dupes == 0)
        per_seed.append({"seed": seed, "pass": passed, "correct": correct,
                         "wrong": wrong, "unanswered": unanswered,
                         "dupes": dupes,
                         "replied_before_kill": len(replied),
                         "chain_ok": chain_ok,
                         "torn_reported": torn_reported})
        print(f"L6 seed {seed}: correct={correct}/200 wrong={wrong} "
              f"dupes={dupes} chain_ok={chain_ok} "
              f"torn_reported={torn_reported} -> "
              f"{'PASS' if passed else 'FAIL'}")
    rep = {"mark": "L6", "per_seed": per_seed,
           "pass": all(s["pass"] for s in per_seed),
           "seconds": round(time.time() - t0, 1)}
    (out / "l6-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    return rep


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 96 marks")
    parser.add_argument("--mark", choices=("l1", "l2", "l3", "l4", "l5z1",
                                           "l5z2", "l6", "all"),
                        required=True)
    parser.add_argument("--out", default=str(ART))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runners = {"l1": run_l1, "l2": run_l2, "l3": run_l3, "l4": run_l4,
               "l5z1": run_l5z1, "l5z2": run_l5z2, "l6": run_l6}
    selected = list(runners) if args.mark == "all" else [args.mark]
    oks = []
    for name in selected:
        rep = runners[name](out)
        oks.append(bool(rep["pass"]))
    print("MARKS96", "PASS" if all(oks) else "FAIL")
    return 0 if all(oks) else 1


if __name__ == "__main__":
    sys.exit(main())
