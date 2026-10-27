# Exp 146b RESULTS — doubt with hearsay exemption (Muse). REGISTERED MIXED: H1 FAIL, H2 FAIL, H3 PASS, H4 PASS, H5 PASS.

Target: loop146c = loop129b + Doubt146bMixin; loop146d = loop139b +
Doubt146bMixin (scripts/fable_doubt146b_store.py, fable_loop146c_agent.py,
fable_loop146d_agent.py, fable_doubt146b_probe.py, fable_doubt146b_bench.py;
configs artifacts/fable-doubt146b-20260922/loop146c-config.json,
loop146d-config.json). ONE CHANGE vs 146: hearsay/reported-speech/quoted
turns never record a doubt; only first-person refused teaches do.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| H1 146-D3 re-run on 146c | 31/32, only B07 fails; 0 stale, 0 lost | 28/32; failures B07 (predicted) + C03/G01/G02; stale-counter 1 | FAIL |
| H2 new 24-dialogue probe | 24/24 | 21/24; failures H13/H17/H18; stale-counter 1 | FAIL |
| H3 marks123 on 146c vs loop129b ref | per-case identical, all suites | identical: p2 64/64, p4 30/30, rt110 62/62, bench/q1/q4/rt81/sleep/soak identical | PASS |
| H4a bench 800 items 146c vs 146 rows | 0 moves | 0 moves (edit200/old/new/bench132) | PASS |
| H4b bench 600 items 146d vs 139b rows | 0 worse/lost, only 069 wrong->abstain | exactly 069 wrong->abstain; worse 0, lost 0 | PASS |
| H5 time per run | < 1500 s Mac CPU | H1 1.9, H2 1.6, H4a 44.5, H4b 27.3, H3 259.2, rt110-rerun 159.7 s | PASS |

H3 detail: p2 A2/A6/A8 and rt110 T4 match loop129b (the 146 hearsay-veto
moves are gone); q1 FAIL replies byte-identical to ref; q4 same
pre-existing leaks; soak 2000 turns 3 kill-9s, 0 lost/wrong/doubled.
H4b detail: 069 abstains with the doubt reply ("could not store ... one
fact"); bench132-162-style wrongs untouched. Control: the 7 non-vacuous
H2 hearsay dialogues (H01/H02/H03/H10/H20/H23/H24) all abstain under OLD
loop146 (doubts_left=1) and all answer the standing fact under 146c
(doubts_left=0) -- the probe is non-vacuous and the fix is what moves it.

## Cause of the H1 FAIL (3 cross-base cases, not the change)

C03/G01/G02 carry loop139-base expectations ("Lena's city is not
Bergen." -> "could you split that"); on the loop129b base the same turn
is a CONFLICT question ("Do you want me to change it ...?"), which
records no doubt by the untouched 146 rule. Proof it is not a 146b
regression: forcing ALL 32 dialogues through OLD loop146 gives
byte-identical outcomes (28/32, same 4 failures, same replies;
probe146b-h1-old146-forced-report.json). The stale-counter 1 is G01's
standing "Oslo" answer with doubts_left=0 -- correct base behavior, not
a doubt-mechanism stale. B07 failed exactly as predicted (opinion
correctly clarifies).

## Cause of the H2 FAIL (3 authoring errors in my sealed file, not the change)

H13 assumed the 139-base split-refusal for "not Bergen" on a 129b-base
loop (CONFLICT instead); H17/H18 assumed a plain re-teach
("Tom's boss is Alice.") Saves, but the 129b base CONFLICTs on plain
value change (146's own C01/C02 re-teach with "Actually," prefix --
that form Saves and clears). All three verified byte-identical on OLD
loop146. Every dialogue the one change touches passes: 10/10
hearsay/quoted contradictions keep the standing answer with 0 doubts;
4/4 first-person refusals doubt + abstain; mixed H15/H16, clears
H17-step-1/H18-step-1/H19-restart, H20/H23/H24 all pass.

## What it means

A quoted third party can no longer veto taught facts: hearsay
contradictions clarify and the standing answer survives (0 doubts),
while first-person refused corrections still abstain with a re-teach
prompt; bench and marks123 behavior is otherwise identical to 146/139b
bases (0 new wrong, 0 correct lost, 069 improved to abstain).

## What it does not mean

The probes do not bless hearsay as true (contradictions still clarify,
never write); 146's D4 FAIL is not rewritten (it stands, diagnosed);
cross-base probe expectations (139 replies on a 129b loop) are still
unmatched by construction; doubts still never add, edit, or delete facts.

## Deviations

1. Pre-seal dev: pure-function checks + BASE loop129b evidence runs only
   (scripts/scratchpad/doubt146b-evidence/); the new loops never ran
   before seal + ledger (SEAL.sha256.txt; P146b.1-5).
2. H3 rt110 flake: full-run rt110 showed 1 then 3 cases differing ONLY in
   the volatile `statuses` log annotation (verdicts + replies identical;
   isolated T4 re-run matched). Re-ran full marks123 (259.2 s, verdicts
   all match) + rt110-only rerun (62/62 per-case identical, kept in
   marks146c-rt110rerun/). A full-marks base-loop129b control
   (marks129b-control/) flakes WORSE on unmodified code (incl. verdict
   moves from empty-turn mailbox races), attributing the annotation noise
   to the sealed subprocess harness, not 146b.
3. All registered waves ran solo; daemon wrappers honor --idle-seconds.

Reproduce: PASSMARKS.md command block (sealed SEAL.sha256.txt).
Ledger: P146b.1 FALSE, P146b.2 FALSE, P146b.3 TRUE, P146b.4 TRUE,
P146b.5 TRUE. Exp 146 verdicts untouched (FAIL stays FAIL).

## Questions for Ben

None. Defaults taken: leading-attribution/generic-clarify hearsay
("Ann said ...", "told me ...") is exempt even though the 146 parsers
never doubted it (behavioral bar only); ambiguous subjects keep 146's
rule; CONFLICT/forget paths untouched.
