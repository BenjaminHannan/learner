"""Diagnosis only: alternate wordings on a fresh state (not graded, not the demo script)."""
import sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fable_marks123_all as M, fable_loop90_agent as L90
mod, dcls, _, _ = M.load_agent(str(ROOT / "scripts/fable_loop138i_agent.py"))
base = M.load_base_cfg(str(ROOT / "artifacts/fable-agent138i-20260922/loop138i-config.json"))
tmp = Path(tempfile.mkdtemp(prefix="claude_demo_var_")) / "state"; tmp.mkdir(parents=True)
d = M.make_daemon(dcls, base, tmp)
n = [0]
def say(t):
    n[0] += 1; f = tmp / "inbox" / ("v%03d.txt" % n[0]); f.write_text(t)
    b = sorted(map(tuple, L90.notebook_triples(d.loop.nb)))
    d.process_file(f)
    a = sorted(map(tuple, L90.notebook_triples(d.loop.nb)))
    print("%-48s -> %s | +%s -%s" % (t, (tmp / "outbox" / f.name).read_text().strip()[:110],
          [x for x in a if x not in b], [x for x in b if x not in a]))
for t in ["My name is Juno.", "Do you remember my name?", "What's my name?",
          "Kim's boss is Lee.", "Lee lives in Oslo.",
          "Where does Lee live?", "Where does Kim's boss live?", "What city does Kim's boss live in?",
          "What is the city of Kim's boss?", "Where does the boss of Kim live?",
          "Lee speaks Norwegian.", "Lee speaks English.", "What languages does Lee speak?",
          "What language does Lee speak?", "Does Lee speak English?", "Does Lee speak French?",
          "Lee moved to Bergen.", "Lee lives in Bergen.", "Where does Lee live?",
          "Kim's sister is Juno.", "My sister is Kim.", "Who is my sister?",
          "Kim's dog is Biscuit.", "What is Kim's dog?", "Who is Lee?",
          "What do you know about Kim?", "What did I teach you?", "Who taught you that?",
          "What can you do?", "How old is Kim?", "Who told you Kim's boss is Lee?"]:
    say(t)
