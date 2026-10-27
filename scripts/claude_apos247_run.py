"""Exp 247 runner: runs dev cases or the ask panel on BOTH arms (base228 and
loop247) in one process, interleaved per item (arm order alternates), one
fresh work dir per arm per item under --work (never the repo notebook).

  python scripts/claude_apos247_run.py dev --cases artifacts/claude-apos247-20260922/dev247.jsonl --out ROWS --work DIR
  python scripts/claude_apos247_run.py panel --panel-dir artifacts/claude-askpanel243-20260922 --out ROWS --work DIR

Panel mode runs the scorer's schema check first (SCHEMA-MISMATCH -> exit 3).
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402

ARMS = {
    "base228": ("scripts/claude_loop228_agent.py", "Loop228Daemon",
                "artifacts/claude-determinism228-20260922/loop228-config.json"),
    "mine": ("scripts/claude_loop247_agent.py", "Loop247Daemon",
             "artifacts/claude-apos247-20260922/loop247-config.json"),
}


def _load(arm):
    path, cls, cfg = ARMS[arm]
    spec = importlib.util.spec_from_file_location("apos247_arm_" + arm, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, cls), json.loads(Path(cfg).read_text(encoding="utf-8"))


def _triples(d):
    return [list(t) for t in L90.notebook_triples(d.loop.nb)]


def run_one(dcls, base_cfg, root: Path, setup, question):
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    cfg = copy.deepcopy(base_cfg)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    d = dcls(root, cfg=cfg, idle_seconds=3600.0)
    replies = []
    for j, t in enumerate(setup):
        f = root / "inbox" / f"m{j:02d}.txt"
        f.write_text(t, encoding="utf-8")
        d.process_file(f)
        replies.append((root / "outbox" / f"m{j:02d}.txt").read_text(
            encoding="utf-8").strip())
    after_setup = _triples(d)
    j = len(setup)
    f = root / "inbox" / f"m{j:02d}.txt"
    f.write_text(question, encoding="utf-8")
    t0 = time.perf_counter()
    d.process_file(f)
    dt = time.perf_counter() - t0
    reply = (root / "outbox" / f"m{j:02d}.txt").read_text(encoding="utf-8").strip()
    return {"setup_replies": replies, "stored_after_setup": after_setup,
            "reply": reply, "stored_after_question": _triples(d),
            "q_seconds": dt}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "panel"])
    ap.add_argument("--cases")
    ap.add_argument("--panel-dir", default="artifacts/claude-askpanel243-20260922")
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args(argv)
    if a.mode == "panel":
        import claude_apos247_score as SC
        cases, _base = SC.schema_check(a.panel_dir)
    else:
        cases = [json.loads(x) for x in Path(a.cases).read_text(
            encoding="utf-8").splitlines() if x.strip()]
    work = Path(a.work).resolve()
    repo_nb = (SCRIPTS.parent / "notebook").resolve()
    assert repo_nb not in work.parents and work != repo_nb
    arms = {k: _load(k) for k in ARMS}
    t_start = time.time()
    with open(a.out, "w", encoding="utf-8") as fh:
        for i, c in enumerate(cases):
            order = ["base228", "mine"] if i % 2 == 0 else ["mine", "base228"]
            for arm in order:
                dcls, cfg = arms[arm]
                row = run_one(dcls, cfg, work / arm / c["id"], c["setup"],
                              c["question"])
                row.update({"id": c["id"], "arm": arm, "family": c["family"],
                            "question": c["question"], "gold": c.get("gold"),
                            "allowed_mentions": c.get("allowed_mentions", [])})
                fh.write(json.dumps(row) + "\n")
                fh.flush()
    print(f"ran {len(cases)} items x 2 arms in {time.time() - t_start:.1f}s -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
