"""Turn tools/voice/extent.mjs output into the least scene lengths pace.py must respect.
    python3 tools/voice/extent_need.py EXTENT.json narration/extent-min.json [--end-margin 1.0] [--start-margin 1.5]
For each scene whose last picture tween ends less than --end-margin seconds before the scene end (or starts less than --start-margin before it),
raises that scene's least length by the shortfall (kept in the json as {"chNN.sNN": seconds}). Prints how many scenes were raised; exit 0 always."""
import json, os, sys

ext = json.load(open(sys.argv[1]))
out = sys.argv[2]
em = float(sys.argv[sys.argv.index("--end-margin") + 1]) if "--end-margin" in sys.argv else 1.0
sm = float(sys.argv[sys.argv.index("--start-margin") + 1]) if "--start-margin" in sys.argv else 1.5
cur = json.load(open(out)) if os.path.exists(out) else {}
raised = 0
for k, v in ext.items():
    if "-s" not in k:
        continue                                  # title cards and the end card keep their fixed length
    cid, sid = k.split("-", 1)
    d = v["end"] - v["t0"]
    short = max(em - v["endMargin"], sm - v["startMargin"], 0)
    if short > 0.01:
        key = f"{cid}.{sid}"
        want = d + short + 0.5
        if want > cur.get(key, 0):
            cur[key] = round(want, 1); raised += 1
json.dump(cur, open(out, "w"), indent=1)
print(f"{raised} scene(s) raised; {len(cur)} in {out}")
