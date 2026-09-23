Diagnosing the yes/no blind spot — tracing where each question shape falls through.
Your base files check out — now mapping the ears pipeline to find the fall-through points.
I've charted the ears stack — now probing the question handlers directly.
The routing gap is getting clear — yes/no templates exist but are never compiled. Building the 60-dialog probe suite now.
Pilot confirms the split: Is-questions answer when grounded, Does-questions never parse. Checking two-word names before the full run.
Load is clear — running the full 63-dialog suite on 138nb.
Routing trace is nearly complete — verifying the last two reader stages.
All 61 dialogs are in with clean counts — writing the final report.
Verdict: CAUSE FOUND. On 138nb, yes/no questions fall through the ears because the base parser only makes `ask` out of who/what/where (`scripts/fable_agent_loop.py:96`), so no yes/no turn ever becomes a question inside the machine. The only live yes/no reader, the 154d peek, answers just `Is A's R B?` / `Is B A's R?` with single-token names and a stored fact (11 of 51 turns, all correct). Everything else — all 30 Does/Has turns, two-word names, of-forms, unknown/taken-back frames — hits the chain miss (`scripts/fable_loop90_agent.py:291-292`, stage `none`) and gets re-labeled Q2 by the 224 wrapper (`scripts/fable_loop224_agent.py:113-137`). 0 of 61 question turns wrote.

Marks table (integer counts, from rows.jsonl):

| # | Check | Count |
|---|-------|-------|
| M1 | Dev dialogs, 138nb, fresh state each | 61 dialogs, 61 runs |
| M2 | Yes/no-shaped turns | 51 |
| M3 | Answered right (Yes/No/Not-that-I-know) | 11 / 51 |
| M4 | "Didn't understand" (Q2) | 40 / 51 |
| M5 | Q2 with fact stored (should be Yes-able) | 16 / 40 |
| M6 | Q2 with nothing stored (should be IDK) | 24 / 40 |
| M7 | Question turns that wrote | 0 / 61 |
| M8 | 224c engagements | 0 |
| M9 | d224 Q2 entries (40 yes/no + 1 wh boundary) | 41 |
| M10 | Statement controls, 0 writes, no-save clarify | 4 / 4 |
| M11 | Wh controls: 2 answered + 3 targeted-decline / 6 | 5 / 6 parsed |

Every move: none (diagnosis only, no model change). Split observed: does-have 0/9 answered, does-noart 0/1, is-poss 7/12, is-of 0/1, is-inv 4/8, does-live 0/7, does-work 0/5, does-from 0/5, has 0/3. Misses: 16 taught-true Q2 (e.g. `dh-true1`, `dl-true`, `h-true`, `ip-true-2word`, `ii-2word`, `ip-ofform`) + 24 unknown/taken-back Q2 (should be "I don't know"). Correct: all 11 Is answers, all 4 statement controls, 5/6 wh controls.

Fall-through points (file:line): Does/Has — 154d parse None (`fable_fix154d_yesno.py:67,105-109`), 221 table no reading (`fable_fix221_tableask.py:494-497`; yes/no templates exist in the JSON but are never compiled, `:187-189`), 190/153 parse None, 229 skips `?` (`claude_loop229_agent.py:392`), 221c rewrite never adopted (`claude_loop221c_agent.py:205-232`). Is-ungrounded — parsed but `ground_yesno154d` None (`:139-161`). Is-two-word — `_NAME_154D` rejects (`:69,128-129`). Is-of-form — no `'s` split (`:113-114`).

Reader audit: bench73 no (wh/MQuake only, bench-only); 221/237 table no (yesno templates in JSON, reader compiles ask/inverse only); 190 no; 153 no; old-154 OFF since 138f; only 154d parses (Is, single-token, grounded).

Smallest single change proposed: one new additive loop-level wrapper in the 154d slot — parse Does-have/Has/Does-live-in + widened Is (multi-word via `nb.resolve`, of-forms), ground read-only (have→R, live→city), answer Yes / No (single-valued) / Not-that-I-know (multi) / targeted IDK. Moves 40/40 Q2 turns: 12→Yes, 1→No (`dl-false`), 27→IDK; work/from Yes/No needs a director key ruling (else IDK). Full list in `artifacts/claude-diag293-20260923/DIAG.md`.

Deviations: run wrote 61 rows (planning note said 63 — miscount; bar 60+ met). Load 53-58, disk 11 GB free, 1 process, CPU only, no panels opened, 138nb files verified byte-identical to origin/builder-outbox. Additive-only: 4 new scripts (`scripts/claude_diag293_{pilot,pilot2,run,summary}.py`), 1 new dir (`artifacts/claude-diag293-20260923/` + `rows.jsonl`, `DIAG.md`). No commits.

What it means (plain English): the agent hears "Does Ana have a dentist?" as noise, not as a question — even when Ana's dentist is written in its notebook, and even when the notebook is empty and the honest answer is "I don't know." Only plain "Is Ana's boss Tovi?"-style questions with short names get real Yes/No answers. What it doesn't mean: nothing is broken about storing facts, nothing gets written by asking, and every answer it does give is correct — it's one missing question shape, 40 turns wide, one wrapper deep.
