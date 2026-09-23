# 43 — STEP 3: our own EARS and MOUTH (replacing Qwen) — design document

**Fable (senior research designer role), 21 September 2026. Design and opinion only.**
Nothing was trained, rented, downloaded, or changed; this is the only new file. Nothing here starts until Ben says so.

Evidence labels: **measured here** = a number from this repo's own results; **read here** = I read it in this repo's
code today; **estimate** = my arithmetic or judgement; **from memory** = prior work I did not re-check (section J).

Files this design is aligned to (read here): `scripts/fable_notebook_contract.py` (the notebook contract),
`scripts/fable_listening_m1.py` (structured LISTENING lines), `scripts/fable_listening_english.py` (Qwen ears: the
13 acts, the JSON item schema, the deterministic validator), `artifacts/fable-english-listening-20260921/`
(three 150-sentence panels and their marks), `scripts/fable_transport43g.py` + `_v2.py` and
`artifacts/fable-transport43g-20260921/RESULTS.md` (callable skills on a tape + router),
`scripts/fable_talker24_dialogues_frames.py` + `artifacts/fable-talker24-20260920/SEALED-SPLITS.md` (the existing
wording grammar with a sealed held-out-frame split), `design/v3/24-talker-from-scratch-fable-design.md` (the earlier
33M encoder/decoder talker design, which this document replaces for the ears/mouth job).

Mini-glossary (used throughout):
- **token** = one word or punctuation mark after splitting a sentence ("Mira", "'s", "mom", "?").
- **tape** = a row of boxes, one per token, each box holding a short list of numbers. Skills read and write boxes.
- **skill** = a small frozen-able function that reads boxes at chosen *relative* places (e.g. "the box one to my
  right") and writes a result into the current box. Same idea as the CardFold skills in 43G.
- **router** = a small table of numbers saying which skills run at which stage. In 43G it was 21 numbers.
- **pointer** = an output that says "the answer is at position 3 of the input" instead of naming a word.
- **lexicon** = a fixed list of ordinary English words the model has a slot for ("lives", "mother", "not").
- **opaque word** = any word NOT in the lexicon (almost every name and place). The model never learns its identity.
- **slot** = a named blank in a record: subject, relation, value, alias, …
- **abstain** = decline to act: "I didn't understand, please rephrase."
- **bad write** = a wrong fact saved to the notebook without Ben being shown it first.

---

## A. One-page summary

**The recommendation in one sentence.** Build the ears as a *pointing machine*, not a *naming machine*: a ~0.33M-parameter
tape model made of callable skills + a router that reads a sentence in which every name has been replaced by a
meaningless label, and outputs only (a) choices from small closed lists (what kind of sentence, which known
relation) and (b) **positions** in the input; plain software then cuts the exact characters out of Ben's sentence.
Build the mouth as the mirror image: a ~0.1M-parameter causal tape model that writes a sentence *skeleton* out of
~400 function words plus slot symbols (`<S>`, `<R1>`, `<V>`); software pastes the exact strings from the reasoner's
result into the slots; the ears then re-read the finished sentence and must recover the same record, otherwise the
existing contract template is used instead.

**Why this satisfies each ruling.**
1. *Our architecture.* Both parts are the 43G mechanism (frozen-able callable skills on a shared tape, relative
   addressing, a small gate table as router) extended from digits to words. The only conventional pieces are a word
   embedding table and a dot-product pointer read, both tiny and named exactly in B.5.
2. *English only.* The model never sees the identity of any out-of-lexicon word, so it has nowhere to store
   "Paris is in France". It has no output vocabulary for content words, so it cannot state a fact from weights.
3. *Not smart, just a translator.* It only tags, points and picks from closed lists. No chit-chat in v1.
4. *New names.* A never-seen name and a trained name produce the **identical input tensor** (both are `OPQ#k`).
   New-name handling is true by construction, in the same honest sense that 43G's length generalisation was; the
   residual risk (names that are also English words, like Rose or Will) is measured on its own panel.
5. *Zero bad writes.* Five independent brakes: a trained "unsure" class; confidence = the weakest link; three
   separately-seeded ears must agree exactly; every opaque word must be accounted for; the existing deterministic
   validator stays. Anything short of that becomes a yes/no echo or a rephrase request. Nicknames always echo.
6. *Qwen for training sentences.* Recommended **yes, with four fences** (section E.5). Rungs 1–3 do not need it.
7. *Under 30 minutes.* Sentences are short (measured here: mean 5 words, max 12 in all three panels); the model is
   4× smaller than the 1.2M reference; rung 1 is ≈ 4–6 minutes per seed on one Mac core (estimate, smoke-test first).

**What is NOT claimed or attempted:** small talk, long sentences (> 32 tokens), pronouns across sentences, more
than two facts per sentence, typos in function words, any language but English. All of these become "please
rephrase", which ruling 5 says is the right trade.

### The diagram — exactly what crosses each interface

```
 Ben types:  "actually Mira's mom lives in Porto"
     │  one string, ≤ 32 tokens (longer → software replies "shorter sentence please")
     ▼
┌─ 1. TOKENISER (plain software, deterministic) ──────────────────────────────────────────────┐
│ splits words / 's / n't / punctuation; keeps (char_start, char_end) per token — OUTSIDE net │
│ lexicon lookup on lower-case form → id in 0..2999, else OPQ#k (k = random label 1..8)       │
│ asks NOTEBOOK (read-only): which n-grams are known aliases? known relation wordings?        │
└───────────────┬─────────────────────────────────────────────────────────────────────────────┘
                │  ids  int[n]        feats {0,1}[n,10]        pending int[1]      (n ≤ 34 with BOS/EOS)
                ▼
┌─ 2. EARS (learned; 3 copies with different seeds; ~0.33M parameters each) ───────────────────┐
│ tape X[n,96] → 4 stages × bank of 24 callable skills, gated by a 4×24 router table          │
│ closed-list heads: act[15]  flags[6]  n_items[4]  relkey[hop,41]  reltype[hop,2]            │
│ pointer heads (positions only): slot_start/end[5, n+1]   hop_start/end[8, n+1]  stop[8]     │
└───────────────┬─────────────────────────────────────────────────────────────────────────────┘
                │  EarsOut = probabilities over CLOSED LISTS and over INPUT POSITIONS. No strings.
                ▼
┌─ 3. DECODE + GATE (plain software) ─────────────────────────────────────────────────────────┐
│ cut exact substrings by char offsets → item in the existing JSON schema                     │
│ confidence = min(link probabilities); 3-copy agreement; leftover-opaque check; validator    │
│ verdict ∈ { EXECUTE, ECHO (yes/no first), REPHRASE(reason) }                                │
└───────────────┬─────────────────────────────────────────────────────────────────────────────┘
                │  item = {act:"correct", subject:"Mira", relation_path:["mother","city"],
                │          relation_surface:["mom","lives in"], value:"Porto", value_kind, confidence}
                │  → rendered as the existing structured line:  correct Mira ... / ask Mira mother city
                ▼
   LISTENING.hear(line)  ──writes──►  NOTEBOOK (append-only events.jsonl; IDs E0001, F00001)
        (only writer of `taught`)            ▲
                                             │ reads
                            REASONER: hard-coded hop loop today = Notebook.ask(name, relations)
                            later: the relation_path IS the route — LOOKUP(mother) → LOOKUP(city) → STOP
                │
                │  Result{status ∈ OK|SAVED|DUPLICATE_OK|CONFLICT|AMBIGUOUS|UNKNOWN_ENTITY|MISSING_FACT|
                │                  BROKEN_CHAIN|NOT_ALLOWED|BAD_REQUEST,  detail{subject, relation, answer,
                │                  old, new, name, choices, hop, trail[fact ids], source}}
                ▼
┌─ 4. MOUTH ──────────────────────────────────────────────────────────────────────────────────┐
│ 4a software: record → closed-class ids (status, speech act, person, hops, relkeys, reltype) │
│              strings are held back in a slot table {<S>:"Mira", <R1>:"mom", <V>:"Porto"…}   │
│ 4b learned (~0.1M): causal tape, 3 stages × 16 skills → skeleton over 400 words + slot marks│
│              e.g.   <S> 's <R1> lives in <V> .                                              │
│ 4c software: paste exact strings into slots; detokenise; add fixed provenance suffix        │
│ 4d check: EARS re-read the sentence → must give back the same (subject, path, value)        │
│              any failure → the contract's deterministic TEMPLATES[status] is said instead   │
└───────────────┬─────────────────────────────────────────────────────────────────────────────┘
                ▼
   "Mira's mom lives in Porto."
```

The three rules the picture enforces: **(i)** a name's characters never enter a neural network, in either
direction; **(ii)** the only thing that can write a fact is still `Listening.hear`, unchanged; **(iii)** the
mouth can arrange words but every content word is pasted from the result record.

---

## B. EARS design

### B.1 Input representation: words, with a closed lexicon and opaque labels — not bytes, not word-pieces

| Option | Tape length for a 6-word sentence | New names | Can weights memorise a fact about "Paris"? | Verdict |
|---|---|---|---|---|
| **Words: lexicon id or `OPQ#k`** | ≈ 9 | identical input to trained names — guaranteed | No: "Paris" never reaches the network | **chosen** |
| Bytes / characters | ≈ 35 | must be *learned* and then *measured*; odd spellings are a risk | Yes, spelling is visible | loses; revisit only for typo-tolerance |
| Word-pieces (BPE) | ≈ 11 | names split into pieces; span pointers get messy | Yes, name fragments get their own vectors | loses |

Justification. (1) Ruling 2 and ruling 4 are met *structurally* instead of statistically. This mirrors what passed
in experiment 29 (measured here: names as freshly shuffled codes, 3/3 seeds). (2) The 43G tape works on positions
holding discrete symbols; a word tape is its direct analogue. (3) Compute: short tapes keep rung 1 on a Mac core.
(4) It is also how a person does it: *a word I do not know, in a slot where a name fits, is a name.*

**Tokeniser (software, deterministic).** Unicode NFC; strip Markdown wrappers (`**x**`, `` `x` ``, leading `- `)
but remember them as a feature bit (measured here: Ben's panels contain `` `Ren` `` and `**Dilan**`); split on
spaces; split off `. , ; : ! ? ( ) " —`; split clitics `'s ’s n't 'm 're 've 'll 'd` ("where's" → `where` `'s`);
digits-only tokens are opaque with `is_number=1`. Each token keeps `(char_start, char_end)` into the ORIGINAL
string. More than 32 tokens → software REPHRASE(too_long); the network is not called.

**Lexicon (built automatically, once, then frozen and hashed).** The 3,000 most frequent lower-case word forms in
TinyStories + Simple English Wikipedia, after deleting any form that is capitalised in ≥ 50 % of its mid-sentence
occurrences (that rule removes Lily, Tom, London, Monday without anyone hand-picking), plus ≈ 150 forced-in words
from the relation and cue tables. Common names that are also words (rose, will, may, mark, hope, art, bill) stay
in; that collision is a named failure mode with its own test panel (G.3).

**Opaque labels.** Each distinct out-of-lexicon word type in a sentence gets one of eight labels `OPQ#1..#8`,
assigned **at random per sentence** in training (so the label carries no meaning, only "same word again"). A ninth
or later distinct opaque word → REPHRASE(too_long).

**Ten feature bits per token**: `cap_first, all_caps, is_number, in_lexicon, sentence_initial, md_wrapped,
is_punct, known_alias, known_relation_wording, pending_choice_id`. The last three come from read-only notebook
lookups on every 1–3-token n-gram (`Notebook.resolve`, the relation-wording table of B.4, the pending choices).
Feature dropout in training (`cap_first` 30 %, `known_alias` 50 %, `known_relation_wording` 30 %, whole-sentence
lower-casing 25 %) forces the model to work from sentence structure when the hints are missing.

**Tensors into the network:** `ids int[n]`, `feats {0,1}[n,10]`, `pending int[1] ∈ {none, yes_no, choices, other}`.
`X0[t] = W_p·E[ids[t]] + W_f·feats[t]`, with `E` 3,020×48, `W_p` 48→96, `W_f` 10→96; the pending embedding is added
to the BOS box. **No absolute position numbers** — structure comes only from relative offsets and the BOS/EOS
boxes, so nothing in the ears depends on sentence length (the 43A–43D lesson).

### B.2 The network: a bank of callable skills on the tape, plus a router

One ear **skill** `k` is a *gated relative transport* — 43G's "read a place, transform the symbol", with a second
read acting as an on/off gate so a skill can express "IF the next token is `'s` THEN mark me as an owner":

```
u[t] = Σ_δ α_k[δ] · X[t+δ]        v[t] = Σ_δ β_k[δ] · X[t+δ]        δ ∈ {−4..+4, FIRST, LAST, MEAN}  (12 places)
S_k(X)[t] = U_k · ( (A_k u[t]) ⊙ sigmoid(B_k v[t]) )                  A_k, B_k : 96→16     U_k : 16→96
α_k = softmax(10·tanh(a_k)),  β_k likewise                            a_k, b_k ∈ R^12  (bounded — see note)
```

Bounded address scores are 43G-v2's fix (measured here: unbounded scores saturated and 2 of 3 seeds failed to fit).
Rank 16 echoes the low-rank finding of 43E. Parameters per skill: 3·96·16 + 24 = 4,632; bank of **K = 24** ≈ 111k.

**Router.** `G ∈ R^{4×24}` (96 numbers). Stage `s`: `X ← RMSNorm( X + Σ_k sigmoid(10·tanh(G[s,k])) · S_k(X) )`,
four stages, the **same** 24 skills callable at every stage. Gates are independent sigmoids rather than 43G's
one-of-K softmax because parsing needs many detectors firing in parallel, not one step of a chain. Receptive
field: ±16 tokens plus the FIRST/LAST/MEAN global reads.

**Honest label (say this out loud in any write-up).** Mathematically this is a small weight-tied gated convolution
network with learned sparse offsets, so nobody should call it a new kind of neural network. What makes it *ours* is
what it is for: (a) skills are separate, freezable, callable units, so SLEEP can later add a route or a rank-4
skill without touching old ones (section H); (b) the address vocabulary is relative and length-free; (c) outputs
are pointers and closed lists, never generated words. Like 43G, the twelve relative places are **given by hand**;
what is learned is which places each skill uses. When the learned-relative-addressing test now running reports, its
mechanism replaces the given list as a single registered change.

### B.3 Outputs: closed-list heads and pointer heads

Pooled summary `g = [mean_t X ; max_t X ; X[BOS] ; X[EOS]]` (384 numbers).

| Head | Shape | Meaning |
|---|---|---|
| `act` | 15 | the 13 acts of `fable_listening_english.py` (person, alias, teach, correct, ask, forget, quote, yes, no, pick, undo, smalltalk, unsure) + `multi` (> 2 facts) + `dontknow` (used only by the mouth check, C.4) |
| `flags` | 6 sigmoids | correction cue, negation, hypothetical, reported speech, first person, second person |
| `n_items` | 4 | 0, 1, 2, more (rung 1 trains 0/1 only) |
| slot pointers | `[5, 2, n+1]` | start and end position for SUBJ, VAL, ALIAS, CANON, CHOICE; position 0 (BOS) means "absent"; `score = q_slot · X[t]`, softmax over positions |
| hop pointers | `[8, 2, n+1]` + `stop[8]` | relation span for hop 1, hop 2, … in **lookup order**, then STOP |
| `relkey` | `[hop, 41]` | 40 canonical relation keys (city, mother, employer, …) + OPEN |
| `reltype` | `[hop, 2]` | is this relation wording noun-like ("favourite colour") or verb-like ("works at") — the mouth needs it |

**Hop order is a loop, like the reasoner's.** "Mira's mother's city", "the city of Mira's mother" and "what city
does the mother of Mira live in?" all mean `[mother, city]`, with different surface orders, so tagging alone is not
enough. A hard-coded loop calls one skill, NEXT-REL, up to 8 times: query `q_j = MLP([hop_embed[j] ;
mean X over the previous hop's span ; g])` → pointer + STOP. Trained on 1–3 hops; 4 hops recorded only.
The output `relation_path` is literally the reasoner's route: `LOOKUP(mother) → LOOKUP(city) → STOP`. That is
the join point for the planned "one skills+router mechanism for parsing and for reasoning".

**Two facts in one sentence** (measured here: 12 of 150 in every panel). Rung 1: `multi`/`n_items>1` →
REPHRASE(one_thing_at_a_time). Rung 2: every pointer head is additionally conditioned on an item index `i ∈ {1,2}`
and called twice — the same loop trick. More than two → REPHRASE.

**Parameter count (estimate):** embedding 145k + input maps 6k + skills 111k + router 0.1k + act/flags/items 14k +
slot queries 1k + hop loop 46k + relkey/reltype 9k ≈ **0.33M**.

**Loss.** Sum of cross-entropies (act, n_items, each pointer over positions, relkey, reltype) + binary
cross-entropies (flags, stop). AdamW, lr 2e-3 cosine, batch 128, 12,000 updates. One temperature scalar per head
is fitted on the calibration panel afterwards (pre-registered; it only rescales confidence).

### B.4 Decoding into the contract's action schema (software)

The decoder emits exactly the item object that `fable_listening_english.py` already validates
(`act, subject, relation_path, relation_surface, value, value_kind, alias, canonical, choice, text, confidence`
+ `unsure, unsure_reason`), so the learned ears are a **drop-in replacement for the Qwen call** behind the
unchanged validator, `render_item`, `confirm_before_write_policy` and `Listening.hear`. No existing file is edited;
a new adapter script imports them.

- **Strings are substrings.** `subject = utterance[char_start(start_tok) : char_end(end_tok)]`. Byte-exact copy.
  Spans ≤ 4 tokens, end ≥ start, slots may not overlap.
- **Pronouns by table:** a SUBJ pointer landing on `i/me/my` → `Ben`; on `you/your` → `self`; on `she/he/they/her/
  his/their` → REPHRASE(who_is_pronoun). (Same convention as the Qwen ears.)
- **Required slots per act** (else REPHRASE): teach/correct = SUBJ + exactly 1 hop + VAL · ask = SUBJ + 1–8 hops ·
  forget = SUBJ + 1 hop · alias = ALIAS + CANON · person = SUBJ · pick = CHOICE ∈ pending ids · yes/no only if
  pending · quote = whole utterance as `text`, writes nothing.
- **`value_kind` is not learned.** It comes from the relation's declared type in the notebook (mother → person,
  city → literal). For an OPEN relation: literal, unless the value resolves to a known entity → ECHO.
- **Relation canonicalisation: the two-key rule.** Key 1 = the learned `relkey` head. Key 2 = a plain
  relation-wording table, seeded from the existing `RELATION_MAP` and stored beside the notebook.
  Both agree → eligible for EXECUTE. Table has the wording but the head disagrees → ECHO with the table's key.
  Table lacks the wording, head proposes key K → ECHO ("By 'resides in' do you mean where someone lives?"); on
  *yes* the wording is **added to the table**. Head says OPEN → new key = snake_case of the pointed words, ECHO the
  first time, then `declare_relation`. So a silently executed write always uses a wording Ben has already
  confirmed, and new wordings are learned by teaching into the notebook, not into weights — the project's own
  philosophy applied to vocabulary.
- **Touching-names rule.** If two different slots' spans are adjacent with no lexicon token between them
  ("you can call José Luis Pepe" — measured here, a round-2 miss) nothing in the sentence says where one name
  ends, so the verdict is forced to ECHO unless `known_alias` marks one side.

### B.5 Confidence, abstention, clarification

Three verdicts: **EXECUTE** (do it), **ECHO** ("Did you mean: Mira's city is Porto?" → yes/no through the existing
pending mechanism), **REPHRASE(reason)** with reason ∈ {not_sure, too_long, one_thing_at_a_time, who_is_pronoun,
leftover_words}; the reason picks the mouth's reply so Ben knows how to fix it.

`confidence = min( p(act), every required pointer's p(start)·p(end), every hop's p·(1−p_stop) and the final p_stop,
p(relkey), 1 − max(p_negation, p_hypothetical, p_reported) for write acts )`. Minimum, not product: a parse is
only as good as its weakest link, and the weakest link is printable for debugging.

A write is EXECUTED only if **all five brakes** release:
1. act ≠ unsure/multi/quote (trained on ≈ 16 % deliberately unparseable, trap, and too-rich sentences);
2. `confidence ≥ τ_exec`;
3. **agreement**: three ears trained from different seeds decode to the *identical* item (a deep ensemble — the
   cheapest reliable cure for a single network's over-confidence on unfamiliar input; 3 × 0.33M is still tiny);
4. **leftover check**: every opaque token lies inside a pointed span. "Mira lives in Porto with Zed" leaves `Zed`
   unexplained → REPHRASE(leftover_words). An unknown content word can never be silently dropped;
5. the existing deterministic validator accepts it (copy constraint, negation/hearsay/hypothetical guards).

Otherwise: if brakes 1, 4, 5 hold and `confidence ≥ τ_echo` and at least 2 of 3 ears agree → ECHO the majority
item; else REPHRASE. **Alias items always ECHO** (existing policy, keeps the reversed-nickname failure from ever
being silent). A `teach` that contradicts a stored value is already stopped by the notebook's CONFLICT status.

**Thresholds are set by a rule fixed in advance**, on a calibration panel disjoint from every test panel:
`τ0` = smallest value giving 0 wrong EXECUTED writes on calibration; `τ_exec = 1 − (1 − τ0)/2` (halve the allowed
doubt); `τ_echo = 0.5`. **Statistics honesty:** 0 errors in N trials only bounds the true rate below about 3/N at
95 % confidence ("rule of three"). 0/150 means "under 2 %"; 0/3,500 means "under 0.09 % *on sentences like the
test set*". That is why rung 1 uses thousands of generated sentences and rung 2 adds natural ones.

### B.6 What is conventional, exactly

| Component | Why unavoidable | Size | How it stays English-only |
|---|---|---|---|
| Word-embedding table | a word id must become numbers somehow | 3,020 × 48 = 145k | rows exist only for common lower-case words; names and places have no row |
| Dot-product pointer read (one softmax over positions per slot) | copying needs "which position?" as an output; it is the content-addressed twin of 43G's soft choice of place | ≈ 1k + 46k hop loop | outputs positions only |
| RMSNorm, AdamW, cross-entropy | standard training plumbing | — | — |

No self-attention layers, no autoregressive text decoder in the ears, no pretrained weights. A same-size
**BiGRU tagger** with the same heads is built as the yardstick arm in rung 1; it is also the named fallback: if the
tape ears fail where the BiGRU passes, the BiGRU (≤ 0.4M, same delexicalised input, same pointer outputs) becomes
the "clearly-justified minimal conventional component" and Ben is told so in plain words.

---

## C. MOUTH design

### C.1 Starting point: the mouth already exists and is perfectly truthful
`Result.say()` in the contract renders every status through a fixed template ("I don't know Ana's city."). That
is a correct mouth with zero learned weights. A learned mouth is worth building only for what templates cannot do:
say "Mira's mom **lives in** Porto" instead of "Porto.", use the wording Ben used, vary phrasing, and — later —
pick up new phrasings during sleep. So the learned mouth is an **upgrade with a permanent safety net**: any
doubt → the template is said. The mouth's equivalent of "please rephrase" is "say it the boring way".

### C.2 Input: a record with the strings held back
Software splits the reasoner/notebook `Result` plus the question item into two parts.

*Closed-class part (enters the network), all small integers:* `status` (the 10 contract statuses + ECHO +
REPHRASE-reason), `speech_act ∈ {answer, saved, confirm_q, conflict_q, which_q, dontknow, rephrase}`,
`person ∈ {about_ben→"you", about_self→"I", third}`, `n_hops ∈ 1..8`, per hop `relkey ∈ 41` and `reltype ∈ 2`,
`source ∈ {taught, inferred, sleep-derived, web-verified}`, `multi_answer ∈ {0,1}`.
Encoded as `c ∈ R^96` = sum of one learned embedding per field (hop fields get a hop-index embedding added).

*Slot table (never enters the network):* `{<S>: "Mira", <R1>: "mom", <R2>: "lives in", <V>: "Porto", <OLD>, <NEW>,
<NAME>, <CHOICES>}` — exact strings from the record; `<R·>` is the wording Ben used when he taught the fact
(stored as `raw`/relation surface), falling back to the canonical key's default wording.

### C.3 Network: a causal tape writer
Output alphabet = **mouth lexicon** (≈ 400 function and relation words, a subset of the ears' lexicon, embedding
rows tied to the ears' table) + 9 slot symbols + EOS ≈ 410 symbols. Output tape `Y`, length ≤ 24:
`Y0[t] = W_p·E[y_{t−1}] + c`. Bank of **16 causal skills** of the same gated-transport form as B.2, offsets
`δ ∈ {−6..0, FIRST}`, 3 stages, router `3×16 = 48` gates; next-symbol logits through the tied embedding.
≈ **0.1M parameters** (estimate). Greedy or beam-4 decoding with two hard masks: a slot symbol absent from the
slot table has probability 0; EOS is blocked until each mandatory slot for this speech act has appeared exactly once.

Then software: paste strings into slot symbols; detokenise (`Mira 's` → `Mira's`); capitalise the first letter;
append fixed safety suffixes that must never be left to learning (the contract's "(I read that online; you didn't
tell me.)" for `web-verified`).

### C.4 Why it cannot state anything outside the result record — four locks
1. **Alphabet lock (by construction).** The network's output symbols are function words and slot marks. It has no
   symbol for "Porto", "Paris", "blue whale" or any name. A content word can reach the reply only by being pasted
   from the slot table. A unit test asserts: every token of every reply ∈ mouth lexicon ∪ slot-table strings.
2. **Slot-use lock (software).** Every mandatory slot exactly once; no slot not in the record.
3. **Ears-loop lock (learned, independent weights).** Copy-only does not stop "Porto's mom lives in Mira" (right
   words, wrong places) or a dropped "don't". So the finished sentence is parsed by the frozen three-copy ears
   (with I/you swapped, because the mouth's "your" means Ben). It must decode to the same `(subject,
   relation_path, value)` for answer/saved/conflict replies, or to act `dontknow` with the same subject and path
   for MISSING_FACT. Disagreement or low ears confidence → lock 4. People appear to monitor their own speech the
   same way (section J).
4. **Template fallback.** `TEMPLATES[status]` from the contract, unchanged. Statuses with no proposition
   (DUPLICATE_OK, NOT_ALLOWED, BAD_REQUEST, AMBIGUOUS, UNKNOWN_ENTITY, REPHRASE reasons, small-talk reflex line)
   stay template-only in v1 — a learned mouth adds nothing there.

Small talk in v1: one fixed reflex line ("I can remember things you tell me and answer questions about them.").
No learned chit-chat; that was design 24's "thinker", which is parked, not part of this step.

---

## D. Shared weights? Pretraining?

**Sharing.** Share the **lexicon embedding table only** (the mouth's 400 words are rows of the ears' table).
Keep the two skill banks separate in v1, for a reason that matters more than parameter count: the ears are the
mouth's checker (C.4 lock 3), and a checker that shares the speaker's weights shares its mistakes. Sharing skill
banks is a later one-change experiment (the interesting version: mouth skills = ear skills run causally).

**Is language-model pretraining needed for this narrow job? Probably not; test it once, as one change (rung 4).**
- Against: slot-filling systems of this size have long been trained from scratch on a few thousand labelled
  sentences (from memory: ATIS/SNIPS). Our domain is narrower and our labelled data is unlimited (generated).
- For: the one thing labelled data cannot give is knowledge of words and constructions that never occur in any of
  our frames. A model that has read a lot of simple English should place "mum" near "mom" and "resides" near
  "lives", which is exactly what held-out paraphrase families test.
- If used, it must be **delexicalised masked-word prediction on the ears' own encoder**: run the same tokeniser
  over the corpus (so "Paris is the capital of France" becomes `OPQ#3 is the capital of OPQ#1`), hide 15 % of the
  *lexicon* tokens, predict them from the tape. Opaque tokens are never predicted. The fact cannot be learned
  because the network never sees which opaque word was which across sentences.

| Item | Value (estimates; benchmark 200 updates before any wave) |
|---|---|
| Model | the ears' encoder widened to d = 128, K = 32 skills, embedding 3,020×64 ≈ **0.8M parameters** |
| Data | TinyStories (≈ 470M tokens, from memory) sampled to 150M tokens + all Simple English Wikipedia sentences ≤ 32 tokens (tens of millions of tokens, from memory) ⇒ **≈ 200M tokens**, one pass |
| 5070 Ti | tiny models are launch-bound; assume 0.3–1.0M tokens/s ⇒ **≈ 4–12 minutes** per seed; three seeds can share the card |
| Mac | ≈ 70k tokens/s at the quoted 0.03 s/update ⇒ 100M tokens ≈ 24 min (a half-size run fits the 30-minute rule) |
| English-only checks | (1) output/ input tables contain no proper-noun rows (assert on the lexicon file); (2) fact-leak probe, recorded: masked-word loss on true vs. swapped simple statements built only from lexicon words; (3) the end-to-end "empty notebook ⇒ every question answered *I don't know*" test in rung 5 |

Honest footnote that must travel with any claim: TinyStories is model-written text, so English learned from it is
learned second-hand (already accepted as D9 of design 24). Residual common-sense among *common* words ("fish
live in water") can enter the embedding; it cannot be spoken as a fact because of the alphabet lock.

---

## E. Training data plan

### E.1 Sources
1. **Frame grammar (templates).** A *frame* is a sentence with blanks: `"{S}'s {R} is {V}."`. Start from the
   existing sealed table in `fable_talker24_dialogues_frames.py` (read here: ≈ 450 core frames in 9 families with
   construction tags and a sealed 80/20 L1/L2 split), re-targeted from its toy world (friend/gift/prize/charm) to
   the LISTENING schema: 40 canonical relations × 3–8 wordings, OPEN relations from a noun pool, the 13 acts,
   fillers ("btw", "ok so", "small update:"), texting style, Markdown wrappers.
2. **Agent-written paraphrase frames.** Subagents write new frames *with placeholders* per act × construction.
   Every frame is machine-checked (each placeholder exactly once; instantiates; label derivable) before use.
3. **Logged real sentences.** `fable_listening_english.py` already logs every utterance that passes through it.
   Only rows whose line Ben accepted (executed without undo, or echo answered *yes*) are used, for training only.
4. **The three existing 150-sentence panels.** heldout150 becomes a dev/calibration panel (it was already used
   for tuning). heldout2 and heldout3 are reported as "unseen by the model, seen by the designers".
5. **Open corpora** (TinyStories, Simple English Wikipedia): only for building the lexicon and for rung 4's
   optional delexicalised pretraining. Never as a source of facts or labels.
6. **LLM-written paraphrase frames (Qwen)** — only if Ben says yes (E.5).

### E.2 Sizes
| Split | Size | Made from | Used for |
|---|---|---|---|
| TRAIN | generated on the fly; ≈ 200,000 distinct sentences per run (≈ 1.8M tokens) | ≈ 600 train frames × train names × train values | fitting |
| DEV | 5,000 | train frames + 60 dev frames, dev names | early stopping, debugging |
| CAL | 5,000 + heldout150 | dev frames, dev names | temperature and τ (rule in B.5) — nothing else |
| T-seen | 2,000 | **train frames, held-out names/values** | isolates the name effect |
| T-new | 3,000 | **held-out frames (≈ 150), held-out names/values** | the main generalisation number |
| T-far | 1,000 | **held-out construction types** (e.g. every cleft "it is in {V} that {S} lives", every passive) | recorded, not gated: how far does it reach |
| T-trap | 1,000 | negation, hypothetical, hearsay, statement-shaped questions, leftover words, 3+ facts | must write nothing |
| T-hard-names | 500 | names that are lexicon words (Rose, Will, May), all-lower-case names, 2–3-word names, O'Brien / Jean-Luc / José / Zoë, numbers and multi-word values ("Cedar Books") | the residual name risk |
| N4 | 150 | fresh natural-style panel written by an agent that has never seen the frame table, sealed before rung 2 trains | the natural-language gate |
| MOUTH-test | 3,000 records | held-out names, held-out relation wordings, all statuses | rung 3 |

Act mix in TRAIN (matches the panels, measured here, with traps over-weighted): teach 28 %, ask 24 % (1-hop 12,
2-hop 8, 3-hop 4), correct 8 %, alias 6 %, person 4 %, forget 4 %, quote/traps 12 %, yes/no/pick/undo 5 %,
smalltalk 5 %, unsure (gibberish, too rich, pronoun-only) 4 %.

### E.3 What "held out" means, enforced by code before training
- **By frame family, not by sentence.** A family = one frame + its trivial variants (contraction, tense, final
  punctuation). Splits are by family id; test asserts: no template equal after stripping placeholders,
  punctuation and case (the talker24 test already does this), **and** token-set Jaccard similarity < 0.8 between
  any test skeleton and every train skeleton.
- **By construction type** for T-far: the construction tag never appears in TRAIN.
- **Names and values:** 2,000 train / 500 dev / 500 test, disjoint, from a syllable generator plus a public
  first-name list; cities, employers and colours likewise. Because names are opaque to the network, held-out
  names test the *tokeniser, lexicon and decoder* — which is where name bugs can actually live.
- **Relation wordings:** 20 % of wordings per canonical relation and 20 % of OPEN-relation nouns are test-only.
- **Fillers:** 3 of 15 sentence-openers test-only.
- All test panels are generated, hashed and sealed before the first training run of the rung that uses them.

### E.4 The mouth's data is the ears' data, reversed
Every generated declarative pair (sentence, item) is also a (record → skeleton) pair: replace the slot strings in
the sentence by slot symbols. Add status replies (3–6 frames each for saved, conflict_q, confirm_q, dontknow).
One generator, two directions, one sealed split.

### E.5 Ben's open question: may Qwen (or another LLM) write training sentences? — **Recommend YES, with four fences**
| | Pros | Cons |
|---|---|---|
| **Allow (fenced)** | Widest variety of real phrasing for almost no work; free on BensPC; no weights are borrowed; consistent with the already-accepted "model-written text" footnote (TinyStories is the same kind of thing) | English is learned second-hand and must be footnoted; a paraphrase can silently change meaning ("I think {S} lives in {V}" is hearsay, not a fact) → label noise → the one thing that can cause bad writes; LLM style is samey |
| **Forbid** | Cleanest story ("no other model touched it"); no label-noise channel | Fewer phrasings → lower coverage on natural sentences; more agent/Ben hours; note agents (Claude/GPT) writing frames are LLMs too, so the pure version is "Ben and templates only" |

Fences: **(1)** the LLM rewrites *frames with placeholders* — it never sees or writes a name or a fact;
**(2)** every new frame must pass a machine filter: placeholders intact, and when instantiated, the existing
validated Qwen-ears pipeline parses it to the *same* item as its source frame, else it is dropped;
a 200-frame human/agent audit must show ≤ 2 % meaning changes or the batch is discarded;
**(3)** no gated test panel is written by the same model + prompt that wrote training frames;
**(4)** the claim footnote "training sentences partly written by another model; all weights ours" is mandatory.
And it is measured rather than assumed: rung 4 has an arm with and without them.

---

## F. The ladder — five rungs, smallest first

House rules for every rung: marks below are copied into a `PASSMARKS.md`, hashed, and the hash committed before any
gated panel is scored; every seed is printed; counts are integers; a rung's PASS needs **3 of 3 seeds**; 2 of 3 is
PARTIAL and licenses no claim; a 200-update smoke test measures seconds/update before the wave and the wave is
re-planned if the estimate is off by > 2×; one CPU thread per process so 8 runs go in parallel. Within a rung,
arms differ from arm A by exactly one thing. Definitions used in marks: **correct** = the decoded item equals the
gold item exactly; **silent wrong write** = a wrong write item (teach/correct/forget/alias/person/undo) with
verdict EXECUTE; **echoed wrong write** = the same with verdict ECHO.

### Rung 1 — Tape ears on single-fact sentences (Mac CPU, no Qwen needed)
- **Built:** tokeniser + lexicon; the re-targeted frame generator with sealed splits (E.2 except N4); the B.2–B.3
  network, 1 item, ≤ 3 hops; the decoder and five brakes (brake 3 uses the arm's own three seeds; brake 5 is the
  existing validator imported read-only); the scorer.
- **Arms:** **A** tape ears (skills + router). **B** same-size BiGRU tagger, same inputs and heads (yardstick).
  **C** = A but names visible (out-of-lexicon words hashed into 8,192 embedding rows instead of `OPQ#k`) —
  descriptive: shows what the opaque trick buys.
- **Seeds:** 3 per arm, fresh (4301–4303). 9 runs.
- **Wall-clock (estimate):** 12,000 updates × ≈ 0.02 s ≈ 4–6 min per run; 9 runs on 8 cores in two batches +
  scoring ≈ **15–20 min**.
- **Marks (arm A gated; B, C recorded):**
  - R1-SAFE (primary): silent wrong writes over T-seen + T-new + T-trap + T-hard-names (6,500 sentences) = **0**,
    and items written from T-trap = **0**.
  - R1-ECHO: echoed wrong writes ≤ 65 (1.0 % of 6,500).
  - R1-SEEN: T-seen correct ≥ 1,940/2,000 (97 %), of which EXECUTE-correct ≥ 1,800 (90 %).
  - R1-NEW: T-new correct ≥ 2,400/3,000 (80 %), of which EXECUTE-correct ≥ 1,950 (65 %).
  - R1-NAMES: T-hard-names correct ≥ 300/500 (60 %) (its safety is inside R1-SAFE).
  - R1-ASK: wrong EXECUTED questions ≤ 25 of T-seen + T-new (0.5 %).
  - Recorded only: T-far; 4-hop questions; router gate histogram (dead or saturated gates); per-family misses.
- **Decisions licensed:**
  - A passes → tape ears go to rung 2. Allowed sentence: "A 0.33M-parameter skills-and-router model turns
    generated single-fact English into notebook actions with no silent wrong write on 6,500 held-out-wording,
    held-out-name test sentences (3/3 seeds)". Not allowed: anything about natural English.
  - A fails coverage, B passes → one registered fix to A (add a fifth stage *or* widen offsets to ±6, chosen in
    advance by which panel failed); if it still fails, adopt the BiGRU encoder as the justified conventional part.
  - A and B both pass SAFE but fail R1-NEW → the bottleneck is wording variety, not architecture → bring E.5
    (Ben's decision) and rung 4 forward.
  - Any arm shows a silent wrong write → list every one; fix the *brake* that should have caught it (one change);
    rerun on fresh seeds and regenerated panels. Two failed fix cycles → abandonment test G.13(ii).
  - C is expected to match A on T-seen and be worse on held-out names; if it is *not* worse, say so plainly —
    the opaque trick would then be justified by ruling 2 alone, not by accuracy.

### Rung 2 — Drop-in replacement for Qwen, on natural panels
- **Built:** adapter script emitting the existing JSON item schema into the unchanged validator / confirmation
  policy / `Listening.hear`; two items per sentence (item-index loop); pending acts (yes/no/pick/undo);
  relation-wording table with the two-key rule; texting-style and Markdown augmentation; panel N4 sealed first.
- **Arms:** **A** one ears copy + τ. **B** three-copy agreement + τ (the one change = brake 3).
- **Seeds:** 3 per arm (arm B = 3 disjoint triples, 9 models). Wall-clock ≈ **20 min** in two 8-core batches.
- **Marks (gated on N4; heldout2, heldout3 and rung-1 panels re-scored and recorded):**
  - R2-SAFE: silent wrong writes on N4 = **0** under the *strict* round-1/2 definition; echoed wrong writes ≤ 4.
  - R2-TRAP: all trap sentences in N4 write nothing.
  - R2-COV: N4 correct (EXECUTE or ECHO) ≥ **90/150**; "useful" level ≥ 120/150 is recorded, not gated.
    For reference (measured here) Qwen-27B scored 126, 141, 140 of 150 with 3, 1, 0 silent wrong writes.
  - R2-REGRESS: R1-SAFE still 0 on the rung-1 panels.
- **Decisions:** B passes → our ears become the default in the chat loop; Qwen runs only in *shadow* (its parse
  is logged for comparison, never used). Safe but under 90 → stay on Qwen for daily use, go to rung 4. Any silent
  wrong write → stop, itemise, no swap. If A alone also passes, keep B anyway (it is the cheaper insurance).

### Rung 3 — The mouth (can run in parallel with rung 2; uses rung-1 ears as checker)
- **Built:** record splitter, causal tape writer (C.3), paste/detokenise, the four locks, an oracle checker
  (skeleton ∈ the generator's set of valid skeletons for that record; anything else is "novel" and hand-audited).
- **Arms:** **A** learned mouth with ears-loop lock. **B** same without the ears-loop lock (shows what it
  catches). Baseline: contract templates. 3 seeds each; ≈ **10–15 min**.
- **Marks on 3,000 MOUTH-test records:**
  - R3-FAITH (primary): replies emitted that the oracle or the audit marks unfaithful = **0**.
  - R3-ALPHABET: tokens outside (mouth lexicon ∪ record strings) = 0 (a unit test; failure = bug, VOID).
  - R3-FALLBACK: template fallback used on ≤ 450/3,000 (15 %).
  - R3-NOVEL: novel skeletons ≤ 150 (5 %), every one audited; R3-GRAMMAR (recorded): 300 sampled replies judged
    by two independent agents, target ≥ 285 acceptable.
- **Decisions:** pass → learned mouth on, template net stays forever. FAITH fails in A → mouth stays template-only
  and the project loses nothing but style. B ≫ A in unfaithful replies is the evidence that lock 3 earns its keep.

### Rung 4 — Two one-change tests for wording coverage (two waves, each < 30 min)
- **Arms vs. rung-2 recipe A0:** **P** = + delexicalised masked-word pretraining (section D; wave 1 pretrains on
  the 5070 Ti, wave 2 fine-tunes on the Mac). **Q** = + Qwen-written frames under the E.5 fences (only with Ben's
  yes). 3 fresh seeds each; test panels regenerated and re-sealed; N5 = a second fresh natural panel.
- **Marks:** safety marks of rung 2 unchanged (0). Adopt an arm only if T-new correct rises by ≥ 150/3,000
  (5 points) **and** N5 correct rises by ≥ 8/150, paired by seed, in 3/3 seeds. Otherwise the simpler recipe stays.
  Recorded: fact-leak probe for P; label-noise audit for Q.
- **Decisions:** adopt P, Q, both (then one confirmation run of P+Q), or neither. Neither + coverage still
  under 90/150 → abandonment test G.13(iii).

### Rung 5 — All-own-weights conversation (evaluation only, ≈ 10 min)
- **Built:** the full loop with Qwen unplugged: ears → LISTENING → notebook → hop loop → mouth. 30 sealed scripted
  dialogues × 10 turns (agent-written: new names, 2-hop questions, corrections, nicknames, unknowns, traps, one
  simpler rephrase per turn for when the system asks). Plus one free chat by Ben, recorded, not gated.
- **Marks:** wrong facts in the final notebook across 30 dialogues = **0**; unfaithful replies = **0**;
  final notebook complete in ≥ 24/30 dialogues; with an empty notebook, 20/20 world-fact questions ("what is the
  capital of France?") answered with a don't-know status; rephrase requests ≤ 25 % of user turns (recorded).
- **Decision:** pass → Qwen leaves the demo path. Allowed sentence: "Every weight that listens or speaks was
  trained from scratch by Ben; it starts knowing no facts, stores what it is told, and said nothing in these 300
  turns that was not in its notebook." The training-data footnote (E.5) goes with it.

---

## G. Failure modes, how each shows up in the numbers, and what would make me abandon this

| # | Failure | Signature in the numbers | First response (one change) |
|---|---|---|---|
| 1 | Over-confident wrong parse of an unfamiliar construction | R1-SAFE clean on T-seen but > 0 on T-new / N4; the wrong items have confidence near 1.0 in a single copy | rely on agreement (brake 3); if all three agree on the wrong item, the construction goes into the trap/unsure training class |
| 2 | Coverage collapse on natural text | N4 correct < 90 with REPHRASE clustered in a few constructions (print misses by construction tag) | more frames for those constructions; rung 4 |
| 3 | Names that are English words (Rose, Will, May, Art) or lower-case names | T-hard-names far below T-new; misses have `in_lexicon=1` inside the gold span | `known_alias` feature already helps for known people; raise lexical dropout so in-lexicon words are often seen as opaque |
| 4 | Hop order reversed on "of"-chains | 2- and 3-hop ask accuracy ≪ 1-hop; wrong paths are exact reversals | more mixed-order frames; safety net: the mouth's answer restates the path ("Mira's mother's city is …"), so Ben sees a mis-heard question |
| 5 | Tape ears under-fit where BiGRU fits | arm A train accuracy < 99 % while B ≥ 99 % | the registered fix in rung 1; then the named fallback |
| 6 | Router / address saturation (the 43G-v1 disease) | gate histogram piled at 0 or 1 early; skills with zero gradient norm; seed-to-seed fit failures | already bounded (10·tanh); lower the bound to 5 |
| 7 | Nickname direction reversed | echoed-wrong rate on alias items > 5 % | never silent (always ECHO); add frames; use `known_alias` asymmetry (the known side is the canonical) as a decoder rule |
| 8 | Touching names ("call José Luis Pepe") | span-boundary errors only where two opaque spans touch | already forced to ECHO |
| 9 | Two-fact sentences mangled (subject dropped in the second clause) | item-2 SUBJ pointer errors on elided-subject frames | restrict rung 2 to repeated-subject forms; elided → REPHRASE |
| 10 | τ calibrated on generated text does not transfer | CAL clean, N4 silent wrong write with confidence ≥ τ_exec | CAL must include natural sentences (heldout150 + logged); raise margin rule from /2 to /4 |
| 11 | Leakage between splits | T-new ≈ T-seen to the decimal; Jaccard assertion failing | VOID the run; fix the split; regenerate |
| 12 | Mouth slot swap or lost negation passing the ears-loop (correlated error) | R3-FAITH > 0 in arm A; the same record fails in ears parse of the *gold* sentence | keep banks unshared; add the oracle skeleton whitelist as a fifth lock for the affected speech act |
| 13 | Pretraining leaks common-sense | fact-leak probe gap grows with pretraining tokens | harmless to truthfulness (alphabet lock); record and disclose |

**What would make me abandon (pre-committed):**
- **(i) Partial — drop the skill-bank encoder, keep everything else:** arm A fails rung 1 after its one registered
  fix while the same-size BiGRU passes. The honest report is then "pointing + opaque names + brakes work; our
  tape encoder did not beat a 1997-style recurrent net at this job."
- **(ii) Drop learned ears for writes:** after two fix cycles no arm reaches 0 silent wrong writes with at least
  50 % EXECUTE-or-ECHO coverage on T-new. Fallback options to put to Ben: keep Qwen as placeholder longer, or
  define a small **controlled English** ("Fable English": a documented set of sentence shapes) parsed by rules,
  with learned ears only for questions, where a mistake costs a wrong answer rather than a wrong memory.
- **(iii) Ceiling:** rung 4 shows that neither 10× more frames nor pretraining moves N-panel coverage above
  90/150. Then narrow supervised ears have hit their limit and only a much larger pretrained language model
  would help — which collides with ruling 1. That is a decision for Ben, not something to slide into.
- **(iv) The design is pointless if** templates + a rule parser (the talker24 reference parser style) match the
  learned ears on N4. A rule-parser baseline on N4 is therefore recorded in rung 2. If rules win, say so.

---

## H. How SLEEP meets the ears and mouth — FUTURE WORK, nothing here is built or promised

All of this must obey the sleep ruling: automatic and mathematical; the model never proposes a rule or chooses
what to store.

1. **Free labels from rephrasing.** Fixed pairing rule: a REPHRASE at turn *t*, followed at turn *t+1* by an
   EXECUTED item whose every slot string also occurs in the failed sentence ⇒ (failed sentence, that item) is a
   training episode. The copy constraint does the alignment; no model judges anything. Echo-*yes* turns give
   episodes the same way.
2. **A frequent phrasing becomes a routed skill.** When ≥ 20 episodes share a skeleton the ears could not parse,
   sleep trains — exactly as in 43H — a small new route (gate numbers over the frozen ear skills) and, only if
   routing alone cannot fit, one new **rank-4** skill (43E's measured result: rank-limited updates generalise
   better from few episodes). Old skills stay frozen, so old sentences cannot get worse by construction.
3. **Install gate.** 4-fold cross-validated exact match ≥ floor (43H's rule, which correctly *rejected* a bad
   install, measured here) **and** the full sealed safety panel still shows 0 silent wrong writes. Else rejected
   and logged.
4. **The mouth learns Ben's phrasing.** Ben's own teach sentences, turned into skeletons, are candidate mouth
   routes by frequency count; installed only if the ears-loop check passes on all of them.
5. **Already available without sleep (not future):** new relation wordings are learned by echo-*yes* into the
   relation-wording table (B.4). That is notebook learning, not weight learning.
6. **One mechanism.** Ears output a route (`LOOKUP(mother) → LOOKUP(city) → STOP`), the reasoner executes routes,
   sleep installs routes. If the skills+router reasoner arrives, parsing, reasoning and consolidation share one
   currency. Open risk: whether 43H's 20-episode result survives *learned* addressing is being tested now; this
   section inherits that answer.

---

## I. Difficulty, compute, parallelism — estimates, not promises

| Rung | Work | Calendar (part-time, incl. one fix cycle) | My pass probability (to be hashed into the predictions ledger) |
|---|---|---|---|
| 1 | generator re-target + frames (agents), tokeniser/lexicon, model, scorer | 1.5–2 weeks | SAFE 0.75 · R1-NEW 0.6 · arm A ≥ arm B 0.5 |
| 2 | adapter, 2-item loop, pending acts, N4, rule baseline | 1–1.5 weeks | SAFE 0.6 · COV ≥ 90/150 0.5 |
| 3 | mouth + locks + oracle | 1–1.5 weeks (parallel with 2) | 0.8 |
| 4 | pretraining arm, Qwen-frame arm | 1 week | adopt P 0.4 · adopt Q 0.6 |
| 5 | dialogue scripts, end-to-end scoring | 1 week | 0.5 given 2 and 3 passed |

**Total: about 5–7 weeks if things go well, 8–10 realistic.** The hard part is not the network; it is writing
enough *varied* frames and keeping the splits honest. The most likely disappointment is rung 2 coverage on natural
sentences, not safety.

**Compute.** Rungs 1, 2, 3, 5 run entirely on the Mac CPU (each wave ≤ 20 min, estimate). Rung 4's pretraining is
≈ 4–12 min per seed on the 5070 Ti. **Cloud: $0 planned**; the $27 stays untouched. Disk: TinyStories + Simple
Wikipedia ≈ 2–3 GB (from memory; confirm before downloading).

**Parallel tracks.** (a) frame writing by agents ∥ model/scorer code; (b) rung 3 (mouth) ∥ rung 2 (ears) once
rung 1 ears exist; (c) seeds across 8 cores; (d) the 43-series learned-addressing work continues independently
and plugs into B.2 as one change; (e) lexicon building and corpus download ∥ everything.

---

## J. Prior work — all from memory; **verify before citing**

- *Pointer Networks* — Vinyals, Fortunato, Jaitly (2015): outputs that are positions in the input. The ears' core.
- *CopyNet* — Gu et al. (2016); *pointer-generator* — See, Liu, Manning (2017): copying words instead of generating them.
- *Seq2SQL* / *SQLNet* — Zhong et al. (2017), Xu et al. (2017): semantic parsing with pointer outputs into a fixed sketch.
- *Building a Semantic Parser Overnight* — Wang, Berant, Liang (2015): canonical templates + paraphrases as training data; *Data recombination* — Jia & Liang (2016). Closest to the data plan.
- *Language to Logical Form with Neural Attention* — Dong & Lapata (2016).
- Joint intent + slot filling on ATIS/SNIPS — Mesnil et al. (2015), Liu & Lane (2016), Goo et al. (2018): small recurrent taggers trained from scratch reach mid-90s slot F1. Basis for "pretraining probably unnecessary".
- Delexicalisation — Henderson, Thomson, Young (2014, dialogue state tracking); Wen et al. (2015, SC-LSTM generation); TRADE — Wu et al. (2019, copy in state tracking). The opaque-word and slot-skeleton ideas.
- *Neural Module Networks* — Andreas et al. (2016): a parse chooses a layout of reusable modules. Cousin of "the question is a route".
- *Gated convolutional language models* — Dauphin et al. (2017); *ConvS2S* — Gehring et al. (2017): what the skill bank is mathematically. *Universal Transformers* — Dehghani et al. (2018): weight-tied stages. *Sparsely-gated mixture of experts* — Shazeer et al. (2017): routing.
- *TinyStories* — Eldan & Li (2023); *BabyLM challenge* (2023–24): small models, simple English.
- *SCAN* — Lake & Baroni (2018); *COGS* — Kim & Linzen (2020): sequence models fail on held-out *constructions*. The warning behind T-far and abandonment test (iii).
- Selective classification / reject option — Chow (1970), Geifman & El-Yaniv (2017); *Deep ensembles* — Lakshminarayanan et al. (2017); *On calibration of modern neural networks* — Guo et al. (2017). Basis for B.5.
- "Rule of three" for zero observed events — Hanley & Lippman-Hand (1983).
- *Attempto Controlled English* — Fuchs et al.: the controlled-English fallback. Levelt's *perceptual loop* theory of speech self-monitoring (1983/1989): the ears-check-the-mouth idea.

---

## K. Alternatives considered, and why each loses

| Alternative | Why it loses |
|---|---|
| Design 24's 33M transformer encoder/decoder around a 416-number "thought" | A stock seq2seq by Ben's later ruling 1; a generating decoder can mis-spell or invent names; hours of GPU per try instead of minutes; its typed-slot and copy-only ideas are kept here |
| Byte/character ears | 4× longer tapes, must *learn* that spelling is irrelevant, new-name safety becomes statistical. Worth revisiting only for typo tolerance |
| Word-piece (BPE) ears | name fragments get vectors (a fact-leak channel); spans over pieces are fiddly |
| Same-size BiGRU or 2-layer transformer tagger | Would very likely work; it is the yardstick and named fallback, but it has no callable skills for sleep to route over, so it is a dead end for section H |
| Fine-tune a small pretrained LM | not Ben's weights |
| Keep Qwen | 27B borrowed parameters; allowed only as a temporary placeholder |
| Rules only (regex grammar) | no learning, brittle outside its patterns; kept as a recorded baseline and as the honest "is learning buying anything?" check (G iv) |
| Mouth as a free text generator | cannot be made truthful at this size; the alphabet lock is the whole point |

## L. Decisions needed from Ben
1. E.5: may Qwen write *placeholder frames* for training, under the four fences? (Recommended yes. Rungs 1–3 proceed either way.)
2. Is it acceptable that the tokeniser, the lexicon file, the relation-wording table and the brakes are plain software around the learned parts? (Recommended yes: they are the "skull", and they are where the zero-bad-writes guarantee lives.)
3. Is a fixed reflex line for small talk acceptable in v1? (Recommended yes; learned chit-chat is a separate, later project.)
4. If the tape ears lose to the same-size BiGRU after one fix, do you accept the BiGRU as the minimal conventional encoder, or would you rather pause and rethink the skill design? (My recommendation: accept it for the demo path, keep researching the tape encoder on the side.)

