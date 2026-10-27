"""Drop tries whose every assistant reply is empty (server OOM -> 404 -> saved as fake tries). Keeps a .bak copy."""
import json, shutil, sys
for f in sys.argv[1:]:
    rows = [l for l in open(f) if l.strip()]
    keep = [l for l in rows if not all(m["content"] == "" for m in json.loads(l)["messages"] if m["role"] == "assistant")]
    shutil.copy(f, f + ".bak_before_oom_clean")
    open(f, "w").writelines(keep)
    print(f, len(rows), "->", len(keep))
