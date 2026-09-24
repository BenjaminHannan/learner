#!/usr/bin/env python3
"""rsn-298 scorer: branchpanel298 replies (prun.py output) for 292 and 298.

usage: claude_rsn298_score.py items.jsonl run292.json run298.json
An item is RIGHT when its reply contains every "must" string, no "never" string, does not ask
"Which one" (except OVER4, where "Which one" is a must), and the question turn wrote nothing.
WRONG = the reply contains a "never" string. Matching is case-insensitive on whole words.
"""
import json, re, sys, collections

def has(reply, s):
    return re.search(r"(?<![\w])" + re.escape(s.casefold()) + r"(?![\w])", reply.casefold()) is not None

def score(items, run):
    by = {r["id"]: r for r in run}
    out = {}
    for it in items:
        r = by[it["id"]]; rep = r["reply"]
        wrong = any(has(rep, s) for s in it.get("never", []))
        ask = "which one" in rep.casefold()
        ok = all(has(rep, s) for s in it["must"]) and not wrong and not r["wrote"]
        if it["category"] != "OVER4" and ask:
            ok = False
        out[it["id"]] = {"cat": it["category"], "right": ok, "wrong": wrong, "wrote": r["wrote"], "reply": rep}
    return out

def main():
    items = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
    s292 = score(items, json.load(open(sys.argv[2])))
    s298 = score(items, json.load(open(sys.argv[3])))
    tab = collections.defaultdict(lambda: collections.Counter())
    for i in items:
        c = i["category"]
        for arm, s in (("292", s292), ("298", s298)):
            x = s[i["id"]]
            tab[c][arm + "_right"] += x["right"]; tab[c][arm + "_wrong"] += x["wrong"]
            tab[c][arm + "_wrote"] += x["wrote"]
        tab[c]["n"] += 1
        tab[c]["same_reply"] += s292[i["id"]]["reply"] == s298[i["id"]]["reply"]
    main4 = ["SAME", "DIFFER", "PARTIAL", "NONE"]
    tot = lambda k: sum(tab[c][k] for c in tab)
    res = {"by_category": {c: dict(tab[c]) for c in sorted(tab)},
           "main4_right_292": sum(tab[c]["292_right"] for c in main4),
           "main4_right_298": sum(tab[c]["298_right"] for c in main4),
           "wrong_292": tot("292_wrong"), "wrong_298": tot("298_wrong"),
           "none_wrong_298": tab["NONE"]["298_wrong"],
           "wrote_298": tot("298_wrote"),
           "control_same": tab["CONTROL"]["same_reply"], "over4_same": tab["OVER4"]["same_reply"]}
    res["P298.1"] = res["main4_right_298"] >= 48 and res["main4_right_298"] >= res["main4_right_292"] + 30
    res["P298.2"] = res["wrong_298"] <= res["wrong_292"] and res["none_wrong_298"] == 0
    res["P298.3"] = res["control_same"] == tab["CONTROL"]["n"] and res["over4_same"] == tab["OVER4"]["n"]
    res["P298.4"] = res["wrote_298"] == 0
    print(json.dumps(res, indent=1))

if __name__ == "__main__":
    main()
