#!/usr/bin/env python3
"""vast pack for the copy-talker test (PASS-MARKS-CT.md): rent5's pack with this round's marks added.
Usage: rent_ct.py SEED OUTDIR"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rent5
rent5.OWN = rent5.OWN + ["PASS-MARKS-CT.md"]
COMMON = "--gen 8000 --kinds 6 --block-r6 --extra-eval english_test/NEW-KINDS-R5.json --extra-eval2 english_test/NEW-KINDS2-R6.json --tag -ct"
def runs(seed):  # allptr only for seed 0 (control = round 6 six arm; PASS-MARKS-CT.md)
    return [f"--arm {a} {COMMON}" for a in ((("allptr",) if seed == 0 else ()) + ("copytalk", "copytalk_nocore"))]

if __name__ == "__main__":
    rent5.pack(int(sys.argv[1]), sys.argv[2], "", runs(int(sys.argv[1])))
