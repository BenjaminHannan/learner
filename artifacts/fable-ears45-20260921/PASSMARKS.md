# PASSMARKS — Rung 1 of `design/v3/30-modes/43-talker-ears-mouth-design-fable.md`

Written and hashed **before any registered training run**. Everything below is fixed in
advance. Nothing on a test panel may guide any choice; only DEV and CAL may.

Date: 2026-09-21 · artifacts dir: `artifacts/fable-ears45-20260921/`

---

## 1. The marks, copied from section F of the design

House rules (section F, verbatim): *"marks below are copied into a `PASSMARKS.md`, hashed,
and the hash committed before any gated panel is scored; every seed is printed; counts are
integers; a rung's PASS needs 3 of 3 seeds; 2 of 3 is PARTIAL and licenses no claim; a
200-update smoke test measures seconds/update before the wave and the wave is re-planned if
the estimate is off by > 2×; one CPU thread per process. Within a rung, arms differ from arm
A by exactly one thing. Definitions used in marks: **correct** = the decoded item equals the
gold item exactly; **silent wrong write** = a wrong write item (teach/correct/forget/alias/
person/undo) with verdict EXECUTE; **echoed wrong write** = the same with verdict ECHO."*

Rung-1 marks (arm A gated; B, C recorded):

- **R1-SAFE (primary):** silent wrong writes over T-seen + T-new + T-trap + T-hard-names
  (6,500 sentences) = **0**, and items written from T-trap = **0**.
- **R1-ECHO:** echoed wrong writes ≤ **65** (1.0 % of 6,500).
- **R1-SEEN:** T-seen correct ≥ **1,940/2,000** (97 %), of which EXECUTE-correct ≥ **1,800** (90 %).
- **R1-NEW:** T-new correct ≥ **2,400/3,000** (80 %), of which EXECUTE-correct ≥ **1,950** (65 %).
- **R1-NAMES:** T-hard-names correct ≥ **300/500** (60 %).
- **R1-ASK:** wrong EXECUTED questions ≤ **25** of T-seen + T-new (0.5 %).
- **Recorded only:** T-far; 4-hop questions; router gate histogram (dead or saturated
  gates); per-family misses.

Arms: **A** = `tape` (skills + router, B.2–B.3). **B** = `bigru` (same-size BiGRU tagger,
same inputs and heads). **C** = `names` (= A but out-of-lexicon words hashed into 8,192
embedding rows instead of `OPQ#k`). Registered seeds **4301, 4302, 4303** per arm.

---

## 2. Registered interpretations (fixed before sealing)

These resolve points the design leaves open. They are registered here so they cannot be
chosen after seeing a test number.

1. **What "correct" means for a sentence whose gold has no item.** The generator's traps,
   small talk, gibberish and two-fact sentences have gold item `None` (nothing may be
   written). Such a sentence counts **correct** when the system produces no item — verdict
   REPHRASE — or an act in {unsure, smalltalk, multi, dontknow}. It counts **incorrect**
   otherwise. For a sentence whose gold has an item, **correct** = verdict is EXECUTE or
   ECHO **and** the decoded item equals the gold item on every schema field except
   `confidence` (act, subject, relation_path, relation_surface, value, value_kind, alias,
   canonical, choice, text). "EXECUTE-correct" = correct with verdict EXECUTE.
2. **Brake 3 and the "3 of 3 seeds" rule.** Brake 3 (three ears agree) consumes the arm's
   own three registered seeds, so an arm has exactly **one** five-brake system, not three.
   The **gated verdict is the full five-brake pipeline** over seeds 4301+4302+4303. Every
   single ear is *also* scored alone against the same marks, with brakes 1, 2, 4, 5 only and
   its own τ, and all three single-ear numbers are printed separately in RESULTS.md — before
   the agreement brake (single ear) and after it (ensemble), clearly separated. No mark is
   gated on a single ear.
3. **Thresholds.** τ0 = the smallest value giving 0 wrong EXECUTED writes on the CAL panel
   under the same pipeline being scored; τ_exec = 1 − (1 − τ0)/2; τ_echo = 0.5 fixed.
   Computed separately for the ensemble and for each single ear. CAL is never a test panel.
4. **Per-head temperatures** are fitted on CAL by golden-section search on log-temperature
   at the end of each training run, and stored in the checkpoint.
5. **`quote`** (a hypothetical or reported-speech sentence repeated back) writes nothing and
   is excluded from EXECUTE by brake 1, so its best verdict is ECHO; brake 4 (leftover
   opaque tokens) is applied only to acts that point at spans (teach, correct, ask, forget,
   alias, person), never to `quote`, `smalltalk` or `unsure`.
6. **Pending acts** (yes / no / pick / undo) never occur in rung 1 — there is no pending
   state — so the decoder answers REPHRASE(not_sure) for them and the `CHOICE` slot is
   always absent. `pending_choice_id` is therefore always 0 in rung 1.

---

## 3. Deviations from the design, stated before sealing

1. **No frequency lexicon.** B.1 builds the lexicon from the 3,000 most frequent lower-case
   forms of TinyStories + Simple English Wikipedia. Neither corpus is on this machine and
   this task may not download. The lexicon is instead (a) a hand-written common-English word
   list (`scripts/fable_ears45_lexicon.py`, ~1,250 forms, no personal or place names, but
   keeping name-colliding words like *rose, will, may, mark, hope, art, bill, grace, sky,
   daisy*), plus (b) every word form of the TRAIN frames, plus (c) every word of the
   relation-wording and correction-cue tables. **Rule for test-only material:** a test-only
   relation wording or sentence opener is in the lexicon **iff its words are in list (a)** —
   i.e. only if a real frequency lexicon would plausibly have held them. List (a) was
   written before the frame table was split and is not adjusted per split. Seventeen forms
   judged too rare for a 3,000-form list (*resides, dwells, hails, moniker, surname,
   employed, occupation, abode, domicile, …*) are deliberately absent and therefore reach
   the network as opaque labels. Final lexicon: **1,303 rows** including PAD/BOS/EOS and the
   eight `OPQ` rows.
2. **Simulated notebook feature bits.** There is no live notebook in rung 1, so of the ten
   feature bits of B.1:
   - `known_relation_wording` is computed for real, by longest 1–3-token match against the
     relation-wording table (the same table the decoder's key 2 uses);
   - `known_alias` is **simulated**: each maximal run of consecutive opaque non-punctuation
     tokens is marked "the notebook knows this name" with probability 0.45, independently of
     its role in the sentence, so the bit carries no information about which slot it is. It
     is then dropped 50 % of the time in training, as B.1 prescribes;
   - `pending_choice_id` is always 0 (interpretation 6).
3. **Updates reduced from 12,000 to 8,000 for every arm equally.** The design estimates
   0.02 s/update. The registered 200-update smoke on throwaway seed 9999 measured
   **0.120 s/update** alone and **0.151–0.155 s/update** with three processes in parallel on
   this Mac — 6–8× the design's estimate. 12,000 updates × 0.155 s = 31 min, over the
   30-minute wave limit. Per the task's rule, updates are cut equally for all three arms:
   **8,000 updates, batch 128, AdamW lr 2e-3 cosine** (everything else as B.3). This is the
   only training-recipe change and it is identical across arms.
4. **Waves.** One wave per arm, three seeds in parallel (never more than 3 training
   processes), scoring after each wave: A (`tape`), then B (`bigru`), then C (`names`).
5. **Frame-table size.** The design's E.2 asks for roughly 600 TRAIN / 60 DEV / 150 held-out
   frames. The re-targeted table yields **300 train / 26 dev / 55 new / 26 far** frames over
   22 families. Counts per family are printed by
   `fable_ears45_data.py --report` and reproduced in RESULTS.md. Seven families
   (`correct.link`, `correct.noun`, `person`, `trap.leftover`, `trap.multi`,
   `trap.negation`, `trap.stmtq`) have **zero** held-out (`new`) frames, so for those
   families T-new tests held-out *names, values and wordings* but not held-out *templates*.
   This is recorded, not repaired.
6. **`teach` / `correct` are one-hop only.** The unchanged validator
   (`fable_listening_english._validate_shape`) requires teach and correct to carry exactly
   one hop, although the design's B.3 example shows a two-hop `correct`. Rung 1 therefore
   generates no multi-hop teach/correct sentences. Multi-hop appears only in `ask`
   (1–3 hops, weights 0.50 / 0.333 / 0.167).
7. **No 4-hop questions.** The generator's maximum is 3 hops, so the "4 hops recorded only"
   line is recorded as *not measured* rather than as a number.
8. **Two-item sentences.** Rung 1 trains 1 item only (as the design says). `trap.multi`
   sentences carry gold `n_items` of 2 or 3 and gold item `None`; the correct behaviour is
   REPHRASE(one_thing_at_a_time).
9. **Held-out relation wordings stay in the wording table.** That is the design's own
   two-key rule (B.4): the table supplies the key, the untrained `relkey` head disagrees,
   and the decoder ECHOes with the table's key. A held-out wording can therefore produce a
   *correct* item at ECHO, never a silent write.
10. **Batches are drawn within length buckets** (≤10, ≤14, ≤18, ≤64 tokens), with a bucket
    chosen in proportion to its size, so every training example still has the same
    probability of being drawn; this only reduces padding and CPU time.
11. **The training pool** is 60,000 sentences generated once from the TRAIN frames and TRAIN
    name/value pools with a fixed pool seed (45100), identical for every arm and seed;
    `--seed` controls initialisation, batch order, feature dropout and the per-sentence
    opaque-label shuffle.

---

## 4. Panels (E.2 sizes) and their hashes

Generated by `fable_ears45_data.py --panels`, sealed before any training.

| panel | size | frames | names/values | held-out wordings |
|---|---|---|---|---|
| dev | 5,000 | train+dev | dev | no |
| cal | 5,000 | dev | dev | no |
| t_seen | 2,000 | train | test | no |
| t_new | 3,000 | new | test | yes |
| t_far | 1,000 | far | test | yes |
| t_trap | 1,000 | all, trap families only | test | yes |
| t_hard | 500 | train+new | hard names/values | yes |

```
dev        a15d65a29e5136646bc5758c22a22ffd4ea5798203c7c0c87d00ee187b0300af
cal        a6929f1eed3526268aea929465b2f3c4b1a78a543548579b3619d183ec504579
t_seen     5aac3fb6fa6c10d9de3b0e2fa639b252bc949007d65cfd46d36e7cef57a74427
t_new      1f1c81b42175607ed7de55bddde7fd30edb33102edb0dfa108f85dd499bc105a
t_far      856221c814fde0247b91a87762063261e15588c80a7ea453ec3ed624a57d10df
t_trap     836a5d1eb744c1c884fc9d4dbc1ab97ec2ab61a4a0260265e46dfe5568d3b5b5
t_hard     79a2e04f6a78422150447ccf50cd717867dc1cd5912c45d6d01b78a380c7c7f7
```

Split / pool / lexicon identity: split sha `41d7e588dd0b2f3c`, pools sha `1b4f9f5bdf0d7001`,
lexicon sha `552899c55ae3a0f0`.

E.3 enforcement runs as assertions inside `fable_ears45_data.py`
(`Split.assert_heldout`, `Pools.assert_disjoint`): no held-out template equals a train
template after stripping placeholders, punctuation and case; token-set Jaccard < 0.8 between
every `new` skeleton and every train skeleton; no T-far construction tag appears in TRAIN;
name / place / organisation / colour / literal pools are disjoint across train, dev and test.
Nine frames were moved back into TRAIN by that repair and are listed by `--report`.

---

## 5. Unit self-test that must pass before training

`scripts/fable_ears45_selftest.py`: 1,000 generated sentences across all panels; the gold
spans must decode back to the exact gold strings, and the decoder fed **oracle**
probabilities built from the gold targets must reproduce the gold item byte for byte, and
the unchanged validator must accept every gold item. Result required: `SELFTEST PASS`.

---

## 6. If a registered mark fails

Record the FAIL and stop. No fix cycle in this task. Every silent wrong write is listed
verbatim (utterance, gold item, decoded item) and up to 30 echoed wrong writes likewise, so
the lead can decide.
