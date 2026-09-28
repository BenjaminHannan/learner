#!/usr/bin/env python3
"""Lead 0 (Director helper, 2026-09-28): can the plain LFM2.5-1.2B talker retell a code-made, checked grid exactly?

Read-only: no training, no adapter, no reader, no reasoner. For each item the note is the H1 frame that
claude_e2e02d.reasoner_note() builds, holding the code-made TRUE solution; the talker gets the same system text and
chat form as the 0.2d chain (claude_e2e02d.system_text / user_text, empty W block, no history). Score = the last
size x size run of numbers in the reply (claude_rsn358b3_panel.final_grid) equals the note's grid, cell for cell.
Arms per grid seed: R (note = true solution, the test) and N (no note: the talker sees only the puzzle; a control,
shows the talker is not just solving it). Greedy, max 160 new tokens, thinking off (as the chain).

  python -B scripts/claude_dir_lead0_retell.py run --model LFM_SNAPSHOT_DIR --out DIR [--seeds 1,2] [--n 100]
  python -B scripts/claude_dir_lead0_retell.py selftest      (no model: fake talkers)
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358b2_bridge as B      # noqa: E402
import claude_rsn358b3_panel as P       # noqa: E402

SIZES = (5, 6, 7)


def make_items(seed, n):
    """n items per seed, split across SIZES (n=100 -> 34/33/33), code-made puzzle + true solution."""
    counts = [n // 3 + (1 if i < n % 3 else 0) for i in range(3)]
    items = []
    for s, c in zip(SIZES, counts):
        for k, r in enumerate(B.make_requests(seed * 100 + s, c, s, False)):
            items.append({"id": "L0-%d-%d-%03d" % (seed, s, k), "size": s, "puz": r["puz"], "sol": r["sol"], "text": r["text"]})
    return items


def note_for(sol):
    import claude_e2e02d as E
    return E.reasoner_note({"ok": True, "grid": sol})


def score_reply(reply, item):
    g = P.final_grid(reply, item["size"])
    return {"exact": g == item["sol"], "has_grid": g is not None, "solves_puzzle": B.is_solution(item["puz"], g) if g else False}


def prompts(item, with_note):
    import claude_e2e02d as E
    system = E.system_text([], note_for(item["sol"]) if with_note else "")
    return system, [{"role": "user", "content": E.user_text([], item["text"])}]


def run_arm(talk, items, with_note):
    out = []
    for it in items:
        system, msgs = prompts(it, with_note)
        reply = talk.reply(system, msgs, 160)
        out.append({"id": it["id"], "size": it["size"], "arm": "R" if with_note else "N", "reply": reply,
                    "hit_max": getattr(talk, "hit_max", 0), **score_reply(reply, it)})
    return out


def summarize(rows):
    def cnt(rs, k): return sum(1 for r in rs if r[k])
    s = {"n": len(rows), "exact": cnt(rows, "exact"), "has_grid": cnt(rows, "has_grid"), "solves_puzzle": cnt(rows, "solves_puzzle"), "hit_max": cnt(rows, "hit_max")}
    s["by_size"] = {str(z): {"n": sum(1 for r in rows if r["size"] == z), "exact": sum(1 for r in rows if r["size"] == z and r["exact"])} for z in SIZES}
    return s


def main_run(a):
    import claude_e2e02d as E
    bad = E.talker_problem(a.model)
    if bad:
        raise SystemExit("lead0: " + bad)
    talk = E.Talker(a.model)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    summary = {"model": a.model, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for seed in [int(x) for x in a.seeds.split(",")]:
        items = make_items(seed, a.n)
        for with_note in (True, False):
            rows = run_arm(talk, items, with_note)
            name = "seed%d_%s" % (seed, "R" if with_note else "N")
            (out / (name + ".jsonl")).write_text("".join(json.dumps(r) + "\n" for r in rows), newline="")
            summary[name] = summarize(rows)
            print("lead0", name, summary[name]["exact"], "of", summary[name]["n"], flush=True)
    summary["ended_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", newline="")


class _Perfect:
    def reply(self, system, msgs, n):
        i = system.find("(checked):\n")
        return "Here it is:\n" + system[i + len("(checked):\n"):].split("\n\n")[0] if i >= 0 else "I can't tell."


class _Drops:
    def reply(self, system, msgs, n):
        r = _Perfect().reply(system, msgs, n)
        return r.replace("1 2", "1", 1) if r.startswith("Here") else r


def selftest():
    items = make_items(1, 100)
    assert len(items) == 100 and len({i["id"] for i in items}) == 100
    assert all(B.is_solution(i["puz"], i["sol"]) for i in items)
    ok = 0
    r = run_arm(_Perfect(), items, True); ok += summarize(r)["exact"] == 100
    n = run_arm(_Perfect(), items, False); ok += summarize(n)["exact"] == 0
    d = run_arm(_Drops(), items, True); ok += summarize(d)["exact"] < 100
    assert make_items(1, 100) == items          # deterministic
    print("lead0 selftest %d/3 ok" % ok)
    return ok == 3


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--model", required=True); r.add_argument("--out", required=True)
    r.add_argument("--seeds", default="1,2"); r.add_argument("--n", type=int, default=100)
    sub.add_parser("selftest")
    a = ap.parse_args()
    sys.exit(0 if selftest() else 1) if a.cmd == "selftest" else main_run(a)
