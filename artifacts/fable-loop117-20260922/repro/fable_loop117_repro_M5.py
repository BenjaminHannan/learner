import os, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "artifacts" / "fable-loop117-20260922" / "loop117-config.json"
root = Path(tempfile.mkdtemp())
env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
proc = subprocess.Popen(
    ["uv", "run", "--offline", "--no-project", "--python", "3.12",
     "--with", "torch", "--with", "numpy", "python", "-B",
     str(ROOT / "scripts" / "fable_loop117_agent.py"),
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
say("WHO IS MIRA'S CITY?", 'm1.txt')
# EXPECTED (same as sealed exp-110 M5): turn 1 must contain 'Lisbon'
(root/'STOP').write_text('stop\n'); proc.wait(timeout=60)
