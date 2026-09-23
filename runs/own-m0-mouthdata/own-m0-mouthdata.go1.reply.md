Building your 20,000 conversational training pairs — starting with rules and source records.
Schema is clear. Now checking seal conventions and hunting down the rules file.
Rules absorbed. Setting up the work plan and inspecting relation kinds.
Now writing the faithfulness filter (check script).
Now the main build script with pools, relations, ~340 templates, and turn frames.
Retrying the file write (same content, corrected call).
Writing the build script in chunks (header + pools + first templates).
Fixing three FORGOT templates that collide with the save-phrase rule, then adding the generation engine.
Now the generation engine, verification, and CLI.
Removing a leftover unused block, then piloting.
Expected caps gaps. Extracting the full missing-token set.
Two SAVED templates need save-phrase fixes, plus 13 allowlist additions.
I dropped "Sorry" from the allowlist edit. Adding it.
Selftest clean (339 template checks + planted violations, 0 mismatches). Piloting the full build to a temp dir.
WHOSE combos collide (owner is always "our"). Including the value in the key.
Sealed. Running the registered build (mandated uv command).
All marks pass. Verifying seal integrity and sampling report rows.
Seal intact. Writing RESULTS.md.
**Verdict: PASS Pm0.1–Pm0.5.** 20,000 train + 1,000 dev conversational-mouth pairs built on CPU, filter dropped 0, fresh re-check fails 0, seal 3/3 OK after the run. PUSH: `artifacts/claude-own-m0-20260923` `scripts/claude_own_m0_build.py` `scripts/claude_own_m0_check.py`.

## Marks table (integer counts)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| Pm0.1 train refails (20,000 rows) | 0 | 0 | PASS |
| Pm0.1 dev refails (1,000 rows) | 0 | 0 | PASS |
| Pm0.2 max reply share, train (worst: FORGOT 62/2500) | ≤3% | 2.48% | PASS |
| Pm0.2 max reply share, dev (ABSTAIN/FORGOT 3/100) | ≤3% | 3.00% | PASS |
| Pm0.3 distinct templates/status, train (min 48) | ≥40 | 48 | PASS |
| Pm0.3 distinct templates/status, dev (min 48) | ≥40 | 48 | PASS |
| Pm0.4 dev ∩ train names | 0 | 0 | PASS |
| Pm0.4 dev ∩ train combos (4000 vs 200) | 0 | 0 | PASS |
| Pm0.5 crashes | 0 | 0 | PASS |

Train top-shares: ABSTAIN 2.30%, CLARIFY 1.32%, OK 1.97%, SAVED 2.00%, UNKNOWN 2.10%. Dev: CLARIFY 2.00%, OK 2.00%, SAVED 2.00%, UNKNOWN 2.67%.

## Rows per status / per tag

Train: OK 7000, SAVED 3000, UNKNOWN 3000, ABSTAIN 2000, CLARIFY-tag 1500, WHOSE 1000, FORGOT 2500 = 20,000. Tags: ANSWER 7000, ACK_SAVE 3000, ABSTAIN 5000, CLARIFY 1500, FORGOT_ACK 2500, WHOSE 1000. Dev: OK 350, SAVED 150, UNKNOWN 150, ABSTAIN 100, CLARIFY-tag 100, WHOSE 50, FORGOT 100 = 1,000.

## Drops by filter rule

R1_missing 0, R2_extra 0, R3_caps 0, R4_status 0 — train and dev. Selftest caught all 10 planted violations with exact expected rules; all 339 template checks pass.

## Every move, every miss

1. Read plan §3.3, talk-fluency plan, our-policy decision, say_forms nouns, talker120 schema (names-only read of heldout for the 96-name blocklist — no items opened).
2. Wrote check.py (R1–R4) + build.py (pools, 339 templates, varied turn frames, round-robin assignment).
3. **Miss 1 (pre-seal):** selftest found 80 R3 + 2 R4 template fails → added 14 allowlist tokens, fixed 2 SAVED + 3 FORGOT templates.
4. **Miss 2 (pre-seal pilot):** Pm0.2 hit 3.50–3.60% on kind-heavy lists; 9 WHOSE combo overlaps → per-list round-robin, kind rotation, `stated_value` in WHOSE records. Re-pilot: all green.
5. Wrote PASSMARKS.md, appended Pownm0.1–2 to ledger, sealed 3 files (584a86bd…).
6. Registered run via mandated uv-offline py3.12: 21,000 rows, verify exit 0, independent check CLI 0 fails, seal re-verified 3/3 OK.

## Deviations

Pilots ran under /usr/bin/python3; the sealed registered run used the mandated uv offline command. OPUS-RULES suggests a 20260922-style dir; the brief fixes 20260923, used. Dev dealt 39 of 40 dev owner names — intersection still 0. Dev ABSTAIN/FORGOT top share sits exactly at 3.00% (bar is *more than* 3%).

## 10 random train rows (my own dev material, slots kept)

1. UNKNOWN/ABSTAIN `what is Lissa's hometown` → `Oh, I'm not sure where <S1>'s <R1> is.`
2. OK/ANSWER `prillo's mentor?` → `Yeah, <S1>'s <R1> is <V1>. Want me to remember anything else about <S1>?`
3. UNKNOWN/ABSTAIN `tell me Willo's boss's spouse` → `Oh, I don't know who <S1>'s <R1> is. Want to tell me?`
4. OK/ANSWER `do u know Morna's neighbour's teacher` → `Yeah, <S1>'s <R1> is <V1>.`
5. OK/ANSWER `what is Harko's city` → `Right then, <S1>'s <R1> is <V1>.`
6. FORGOT/FORGOT_ACK `forget what i said about Sella's favorite color` → `Okay, forgotten. I no longer hold what <S1>'s <R1> is.`
7. OK/ANSWER `who is Sella's uncle?` → `Gotcha. <S1>'s <R1> is <V1>.`
8. UNKNOWN/ABSTAIN `where does Ossa live btw` → `Oh, I don't know where <S1>'s <R1> is. Want to tell me?`
9. FORGOT/FORGOT_ACK `erase Zellin's country` → `Okay, I've forgotten where <S1>'s <R1> is.`
10. OK/ANSWER `tell me Zellin's aunt` → `Oh, I know this. <S1>'s <R1> is <V1>.`

## What it means / doesn't mean (plain English)

The mouth has 21,000 checked conversation examples to learn from: warm answers, honest "I don't know"s, save confirmations, "which one?" and "whose?" questions — all with names hidden behind fill-in slots so no real name can leak, and no reply overused. But this is only the study material, not a trained speaker: whether a model actually learns fluent, faithful English from it (M1) and whether Ben would call it fluent (blind F0 judging) are both still unmeasured.
