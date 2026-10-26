"""Night step 3: sort the day into lessons and render them for training.
Usage: build.py TOKENIZER_DIR ENV_JSON OUT_DIR DAY_RESULTS [FIX_RESULTS ...]
Writes OUT_DIR/night.jsonl (kind pos | pair | neg) and OUT_DIR/build_stats.json. Everything is rendered with the NORMAL system prompt (no critique).
Length caps (tokens): MAXTOK=16384 for positives, MAXTOK_PAIR=12288 for pair/negative sequences (both sides of a pair keep their graphs in the DPO step,
so these decide the 24 GB fit on a 4090). Every drop is counted in build_stats. build_stats also holds the share of SFT target turns that are questions."""
import collections, json, os, sys
from common import agent_questions, ok, real, sims
from render import load_tok, render_traj

MAXTOK = int(os.environ.get("MAXTOK", 16384)); MAXTOK_PAIR = int(os.environ.get("MAXTOK_PAIR", 12288))
tokd, envp, outd, dayp = sys.argv[1:5]; fixps = sys.argv[5:]
tok = load_tok(tokd); env = json.load(open(envp))
stats = collections.Counter(); cache = {}; seen_drop = set()


def enc(s, cap=MAXTOK, what="pos"):  # {ids, mask} or None (render error or over the cap); each sim rendered once
    k = s["id"]
    if k not in cache:
        try:
            ids, mask = render_traj(tok, env, s["messages"])
            cache[k] = {"ids": ids, "mask": mask}
        except Exception as e:
            stats["render_error"] += 1; print("render error", s["task_id"], str(e)[:100]); cache[k] = None
    if cache[k] is not None and len(cache[k]["ids"]) > cap:
        if (what, k) not in seen_drop:
            seen_drop.add((what, k)); stats["dropped_%s_over_%d" % (what, cap)] += 1
        return None
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
            stats["sft_turns"] += sum(1 for m in s["messages"] if m["role"] == "assistant" and m.get("usage") is not None)
            stats["sft_question_turns"] += agent_questions(s["messages"])
    for i, s in enumerate(bad):
        e = enc(s, MAXTOK_PAIR, "pair")
        if not e:
            continue
        if pool:  # the chosen side rotates over the pool; skip ahead to one that fits the pair cap
            c = next((x for x in (enc(pool[(i + k) % len(pool)], MAXTOK_PAIR, "chosen") for k in range(len(pool))) if x), None)
            if c:
                rows.append({"kind": "pair", "task": t, "chosen": c, "rejected": e}); stats["pairs"] += 1
            else:
                stats["pair_dropped_no_chosen_fits"] += 1
        else:
            rows.append({"kind": "neg", "task": t, **e}); stats["negs"] += 1
stats["sft_question_share"] = round(stats["sft_question_turns"] / max(stats["sft_turns"], 1), 4)
stats["tokens_pos_total"] = sum(len(r["ids"]) for r in rows if r["kind"] == "pos")
stats["assistant_tokens_pos"] = sum(sum(r["mask"]) for r in rows if r["kind"] == "pos")
with open(outd + "/night.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
json.dump(dict(stats), open(outd + "/build_stats.json", "w"), indent=1); print(dict(stats))
