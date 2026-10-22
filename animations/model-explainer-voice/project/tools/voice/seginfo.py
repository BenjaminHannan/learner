"""Show what a narration writer needs for one chapter: every segment with its time slot, caption, how long the caption itself would take to say,
and the scene's own text (headings, chips, labels) so numbers and caveats can be checked.
    python3 tools/voice/seginfo.py ch04"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from speakify import speakify  # noqa: E402
from check_script import predict_dur, scene_text  # noqa: E402

cid = sys.argv[1]
plan = [s for s in json.load(open(os.path.join(ROOT, "narration", "plan.json")))["segments"] if s["ch"] == cid]
ch = json.load(open(os.path.join(ROOT, "content", cid + ".json"))) if os.path.exists(os.path.join(ROOT, "content", cid + ".json")) else None
print(f"chapter {cid}: {len(plan)} segments")
last = None
for s in plan:
    if s["scene"] != last:
        last = s["scene"]
        if ch and s["scene"] != "card":
            print(f"\n=== scene {s['scene']} — everything on screen: {scene_text(ch, s['scene'])[:700]}")
    pred = predict_dur(speakify(s["text"]))
    flag = "  <-- caption alone is TOO LONG to say" if pred > s["slot"] - 0.5 else ""
    print(f"[{s['id']}] slot {s['slot']:.1f} s, aim for <= {s['slot'] - 1.0:.1f} s of speech (caption alone: {pred:.1f} s){flag}\n    caption: {s['text']}")
