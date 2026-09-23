# Experiment 237 blind alias panel (TEST-ONLY)

TEST-ONLY. Do not tune on, print, or show this panel to the 237 builder before it seals its own work.

80 items, each a fresh session (new workdir / notebook per item).

| family | count | expect |
|---|---|---|
| synonym | 30 | ANSWER (question uses a true synonym of the stored relation word; 12 synonym pairs) |
| new_relation | 20 | ANSWER (everyday relation asked in a form base 221 fails on) |
| date | 10 | ANSWER (stored date relation asked naturally) |
| trap | 10 | ABSTAIN (asked relation is not a synonym; reply must give no stored value; a "worked out backwards" value only if actually true) |
| control | 10 | UNCHANGED (base 221 already answers right) |

## Files
- panel.jsonl: fields id, family, setup (list of teach turns), question, expect (ANSWER / ABSTAIN / UNCHANGED), gold (value or null), note.
- base221.jsonl: fields id, base_reply (base 221's reply to the panel question), stored_after_setup (notebook triples; read after the question turn, which writes nothing).
- SEAL.sha256.txt: shasum -a 256 of panel.jsonl and base221.jsonl, repo-relative.

Base: scripts/fable_loop221_agent.py with artifacts/claude-tableask221-20260922/loop221-config.json, run with the scratchpad dialog_nb.py probe runner.
Checks done on the base before sealing: every setup sentence saved (stored triple present); for synonym items, the same question with the exact stored relation word ("Who/What is X's <stored word>?") returned the gold value. All 80 pass.
All names are fictional.
