# usage: run_cases.py <agent.py> <config> <workdir> <cases.json> <out.jsonl> <arm>
import sys, json, shutil, time
from pathlib import Path
sys.path.insert(0, 'scripts')
import fable_marks123_all as M
import fable_notebook_contract as C
import fable_loop90_agent as L90
agent, cfg, wd, cases_p, out_p, arm = sys.argv[1:7]
mod, dcls, _, _ = M.load_agent(agent); base = M.load_base_cfg(cfg); W = Path(wd)
cases = json.load(open(cases_p))
def trip(d, root):
    nb = d.loop.nb if hasattr(d, 'loop') else C.Notebook(root / "notebook")
    return sorted(tuple(map(str, x)) for x in L90.notebook_triples(nb))
with open(out_p, 'w') as out:
    for c in cases:
        root = W / c['id']; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        turns = c['setup'] + [c['question']]; reps = []
        for j, t in enumerate(turns):
            if j == len(turns) - 1:
                before = trip(d, root); t0 = time.perf_counter()
            f = root / "inbox" / f"m{j:02d}.txt"; f.write_text(t); d.process_file(f)
            reps.append((root / "outbox" / f"m{j:02d}.txt").read_text().strip())
        ms = (time.perf_counter() - t0) * 1000
        after = trip(d, root)
        out.write(json.dumps({"id": c['id'], "arm": arm, "setup_replies": reps[:-1], "question": c['question'],
            "reply": reps[-1], "before": before, "after": after, "q_ms": round(ms, 2)}) + "\n")
        print(arm, c['id'], repr(c['question']), '->', repr(reps[-1]), flush=True)
