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
    if "error" in d:
        nums.append("ERR=" + "".join(c for c in d["error"] if c.isalnum() or c in " _.:()")[:120])
    sc = d.get("scores") if isinstance(d.get("scores"), dict) else {}
    for mode, m in (("w", sc.get("weights")), ("d", sc.get("diary"))):  # Sleep-B results (backbone/sleep/brain/sleepb.py)
        if isinstance(m, dict):
            f = m.get("forward") or {}
            nums += [f"{mode}C4={100 * (f.get('C4') or 0):.0f}", f"{mode}C2={100 * (f.get('C2') or 0):.0f}", f"{mode}C1={100 * (f.get('C1') or 0):.0f}",  # None (class absent) -> 0
                     f"{mode}2hop={100 * (m.get('twohop') or {}).get('acc', 0):.0f}", f"{mode}chg={100 * (m.get('changed') or {}).get('new', 0):.0f}",
                     f"{mode}rt={100 * (m.get('routine') or {}).get('acc', 0):.0f}", f"{mode}int={100 * (m.get('integration') or 0):.0f}",
                     f"{mode}pool={100 * (m.get('pooled') or 0):.0f}"]
    r = sc.get("router")  # Sleep-B addendum 1 arms: router R pooled / integration
    if isinstance(r, dict):
        nums += [f"rpool={100 * (r.get('pooled') or 0):.0f}", f"rint={100 * (r.get('integration') or 0):.0f}"]
    ae = d.get("arc_easy")  # Sleep-B: ARC-Easy accuracy of the slept model
    if isinstance(ae, dict) and isinstance(ae.get("acc"), (int, float)):
        nums.append(f"arc={100 * ae['acc']:.1f}")
    if name.endswith(".partial"):  # unfinished arm: nights done so far
        nums.append(f"n{len(d.get('nights') or [])}")
    elif d.get("nights"):  # Sleep-B: which nights the morning gate reverted (1 = reverted)
        nums.append("rv=" + "".join("1" if isinstance(n, dict) and n.get("reverted") else "0" for n in d["nights"]))
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
