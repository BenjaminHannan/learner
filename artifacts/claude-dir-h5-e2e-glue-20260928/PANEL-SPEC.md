# H5: panel spec for the first joined test (e2e-1), code-made panel generator, Luna wording spec

Helper H5, 2026-09-28T19:31Z (`date -u`). No model was run and no GPU was used (this box has no torch). Marks come from H4's
`artifacts/claude-dir-h4-e2e-20260928/PASSMARKS.md` and are not changed here. Labels: **shown** = I ran it or read it in a file (path
given), **suggested** = fits the evidence, **untested** = nobody has run it. The small card experiments and the village model are out.
**I did not generate, open or read the sealed panel.** The generator has a sealed mode; only the Director runs it.

## 1. What is built (all shown by selftests in section 6)

| File | What it is |
|---|---|
| `scripts/claude_dir_h5_panel.py` | code-made panel generator (facts, names, puzzles, layouts, gold answers), the wording-job maker, the wording validator, the merge step |
| `artifacts/claude-dir-h5-e2e-glue-20260928/dev-sample/` | a 6-life DEV rehearsal sample the generator made (dev seed 585103). Its text is a code key=value dump ("[DEV-PLUMBING] ..."), not chat. It is never a panel. |
| `artifacts/claude-dir-h5-e2e-glue-20260928/dev-sample/rehearsal-mock/` | mock-model arm outputs on that sample plus the scorer in rehearsal mode (plumbing only) |

## 2. What the code makes, and what only Luna/GLM writes

Made by code (and never touched by wording): every fictional name, place, organisation and school; every fact and its owner,
relation and value; corrections; which turn an owner is first named in; the pronoun of each person; every number square (a unique-solution
puzzle with its solution), the broken square (a clue copied into a blank of its own row, so no answer exists), the square lookalike, the
number lookalikes (a table whose rows are not equal to its columns, a labelled list, a comma list); the layout of each grid block; the gold
answer of every ask; the order of turns; the halves; the counts.

Written by Luna (or GLM), from code seeds, in slots: the sentence around each fact, correction, ask and small-talk turn, and the optional
lead-in and the request sentence around each grid/table block. **The block itself is inserted by code**, so the wording can never edit,
reflow or leak a grid. No slot is written by Claude, and this file contains no example of chat wording on purpose.

Names are drawn from syllables (`Words` in the generator): 5 to 9 letters, unique inside a life, first letters of persons differ inside a
life, none on `artifacts/claude-lis320-20260926/avoid_names_dev.txt`, none in `/usr/share/dict/words` if this box has it. Places end in a
fixed suffix from a short list; organisations and schools get a fixed suffix word.
(Note: for the sealed run the lis-320 test avoid list exists only as a hash, `avoid_test.sha256`. See open question Q4.)

## 3. Panel structure (equals H4's table, shown by the full-size dev build: 60 lives, 324 turns)

| Item | Pooled | Per half | How the generator makes it |
|---|---|---|---|
| solve squares 5x5 / 6x6 / 7x7 | 20 / 20 / 10 | 10 / 10 / 5 | unique-solution Latin puzzle; every symbol shows at least once; blanks written `_` |
| broken squares | 12 | 6 | a valid puzzle, then one clue copied into a blank of its row |
| square lookalikes | 12 | 6 | a valid square is present; the ask is one of `title, count_blanks, most_clues_row, comment` |
| number lookalikes | 20 | 10 | table (rows != columns) / labelled list / comma list; ask is `sum, largest, count_items` (code gold) |
| answerable asks | 60 = 30 plain + 15 corrected + 15 backref | 30 | exactly one per life (see below) |
| never-told asks | 30 | 15 | relation never told for that owner anywhere in the life (checked by selftest) |
| small talk | 40 | 20 | topic word only |

The corrected and backref counts are 8+7 and 7+8 over the two halves (15 cannot split evenly); PASSMARKS' "differing by more than 2" rule allows it.
Answerable ask forms: **plain** = one fact turn, then the ask, owner either the user ("my ...") or a named person told in the same turn;
**corrected** = fact, later a CORRECT turn with a new value (the old value is forbidden in the correcting wording and in the ask, so a stale
mention in a reply is clean evidence); **backref** = a turn that names a person and their link to the user, then a later turn that speaks of that
person only by pronoun, then an ask that uses the name. **Never-told** = the ask names a relation nobody told (either for the user, or for a
named person who was introduced but whose relation was not told).
Every life holds one answerable ask; the other items are dealt over the lives round-robin from a shuffled list, so lives run 4 to 8 turns in the dev build (4: 5 lives, 5: 32, 6: 18, 7: 4, 8: 1) and the two halves stay balanced (selftest: no item differs between halves by more than 2).

**Layouts** (shown in the dev build: 38 held-out vs 36 seen among 74 squares). Seen = gr-1's eight practice layouts drawn by this file's own
renderer (`row, bare, pipe, comma, md, latex, label, colhead`). Held-out = a separator mark taken from gr-9's TEST set (`claude_gr9.split_seps()[2]`:
`§ $ £ % ¶ ! !! ' " ` ''`, marks gr-9 neither trained nor developed on) plus three I added (`¡ ‖ ⁂`), used as ` mark `, `mark ` or `mark` between cells.
Half of the squares (rounded) get each class and the class is logged in the truth file (`layout_class`). Caveat (**untested**): "seen" means
seen by gr-1 by name; I did not diff my renderer's output against gr-6/7's rendered training text, so a "seen" layout may look a little different
from what was trained on, and a "held" mark may sit near a mark gr-6 used. The label is a design intent, not a measured fact.

## 4. Files a run makes, and who may open them

| File | Holds | Who opens it |
|---|---|---|
| `turns.jsonl` | `{id, life_id, half, turn_no, text}` only (selftest: no other key) | runners |
| `answers.jsonl` | truth: item type, owner, relation, gold, old value, puzzle, solution, layout, ask kind, blank counts | the scorer only (the "truth file no runner opens") |
| `skeleton.json` | turn skeletons with facts and blocks (so it carries truth too) | the merge step; Director keeps it with the truth |
| `wording_jobs.jsonl` | one line per life for Luna/GLM (section 5) | Luna/GLM |
| `panel_counts.json`, `SHA256.txt` | counts, layout split, held-mark source, sha256 of the files | everyone |

Sealed mode writes `answers.jsonl` to `--truth-dir` and sets modes 0600 on it and on the skeleton; it writes NO `turns.jsonl` (no wording
exists yet) and it refuses the dev seeds. Dev mode fills the slots with the plumbing dump.

## 5. The exact generator prompt-spec for Luna (or GLM) (the wording jobs)

One call per half, and inside a half one call per life or a few lives at a time (Director's choice; PASSMARKS wants the two halves in separate calls).
The Director sends the text below, with `<JOB>` replaced by one line of `wording_jobs.jsonl`. **Send nothing from `answers.jsonl` or `skeleton.json`.**
(The job already lists what the wording must carry, and, for asks, the values it must not reveal.)

```
You write single chat messages that an imaginary person types to a personal-assistant chatbot. The messages become a test set, so they must read like real
typed chat. You get one JSON job for one person's conversation. Each entry of "slots" is one message (or one part of a message) to write. Answer with ONLY
this JSON and nothing else:
{"life_id": "<same as the job>", "slots": {"<slot_id>": "<text>", ...}}
Rules, all checked by a program that rejects the whole answer if one is broken:
1. Every slot_id of the job appears exactly once. A slot whose contract has "optional": true may be the empty string.
2. Each text is a single line (no line breaks), at most 300 characters, and contains no digit (0-9) and no emoji.
3. Every string in a slot's "must_include" appears in the text spelled exactly as given, as whole words. No string in "must_not_include" appears in the text at all.
4. No text may use any word listed in the job's "avoid_strings" unless that same word is in that slot's must_include.
5. kind "fact": the person tells the assistant the fact(s) in "facts" (owner, rel, value). owner "USER" means the fact is about the person's own life
   (speak in the first person); another owner is that named third person. "rel" is the kind of link or attribute, and how to put it in words is up to you. Vary the phrasing between slots.
   owner_ref "me": the person speaks about themself. owner_ref "named": the text uses the owner's name. owner_ref "pronoun": the text refers to that person ONLY with the
   given "pronoun" (they/she/he) and never by name. mode "CORRECT": the person fixes something they said earlier about the same thing, and the text makes clear that
   the new value replaces the old one; do not write the old value. When "pronoun" is given for an owner_ref "named" slot, that is the pronoun to use if the person is referred to again.
6. kind "ask": the person asks the assistant to recall the value of "rel" for "owner" (owner "USER" = the person themself). Never write the answer.
7. kind "smalltalk": one casual message about the given "topic"; it names nobody, and asks nothing that depends on earlier messages.
8. kind "square" or "numbers": two slots, "lead" and "ask". A block of numbers (a grid, table or list; blank cells are written "_") is added by a program. The
   "lead" goes before it (it may be empty), the "ask" is the request about it. "ask_kind" says the request: solve = fill in the blank cells; title = suggest a title for it;
   count_blanks = how many blank cells it has; most_clues_row = which row has the most filled cells; comment = a passing remark or a question about it that needs no calculation;
   sum = the total of the numbers; largest = the biggest number; count_items = how many numbers there are. "order" says where the block sits: "lead-block-ask" = lead, then the block, then the ask;
   "ask-block" = the ask comes first and the block follows it (the lead is then not used and must be empty). Do not describe the block's contents or write any number.
9. Do not mention tests, panels, prompts or that you are an AI. Use ordinary informal chat: varied length, varied openings, occasional lower case. Nothing in one slot may depend on words
   that only appear in another slot of the same job except through the facts listed.
JOB: <JOB>
```

**What the code checks on the answer** (`validate_wording`, shown by selftest for digits and missing slots; the other checks are the same code path and
are **untested on real Luna output**): every slot present; no line breaks; no digit; at most 400 characters; `must_include` present as whole words; `must_not_include`
absent; no life word in small talk or in a lead; no unknown slot. A rejected answer is written to `wording_problems.json` and nothing is merged. Whether the wording
"reads natural" cannot be checked by code: that is the V5 check below.

**V5 blind wording check (separate call, run by the Director after merge).** The checker is shown, per life, the assembled `turns.jsonl` texts only (never a truth file,
never any model output) and asked for JSON: `{"life_id":..,"natural":[true/false per turn],"leaks_answer_in_question":true/false}`. The checker's instruction is a fixed
text the Director owns (the PASSMARKS bars are 95% natural and at most 3 of 60 lives leaking). I did not write that instruction, so that no Claude-worded text touches the
panel path.

**Director steps, in order** (none done by me): (1) make a seeds file outside the repo, `{"h1": <fresh int>, "h2": <fresh int>}`; (2) `python -B scripts/claude_dir_h5_panel.py make --mode sealed --seeds-file S.json --out PANELDIR --truth-dir TRUTHDIR`;
(3) run the two halves through Luna in separate calls, one `wording.jsonl` line per life; (4) `python -B scripts/claude_dir_h5_panel.py merge --skeleton PANELDIR/skeleton.json --wording wording.jsonl --out PANELDIR --truth-dir TRUTHDIR`;
(5) V5 check; (6) `sha256sum` `turns.jsonl` and `TRUTHDIR/answers.jsonl` into the seal file before the first arm runs.

## 6. Selftest (rerun with the command here)

`python -B scripts/claude_dir_h5_panel.py selftest`: 31 of 31 checks pass. They cover: unique-solution puzzles at 5, 6, 7; broken squares have no solution; the full-size build equals
H4's count table (20/20/10/12/12/20/30/15/15/30/40); 60 lives; turn rows carry no truth key; turn ids match truth ids; each item within 2 between halves; half the squares held-out;
dev asks never contain their gold; never-told relations are told nowhere for that owner; the hand parser reads back the row/bare/comma/pipe layouts exactly (md also reads; latex, label, colhead and mark layouts do not) (grid equal to the truth puzzle);
no name on the avoid list; the 6-life sample; determinism; sealed mode refuses the dev seeds; the validator flags digits, missing slots and a life word used where it may not be.

## 7. Honest limits

1. The dev sample's text is not chat. It exercises wiring only, and the real reader (lis-320) would read it badly. Do not score a real model on it.
2. The wording contract asks Luna to obey `must_include` etc. Real Luna output has not been tried here (the Director's Codex path had no probe result I could see). Expect some rejections; the merge step tells which.
3. Only Latin squares in chat exist in the panel, as in H4's plan. Sums and word questions are out.
4. Backref facts speak of a person by pronoun only. The current reader gate (`claude_lis300_compiler.check_fact`) refuses pronoun owners (shown, `GLUE.md` section 5), so E6c is the mark at most risk from the reader, not the talker.
