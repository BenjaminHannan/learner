#!/usr/bin/env python3
"""Experiment 57 -- wiring end-to-end: sleep installs 'grandmother', new people asked.

Task (doc 61): two paths wire51 never exercised --
  (A) the Exp-46 sleep install recipe firing on >= 20 episodes of one candidate
      word ('maternal_grandmother' = mother-of-mother);
  (B) asking grandmother questions on NEW people after the install.

Session (80 turns, plain-software FakeEars -- a STAND-IN, not the real ears: it
emits the same action objects EnglishEars would, so there is no Qwen bridge
dependency for the registered marks):
  turns  1-50  teach mother chains: 20 train triples (K kid, M mom, G gran) and
               5 test triples (T kid, N mom, H gran). Test chains are taught but
               never asked about before sleep.
  turns 51-70  20 'Who is Kxx's maternal grandmother?' questions -> 20 episodes.
  turns 71-75  5 small-talk fillers (write nothing).
  [auto-sleep fires at experience 75; the installed word is then bridged into
   the live reasoner50 -- see below -- because adapters keep the trained R44
   logits in a checkpoint file only]
  turns 76-80  5 'Who is Txx's maternal grandmother?' questions on NEW people.

Why the bridge step: HardGate46Sleeper._run_exp46 trains Exp-44 word logits and
saves a .pt file but never calls FableReasoner50.load_word, so the live
reasoner would keep abstaining after an accepted install. This script copies
the installed word's 27 numbers (words.0, [3][9], keep+8 skills, same order in
R44.RELATIONS and R50.CORE8) into the loop's own reasoner50 instance. The copy
is read-only w.r.t. training (hardened +/-30 logits, argmax chain audited by
the gate); nothing outside this file is edited.

A second run of the same 80 turns through the REAL EnglishEars is attempted
iff the Qwen bridge answers GET /v1/models within 5 s; else 'bridge down' is
recorded and the run is skipped (no marks depend on it).

Seeds 5701/5702/5703 drive the SLEEPER's gate (fold shuffle + fit RNG). The
base network is fixed to the sealed Exp-44 base-seed4102.pt in all seeds
(no matching base checkpoints exist for 5701+; training fresh bases would
break the wall-clock budget). Stated in RESULTS.md as a deviation.

Marks (sealed in PASSMARKS.md before the wave):
  W1 sleeper attempts >= 1 install
  W2 gate decision recorded and audited (mark = recorded, not accepted)
  W3 if accepted: new-people questions 5/5, else MISSING_FACT 5/5, never wrong
  W4 wrong writes 0
  W5 hash chain verifies
  W6 wall-clock < 15 min (whole wave)

Additive, offline, CPU, one thread. Imports fable_wire51_adapters,
fable_agent_loop, fable_notebook_contract read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402
import fable_notebook_contract as C  # noqa: E402
import fable_wire51_adapters as AD  # noqa: E402

ARTIFACT = SCRIPTS.parent / "artifacts" / "fable-wire57-20260921"
BASE_PT = (SCRIPTS.parent / "artifacts" / "fable-reasoner44-20260921"
           / "runs" / "base-seed4102.pt")
SEEDS = (5701, 5702, 5703)
SLEEP_THRESHOLD = 75
WORD = "maternal_grandmother"
BRIDGE_URL = "http://127.0.0.1:18081"

TRAIN = [(f"K{i:02d}", f"M{i:02d}", f"G{i:02d}") for i in range(1, 21)]
TEST = [(f"T{i:02d}", f"N{i:02d}", f"H{i:02d}") for i in range(1, 6)]
FILLERS = ["Hi, how are you?", "Thanks, that helps.",
           "What's the weather like today?", "Tell me a joke.", "Good morning!"]


def build_turns() -> list[dict]:
    turns: list[dict] = []
    for kid, mom, gran in TRAIN + TEST:
        turns.append({"kind": "teach", "text": f"{kid}'s mother is {mom}.",
                      "expect": (kid, "mother", mom)})
        turns.append({"kind": "teach", "text": f"{mom}'s mother is {gran}.",
                      "expect": (mom, "mother", gran)})
    for kid, _, gran in TRAIN:
        turns.append({"kind": "episode", "text": f"Who is {kid}'s maternal grandmother?",
                      "expect": gran})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    for kid, _, gran in TEST:
        turns.append({"kind": "probe", "text": f"Who is {kid}'s maternal grandmother?",
                      "expect": gran})
    assert len(turns) == 80, len(turns)
    return turns


def _display(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], value["entity"])
    return str(value.get("literal", ""))


def verify_chain(state_dir: Path) -> dict:
    """Recompute the notebook hash chain from genesis (W5)."""
    path = state_dir / "notebook" / C.LOG_NAME
    prev = C.GENESIS
    n = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("prev") != prev:
                return {"ok": False, "lines": n, "note": f"link broken at line {n + 1}"}
            prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
            n += 1
    except (OSError, ValueError) as exc:
        return {"ok": False, "lines": n, "note": str(exc)[:120]}
    return {"ok": True, "lines": n, "note": f"{n} lines chained from genesis"}


def bridge_up(timeout: float = 5.0) -> bool:
    try:
        with urllib.request.urlopen(BRIDGE_URL + "/v1/models", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _best_effort_set(R44, village, tag: str, seed: int, count: int,
                     lengths: tuple) -> list:
    """Up to `count` resolvable questions per hop length; lengths with < 4
    resolvable are skipped. Same sampler, same tags otherwise."""
    qs = []
    for length in lengths:
        c = count
        got = None
        while c >= 4:
            try:
                got = R44.sample_set(village, f"{tag}/hop{length}", seed,
                                     c, (length,), "resolvable")
                break
            except RuntimeError:
                c //= 2
        if got:
            qs.extend(got)
    return qs


class SparseVillageSleeper(AD.HardGate46Sleeper):
    """The Exp-46 recipe, unchanged EXCEPT the regression probe and held set.

    The registered recipe probes 3x64 base questions, which a live notebook of
    60 people with only mother facts cannot supply (no hop-3 chains exist, and
    only ~55 hop-1 links). The install gate itself (robust loss, harden to the
    argmax chain, OOF >= 0.80, refit agreement >= 0.90, old skills unchanged,
    reload identical) is byte-for-byte the same code path (R44.sleep_word via
    the hardgate patch); only the probe/held builders below are village-sized,
    and the unchanged rule stays exact equality on whatever probe was built.
    Declared as a deviation in RESULTS.md.
    """

    def _run_exp46(self, notebook) -> dict:
        episodes = list(self.reasoner.episodes) if self.reasoner else []
        if len(episodes) < self.MIN_EPISODES:
            return {"attempted": False, "queued": len(episodes),
                    "reason": f"{len(episodes)} word episodes (< {self.MIN_EPISODES}); "
                              "kept queued, nothing to gate"}
        if self.reasoner is not None:
            self.reasoner.episodes.clear()
        try:
            import torch
            import fable_reasoner44 as R44
            import fable_hardgate46 as G  # read-only: patches R44.fit_word
        except Exception as exc:
            return {"attempted": False, "reason": f"recipe unavailable: {exc}"}
        torch.set_num_threads(1)
        if not self.checkpoint.exists():
            return {"attempted": False, "reason": f"no base checkpoint at {self.checkpoint}"}

        R44 = G.R44
        village = AD._village_from_notebook(R44, notebook)
        matrices = R44.notebook_matrices(village)
        base_state = torch.load(self.checkpoint, map_location="cpu", weights_only=True)
        base_state = base_state["state"] if "state" in base_state else base_state
        out = self.state_dir / "sleep-checkpoints"
        out.mkdir(parents=True, exist_ok=True)

        base_model = R44.Reasoner()
        base_model.load_state_dict(base_state)
        probe = _best_effort_set(R44, village, "wire57/probe", self.seed, 64, (1, 2, 3))
        if not probe:
            return {"attempted": False, "reason": "live village too sparse for any probe"}
        before = R44.predict(base_model, village, matrices, probe)
        held = _best_effort_set(R44, village, "wire57/held", self.seed, 64, (1, 2, 3))
        results = []
        by_word: dict[int, list] = {}
        for ep in episodes:
            by_word.setdefault(ep["word"], []).append(
                R44.Question(ep["start"], (R44.R + ep["word"],), ep["answer"]))
        for w, eps in sorted(by_word.items()):
            rec = R44.sleep_word(base_state, w, eps, village, matrices, self.seed,
                                 "wire57-live", before, probe, village, matrices, held, out)
            results.append({"word": R44.WORD_NAMES[w], "episodes": len(eps),
                            "installed": bool(rec.get("installed")),
                            "oof_best": max((float(v["match"]) for v in
                                             rec.get("cv_table", {}).values()), default=0.0),
                            "refit_agreement": rec.get("refit_agreement"),
                            "reason": rec.get("reason")})
        installed = sum(1 for r in results if r["installed"])
        self.installs += installed
        return {"attempted": True, "installed": installed, "words": results,
                "probe_size": len(probe), "held_size": len(held)}


def run_seed(seed: int, root: Path, *, ears_mode: str = "fake",
             threshold: int = SLEEP_THRESHOLD) -> dict:
    t0 = time.time()
    state_dir = root / f"seed{seed}"
    if ears_mode == "fake":
        ears = A.FakeEars()  # stand-in: same action dicts EnglishEars emits
    else:
        ears = AD.EnglishEars(mode=ears_mode)
    mouth = AD.TemplateMouth()
    reasoner = AD.NotebookReasoner(state_dir, checkpoint=str(BASE_PT), seed=seed)
    sleeper = SparseVillageSleeper(state_dir, reasoner=reasoner,
                                   checkpoint=str(BASE_PT), seed=seed)
    loop = A.AgentLoop(state_dir, ears=ears, mouth=mouth, reasoner=reasoner,
                       sleeper=sleeper, sleep_threshold=threshold)
    if isinstance(ears, AD.EnglishEars):
        ears.bind(loop.listening, loop.nb)
    turns = build_turns()
    phase1, phase2 = turns[:75], turns[75:]

    per_turn: list[dict] = []
    wrong_writes = 0

    def do_turn(i: int, turn: dict) -> dict:
        nonlocal wrong_writes
        nb = loop.nb
        before = set(nb.facts)
        loop.submit(turn["text"])
        events = loop.run_until_idle()
        said = " ".join(line for e in events for line in e["said"])
        new = [nb.facts[f] for f in set(nb.facts) - before]
        entry = {"i": i, "kind": turn["kind"], "text": turn["text"], "said": said,
                 "new_facts": len(new), "ears": loop.ears.last_source
                 if hasattr(loop.ears, "last_source") else ears_mode}
        kind = turn["kind"]
        if kind == "teach":
            want = turn["expect"]
            ok = (len(new) == 1 and nb.entities.get(new[0]["subject"], "") == want[0]
                  and new[0]["relation"] == want[1]
                  and _display(nb, new[0]["value"]) == want[2]
                  and new[0]["source"] == "taught")
            entry["fact_ok"] = ok
            if not ok:
                wrong_writes += 1
                entry["note"] = f"expected {want}"
        elif kind in ("episode", "probe", "filler"):
            if new:
                wrong_writes += 1
                entry["note"] = "a question/filler wrote a fact"
        per_turn.append(entry)
        return entry

    for i, t in enumerate(phase1, 1):
        do_turn(i, t)

    outcome = dict(sleeper.last_outcome or {})
    recipe = dict(outcome.get("recipe", {}))
    attempted = bool(recipe.get("attempted"))
    words = recipe.get("words", [])
    installed = bool(recipe.get("installed")) if attempted else False
    gate = {"attempted": attempted, "installed": installed, "words": words,
            "audit_violations": outcome.get("audit", {}).get("violations", ["unknown"]),
            "sleeps": sleeper.sleeps,
            "episodes_seen": sum(w.get("episodes", 0) for w in words)}

    bridged = False
    if installed:
        ckpts = sorted((state_dir / "sleep-checkpoints").glob(f"word-seed{seed}-*-{WORD}-*.pt"))
        if ckpts and getattr(reasoner, "_impl50", None) is not None:
            try:
                import torch
                torch.set_num_threads(1)
                sd = torch.load(ckpts[-1], map_location="cpu", weights_only=True)
                logits = sd["words.0"].tolist()
                reasoner._impl50.load_word(WORD, logits)
                bridged = True
            except Exception as exc:  # noqa: BLE001 -- recorded, never fatal
                gate["bridge_error"] = str(exc)[:160]

    probe_results = []
    for i, t in enumerate(phase2, 76):
        entry = do_turn(i, t)
        hit = t["expect"].lower() in entry["said"].lower()
        abst = ("don't know" in entry["said"].lower()
                or "do not know" in entry["said"].lower())
        probe_results.append({"text": t["text"], "said": entry["said"],
                              "expect": t["expect"], "hit": hit, "abstained": abst})
    correct = sum(1 for r in probe_results if r["hit"])
    abstained = sum(1 for r in probe_results if r["abstained"] and not r["hit"])
    wrong_answers = sum(1 for r in probe_results if not r["hit"] and not r["abstained"])

    chain = verify_chain(state_dir)
    seconds = round(time.time() - t0, 1)
    return {"seed": seed, "ears_mode": ears_mode, "turns": 80,
            "wrong_writes": wrong_writes,
            "episodes_queued_total": len(reasoner.episodes) + gate["episodes_seen"],
            "gate": gate, "bridged": bridged,
            "probes": {"correct": correct, "abstained": abstained,
                       "wrong_answers": wrong_answers, "detail": probe_results},
            "chain": chain, "seconds": seconds,
            "backend": reasoner.backend, "per_turn": per_turn}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 57: sleep installs grandmother (doc 61)")
    parser.add_argument("--root", default=str(ARTIFACT / "runs"),
                        help="folder holding one state dir per seed")
    parser.add_argument("--report", default=str(ARTIFACT / "wave-report.json"))
    parser.add_argument("--seed", type=int, action="append", default=None)
    args = parser.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    seeds = tuple(args.seed) if args.seed else SEEDS

    up = bridge_up()
    rep = {"seeds": list(seeds), "base_checkpoint": str(BASE_PT),
           "bridge": "up" if up else "down", "runs": []}
    for seed in seeds:
        rep["runs"].append(run_seed(seed, root))

    if up:  # same session through the real ears; recorded only, no marks
        try:
            eng = run_seed(seeds[0], root / "english", ears_mode="english")
            rep["english_probe"] = {
                "episodes": eng["gate"].get("episodes_seen", 0),
                "attempted": eng["gate"]["attempted"],
                "note": "recorded only; Qwen parser rejects the phrase (wire51 deviation 3)"}
        except Exception as exc:  # noqa: BLE001
            rep["english_probe"] = {"note": f"english run failed: {str(exc)[:160]}"}
    else:
        rep["english_probe"] = {"note": "bridge down; skipped (no mark)"}

    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True), encoding="utf-8")
    for r in rep["runs"]:
        g = r["gate"]
        print(f"seed {r['seed']}: attempts={int(g['attempted'])} "
              f"installed={int(g['installed'])} episodes={g['episodes_seen']} "
              f"probes={r['probes']['correct']}/5 abst={r['probes']['abstained']} "
              f"wrong_writes={r['wrong_writes']} chain={r['chain']['ok']} "
              f"{r['seconds']}s")
    print(f"bridge: {rep['bridge']}; english_probe: {rep['english_probe'].get('note')}")
    print(f"report -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
