import sys, json, shutil
from pathlib import Path
sys.path.insert(0, 'scripts')
import fable_marks123_all as M
mod, dcls, _, _ = M.load_agent(sys.argv[1]); base = M.load_base_cfg(sys.argv[2]); S = Path(sys.argv[3]); dialogs = json.load(open(sys.argv[4]))
for i, msgs in enumerate(dialogs):
    root = S / f"d{i:02d}"; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root)
    for j, t in enumerate(msgs):
        f = root / "inbox" / f"m{j:02d}.txt"; f.write_text(t); d.process_file(f)
        rep = (root / "outbox" / f"m{j:02d}.txt").read_text().strip()
        if t.strip().endswith('?') or j == len(msgs)-1: print(f"{i:02d} {t!r} -> {rep[:90]!r}")
