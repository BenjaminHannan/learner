"""Verifier runner for exp 236: dialog_nb.py + 228 guard + '__RESTART__' turns (new daemon, same dir)."""
import sys, json, shutil
from pathlib import Path
sys.path.insert(0, 'scripts')
from claude_fix228_srcguard import install_srcguard228
install_srcguard228()
import fable_marks123_all as M
import fable_notebook_contract as C
import fable_loop90_agent as L90
mod, dcls, _, _ = M.load_agent(sys.argv[1]); install_srcguard228()
base = M.load_base_cfg(sys.argv[2]); S = Path(sys.argv[3]); dialogs = json.load(open(sys.argv[4]))
out = []
for i, msgs in enumerate(dialogs):
    root = S / f"d{i:02d}"; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root); rows = []
    for j, t in enumerate(msgs):
        if t == "__RESTART__":
            d = M.make_daemon(dcls, base, root); rows.append([t, "(restarted)"]); print(f"{i:02d} RESTART"); continue
        f = root / "inbox" / f"m{j:02d}.txt"; f.write_text(t); d.process_file(f)
        rep = (root / "outbox" / f"m{j:02d}.txt").read_text().strip()
        rows.append([t, rep]); print(f"{i:02d} {t!r} -> {rep!r}")
    st = [list(x) for x in L90.notebook_triples(d.loop.nb)]
    print(f"{i:02d}   STORED {st}")
    out.append({"i": i, "turns": rows, "stored": st})
json.dump(out, open(sys.argv[5], "w"), indent=1)
