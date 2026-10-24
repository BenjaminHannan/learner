"""Write a compact summary of every out/**/result_*.json into this Vast instance's label, so results can be read
from the instance list even when Vast's log service fails. Uses the container's own key (CONTAINER_API_KEY)."""
import json, os, sys, urllib.request
from pathlib import Path

LABEL = sys.argv[1] if len(sys.argv) > 1 else "claude-bb"
parts = []
for f in sorted(Path("out").rglob("result_*.json")):
    try:
        d = json.loads(f.read_text())
    except Exception:
        continue
    name = f.stem.replace("result_", "")
    nums = []
    for k, v in d.items():
        if isinstance(v, dict) and isinstance(v.get("accuracy"), (int, float)):
            nums.append(f"{k}={100 * v['accuracy']:.1f}")
        elif isinstance(v, (int, float)) and ("acc" in k or k.endswith("_rate")) and not isinstance(v, bool):
            nums.append(f"{k}={100 * v:.1f}" if v <= 1 else f"{k}={v:.1f}")
    parts.append(name + ":" + ",".join(nums))
text = (LABEL + "|" + ";".join(parts))[:1000]
print("[label]", text, flush=True)
if os.environ.get("CONTAINER_ID") and os.environ.get("CONTAINER_API_KEY"):
    req = urllib.request.Request(f"https://console.vast.ai/api/v0/instances/{os.environ['CONTAINER_ID']}/",
                                 data=json.dumps({"label": text}).encode(), method="PUT",
                                 headers={"Authorization": "Bearer " + os.environ["CONTAINER_API_KEY"], "Content-Type": "application/json"})
    try:
        print(urllib.request.urlopen(req, timeout=30).read()[:200])
    except Exception as e:
        print("[label] failed", e)
