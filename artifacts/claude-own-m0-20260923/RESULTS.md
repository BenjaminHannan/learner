# RESULTS — own-M0: conversational-mouth training pairs (builder, CPU only)

## Result

Registered verdict: PASS Pm0.1–Pm0.5. 20,000 train + 1,000 dev rows
written; filter dropped 0; fresh re-check fails 0; seal 3/3 OK after run.

## Marks table (integers)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| Pm0.1 train rows failing fresh re-run of check (20,000) | 0 | 0 | PASS |
| Pm0.1 dev rows failing fresh re-run of check (1,000) | 0 | 0 | PASS |
| Pm0.2 max single-reply share, train (worst status FORGOT 2.48%) | <= 3% | 2.48% | PASS |
| Pm0.2 max single-reply share, dev (ABSTAIN/FORGOT 3.00%) | <= 3% | 3.00% | PASS |
| Pm0.3 distinct templates per status, train (min 48) | >= 40 | 48 | PASS |
| Pm0.3 distinct templates per status, dev (min 48) | >= 40 | 48 | PASS |
| Pm0.4 dev names ∩ train names | 0 | 0 (64 vs 39 used) | PASS |
| Pm0.4 dev combos ∩ train combos | 0 | 0 (4000 vs 200) | PASS |
| Pm0.5 crashes | 0 | 0 (exit 0) | PASS |

Per-status top shares (train): ABSTAIN 2.30%, CLARIFY 1.32%,
FORGOT 2.48%, OK 1.97%, SAVED 2.00%, UNKNOWN 2.10%.
Per-status top shares (dev): ABSTAIN 3.00%, CLARIFY 2.00%,
FORGOT 3.00%, OK 2.00%, SAVED 2.00%, UNKNOWN 2.67%.
Distinct templates (train): ABSTAIN 48, CLARIFY 92, FORGOT 48, OK 51,
SAVED 50, UNKNOWN 50. Dev: ABSTAIN 48, CLARIFY 92, FORGOT 48, OK 51,
SAVED 50, UNKNOWN 50.

## Rows per status / per tag (integers)

Train: OK 7000, SAVED 3000, UNKNOWN 3000, ABSTAIN 2000, CLARIFY 1500,
WHOSE 1000 (status CLARIFY), FORGOT 2500 = 20,000.
Tags train: ANSWER 7000, ACK_SAVE 3000, ABSTAIN 5000, CLARIFY 1500,
FORGOT_ACK 2500, WHOSE 1000.
Dev: OK 350, SAVED 150, UNKNOWN 150, ABSTAIN 100, CLARIFY-tag 100,
WHOSE 50, FORGOT 100 = 1,000.
Tags dev: ANSWER 350, ACK_SAVE 150, ABSTAIN 250, CLARIFY 100,
FORGOT_ACK 100, WHOSE 50.

## Drops by filter rule (integers)

R1_missing 0, R2_extra 0, R3_caps 0, R4_status 0, train and dev.
Selftest (pre-seal, in-memory): 10 planted violations each caught with
the exact expected rule set; all 339 template checks pass.

## Every move (dev material, own data — not a panel)

1. Read plan §3.3, talk-fluency plan, our-policy decision, say_forms.json
   nouns, talker120 train schema (names-only read of heldout for the
   96-name blocklist).
2. Wrote check.py (R1–R4) and build.py (pools, 339 templates, turn
   frames, round-robin assignment, kind rotation).
3. Pilot selftest: 80 R3 + 2 R4 template misses found; fixed allowlist
   (+14 tokens) and 2 SAVED templates ("Glad to save… noted",
   "written that down and saved it"); fixed 3 FORGOT "Got it" clashes.
4. Pilot build: Pm0.2 miss (3.50–3.60% on kind-heavy lists) and 9 WHOSE
   combo overlaps found; fixed by per-list round-robin, kind rotation,
   stated_value in WHOSE records.
5. Wrote PASSMARKS.md, appended Pownm0.1–2 to ledger, sealed 3 files.
6. Registered run (uv offline, python 3.12): 20,000 + 1,000 rows, 0
   drops; verify exit 0; independent check.py CLI 0 fails both files;
   seal re-verified 3/3 OK.

## Deviations

- Used /usr/bin/python3 for pilots/selftest, mandated uv-offline
  python 3.12 for the sealed registered run and re-checks. Same code,
  same seeds.
- OPUS-RULES names artifacts dir 20260922-style; task brief fixes
  20260923, which was used.
- Dev uses 39 of 40 dev owner names (rotation simply never dealt the
  40th); bar is intersection = 0, still PASS.

## What it means (plain words)

The mouth now has 21,000 example conversations to learn from. Every
example was re-checked by an independent checker and passed: the right
name/value slots are there, no real names leak into the reply text, and
the wording fits the situation (hedges when it does not know, save-talk
only when saving, never restating a forgotten fact, asking "whose" for
"our"). No reply is overused (worst 3.00% on tiny dev splits), and dev
names/combos never appear in train.

## What it doesn't mean

This is not a trained mouth and not a fluency proof. It says nothing
about whether a model will actually learn from these pairs (M1), nor
about Ben's bar (fluent conversational English, judged blind on F0).
Grammar/naturalness of generated (non-template) replies is unmeasured.
