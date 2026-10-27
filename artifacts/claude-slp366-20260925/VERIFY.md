# slp-366 blind recount (VERIFY)

A separate recount of results.json → `runs`, done with print-only Python run from stdin (no files written, nothing run
except reading). I computed my own numbers first and only then read the precomputed `marks` key. The two agree on every mark.
Sources read: PASSMARKS.md (including the Run 1 VOID note), scripts/claude_slp366_scorecard.py,
scripts/claude_slp366_main.py, scripts/claude_slp364_gate.py (build_probes, ask_all, _grade), and a short look at
scripts/claude_slp360_test.py:build and the chains in scripts/fable_sleep130_agent.py.

## Marks

| Mark | Seed | My value | Bar | Result |
|---|---|---|---|---|
| P366.1 taught one-hop right, every night | 1 | 27/27, 60/60, 112/112, 120/120, 120/120, 120/120 | all | pass (but see check 2: nights 4-6 are a sample) |
| P366.1 | 2 | same as seed 1 | all | pass (same caveat) |
| P366.2 made-up lure answers, every night | 1 | 0 on each night (0/3 … 0/8) | 0 | pass (see check 4 on what "made-up" counts) |
| P366.2 | 2 | 0 on each night (0/3 … 0/8) | 0 | pass |
| P366.3 kept words stay ≥ 95% | 1 | 6/6 words ≥ 90% on their own night (13/13 each); lowest later value 100% | yes | pass |
| P366.3 | 2 | same: 6 learned, lowest later 100% | yes | pass |
| P366.4 word_new, nights 2-6 | 1 | 3/3, 9/9, 18/18, 30/30, 45/45 (lowest 100%) | ≥ 90% | pass |
| P366.4 | 2 | same | ≥ 90% | pass |
| P366.5 final night word rate, SLEEP − NOSLEEP | 1 | 118/118 (100%) − 0/118 (0%) = +100 | ≥ +50 | pass |
| P366.5 | 2 | 118/118 − 0/118 = +100 | ≥ +50 | pass |

Other facts from the runs: every SLEEP night was kept (6/6 per seed) and no night had a gate reason. Word probe totals were
13, 28, 46, 67, 91, 118, which are exactly the numbers the world design predicts (check 2). The prediction that some
grown-slot words might not install was wrong in a good way: father_of_mother, boss_of_mother and teacher_of_mother each
scored 13/13 on their own night. In the precomputed `marks`, all five marks are true for s1 and s2, and learned_on_night,
the 100.0/0.0 rates and kept all match my numbers.

## Checks

**1. Are the seed 1 and seed 2 worlds different?** Only in their names.
- *Shown (results.json):* apart from timing (sleep_seconds and total seconds), every per-night field is identical between
  seeds in both arms. My comparison returned True for SLEEP and for NOSLEEP. The timings differ (for example night 6 took
  427.3 s vs 394.9 s), so these were two separate executions and not a copied result.
- *Shown (code):* results.json stores no names. In `build_days`, the seed changes only one thing: `"" if seed == 1 else f"s{seed}"`
  is added to the end of every name (the correction names become e.g. `Geq100s2n`). The relations, group sizes,
  number of people, teaching order, corrections and lures are the same for both seeds. My copy of the builder gives
  408 entities per seed, with 0 names in common (for example `Faq100` vs `Faq100s2`).
  `claude_slp360_test.build` also passes the seed to the sleeper's own RNG seeds (sleep145/130/131/115/104_seed).
- *Suggested:* seed 2 is the same world with its names relabelled and a different sleeper RNG, so it does not
  replicate the result on a second world. Identical counts are what a deterministic path would give on a relabelled copy.
  Treat this as n = 1 world run twice, not 2 worlds.

**2. Does "taught 120/120" on nights 4-6 mean every fact was checked?** No. It is a fixed sample.
- *Shown (code):* the scorecard's taught probes are `G.build_probes(loop)` with only kind T kept, and MAX_T364 = 120 caps
  them. The scorecard builds its word probes itself with no cap, so the 150 cap (MAX_W364) does **not** apply to the
  scorecard's word counts. It applies only inside the gate's own keep decision, where there are 118 or fewer complete
  chains and the cap is never reached. MAX_L364 = 60 does limit the gate's lure probes.
- *Shown (arithmetic that matches teach_turns 27/34/53/49/55/61 in results.json):* the number of distinct taught
  one-hop facts is 27, 60, 112, 160, 214, 274 by nights 1-6. Only 120 of them are checked on nights 4, 5 and 6
  (75%, 56% and **44%**). My counts for nights 1-3 match the recorded n exactly.
- *Suggested (my copy assumes entity ids E0001… follow the order of first mention, which fits `new_entity`'s
  `E{len+1:04d}`):* probes follow entity-id order, so the same 120 facts are asked every night from 4 on: all of days
  1-3 plus 8 of day 4's 48. No one-hop fact taught on days 5 or 6 is ever asked. Four of the five corrections fall inside
  the checked set. Day 6's correction (of day 5's first asked person) does not. The gate's "taught answer changed" check uses
  the same capped set, so it has the same blind spot.
- *Shown, partial mitigation:* `_walk` needs exactly one taught row at every hop. The word-probe totals (67/91/118) match
  the design exactly, so every chain fact still exists as a single taught row on every night. That means the facts are
  still in the notebook. It does not show that their one-hop answers are right.

**3. Are NOSLEEP's 0% word scores "I don't know" or wrong names?** They are not wrong names. Whether they are honest
"I don't know" answers is suggested but not shown.
- *Shown:* NOSLEEP records `wrong` = 0 in word_old, word_today and word_new on every night for both seeds, and 0
  made-up lure answers. No reply named a notebook person outside the allowed set.
- *Not shown:* results.json keeps only n/right/wrong, not abstain vs "other", and stores no reply text.
  *Suggested:* they are abstains, because the contract's MISSING_FACT template is "I don't know {subject}'s {relation}."
  One caveat applies: a reply that gives an intermediate person as the answer (one hop short) counts as allowed (`ok` = path[:-1]),
  so it would show as abstain/other, not wrong.

**4. Parts of the design that make a mark easier to pass than its wording suggests**
- *Shown (P366.2):* for a broken-chain lure, `ok` = the known path, so a reply that names the lure's known first-hop person
  **as the answer** is not counted as made-up. `wrong` also counts only names that already exist in the notebook, so an
  invented name that is not in the notebook is graded "other" and not made-up. There are also only 3-8 lures per night.
  Two of them are the same two invented names asked about maternal grandmother every night.
- *Shown (all word marks):* `_grade` checks "right" first. A reply that names the right person **and** other wrong
  people still counts as right.
- *Shown (P366.1, word marks):* both probe lists are built from the notebook **after** the night, not from the teaching
  script. A lost taught fact would drop its probe instead of failing it, and a person with a broken chain is skipped
  (`if end is None: continue`). The exact totals in check 2 show that this did not happen here, but the marks themselves
  would not catch it.
- *Shown (P366.1 "corrections applied"):* a T probe wants every *current* taught row. If a correction failed to replace
  the old row, a reply naming both old and new would still grade right. The corrected person's word probe is dropped
  (the chain now ends at a new name), so the scorecard never tests any correction as a word.
- *Suggested (P366.5):* NOSLEEP never sleeps, and words are learned only in sleep, so its 0% is fixed by the design.
  The +50 bar in practice asks only whether SLEEP reaches ≥ 50%.
- *Suggested/untested (P366.4):* transfer people for an old word are taught on day d and scored after night d's sleep.
  So "generalisation" is measured after another full night with those facts present, not straight after teaching.
  If the sleeper writes sleep rows for everyone whose chain is complete, word_new would test that write-out and not a
  learned rule. The data here cannot tell these apart.
- *Suggested (P366.1):* the checked set is frozen at days 1-4, so P366.1 cannot fail from damage to anything taught on days 5-6.

**5. Seal check** (`shasum -a 256 -c artifacts/claude-slp366-20260925/SEAL.sha256.txt`, run from the tree root)
- *Shown:* `scripts/claude_slp366_scorecard.py: OK`, `scripts/claude_slp366_main.py: OK`,
  `artifacts/claude-slp366-20260925/PASSMARKS.md: FAILED` (1 mismatch, as expected).
- *Shown:* I took PASSMARKS.md with the "## Run 1 VOID" section removed, ending in a single newline, and it hashes to
  exactly the sealed value (516a7516…). So the marks table and the text above the VOID note are unchanged since sealing.
  The only change is the appended note.
- *Suggested:* the seal covers main.py, which by the VOID note's own account was written after run 1 crashed. So this
  seal file was written after run 1. It shows that the marks were fixed before run 2 (results.json is dated 03:11), not
  before run 1. The scorecard's timestamp (02:28, before run 1 at 02:41) is the only evidence of an earlier date. The
  timestamps in this tree may come from a copy, since PASSMARKS, SEAL and main.py all read 02:54:58.98. I also checked the
  crash the note describes: `marks366` is defined after `if __name__ == "__main__"`, so it is not yet defined when
  `main()` runs as a script. The wrapper imports the module, so it avoids this.

## Plain summary for Ben
Recounting from the raw per-night numbers: every mark passes on both seeds, and the file's own results say the same.
Keep three limits in mind. First, "seed 2" is the same world with "s2" added to every name, so this is really one world
tested twice. Second, from night 4 on the taught-fact check asks the same 120 facts each night, and by night 6 there are 274.
Nothing taught on days 5-6 was ever asked directly. Third, the made-up-answer check is lenient: it would miss an invented
name that isn't in the notebook, and it would miss a lure answered with the one person the model does know.
