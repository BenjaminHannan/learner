import os, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "fable-redteam110-20260921"
CFG = ROOT / "artifacts" / "fable-loop102-20260921" / "loop102-config.json"
root = Path(tempfile.mkdtemp())
env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
proc = subprocess.Popen(
    ["uv", "run", "--offline", "--no-project", "--python", "3.12",
     "--with", "torch", "--with", "numpy", "python", "-B",
     str(ROOT / "scripts" / "fable_loop102_agent.py"),
     "--daemon", "--dir", str(root), "--config", str(CFG),
     "--idle-seconds", "3600"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
for _ in range(2400):
    if (root / "daemon_status.json").exists() or proc.poll() is not None:
        break
    time.sleep(0.05)
def say(text, name):
    (root / "inbox" / name).write_text(text)
    for _ in range(2400):
        if (root / "done" / name).exists():
            break
        time.sleep(0.05)
    print(name, "->", (root / "outbox" / name).read_text().strip()[:150])

say("Mira's city is Lisbon.", 'm0.txt')
say("Is Mira's city Lisbon? Also teach Mira's pet is a cat.", 'm1.txt')
say("Who is Mira's city?", 'm2.txt')
# EXPECTED (sealed pre-run): turn 1 must contain 'Was that a question?'; turn 2 must contain 'Lisbon'
# OBSERVED: BUG -- turn 1 lacks 'Was that a question?' (got "I didn't understand that. Could you say it another way?\n")
(root/'STOP').write_text('stop\n'); proc.wait(timeout=60)
