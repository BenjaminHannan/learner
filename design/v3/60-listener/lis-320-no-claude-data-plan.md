# lis-320 plan: reader training data with no Claude-written or Claude-judged rows

Reading-facts thread, written 2026-09-26 16:42 UTC. This is a draft plan, not a registered test.

## Why
Goals page rule (Ben 16:39, 5f38f110e): nothing a model trains on is written or judged by Claude. The current reader (lis-319,
lis-319f) trains on 50,044 rows (lis-319f: 51,244). 23,044 of them are Opus-written dialogs kept on Opus-labeller agreement
(opus 5,012, opus301 4,960, chat318 7,936, hist319 5,136). 27,000 (o0b) come from a code world-sampler with exact labels,
but its wording templates were written by a Claude builder agent (the Thread manager rules whether o0b counts as code).
Tests are unaffected: blind Claude judges that only score sealed tests carry on.

## Data design (one retrained reader, lis-320)
1. Seeds by code: a world sampler (people, relations, values, fictional names) and a per-dialog script of turn intents:
   teach (1-3 facts), correct (replace an earlier value), backref (fact about someone named earlier, by pronoun or role word),
   former (a past job or home, labelled as former), job+home in one sentence, ask, and lookalikes (question, plan, doubt,
   someone else's claim, hypothetical, negation only, confirm, ambiguous pronoun), plus smalltalk. Labels come from the seed, so
   code writes every label.
2. Wording by GLM 5.3 Flash (OpenRouter, from the Mac; the key stays in ~/.config/openrouter/key, and scripts read it
   themselves). One call per dialog. It gets the intents and exact values and must write the user turns and short
   assistant replies. Temperature is high enough for varied, messy chat.
3. Code checks each row against its seed: every value is a verbatim whole-word span of its turn; the owner is spelled
   verbatim where the intent says (turn, or only earlier turns for backref); lookalike turns contain no forbidden
   stated-as-true pattern for their value; no dev or test name clashes. Failing rows are dropped, never repaired by hand.
4. Optional second check by a different model: GLM reads each kept turn blind (same prompt as the reader) and a row is
   kept only if its frame agrees with the seed. That is a model-judged label, but not a Claude one.
5. The mix replaces the 23,044 Claude rows one for one (same family proportions). o0b stays or goes on the manager's ruling.
   The lis-319f former relabels (code) and the lis-319o owner contract (compiler) carry over.

## Order
- Pilot first (Mac, GLM, 30 dialogs): code-check pass rate and cost per 1,000 rows, measured, not estimated.
- Then generate the full set, run the dry build (counts only), and register lis-320 vs lis-319f on a fresh sealed panel
  (Claude-written test panels and blind Claude judges are allowed for tests), with marks sealed before training.
- Training on a rental ($2 line, about $1 per lis-319f run).
