# Exp 281b — RESULTS: FAIL (M1 stored bar 9/25; every other bar passes)

Registered runs on 2026-09-23 with the sealed agent/config (17/17 seal OK before and after; panel seal OK;
each arm run exactly once per step; the panel folder was never read item by item and no item text is quoted
here). Panel: 60 turns / 10 dialogs, split 10 teach_setup + 25 stored_called + 10 nostore_called + 10
ambiguous_called + 5 control_plain, exactly the brief's spec. Raw rows: `run/panel-281.json`,
`run/panel-281b.json`; score: `run/panel-score281b.json`, `run/panel-score.txt`. M2/probes figures are the
registered `run/regscore.txt` (VERDICT PASS).

## M1 — blind calledpanel281b, 281's number next to every figure

| bar | 281b | 281 | verdict |
|---|---|---|---|
| stored ≥ 90% exact over denominator (≥ 23/25) | 9/25 | 9/25 | FAIL |
| stored wrong answers (over denominator) | 0 | 0 | PASS |
| notstored abstain (0 guesses) | 10/10 | 10/10 | PASS |
| ambiguous same as 281 (0 moves) | 10/10 | — | PASS |
| control same as 281 (0 moves) | 5/5 | — | PASS |
| teach gold triple stored (panel-validity bar: at most 2 fail) | 10/10 | 10/10 | panel VALID |
| M3 store diffs 281b vs 281 (all 60 turns) | 0 | — | PASS |
| M3 question writes on 281b | 0 | 0 | PASS |

Denominator: 25/25 stored rows sit in dialogs whose teach triple is stored on the 281 arm (0 excluded), so the
note's ≥ 90% bar is ≥ 23/25. Control right 5/5 on both arms. Teach stores and teach write counts identical
281b vs 281 on all 10 teach rows.

## Every move vs 281 on the panel (none) and every miss (16, all abstain, 0 wrong)

- Stored moves 281→281b: none (25/25 stored replies byte-identical; the 9 right ids are the same 9 on both
  arms, so 0 flips toward an abstain anywhere and no 5× single-item follow-ups were needed).
- Stored right on 281b (9): d01#2, d02#1, d03#2, d04#1, d05#3, d06#1, d07#2, d09#2, d10#1 — all formal
  called/nameof wordings with "?" that 281 already rewrites.
- Stored miss on 281b (16, all abstain, 0 wrong): d01#1, d01#3, d02#2, d02#3, d03#1, d03#3, d04#2, d04#3,
  d05#1, d05#2, d06#2, d07#1, d08#1, d08#2, d09#1, d10#2.
- Miss shape categories (mechanical features only, no text read): 5 misses are 2-token no-apostrophe relation
  phrases whose subject restores to a known entity and whose formalisation 281's matcher accepts, yet the head
  does not answer — the formalised relation phrase does not resolve to the stored triple (a wording difference
  beyond casual typing, e.g. a different relation word than the teach turn used). 11 misses match no called
  shape at all even generously (2 carry no called/named/name-of cue whatever; the rest keep a cue word but in
  wordings outside the four sealed shapes, e.g. embedded clauses rather than a trailing called/named). In
  short: none of the panel's 16 missed stored items is a briefed-dimension casual typing (letter case,
  apostrophe, whats/what's/what-is, missing ?) of a sealed-shape question over the taught fact — every such
  shape works (dev 34/34 stored, mock panel, and the 9 formal panel items).
- 281 itself scores 9/25 on this panel (vs 16/25 on its own burned panel), consistent with harder wordings.

## M2 + probes (registered `run/regscore.txt`, PASS, exactly as predicted in P281b.2)

- sessions152 (180 units): 0 moved. bench 4×200: 0 moved. GATE clean.
- rt136 (145 units): 0 field diffs vs 281's rows (vs-138j labels identical to 281's; the NOT-clean gate string
  is the same 13 inherited 222 WRONG-WRITE + 1 junk as on 281).
- rt143_nogate (124 rows): 0 moved.
- verifier probes: vp 98 rows 0 changes, supp 12 rows 0 changes vs 281's rows.

## Report-only: broken "don't know X's R called/named." abstains

- 281b: 0 turns; 281: 0 turns. (This panel's misses abstain with other wordings, not the broken template.)

## Deviations

None after the seal. The 17-file seal re-verified 17/17 OK after all registered runs. Each registered command
ran once per arm (runall into `run/`, panel into `run/`); no driver was added or fixed after the seal (the
panel runner/scorer with the schema gate and the `user`-key acceptance were sealed before it, after a mock
end-to-end). Ledger P281b.1–P281b.3 appended before the registered runs, P281b.4 after. No commits or pushes
(the rules forbid them); all deliverables are in place in the worktree.

## What it means (plain high-school English)

- Casual typing of the exact questions 281 was built for now works: lowercase, missing apostrophes, "whats",
  and missing question marks are all read as the formal question (proven on 56 home-made dialogs and the mock
  panel). Nothing else changed: no new guesses, no new writes, frozen suites and probes byte-identical to 281.
- The blind panel still fails the 90% bar because its missed questions are not typed-casually versions of the
  covered questions — they reword the question itself (different relation words, embedded clauses, cue-less
  forms). That is a different job than this experiment's one change.

## What it doesn't mean

- It does not mean 281b is worse than 281 anywhere: on the panel every figure is equal-or-better (9/9 shared
  right answers, 0 wrong, 0 moves on ambiguous/control, 0 store diffs), and 281b fixed nothing it broke nothing.
- It does not mean casual typing is solved in general: multi-word no-apostrophe subjects, pronouns, and
  embedded clauses ("tell me what ... is called") are still out of scope by design.
- It does not mean the stores are unsafe: question turns wrote nothing on either arm on any of the 60 turns.
