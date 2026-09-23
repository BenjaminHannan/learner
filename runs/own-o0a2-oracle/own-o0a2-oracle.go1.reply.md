Fixing the 67.6% miss — writing 300 fresh turns and the v1 cue rule.
I have the v0 rule and the mix spec. Now extracting the relation table's teach-template cues (read-only) before writing fresh turns.
All 75 teach templates mapped. Now writing the 300 fresh turns (my own wording) before any rule code.
Over by 12 statement turns — trimming 12 duplicates whose relations appear elsewhere.
300 turns, only the 2 intentional pronoun cases flagged. Sealing data first, before any rule code.
Data sealed. Now writing PASSMARKS.md (predictions, sealed before the run).
Now the v1 compiler (three ceilings, v0 imported read-only).
Sealed. Load 59.2 (<60), disk 12GB. Appending predictions to the ledger, then the single registered run.
Single run complete: v1 252/281 = 89.7%. Verifying seals, then pulling the full non-writable list for RESULTS.md.
Seals verified, all 29 non-writable facts accounted for. Writing RESULTS.md and the outcome ledger line.
Verdict: PASS. The v1 rule clears the bar on 300 fresh turns: 252/281 = 89.7% (bar ≥ 85%), and 0/114 no-save facts writable under every rule.

Marks table (integer counts; ACD = ASSERT/CORRECT/DENY gold facts, n=281; nosave n=114):

| Mark | Rule, WE | Result | Bar |
|---|---|---|---|
| Pown0a2.1 | v1, WE not allowed: 252/281 = 89.7% | PASS | ≥ 85% |
| Pown0a2.1 | v1, WE allowed: 262/281 = 93.2% | report | — |
| Pown0a2.2 | nosave writable: 0/114 in all 6 columns (v0/v1/licensed × WE) | PASS | = 0 |
| Pown0a2.3 | v0: 92/281 = 32.7% (not allowed), 98/281 = 34.9% (allowed) | report | — |
| Pown0a2.3 | learned-licensed: 259/281 = 92.2% (not allowed), 269/281 = 95.7% (allowed) | report | — |

Every move: v1 fixes 160 of the 189 v0 misses (WE not allowed). Learned-licensed fixes 7 more, leaving 22 (12 with WE allowed).

Every miss — all 29 non-writable under v1, WE not allowed:
- WE-owner 10: s157 Our dog Pip; s158 Our cat Moss; s159 Our cousins Dara+Kito (2); s160 Our hometown Essel; s161 Our dogs Pip+Zib (2); s162 Our mom Lena; m022 Our hometown Essel; m029 Our dog Pip. All writable with WE allowed.
- typo 5 (needs asking, by design): s163 Pipp→Pip; s164 Lenn→Lena; s165 Halvvo→Halvo; s166 Linna→Lina; s167 Leea→Lea.
- relation-OTHER 5 (never writable): s168 aura; s169 blicket; s170 zog; s171 mentor-spirit; s172 gloof.
- no-relation-cue 7: s173 "Pip is Mira's."; s174 "Mira's Pip won the prize."; s175 "Give Pip a treat, Mira's little star."; s178 "living in" ≠ "lives in"; s179 "works hard at" not contiguous; s180 "children" ≠ child+s (2 facts).
- owner-not-span 2: s176 "He lives in Rook." (Bo only in prev reply); s177 "She works at Halvo." (Ada only in prev reply).

Deviations:
- D1: v0 predicted ~120/281, measured 92/281. My fresh set is denser in plural/verb wordings than O0a's by design (it must contain the cases v1 claims to fix). Report-only, no re-run, no post-seal change.
- Otherwise none: one run, seals 4/4 OK post-run, no TEST-ONLY panel, no other agent folder, fictional names only, v0 column via read-only import of the O0a compiler.

What it means: the one fix works on new sentences — letting plurals ("sisters", "bosses") and the table's own verb phrases ("lives in", "works at") count as naming the relation lifts the ceiling from 32.7% to 89.7%, over the bar v0 failed. Nothing that should ask got auto-saved.
What it doesn't mean: a real trained reader isn't at 89.7% — this used perfect oracle readings; the ear still has to find spans and modes. Cue-less facts, inflections, "children", typos, pronouns remain; only the no-cue backup covers those (92.2%/95.7%).

PUSH: artifacts/claude-own-o0a2-20260923 scripts/claude_own_o0a2_compiler.py artifacts/fable-predictions-ledger.md
