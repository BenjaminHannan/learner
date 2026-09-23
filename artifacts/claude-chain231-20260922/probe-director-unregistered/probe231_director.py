import sys, tempfile, json
from pathlib import Path
W="/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/scripts"
sys.path.insert(0, W)
import claude_chain231_run as R
import claude_loop231_agent as A
CASES = {
 "a_2hop_work": (["Kestrel's boss is Orrin.", "Orrin works at Palewick Mill."],
                 "Where does Kestrel's boss work?"),
 "b_3hop_city": (["Fenn's boss is Ada.", "Ada's boss is Brisk.", "Brisk's boss is Corvin.",
                  "Corvin lives in Hollowmere."],
                 "What city does Fenn's boss's boss's boss live in?"),
 "b_3hop_city_where": (["Fenn's boss is Ada.", "Ada's boss is Brisk.", "Brisk's boss is Corvin.",
                  "Corvin lives in Hollowmere."],
                 "Where does Fenn's boss's boss's boss live?"),
}
for arm in ("138i", "221", "231"):
    for name, (setup, q) in CASES.items():
        d = Path(tempfile.mkdtemp(prefix=f"p231d-{arm}-"))
        loop = R.build(arm, d)
        saved = []
        for t in setup:
            h = R.facts_hash(loop.nb); loop.turn(t); saved.append(R.facts_hash(loop.nb) != h)
        h = R.facts_hash(loop.nb)
        rep = " ".join(loop.turn(q))
        print(json.dumps({"arm": arm, "case": name, "setup_saved": saved, "q": q, "reply": rep,
                          "wrote": R.facts_hash(loop.nb) != h,
                          "stage": getattr(loop.ears, "last_stage", None) if hasattr(loop, "ears") else None}))
print("chain_parse_a", A.unique_chain231("Where does Kestrel's boss work?") if hasattr(A,"unique_chain231") else None)
