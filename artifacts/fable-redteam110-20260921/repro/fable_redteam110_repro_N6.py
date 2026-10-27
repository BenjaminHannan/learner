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

say('CM Punk is married to AJ Lee', 'm0.txt')
say('Which language is the native tongue of the person who is married to CM Punk?', 'm1.txt')
# EXPECTED (sealed pre-run): {'abstain_on': [1], 'zero_fact_writes_on': [1], 'checks': [{'turn': 1, 'absent': ['English', 'Russian']}]}
# OBSERVED: BUG -- turn 1 should abstain (got 'Was that a question?\n')
(root/'STOP').write_text('stop\n'); proc.wait(timeout=60)
