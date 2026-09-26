# Decide which facts a small chat reader should save (no code or file access needed)

You are an expert in LLM calibration, selective prediction, verifiers and information extraction. You have **no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer rather than guessing. Mark every claim as **shown by the data below**, **suggested**, or **untested**.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

Scope: this is only about the **chat fact-reader and its save gate**. My project has other parts (small synthetic "card" experiments, a simulated "village" world, a puzzle reasoner). Do not mix those in or borrow numbers from them.

## 1. What the system does

A personal assistant keeps a **notebook** of facts the user tells it ("my sister Lenka is 19"). A wrong saved fact is much worse than a missed one, because the assistant later states it as true. Missed facts can partly be recovered: the assistant may ask "I think you told me X, is that right?" and save only on a yes (I approved that wording).

**Reader.** MiniCPM5-1B (about 1.1B parameters) with a rank-32 LoRA, fine-tuned on about 50,000 labelled turns (about half synthetic, the rest LLM-written chat checked by a blind second labeller). For each user message it sees up to 6 earlier user turns plus the assistant's last reply, and greedily writes one JSON frame:
`{"act": "TEACH|ASK|...", "facts": [{"owner", "rel", "value", "mode"}], "ask": ...}`. `mode` is ASSERT / CORRECT (savable) or PLAN, HYPOTHETICAL, NEGATED, REPORTED, etc. (not savable). A plain-code compiler rejects structurally bad facts (value not in the text, "our/we" owners, and similar).

**Gate (today).** Each fact gets `conf` = the **minimum token probability** over the act tokens plus that fact's JSON tokens (greedy decode). A fact is saved if `conf >= T`, else it is held back. Each fact is released on its own. T was chosen on a dev set by the rule "smallest grid value with 0 wrong-save messages, else 0.995". No value ever reaches 0, so T = 0.995.

Hardware and rules: one RTX 5070 Ti (16 GB), rentals up to about $4 per job, and only models already downloaded (MiniCPM5-1B, Qwen3.5-2B, LFM2.5-1.2B). Every test set is sealed, written blind by one LLM agent, checked by a blind second labeller, and run **once**. One change per experiment, with pass marks fixed before the run. Median read time is about 1.4 s per message.

## 2. Results

### 2a. Newest reader on a sealed test (240 messages, 211 true facts)
Found = the greedy frame contains the fact in a savable mode (before the gate).

| Reader | Found | Saved right at T=0.995 | Held back (right) | Messages with a wrong save |
|---|---|---|---|---|
| Old reader (sees only the last reply) | 103 | 58 | 45 | 11 |
| New reader (sees 6 earlier turns) | 197 | 65 | 132 | 1 |

### 2b. New reader, dev sweep (1,311 messages, 1,053 true facts; "saved right" requires owner, relation and value to match)

| T | Saved right | Messages with a wrong save |
|---|---|---|
| 0.50 | 987 | 24 |
| 0.80 | 938 | 14 |
| 0.90 | 896 | 10 |
| 0.95 | 837 | 5 |
| 0.98 | 771 | 3 |
| 0.99 | 703 | 3 |
| 0.995 | 611 | 3 |

(Unsaved facts are not all lost. On an earlier 771-fact test, asking back about every held-back fact would have recovered 743/771, at the cost of 217 questions to the user.)

### 2c. A learned checker that failed (rd-371)
A second MiniCPM5-1B + LoRA answers "Does the user's chat turn state this fact? yes/no". Score = P(yes) from a softmax over the first "yes" and "no" tokens. Training: 22,498 rows. Yes = labelled true facts. No = code-made perturbations of the same turns: swapped owner and value, a different value, a different owner, a different relation, a non-saving mode shown as ASSERT, and "we" changed to "me". **Every training prompt was 450 characters or fewer.** The same reads from an older reader were scored two ways. For B, T was picked on dev by the rule "smallest value with 0 wrong messages, else the LARGEST grid value" (0.9999). The old gate's rule instead falls back to 0.995.

Dev (959 short messages, 761 facts): old gate at 0.995 saved 462 with 2 wrong messages. Checker at 0.95 saved 718 (3 wrong), at 0.999 590 (2 wrong), at 0.9995 529 (1 wrong), at 0.9999 400 (1 wrong).

Sealed test (240 messages, 426 facts, of which 342 were found by the reader):

| | Old gate 0.995 | Checker 0.9999 |
|---|---|---|
| Saved right | 106 | 15 |
| Messages with a wrong save | 2 | 0 |
| Long multi-fact messages: saved of 153 found | 38 | 1 |
| Trap messages (role swaps etc.): saved of 126 found | 53 | 8 |

### 2d. Confident dev errors (verbatim; dev data, not a test set; reads by the older reader from 2c)
- "Guess my favorite color is blue." The key says don't save (hedge). The reader saved it (me, favorite_color, blue) with min-token 0.99988, and the checker said yes with 0.99992.
- "Ada was born in May." Read as place_of_birth instead of date_of_birth; reader min-token 0.9973, checker P(yes) 0.9993.
- After the reply "Noted that Bram was born in Holt.", the user wrote "he grew up there but was born in Addison". The reader wrote (Bram, place_of_birth, Addison) with min-token 0.56 (held by the old gate), but the checker said yes with 0.9985; the key had no save for this row.

### 2e. Running now
The same new reader on a fresh sealed test (239 messages, 424 facts), one read scored at T=0.995 vs T=0.98. Pass: 0.98 saves at least 25 more right facts, at most 1 more wrong message, at most 3 of 239, and at most 1 save on a message with no facts. Proved wrong if 0.98 adds 3 or more wrong messages.

## 3. Where the project is heading
The memory is moving from typed relation facts to **plain-sentence notes** ("Lenka started at Orrin Labs in March"), found by meaning, each citing the chat turns it came from. So the gate should, if possible, generalise to "does the cited source support this sentence?", not only to (owner, relation, value) triples. Relation facts are a small part of what the assistant will do.

## 4. What I want from you
1. **Diagnosis.** Why does min-token confidence give this curve? Why does no bar reach zero wrong saves, and is "0 wrong on dev" even a sensible target given label noise (e.g. "Guess my favorite color is blue" is arguably a hedge)? What wrong-save rate can a test of this size certify? (I know 0 errors in 299 bounds the rate below 1% at 95%.)
2. **The checker.** Beyond the lopsided threshold rule and short-only training, what else in its design (negatives, prompt, scoring) would make it hold back almost everything on long messages?
3. **Ranked gate designs** that fit a 1B model on one 16 GB GPU. Consider at least: sequence-level vs min-token confidence; agreement across k sampled reads; calibration on dev (temperature or isotonic); conformal / risk-controlling thresholds for a target wrong-save rate; a checker trained with long contexts and harder negatives (hedges, corrections, wrong relation); per-kind bars; routing doubtful facts to ask-back instead of dropping them. For each, say what it costs per message and which of my failures it addresses.
4. **A fair rule for choosing the bar**, one I can apply the same way to every arm, and say how to keep it honest when dev data is small.
5. **One next experiment at a time** (at most three, in order). Each is one change, with pass marks fixed in advance and the result that would prove it wrong. Use my numbers above as the baseline.
6. Label every claim **shown / suggested / untested**.
7. **Plain-language summary for me** (a high-school senior): five to eight sentences on what is going wrong and what to try first, without jargon.
