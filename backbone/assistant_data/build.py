"""Validate raw generations, dedupe, split. usage: python3 build.py RAW.jsonl OUTDIR [--eval 200]"""
import argparse, json, re, random, collections, pathlib, hashlib
from jsonschema import Draft202012Validator
import generate as G
HERE = pathlib.Path(__file__).parent
TOOLS = json.loads((HERE/"tools.json").read_text())
VAL = {t["function"]["name"]: Draft202012Validator(t["function"]["parameters"]) for t in TOOLS}
RM = re.compile(r"\brm\b|--force|push\s+-f|\bmkfs\b|\bdd\b|>\s*\S")
def norm(s): return re.sub(r"[^a-z0-9 ]", "", s.lower()); 

def convert(obj, spec):
    """returns (example, None) or (None, reason)"""
    if not isinstance(obj, dict) or not isinstance(obj.get("messages"), list): return None, "bad_shape"
    msgs = []; pending = []; n = 0; calls = []
    for m in obj["messages"]:
        if not isinstance(m, dict): return None, "bad_message"
        r = m.get("role"); c = m.get("content")
        if r == "user":
            if pending: return None, "missing_tool_result"
            if not isinstance(c, str) or not c.strip(): return None, "empty_user"
            msgs.append({"role":"user","content":c})
        elif r == "assistant":
            if pending: return None, "missing_tool_result"
            tcs = m.get("tool_calls")
            if c is not None and not isinstance(c, str): return None, "bad_content"
            if tcs:
                out = []
                for tc in tcs:
                    if not isinstance(tc, dict): return None, "bad_tool_call"
                    name, args = tc.get("name"), tc.get("arguments")
                    if name not in VAL: return None, "unknown_tool"
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except Exception: return None, "args_not_json"
                    if not isinstance(args, dict): return None, "args_not_object"
                    if next(VAL[name].iter_errors(args), None): return None, "schema_violation"
                    n += 1; cid = f"call_{n:04d}"
                    out.append({"id":cid,"type":"function","function":{"name":name,"arguments":json.dumps(args, ensure_ascii=False)}})
                    pending.append((cid, name)); calls.append((len(msgs), name, args))
                msgs.append({"role":"assistant","content":c if c else None,"tool_calls":out})
            else:
                if not isinstance(c, str) or not c.strip(): return None, "empty_assistant"
                msgs.append({"role":"assistant","content":c})
        elif r == "tool":
            if not pending: return None, "orphan_tool"
            if not isinstance(c, str): c = json.dumps(c, ensure_ascii=False)
            cid, name = pending.pop(0)
            msgs.append({"role":"tool","tool_call_id":cid,"name":name,"content":c})
        else: return None, "bad_role"
    if pending: return None, "missing_tool_result"
    if not msgs or msgs[0]["role"] != "user" or msgs[-1]["role"] != "assistant" or msgs[-1].get("tool_calls"): return None, "bad_order"
    # safety: irreversible calls need an earlier user turn after an assistant text-only turn
    for idx, name, args in calls:
        risky = name == "send_email" or (name == "run_shell" and RM.search(args.get("command","")) and re.search(r"\brm\b|--force|push\s+-f", args.get("command","")))
        if risky:
            seq = [m["role"] + ("T" if m.get("tool_calls") else "") for m in msgs[:idx]]
            ok = any(seq[i] == "assistant" and seq[i+1:].count("user") >= 1 for i in range(len(seq)))
            # need assistant text turn followed later by a user turn
            ok = any(seq[i] == "assistant" and "user" in seq[i+1:] for i in range(len(seq)))
            if not ok: return None, "unconfirmed_irreversible"
    if any(m["role"]=="assistant" and re.search(r"<think>|let me think", (m.get("content") or ""), re.I) for m in msgs): return None, "reasoning_leak"
    sysmsg = G.SYS_STYLES[spec["sys_style"]].format(**spec)
    return {"scenario": obj.get("scenario", spec["scenario"]), "tools": TOOLS,
            "messages": [{"role":"system","content":sysmsg}] + msgs}, None

def parse_text(t):
    t = t.strip(); t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try: return json.loads(t)
    except Exception:
        i, j = t.find("["), t.rfind("]")
        if i >= 0 and j > i:
            try: return json.loads(t[i:j+1])
            except Exception: pass
    return None

def salvage(t):
    """Recover complete conversation objects from malformed output (restarts, trailing prose, truncation)."""
    dec = json.JSONDecoder(); out = []; i = 0
    while True:
        j = t.find('{"scenario"', i)
        if j < 0: break
        try: o, e = dec.raw_decode(t, j); out.append(o); i = e
        except Exception: i = j + 1
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("raw"); ap.add_argument("out"); ap.add_argument("--eval", type=int, default=200)
    a = ap.parse_args()
    drops = collections.Counter(); good = []; seen = set(); total = 0
    for line in open(a.raw):
        rec = json.loads(line); arr = parse_text(rec["text"]); salv = False
        if not isinstance(arr, list):
            arr = salvage(rec["text"]); salv = True
            if not arr: drops["call_unparseable"] += 1; continue
        free = list(rec["specs"])
        for i, obj in enumerate(arr):
            total += 1
            if salv:
                m = [x for x in free if isinstance(obj, dict) and x["scenario"] == obj.get("scenario")]
                if not m: drops["extra_item"] += 1; continue
                spec = m[0]; free.remove(spec); drops["_salvaged_items"] += 1
            else:
                if i >= len(rec["specs"]): drops["extra_item"] += 1; continue
                spec = rec["specs"][i]
            ex, why = convert(obj, spec)
            if why: drops[why] += 1; continue
            ex["scenario"] = spec["scenario"]  # trust requested spec
            k = norm(ex["messages"][1]["content"])
            if k in seen: drops["duplicate"] += 1; continue
            seen.add(k); good.append(ex)
    rng = random.Random(0); by = collections.defaultdict(list)
    for e in good: by[e["scenario"]].append(e)
    ev, tr = [], []
    frac = min(1.0, a.eval / max(1, len(good)))
    for s, L in sorted(by.items()):
        rng.shuffle(L); k = round(len(L) * frac); ev += L[:k]; tr += L[k:]
    rng.shuffle(tr); rng.shuffle(ev)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for name, L in (("train.jsonl", tr), ("eval.jsonl", ev)):
        with open(out/name, "w") as f:
            for e in L: f.write(json.dumps(e, ensure_ascii=False)+"\n")
    (out/"tools.json").write_text(json.dumps(TOOLS, indent=1))
    cost = json.loads(pathlib.Path(a.raw+".cost").read_text()) if pathlib.Path(a.raw+".cost").exists() else {"in":0,"out":0}
    def st(L):
        tc = collections.Counter(); calls = 0
        for e in L:
            for m in e["messages"]:
                for c in m.get("tool_calls") or []: tc[c["function"]["name"]] += 1; calls += 1
        return {"n": len(L), "avg_messages": round(sum(len(e["messages"]) for e in L)/max(1,len(L)),2),
                "avg_tool_calls": round(calls/max(1,len(L)),2), "tool_call_counts": dict(tc),
                "per_scenario": dict(collections.Counter(e["scenario"] for e in L))}
    salvaged = drops.pop("_salvaged_items", 0)
    stats = {"generated_items": total, "salvaged_from_malformed_calls": salvaged, "valid_after_dedupe": len(good), "drop_reasons": dict(drops),
             "train": st(tr), "eval": st(ev), "tokens": cost,
             "estimated_cost_usd": round(cost["in"]*G.PRICE_IN/1e6 + cost["out"]*G.PRICE_OUT/1e6, 2),
             "pricing_assumed_per_M": {"in": G.PRICE_IN, "out": G.PRICE_OUT}}
    (out/"stats.json").write_text(json.dumps(stats, indent=1)); print(json.dumps(stats, indent=1))
if __name__ == "__main__": main()
