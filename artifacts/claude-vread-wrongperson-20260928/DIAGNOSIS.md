# Why the vector reader credits the wrong person on backref facts (read-only diagnosis, helper W, 2026-09-28T18:59Z)

Scope: reading the saved vread files and running CPU counting scripts over them. Dev split only (1,444 turns, 136 of them backref).
No training, no GPU, no model run, no edits to existing files. Nothing here touches the small card experiments or the village model.
Labels: **shown** = counted in the files by a script listed here; **suggested** = fits the counts, not proven; **untested**.
Every number below comes from one of these outputs in this folder (script that made it in brackets):
`repro.json` [claude_vread_wp_repro.py], `table.jsonl` [claude_vread_wp_table.py], `cues.json` [claude_vread_wp_cues.py],
`train_mix.json` [claude_vread_wp_train_mix.py], `summary.json` [claude_vread_wp_summary.py]. Shared loader: `scripts/claude_vread_wp_common.py`.
Re-run order is in the last section. Names in quoted chats are replaced by placeholders.

## 1. Short answer

The wrong-person problem is real but narrow. It only shows up when the prompt names two or more people (shown). The vector reader
then picks a person who does not fit the turn's own clue (a role word like "my mother", or a she/he) in 13 of 13 cases where the
pick is a known person (shown; the fit test is a text heuristic, so the mechanism is suggested). It is not a simple "always the
newest name" rule (shown). It is about 40% of the backref gap at the same bar; the other 60% is low confidence on cards that
point at the right person (shown). The saved files cannot say why the net fails to bind the clue (layer, one round, or too little
contrast practice): that needs a new run (section 6).

## 2. Reproducing "16 against 4" (manager's first ask)

Own script `claude_vread_wp_repro.py`, raw files `run/out/vec_dev_reads.jsonl` and `lora_dev_reads.jsonl`, same definition as
`scripts/claude_vread2_score.py:96-118` (every emitted backref card at any confidence takes the first unused gold card with the
same relation and state; gold owner a name; owner text differs and is not "me"; rival = another person from the dialog's gold
cards with a whole-word copy in the prompt). Output: `repro.json` → `counts`.

| | vector | LoRA |
|---|---|---|
| backref rows / gold cards | 136 / 136 | 136 / 136 |
| matched cards (gold owner a name) | 136 | 135 (in row `...-00966-t7` LoRA wrote no card with the gold relation and state; it is one of the 41 rival rows) |
| right person | 119 | 131 |
| **wrong person, all matched cards** | **17 of 136** | **4 of 135** |
| matched cards with a rival named | 41 | 40 |
| **wrong person, rival named** | **16 of 41** | **2 of 40** |

The bases differ by one card: there are 41 rival rows for both readers, but the denominator is matched cards, and LoRA has no matched card in one of them (40 of 41; 135 of 136 overall). So every LoRA figure is "x of 40" when counted on matched cards and "x of 41" only when counted on rows (section 4.1).

- **Does my count match?** The 16 matches (shown): vector 16 of 41 with a rival named. It also matches
  `artifacts/claude-vread2-20260928/PASSMARKS.md:118`.
- **The 4 does not match on the same basis.** It only appears as LoRA's count over ALL matched cards (4 of 135). On the same
  rival-named basis as the 16, LoRA has 2 of 40. So "16 against 4" mixes two bases. Like for like: 16 vs 2 (rival named) or 17 vs 4 (all).
- The 17th vector card (no rival named) is a span error, not a wrong person: the owner text is
  "<NAME> works for <FIRM>.\nAssistant: Is <NAME>", i.e. start and end pointers on two different copies of the right name
  (`table.jsonl`, id `...-01596-t6`). So the true wrong-person count for the vector reader is 16 of 136 (shown), all in rival prompts.
- Caveat: no tokenizer is on this machine, so "copies" are text matches without the vread2 "tokens decode exactly" test.
  The right-owner-by-copies counts still equal the ones in PASSMARKS.md:114-116 (8 of 49, 11 of 40, 19 of 30; `summary.json` → `vector_right_owner_below_0.97_by_copies`),
  so the difference is nil for these rows. A rival name that is in no kept gold card is invisible to this count (see 4.6).

## 3. What the saved reads hold (manager's second ask)

The dev reads do NOT hold the 7 per-card probabilities. Each vector card has only
`conf, owner, owner_tokens, rel, state, value, value_tokens` (1,497 of 1,497 cards; `summary.json` → `vector_reads_format`).
`claude_vread_model.py:150-165` decode() computes the 7 and keeps only their minimum as `conf` (line 163), and `read_rows` (line 330) writes only `conf`.
The LoRA reads hold one probability per fact, also a minimum (`summary.json` → `lora_reads_format`; `scripts/claude_vread_score.py:lora_cards`).
- What can still be inferred: a card's `conf` is the minimum of all 7, so `conf ≥ 0.97` means the owner-start probability (the only
  one that can choose the person) was ≥ 0.97. That was so for 4 of the 17 wrong-person cards (shown, `summary.json` →
  `vector_wrong_picks.conf_at_or_above_0.97`). Nothing more.
- What is missing: which of the 7 was lowest on the wrong-person cards. vread2's fresh-set reads do carry `p7`
  (`scripts/claude_vread2_score.py:34,110,128`), but they are the fresh split, not dev, so I did not open them.
- Aggregate answer that already exists (fresh split, right-person backref cards below 0.97, `claude-vread2-20260928/RESULTS.md:66-68`):
  owner start or end is the lowest on 104 of 114 (A-s327) and 72 of 88 (A-s331); owner end alone 72 and 49. That is about the
  right-person low-confidence problem, not the wrong-person one.
- To get it for wrong-person cards on dev (not done): read dev once with vread2's `run/ckpt/A-s327.pt` (same recipe as vread; the
  vread checkpoint itself was never copied back, `claude-vread-20260927/RESULTS.md:118`) with `p7` written out. Needs the 1B model
  and a torch install; neither is on this machine. Alternatively, tabulate the wrong-person cards in the existing vread2 fresh reads
  (`p7` present, no model needed): a manager decision, since it is not dev.

## 4. Evidence on each candidate

### 4.1 Where the errors are (shown)
`summary.json` → `vector_by_n_persons`, `vector_by_gold_rank_when_2plus`, `lora_*`.
- Prompt names one person: vector wrong in 1 of 95 (that one is the span error above); LoRA 2 of 95.
- Two or more people named (41 rows): vector wrong in 16 of 41; LoRA wrong in 2 of 40 matched cards (the 41st row has no LoRA card, section 2), right in 38.
- Of those 41: the gold owner is the newest person in 22, not the newest in 19.
  - Vector: gold newest → 6 wrong of 22; gold not newest → 10 wrong of 19.
  - LoRA: gold newest → 0 wrong of 22 (1 no card); gold not newest → 2 wrong of 19.
- Outside backref the vector reader also names the wrong person, but rarely: 8 cards (teach 3, correct 2, correct_ref 2, former 1);
  LoRA 2 (both teach). `summary.json` → `wrong_person_all_families_matched_cards`.

### 4.2 "Does it always pick the nearest or newest name?" No (shown)
- Of the 16 wrong picks in rival prompts, 13 are names of other people in the dialog's gold cards (the other 3 are not a known person: a pet name, a fragment `Ul` of a
  name in the turn, and `Fiha`, a name that appears in no kept gold card; the 17th vector wrong card is the span error). Of those 13: 8 are more recent than the gold owner, 5 older; 7 are
  the newest person in the prompt (`summary.json` → `vector_wrong_picks`).
- 6 of the 22 rival rows where the gold owner IS the newest person are still wrong (section 4.1).
- An "always pick the newest person" rule would be right in 22 of the 41 rival rows (and 117 of all 136 backref rows,
  `summary.json` → `always_newest_person_rule_right_in*`). Vector is right in 25 of 41, LoRA in 38 of 41.
- Suggested: a recency pull exists (10 of 19 wrong when the gold owner is not newest, against 6 of 22 when it is), and it is
  partly there in fresh data too (vread2: 23 of 40 wrong owners start after the gold name's newest copy for A-s327,
  `claude-vread2-20260928/RESULTS.md:62`). But it does not explain all of it.

### 4.3 Does the pick fit the turn's clue? Mostly no (shown for counts, suggested for meaning)
Heuristic in `claude_vread_wp_cues.py` (role words and he/she marks read from the earlier lines that name a person). `summary.json` →
`vector_wrong_picks.role_cue_wrong_picks`, `pronoun_cue_wrong_picks`, `cues.json`.
- 79 of 136 backref turns give a role word ("my mother has a rabbit"), 57 give a pronoun. Wrong picks by clue: role 9, pronoun 8.
- Role rows: of 9 wrong picks, 6 are a known person introduced with another role, 3 are not a known person; 0 of 9 has the turn's role.
- Pronoun rows: of 8 wrong picks, 7 are a known person marked with the other gender, 1 is not a known person.
- Example (placeholders; `...-00384-t8`): earlier lines say "my friend is <F>, she lives in ..." and "my mother is <M>, and her favourite
  foods are ..."; the turn is "my mother has a rabbit called <PET>". Vector answers owner <F> (confidence 0.09); LoRA answers <M> (0.995).
- Example (`...-00466-t4`): "my best friend is <A> and he plays drums", "my boss is <B>", "<C> is my father and he's 55";
  turn "she has a rabbit named <PET>". Gold <B>. Vector answers <A> (0.09), LoRA answers <C> (0.30). Both fail; the clue "she"
  excludes both picks.
- LoRA's 4 wrong-person cards: 2 clash with the pronoun's gender, 2 are names not in the dialog's gold cards
  (`cues.json` → `summary.lora_wrong_picks`, `table.jsonl`). Its confidence on all 4 is below 0.9, so it saved none.
- Suggested: the vector reader is not binding the turn's role word or pronoun to the line that introduced the person, when a
  second person competes.

### 4.4 Is the gold label ambiguous? Almost never (shown by heuristic, suggested)
- Role rows: the gold owner is introduced with the turn's role in 79 of 79 role rows.
- Rows where another named person also fits the turn's clue (same role, or gender not excluded by a mark): 1 of 136
  (id `...-00390-t8`, an unmarked rival, both readers right). `summary.json` → `rows_where_another_person_also_fits_the_turn_cue`.
- The "ambiguous_pronoun" look-alike family is separate by design (gold has no fact) and is not in these rows.
- Limit: the heuristic reads roles and he/she in the text; a person with no mark counts as fitting. I read 6 of the 17 wrong-person
  chats by eye and found none where a human could not tell who was meant.
- Conclusion: the label is not the cause.

### 4.5 Position offsets clipped at ±4 (shown in code; effect untested)
- Code: `claude_vread_model.py:76-84` builds token-to-token column offsets with `.clamp(-R.CLIP, R.CLIP)` and `R.CLIP = 4`
  (`claude_rsn358a_run.py:39`). Any two tokens more than 4 apart share the same attention bias, and the thinker has no other
  position input (`VReader.prepare`, `claude_vread_model.py:100-110`: the adapter is LayerNorm + Linear on the 1B vector only). So the
  thinker cannot read "how far back" from its own bias; whatever recency it uses must come from the 1B's vectors.
- Data: the error does not grow cleanly with distance. In the 41 rival rows, user-lines back to the owner (1..5): vector wrong 7 of
  17, 1 of 8, 3 of 7, 3 of 5, 2 of 4; median words back 38 for wrong vs 30 for right (`summary.json` →
  `user_lines_back_2plus_persons_vector`, `words_back_2plus_persons`). n is too small to call a trend. Distance and "gold not newest" are also tangled.
- Verdict: not supported as the main cause (suggested); not ruled out (untested).

### 4.6 What the LoRA reader does on the same cards (shown)
- On the 17 cards where the vector reader is wrong, LoRA is right on 15 and wrong on 2 (ids `...-00466-t4` and `...-01463-t7`, which both
  readers get wrong). On LoRA's 4 wrong cards, the vector reader is right on 2 and wrong on 2. (`summary.json` → `lora_on_the_vector_wrong_cards`, `vector_on_the_lora_wrong_cards`.)
- Confident wrong: 4 of the vector's 17 wrong cards had conf ≥ 0.97 (0.972, 0.990, 0.994, 0.998), which is where the 4 backref wrong
  saves come from. 13 had conf under 0.97 and were dropped. LoRA's wrong cards were all under 0.9.
- Limit of the count: "person" and "rival" mean names in the kept gold cards of the dialog. A name in a dropped row is unseen, so
  rival counts are a floor (the vector's `Fiha` and LoRA's `Kabraine` and `Holo` are probably such names).

### 4.7 How much of the backref gap is wrong-person? (shown)
`summary.json` → `gap_decomposition_hist_rule` (history rule, 136 gold cards; these reproduce RESULTS: 81, 88, 63, 112).

| card outcome | vector 0.97 | LoRA 0.995 | vector 0.995 | LoRA 0.97 |
|---|---|---|---|---|
| right person, saved right | 81 | 88 | 63 | 112 |
| right person, confidence below bar | 38 | 43 | 56 | 19 |
| wrong person, saved (wrong save) | 4 | 0 | 1 | 0 |
| wrong person, not saved | 13 | 4 | 16 | 4 |
| no card | 0 | 1 | 0 | 1 |

- At the same bar 0.97 the gap is 31 cards (81 vs 112): wrong person 13 more, low confidence on the right person 19 more, LoRA's one missing card -1.
  So wrong person is about 13 of 31 (42%); low confidence (Astra's problem 1) is 19 of 31.
- At each arm's own bar the gap is 7 cards: wrong person costs the vector 13 more, its lower confidence bar wins back 5, LoRA's no-card 1.
- vread2's fix for the low-confidence part was INCONCLUSIVE (`claude-vread2-20260928/RESULTS.md:3`). Its report-only wrong-person counts
  did not move much: 35 vs 28 of 135 and 29 vs 21 of 135 with a rival named (`RESULTS.md:61`).

### 4.8 Practice (shown counts, effect untested)
`train_mix.json` (gold labels only; person and newest defined as above).
- Vector arm's train: 880 backref cards, 260 with a rival named, 124 of those with the owner NOT the newest person. Dev: 136, 41, 19.
  LoRA also trained on the 108-card calibration slice (33 rival, 17 not newest).
- The vector net fit train perfectly: loss 0.0027, every batch fully right on the last step
  (`claude-vread-20260927/run/out/vec_train.log`, last two lines; RESULTS.md:75). Yet dev is wrong in 10 of 19 not-newest rival rows.
  Suggested: with ~12 passes over 124 examples the net can reach zero loss by memorising, without learning a clue-binding rule.
  LoRA trained on nearly the same rows for 2 epochs and generalises (17 of 19), so row count alone is not the difference (suggested).

## 5. Ranked causes

| # | Cause | Label | Evidence |
|---|---|---|---|
| 1 | The reader does not bind the turn's clue (role word or he/she) to the right introduction when a second person is named | pattern **shown**, mechanism **suggested** | 16 of 41 vs 1 of 95 (4.1); 13 known-person picks all contradict the clue (4.3); gold unambiguous in 135 of 136 (4.4); LoRA right on 15 of the 17 (4.6) |
| 2 | What the frozen layer 12 plus a 2-block, 1-round reader can represent (Astra's causes 1 and 2) | **untested** | Saved files have layer 12 only, one round on every turn (`RESULTS.md:55`, dev reads: `rounds` = 1 on 1,444 of 1,444, `summary.json` → `vector_reads_format.rounds`), and per-layer totals over all families only (`run/out/vec/layers.json`, 800 steps, not 4,000: `claude_vread_model.py:57`). Cannot split it from #3 |
| 3 | Too little contrast practice, memorised (Astra's cause 3) | **suggested** | 260 rival train cards, 124 owner-not-newest; train loss 0.0027 (4.8) |
| 4 | A recency pull toward the newest person | **shown** but partial | 8 of 13 person picks more recent; 6 of 22 wrong even when gold is newest (4.2) |
| 5 | Pointer slips: owner is not a known person or is a span over two copies (a pet name, the fragment "Ul", "Fiha", the two-copy span) | **shown**, small | 4 of 17 vector cards (4.2); the two-copy span overlaps with Astra's problem 1 |
| 6 | Position offsets clipped at ±4 | code **shown**, effect **untested**, not supported as main | 4.5 |
| 7 | Gold label ambiguity | not supported | 1 of 136 (4.4) |
| - | Seed noise (Astra's cause 5) | **untested** on dev | one seed each; on fresh data A's two seeds differ by 6 of ~135 rival cards (35 vs 29, `RESULTS.md:61`), far smaller than 16 vs 2 |

What the saved files cannot tell: which of causes 2 and 3 matters; which of the 7 probabilities is lowest on the wrong cards;
whether a deeper layer or a forced second round would fix it; whether a rival name absent from the kept gold cards is hiding in
the "1 person" rows.

## 6. One proposed fix (one change, pass marks fixed in advance)

**Why the data change and not layer 18 (manager's question).** Two candidate single tests: (a) read the 1B at layer 18 (tests cause 2),
(b) add contrast practice, data only (tests cause 3, which sits next to my top cause 1).
- Evidence that layer 18 carries more coreference than layer 12: **none in the repo (untested)**. The only layer evidence is the
  all-family calibration at 800 steps, where layer 12 beat layer 18 (1,010 vs 810; `claude-vread-20260927/RESULTS.md:66-70`,
  `run/out/vec/layers.json`), and it has no per-family split. My earlier "coreference sits in the middle to upper layers" was general
  knowledge, not a repo finding.
- Does the 1B have layer 18? Yes, at least: layers 6, 12, 18 and 24 were all read and trained on in the vread run (`layers.json` keys;
  `run/out/vec_layers.log`), so hidden state 18 exists. The total depth of MiniCPM5-1B is not stated in any file in the repo
  (no config, no `num_hidden_layers`); I did not check it elsewhere.
- Layer 18 is a guess with no support; (b) has counts behind it (260 rival train cards, 124 with the owner not newest, train loss 0.0027;
  section 4.8), needs no architecture change, keeps layer 12, and if it fails the named next step is layer 18. So (b) goes first.
- An honest limit of (b): the dose is small (about +52% rival cards) and the training loss is already near zero, so a fail says
  "this much extra practice is not enough", not "practice is not the cause".

**Change: add the fresh Luna rows of chunks 11-13 to the vector reader's training rows. Nothing else changes.** Train rows
11,217 + 6,483 = 17,700 (vread2 data pack, `claude-vread2-20260928/data`), same layer 12, same 4,000 steps at batch 32 (so fewer passes
per row: about 7 instead of 11; this comes with the change and is disclosed), seeds 327 and 331, same calibration slice (kept out
of training) and same rule for the save bar, same scorer. Extra rival-named backref cards: about 135 (vread2 `scores/A-s327.json`
→ `owner_bins.rival_named:matched` = 135), so 260 → about 395 (**suggested** count; the owner-not-newest share of the new ones is
not counted, since I stayed off the fresh split).

**Control and test set.** Control A = the vread2 A checkpoints (`run/ckpt/A-s327.pt`, `A-s331.pt`; the vread recipe), read on dev with
the same scorer. B = the new checkpoints, read on dev. Dev is the only split with a clean rival-named count (41 cards, vread 16 of 41), and it
has been used only for vread's sealed marks and this diagnosis, never to choose a setting. If lis-320 chunks 14+ land with about 2,900
rows (60 rival cards at the fresh rate of 135 per 6,483 rows), use them instead and read A there too. Each checkpoint is read once.

Pass marks (each seed, B against A of the same seed; written before any training):
- Validity: A's rival-named wrong-person count on the test set ≥ 12 of 41 in both seeds (vread got 16). Otherwise INCONCLUSIVE.
- P1, target: B's rival-named wrong-person count ≤ 0.6 × A's, rounded down (A = 16 gives ≤ 9), in both seeds.
- P2: B's backref right saves at 0.97, history rule ≥ A + 10 in both seeds (vread: 81).
- P3, guards: B's wrong turns on the whole test set at its own bar ≤ A + 2; B's main-rule right saves ≥ 0.95 × A.
- PASS = validity, P1, P2, P3 in both seeds.
- **Result that proves it wrong:** in both seeds B's rival-named wrong-person count is within 3 of A's (≥ A − 3). Then this much extra
  practice does not fix binding. Named next step, not part of this test: layer 18 (cause 2), or a forced second round.
- Anything else is FAIL with the reason reported. Seed spread on dev is unknown (on fresh data A's two seeds differ by 6 of ~135), so
  a pass in one seed only is a FAIL.
- Cost, suggested: like vread2's paired run (about 40 minutes on one RTX 4090) plus dev reads; the manager decides on a rental.
  Keep the result separate from the small card experiments and the village model.

## 7. For Ben (6 lines)
1. The number "16 against 4" mixes two ways of counting. Counted the same way it is 16 of 41 for the small reader against 2 of 40 for the normal reader.
2. Almost all the mix-ups happen when two people were named earlier; with only one person named, the small reader gets it right in 94 of 95 cases.
3. It does not just pick the last name it saw: it also picks the wrong person when the right person was the newest, and it often picks someone the words rule out (a "she" who was called "he", a "my mother" who was a friend).
4. The question was never confusing: only 1 of 136 questions had a second person who could also fit the clue.
5. Of the 31 backref saves the small reader loses to the normal reader at the same confidence bar, 13 are wrong-person cards and 19 are the reader being unsure about the right person.
6. The saved files cannot say why. My one proposed test: give the small reader more practice on rival cases (add the fresh chats to its training), with pass marks fixed beforehand and a result that would show it is not enough. Reading a deeper layer (18) is the named next step, because nothing in the repo says layer 18 is better than 12.

## 8. Re-running (all CPU, single thread, about a minute each)
```
D=artifacts/claude-vread-wrongperson-20260928
python -B scripts/claude_vread_wp_repro.py --out $D/repro.json
python -B scripts/claude_vread_wp_table.py --out $D/table.jsonl
python -B scripts/claude_vread_wp_cues.py --table $D/table.jsonl --out $D/cues.json
python -B scripts/claude_vread_wp_train_mix.py --out $D/train_mix.json
python -B scripts/claude_vread_wp_summary.py --dir $D
```
