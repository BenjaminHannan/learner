# M0 — Notebook demo v0

A notebook on disk that remembers what you teach it, read by the frozen 79,316-parameter
lookup operator. Nothing here was trained. The operator checkpoints are the registered
grow-blind seeds 0, 1 and 2, opened read-only.

## The command

```sh
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27

OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B \
  scripts/fable_notebook_m0.py chat
```

That opens the notebook at `artifacts/fable-notebook-m0-20260920/notebook/` and uses
operator seed 0. Add `--seed 1` or `--seed 2` for the other two frozen checkpoints, or
`--notebook <dir>` for a different notebook. Quit the chat and start it again tomorrow: the
notebook is a file, so it is still there.

## Six lines to type

```
Mira's friend is Oren.
Oren's gift is a drum.
Tal's gift is a kite.
What is Mira's friend's gift?
Actually, Mira's friend is Tal.
What is Mira's friend's gift?
```

Line 4 answers `a drum`; line 6, after the correction, answers `a kite`. That is the point:
nothing was retrained, and no two-hop answer was ever stored. The answer changes because
the chain of lookups is run fresh against the corrected notebook each time you ask.

Also useful inside the chat: `:view` (the rows the operator reads), `:diary` (the whole
append-only history, corrections included), `:names` (which name got which entity token),
`:help`, `:quit`.

Other subcommands: `teach "<sentence>"`, `ask "<question>"`, `wipe` (archives the diary and
starts empty — the wipe test: with nothing to read, it answers nonsense), `vocab`, `eval`.

## The tiny English it understands

It never guesses. Anything outside these shapes gets a plain refusal listing them.

| shape | example |
|---|---|
| a friend fact | `Mira's friend is Oren.` |
| an attribute fact | `Oren's gift is a drum.` |
| a correction | `Actually, Mira's friend is Tal.` (plain re-teaching works too) |
| a person question | `Who is Mira's friend?` … `Who is Mira's friend's friend?` |
| a thing question | `What is Mira's gift?` … `What is Mira's friend's friend's charm?` |

Relations: `friend`, `gift`, `prize`, `charm`. Values: `drum, kite, lamp, rope, coin,
flute, brush, candle, mirror, ladder, kettle, basket, ribbon, feather, pebble, whistle`.
Names: any capitalised word, at most **16 different ones** — that is the operator's hard
limit of 16 entity tokens, not a choice. Chains are capped at 10 steps. The full list is in
`VOCABULARY.json`.

## What this shows / what it does not show

**Supplied code — hand-written by us, not learned by anything:** the loop that reads the
hop sequence off your question and makes one lookup per step; the reader that turns English
into a fact row; the printer that turns the answer token back into English; the correction
rule (latest row per `(subject, relation)` wins); the symbol table that gives each name a
token.

**Learned — the only learned thing in the demo:** the lookup reader. Given a list of fact
rows and a `(person, relation)` pair, produce the object. 79,316 parameters, frozen.

**It shows** that a learned reader can sit behind a persistent, correctable notebook: facts
survive quitting the program, a correction replaces exactly one line and immediately
changes every answer that runs through it, and every answer comes with the exact trace of
lookups that produced it. Measured across 64 scripted teaching sessions per operator seed:
100% one-hop and 100% two-hop at every notebook size from 1 row to 64, on all three seeds
(`RESULTS.md`).

**It does not show** any of the following, and no sentence about this demo should imply
them:

* **No learning of language.** The reader and printer are regular expressions.
* **No "I don't know".** Ask about something you never taught and it will answer, usually
  with high confidence, and be wrong. Measured: mean confidence 0.80–0.92 on untaught
  questions, 46–78% of them above 0.9. That is the baseline failure this demo exists to
  make visible; roadmap M2 is the fix.
* **No new names.** Sixteen people, ever, because the operator has sixteen entity tokens.
  Roadmap M1.
* **No more than 64 facts.** Sixteen people × (one friend + three attributes) is the whole
  vocabulary. Roadmap M3.
* **No learned control.** The program — how many lookups and in what order — is read off
  your question by supplied code. The model never decides how many steps to take or when to
  stop. Roadmap M5.
* **Nothing learned from your teaching.** The weights are frozen and identical before and
  after every session. The knowledge is entirely in the notebook file; wipe it and the
  model knows nothing.

A large pretrained model handed the same diary would beat this at being an assistant, with
free-form English and no 16-name ceiling. This is worth building only as evidence that a
tiny model can learn *how to look things up* — so the numbers in `RESULTS.md` are the
claim, and nothing more.

## Files here

| file | what it is |
|---|---|
| `PREREG-MARKS.md` | the marks, written before `eval` was run; `eval` refuses to start without it |
| `results.json` | every seed, every size, raw counts |
| `RESULTS.md` | the same, as tables |
| `VOCABULARY.json` | the fixed published vocabulary |
| `notebook/` | the notebook `chat` uses by default |
| `eval-notebooks/` | the 64 scripted teaching sessions, as real notebooks on disk |
| `reload/` | the question files and answers of the fresh-process kill-and-reload check |
