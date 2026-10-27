#!/usr/bin/env python3
"""Experiment 90 marks Z1..Z5 (each writes JSON under the exp-90 artifact dir).

  Z1  60-turn acceptance file through the Loop90 mailbox: 0 wrong writes,
      every status matching the contract (scored from daemon-log records).
  Z2  Fable-Edit-200 English arm through the loop notebook (bench73 ears over
      the loop's notebook + Reasoner77): every item in its expected cell,
      0 WRONG.
  Z3  69 red-team core + 56 web cases re-run by import (results land in the
      exp-90 dir, never in the sealed sezures); verdicts must match the sealed
      baselines with zero new BUGs; plus doctrinal checks against the actual
      loop90 notebook/thinker.
  Z4  kill-9 + restart keeps the chain (daemon74 selftest D2 helpers reused
      against the Loop90 daemon), seeds 1/2/3 reported separately.
  Z5  --config JSON documents every plug point; a loop built from that file
      answers a smoke turn.

Additive only: sealed artifacts are read, never written. Probes run via
imported case functions; their writers are redirected to the exp-90 dir.

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop90_marks.py --mark z1
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
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402
import fable_bench65_notebook_arm as B65  # noqa: E402
import fable_bench73_english_arm as B73  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402
import fable_notebook_contract as C  # noqa: E402
import fable_turns84_run as T84  # noqa: E402 (scoring helpers, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-loop90-20260921"
TURNS = ROOT / "data" / "open" / "turns84" / "turns.jsonl"
DATA200 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"

PY = [sys.executable, "-B", str(SCRIPTS / "fable_loop90_agent.py")]


def show_value(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], f"?{value['entity']}")
    return str(value.get("literal"))


# ------------------------------------------------------------------ Z1
def spawn_loop90(d: Path, cfg: dict, idle_seconds: float = 3600.0):
    d.mkdir(parents=True, exist_ok=True)
    cfg_path = d / "loop90-config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    (d / "STOP").unlink(missing_ok=True)
    (d / "heartbeat.json").unlink(missing_ok=True)
    (d / "daemon_status.json").unlink(missing_ok=True)
    log = open(d / "daemon.stdout.log", "w", encoding="utf-8")  # noqa: PTH123
    proc = subprocess.Popen(PY + ["--daemon", "--dir", str(d),
                                  "--config", str(cfg_path),
                                  "--idle-seconds", str(idle_seconds)],
                            stdout=log, stderr=subprocess.STDOUT)
    proc._log = log  # type: ignore[attr-defined]
    deadline = time.time() + 120.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"loop90 daemon exited early: {proc.poll()}")
        if (d / "heartbeat.json").exists() and (d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("loop90 daemon did not write heartbeat/status in time")


def submit(d: Path, name: str, text: str) -> None:
    tmp = d / "inbox" / f"{name}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text if text.endswith("\n") else text + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, d / "inbox" / f"{name}.txt")


def wait_outbox(d: Path, name: str, timeout: float = 120.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        path = d / "outbox" / f"{name}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    raise RuntimeError(f"no outbox reply for {name} within {timeout}s")


def stop_daemon(proc, d: Path, timeout: float = 10.0) -> float:
    t0 = time.time()
    (d / "STOP").write_text("stop\n", encoding="utf-8")
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    dt = time.time() - t0
    if proc.poll() is None:
        proc.kill()
        raise RuntimeError("daemon did not stop in time")
    proc._log.close()  # type: ignore[attr-defined]
    return dt


def z1_default_cfg(state_dir: Path) -> dict:
    cfg = dict(L90.DEFAULT_CONFIG)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = 10 ** 9  # listening-only acceptance, as exp 84
    return cfg


def run_z1(out: Path) -> dict:
    t0 = time.time()
    rows = [json.loads(line) for line in TURNS.read_text(encoding="utf-8")
            .splitlines() if line.strip()]
    assert [r["n"] for r in rows] == list(range(1, 61))
    state = out / "z1-daemon"
    if state.exists():
        shutil.rmtree(state)
    proc = spawn_loop90(state, z1_default_cfg(state))
    for row in rows:
        submit(state, f"t{row['n']:03d}", row["turn"])
        wait_outbox(state, f"t{row['n']:03d}")
    stop_daemon(proc, state)
    log = [json.loads(line) for line in
           (state / "daemon.log.jsonl").read_text(encoding="utf-8")
           .splitlines() if line.strip()]
    turns = [e for e in log if e.get("event") == "turn"]
    assert len(turns) == 60, f"got {len(turns)} turn entries"

    nb = C.Notebook(state / "notebook")  # read-only open for the audit
    per_turn, wrong_total, match_total = [], 0, 0
    for row, entry in zip(rows, turns):
        n, exp = row["n"], row["expected"]
        records = entry.get("records", [])
        obs = T84.observed_status(records[0]) if len(records) == 1 else (
            "MULTI_RECORD" if records else "NO_RECORD")
        status_match = obs == exp["status"]
        answer_match = None
        if exp["status"] == "OK":
            answer_match = (records[0].get("kind") == "answer"
                            and records[0].get("fields", {}).get("answer")
                            == exp["answer"]) if records else False
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
        per_turn.append({"n": n, "turn": row["turn"], "kind": row["kind"],
                         "expected": exp["status"], "observed": obs,
                         "status_match": bool(status_match),
                         "answer_match": answer_match,
                         "wrong": wrong, "wrong_detail": detail,
                         "ears_stage": entry.get("ears_stage"),
                         "ears_score": entry.get("ears_score"),
                         "said": entry.get("reply")})
    status = json.loads((state / "daemon_status.json").read_text(
        encoding="utf-8"))
    rep = {"mark": "Z1", "turns": 60, "status_match": sum(
        t["status_match"] for t in per_turn), "wrong_writes": wrong_total,
           "all_match_no_wrong": match_total,
           "pass": wrong_total == 0 and match_total == 60,
           "boot_ok": status.get("boot_ok"),
           "seconds": round(time.time() - t0, 1), "per_turn": per_turn}
    (out / "z1-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"Z1: match={rep['status_match']}/60 wrong={wrong_total} "
          f"boot_ok={rep['boot_ok']} {rep['seconds']}s -> "
          f"{'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ Z2
def z2_cfg(state_dir: Path) -> dict:
    cfg = dict(L90.DEFAULT_CONFIG)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = 10 ** 9
    return cfg


def run_z2(out: Path) -> dict:
    t0 = time.time()
    items = B65.load_items(DATA200)
    assert len(items) == 200, len(items)
    scratch = out / "z2-items"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    rows, wrong_total = [], 0
    stage_counts: dict[str, int] = {}
    for item in items:
        sdir = scratch / item["id"]
        loop = L90.build_agent(z2_cfg(sdir))
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
            stage_counts[loop.ears.last_stage] = \
                stage_counts.get(loop.ears.last_stage, 0) + 1
        q_before = set(loop.nb.facts)
        said = loop.turn(item["question"])
        q_new = [f for f in set(loop.nb.facts) - q_before]
        recs = list(loop.last_records) if hasattr(loop, "last_records") else []
        rec = recs[0] if recs else {}
        status = rec.get("status", "NO_RECORD")
        if q_new:
            teach_wrong += len(q_new)  # a question must never write
        row = {"id": item["id"], "type": item["type"],
               "expected": item["expected"], "status": status,
               "teach_wrong": teach_wrong,
               "pending_hit": pending_hit,
               "question_wrote": len(q_new),
               "said": said}
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
    rep = {"mark": "Z2", "items": len(rows),
           "verdicts": {v: sum(1 for r in rows if r["verdict"] == v)
                        for v in ("correct", "abstain_ok", "WRONG", "MISS",
                                  "WRITE_FAULT")},
           "wrong_or_fault": sum(1 for r in rows if r["verdict"] in (
               "WRONG", "WRITE_FAULT")),
           "table": table, "ears_stages": stage_counts,
           "pass": all(r["verdict"] in ("correct", "abstain_ok")
                       for r in rows),
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "z2-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    (out / "z2-rows.jsonl").write_text("\n".join(
        json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    print(f"Z2: {rep['verdicts']} stages={stage_counts} "
          f"{rep['seconds']}s -> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ Z3
def run_z3(out: Path) -> dict:
    t0 = time.time()
    import fable_redteam67_probe as P67  # noqa: E402 (read-only; never edited)
    core = []
    for cid, title, expected, fn in P67.CASES:
        try:
            observed, verdict, note = fn()
        except Exception as exc:  # noqa: BLE001 -- a crash is itself a finding
            observed, verdict, note = (f"CRASH {type(exc).__name__}: {exc}",
                                       "BUG", "crashed")
        core.append({"id": cid, "title": title, "expected": expected,
                     "observed": observed, "verdict": verdict, "note": note})
    sealed67 = json.loads((ROOT / "artifacts" / "fable-redteam67-20260921"
                           / "probe-results.json").read_text(
        encoding="utf-8"))
    base67 = {c["id"]: c["verdict"] for c in sealed67["cases"]}

    real_urlopen = urllib.request.urlopen
    import fable_redteam79_probe as P79  # noqa: E402 (firewalls urllib)
    try:
        web = []
        for builder in P79.CASES:
            cid, title, expected, fn = builder()
            try:
                observed, verdict, note = fn()
            except Exception as exc:  # noqa: BLE001
                observed, verdict, note = (
                    f"CRASH {type(exc).__name__}: {exc}", "BUG", "crashed")
            web.append({"id": cid, "title": title, "expected": expected,
                        "observed": observed, "verdict": verdict,
                        "note": note})
    finally:
        urllib.request.urlopen = real_urlopen
    sealed79 = json.loads((ROOT / "artifacts" / "fable-redteam79-20260921"
                           / "fable_redteam79_results.json").read_text(
        encoding="utf-8"))
    base79 = {c.get("id", c.get("cid")): c["verdict"]
              for c in sealed79["cases"]}

    def tally(cases):
        return {"total": len(cases),
                "OK": sum(1 for c in cases if c["verdict"] == "OK"),
                "BUG": sum(1 for c in cases if c["verdict"] == "BUG"),
                "UNCLEAR": sum(1 for c in cases if c["verdict"] == "UNCLEAR")}

    new_bugs67 = [c["id"] for c in core
                  if c["verdict"] == "BUG" and base67.get(c["id"]) != "BUG"]
    changed67 = [c["id"] for c in core
                 if base67.get(c["id"]) != c["verdict"]]
    new_bugs79 = [c["id"] for c in web
                  if c["verdict"] == "BUG" and base79.get(c["id"]) != "BUG"]
    changed79 = [c["id"] for c in web
                 if base79.get(c["id"]) != c["verdict"]]

    # Doctrinal checks against the ACTUAL loop90 notebook + thinker.
    doc: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        doc.append({"check": name, "pass": bool(ok), "detail": detail})
        print(("ok  " if ok else "FAIL") + f" loop90-{name} {detail}")

    with tempfile.TemporaryDirectory(prefix="loop90_z3_") as tmp:
        loop = L90.build_agent({**dict(L90.DEFAULT_CONFIG),
                                "state_dir": tmp,
                                "sleep_threshold": 10 ** 9})
        said = " ".join(loop.turn("Mira's city is Lisbon."))
        check("teach-ask roundtrip",
              "Saved" in said and loop.turn("Who is Mira's city?")[0]
              .endswith("Lisbon."), said)
        nb = loop.nb
        r = nb.assert_fact("z3-q1", "thinking", "web-quarantine",
                           nb.resolve("Mira").detail["entity_id"], "orbit",
                           {"literal": "Mars"},
                           provenance={"url": "https://example.org/x",
                                       "quoted_span": "Mira orbits Mars."})
        check("quarantine row stored", r.status == C.SAVED, r.status)
        rec = loop.reasoner.answer({"name": "Mira", "relations": ["orbit"]},
                                   nb)
        check("quarantine never answers",
              rec["status"] == C.MISSING_FACT, rec["status"])
        rec2 = loop.reasoner.answer({"name": "Mira", "relations": ["city"]},
                                    nb)
        check("taught still answers",
              rec2["status"] == C.OK and rec2["fields"].get("answer")
              == "Lisbon", str(rec2["status"]))
        # Thinker slot: the SAME class build_agent wires (exp-89 wrapper
        # when present, else m2), fed one clean claim from a fake searcher.
        import fable_thinking_m2 as M  # noqa: E402
        pages = {"moons": [{"subject": "Phobos", "relation": "orbits",
                             "value": "Mars",
                             "url": "https://example.org/p",
                             "quote": "Phobos orbits Mars."}]}
        thinker_nb_dir = Path(tmp) / "think-nb"
        tnb = L90.Loop90Notebook(thinker_nb_dir)
        think_cls = (L90.W89.QuarantinedThinking89
                     if L90.W89 is not None else M.Thinking)
        mind = think_cls(tnb, M.FakeSearcher(pages),
                         M.FakeFetcher({"https://example.org/p":
                                        "Phobos orbits Mars."}))
        check("thinker class is " + think_cls.__name__,
              ("Quarantine" in think_cls.__name__) or
              think_cls is M.Thinking, L90.THINKER_MODULE)
        mind.assign("moons")
        mind.think_once()
        waiting = mind.waiting()
        check("thinker quarantines (1 waiting, none believed)",
              len(waiting) == 1, f"waiting={len(waiting)}")
        # Tail seal: live on the loop's notebook class (throwaway dir).
        import fable_fix77_core as F77  # noqa: E402
        sdir = Path(tmp) / "seal-nb"
        snb = L90.Loop90Notebook(sdir)
        se = snb.new_entity("s-e1", "Zed")
        snb.declare_relation("s-r1", "city", True)
        snb.assert_fact("s-f1", "listening", "taught",
                        se.detail["entity_id"], "city", {"literal": "Oslo"})
        snb.advance_seal()
        try:
            F77.verify_full(sdir)
            sealed_ok = True
        except C.LogCorrupt:
            sealed_ok = False
        check("seal verifies after writes", sealed_ok, "")
        lines = (sdir / C.LOG_NAME).read_text(encoding="utf-8").splitlines()
        last = json.loads(lines[-1])
        last["value"] = {"literal": "Rome"}  # valid JSON + valid prev link
        lines[-1] = json.dumps(last, sort_keys=True)
        (sdir / C.LOG_NAME).write_text("\n".join(lines) + "\n",
                                       encoding="utf-8")
        try:
            F77.verify_full(sdir)
            tail_caught = False
        except C.LogCorrupt:
            tail_caught = True
        check("tail edit detected", tail_caught, "")

    rep = {"mark": "Z3",
           "core": {**tally(core), "new_bugs": new_bugs67,
                    "changed_vs_sealed": changed67,
                    "sealed": sealed67["summary"]},
           "web": {**tally(web), "new_bugs": new_bugs79,
                   "changed_vs_sealed": changed79,
                   "sealed": sealed79["summary"]},
           "doctrinal": doc,
           "pass": (not new_bugs67 and not new_bugs79 and not changed67
                    and not changed79 and all(d["pass"] for d in doc)),
           "seconds": round(time.time() - t0, 1)}
    rep["core_cases"] = core
    rep["web_cases"] = web
    (out / "z3-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"Z3: core={tally(core)} web={tally(web)} "
          f"doctrinal={sum(d['pass'] for d in doc)}/{len(doc)} "
          f"{rep['seconds']}s -> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ Z4
def run_z4(out: Path) -> dict:
    from fable_daemon74_selftest import (  # noqa: E402 (helpers reused)
        check_answer, fact_name, fact_value, submit as _submit,
        wait_outbox as _wait, stop_daemon as _stop)
    _ = (_submit, _wait, _stop)  # same mailbox file discipline, loop90 spawn
    t0 = time.time()
    cfg = dict(L90.DEFAULT_CONFIG)
    cfg["sleep_threshold"] = 10 ** 9
    per_seed = []
    for seed in (1, 2, 3):
        d = out / f"z4-daemon-s{seed}"
        if d.exists():
            shutil.rmtree(d)
        proc = spawn_loop90(d, {**cfg, "state_dir": str(d)})
        names = [fact_name("D2", seed, i) for i in range(200)]
        values = [fact_value("D2", seed, i) for i in range(200)]
        for i, (name, value) in enumerate(zip(names, values)):
            submit(d, f"teach-{i:03d}", f"{name}'s city is {value}.")
        deadline = time.time() + 120.0
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
        proc = spawn_loop90(d, {**cfg, "state_dir": str(d)})
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
        print(f"Z4 seed {seed}: correct={correct}/200 wrong={wrong} "
              f"dupes={dupes} chain_ok={chain_ok} "
              f"torn_reported={torn_reported} -> "
              f"{'PASS' if passed else 'FAIL'}")
    rep = {"mark": "Z4", "per_seed": per_seed,
           "pass": all(s["pass"] for s in per_seed),
           "seconds": round(time.time() - t0, 1)}
    (out / "z4-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"Z4 -> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


# ------------------------------------------------------------------ Z5
PLUG_POINTS = ("ears", "notebook", "reasoner", "mouth", "thinker", "sleeper")


def run_z5(out: Path) -> dict:
    cfg_path = out / "loop90-config.json"
    if not cfg_path.exists():
        cfg = dict(L90.DEFAULT_CONFIG)
        cfg["thinker"]["module"] = L90.THINKER_MODULE
        cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    checks = []
    for point in PLUG_POINTS:
        entry = cfg.get(point)
        ok = isinstance(entry, dict) and bool(entry.get("stand_in")) and bool(
            entry.get("replacement"))
        checks.append({"plug": point, "documented": ok,
                       "stand_in": (entry or {}).get("stand_in"),
                       "replacement": (entry or {}).get("replacement")})
    tau = L90.load_tau_hat(cfg["ears"].get("tau_hat_path"))
    with tempfile.TemporaryDirectory(prefix="loop90_z5_") as tmp:
        file_cfg = dict(cfg)
        file_cfg["state_dir"] = tmp
        loop = L90.build_agent(file_cfg)
        said = " ".join(loop.turn("Mira's city is Lisbon."))
        said2 = " ".join(loop.turn("Who is Mira's city?"))
        smoke = "Saved" in said and said2.endswith("Lisbon.")
        parts = {"ears": type(loop.ears).__name__,
                 "notebook": type(loop.nb).__name__,
                 "reasoner": type(loop.reasoner).__name__,
                 "mouth": type(loop.mouth).__name__,
                 "sleeper": type(loop.sleeper).__name__,
                 "thinker_module": loop.parts90.get("thinker_module"),
                 "tau_hat_used": loop.parts90.get("tau_hat_used"),
                 "protocol_ears": isinstance(loop.ears, A.Ears),
                 "protocol_mouth": isinstance(loop.mouth, A.Mouth),
                 "protocol_reasoner": isinstance(loop.reasoner, A.Reasoner),
                 "protocol_sleeper": isinstance(loop.sleeper, A.Sleeper),
                 "agentloop_compatible": isinstance(loop, A.AgentLoop)}
    rep = {"mark": "Z5", "config": str(cfg_path), "plug_checks": checks,
           "tau_hat_from_json": tau, "smoke": smoke, "parts": parts,
           "pass": all(c["documented"] for c in checks) and smoke
           and all(parts[k] for k in ("protocol_ears", "protocol_mouth",
                                      "protocol_reasoner",
                                      "protocol_sleeper",
                                      "agentloop_compatible"))}
    (out / "z5-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    print(f"Z5: plugs={sum(c['documented'] for c in checks)}/6 "
          f"smoke={smoke} -> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 90 marks")
    parser.add_argument("--mark", choices=("z1", "z2", "z3", "z4", "z5",
                                           "all"), required=True)
    parser.add_argument("--out", default=str(ART))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runners = {"z1": run_z1, "z2": run_z2, "z3": run_z3, "z4": run_z4,
               "z5": run_z5}
    selected = list(runners) if args.mark == "all" else [args.mark]
    oks = []
    for name in selected:
        rep = runners[name](out)
        oks.append(bool(rep["pass"]))
    print("MARKS", "PASS" if all(oks) else "FAIL")
    return 0 if all(oks) else 1


if __name__ == "__main__":
    sys.exit(main())
