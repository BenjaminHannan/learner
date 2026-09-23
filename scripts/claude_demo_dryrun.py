"""Demo dry-run: loop138i base agent vs SmolLM2-360M-Instruct (fair prompt).

Measurement only. Reads artifacts/claude-demo-dryrun-20260922/script.json,
drives a fresh loop138i daemon in a temp state dir (never repo notebook/),
and SmolLM with scripts/fable_fairsmol211.py's fair prompt + bench66 greedy
decode (both imported, not copied). Writes raw.json next to script.json.

Usage:
  python -B scripts/claude_demo_dryrun.py agent   # agent arm only
  python -B scripts/claude_demo_dryrun.py smol    # SmolLM arm only
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
ART = ROOT / "artifacts" / "claude-demo-dryrun-20260922"
SCRIPT = json.loads((ART / "script.json").read_text(encoding="utf-8"))["turns"]


def run_agent() -> list[dict]:
    import fable_marks123_all as M
    import fable_loop90_agent as L90
    mod, dcls, _, _ = M.load_agent(str(ROOT / "scripts" / "fable_loop138i_agent.py"))
    base = M.load_base_cfg(str(ROOT / "artifacts" / "fable-agent138i-20260922" / "loop138i-config.json"))
    tmp = Path(tempfile.mkdtemp(prefix="claude_demo_agent_"))
    root = tmp / "state"
    root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root)
    rows = []

    def triples():
        return sorted(tuple(t) for t in L90.notebook_triples(d.loop.nb))

    for i, t in enumerate(SCRIPT):
        before = triples()
        t0 = time.time()
        if t["kind"] == "restart":
            del d
            d = M.make_daemon(dcls, base, root)  # NEW daemon, SAME state dir
            reply = "[restarted: new daemon on same state dir]"
        else:
            name = "m%02d.txt" % i
            f = root / "inbox" / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(t["text"], encoding="utf-8")
            try:
                d.process_file(f)
                out = root / "outbox" / name
                reply = out.read_text(encoding="utf-8") if out.exists() else "[no outbox file]"
            except Exception as e:  # record, keep going
                reply = "[EXCEPTION %s: %s]" % (type(e).__name__, e)
        after = triples()
        rows.append({"id": t["id"], "text": t["text"], "reply": reply.strip(),
                     "added": [list(x) for x in after if x not in before],
                     "removed": [list(x) for x in before if x not in after],
                     "facts_after": [list(x) for x in after],
                     "fact_ids": sorted(d.loop.nb.facts.keys()),
                     "secs": round(time.time() - t0, 2)})
        print("A%02d %-45s -> %s | +%s -%s" % (t["id"], t["text"][:45], reply.strip()[:120],
                                               rows[-1]["added"], rows[-1]["removed"]), flush=True)
    rows.append({"state_dir": str(root)})
    return rows


def run_smol() -> list[dict]:
    import torch
    torch.manual_seed(6601)
    torch.set_num_threads(1)
    from fable_fairsmol211 import build_fair_prompt
    from fable_bench66_baselines import greedy_answer, MAX_NEW_TOKENS
    from fable_bench125_run import load_model
    model, tok = load_model()
    taught: list[dict] = []
    rows = []
    for t in SCRIPT:
        t0 = time.time()
        if t["kind"] == "restart":
            taught = []  # restart = empty context: SmolLM has no memory
            rows.append({"id": t["id"], "text": t["text"],
                         "reply": "[restarted: context emptied]", "n_facts": 0, "secs": 0})
            continue
        if t["kind"] == "teach":
            subj, rel = t["fact"]
            taught.append({"sentence_en": t["text"], "subject": subj, "relation": rel,
                           "edit": bool(t.get("correction"))})
            # A teach turn is also a turn SmolLM must reply to; ask it with the
            # statement as the "question" so its reply is shown side by side.
        prompt = build_fair_prompt(tok, taught, t["text"])
        ans = greedy_answer(model, tok, prompt)
        rows.append({"id": t["id"], "text": t["text"], "reply": ans,
                     "n_facts": len(taught), "secs": round(time.time() - t0, 2),
                     "prompt": prompt})
        print("S%02d %-45s -> %s" % (t["id"], t["text"][:45], ans), flush=True)
    rows.append({"max_new_tokens": MAX_NEW_TOKENS})
    return rows


def main() -> int:
    which = sys.argv[1]
    raw_path = ART / "raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {}
    t0 = time.time()
    raw[which] = run_agent() if which == "agent" else run_smol()
    raw[which + "_seconds"] = round(time.time() - t0, 1)
    raw_path.write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
    print("done %s in %.1fs" % (which, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
