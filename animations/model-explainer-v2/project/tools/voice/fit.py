"""Fit report: how each made clip compares with the time slot of its caption.
    VOICE_AUDIO_DIR=<local clips dir> python3 tools/voice/fit.py [--only ch04] [--tempo-max 1.0] [--json out.json]
Classes: ok (clip fits its slot), tempo (needs a small speed-up, at most --tempo-max), shorten (too long even with the speed-up: rewrite shorter).
The last line of a scene may use extra time (the scene fade), see EXTRA_LAST."""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AUDIO = os.environ.get("VOICE_AUDIO_DIR") or os.path.join(ROOT, "narration", "audio")
EXTRA_LAST = 0.3   # seconds the last caption of a scene may run past its slot (the next scene's first caption starts 0.6 s after the cut)


def classify(plan, index, tempo_max):
    rows = []
    last_of_scene = {}
    for s in plan:
        last_of_scene[(s["ch"], s["scene"])] = s["id"]
    for s in plan:
        e = index.get(s["id"])
        if not e or "dur" not in e:
            rows.append({"id": s["id"], "cls": "missing", "slot": s["slot"]})
            continue
        slot = s["slot"] + (EXTRA_LAST if last_of_scene[(s["ch"], s["scene"])] == s["id"] else 0)
        need = e["dur"] / slot
        cls = "ok" if need <= 1.0 else ("tempo" if need <= tempo_max else "shorten")
        rows.append({"id": s["id"], "cls": cls, "dur": e["dur"], "slot": round(slot, 2), "need": round(need, 3), "source": e.get("source"), "spoken": e["spoken"]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--tempo-max", type=float, default=1.0)
    ap.add_argument("--json")
    a = ap.parse_args()
    plan = json.load(open(os.path.join(ROOT, "narration", "plan.json")))["segments"]
    index = json.load(open(os.path.join(AUDIO, "index.json")))
    rows = classify([s for s in plan if not a.only or s["ch"] in a.only], index, a.tempo_max)
    from collections import Counter
    print(dict(Counter(r["cls"] for r in rows)))
    for r in rows:
        if r["cls"] in ("tempo", "shorten", "missing"):
            print(f"  {r['cls']:8s} {r['id']:14s} clip {r.get('dur', 0):5.1f} s vs slot {r['slot']:5.1f} s (x{r.get('need', 0):.2f})  {r.get('spoken', '')[:90]}")
    used = sum(r.get("dur", 0) for r in rows)
    print(f"speech total {used / 60:.1f} min of {plan[-1]['end'] / 60:.1f} min")
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
    sys.exit(1 if any(r["cls"] in ("shorten", "missing") for r in rows) else 0)


if __name__ == "__main__":
    main()
