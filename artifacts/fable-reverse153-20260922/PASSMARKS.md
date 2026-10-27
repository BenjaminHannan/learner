# Exp 153 PASSMARKS — reverse questions on taught facts (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard). Director probe on loop150: after
"Tom's boss is Bob." every reverse question gets "I didn't understand
that". Reversal is a benchmark target (plain transformers fail 'A is B ->
B is A'; the notebook stores triples, so reverse lookup is exact).

THE ONE CHANGE (scripts/fable_fix153_reverse.py, Reverse153Mixin; thin
loop153 = loop150 + mixin in scripts/fable_loop153_agent.py with --daemon
entry incl. idle_seconds; loop150 imported read-only, no file edited): a
reverse-question stage that runs ONLY when the forward question path did
not understand the message (base ears returned exactly the loop's own miss
clarify). Four closed frames -> map R with the loop's own relation table
(FakeEars._relation) -> collect every subject S with a live taught (S,R,V)
triple (source == taught AND active, so corrected-away, forgotten,
refused/hearsay content never answers) -> "Bob is the boss of Tom."
(several: "... of Tom and Sue." in teach order; none: "I don't know anyone
whose boss is Bob.", never invents). Clarify actions only: a reverse
question never writes. Multi-hop reverse matches no frame and keeps the
base clarify (out of scope, never answered wrong).

## Sealed frames (exact; case-insensitive; trailing "?" required)

- F1 `Whose R is V?` (e.g. "Whose boss is Bob?")
- F2 `Who|What is V the R of?` (e.g. "Who is Bob the boss of?")
- F3 `V is the R of whom|what|who?` (e.g. "Bob is the boss of whom?",
  "Kelm is the capital of what?")
- F4 `Which|What X has V as its R?` (e.g. "Which city has Kelm as its
  capital?"; X is a single word, ignored)

R and V spans are single noun phrases (letters/spaces; no "'s"/"of"/
"that"/"who"/"which"/"where"/"and"/punctuation): multi-hop shapes
("Whose mother's boss is Bob?") match no frame.

Sealed inputs:
- V1/V2 probe: artifacts/fable-reverse153-20260922/cases153.json (50
  dialogues: 26 single-subject reverse over 8 relations x all 4 frames, 12
  multi-subject exact-set, 12 negatives: 3 relation-mismatch + 3
  never-taught-value + 2 corrected-away + 2 forgotten + 1 hearsay-refused +
  1 multi-hop-clarify).
- loop153-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: loop150's marks123 run
  (artifacts/fable-fix150-20260922/marks150).
- G3 reference: exp-152 phone sessions T-T run
  (artifacts/fable-session152-20260922/sessions152.json; runner imports
  scripts/fable_session152_run.py and swaps the target to loop153).

## Marks (integer counts, every seed/case reported, never averaged)

- V1 new probe of 50 dialogues through loop153
  (scripts/fable_fix153_probe.py --agent loop153): 26/26 single-subject
  exact replies; 12/12 multi-subject exact sets; 12/12 negatives honest
  (11 exact don't-know + N11 base clarify); 0 wrong over all 50.
- V2 0 FACT writes from any of the 50 reverse-question turns.
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts
  identical to the sealed loop150 rows
  (scripts/fable_fix153_bench.py reuses scripts/fable_loop129b_bench.py by
  import, daemon/config swapped to loop153); ZERO moves predicted.
- G2 scripts/fable_marks123_all.py suites per-case verdict-identical to
  loop150's marks150; ZERO moves predicted.
- G3 exp-152 phone sessions re-run with loop153 swapped in for T-T: every
  reply identical to the sealed T-T run; ZERO reply moves and 0 new WRONG
  predicted, 0 new writes except none predicted (no session turn matches
  any reverse frame).
- G4 every registered run < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrapper
  takes idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Director reproduction on loop150: teach "Tom's boss is Bob." saves;
  "Whose boss is Bob?" -> "I didn't understand that. Could you say it
  another way?".
- parse_reverse over all 5 director probes -> exact (R,V); multi-hop
  ("Whose mother's boss is Bob?"), bench MQuAKE shapes ("Who is the
  composer of Gilded Mirrors?", "What is the capital of France?") -> None.
- Full-gate (parse + single-phrase screen) fires NOWHERE on: 600 bench
  questions (edit200 + old_s2fresh + new_121; 7 parse-only hits all carry
  "that"-relatives, rejected), 180 session152 turns, 101 '?' literals from
  suite scripts, redteam136/cases150/loop150-redteam JSONs.
- Base calibration (scripts/fable_fix153_probe.py --agent loop150 on the
  frozen probe): 49/50 WRONG (all reverse Qs clarify, 0 answers) + N11 OK
  (multi-hop clarifies on base too); 0 SETUP-FAIL (all setups store);
  0 writes on all 50 question turns.
- Code responsible, read before sealing: ChainEars total miss
  (scripts/fable_loop90_agent.py:291-292), FakeEars fallthrough
  (scripts/fable_agent_loop.py:148), compose_question narrow reversal
  (scripts/fable_bench73_english_arm.py:246-336), N-hop/2-hop double-None
  fallback (scripts/fable_loop113b_agent.py:101-102); reused relation
  table (scripts/fable_agent_loop.py:150-152) and triple store
  (scripts/fable_loop90_agent.py:101-114).
