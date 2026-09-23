# lis-301: our own reader, second try, with targeted hard-case training rows

Written by the listener thread (Opus) on 2026-09-23, before any lis-301 training. lis-300 was a registered FAIL (P300.2 recall 71/137 = 51.8%). This is its one diagnosis-driven follow-up.

## Diagnosis (lis-300 dev only; the lis-300 panel was read by category only)

- The threshold rule needs 0 dev wrong-save turns. Dev never reached that (38 at T = 0, 6 at T = 0.995), so T fell back to 0.995, and recall collapsed.
- Of the 6 dev wrong turns left at T = 0.995:
  - 3 are dev-key errors: the o0a2 key "fixes" typos ("Lenn" becomes "Lena"), while the spec keeps values as typed.
  - 1 is a value-boundary call ("2011 Corvan").
  - 2 are real misreads: reported speech read as a plain statement.
- The 38 dev wrong turns at T = 0 are hard cases that were rare in training:
  - reported, check and suppose turns read as statements;
  - relation direction flipped (founded, painted, wrote, teaches);
  - verb relations confused (died in, studied at, worked in);
  - unknown relation words mapped to near names;
  - the wrong owner in contrast turns;
  - garbled mixed tell-and-ask turns;
  - typo keys.
- On the panel at T = 0, 5 of the 7 wrong turns were ambiguous pronouns. The training set had 17 such rows, out of about 32,000.

## The one change

Training data. lis-300's data is rebuilt unchanged, then up to 1,500 new Opus-written rows are added (`data/opus_w4..w6.jsonl`, families weighted to the hard cases above, with person names A–M). Only rows that a blind second Opus labeller reproduced are kept (`scripts/claude_lis300_agree.py`). They are repeated 4 times, and 10% go to dev. The builder is `scripts/claude_lis301_data.py`.

These stay identical to lis-300:
- base model, LoRA settings, epochs, learning rate, batch, max length, seed 300;
- prompt, frame format, confidence and reader code;
- the compiler;
- the threshold rule (the smallest grid T with 0 dev wrong-save turns, else 0.995);
- the scorer.

Conventions that frame-spec.md implied but did not state are written down in `design/v3/60-listener/frame-spec-notes-301.md`. The format is unchanged.

**Dev key fix (key correction, not a system change).** A blind second Opus labeller relabelled every opus_dev and o0a2 dev turn. Rows where the two disagree on what is scored (the saved facts after the compiler, whether it asks whose, and the ask for ASK turns) are dropped from dev. Act-only differences are kept, because the act is not scored. The result is 394 of 439 kept, and 45 dropped (opus_dev 8, o0a2 37). Of the dropped rows, 22 disagree on saves: 5 are typo keys, several are "X's brother is Oren and he ..." pronoun calls, and several are o0a2 keys that assume facts the turn doesn't state. The ids are in `data/dev_agreed_ids.txt`, and the relabel is in `data/dev_relabel_B.jsonl`. This is the same agreement filter the training rows and panels already pass (key-writing rule 3). The o0b_l2 dev rows are kept.

## Registered test

`artifacts/claude-lispanel301-20260923/` is a fresh 240-turn panel:
- written blind by a separate Opus agent;
- same family counts as panel 300;
- person names N–Z;
- key audited by a second blind Opus labeller, with the key version sealed before the run.

It runs once. Panel 300 is spent and is not reused.

## Marks (same bars as lis-300)

| Mark | Bar |
|---|---|
| P301.1 wrong-save turns | ≤ 1 of 240 |
| P301.2 exact recall of gold writes | ≥ 85% |
| P301.3 ASK turns read correctly | ≥ 90% |
| P301.4 our/we turns that ask whose | ≥ 90% |
| P301.5 unparseable outputs | ≤ 2% of turns |
| P301.6 median read time (GPU) | ≤ 1,500 ms |

Report only:
- T and the dev sweep;
- wrong facts per saved fact and per turn;
- wrong-save turns and recall at T = 0;
- misses by family, at category level only;
- training loss and tok/s.

**Proved wrong if:**
- P301.1 fails (≥ 2 wrong-save turns); or
- P301.2 < 75%; or
- dev still has no zero-wrong T below 0.995.

Any of these means more hard-case data alone does not make the reader safe and useful at once, and the next step is a different mechanism, not more rows.
