"""Copy back per-run result files from a stopped box with execute+cat, check each parses, write to results/boxID/out."""
import json, sys
from pathlib import Path
import rent
iid, arm = int(sys.argv[1]), sys.argv[2]
out = Path(f"results/box{iid}/out"); out.mkdir(parents=True, exist_ok=True)
ok = 0
for s in range(6):
    for suf in (".json", "-rows.json"):
        name = f"arm{arm}-seed{s}{suf}"
        b = rent.exec_cat(iid, f"/job/out/{name}")
        try:
            json.loads(b); (out / name).write_bytes(b); ok += 1
        except Exception:
            print("FAIL", name, (b or b"")[:120])
print(json.dumps({"box": iid, "arm": arm, "files_ok": ok, "of": 12}))
