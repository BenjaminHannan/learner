"""Night step 3: sort the day into lessons and render them for training.
Usage: build.py TOKENIZER_DIR ENV_JSON OUT_DIR DAY_RESULTS [FIX_RESULTS ...]
Writes OUT_DIR/night.jsonl (kind pos | pair | neg) and OUT_DIR/build_stats.json. Everything is rendered with the NORMAL system prompt (no critique)."""
import collections, json, sys
from common import ok, real, sims
from render import load_tok, render_traj

MAXTOK = 16384
tokd, envp, outd, dayp = sys.argv[1:5]; fixps = sys.argv[5:]
tok = load_tok(tokd); env = json.load(open(envp))
stats = collections.Counter(); cache = {}


def enc(s):  # (ids, mask) or None; each sim rendered once
    k = s["id"]
    if k not in cache:
        try:
            ids, mask = render_traj(tok, env, s["messages"])
            cache[k] = None if len(ids) > MAXTOK else {"ids": ids, "mask": mask}
            stats["dropped_over_%d" % MAXTOK] += cache[k] is None
        except Exception as e:
            stats["render_error"] += 1; print("render error", s["task_id"], str(e)[:100]); cache[k] = None
    return cache[k]


day = collections.defaultdict(list); fix = collections.defaultdict(list)
for s in sims(dayp):
    if real(s):
        day[str(s["task_id"])].append(s)
for p in fixps:
    for s in sims(p):
        if real(s) and ok(s):
            fix[str(s["task_id"])].append(s)  # only retries that passed tau2's check
rows = []
for t in sorted(day, key=int):
    good = [s for s in day[t] if ok(s)]; bad = [s for s in day[t] if not ok(s)]
    pool = good + fix.get(t, [])  # chosen pool: passing day runs first, then verified retries
    stats["tasks"] += 1; stats["tasks_with_pass"] += bool(good); stats["tasks_fixed"] += (not good and bool(fix.get(t)))
    for s in pool:
        e = enc(s)
        if e:
            rows.append({"kind": "pos", "task": t, "src": "day" if s in good else "fix", **e}); stats["pos"] += 1
    for i, s in enumerate(bad):
        e = enc(s)
        if not e:
            continue
        if pool:
            c = enc(pool[i % len(pool)])
            if c:
                rows.append({"kind": "pair", "task": t, "chosen": c, "rejected": e}); stats["pairs"] += 1
        else:
            rows.append({"kind": "neg", "task": t, **e}); stats["negs"] += 1
stats["tokens_pos_total"] = sum(len(r["ids"]) for r in rows if r["kind"] == "pos")
stats["assistant_tokens_pos"] = sum(sum(r["mask"]) for r in rows if r["kind"] == "pos")
with open(outd + "/night.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
json.dump(dict(stats), open(outd + "/build_stats.json", "w"), indent=1); print(dict(stats))
