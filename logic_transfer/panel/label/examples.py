"""Print worked derivations for chosen prompts (independent reader).  python3 examples.py > examples.txt"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
B = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
PICK = {  # id -> note
 "lt-logic-gate-21-000121": "convention: classical false, documented unknown (case split on 'naxpus')",
 "lt-logic-gate-21-001569": "convention: case split (p->X and not-p->X)",
 "lt-logic-gate-21-000375": "convention: case split via entity rule",
 "lt-logic-test_sampler-22-000138": "convention: reductio / modus tollens",
 "lt-placebo-dev-25-000662": "convention: modus tollens",
 "lt-logic-test_sampler-22-000997": "convention: text is classically inconsistent",
 "lt-logic-dev-23-001078": "wording: 'Every p and q' read distributively",
 "lt-logic-dev-23-001121": "wording: 'All p are not q' read as 'not all'",
 "lt-logic-gate-21-000001": "plain agreement, depth 1",
 "lt-logic-dev-23-000657": "plain agreement, depth 3 (false/true via negations)",
}
FILES = ["eval/logic_gate", "eval/logic_dev", "eval/logic_test_sampler", "eval/placebo_dev"]
fmt = lambda l: ("~" if l[0] else "") + f"{l[1]}({l[2]})"
for fn in FILES:
    for line in open(B + fn + ".jsonl"):
        r = json.loads(line)
        if r["id"] not in PICK: continue
        p = rlib.parse_prompt(r["prompt"])
        lab, contra, rd, gr = rlib.fwd(p.facts, p.rules, p.query)
        print("=" * 100); print(r["id"], "--", PICK[r["id"]])
        print("PROMPT:", rlib.split_options(r["prompt"])[0])
        print("PARSED facts:", ", ".join(fmt(f) for f in p.facts)); 
        print("PARSED rules:", "; ".join(("%s: " % e if e else "x: ") + " & ".join(("~" if n else "") + w for n, w in l) + " -> " + ("~" if rh[0] else "") + rh[1] for l, rh, e in p.rules))
        print("QUERY:", fmt(p.query), "| gold:", r["answer"])
        steps = []
        for rnd in range(1, 9):
            for l, k in sorted(rd.items(), key=lambda kv: str(kv[0])):
                if k == rnd:
                    src = [pr for pr, c in gr if c == l and all(x in rd and rd[x] < rnd for x in pr)]
                    steps.append(f"  round {rnd}: {fmt(l)}  from  {', '.join(fmt(x) for x in src[0])}")
        print("FORWARD CHAINING (documented):", "nothing derived" if not steps else ""); print("\n".join(steps))
        print("  -> my label:", lab, "| min proof size/height:", rlib.min_depth(p.facts, p.rules, p.query)[1:])
        print("  modus-tollens-closed:", rlib.fwd(p.facts, rlib.contrapositive_rules(p.rules), p.query)[0],
              "| textbook entailment:", rlib.classical(p.facts, p.rules, p.query),
              "| DIST:", rlib.fwd(p.facts, rlib.distribute(p.rules, p.rule_ids, {"R3:1", "R3:2", "R3:7", "R3:9"}), p.query)[0],
              "| PNEG:", rlib.fwd(p.facts, rlib.drop_rules(p.rules, p.rule_ids, {"R2:4", "R2:5", "R2:6", "R2:9", "R2:13"}), p.query)[0])
