"""Usage (from repo root): run_probes.py <agent.py> <config> <fresh workdir> <probes.json> <out.json>
Each dialog in its own fresh dir; "__RESTART__" rebuilds the daemon on the same dir. Records reply, event delta, triples after every turn."""
import sys, json, shutil, gc
from pathlib import Path
sys.path.insert(0, 'scripts')
import fable_marks123_all as M
import fable_loop90_agent as L90
mod, dcls, _, _ = M.load_agent(sys.argv[1]); base = M.load_base_cfg(sys.argv[2]); S = Path(sys.argv[3]); P = json.load(open(sys.argv[4]))
def nev(d):
    nb = d.loop.nb
    for o in (nb, getattr(nb, 'nb', None)):
        if o is not None and hasattr(o, 'events'): return len(o.events)
    return -1
trip = lambda d: [list(x) for x in L90.notebook_triples(d.loop.nb)]
out = []
for p in P:
    root = S / p["id"]; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root); k = 0; rows = []
    for t in p["turns"]:
        if t == "__RESTART__":
            del d; gc.collect(); d = M.make_daemon(dcls, base, root)
            rows.append({"restart": True, "triples": trip(d)}); continue
        kind, text = t.split("|", 1)
        f = root / "inbox" / f"m{k:02d}.txt"; f.write_text(text); b = nev(d)
        try:
            d.process_file(f); rep = (root / "outbox" / f"m{k:02d}.txt").read_text().strip()
        except Exception as e:
            rep = f"CRASH {type(e).__name__}: {e}"
        rows.append({"kind": kind, "turn": text, "reply": rep, "ev": nev(d) - b, "triples": trip(d)}); k += 1
    out.append({"id": p["id"], "feature": p["feature"], "rows": rows, "stored": trip(d)})
    del d; gc.collect(); shutil.rmtree(root, ignore_errors=True)
json.dump(out, open(sys.argv[5], "w"), indent=1)
print("done", len(out))
