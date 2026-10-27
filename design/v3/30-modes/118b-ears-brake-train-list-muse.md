# 118b — Train-list leftover brake (exp 118b, muse, 2026-09-22)

Registered single-change follow-up to exp 118, which showed the leftover brake
buys safety (0 silent writes, all seeds) at a coverage price (SEEN 455→191,
NEW 640→79) because its 11-word framing list was tuned on the CAL draw while
test draws use introducers CAL never saw. The one change: replace the
CAL-tuned list with a list derived from the exp-47 TRAINING pool — the
sentences the ears were trained on. Result: safety holds at zero, SEEN
recovers inside its bar (413 ≥ 410), NEW does not (510 < 576). Split verdict.

## 1. Design

Rule (brief-fixed): a word is allowed iff it appears OUTSIDE the gold
subject/value spans in ≥ K training sentences and inside a gold VALUE span in
< J of the sentences containing it. The relation is a class label with no char
span, so spans = subject + value/object; span-less NO_FACT/UNSURE rows count
every word as outside. Tokenisation is byte-identical to the brake. Training
sentences are regenerated with the exp-47 builder (`synth_pool_rows` with the
sealed seeds + `webred_pool_rows`); the pool identity gate reproduces the
BensPC pool exactly (kept=140,903, dropped=614), so these are the ears'
sentences, not a proxy. K,J are fixed on CAL only: grid K ∈ {3,5,10,20,30,50}
× J ∈ {0.01,0.02,0.05}, lexicographic selection (max CAL blocked-wrong at
tau=0, then min CAL blocked-correct at sealed taus, then smaller list, then
aside-free, then larger K / smaller J) → **K=50, J=0.01, 2,618 words**.
V1 and the relation cue-word rule are reused imports, byte-identical to 118;
the brake/downgrade semantics are unchanged. Scripts: `fable_brake118b_
trainlist.py` (pool stats), `_tune.py` (CAL K,J), `_leftover.py` (brake),
`_score.py` (118's sealed scorer + leftover-word firing counters).

## 2. What the tuning showed (CAL only, pre-seal)

Safety-first selection picks the smallest list (2,618 words): it blocks the
most CAL wrongs at tau=0 (260/273 vs 229 for every K≤30 list) and is the only
grid row without "aside" ("aside" has 33 outside-span training occurrences —
every K≤30 list contains it, which would re-open the trap writes). Price:
425/2,359 CAL correct-execute instances stay blocked (118's CAL-tuned list: 0)
— residual offenders "one" (242) and "mind" (187). Both exclusions are
mechanistic, not noise: "one" sits inside gold VALUE spans in 7.2% of training
occurrences (genuinely content as well as framing); "mind" occurs outside
spans 31 times in training (below K=50). CAL wrong writes at the sealed taus:
0 exist with or without the brake (vacuous); the tau=0 view is the stress
signal. Diff vs 118's V2: +2,609 words, −2 ("mind", "one").

## 3. What happened (artifacts/fable-brake118b-20260922/)

B1 PASS: 0 silent /6,500, ensemble + all singles; traps #259/#751 fire on
"aside" and ECHO. B2 PASS: NEG/ASK/NEWREL all 0. B3 SPLIT: SEEN 455→413
(−9.2%, bar ≤10%) but NEW 640→510 (−20.3%); singles −8%…−26%. B4 PASS (113.8
s). reading94 0/0/0 with and without the brake (vacuous, matches 106).
Correct counts bit-identical to exp 47 (downgrades → correct ECHOs). Fires fall
264+561 → 42+130. Every remaining downgrade class (ensemble leftover counters):
"new" (16 SEEN / 90 NEW — "New fact" draws dominate t_new; J-excluded at
18.5% value contamination), "one" (15/17 — J-excluded at 7.2%), "days" (0/28 —
"these days" temporal framing absent from training AND J-excluded at 4.5%),
and "about NAME:" double mentions (11 SEEN — a span-coverage gap: the frame
covers one mention, the "about"-phrase name is a true leftover).

## 4. Limits and next

Does not show the brake is net-good (NEW still fails its bar by 66 executes);
does not move WebRED (ensemble executes 0 on wpos/wclosed/wnewrel); does not
certify any threshold. The experiment bounds word-list approaches: lists
generalise exactly as far as the training distribution's framing vocabulary
reaches, and the J-filter provably must exclude words that double as content
("new", "one", "days") — no (K,J) setting recovers those draws. Ranked next
single changes (unchanged from 118): (1) grammar-based framing detection
instead of word lists (would cover "New fact", "these days", "One thing"
uniformly); (2) span-swallowing guard for "about NAME:" double mentions (11
SEEN executes); (3) pair with WebRED-length coverage work. Ledger P118b:
TRUE/TRUE/FALSE/TRUE/TRUE(vacuous) — 4/5 with the FALSE priced at 0.40
beforehand.
