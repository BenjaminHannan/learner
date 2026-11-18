"""CPU test of analyze.py (PREREG-2 mode) on fake summary lines. Usage: python3 skillsleep/tests/test_analyze.py"""
import json, subprocess, sys, tempfile
from pathlib import Path

AN = Path(__file__).parent.parent / "analyze.py"
d = Path(tempfile.mkdtemp()); rows = []


def line(arm, dom, per, ask=None, not_real=0):
    rows.append({"arm": arm, "domain": dom, "sims": sum(map(len, per.values())), "pass": sum(map(sum, per.values())), "per_task": per, "per_task_real": per, "not_real": not_real,
                 "ask": ask or {"writes": 40, "asked": 20, "rate": 0.5, "questions": 30, "q_per_sim": 0.4, "real_sims": 80}})


T = [str(i) for i in range(40)]
def pt(base, extra=0): return {t: [1] * 2 + [0] * 2 if i < base else [1, 1, 1, 0] if i < base + extra else [0] * 4 for i, t in enumerate(T)}
line("A0", "retail_test", pt(12)); line("A0", "airline_test", {str(i): [1, 0] for i in range(20)}); line("A0", "arc_easy", {str(i): [1] for i in range(200)})
for arm, extra, ask_a in (("C1s1", 3, 18), ("C1s2", 3, 18), ("C2s1", 12, 20), ("C2s2", 12, 20), ("C3s1", 9, 4), ("C3s2", 14, 20)):
    line(arm, "retail_test", pt(12, extra), {"writes": 40, "asked": ask_a, "rate": ask_a / 40, "questions": 30, "q_per_sim": 0.4, "real_sims": 160}, not_real=2)
    line(arm, "airline_test", {str(i): [1, 0] for i in range(20)}); line(arm, "arc_easy", {str(i): [1] for i in range(200)})
for a in ("C3s1", "C3s2"):
    json.dump({"arm": a, "opt_steps": 100, "fork_pairs": 120, "pairs": 33, "dpo_sat_step": 70 if a == "C3s1" else 12}, open(d / f"train_info_{a}.json", "w"))
(d / "summary.jsonl").write_text("\n".join(map(json.dumps, rows)) + "\n")
out = subprocess.run([sys.executable, str(AN), str(d / "summary.jsonl")], capture_output=True, text=True); print(out.stdout[-3500:], out.stderr[-800:])
o = out.stdout
assert out.returncode == 0
assert "Q1 longer night helps: PASS" in o, "C2 is +30 points over A0 in both seeds"
assert "Q2 bad examples help at dose: PASS" in o and "Q3 near-miss pairs help: FAIL" in o
assert "Q4 pairs not saturated (C3s1" in o and "NOT saturated" in o and "SATURATED early" in o
assert "HARM: ask" in o and "No harm C3: FAIL" in o and "No harm C2: PASS" in o  # C3s1 asks 4/40 vs A0 20/40
assert "excluded sims" in o and "| 2, 0 |" in o
print("ANALYZE TEST OK")
