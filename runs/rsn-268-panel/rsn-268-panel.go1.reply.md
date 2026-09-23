Verdict pending — building your blind panel.
Spec is clear and the base agent loads. Now I'll pilot the teach forms to see what the base actually stores.
Teach form verified: `A's R is B.` stores reliably across all relations; `The R of A is B.` mostly fails. I'll use only the first form. Now building the panel writer.
Panel generated with exact family counts. Load is below the limit, disk is fine. Running the base now, one item at a time.
All teaches stored exactly as expected — no replacements needed. Scoring now.
VERDICT: Panel complete and sealed. All 70 items written, run once each on the 138m base, scored, sealed. Base result: 46 right, 0 wrong, 24 misses out of 70.

Marks table (integer counts, category level only):

| family | n | right | wrong | misses | question_wrote |
|---|---|---|---|---|---|
| reverse_chain | 24 | 10 | 0 | 14 | 0 |
| reverse_nochain | 10 | 4 | 0 | 6 | 0 |
| uncued_reverse | 8 | 8 | 0 | 0 | 0 |
| forward_chain | 12 | 12 | 0 | 0 | 0 |
| forward_1hop | 10 | 9 | 0 | 1 | 0 |
| abstain | 6 | 3 | 0 | 3 | 0 |
| TOTAL | 70 | 46 | 0 | 24 | 0 |

Every move / every miss (by id only, no item text quoted):
- reverse_chain right 10 (n268-001, 003, 013, 015, 017, 018, 019, 022, 023, 024); miss 14 (002, 004, 005, 006, 007, 008, 009, 010, 011, 012, 014, 016, 020, 021). The misses are the "married to" and "what did X found/write/compose" shapes, which the base does not parse.
- reverse_nochain right 4 (025, 029, 030, 031); miss 6 (026, 027, 028, 032, 033, 034). Same unparseable shapes.
- uncued_reverse right 8/8, no misses.
- forward_chain right 12/12, no misses.
- forward_1hop right 9; miss 1 (060, the "composed" shape).
- abstain right 3 (065, 069, 070); miss 3 (066 "was that a question", 067 and 068 "didn't understand" — replies with no abstain form, so neither right nor wrong).
- wrong = 0 everywhere; question_wrote = 0 everywhere (no question turn stored a fact).
- All 70 setup teaches stored exactly as expected (every setup reply confirmed storage), so zero items needed replacing. 35 items carry two-word proper names (spec minimum 20). Reverse_chain spans 8 relations, none over 5 items, with 6 two-subject items.

Deviations:
1. Extra file `score138m.json` sits in the folder beside the spec's seven files. It is machine-readable score output only, NOT in the seal. Kept and reported rather than deleted (additive-only rule).
2. "PUSH: artifacts/claude-nhoppanel268-20260923" — files are written in the worktree but NOT committed or pushed, because OPUS-RULES forbids commits/pushes. Awaiting director pickup.
3. No other deviations: additive only (7 new files, zero edits/deletes), fictional names only, no forbidden files opened, TEST-ONLY panels never touched, one process at a time, disk stayed above 3 GB free (16 GB), load stayed under 60.

What it means (plain high-school English): The base is perfect at plain two-step forward questions and at plain "whose X is Y" backwards questions, but it cannot understand several backwards question wordings (married-to, what-did-X-found/write/compose). That gap is exactly what this panel was built to measure.

What it doesn't mean: It does NOT mean the base forgot the facts — every fact was stored correctly. It does NOT mean the panel is broken — the misses come from question shapes the base can't parse, which is the reasoning line under test. It does NOT predict how any other agent will score.
