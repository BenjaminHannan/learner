"""Probe runner with restarts. Usage: restart_probe.py <agent.py> <config> <fresh workdir> <probe.json>
probe.json = list of dialogs (list of turns). Special turns:
  "__RESTART__" -> drop the daemon, build a new daemon on the same root (notebook reloaded from disk)
  "__TRIPLES__" -> print stored triples now
Per turn prints reply and the change in notebook event count (writes)."""
import sys, json, shutil, gc
from pathlib import Path
sys.path.insert(0, 'scripts')
import fable_marks123_all as M
import fable_loop90_agent as L90
from claude_fix228_srcguard import install_srcguard228
install_srcguard228()  # required for new harnesses (exp 228)
mod, dcls, _, _ = M.load_agent(sys.argv[1]); base = M.load_base_cfg(sys.argv[2]); S = Path(sys.argv[3]); dialogs = json.load(open(sys.argv[4]))
def nev(d):
    nb = d.loop.nb
    for o in (nb, getattr(nb, 'nb', None)):
        if o is not None and hasattr(o, 'events'): return len(o.events)
    return -1
def trip(d):
    return [tuple(x) for x in L90.notebook_triples(d.loop.nb)]
for i, msgs in enumerate(dialogs):
    root = S / f"d{i:02d}"; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root); k = 0; nres = 0
    for t in msgs:
        if t == "__RESTART__":
            del d; gc.collect(); d = M.make_daemon(dcls, base, root); nres += 1
            print(f"{i:02d} -- RESTART {nres} --"); continue
        if t == "__TRIPLES__":
            print(f"{i:02d}   TRIPLES {trip(d)}"); continue
        f = root / "inbox" / f"m{k:02d}.txt"; f.write_text(t); b = nev(d)
        try:
            d.process_file(f); rep = (root / "outbox" / f"m{k:02d}.txt").read_text().strip()
        except Exception as e:
            rep = f"CRASH {type(e).__name__}: {e}"
        print(f"{i:02d} {t!r} -> {rep!r}  [+{nev(d)-b} ev]"); k += 1
    print(f"{i:02d}   STORED {trip(d)}")
