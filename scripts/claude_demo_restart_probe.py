"""Probe: does loop138i duplicate facts / lose USER name on restart? Copies state first."""
import sys, json, shutil, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fable_marks123_all as M
import fable_loop90_agent as L90
mod, dcls, _, _ = M.load_agent(str(ROOT / "scripts/fable_loop138i_agent.py"))
base = M.load_base_cfg(str(ROOT / "artifacts/fable-agent138i-20260922/loop138i-config.json"))
tmp = Path(tempfile.mkdtemp(prefix="claude_demo_probe_")) / "state"; tmp.mkdir(parents=True)
d = M.make_daemon(dcls, base, tmp)
def say(d, name, text):
    f = tmp / "inbox" / name; f.write_text(text); d.process_file(f)
    return (tmp / "outbox" / name).read_text().strip()
print("A", say(d, "a1.txt", "My name is Juno."))
print("A", say(d, "a2.txt", "Kim's boss is Lee."))
print("facts before:", {k: (v["subject"], v["relation"], v["value"], d.loop.nb.active(k)) for k, v in d.loop.nb.facts.items()})
d2 = M.make_daemon(dcls, base, tmp)
print("notes:", d2.loop.notes[-5:] if hasattr(d2.loop, "notes") else None)
print("facts after:", {k: (v["subject"], v["relation"], v["value"], d2.loop.nb.active(k), v.get("source")) for k, v in d2.loop.nb.facts.items()})
print("entities:", dict(list(d2.loop.nb.entities.items())[:10]))
print("B", say(d2, "b1.txt", "What is my name?"))
print("B", say(d2, "b2.txt", "Who is Kim's boss?"))
print("B", say(d2, "b3.txt", "Do you remember my name?"))
