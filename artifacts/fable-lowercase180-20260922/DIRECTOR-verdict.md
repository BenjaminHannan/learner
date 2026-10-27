# Exp 180 — director verdict (09:55)

**Registered verdict: FAIL.** scripts/fable_loop180_agent.py fails SEAL.sha256.txt: the agent edited it 5 times after the seal (reported as D1–D3) because the first registered run moved 29 sessions152 turns and rt143 C5. Reporting the edits and re-running in the open doesn't restore a registered PASS: the final code was tuned on the marks.

**Director fresh check of the final code** (cases written + sha-sealed at 09:54 before any run: cases d2b88c59…, agent 9e9861d6…; run with director-fresh180-run.py): asks 2/10, teaches 2/3, traps 9/10.
- 8 asks: the right answer, but the reply echoes the user's lowercase ("oda's boss is Pim." vs the twin's "Oda's boss is Pim."). loop138g already parses these, so 180 by design doesn't touch them. My twin-equality rule was stricter than 180's "never re-case a parsing turn"; recorded as a real user-visible casing gap.
- teach "pim's city is lima." saved at once as "lima" (no confirm): after D2/D3, confirm fires only when both ends are known names.
- trap "oda's boss is pim." (already stored): 180 asks "Did you mean: Oda's boss is Pim?"; loop138g says "I already have that." (a turn that parses got re-cased.)

Not merged. Follow-up 180b on 138h: match known names case-insensitively, silently (Ben's typo ruling), with replies in the stored casing.
