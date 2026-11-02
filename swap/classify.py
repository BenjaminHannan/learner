"""Classify failed tau2 tasks: leaked planning text as the reply / wrong-or-missing tool call / other."""
import json, re, sys, collections
d = json.load(open(sys.argv[1]))
LEAK = re.compile(r"\b[Tt]he user(?:'s)? (?:wants|has|is|asked|needs|said|provided|mentioned|confirmed|requested|would)|^(?:I need to|I should|I must|Let me (?:check|think|first)|According to (?:the )?policy)|\bthe user\b", re.M)
rows, cnt, cross = [], collections.Counter(), collections.Counter()
for s in d["simulations"]:
    ri = s.get("reward_info") or {}
    if ri.get("reward", 0) >= 1: continue
    msgs = s["messages"]
    replies = [m for m in msgs if m["role"] == "assistant" and m.get("content") and not m.get("tool_calls")]
    leaks = [m["content"] for m in replies if LEAK.search(m["content"])]
    called = collections.defaultdict(list)
    for m in msgs:
        for tc in m.get("tool_calls") or []: called[tc["name"]].append(tc.get("arguments"))
    bad = [c["action"] for c in ri.get("action_checks") or [] if not c["action_match"] and c.get("tool_type") == "write"]
    missing = [a["name"] for a in bad if a["name"] not in called]
    wrong = [a["name"] for a in bad if a["name"] in called]
    leak, tool = bool(leaks), bool(bad)
    primary = "leak" if leak else ("tool" if tool else "other")
    cnt[primary] += 1; cross[(leak, tool)] += 1
    rows.append(dict(task=s["task_id"], primary=primary, leak_msgs=f"{len(leaks)}/{len(replies)}", missing=missing, wrong_args=wrong,
                     term=s.get("termination_reason"), leak_example=(leaks[0][:120].replace("\n", " ") if leaks else "")))
for r in rows: print(json.dumps(r))
n = len(d["simulations"]); passed = n - len(rows)
print(json.dumps({"tasks": n, "passed": passed, "failed": len(rows), "primary": dict(cnt),
                  "leak_and_tool": cross[(True, True)], "leak_only": cross[(True, False)], "tool_only": cross[(False, True)], "neither": cross[(False, False)]}))
