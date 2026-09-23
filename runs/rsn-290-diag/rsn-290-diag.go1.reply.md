Diagnosis run starting — checking rules and rig before testing the models.
Found the 138k→138m delta. Now mapping the suspect stages.
Pilot first: confirming the phenomenon and attribute paths before the full run.
Shell quoting issue — retrying with simpler quoting.
138k and 138l identical so far. Now the 138m side.
Bisect is decisive. Now computing the verified integer counts from the rows file.
All counts verified by code. Writing the DIAG.md report.
Verdict: CAUSE FOUND — the exp-224 decline rewrite (`install_decline224`, installed on every 138m build) turns 138k's honest "don't know" decline into 138m's "I didn't understand that question" on exactly the turns the ears never parsed (14 of 42 dev dialogs). 224c, 233, 234, 230c/219, 227c all exonerated by direct test.

Marks table (integer counts, computed from rows.jsonl by script):

| # | Check | Count |
|---|-------|-------|
| M1 | Dev dialogs (own wording, fictional names), fresh state each, run on 138k/138l/138m | 42 dialogs, 126 runs |
| M2 | 138k vs 138l reply equality | 42 / 42 identical |
| M3 | Parsed turns (ears emitted `ask`) byte-identical on k, l, m | 28 / 28 |
| M4 | Unparsed turns flipped glue → Q2, 138k → 138m | 14 / 14 |
| M5 | 224-alone stack (138l+224) reproduces 138m's Q2 | 14 / 14 |
| M6 | 224c engagements anywhere (q1honest log) | 0 |
| M7 | 138m classes minus wrappers serve old glue (class layers exonerated) | 14 / 14 |
| M8 | Question turns writing to notebook | 0 / 180 |
| M9 | 138m d224 entries: kind Q2, qbranch=False, acts (clarify, clarify) | 14 / 14 |

Every move: 14 reply changes, all glue → Q2, all on unparsed turns — 12× "Does A have an R?" (taught 2, never 4, taken-back 4, boundary "Has Bex a dog?"/"Does Lena have mother?" 2) plus "Where lives Bex?" and "Who is mother of Bex?". Zero moves on the other 28 dialogs (all What/Where/Who that parse, incl. all taken-back arms, are byte-identical across k/l/m).

Every miss: `t-does-dog`, `t-does-mother` — fact taught and stored, yet 138k gives the glue and 138m gives Q2 (2 misses on all agents; pre-existing 138k gap, not caused by 138m).

Deviations: (1) first bisect stack `138m-no224` leaked the wrappers (build re-entered the installing builder) — its 18 rows are VOID, match full-138m 18/18, superseded by asserted-clean `138m-no224v2`; rows kept and relabeled, nothing deleted. (2) Load 36–51 (bar 60), disk 14 GB free, 1 process, CPU only. No panels opened, no model changes, additive-only (7 new scripts, 1 new artifacts dir; artifacts/ is gitignored so files sit untracked in the worktree — no git ops per rules).

Exact cause: `scripts/fable_loop224_agent.py:113-137` (`turn224`; kind branch :121-127, `_pipeline_question` fallback :73-81 fires on mere "?" suffix while `qbranch` is False), installed by `scripts/claude_loop138m_agent.py:213-214`, sentence from `scripts/fable_decline224.py` (Q2_SENTENCE).

Was it parsed? No — genuinely not parsed: acts=`[clarify]` only, `has_ask`=False, stage=`none`, intent=DECLINE, 0 writes, 14/14. So 138m did not parse-and-find-nothing. But the reply is still misleading: Q2 was triggered by text shape, not by pipeline question-handling, and for the never/taken-back arms the discarded "I have no record of it" half was TRUE — 138m reports a hearing failure where the fact is simply absent.

Smallest single fix (named, not implemented — diagnosis only): a clarify-only bypass in the 224 swap guard (new wrapper file, no frozen edits) that passes the original glue through when there is no `ask`, no `qbranch`, only `clarify` acts — restores the byte-identical 138k reply on exactly these 14 turns, touches nothing else.

What it means (plain English): if you ask 138m "Does A have an R?", it answers "I didn't understand" even when the real issue is just that nobody taught it that fact — the honest "I have no record" got thrown away. What it doesn't mean: 138m isn't faking the parse failure (it really can't hear these questions), nothing about What/Where/Who answers moved (28/28 identical), and it never invents facts here (0 writes).

Files: `artifacts/claude-diag290-20260923/DIAG.md` + `rows.jsonl` (198 rows; 18 labeled `138m-no224` are VOID), `scripts/claude_diag290_{run,bisect,bisect2,summary,pilot,probe,probe2}.py`.
