import json, re, sys, importlib.util
spec = importlib.util.spec_from_file_location("dlg", "dialogs.py"); dm = importlib.util.module_from_spec(spec); spec.loader.exec_module(dm)
VALS = ["Quellport","Brindlecorp","Veltish","Farrowgate","Coldmere Mills","Tillmarsh","Dunmere","Norric","Harrowby","Quillworks","Osterby","Quellmoor","Delmoor"]
ONEWORD = {("v10",0),("v10",2),("v10",4),("v10",5),("v15",4)} | {("v11",i) for i in range(9)}
allowed = {did: set(al) for did, _, _, al in dm.D}
def norm(s): return re.sub(r"\s+"," ",s.strip().lower().rstrip("."))
def score(rows):
    res = {}
    prev = {}
    for r in rows:
        k = (r["dialog"], r["turn"])
        vals_in = [v for v in VALS if re.search(r"\b"+re.escape(v)+r"\b", r["reply"], re.I)]
        g = r["gold"]
        right = wrongval = None
        if g is not None:
            wrongval = [v for v in vals_in if v.lower() != g.lower()]
            right = (g == "" and not vals_in) or (g != "" and g in vals_in and not wrongval)
        taught = [tuple(x[:3]) for x in r["stored_all"] if x[4] == "taught"]
        bad = [t for t in taught if (norm(t[0]), t[1], norm(t[2])) not in allowed[r["dialog"]]]
        n = len(r["stored_all"]); p = prev.get(r["dialog"], 0); prev[r["dialog"]] = n
        qwrite = g is not None and n > p
        res[k] = dict(right=right, wrongval=wrongval, bad=bad, qwrite=qwrite, reply=r["reply"], text=r["text"], gold=g, newbad=None)
    # new bad writes (first appearance)
    seen = {}
    for k, v in res.items():
        s = seen.setdefault(k[0], set()); nb = [b for b in v["bad"] if b not in s]; s.update(v["bad"]); v["newbad"] = nb
    return res
A = score(json.load(open("rows_base228.json"))); B = score(json.load(open("rows_232c.json")))
def tally(R):
    q = [v for v in R.values() if v["gold"] is not None]
    return dict(questions=len(q), right=sum(v["right"] for v in q),
        wrong_value_replies=sum(bool(v["wrongval"]) for v in q),
        wrong_or_junk_writes=sum(len(v["newbad"]) for v in R.values()),
        question_writes=sum(v["qwrite"] for v in R.values()))
ta, tb = tally(A), tally(B)
lost = [k for k in A if A[k]["right"] and B[k]["right"] is False]
oneword = [k for k in ONEWORD if A[k]["reply"] != B[k]["reply"]]
print("228 ", ta); print("232c", tb); print("lost", lost); print("oneword changed", len(oneword), "of", len(ONEWORD), oneword)
for name, R in (("228", A), ("232c", B)):
    for k, v in R.items():
        if v["right"] is False or v["newbad"] or v["qwrite"]:
            print(name, k, repr(v["text"]), "gold=", repr(v["gold"]), "->", repr(v["reply"][:200]), "wrongval", v["wrongval"], "newbad", v["newbad"], "qwrite", v["qwrite"])
json.dump(dict(base228=ta, v232c=tb, lost=lost, oneword_changed=oneword), open("counts.json","w"), indent=1)
