#!/usr/bin/env python3
"""138nb step 1: reproduce on 138n that 190 answers with no label.
30+ dev dialogs in own wording, fictional names. Prints replies + stage.
Does not quote any blind panel. New file only."""
from __future__ import annotations
import copy, json, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138n_agent as AG138N

# each dialog: (id, turns)
D = [
 ("d01", ["Bex's mother is Talia.", "Whose mother is Talia?"]),
 ("d02", ["Bex's mother is Talia.", "Rin's mother is Talia.", "Whose mother is Talia?"]),
 ("d03", ["Bex's boss is Lee.", "Who has Lee as their boss?"]),
 ("d04", ["Bex's boss is Lee.", "Rin's boss is Lee.", "Who has Lee as their boss?"]),
 ("d05", ["Bex's city is Oslo.", "Who lives in Oslo?"]),
 ("d06", ["Bex's city is Oslo.", "Rin's city is Oslo.", "Who lives in Oslo?"]),
 ("d07", ["Bex's birthplace is Paris.", "Who was born in Paris?"]),
 ("d08", ["Bex's birthplace is Paris.", "Rin's birthplace is Paris.", "Who was born in Paris?"]),
 ("d09", ["My boss is Lee.", "Who has Lee as their boss?"]),
 ("d10", ["My city is Oslo.", "Who lives in Oslo?"]),
 ("d11", ["Bex's mother is Talia.", "Whose mother is Zara?"]),  # Zara unknown -> called
 ("d12", ["Bex's mother is Talia.", "Rin is here.", "Whose mother is Rin?"]),  # Rin known, no match -> whose
 ("d13", ["Bex's city is Oslo.", "Rin is here.", "Who lives in Rin?"]),  # known value no match? (odd but tests abstain)
 ("d14", ["Bex's mother is Talia.", "Whose mother is Quix?"]),  # unknown -> called
 ("d15", ["Bex's teacher is Moss.", "Whose teacher is Moss?"]),
 ("d16", ["Bex's coach is Tobin.", "Who has Tobin as their coach?"]),
 ("d17", ["Bex's spouse is Wren.", "Whose spouse is Wren?"]),
 ("d18", ["Bex's friend is Pell.", "Who has Pell as their friend?"]),
 ("d19", ["Bex's school is Harlow.", "Whose school is Harlow?"]),
 ("d20", ["Bex's pet is Miso.", "Whose pet is Miso?"]),
 ("d21", ["Bex's mother is Talia.", "Who is Bex's mother?"]),  # forward control
 ("d22", ["Bex's city is Oslo.", "What is Bex's city?"]),  # forward control
 ("d23", ["Bex's boss is Lee.", "Bex's boss is Sam.", "Whose boss is Lee?"]),  # superseded -> no match
 ("d24", ["Bex's mother is Talia.", "Bex's mother is Zara.", "Whose mother is Talia?"]),  # corrected away
 ("d25", ["My mother is Talia.", "Whose mother is Talia?"]),  # my subject reverse
 ("d26", ["Bex's sister is Lark.", "Whose sister is Lark?"]),
 ("d27", ["Bex's brother is Pike.", "Rin's brother is Pike.", "Who has Pike as their brother?"]),
 ("d28", ["Bex's country is Wendland.", "Whose country is Wendland?"]),
 ("d29", ["Bex's hometown is Harlow Cross.", "Whose hometown is Harlow Cross?"]),
 ("d30", ["Bex's dog is Biscuit.", "Whose dog is Biscuit?"]),
 ("d31", ["Bex's mother is Talia.", "Who lives in Oslo?"]),  # no-match lives, Oslo unknown
 ("d32", ["Bex's boss is Lee.", "Who was born in Paris?"]),  # unknown born value
 ("d33", ["My birthplace is Paris.", "Who was born in Paris?"]),  # my born
 ("d34", ["Bex's city is Oslo.", "What is Bex's mother?"]),  # forward abstain control
 ("d35", ["Bex's mother is Talia.", "Rin's mother is Talia.", "Who has Talia as their mother?"]),
 ("d36", ["Bex's neighbour is Cato.", "Whose neighbour is Cato?"]),
]

def run():
    base = copy.deepcopy(AG138N.DEFAULT_CONFIG138N)
    n_label = 0; n_subject = 0; n_abstain = 0
    for did, turns in D:
        sd = Path(tempfile.mkdtemp(prefix="nb-dev-"))
        cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
        loop = AG138N.build_agent138n(cfg)
        for j, t in enumerate(turns):
            rep = " ".join(loop.turn(t))
            st = getattr(getattr(loop, "_inner138j_ears", None), "last_stage", "") or getattr(getattr(loop, "ears", None), "last_stage", "")
            # loop.turn is wrapped; stage lives on inner ears
            print(f"{did} t{j}: stage={st} reply={rep}", flush=True)
            if j == len(turns) - 1:
                if "(worked out backwards)" in rep: n_label += 1
                if rep.startswith("I don't know anyone"): n_abstain += 1
                elif "'s " in rep and " is " in rep: n_subject += 1
        shutil.rmtree(sd, ignore_errors=True)
    print(f"SUMMARY dialogs={len(D)} final_subject_no_label={n_subject} final_with_label={n_label} final_abstain={n_abstain}")

if __name__ == "__main__":
    run()
