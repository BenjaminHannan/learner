Rebuilding the failed run with hard-case rows — assembling your sealed training pipeline.
Your core specs are in hand — now tracking down the sealed blind panel and prior run details.
Found your GPU machine's prior setup — now pulling the exact environment details.
GPU and training environment verified — now staging the code and checking the model weights.
Staging the data-integrity checks before building the training set.
Training complete — now reading the dev set to pick the confidence threshold.
Sweep points to T=0.995 — now scoring each dev source at that threshold.
Dev numbers are locked — sealing the threshold and model before touching the blind panel.
Panel seal verified — running the reader on the blind panel exactly once.
Model secured on both machines — now writing up the registered result.
Ledger updated — final check that the push set is complete and the worktree has additions only.
Verdict: FAIL (lis-301 does not pass; P301.2 recall 51/145 = 35.2% vs bar 85%).

Marks table (arm A = reader + compiler at T = 0.995, 240 blind panel turns, run once):

| Mark | Bar | Integer counts | Result |
|---|---|---|---|
| P301.1 wrong-save turns | ≤ 1 of 240 | 0 of 240 | PASS |
| P301.2 exact recall of gold writes | ≥ 85% | 51 of 145 (35.2%) | FAIL |
| P301.3 ASK turns read correctly | ≥ 90% | 34 of 40 (85.0%) | FAIL |
| P301.4 our/we turns that ask whose | ≥ 90% | 17 of 18 (94.4%) | PASS |
| P301.5 unparseable outputs | ≤ 2% of turns | 0 of 240 (0%) | FAIL-free, PASS |
| P301.6 median read time (GPU) | ≤ 1,500 ms | median 1522.7, p90 2158.8, max 2942.8 | FAIL |

Every move, every miss (category level only, nothing quoted):
- 0 wrong-save turns at T; no family wrote a wrong fact. All no-save families had 0 wrong turns: negation 12, check 12, suppose 10, plan 10, reported 8, chat 8, pronoun-ambiguous 6 turns.
- Recall hits by family at T: tell-single 6/14, tell-multi 2/24, tell-plural 9/18, tell-appositive 0/21, tell-verb 6/12, tell-typo 5/8, tell-self 5/7, correct 9/19, short-answer 3/7, pronoun-clear 5/13; 93 of 145 gold facts held back; turn-exact 43/105.
- ASK misses: 6 total (2 inverse, 2 lowercase, 2 twohop); wh 11/11, yesno 7/7.
- we: 17/18 asked whose; our-we family 0 gold writes, 0 wrong turns.
- Report-only: wrong facts per saved fact 0/51 at T (5/147 at T=0); per turn 0/240 at T (4/240 at T=0). At T=0: recall 142/145 (97.9%), 4 wrong turns (1 pronoun-ambiguous, 1 tell-typo, 1 our-we, 1 tell-appositive; 2 on no-save turns), 0 held back.
- Dev at T: 462/761 hits (60.7%), 2 wrong turns (both o0a2-family rows), ask 77/81, we 13/13. Per src: o0b_l2 239/352, opus_dev 32/74, o0a2 141/238, opus301_dev 50/97; 0 wrong turns in every src except o0a2.
- Training: 4622/4622 steps, 2 epochs, 26.05 min, 4727.7 tok/s, dev loss 0.0545, batch 16, seed 300. Base snapshot re-verified (sha 7ab8fd86…); merged sha b4fd93a2… kept at ~/premonition-models/lis301-merged/ (hash verified) and on BensPC. Dollars: $0.
- Data: train 36,972 (o0b 27,000 + opus 5,012 + opus301 4,960), dev 959 (428+131+263+137), opus301 agreed 1,377, dev dropped 45 (8+37). Matches DATA-AUDIT exactly. Seals: data 14/14 + 13/13 OK, key 2/2 OK, SEAL-run written before the panel.

Deviations (environment only; sealed code imported and run unmodified, never patched): reused the lis-300 venv and base-model snapshot (sha re-verified) with a new work dir C:\Users\benja\lis301; PYTHONUTF8=1 and venv certifi bundle env vars as in lis-300; batch-8 fallback not needed; 150-min cap never bound.

What it means (plain high-school English): the extra hard-case rows did buy safety — the blind panel now has 0 wrong saves (lis-300 had 1) and dev wrong turns fell from 6 to 2. But the safety gate still throws away almost two thirds of the true facts (93 of 145 held back), so recall fell to 35.2% (lis-300 had 51.8%), and dev still has no threshold with zero wrong turns. Two of the three PASSMARKS "proved wrong" clauses trip (P301.2 < 75%; no zero-wrong dev T below 0.995), so more hard-case data alone does not make the reader safe and useful at once — the next step is a different mechanism, not more rows.

What it doesn't mean: it doesn't mean the reader can't read (142 of 145 with no gate, 97.9%, same as lis-300), and it doesn't mean the test leaked (N–Z names never trained on, seals checked, panel run exactly once).

PUSH files on disk: artifacts/claude-lis301-20260923/{RESULTS.md, THRESHOLD.txt, SEAL-run.sha256.txt, dev_sweep.txt, panel_score.json, panel_score_T0.json, train_summary.json, train_log.jsonl, dev/ (dev.jsonl, dev_rows.jsonl, dev_pred.jsonl)} plus 6 appended ledger lines P301.1–P301.6. Note: artifacts/ is gitignored in this checkout, so the watcher will need to force-add these paths.
