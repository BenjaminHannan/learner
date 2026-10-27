#!/usr/bin/env python3
"""Smoke test of claude_dir_sl_read.py extract + judge on RANDOM-INIT nets (no practised net exists on the cloud box).
Builds a fake source dir and a fake baseline run dir whose adapt.json/source.json hold the counts the sealed harness scorer gives
those random nets, runs extract for rung 64 only, and checks every consistency line is true. Says nothing about any real result."""
import json, subprocess, sys, tempfile
from pathlib import Path
import torch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_fewex_bench as B, claude_fewex_data as D, claude_fewex_net as N
B.N = N
torch.manual_seed(11)
d = Path(tempfile.mkdtemp())
(src, run) = (d / "src", d / "run"); src.mkdir(); run.mkdir()
net0, net64 = N.Net("loop"), N.Net("loop")
torch.save(net0.state_dict(), src / "source.pt"); torch.save(net64.state_dict(), run / "k64.pt")
maze = D.panels()[0]["dev"][9]
old = D.old_panels(D.SOURCE_SEED + 300)
(src / "source.json").write_text(json.dumps({"arm": "loop", "seed": 0, "fixed_depth": 16, "old": {k: B.score(net0, v, 16) for k, v in old.items()}}))
adapt = {"arm": "loop", "seed": 0, "fixed_depth": 16, "rungs": {"0": {"9": B.score(net0, maze, 16)}, "64": {"9": B.score(net64, maze, 16)}}}
(d / "adapt.json").write_text(json.dumps(adapt))
subprocess.run([sys.executable, str(ROOT / "scripts/claude_dir_sl_read.py"), "extract", "--source-dir", str(src), "--run-dir", str(run),
                "--adapt-json", str(d / "adapt.json"), "--seed", "0", "--out", str(d / "rec.json"), "--rungs", "64", "--threads", "4"], check=True)
rec = json.loads((d / "rec.json").read_text())
assert rec["consistency"] and all(v["ok"] for v in rec["consistency"].values()), rec["consistency"]
import shutil; shutil.copy(d / "rec.json", "/tmp/sl_smoke_rec.json")
print(json.dumps({"smoke": "ok", "nets": sorted(rec["nets"]), "consistency_keys": sorted(rec["consistency"]), "items": {k: len(v) for k, v in rec["nets"]["k64"].items()}}))
