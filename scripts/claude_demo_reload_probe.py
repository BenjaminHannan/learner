"""Probe: reload a COPY of the main dry-run state dir and dump fact records."""
import sys, shutil, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fable_marks123_all as M
src = Path(sys.argv[1])
tmp = Path(tempfile.mkdtemp(prefix="claude_demo_reload_")) / "state"
shutil.copytree(src, tmp)
mod, dcls, _, _ = M.load_agent(str(ROOT / "scripts/fable_loop138i_agent.py"))
base = M.load_base_cfg(str(ROOT / "artifacts/fable-agent138i-20260922/loop138i-config.json"))
d = M.make_daemon(dcls, base, tmp)
for k, v in d.loop.nb.facts.items():
    print(k, v["subject"], v["relation"], v["value"], d.loop.nb.active(k), v.get("source"))
print(d.loop.nb.entities)
import fable_loop90_agent as L90
print("triples on fresh-process boot:", L90.notebook_triples(d.loop.nb))
