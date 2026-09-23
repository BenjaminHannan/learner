# Own ear and own mouth: the plan (Opus 5.5, own-model line, 2026-09-23)

Design only. Nothing was trained, downloaded, built or run for this file. No TEST-ONLY panel was opened.
This is only about the chat assistant (ear → notebook → reasoner → mouth). It says nothing about the small card
experiments or the village model.

Evidence labels: **shown** = measured in this repo (file named) or published (arXiv id); **suggested** = published
in a different setting; **untested** = my reasoning or arithmetic.

---

## 0. One-page summary

**Goal.** Swap the two borrowed parts for Ben's own weights and architecture:
- the ear (today: SmolLM2-360M fine-tuned to write `TEACH | s | r | v` lines, "ear v4.1");
- the mouth (today: the 241 hand-made grammar layer, with talker120b and borrowed SmolLM2 as earlier tries).

The own parts must do at least as well as the borrowed ones on the same sealed marks, and the whole system must
beat a same-size plain transformer on two-hop, reversal, abstention and MQuAKE-style edits.

**The main choice: drop-in first, "thought vector" second.** Doc 24 (approved by Ben as D1–D9 on 20 Sept) planned a
416-number typed thought with a free "gist" for small talk. Since then the pipeline has settled on frames
(`TEACH/ASK/NONE` from the ear, reply records into the mouth), and every sealed mark is written against frames. So v1
of the own ear writes **the same frames**, and v1 of the own mouth reads **the same reply records**. Each own part
is then a one-change swap that the existing marks can judge. The typed slots of doc 24 (act, who, relation path,
value) are exactly a frame, so nothing is thrown away. The gist and the "thinker" for small talk come after the
fact path works (stage T1 below).

**What already exists and is ours** (shown):
- talker101: our own 28.85M decoder, trained from random numbers on SimpleStories (617M tokens, about 3.5 h on
  BensPC, about 49,000 tokens/s). Validation loss PASS; grammar test BLiMP-10 67.4% (bar 70%) = registered FAIL.
  Board 04:42, `artifacts/claude-talker101-eval-20260922/`.
- talker120b: talker101 fine-tuned to speak from records. Before the brake 172/500 unfaithful; after the brake 0/500.
  Names got cut up ("Fara" for Farah) because the copy head copied word pieces, not whole names. Board 05:44.
- A plain-torch Llama re-implementation with exact parity (235 design note), and the frame generator families C1–C8
  (`artifacts/claude-smolear257-20260922/PASSMARKS.md`).

**The plan in one line each:**
1. **Ear:** a 32.9M bidirectional reader (29.4M encoder + 3.5M heads) of our own, pretrained by fill-in-the-blank, with heads that *point at words in
   the turn* instead of writing words, plus a separate "what is the speaker doing?" head.
2. **Mouth:** keep talker101 (already ours); change it to copy *whole names* through slot tokens; check every reply
   by reading it back with the own ear against the reply record; fall back to the 241 grammar layer.
3. **Gate:** a small plain-code write compiler is the only thing that can write (§4.1). The Qwen QA checker (exp 264) stays the permission to write until the own ear has its own measured miss
   rate. A round trip trains the ear and mouth; it is never permission to write (Ben's ruling).
4. **Baselines:** a plain transformer of the same audited size with the same data and compute, the same model with retrieval
   (MeLLo-style), and the same model given the same notebook, so "it's just a database" is answered by a number.
5. **Compute:** about 11–12 GPU-hours on BensPC for everything (free), or about 3.5 hours on one rented RTX 5090
   (about $2, cap $5). Stage O0 is CPU-only and can start now.

**The one decision for Ben** is at the end (§9).

---

## 1. Why the ear is the hard part (what the errors were)

The notebook plus reasoner answers two-hop, reversal, abstention and single-edit multi-hop questions exactly when
given clean frames (200/200 on Fable-Edit-200, shown, board exp 111). The weak point is reading English.

Real wrong saves seen so far (shown; board and 261b-decision.md; category level only):

| Error kind | Seen in | Example shape (invented, not a panel item) |
|---|---|---|
| typo stored inside a fact | 261 (2) | "my sisters name is Mira Stil" → value "Mira Stil" |
| saved from a check-question with no "?" | 261 (1), 257, 235 | "so Mira's dog is Pip" |
| pretend / plan saved as fact | 257 | "let's say Oren's boss is Tal" · "Mira wants a cat named Fig" |
| pronoun bound to the wrong person | 257, 235 | "Ada's son is Bo and he lives in Rook" → Ada lives in Rook |
| "our/we" as a subject | 257 | "our dog is Pip" → owner "our" |
| dropped facts from list sentences (recall) | 261 | "Mira and Tal are my sisters" → 1 fact, not 2 (4/16 found) |

Two lessons decide the design:
- Most of these are **act errors** (is the speaker telling, checking, supposing, planning?) and **binding errors**
  (which person does a word belong to). A pointer design stops *invented* words, but not these. They need their own
  outputs and their own training data.
- The 27B checker approved every real error it saw in 261 (shown). A reader and a gate trained on the same kind of
  data share blind spots (research note v3). An own ear that is small, pointer-based and trained on different data
  is a chance to get a *second reader whose mistakes are different*, which can be measured (§4.4).

---

## 2. The own ear (English → frames)

### 2.1 Shape

| Part | Size | Notes |
|---|---|---|
| Tokenizer | 8,192 byte-level BPE, **case kept** | trained by us on the pretraining mix plus generated chat; case matters for names and the typo guard |
| Encoder | 8 layers, width 512, 8 heads, RMSNorm, rotary positions, looks both ways | ≈ 25.2M + 4.2M embeddings ≈ **29M** (same size class as talker101) |
| Input | previous assistant reply + `<SEP>` + this turn, ≤ 128 tokens | the previous reply is needed for "No, Milan." corrections and "so …?" checks |
| Act head | from a pooled vector | **STATE / CORRECT / DENY / ASK / CHECK / SUPPOSE / PLAN / CHAT / UNCLEAR**. Only STATE, CORRECT and DENY can ever write. |
| Fact-count head | 0–6 | how many facts the turn states |
| Fact slots | 6 learned queries (set prediction, matched to the gold facts during training) | each slot: exists? · owner · relation · value · a confidence |
| Owner | pointer to a whole-word span of the turn, **or** the token `ME` (I/me/my), **or** `WE` (we/our) | Ben's ruling 1 makes "me/my" the user. "we/our" gets its own token: the write compiler maps it to the user only under the current 261 canonicaliser rule, so that rule stays visible and can be changed and measured (both outside answers: "our" is not "my") |
| Relation | a choice from relation table v2 (+ "other") **plus a pointer to the relation words** ("mother", "sister-in-law") | a class, never free text; the cue must be a whole span, so "sister" cannot eat half of "sister-in-law" |
| Value | pointer to a whole-word span of the turn | |
| Slot mode | ASSERT / CORRECT / DENY / ASK / CHECK / SUPPOSE / PLAN / REPORTED / NONE, per slot | a turn can state one thing and ask another; the turn-level act head is kept as a summary |
| Question head (ASK) | owner pointer + up to 3 relation choices + an "inverse" flag | "Who is Ada's child?" = owner Ada, relation mother, inverse |
| Total | | **32,850,051** by the count in §7.1 (design count; audited after the build) |

### 2.2 What each part stops, and what it doesn't

| Part | Stops by construction | Does NOT stop |
|---|---|---|
| Span pointers for owner and value | invented names and values; half-names; leftover words glued onto a value (a span ends at a word boundary) | a typo that is really in the turn (it is copied faithfully); a span that is the wrong word |
| `ME` token as the only way to say "me" | "our"/"we" as a stored subject | who "we" means when it is not the user |
| Relation as a class | invented relation names | the wrong relation from the table |
| Act head with 9 kinds, writing only from 3 | nothing by construction; it makes the "is this being told?" decision its own trained output instead of a side effect | a wrong act (needs data, §2.4, and the gate) |
| Count head + set slots | nothing by construction; it makes a dropped fact visible (count 2, one slot filled → ask, don't half-save) | the count and the list both being wrong the same way |
| Previous reply in the input | nothing by construction | it makes corrections and check-questions learnable |

**Also by construction, in software (§4.1):** only the write compiler can write; it takes spans of the unchanged turn,
never a string from a network, and writes a turn's facts all together or not at all.

**Claims:** pointer copying for faithful outputs is suggested (pointer-generator networks, arXiv 1704.04368;
transformers copy far better than recurrent models, arXiv 2402.01032). Set prediction with a matching loss for
extracting several facts from one sentence is suggested (arXiv 2011.01675). That this combination fixes our error
kinds is untested.

### 2.3 Training stages for the ear

1. **Pretraining, fill-in-the-blank** (span masking, 15%). Data (§5): SimpleStories + TinyStories-V2 +
   TinyDialogues + WebRED sentences, ≈ 600M tokens. No facts are learned as truth: this only teaches English.
2. **Frame training** on generated turns whose labels are exact by construction (§2.4), ≈ 50M tokens, 3 seeds.
3. **Calibration** of the confidence on a development split with Learn-then-Test (as exp 213 already does). Below
   the threshold the ear asks instead of saving.

### 2.4 Frame training data (exact labels, no Qwen labels)

Built by a generator that simulates the notebook, as in doc 24 §4.2, reusing the 257 families C1–C8. New families,
each a **counterfactual minimal set**: the same words with one change that flips save/no-save.

| Family | Minimal set (invented) | Label |
|---|---|---|
| act | "Mira's dog is Pip." / "Is Mira's dog Pip?" / "so Mira's dog is Pip" / "Say Mira's dog is Pip." / "Suppose Mira's dog is Pip." / "Mira wants a dog called Pip." | STATE / ASK / CHECK / SUPPOSE / SUPPOSE (Ben ruling 4) / PLAN |
| binding | "Ada's son is Bo and he lives in Rook." / "Ada's son is Bo and she lives in Rook." | the second fact goes to Bo / to Ada |
| plural | "Mira and Tal are my sisters." / "My sisters are Mira, Tal and Oona." | 2 / 3 facts, owner `ME` |
| appositive | "My boss, Tal, has a cat named Fig." | 2 facts |
| correction | "Fig, not Moss." / "Actually it's Fig now." | CORRECT or DENY with the old value |
| chat noise | missing "?", all lower-case, doubled letters, missing apostrophes ("toms boss") | same label as the clean turn |
| typos in values | "Mira Stil" where the notebook knows "Mira Still" | save the typed span but raise a spelling flag → the system asks (research note v3: a flag, never a silent fix of a name) |

- Names: a pool of fictional names, re-drawn per example; a separate reserved pool never used in training (test only).
- Wordings: ≥ 40 hand-written frames per (act × relation kind), plus Qwen paraphrases **written with placeholders**
  (`{S}`, `{R}`, `{V}`) so the label comes from the generator, never from Qwen. Split by frame before training into
  L1 (seen frames, new names), L2 (held-out frames), L3 (outside wordings, sealed).

### 2.5 Optional later: cycle training

Once the own mouth exists: sentence → ear → frame → mouth → sentence, with a loss on the round trip, as a way to
learn from unlabelled chat (CycleGT, arXiv 2006.04702, suggested). This is training only. Round-trip agreement is
never permission to write (Ben's ruling; research note v3 §5 shows how a wrong fact can round-trip perfectly).

---

## 3. The own mouth (reply record → English)

### 3.1 Shape

Keep **talker101** (28.85M, ours, already trained; 10 layers, width 512, 4,096 BPE). It already learned English;
retraining it would spend GPU hours for nothing until a test says it must.

Changes, one per stage (§6):
1. **Whole-name copy.** Training targets say `<S1>`, `<V1>`, `<OLD>` where a name or value goes; the printer puts the
   exact string back. The copy head no longer copies word pieces, so "Fara" for Farah cannot happen.
2. **Meaning check by read-back.** Every reply is read by the own ear; the frame it reads must match the reply
   record (act, owner, relation, value, negation, direction). Here a round trip *is* a fair check, because the
   thing it is compared with is the source (the record), not the ear's own guess. If it doesn't match → the 241
   grammar layer says it instead.
3. **Grammar.** If 3.1 fails the grammar mark, the pre-named fix is to continue pretraining talker101 on
   TinyDialogues + TinyStories (conversation shape) for about 1 GPU-hour.

### 3.2 Small talk (later, stage T1)

Doc 24's thinker and gist (D5) sit on top of this mouth and are unchanged as a plan. They start only after the fact
path passes, because small talk through a 256-number gist is the riskiest part (doc 24 §1.2: likely to disappoint).

---

## 4. The write gate

### 4.1 The write compiler (the only thing that may write)

Taken from both outside answers (§11). A small piece of plain code is the **only** part of the system with write
permission. Networks (ear, reasoner, mouth) only *propose*. The compiler:
- takes spans (character offsets) of the unchanged turn, never a string produced by a network;
- takes the relation from the table only, with the direction set by the table's rule for that cue, not by a network;
- maps `ME` to the user; maps `WE` only as the current canonicaliser rule says;
- writes all of a turn's facts together or none of them (a count that disagrees with the filled slots → ask);
- stores the source turn, spans and a transaction id with each row; corrections supersede, they never erase;
- never writes inferred facts or inverses (as today).

These are guarantees about the software. They are **not** a guarantee that English was understood: a copied name can
belong to the wrong person and a check-question can look exactly like a statement. That part can only be measured.

I do **not** adopt the outside answers' stricter option, where the compiler re-parses the turn with its own grammar
and writes only what every grammar reading supports. That grammar would be the retired rule tables again, and both
answers name it as the design's weak point. Stage O0 measures its ceiling instead (oracle coverage), so the choice
rests on a number.

**Update 2026-09-23 10:45 (after O0a/O0a2, board entry):** Ben ruled that "we/our" facts are never saved as the
speaker's; the system asks whose they are. The literal-cue rule capped coverage (v0 67.6%; v1 89.7% on a set rich in
plurals, 83.5% on the earlier natural set), so relations are **licensed by the ear's calibrated relation head**, with
a cue in the turn as extra evidence and a higher threshold for cue-less facts (set on dev). Spans, modes, WE→ask and
atomic writes stay hard rules. O0a3 measures which wrong readings each rule lets through.

### 4.2 Rule

A fact is written only when **all** of these hold:
1. the own ear says act ∈ {STATE, CORRECT, DENY}, the slot is above its calibrated threshold, and count = filled
   slots;
2. the software guards pass (span, mixed-case/typo guard from 261b, comma guard 263);
3. an **independent** check of the fact against the *original turn* says yes: while the own ear is new, this is the
   Qwen QA checker from exp 264 (whatever 264 registers).

### 4.3 When the own ear may become its own gate

Only after it has a measured miss rate on errors *the other reader actually makes*, not on made-up corruptions.

### 4.4 Measuring whether two readers share blind spots

On a development split (never a blind panel), run ear v4.1+Qwen and the own ear on the same turns. Count:
- a = turns where only the borrowed reader is wrong, b = only the own ear, c = both wrong in the same way.

If errors were independent, c would be about (a+c)(b+c)/N. A c far above that means shared blind spots and "both
agree" is worth little. "Save only when two different readers agree on the whole frame" is a real check (both read
the source), unlike the round trip. **Untested.**

---

## 5. Data (licences, no personal data, no unverified web text)

| Set | Written by | Size (from doc 24 / 87) | Licence | Used for | Status |
|---|---|---|---|---|---|
| SimpleStories | GPT-4o-mini | 2.1M stories, 617M tokens with our 4k BPE (shown, talker101) | MIT | ear pretraining; mouth (already used) | on BensPC |
| TinyStories-V2 (GPT-4 file) | GPT-4 | 2.23 GB ≈ 0.55B tokens | CDLA-Sharing-1.0 (sharing applies to republishing the data) | ear pretraining | download approved (D3, ≤ 7 GB total); builder checks size |
| TinyDialogues | GPT-4 | 316 MB ≈ 40M tokens | MIT | ear pretraining; mouth fix 3 | download approved (D3) |
| WebRED sentences | Wikipedia sentences, human-labelled | 53 MB | CC BY 4.0 | ear pretraining (varied vocabulary, Ben's 21 Sept ruling) | on disk, `data/open/webred/` |
| Generated teach/ask/correct turns | our generator | ≈ 50M tokens | ours | ear frames; baselines | to build (O0) |
| Qwen placeholder paraphrases | Qwen3.8-27B on BensPC | ≈ 1,500 frames | ours | wording variety only; never labels | later (a Qwen night) |

Rules: fictional names only; no personal data; the repo-root `notebook/` is never read; no general web crawl.
All English-teaching text above was written by big AI models. **No weights are borrowed**, but every claim must say
"it learned English from simple stories and chats written by large AI models" (doc 24 D9).

---

## 6. Staged plan: one change per stage, marks fixed in advance

Each stage is its own sealed experiment with `PASSMARKS.md` sealed before the run. Numbers here are the proposed
marks; the builder copies them into the seal unchanged or the director re-rules them in writing before sealing.
"Dev" = a generated development split, never a blind panel.

Rule for every training change (from the outside answers): the comparison arm is the previous accepted model trained
for the **same extra budget** on the same data, so "it helped" can't just mean "it trained longer".

### O0 — CPU only, no weights kept (can start now)
**Change:** none to the model; builds the tools. **Also the oracle-coverage check:** give the write compiler the
*correct* frames for 300 development turns written from a spec (not a blind panel) and count what share of the real
facts it would let through. If even perfect reading gets < 85%, no training can reach the 85% recall target under
these write rules, and the rules change before any GPU hour is spent. Generator + sealed L1/L2/L3 splits + counterfactual families,
the 8,192 tokenizer, the ear model code, and a **3M-parameter ear trained on the Mac CPU for ≤ 25 min** on generated
frames only (no pretraining).
Marks: every generated label re-derived by a rule-based checker (0 mismatches in 10,000); splits hashed; the tiny ear
on L1 dev: whole-frame exact ≥ 90%, act accuracy on the counterfactual act family ≥ 95%, and **0 values or owners
that are not a span of the turn** (checked on every output). **Proved wrong if** the tiny ear can't separate
STATE from CHECK/SUPPOSE/PLAN on L1 (< 80%), which would mean the act family is too weak to learn even in-template.

### E1 — pretrained own ear vs the same ear from scratch (GPU ≈ 3.5 h + 2 × 15 min)
**Change:** fill-in-the-blank pretraining on/off, everything else identical (32.9M ear, same frame data, seed).
**Side arm (the decisive ear comparison):** a same-size own *autoregressive* frame writer (the rival design, §10), with
the same pretraining, the same labels and the **same write compiler**. If the pointer ear does not beat it on wrong
proposals or recall, the pointer design is not shown to be better.
Marks: on L2 (held-out wordings), whole-frame exact improves by ≥ 10 points with pretraining; wrong writes (a save
that is not in the gold) ≤ 1 per 300 dev turns in the pretrained arm. **Proved wrong if** L2 gains < 3 points:
pretraining is then not what makes new wordings readable, and the plan re-thinks before scaling.

### E2 — counterfactual act families added (3 seeds × 15 min)
**Change:** add the act, binding and noise families of §2.4 to the frame data.
Marks: on dev, saves from CHECK/SUPPOSE/PLAN turns ≤ 1 per 200 such turns in every seed; true facts lost vs E1
≤ 2%. **Proved wrong if** check-questions without "?" are still read as STATE in ≥ 5% of those turns.

### E3 — set slots with a count (3 seeds × 15 min)
**Change:** the 6 set slots + count head replace a single-fact output (E1/E2 arms use 1 slot + "more" flag).
Marks: plural and appositive dev turns: all facts found ≥ 90% (261 was 4/16); turns with count ≠ filled slots are
asked about, never half-saved. Recall reported three ways (read right, saved right, sent back as a question).
**Proved wrong if** plural recall < 60%.

### E4 — own ear against ear v4.1 on a fresh blind panel
**Change:** swap ear v4.1 for the own ear inside the current pipeline; gate (Qwen QA from 264) unchanged.
Panel: written blind by a separate agent from a spec, sealed before the run, ≥ 150 turns, same marks as 261b
(wrong saves ≤ 1, exact TEACH ≥ 85%, ASK ≥ 90%, median ≤ 800 ms). Report wrong saves per saved fact and per turn,
plus recall. Also report the shared-blind-spot count of §4.4 on dev.
**Proved wrong if** the own ear has more wrong saves *before the gate* than ear v4.1 on the same panel.

### E5 — certification run (later)
Freeze everything first (weights, tokenizer, relation table, compiler, thresholds, grading rules). A fresh,
representative sample of **≥ 368 independent everyday-chat turns** for writes and ≥ 368 replies for grammar: with 0
errors in each, both rates are below 1% *together* at 95% (2.5% error allowed per claim). 300 turns certify one rate
alone. Report the rate per turn (a turn with any wrong save) and, separately, per saved fact (with turns as clusters),
plus automatic recall ≥ 85% and how often it asked. Confirmed-after-asking facts are reported apart, never counted as
automatic recall. A failed certification is not re-run until it passes under the same 95% claim; any retry is
pre-registered with its own error budget. The certificate names the kind of chat it was tested on.

### M1 — whole-name copy in talker101 (GPU ≈ 1 min, or Mac CPU)
**Change:** slot tokens instead of word-piece copy, vs talker120b.
Marks: truncated names 0/500; raw unfaithful before the brake ≤ 50/500 (120b: 172/500); status right ≥ 489/500.
**Proved wrong if** raw unfaithful stays > 120/500: the names were not the main problem.

### M2 — read-back check with the own ear (needs E3)
**Change:** add the §3.1(2) meaning check before the reply is sent; 241 layer as fallback.
Marks: 0 unfaithful after the check on 1,200 renders, *including* act, negation and direction (the old brake misses
these, doc 240 §0.2); fallback rate ≤ 10%.

### M3 — grammar and naturalness, blind
**Change:** none (a measurement of M2), graded with the 241 style sheet v2 by a blind grader.
Marks: grammar ≥ 99% over ≈ 1,200 renders and ≥ 97% per act; blind pairwise naturalness vs 241b ≥ 60% wins.
**Proved wrong if** grammar < 97%: then the pre-named fix (§3.1 step 3) is the next single change.

### B — the comparison (after E4 and M3)
See §7. Marks fixed before the baselines are trained.

### T1 — small talk through the thought (after B)
Doc 24 S1/S2 (thinker + gist) on top of the own ear and mouth, with doc 24's marks.

---

## 7. A fair comparison with a same-size plain transformer

Benchmarks (all synthetic, fictional names, generated by our generator, sealed before any baseline is trained):
- **two-hop:** facts taught in separate turns, asked as one question;
- **reversal:** taught "Ada is Bo's mother", asked "Who is Ada's child?" (the reversal curse, arXiv 2309.12288);
- **abstention:** untaught facts and never-mentioned people, plus the wipe test (empty notebook → "I don't know");
- **MQuAKE-style edits:** teach a chain, correct one link, ask the multi-hop question (MQuAKE, arXiv 2305.14795);
- **3- and 4-hop** chains longer than any in training;
- grammar of the answers.

Arms:

| Arm | Size | Memory | Why it's there |
|---|---|---|---|
| **Premonition-own** | **61,783,463** (§7.1) | notebook | the system |
| **B-plain** | **61,783,680** (§7.1), decoder-only, same 8,192 tokenizer | the conversation in its context window (1,024 tokens) | Ben's goal: beat an equal-size plain transformer |
| **B-RAG** | 61,783,680; B-plain + retrieval of the taught sentences for each question (MeLLo-style) | a retrieval store | an expert's first question: "how is this not just a database?" |
| **B-notebook** | 61,783,680; B-plain given the same notebook, as serialized rows in its context, with the same write compiler | the same notebook | separates "the notebook helps" from "the learned ear, reasoner and mouth help" |

### 7.1 Parameter counts (design counts, recomputed from the shapes; the builder re-counts from the built models)

Every learned number the benchmark path uses is counted, including all ear heads, the whole mouth and the reasoner.

| Part | Shape | Parameters |
|---|---|---:|
| Ear embeddings | 8,192 × 512 | 4,194,304 |
| Ear encoder | 8 blocks × (attention 4·512² + MLP 8·512² + 2 norms) + final norm | 25,174,528 |
| Ear slot layer | 1 cross-attention layer for the 6 slot queries + the queries | 1,052,672 |
| Ear pointers | owner, value and relation-cue start/end projections (6 × 512²) | 1,572,864 |
| Ear question pointers | question-owner start/end (2 × 512²) | 524,288 |
| Ear classifiers | relation (154 classes) per slot + 3 for questions, slot mode (9), act (9), count (7), exists, inverse | 329,859 |
| Ear special tokens | `ME`, `WE`, `SEP` | 1,536 |
| **Ear total** | | **32,850,051** |
| Mouth (talker101, incl. its 0.52M copy head) | as trained; `artifacts/fable-talker101-20260921/RESULTS.md` | 28,847,105 |
| Mouth slot tokens | 8 new tokens × 512 (M1) | 4,096 |
| Reasoner | the existing lookup operator | 79,316 |
| **Premonition-own total** | | **61,783,463** (the first version of this doc said "≈ 59M" and left out the ear heads) |
| **Each baseline** | decoder-only, 12 blocks, width 640, SwiGLU MLP width 1,600, 8,192 tied embeddings, RMSNorm | **61,783,680** (+217, +0.0004%) |

B-RAG and B-notebook reuse B-plain's pretrained weights (retrieval and rows are test-time inputs), and the
3 seeds are for the dialogue-training stage; the long pretraining runs once per side, as in §8.
Retrieval in B-RAG uses plain word-overlap search (no learned parameters), and B-notebook gets the rows as text, so
all three baselines have the same count. If the built system's audited count differs, the baselines are re-sized to
within 0.2% before any baseline is trained, and both counts go in the PASSMARKS.

Three tests keep the sources of a win apart: (1) **language boundary**: English → each reader → the same compiler and
notebook, score the fact sets; (2) **reasoning**: gold facts and gold questions in, no ear; (3) **end to end**.
If Premonition-own beats only B-plain, the honest claim is "an external-memory assistant works better", not "a
better reasoner".

Fairness rules (fixed in advance):
- same pretraining text and the same number of training FLOPs as ear + mouth pretraining together (so each baseline ≈
  62M × 617M tokens), the same generated teach/ask/correct dialogues as training text, 3 seeds each (training time and FLOPs reported too:
  equal parameters do not mean equal compute for an encoder + decoder versus one decoder);
- the same test items, greedy decoding, the same answer extractor for every arm;
- report the ear's reading accuracy separately, so a win is not credited to the notebook when the reading failed,
  and a loss is not blamed on the notebook when the reading failed;
- parameter counts audited from the built models (shared tensors counted once); the baselines are sized to within 1%
  of Premonition-own's audited count, not "about the same";
- say plainly what the notebook gives for free (exact storage, edits by overwrite) and where the learned parts
  (ear, reasoner, mouth) had to earn it.

Expected (untested): B-plain loses on 3–4 hops and on long conversations. It may **not** lose on reversal: the
reversal-curse paper (arXiv 2309.12288) found models *can* reverse a fact that is in their context window; the curse is
about facts learned in the weights. So reversal is only a fair win if B-plain actually fails it when measured.
Success = a paired gain of ≥ 5 points in each benchmark family, over ≥ 500 independent fictional worlds per family,
with the confidence interval above zero after correcting for the four families, across 3 seeds (no best-seed picking).
If B-RAG or B-notebook ties Premonition-own, that is the headline.

---

## 8. Compute and money

Anchor (shown): talker101, 28.85M parameters, 617M tokens, about 49,000 tokens/s on BensPC's RTX 5070 Ti, about
3.5 h. Planning rule (untested): time scales with parameters × tokens.

| Job | BensPC (free) | One rented RTX 5090 (≈ 3× faster on a small model, shown on the 4M model; $0.27–0.60/h listed) |
|---|---|---|
| O0 tiny ear | Mac CPU ≤ 25 min | — |
| E1 ear pretraining, 29M × 600M tokens | ≈ 3.5 h | ≈ 1.2 h ≈ $0.50–0.75 |
| E1–E3 frame training, 8 short runs | ≈ 2 h | ≈ 0.7 h |
| M1 mouth fine-tune | ≈ 1 min | — |
| Each baseline, 61.8M × 617M tokens | ≈ 7.5 h (two resumable runs of ≤ 6 h, D8) | ≈ 2.5 h ≈ $1–1.50 |
| B-RAG and all evaluations | ≈ 1 h | — |
| **Total** | **≈ 11–12 GPU-hours, $0** | **≈ 3.5–4 h, ≈ $2–2.50; hard cap $5** |

BensPC is shared: Qwen (the 264 checker, 261b) takes about 15 GB of the 16 GB card, so it can check or train, never
both. The $30 cap is shared across all lines; the ledger must be read before any rental.

---

## 9. The decision for Ben

**Decided by Ben (2026-09-23 03:00 UTC): "Anything that starts and finishes overnight, use rtx 5070-ti as a blanket
rule."** So E1 ear pretraining (≈ 3.5 h) and each baseline pretraining run (≈ 7.5 h, split into two resumable runs)
go on BensPC overnight, free. A rental would only come up again for a job that can't fit in a night, and that would
be a new question to Ben. The options below are kept as they were asked.

**Where should the first long GPU job run (own-ear pretraining, E1, ≈ 3.5 h on BensPC)?**
- **Rent one RTX 5090 for about 1.2 hours (≈ $1, hard cap $3)** — runs in parallel with the other lines, which keep
  BensPC for the Qwen checker work. *Recommended*, because the GPU is the thing every line is waiting on.
- Run it on BensPC overnight, free — nothing else can use the GPU for those hours.
- Wait until the checker work is finished.

Either way it starts only after O0 passes on the Mac CPU. O0 needs no decision and can start now.

---

## 10. Risks and the strongest objection

- **Objection:** "The own ear is a slot-filling parser; the hard part is still the act and binding decisions, and a
  30M model trained on template-ish data will fail on how Ben really types." True risk. Answers: pretraining (E1)
  plus Qwen placeholder paraphrases for variety; the L3 outside-wording split; and the gate stays independent until
  E4/E5 measure the own ear on fresh blind turns. If E4 fails, the borrowed ear stays and the own ear becomes the
  second, different reader of §4.4.
- **Rival design considered:** a 60M own decoder that writes frame text (like ear v4.1, but ours). Simpler, and it
  reuses talker101's code. Rejected as the first choice because free-text output can invent spans and glue leftover
  words, the two things pointers remove for free. It stays available as an arm for E1 if E1's pointer ear fails.
- **Mouth grammar:** talker101 scored 67.4% on BLiMP-10. Replies are a much narrower language than BLiMP, and M2
  falls back to the 241 layer, so a failure costs naturalness, not truth.

## 11. What the two outside answers changed (Ben relayed them, 02:45 UTC)

Both answers (to research prompt 3) recommend the same thing: a span/pointer reader whose output is only a proposal,
and a small rule-checked writer. I checked each claim against the repo and the rest of this plan.

**Adopted:**
- the write compiler as the only writer, with source spans, atomic turns and provenance (§4.1);
- "our/we" as its own token, not silently "me" (§2.1);
- a pointer to the relation words, whole cues only ("sister-in-law") (§2.1);
- a mode per fact, so a turn can state and ask at once (§2.1);
- the oracle-coverage check before any GPU run (O0);
- equal-extra-budget controls for every training change (§6);
- the same-compiler autoregressive reader as the decisive ear control (E1), and a notebook-equipped plain baseline
  (§7);
- the reversal caveat: plain transformers can reverse facts that are in context (arXiv 2309.12288) (§7);
- certification: 368 per claim for two claims together, per-turn vs per-fact, frozen before testing (E5);
- freeze the relation table before scoring ("pet" vs "dog" must be declared, as 261b now does).

**Not adopted, and why:**
- *A hand-written grammar inside the compiler that re-parses the turn and decides.* It would bring back the retired
  rule tables, and both answers call it the design's weakest point. Kept only as a measured option (O0).
- *Paying an outside AI service (~$20) for paraphrases.* It spends the shared $30 cap and sends data outside; Qwen on
  BensPC already does this for free.
- *Their GPU-hour estimates (17–67 h per 1.2B tokens).* They assumed 5,000–20,000 tokens/s without a measurement. This
  repo measured about 49,000 tokens/s for a 29M model on the 5070 Ti (talker101), so §8's numbers stand.
- *A 33M total with a new 14M mouth.* talker101 (29M, already ours and trained) is the mouth; retraining a smaller one
  costs GPU hours before any test says it's needed. Baseline sizes follow the audited total either way.

Note for the reasoner line (outside this plan): both answers suggest the reasoner return the ids of the rows it used,
with code checking they are still current. That belongs to the base, not to the ear or mouth.

## Sources

Pointer-generator networks arXiv 1704.04368 · Repeat After Me arXiv 2402.01032 · Set prediction networks arXiv
2011.01675 · CycleGT arXiv 2006.04702 · TinyStories arXiv 2305.07759 · SimpleStories arXiv 2504.09184 ·
TinyDialogues arXiv 2408.03617 · Pointer networks arXiv 1506.03134 · PICARD arXiv 2109.05093 · COGS arXiv 2010.05465 ·
CycleGAN hides information arXiv 1712.02950 · Reversal curse arXiv 2309.12288 · MQuAKE / MeLLo arXiv 2305.14795 · Grokked
transformers are implicit reasoners arXiv 2405.15071 · UniversalNER arXiv 2308.03279 ·
vast.ai RTX 5090 pricing https://vast.ai/pricing/gpu/RTX-5090 · price comparison
https://getdeploying.com/gpus/nvidia-rtx-5090. Repo inputs: design/v3/24, 24b, 30-modes/87, 235, 240, 257
PASSMARKS, director board entries 04:42 / 05:08 / 05:44, research note v3
(`/mnt/project-files/research-2026-09-23/`).
