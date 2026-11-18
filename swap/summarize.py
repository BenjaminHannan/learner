"""One JSON line per tau2 run: DB match / reward pass out of all sims, per-task wins, agent tokens and wall time per sim."""
import json, sys, collections
d = json.load(open(sys.argv[1])); arm = sys.argv[2]; wall = int(sys.argv[3])
sims = d["simulations"]; per = collections.defaultdict(list); term = collections.Counter()
tok = []; dur = []; ncalls = 0; nreplies = 0
for s in sims:
    ri = s.get("reward_info") or {}
    db = bool((ri.get("db_check") or {}).get("db_match")); rw = ri.get("reward", 0) >= 1
    per[str(s["task_id"])].append(int(db)); term[s.get("termination_reason")] += 1
    ct = sum((m.get("usage") or {}).get("completion_tokens", 0) for m in s["messages"] if m["role"] == "assistant")
    tok.append(ct); dur.append(s.get("duration") or 0)
    for m in s["messages"]:
        if m["role"] == "assistant":
            ncalls += len(m.get("tool_calls") or []); nreplies += 1
n = len(sims)
print(json.dumps({"arm": arm, "sims": n, "db_match": sum(sum(v) for v in per.values()),
                  "reward_pass": sum((s.get("reward_info") or {}).get("reward", 0) >= 1 for s in sims),
                  "per_task": {k: v for k, v in sorted(per.items(), key=lambda x: int(x[0]))}, "termination": dict(term),
                  "agent_tokens_per_sim": round(sum(tok) / max(n, 1)), "secs_per_sim": round(sum(dur) / max(n, 1), 1),
                  "tool_calls": ncalls, "assistant_msgs": nreplies, "wall_s": wall}))
