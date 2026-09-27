"""Run heldout150.json once against the live placeholder model. Usage: run_heldout.py OUT.json"""
import json, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import fable_listening_english as E
WRITE = ("teach ", "correct ", "alias ", "person ", "forget ", "undo")
items = json.load(open(os.path.join(HERE, "heldout150.json"), encoding="utf-8"))
known = ["Ben"]
out, exact, unsafe = [], 0, 0
for it in items:
    t0 = time.time()
    try:
        got = E.parse_english_proposal(it["english"], it["pending"], known)["lines"]; err = None
    except Exception as e:
        got, err = [], f"{type(e).__name__}: {str(e)[:160]}"
    ok = got == it["want"]
    bad = [g for g in got if g.startswith(WRITE) and g not in it["want"]]
    exact += ok; unsafe += bool(bad)
    out.append({**it, "got": got, "err": err, "ok": ok, "unsafe": bad, "sec": round(time.time() - t0, 1)})
    print(("OK  " if ok else "MISS"), it["n"], it["english"], "| want", it["want"], "| got", got, "|", err or "", flush=True)
print(f"EXACT {exact}/{len(items)}  UNSAFE_WRITE_ITEMS {unsafe}")
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
