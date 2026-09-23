"""Round 3: like run_heldout.py but records whether a write would be echoed first."""
import json, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import fable_listening_english as E
WRITE = ("teach ", "correct ", "alias ", "person ", "forget ", "undo")
items = json.load(open(os.path.join(HERE, "heldout3.json"), encoding="utf-8"))
out, exact, unsafe, echoed_wrong = [], 0, 0, 0
for it in items:
    try:
        p = E.parse_english_proposal(it["english"], it["pending"], ["Ben"]); got, echo, err = p["lines"], p["confirm_before_write"], None
    except Exception as e:
        got, echo, err = [], False, f"{type(e).__name__}: {str(e)[:160]}"
    ok = got == it["want"]
    bad = [g for g in got if g.startswith(WRITE) and g not in it["want"]]
    exact += ok; unsafe += bool(bad and not echo); echoed_wrong += bool(bad and echo)
    out.append({**it, "got": got, "echo": echo, "err": err, "ok": ok, "wrong_writes": bad})
    print(("OK  " if ok else "MISS"), it["n"], it["english"], "| want", it["want"], "| got", got, "| ECHO" if echo else "|", err or "", flush=True)
print(f"EXACT {exact}/{len(items)}  UNSAFE_NO_ECHO {unsafe}  WRONG_BUT_ECHOED {echoed_wrong}")
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
