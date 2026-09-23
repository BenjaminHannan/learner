"""Probe: in-process restart, compare nb.facts keys vs values vs notebook_triples."""
import sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fable_marks123_all as M, fable_loop90_agent as L90
mod, dcls, _, _ = M.load_agent(str(ROOT / "scripts/fable_loop138i_agent.py"))
base = M.load_base_cfg(str(ROOT / "artifacts/fable-agent138i-20260922/loop138i-config.json"))
tmp = Path(tempfile.mkdtemp(prefix="claude_demo_vals_")) / "state"; tmp.mkdir(parents=True)
d = M.make_daemon(dcls, base, tmp)
for i, t in enumerate(["My name is Juno.", "Kim's boss is Lee.", "Hi!"]):
    f = tmp / "inbox" / f"a{i}.txt"; f.write_text(t); d.process_file(f)
del d
d = M.make_daemon(dcls, base, tmp)
nb = d.loop.nb
print(type(nb).__name__, type(nb.facts).__name__, len(nb.facts), len(list(nb.facts.values())))
print(L90.notebook_triples(nb))
f = tmp / "inbox" / "b.txt"; f.write_text("What have I taught you?"); d.process_file(f)
print((tmp / "outbox" / "b.txt").read_text())
