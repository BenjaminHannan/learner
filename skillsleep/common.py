"""Shared helpers: read tau2 results (.json or .json.gz), pass flag, summary line.
CLI: common.py strip SRC DST.gz            copy a results.json without the bulky raw_data fields
     common.py summarize ARM DOMAIN WALL_S FILE...   one summary JSON line (several files are merged)"""
import collections, gzip, json, sys

REAL_END = {"user_stop", "agent_stop", "max_steps", "too_many_errors"}  # runs that ended on their own (not infra/API errors)
# every tool that changes the store (retail + airline tool lists of tau2 cc1df47); transfer_to_human_agents and calculate are not writes
WRITE_TOOLS = {"cancel_pending_order", "exchange_delivered_order_items", "modify_pending_order_address", "modify_pending_order_items",
               "modify_pending_order_payment", "modify_user_address", "return_delivered_order_items",
               "book_reservation", "cancel_reservation", "send_certificate", "update_reservation_baggages",
               "update_reservation_flights", "update_reservation_passengers"}


def load(path):
    return json.load(gzip.open(path, "rt") if str(path).endswith(".gz") else open(path))


def sims(path):
    return load(path)["simulations"]


def ok(s):  # tau2's own check: reward 1 (db end state + required info said)
    return ((s.get("reward_info") or {}).get("reward") or 0) >= 1


def real(s):
    return str(s.get("termination_reason", "")).split(".")[-1] in REAL_END and s.get("reward_info") is not None


def asked(text):  # a question to the user
    return (text or "").rstrip().endswith("?")


def agent_questions(messages):  # generated agent turns (not the canned greeting) that end in a question
    return sum(1 for m in messages if m["role"] == "assistant" and m.get("usage") is not None and asked(m.get("content")))


def writes_asked(messages):
    """(write tool calls, how many of them came after a question to the user that the user answered).
    A write counts as asked when the most recent agent message with text before it ends with '?' and a user message sits between them."""
    w = a = 0; q = False; user_since = False
    for m in messages:
        if m["role"] == "user":
            user_since = True
        elif m["role"] == "assistant":
            for t in m.get("tool_calls") or []:
                if t["name"] in WRITE_TOOLS:
                    w += 1; a += bool(q and user_since)
            if (m.get("content") or "").strip() and m.get("usage") is not None:
                q = asked(m["content"]); user_since = False
    return w, a


def summarize(paths, arm, domain, wall=0):
    ss = [s for p in paths for s in sims(p)]; per = collections.defaultdict(list); per_real = collections.defaultdict(list)
    W = A = Q = N = 0
    for s in ss:
        per[str(s["task_id"])].append(int(ok(s)))
        if real(s):  # infra/API-error sims (e.g. Haiku 429s) left out
            per_real[str(s["task_id"])].append(int(ok(s)))
            w, a = writes_asked(s["messages"]); W += w; A += a; Q += agent_questions(s["messages"]); N += 1
    return {"arm": arm, "domain": domain, "sims": len(ss), "pass": sum(sum(v) for v in per.values()),
            "per_task": dict(sorted(per.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)),
            "per_task_real": dict(per_real), "not_real": len(ss) - sum(map(len, per_real.values())),
            "termination": dict(collections.Counter(str(s.get("termination_reason")) for s in ss)), "wall_s": int(wall),
            "ask": {"writes": W, "asked": A, "rate": A / W if W else None, "questions": Q, "q_per_sim": Q / N if N else None, "real_sims": N}}


if __name__ == "__main__":
    if sys.argv[1] == "strip":
        d = load(sys.argv[2])
        for s in d["simulations"]:
            for m in s.get("messages") or []:
                m.pop("raw_data", None)
            s.pop("ticks", None)
        with gzip.open(sys.argv[3], "wt") as f:
            json.dump(d, f)
    elif sys.argv[1] == "summarize":
        print(json.dumps(summarize(sys.argv[5:], sys.argv[2], sys.argv[3], int(sys.argv[4]))))
