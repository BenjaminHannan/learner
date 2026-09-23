# 118 — Ears leftover brake (exp 118, muse, 2026-09-22)

Registered single-change follow-up to the exp-47 FAIL (ears rung 2), built on
the exp-95 diagnosis (doc 95). One change, plain software, Mac CPU, no
retraining: a LEFTOVER BRAKE. Result: SAFE fixed (0 silent writes, all seeds),
coverage lost (B3 fails every comparison) — recorded as a split verdict.

## 1. The diagnosis it answers

Exp 47 failed SAFE on 2 silent wrong writes (t_trap #259 "Fertelovic aside,
…" and #751 "… lisvannov aside, …", margins ≤ 0.016). Doc 95 §3: every brake
passed — brake 4 checks only `[UNK]` wordpieces, no brake watches leftover
phrasing, and brake 5 validates the adapted item the sentence supports. The
registered fix: refuse any write whose sentence contains content outside the
frame's subject/relation/value spans.

## 2. Design

`scripts/fable_brake118_leftover.py`, one function: `leftover_blocks(text,
frame, chspans) -> (blocked, reason, words)`. WordPiece spans map to character
ranges (tokenizer re-encode; deterministic, no weights). A word is CONSUMED if
it overlaps a span, is in the allow-list, or is a cue word of the predicted
relation (class-name tokens + closed_map + LE.RELATION_MAP surfaces that
canonicalise to it — code tables only, never panels). Any other alphabetic
word (len ≥ 2, possessive stripped) blocks the write: EXECUTE downgrades to
ECHO when the sealed pair-ECHO conditions hold, else REPHRASE. ECHO is never
braked; abstain/span-less frames never blocked. Taus reused sealed; the brake
is the only delta.

Allow-list discipline (the point of the experiment): V1 closed-class English
+ copula + interjections, fixed BEFORE any panel read. V2 = 11 framing words
tuned on CAL only (each unblocked ≥1 CAL correct execute, 0 CAL wrong
writes): one keep mind hmm quick way listen thing actually meant say. No
test-panel token was ever added. Consequence, stated upfront: draws with new
framing vocabulary will over-fire.

## 3. What happened (artifacts/fable-brake118-20260922/)

B1 PASS: 0 silent /6,500 in ensemble + all singles; trap written 0; both
"aside" writes now ECHO. B2 PASS: NEG/ASK/NEWREL all 0, all seeds. B3 FAIL:
SEEN stmt-exec 455→191 (singles 83→19, 527→238, 100→27); NEW 640→79 (102→10,
766→98, 103→0). Correct counts bit-identical to exp 47 (downgrades became
correct ECHOs). B4: SAFE/NEG/NEW/NAMES/ASK/NEWREL pass; SEEN-exec fails vs
both bars (191 < 736 and < corrected 589); WEB still 0/46. B5: reading94
0 writes all seeds with and without the brake (matches exp 106 exactly:
REPHRASE 398/396/398 — pipeline cross-check). Corrected bar, registered
pre-run: exp 47 intended ceil(0.90×817)=736; over executable concrete rows
ceil(0.90×654)=589.

## 4. Why, and what next

Firing analysis: test draws frame teaches with introducers CAL never used
("write this down", "just so you know", "New fact", "at the moment"). A fixed
list tuned on one draw cannot cover the next draw's framing — the experiment
measures exactly that gap (safety generalises, framing lists don't). Ranked
next single changes: (1) grammar-based framing detection (imperative/discourse
clause vs content clause) instead of word lists; (2) span-swallowing guard
(value span covering ", X too" patterns — 4 CAL misses show the hole);
(3) pair with WebRED-length coverage work since executes stay ~0 on real text.

## 5. Limits

Does not show the brake is net-good (coverage cost dominates here); does not
move WebRED; does not certify any threshold; tuning and testing draws differ
by construction, so CAL numbers never promised test coverage. Ledger P118:
TRUE/TRUE/FALSE/TRUE/TRUE(vacuous) — 4/5 with the FALSE honestly priced at
0.65 beforehand.
