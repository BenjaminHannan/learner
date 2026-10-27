# Sleep-B addendum 18: fix the two-step card writer (written 2026-10-27 ~12:00Z, before any run of it)

Labels: shown / suggested / untested. Model K2-Horizon-3.7B (bf16 base), Week-2, seed 1. Recipe: addendum 17's arm (arm B plus the
570-question gate) exactly, with one change: how REM writes its two-step cards. Not the village model, not the card experiments.

## Why
- Goal (Ben, 2026-10-25): two-hop >= 75 of 78, weights only.
- **Shown (arm B's result JSON, results_a14/result_k2c_r2.json):** the REM writer keeps very few of its two-step cards.
  - Chain cards kept / written, nights 2-7: 6/138, 15/346, 32/612, **0/1072**, 78/1920, 96/1586 (4-6% kept; none on night 5).
  - On night 5 the thinking averaged 17 tokens per sample (other nights: 280-450), and 1064 of 1072 samples never closed their think
    block. **Suggested:** the writer is the model as trained so far (adapter on), and night 4's training broke its thinking.
  - On night 6, 1362 chain units were open but only 960 could be tried (the per-night cap), so unusable pairs also take slots.
- **Shown (same JSON):** two-hop depends on the night a test's chain first became dreamable (both facts said on 2+ days):
  night 2-3: 9 of 9 right; night 4: 12 of 16; night 5: 9 of 19; night 6: 9 of 15; night 7: 0 of 19 (night 7 was undone).
  Tests whose cards came late or not at all fail.
- **Shown (addendum 14 probe, Week-1, base model, one night, results_a14/probe.json):** of 537 q_think samples, 72 were kept, 244
  dropped as bad, 210 unverified, 9 test leaks and 2 parse failures. The rejected examples show three fixable losses:
  - the verifier (base model, chat lines + the card's question) often names the answer only after a lead-in, and is cut at 20 tokens
    ("The person who moved to Defaglus is Molitrin. According to the messages, Molitr");
  - pairs made of one fact extracted twice ("Bouzeibas is the mentor of Glisemu" / "Bouzeibas has Glisemu as a mentor", far ends
    "Glisemu" and "Glisemu as a mentor") can never give a valid chain;
  - a capped think block often runs on after the question on the same line ("What boat is Duflodol? -- no, forbidden. Need find."),
    which fails the "line ends with ?" parse.

## The arm
- **k2c_r2_g570_w:** addendum 17's flags plus four writer switches, which together are the one change "the REM writer":
  - `--rem-writer base`: the base model (adapter off) writes the REM dreams (chains and gists). The facts are in the prompt, so the
    writer needs no memory of them.
  - `--rem-pairs distinct`: no pair whose far ends (normalized) contain one another.
  - `--rem-parse first_q`: the reply's first line is cut after its first "?", then checked as before.
  - `--rem-verify-tokens 96`: the verifier may write 96 tokens instead of 20. Its check is unchanged: the answer must appear in its
    reply.
- Everything else is addendum 17's arm, as it runs on Ben's PC: `--rem-chain-mode q_think --rem-dirs both --rem-tries 2
  --rem-steps-mult 2 --gate-arc-n 570`, `--arc-base`, revision 9d280ff7, seed 1, `--gen-bs 24` (16 on running out of memory),
  `--tok-budget 256`, the 14 GiB memory cap, report-only `--think-eval` and `--reword data/week2_reworded.json`.
- All four switches default to today's behaviour. With them off, a CPU smoke run's result JSON (addendum 17's flags, with `--rem-chain-mode q`)
  matches code 005265d6fb apart from timing and the four new entries in `args`.

## Pre-check (cheap; generation only, Week-1, no training)
`k2_chain_probe.py --variants q_think --tries 1 --gen-bs 24 --also-fixed`, one night (4 cycles), on Ben's PC: today's writer, then
the same seed with `--rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96` (`--rem-writer` has no effect without a trained
adapter).
- **Go** if the fixed run dreams at least 24 of the 27 reachable two-hop tests forward, and at least 3 more than today's run. Both
  runs share one tagged world in one invocation (`--also-fixed`). If this world has R reachable tests and R is not 27, the bar is
  ceil(0.88 R).
- **Otherwise** the full arm does not run. The fates of both runs are recorded, and the writer is redesigned first.

## Marks for the full arm (fixed now; paired exact McNemar against addendum 17's run, same questions)
If addendum 17 has no result, the comparisons are against arm B instead, with B's numbers.
- **G (Ben's goal):** two-hop >= 75 of 78.
- **S1 (the writer keeps cards every night):** no night with open chain units keeps 0 chain cards, and the week keeps at least twice
  as many chain cards as addendum 17's run.
  - **Wrong if** a night with open units keeps 0 chains again with the base writer.
- **S2 (more cards, more two-step):** two-hop >= addendum 17's + 8, with p < 0.05.
  - **Wrong if** S1 passes but two-hop is no higher than addendum 17's. Then cards are not the bottleneck; learning them is.
- **No harm:**
  - ARC-Easy 500 >= pre - 5;
  - diary pooled >= base_diary - 5;
  - recall C2+C4 >= addendum 17's - 3;
  - changed-new >= 53.3 (B's).
- **Reported:** chain fates per night, two-hop by the night each test's chain became dreamable, kept chains per night, thinking tokens,
  each night's gate score, new-wording recall, think-eval, wall time.
- **Expectation (not a mark):** 2-4x the kept chains, two-hop 55-75. Suggested only.

## Compute and PC order
Free: Ben's PC, in my existing slots (no new slot). The pre-check is about 1 h; the full arm 8-10 h, and it stops itself if it would
pass 11 h.
- Slot 1 (after the sleep race's round 1): the pre-check, then addendum 17.
- Slot 2 (after looping P1): this arm if the pre-check says Go; otherwise addendum 14's arm A, as planned.
- Slot 3 (after looping P2a): addendum 15's R8; slot 4 (after looping P2b): V8.
- If this arm takes arm A's slot, arm A does not run, and addendum 15's base is the defaults. That is the sealed rule's own fallback
  (A's flags only if A passes no harm), applied because A has no result. It is recorded here before any of these runs.
