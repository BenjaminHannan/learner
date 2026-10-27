#!/usr/bin/env python3
"""126 -- demo transcript harness (prep; the director re-runs it on tonight's
integrated agent). Additive only: imports loop agent modules read-only,
edits nothing.

Drives ONE fresh daemon dir through the mailbox (inbox/*.txt in, outbox
same-name replies out) with a scripted plain-English conversation (~37
turns), in acts:

  1 knows nothing ("Who is Mira's mother?" -> honest "I don't know")
  2 Ben teaches 8 facts in varied phrasings (possessive + married/created/
    citizen templates, all single-word names)
  3 two-hop + three-hop questions; four-hop (Ivy/Owen/Petra/Peru/Quechua
    single-outgoing chain) ONLY if the agent has an N-hop composer --
    otherwise the transcript carries "not supported by this agent" and the
    four-hop is SKIPped, never faked
  4 forget one fact, ask again (abstain), re-teach, ask again (answered)
  5 a wrong teach contradicting a taught fact -> refuses to overwrite and
    says why (old value kept)
  6 self-questions ("How many facts do you know?", "What did I teach you
    last?" -> honest clarify, no fabrication; trick "What is Tom's
    favourite number?" never taught -> honest abstain)
  7 live sleep: teach mother-chains (the raw material for "maternal
    grandmother" episodes as exp 104 did), let the daemon's sleep ticks
    fire, then probe the word on taught chains AND on NEW people never
    seen. loop117/loop113b carry HardGate46Sleeper with reasoner=None, so
    no install is possible: expectation is honest abstain + SKIP note, with
    evidence (state.json sleep ticks >= 1, zero sleep-derived facts).
  8 comparison panel READ from JSON files that already exist (never typed):
    artifacts/fable-bench113b-20260922/fable_bench113b_summary.json,
    artifacts/fable-bench66-20260921/fable_bench66_results.json, and
    artifacts/fable-bench125-20260922/ if present at run time.

Per-act expectations live in EXPECT (module level, frozen BEFORE the run;
also sealed in PASSMARKS.md). Output per agent run, keyed by --agent stem:
  <out>/transcript-<agent>.md   every turn verbatim + one plain-English note
  <out>/fable-demo126-results.json  merged dict keyed by agent, per-act
    PASS/FAIL/SKIP against EXPECT.

Sealed PASSMARKS cover: A1 abstain; A2 all Saved; A3 two-hop Porto,
three-hop Norway, four-hop Quechua iff composer else SKIP; A4
Forgotten/abstain/Saved/Lisbon; A5 refusal naming Lisbon + Lisbon kept;
A6 clarify/clarify/abstain with no fabrication; A7 abstains + >=1 sleep
tick + 0 installs; A8 panel equals the files; wall-clock < 900 s.

Usage (Mac CPU, no install):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_demo126_run.py --agent scripts/fable_loop117_agent.py \\
    --config artifacts/fable-loop117-20260922/loop117-config.json \\
    --out artifacts/fable-demo126-20260922
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

TIME_LIMIT_S = 900.0
TURN_TIMEOUT_S = 180.0
BOOT_TIMEOUT_S = 240.0

# ---------------------------------------------------------------- expectations
# Frozen BEFORE the registered runs (mirrored in PASSMARKS.md). Kinds:
# abstain (reply honestly says it does not know), saved, exact (normalised
# answer equals value), refuse (contradiction refused: names old value, no
# save), clarify (honest non-answer, no fabrication).
EXPECT = {
    "A1": "ask on an empty notebook abstains",
    "A2": "all 8 teaches reply Saved",
    "A3": "two-hop=Porto, three-hop=Norway, four-hop=Quechua iff composer else SKIP",
    "A4": "Forgotten, then abstain, then Saved, then Lisbon",
    "A5": "contradiction refused (names Lisbon, no save), Lisbon kept",
    "A6": "count/last clarify without fabrication, trick abstains",
    "A7": "word probes abstain, >=1 sleep tick fired, 0 installs",
    "A8": "panel numbers equal the JSON files exactly",
}

TURNS: list[dict] = [
    {"act": "A1", "ben": "Who is Mira's mother?", "kind": "abstain"},
    {"act": "A1", "ben": "Who is Keir's boss?", "kind": "abstain"},
    {"act": "A2", "ben": "Mira's mother is Ana.", "kind": "saved"},
    {"act": "A2", "ben": "Ana's city is Porto.", "kind": "saved"},
    {"act": "A2", "ben": "Mira's city is Lisbon.", "kind": "saved"},
    {"act": "A2", "ben": "Mira's boss is Keir.", "kind": "saved"},
    {"act": "A2", "ben": "Keir's city is Bern.", "kind": "saved"},
    {"act": "A2", "ben": "Mira is married to Theo", "kind": "saved"},
    {"act": "A2", "ben": "Theo was created by Wren", "kind": "saved"},
    {"act": "A2", "ben": "Wren is a citizen of Norway", "kind": "saved"},
    {"act": "A3", "ben": "What is Mira's mother's city?", "kind": "exact",
     "value": "Porto"},
    {"act": "A3", "ben": "What is Mira's spouse's creator's country of citizenship?",
     "kind": "exact", "value": "Norway"},
    {"act": "A3", "ben": "Ivy is married to Owen", "kind": "saved"},
    {"act": "A3", "ben": "Owen was created by Petra", "kind": "saved"},
    {"act": "A3", "ben": "Petra is a citizen of Peru", "kind": "saved"},
    {"act": "A3", "ben": "The official language of Peru is Quechua", "kind": "saved"},
    {"act": "A3", "ben": "What language is officially spoken in the country where "
     "the creator of the spouse of Ivy is a citizen?",
     "kind": "fourhop", "value": "Quechua"},
    {"act": "A3", "ben": "What is Mira's mother's city?", "kind": "exact",
     "value": "Porto"},
    {"act": "A4", "ben": "Where is Mira's city?", "kind": "exact",
     "value": "Lisbon"},
    {"act": "A4", "ben": "Forget Mira's city.", "kind": "forgotten"},
    {"act": "A4", "ben": "Where is Mira's city?", "kind": "abstain"},
    {"act": "A4", "ben": "Mira's city is Lisbon.", "kind": "saved"},
    {"act": "A4", "ben": "Where is Mira's city?", "kind": "exact",
     "value": "Lisbon"},
    {"act": "A5", "ben": "Mira's city is Oslo.", "kind": "refuse",
     "value": "Lisbon"},
    {"act": "A5", "ben": "Where is Mira's city?", "kind": "exact",
     "value": "Lisbon"},
    {"act": "A6", "ben": "How many facts do you know?", "kind": "clarify"},
    {"act": "A6", "ben": "What did I teach you last?", "kind": "clarify"},
    {"act": "A6", "ben": "What is Tom's favourite number?", "kind": "abstain"},
    {"act": "A7", "ben": "Nora's mother is Ada.", "kind": "saved"},
    {"act": "A7", "ben": "Ada's mother is June.", "kind": "saved"},
    {"act": "A7", "ben": "Leo's mother is Mia.", "kind": "saved"},
    {"act": "A7", "ben": "Mia's mother is Zoe.", "kind": "saved"},
    {"act": "A7", "ben": "June's city is Lyon.", "kind": "saved"},
    {"act": "A7", "ben": "Zoe's city is Nice.", "kind": "saved"},
    {"act": "A7", "ben": "Who is Nora's maternal grandmother?", "kind": "abstain_word",
     "value": "maternal grandmother"},
    {"act": "A7", "ben": "Who is Leo's maternal grandmother?", "kind": "abstain_word",
     "value": "maternal grandmother"},
    {"act": "A7", "ben": "Who is Rex's maternal grandmother?", "kind": "abstain_word",
     "value": "maternal grandmother"},
]

NOT_SUPPORTED_4HOP = ("[Director's note: this agent has no N-hop composer, "
                      "so the four-hop question is not supported by this "
                      "agent and is skipped here -- never faked.]")
SLEEP_SKIP_NOTE = ("[Director's note: this agent's sleeper has no word-episode "
                   "feed (exp-104 style), so no new word can be installed "
                   "overnight; the probes below check it honestly says so.]")

PANEL_FILES = {
    "bench113b": Path("artifacts/fable-bench113b-20260922/fable_bench113b_summary.json"),
    "bench66": Path("artifacts/fable-bench66-20260921/fable_bench66_results.json"),
    "bench125": Path("artifacts/fable-bench125-20260922"),
}


def norm(s: str) -> str:
    return " ".join(str(s).strip().lower().replace("_", " ").rstrip(".").split())


def check(kind: str, reply: str, value: str = "") -> tuple[bool, str]:
    r = str(reply)
    rl = r.lower().replace("_", " ")
    if kind == "abstain":
        ok = "don't know" in rl or "do not know" in rl
        return ok, "honest abstain" if ok else "expected an honest don't-know"
    if kind == "abstain_word":
        ok = ("don't know" in rl or "do not know" in rl) and (
            value.lower() in rl or "anyone called" in rl)
        return ok, "honest word abstain" if ok else "expected honest word abstain"
    if kind == "saved":
        ok = "saved" in rl
        return ok, "saved" if ok else "expected Saved"
    if kind in ("exact", "fourhop"):
        ans = norm(r.split(" is ")[-1].split(" are ")[-1] if " is " in r or " are " in r else r)
        ok = ans == norm(value)
        if not ok:  # fall back: gold appears as a word in the reply
            ok = norm(value) in norm(r)
        return ok, f"answered {value}" if ok else f"expected {value}, got {r[:80]!r}"
    if kind == "forgotten":
        ok = "forgotten" in rl
        return ok, "forgotten" if ok else "expected Forgotten"
    if kind == "refuse":
        ok = ("saved" not in rl and ("have " in rl or "already" in rl)
              and norm(value) in norm(r))
        return ok, "refused, old kept" if ok else "expected a refusal naming the old value"
    if kind == "clarify":
        ok = (("didn't understand" in rl or "didn't catch" in rl
               or "say it like" in rl or "only" in rl) and "saved" not in rl)
        return ok, "honest clarify" if ok else "expected an honest clarify"
    raise ValueError(kind)


def note_for(turn: dict, reply: str, ok: bool) -> str:
    k = turn["kind"]
    if not ok:
        return "This one did not go as the script expected; the result counts it."
    if k in ("abstain", "abstain_word"):
        return "It did not know, so it honestly said so."
    if k == "saved":
        return "It wrote this fact in its notebook."
    if k == "exact":
        return "It answered from its notes."
    if k == "forgotten":
        return "It crossed this fact out of its notebook."
    if k == "refuse":
        return "It refused to overwrite what Ben taught it, and said why."
    if k == "clarify":
        return "It did not understand, so it asked Ben to say it another way."
    return "Recorded."


def load_agent_module(agent_path: Path):
    spec = importlib.util.spec_from_file_location("fable_demo126_agent_mod", agent_path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(agent_path.parent))
    spec.loader.exec_module(mod)
    return mod


def wait_for(path: Path, timeout: float) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if path.exists() and path.stat().st_size > 0:
            return True
        time.sleep(0.05)
    return path.exists() and path.stat().st_size > 0


def read_panel() -> dict:
    panel: dict = {}
    p = ROOT / PANEL_FILES["bench113b"]
    s = json.loads(p.read_text(encoding="utf-8"))
    a = s["arms"]["loop113b"]
    panel["bench113b"] = {
        "splitA_correct": (
            a["fable_edit_200"]["table"]["mquake-twohop"]["correct"]
            + a["fable_edit_200"]["table"]["reversal"]["correct"]),
        "splitA_abstain": (
            a["fable_edit_200"]["table"]["abstain-absent"]["abstain"]
            + a["fable_edit_200"]["table"]["abstain-broken"]["abstain"]),
        "splitA_wrong": (
            a["fable_edit_200"]["table"]["mquake-twohop"]["wrong"]
            + a["fable_edit_200"]["table"]["reversal"]["wrong"]
            + a["fable_edit_200"]["table"]["abstain-absent"]["wrong"]
            + a["fable_edit_200"]["table"]["abstain-broken"]["wrong"]),
        "splitA_n": a["fable_edit_200"]["n"],
        "fresh_correct": a["s2fresh_4hop"]["table"]["mquake-s2fresh-4hop"]["correct"],
        "fresh_abstain": a["s2fresh_4hop"]["table"]["mquake-s2fresh-4hop"]["abstain"],
        "fresh_wrong": a["s2fresh_4hop"]["table"]["mquake-s2fresh-4hop"]["wrong"],
        "fresh_n": a["s2fresh_4hop"]["n"],
    }
    p = ROOT / PANEL_FILES["bench66"]
    rows = json.loads(p.read_text(encoding="utf-8"))["rows"]
    counts: dict = {}
    for arm in ("incontext", "raglite", "finetune"):
        c: dict = {}
        for r in rows:
            v = r["arms"][arm]["verdict"]
            c[v] = c.get(v, 0) + 1
        counts[arm] = c
    panel["bench66"] = {"n": len(rows), "arms": counts}
    p125 = ROOT / PANEL_FILES["bench125"]
    panel["bench125_present"] = p125.is_dir()
    if p125.is_dir():
        tallies = {}
        for f in sorted(p125.glob("*.jsonl")):
            c: dict = {}
            n = 0
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                n += 1
                v = json.loads(line).get("verdict", "?")
                c[v] = c.get(v, 0) + 1
            tallies[f.name] = {"n": n, "verdicts": c}
        panel["bench125"] = tallies
    return panel


def drive(agent_script: Path, config_path: Path, out: Path) -> dict:
    t_start = time.monotonic()
    agent_script = agent_script.resolve()
    stem = agent_script.stem  # e.g. fable_loop117_agent
    short = stem.replace("fable_", "").replace("_agent", "")  # loop117
    has_composer = ("113" in stem) or ("composer" in stem)
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))

    daemon_dir = out / f"daemon-{short}"
    if daemon_dir.exists():
        import shutil as _sh
        _sh.rmtree(daemon_dir)
    daemon_dir.mkdir(parents=True)

    cmd = [sys.executable, "-B", str(agent_script), "--daemon",
           "--dir", str(daemon_dir), "--config", str(config_path),
           "--idle-seconds", "3600"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        if not wait_for(daemon_dir / "daemon_status.json", BOOT_TIMEOUT_S):
            raise RuntimeError("daemon never booted")
        turns: list[dict] = []
        fourhop_skipped = False
        for i, t in enumerate(TURNS):
            if t["kind"] == "fourhop" and not has_composer:
                fourhop_skipped = True
                turns.append({"act": t["act"], "ben": t["ben"], "agent": None,
                              "note": NOT_SUPPORTED_4HOP, "kind": "fourhop-skip",
                              "ok": True})
                continue
            name = f"t{i:04d}.txt"
            tmp = daemon_dir / "inbox" / f"{name}.tmp"
            tmp.write_text(t["ben"] + "\n", encoding="utf-8")
            import os as _os
            _os.replace(tmp, daemon_dir / "inbox" / name)
            if not wait_for(daemon_dir / "outbox" / name, TURN_TIMEOUT_S):
                raise RuntimeError(f"no reply for turn {i}: {t['ben']!r}")
            reply = (daemon_dir / "outbox" / name).read_text(
                encoding="utf-8").strip()
            ok, why = check(t["kind"], reply, t.get("value", ""))
            turns.append({"act": t["act"], "ben": t["ben"], "agent": reply,
                          "note": note_for(t, reply, ok), "kind": t["kind"],
                          "ok": ok, "why": why})
        elapsed = time.monotonic() - t_start
    finally:
        try:
            (daemon_dir / "STOP").write_text("stop\n", encoding="utf-8")
        except OSError:
            pass
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()

    # sleep evidence from the daemon dir itself
    sleeps = 0
    try:
        st = json.loads((daemon_dir / "state.json").read_text(encoding="utf-8"))
        sleeps = int(st.get("counters", {}).get("sleeps", 0))
    except (OSError, ValueError):
        pass
    sleep_derived = 0
    for ev in sorted(daemon_dir.glob("**/events.jsonl")):
        try:
            for line in ev.read_text(encoding="utf-8").splitlines():
                if '"sleep-derived"' in line or "'sleep-derived'" in line:
                    sleep_derived += 1
        except OSError:
            pass

    # per-act verdicts
    acts: dict = {}
    for a in ("A1", "A2", "A3", "A4", "A5", "A6", "A7"):
        ts = [x for x in turns if x["act"] == a and x["kind"] != "fourhop-skip"]
        n_ok = sum(1 for x in ts if x["ok"])
        acts[a] = {"pass": bool(ts) and n_ok == len(ts),
                   "ok": n_ok, "n": len(ts)}
    fh = [x for x in turns if x["kind"] == "fourhop"]
    if has_composer:
        acts["A3"]["fourhop"] = ("PASS" if fh and fh[0]["ok"] else "FAIL")
        acts["A3"]["pass"] = acts["A3"]["pass"] and bool(fh and fh[0]["ok"])
    else:
        acts["A3"]["fourhop"] = "SKIP"
    a7probes = [x for x in turns if x["kind"] == "abstain_word"]
    acts["A7"]["sleep_ticks"] = sleeps
    acts["A7"]["sleep_derived_facts"] = sleep_derived
    acts["A7"]["pass"] = (acts["A7"]["pass"] and sleeps >= 1
                          and sleep_derived == 0 and len(a7probes) == 3
                          and all(x["ok"] for x in a7probes))

    panel = read_panel()
    acts["A8"] = {"pass": True, "panel": panel}

    return {"agent": short, "has_composer": has_composer,
            "fourhop_skipped": fourhop_skipped, "turns": turns,
            "acts": acts, "elapsed_seconds": round(elapsed, 1),
            "sleep_ticks": sleeps, "sleep_derived_facts": sleep_derived}


def build_transcript(res: dict, panel: dict) -> str:
    L: list[str] = []
    L.append(f"A demo evening with the {res['agent']} assistant")
    L.append("")
    L.append("How to read this: Ben speaks, the Agent answers. After each turn, "
             "one line explains what happened, in plain words.")
    L.append("")
    heads = {
        "A1": "Act 1. Starting from nothing.",
        "A2": "Act 2. Ben teaches eight facts.",
        "A3": "Act 3. Questions that join facts together.",
        "A4": "Act 4. Forgetting one fact, then learning it again.",
        "A5": "Act 5. A wrong lesson the agent refuses.",
        "A6": "Act 6. The agent talks about itself.",
        "A7": "Act 7. Overnight learning (live sleep).",
        "A8": "Act 8. How it compares with earlier measurements.",
    }
    last = ""
    for t in res["turns"]:
        if t["act"] != last:
            last = t["act"]
            L.append(heads[last])
            L.append("")
            if last == "A7":
                L.append(SLEEP_SKIP_NOTE)
                L.append("")
        if t["kind"] == "fourhop-skip":
            L.append(NOT_SUPPORTED_4HOP)
            L.append("")
            continue
        L.append(f"Ben: {t['ben']}")
        L.append(f"Agent: {t['agent']}")
        L.append(t["note"])
        L.append("")
    L.append(heads["A8"])
    L.append("")
    b3 = panel["bench113b"]
    L.append(f"Earlier, the loop113b assistant faced {b3['splitA_n']} short edit "
             f"questions: it answered {b3['splitA_correct']} correctly, properly "
             f"passed on {b3['splitA_abstain']}, and got {b3['splitA_wrong']} wrong; "
             f"on 200 long four-step questions it got {b3['fresh_correct']} right, "
             f"passed on {b3['fresh_abstain']}, and got {b3['fresh_wrong']} wrong. "
             f"Those numbers are read from its score file, not typed here.")
    b6 = panel["bench66"]["arms"]
    L.append(f"A small open-weight model, asked the same kind of two-step questions "
             f"200 times with no notebook, got "
             f"{b6['incontext'].get('correct', 0)} right just by reading the question, "
             f"{b6['raglite'].get('correct', 0)} right with retrieved text, and "
             f"{b6['finetune'].get('correct', 0)} right after extra training. "
             f"Those numbers are read from its results file, not typed here.")
    if panel["bench125_present"]:
        parts = [f"{name}: {t['n']} rows, " + ", ".join(
            f"{v} {k}" for k, v in sorted(t["verdicts"].items()))
            for name, t in sorted(panel["bench125"].items())]
        L.append("A third panel existed at run time and was read from its row "
                 "files: " + "; ".join(parts) + ".")
    else:
        L.append("The bench125 panel did not exist yet at run time, so there is "
                 "nothing to quote from it.")
    L.append("")
    L.append(f"This conversation took {res['elapsed_seconds']:.0f} seconds.")
    L.append("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="126 demo transcript harness")
    p.add_argument("--agent", default="scripts/fable_loop117_agent.py")
    p.add_argument("--config",
                   default="artifacts/fable-loop117-20260922/loop117-config.json")
    p.add_argument("--out", default="artifacts/fable-demo126-20260922")
    args = p.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    res = drive(Path(args.agent), Path(args.config), out)
    panel = res["acts"]["A8"]["panel"]
    text = build_transcript(res, panel)
    (out / f"transcript-{res['agent']}.md").write_text(text, encoding="utf-8")

    # verbatim audit: every Ben line and every reply is in the transcript
    missing = [t["ben"] for t in res["turns"]
               if t["kind"] != "fourhop-skip" and t["ben"] not in text]
    missing += [t["agent"] for t in res["turns"]
                if t.get("agent") and t["agent"] not in text]
    assert not missing, f"transcript not verbatim: {missing[:3]}"

    # panel audit: results carry exactly what the files hold
    assert res["acts"]["A8"]["panel"] == read_panel(), "panel drift"

    res["acts"]["time_ok"] = res["elapsed_seconds"] < TIME_LIMIT_S
    agg = {a: ("PASS" if v["pass"] else "FAIL") for a, v in res["acts"].items()
           if a.startswith("A")}
    res["marks"] = agg

    rpath = out / "fable-demo126-results.json"
    merged = {}
    if rpath.exists():
        merged = json.loads(rpath.read_text(encoding="utf-8"))
    merged[res["agent"]] = res
    rpath.write_text(json.dumps(merged, indent=1), encoding="utf-8")

    print("=" * 72, flush=True)
    print(f"DEMO 126 {res['agent']} acts (per act, never averaged)", flush=True)
    for a in sorted(agg):
        print(f"  {a} {agg[a]}", flush=True)
    print(f"TOTAL_ELAPSED_SECONDS {res['elapsed_seconds']:.1f}", flush=True)
    assert res["acts"]["time_ok"], "over the 900 s limit"
    assert all(v["pass"] for k, v in res["acts"].items()
               if k.startswith("A")), "an act FAILED"
    return 0


if __name__ == "__main__":
    sys.exit(main())
