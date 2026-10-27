#!/usr/bin/env python3
"""Exp 257 -- REPORT ONLY, run after the registered 257 run: v4.1 ear on the 235b panel, scored by the
sealed 235b scorer (claude_smolear235b_score.main, unchanged; its own loader, panel and arm-B preds),
with relation table v2 installed (v4.1 emits v2 relations). Never used for tuning.
python claude_smolear257_on235b.py --panel P235b --a-preds A.json --b-preds B235b.json --tau-file TAU.json --out S.json"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235b_score as SC  # noqa: E402

if __name__ == "__main__":
    SC.main()
