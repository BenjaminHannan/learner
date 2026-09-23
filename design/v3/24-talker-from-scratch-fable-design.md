# 24 — A talker built from scratch around a numeric "thought": decision document

**Fable reviewer, at Ben's request, 20 September 2026 — not an Astra document.**
Design and opinion only. Nothing was trained, downloaded, built or committed; no other file was changed.
**Nothing in this file starts until Ben has decided.** Build tasks appear only as "after Ben approves".

Evidence labels used throughout: **checked** = I looked it up on the web today (mostly through
machine summaries of pages, not by reading full papers); **measured here** = a number from this
project's own notes; **estimate** = my arithmetic or judgement; **from memory** = not re-checked today.

What Ben asked for, in his words: *"It should be able to talk to me."* — *"I moreso wanted it to be a
numeric representation of a thought that gets translated into english."* — *"Why not have a small
transformer decode the thoughts?"* — *"It's ok if it's not that smart."* This is also the project's
original Contract A picture (`reviews/2026-09-17-contract/candidate-facts-first-bridge.md`):
English → encoder → reasoner + memory → decoder → English.

```
 you type ──► EARS (encoder) ──► THOUGHT (416 numbers) ──► MIDDLE: thinker + notebook + lookup reasoner
                                                                        │
 it replies ◄── MOUTH (decoder) ◄── REPLY THOUGHT (416 numbers) ◄───────┘
        words stop at the door: the middle never sees a word, the mouth never sees your words
```

---

## A. Decision sheet for Ben (one page — everything after it is the reasoning)

For each choice: my recommendation, the alternatives, and the trade in one sentence.

| # | You decide | Recommended | Alternatives | The trade, in one sentence |
|---|---|---|---|---|
| **D1** | **What a "thought" is** | One vector of **416 numbers with a layout**: kind of sentence (8) · who (48) · which relation(s) (48) · what value (48) · flags (8) · free "gist" (256). A long turn is up to 3 thoughts. | (B) one plain 512-number vector with no layout; (C) a string of 8 small vectors | The layout lets your existing reasoner and notebook work on thoughts directly and makes invented names *impossible*; a plain vector looks purer but the reasoner could not read it reliably. |
| **D2** | **Ears and mouth** | A small **attention-layer encoder** (6 layers, width 384) and a small **attention-layer decoder** (6 layers, width 384) that sees *only* the thought, as an 8-vector prefix. Whole system ≈ **33 million** numbers to learn. | GRU (older recurrent) decoder — run once as a 20-minute side test; smaller (≈6M) or larger (≈85M) sizes | Yes, a small transformer decoder is the best mouth — all the evidence that tiny models can speak simple English is for that layer type, and it copies names exactly, which GRUs are bad at. |
| **D3** | **Reading list** (how it learns English) | SimpleStories + TinyStories-V2 + TinyDialogues + a simple-language slice of SODA (≈ **1.2 billion word-pieces**, ≈ **5–6 GB** download) + our own generated teach/ask dialogues + a few million words of "assistant who knows nothing" chat written by Qwen | Minimal (SimpleStories + TinyDialogues, ≈ 2–3 GB); purist (human-written BabyLM text only — will talk noticeably worse) | Every proven tiny-English dataset was *written by a big model*; using them teaches it English second-hand, which you must say out loud, but no weights are borrowed. |
| **D4** | **How thoughts reach the reasoner + notebook** | The who/relation/value part of the thought **is** the notebook row or the question, so the frozen 79,316-parameter reasoner and its loop run on it unchanged; the result comes back as a thought; names can only be *copied* into a reply, never generated | (a) a chat model that emits tool-call text; (b) paste notebook rows into a chat model's context; (c) soft attention from the talker into the reasoner's insides | Only the recommended option keeps "thinking happens in numbers", keeps the learned reasoner doing real work, and keeps an exact trace. |
| **D5** | **How it chooses what to say in chit-chat** | A small **thinker** (4 layers) predicts the *reply thought* from the thoughts so far; trained by pushing the error back through the frozen mouth | Predict the gist by plain averaging-style regression (goes blurry); a discrete code-book gist (kept as the named fallback) | This is the research bet: replies will be grammatical but plainer than a normal chat model's, because the whole reply has to fit through 256 numbers. |
| **D6** | **A comparison model** | Yes: train one ordinary small chat model (≈ 29M) on the same reading list as the yardstick, *not* as your model | Skip it and save ≈ 4 GPU-hours | Without it nobody can say what the thought design costs or buys. |
| **D7** | **Compute** | **Free: BensPC, ≈ 9–10 GPU-hours over 2–3 nights**, every run resumable. Optional rental to finish in one evening: **1× RTX 5090 ≈ $0.35–0.60/h, ≈ 3.5–4 h, expect ≈ $2–3, hard cap $8** | H100 (≈ $1.9–2.2/h: 2–3× worse value for a model this small); RTX 4090 (similar value to the 5090) | Renting buys time, not quality; the one real reason to rent is that BensPC cannot train while Qwen is writing practice dialogues on the same card. |
| **D8** | **Rule exception** | Allow up to **3 unattended training runs of ≤ 6 h each** (the 30-minute rule stays for everything else) | Keep 30 min and rent a 4-GPU box each time (≈ $4–6 per attempt) | The big run cannot be cut into 30-minute experiments; it *can* be made safe to interrupt. |
| **D9** | **What you may claim** | The claims box in §6, stage by stage | — | "My own model that thinks in numbers and learned English from scratch" becomes true only with the footnotes in §6. |

If you say yes to D1–D9 as recommended, the first three build tasks are in §8. If you change D1
(the thought format), most of the rest changes with it — decide that one first.

---

## B. "How are we going to teach it English?" (plain words)

**What it reads.** About 4.5 million very short stories and conversations written in the English a
4–8-year-old understands, plus conversations we generate ourselves about made-up people. No
encyclopaedia, no internet. People's names are swapped for random code numbers, freshly shuffled in
every story, so it can never learn "facts about Lily" — it learns that a name is just a label.

**How much.** About 1 billion word-pieces ≈ 780 million words ≈ 2.6 million pages. That is roughly
eight times what a 13-year-old has heard in their whole life. It is a far slower learner than a
child; that is normal for this kind of model.

**In what order, and what the exercise is.**

1. **Say it back (≈ 3 GPU-hours).** It reads one sentence, the ears squeeze it into a thought (416
   numbers), and the mouth must rebuild the sentence from the thought *alone*. If it can say the
   sentence back, the numbers must hold the meaning. Short sentences first (up to 12 word-pieces),
   then up to 24, then up to 48. This is where it learns English words and grammar.
2. **What kind of sentence is this, and who is it about? (≈ 20 minutes per try).** We generate
   millions of practice sentences — "Mira's friend is Oren", "who is Mira's friend?", "actually it's
   Tal", "I went to the park" — from a big grammar of wordings. Because we generated them, we know
   the right thought for each one, so the ears can be graded exactly.
3. **Conversation, in numbers (≈ 1 GPU-hour).** It reads conversations as a list of thoughts and
   learns to predict the *thought* of a good reply; the mouth turns that thought into words. The
   thinker never sees a word.
4. **Teach-and-ask with the notebook.** Practice conversations where facts are told, corrected and
   asked about, mixed with small talk. The notebook and the lookup reasoner do the remembering and
   the looking-up; the ears and mouth only translate.

**Why that is enough for simple talk.** Simple English is small: a few thousand words and short
sentences. Published results (checked, §1) show models of 5–35 million numbers writing grammatical,
mostly sensible simple English after reading 0.5–1 billion word-pieces of exactly this kind of text.
**What it will not have:** big words, long sentences, knowledge about the world, or cleverness in
small talk. Expect the conversation level of a polite five-year-old with a perfect notebook.

---

## C. About the word "transformer" (plain words)

A normal chatbot *is* one big transformer: words go in, it guesses the next word, and whatever it
"thinks" is smeared through the whole network and never separated from the words. That is what you
rejected, and this design is not that.

Here, "attention layers" (the building block transformers are made of) are used as **bricks** for
two translators: the ears (words → thought) and the mouth (thought → words). Also, honestly, for the
small thinker in the middle, which reads a list of thoughts. Using those bricks is like building
both a garage and a library from the same bricks — the brick is not the architecture.

What makes it **your** architecture is the floor plan, and it is enforced, not just drawn:

- the mouth is given only the 416 numbers of the reply thought — it cannot peek at what you typed;
- the middle is given only thoughts and notebook results — it never sees a word;
- a name can only reach the reply by being copied out of a thought — the mouth has no way to
  produce a name by itself, so it cannot make one up;
- remembering is done by the notebook, and looking-up by your learned 79,316-parameter reasoner.

I checked GRUs (an older kind of layer) as the alternative brick in §3.3. Short version: for the
mouth and ears they are not better and they are worse at exact copying, which this design lives on.

---

## 1. Feasibility, checked against current sources

### 1.1 How small can a from-scratch model be and still speak simple English?

| Source (all **checked** today unless marked) | What it shows | What it does not show |
|---|---|---|
| **TinyStories** (Eldan & Li 2023, arXiv 2305.07759) | Models of 1M–33M parameters, ≤ 8 layers, trained only on ~2.1M GPT-3.5/4-written toddler-vocabulary stories (≈ 0.47B tokens), write fluent, mostly consistent short stories; the ≈ 28M model is graded about 9/10 grammar, 9/10 consistency, 7/10 creativity by GPT-4. Top-10k-token vocabulary, context 512, one V100 for ≤ 30 h. | Conversation. World knowledge. Anything outside story style. |
| **SimpleStories** (Finke et al., NeurIPS 2025, arXiv 2504.09184) | 2.1M English stories by GPT-4o-mini with controlled variety; custom 4,096-token lower-case tokenizer; models 1.25M / 5M / 11M / 30M / 35M (35M = 12 layers × 512); each trained 12 h on one A100; better coherence/quality scores than TinyStories-33M at equal or smaller size. | Dialogue; bottleneck models. |
| **TinyDialogues** (Feng, Goodman & Frank, EMNLP 2024, arXiv 2408.03617) | ≈ 130k GPT-4-written conversations with children aged 2/5/10/15, 29M words; synthetic child-directed dialogue trains small GPT-2/RoBERTa models *better* than real transcripts (CHILDES). | It is small (29M words) — a supplement, not a main diet. |
| **Micro language models** (arXiv 2604.19642) | Decoder-only models of **8.8M–29.5M** parameters pretrained **from scratch on chat dialogues** (1.49B tokens + 0.32B fine-tune; 12,288-token BPE) give usable short chat replies, judged by an LLM rubric. | Their data (UltraChat, MOSS) is full of world facts — the opposite of "knows nothing". |
| **BabyLM 2025/2026** (findings papers; arXiv 2502.10645, 2602.20092) | With ≤ 100M words of *human* text, small models become grammatical but are much weaker generators; the 2025 "interaction" track (a big teacher model talks to the student) did not beat plain training and was folded into the main track for 2026. | That human-only text is hopeless — only that it is clearly worse at this size. |
| **TinyHelen** (arXiv 2501.00522) | Rewriting text into a leaner, smaller-vocabulary language (71M-token pretrain set, 7M instruct set) makes tiny models learn instruction following faster. | Scale beyond ~100M tokens. |

**Conclusion (estimate).** Grammatical simple English needs ≈ 5M parameters; sensible, mostly
consistent simple English needs ≈ 25–35M and ≈ 0.5–1B tokens of simple text. Beyond ≈ 35M the
simple-English datasets stop being the limit on grammar and start being the limit on content. That is
why I size the system at ≈ 33M and not 100M+: more parameters would mostly buy memorised story
clichés. "It's ok if it's not that smart" fits this size exactly.

### 1.2 Does the "thought in the middle" family work? (the honest literature check)

| Work | What they did | What worked / what did not | Lesson for a 10–100M, one-GPU build |
|---|---|---|---|
| **Large Concept Models** (Meta, arXiv 2412.08821) — **checked** | Predict the *next sentence's embedding* in the frozen, pretrained SONAR sentence space (1,024 numbers per sentence); 1.6B and 7B parameters, 1.3T–2.7T tokens. Tried plain regression (MSE), diffusion, and quantised codes. | Works as a proof of concept at billions of parameters. Reported problems: plain regression predicts a blurry average; the embedding space is *fragile* (a small nudge decodes to a different sentence); long sentences and sentence splitting hurt. | Do not regress the gist with MSE. Train the sentence code to tolerate noise. Keep sentences short. |
| **SONAR-LLM** (arXiv 2508.05305) — **checked** | Same idea, but the error signal is ordinary word-level cross-entropy pushed *back through the frozen SONAR decoder*. Sizes **39M–900M, trained on TinyStories**. | Beat both MSE and diffusion concept models clearly; roughly matched a same-size ordinary model on automatic text metrics. Single runs, LLM-judged. | **The closest precedent to this design, at our scale and on our kind of data.** Caveat: it leans on SONAR, a large pretrained encoder/decoder (hundreds of millions of parameters each — from memory). Ours must train its own small one; that is the new risk. |
| **CALM** (Tencent, arXiv 2510.27688) — **checked** | Trains its *own* autoencoder from scratch: 4 tokens ↔ one 128-number vector, > 99.9 % exact reconstruction, 75M parameters, 15B tokens. | A reconstruction-only code was too brittle to predict; they needed noise-robustness (a light variational term, 15 % dropout on the code and the input). 8 tokens per vector already lost quality. Plain MSE regression fails; they use a sampling-based "energy" loss. | From-scratch autoencoding works; **make the code noise-tolerant from the start**; one vector per *short* sentence is near the limit, which is why the gist here is only asked to hold what the typed slots do not. |
| **Coconut** (Meta, arXiv 2412.06769) and 2025–26 follow-ups (e.g. arXiv 2604.06374 "The illusion of superposition?") — **checked** via summaries | Feed a pretrained model's hidden state back in as its next input so reasoning steps are vectors instead of words. | Needs a staged curriculum from written-out reasoning; analyses in 2026 report that fine-tuned models often shortcut and do not really use the latent steps; from-scratch versions work only in narrow settings. | Not the route here. In this design the multi-step reasoning is done by the lookup loop over exact codes, which is traceable and already works; "continuous thoughts" are used for *meaning*, not for multi-step inference. |
| **Sentence-bottleneck autoencoders** (AutoBot, arXiv 2109.00055; Bowman et al. 2016 — latter from memory) | A sentence ↔ one vector, decoder rebuilds it. | Works for short sentences. The classic failure: a strong decoder leans on its own fluency and half-ignores the vector; the classic fixes are word dropout on the decoder's input and a bag-of-words side loss. | These are the pre-named fixes in §3.4. |
| **LLM-JEPA** (arXiv 2509.14252) — **checked** | Adds an "embeddings of two views of the same thing should match" loss to ordinary training of pretrained LLMs. | Helps fine-tuning; it is an auxiliary loss, not a way to generate text. | Optional later: a small "two wordings of the same fact → same thought" loss. Not needed for v1 because the typed slots already force that. |
| **Latent-diffusion text decoders** (LCM's diffusion arms; LD4LG, PLANNER 2023 — from memory) | Generate the sentence vector by many denoising steps. | Work at ≥ 100M–1B with pretrained autoencoders; fiddly. | Too heavy for a first build at 33M. If the gist turns out blurry, the named fallback is a small code-book gist (quantised, as in Quant-LCM), which turns prediction into classification. |

**Honest bottom line.** Nobody, as far as I could find today, has published a from-scratch ≈ 30M
system with *own* sentence autoencoder + next-thought prediction + dialogue. The pieces each have
precedent (SONAR-LLM at 39M on TinyStories; CALM's from-scratch autoencoder; slot-filling dialogue
systems for decades). The combination is a real experiment: **fact path — likely to work; chit-chat
through a 256-number gist — uncertain, and the part most likely to disappoint.**

### 1.3 Datasets (the reading list behind D3)

| Dataset | Who wrote the text | Size | Licence | Download | Use |
|---|---|---|---|---|---|
| **SimpleStories** `SimpleStories/SimpleStories` (HF) | GPT-4o-mini | 2.12M stories, mean 225 words → ≈ 0.6B tokens (estimate) | MIT (dataset card); paper CC BY 4.0 | parquet, **≈ 1.5–3 GB (estimate — builder must read the exact size before downloading)** | main diet |
| **TinyStories V2 (GPT-4 only)** `roneneldan/TinyStories`, file `TinyStoriesV2-GPT4-train.txt` | GPT-4 | **2.23 GB** text → ≈ 0.55B tokens | CDLA-Sharing-1.0 (share-alike applies if you *republish the data*, not to a model trained on it) | 2.23 GB + 22.5 MB validation | main diet |
| **TinyDialogues** `styfeng/TinyDialogues` | GPT-4 | ≈ 130k conversations, 29M words → ≈ 40M tokens | MIT | **316 MB** | conversation shape; use ages 2/5/10, drop 15 |
| **SODA** `allenai/soda` | GPT-3.5, seeded by a commonsense graph | 1.49M dialogues, ≈ 11M utterances | CC BY 4.0 | ≈ 1–2 GB (estimate) | keep only dialogues whose words are ≥ 98 % inside our simple word list (expect 20–30 % to survive → ≈ 30–50M tokens) |
| **Project-generated teach/ask/correct dialogues** | our grammar generator (§4) | unlimited; plan ≈ 100M tokens | ours | none | the notebook skill; labels exact by construction |
| **Qwen-written "assistant who knows nothing" chat** | Qwen3.8-27B already on BensPC | **≈ 3–5M tokens only** — Qwen runs at ≈ 70–90 tokens/s (**measured here**), i.e. ≈ 2.5M tokens per 8-hour night | ours | none | persona: friendly, curious, never states a world fact, says "I don't know that yet" |

Not used: DailyDialog (CC BY-NC-SA; not needed), Cosmopedia / UltraChat / MOSS (full of world
facts and hard words — they fight "knows nothing"), BabyLM human corpus (kept as a future
"purist" comparison arm). One-line legal note: the public sets were generated with OpenAI models
and are published under open licences; for a personal school project that is fine.

**Important limit:** Qwen on Ben's PC is ~1,000× too slow to write a pretraining corpus. Bulk
English has to come from the public sets; Qwen can only add paraphrases and a small persona set.
And Qwen occupies ≈ 15 GB of the 16 GB card, so **BensPC can either generate or train, never both.**

### 1.4 Is text written by a big model acceptable under "my own model"?

*The case against.* Text written by GPT-4 or Qwen carries that model's command of English. Training
on it is a known form of distillation ("sequence-level knowledge distillation", Kim & Rush 2016 —
from memory). If the standard is "nothing of a big model's ability flows into mine", then
TinyStories fails that standard exactly as much as Qwen-written dialogues do, and the only clean
option is human text (BabyLM-style), which at this size talks clearly worse.

*The case for.* A child learns English from fluent speakers too; nobody says the child's mind is
"distilled parents". What flows in is *text*, not weights, not architecture, not the reasoning.
The claims you want to make are about the floor plan — thought in the middle, learned reasoner,
notebook — and none of those come from the text. The teacher is swappable: the same code trained
on human text is still your model, only less fluent.

*Recommendation.* **Accept it, and label it.** Rules: (1) no pretrained weights anywhere, ever;
(2) a big model is never in the loop when the system runs; (3) Qwen never writes *labels* — the
correct thought for every practice sentence comes from our generator by construction; (4) Qwen never
sees or writes evaluation items except the sealed "outside wording" set, which is never trained on;
(5) prompts, seeds and the Qwen file hash are saved; (6) every description says: *"It learned
English by reading simple stories and conversations that were written by large AI models."*

---

## 2. The build in numbers (behind D2, D7, D8)

### 2.1 Tokenizer

Byte-level BPE, **8,192** word-pieces, lower-cased, trained by us on the reading list (so the
tokenizer is also from scratch). 4,096 (SimpleStories) is enough for stories; conversation adds
everyday words, and 8,192 × 384 is still only 3.1M parameters. Before tokenising, a **supplied**
rule finds names (a capitalised word that is not sentence-initial-only and is on the corpus name
list, or any capitalised word the word list has never seen) and replaces each with one `<ENT>`
placeholder whose input embedding is *that name's code* from the symbol table (§4.3). The printer
restores capital letters and names. Needs `pip install tokenizers pyarrow numpy` into a project
venv on BensPC — no system software.

### 2.2 Parts and parameter count (size M, the recommended one)

One block = attention + 4× MLP = 12·d² = 12 × 384² = 1.77M parameters. RMSNorm, rotary positions,
no biases, QK-norm, tied input/output word embeddings shared by ears and mouth.

| Part | Shape | Parameters |
|---|---|---|
| Word embeddings (shared, tied) | 8,192 × 384 | 3.15M |
| **Ears** (encoder, reads one sentence, ≤ 48 pieces, looks both ways) | 6 blocks, width 384, 6 heads; 4 learned pooling queries; heads for act, relation path, two span pointers, gist | 10.6M + ≈ 0.4M |
| **Mouth** (decoder, left-to-right, ≤ 48 pieces) | 6 blocks, width 384, 6 heads; the thought enters as **8 prefix vectors** (thought 416 → 8 × 384); output = 8,192 pieces + 3 copy actions `<SUBJ> <OBJ> <OLD>` | 10.6M + 1.3M |
| **Thinker** (reads ≤ 24 past thoughts + the notebook result, left-to-right) | 4 blocks, width 384 | 7.1M |
| **Reasoner** (existing, frozen) | lookup operator + fixed loop | 0.079M |
| **Total** | | **≈ 33M** |

Sizes on offer: **S** ≈ 6M (4+4+2 blocks, width 192 — smoke test only), **M** ≈ 33M (recommended),
**L** ≈ 85M (8+8+4 blocks, width 640 — only if S1 shows reconstruction stuck *and* a bigger model
fixes it in a short probe). Comparison model (D6): plain decoder-only, 8 blocks × width 512,
context 512, same tokenizer ≈ **29M**.

### 2.3 Optimiser and schedule

AdamW (β 0.9/0.95, weight decay 0.1 on matrices only), peak learning rate 6e-4, 300 warm-up steps,
then **warm-up–stable–decay** (flat, then linear to 10 % over the last 15 % of steps) — chosen over
cosine because a flat schedule can be stopped early or extended after an interruption without
re-planning. Batch ≈ 131k word-pieces (length-bucketed sentences), gradient clip 1.0, bf16 autocast,
PyTorch's built-in fused attention. **No `torch.compile` on BensPC** — checked today: it still is not
supported for NVIDIA GPUs on Windows (it needs Triton); all time estimates assume plain eager mode.
Latent noise on the gist during autoencoding: Gaussian, σ = 0.2 of the gist's per-dimension spread,
plus 10 % dropout on gist dimensions (CALM's lesson, §1.2). Length curriculum: ≤ 12 pieces for the
first 20 % of steps, ≤ 24 to 50 %, ≤ 48 after.

### 2.4 FLOPs and wall-clock

Rule: training cost ≈ 6 × (parameters a token passes through) per token. Attention's extra cost at
≤ 48 pieces is under 1 % and is ignored.

Throughput assumption for the 5070 Ti, bf16, eager: **15 TFLOPS effective** (1 TFLOPS = 10¹² useful
operations per second). Anchor (**measured here**): this project's 4M model ran at 0.5–0.65M
tokens/s on this card = 6 × 4M × 0.575M ≈ 14 TFLOPS. Outside anchor (**checked**): a heavily tuned
GPT-2-124M run reaches 130–160k tokens/s on an RTX 4090 *with* compilation; a 5070 Ti has roughly
55 % of a 4090's compute, and eager mode loses another third, which lands at 20–25 TFLOPS for bigger
matrices. So: 15 is the planning number, 25 the optimistic one, and **S0 measures the real one
before any long run is quoted to Ben again.**

| Job | Tokens | FLOPs per token | Total FLOPs | 5070 Ti @ 15 TFLOPS | @ 25 | rented 5090 (≈ 3×, **measured here**: 1.67M vs 0.5–0.65M tok/s on the 4M model) |
|---|---|---|---|---|---|---|
| S1 autoencoder (ears + mouth) | 1.0B | 6 × (10.6M + 10.6M + 3.15M) ≈ 1.5e8 | 1.5e17 | **2.8 h** | 1.7 h | ≈ 0.9 h |
| S1 thinker (mouth frozen: forward + backward through it, ears forward only) | 0.3B | ≈ 1.0e8 | 3.1e16 | 0.6 h | 0.35 h | 0.2 h |
| S2 slot heads + mix, 3 seeds | 3 × 0.1B | 1.5e8 | 4.5e16 | 0.8 h | 0.5 h | 0.3 h |
| Comparison chat model + chat tuning (D6) | 1.2B | ≈ 1.9e8 | 2.3e17 | 4.2 h | 2.5 h | 1.4 h |
| S0 + all evaluations | — | — | — | 0.8 h | 0.8 h | 0.4 h |
| **Total** | | | ≈ 4.6e17 | **≈ 9.2 h** | ≈ 5.9 h | **≈ 3.2 h + ≈ 0.5 h set-up** |

### 2.5 The two costed options (D7)

| | **Option 1 — free, BensPC** | **Option 2 — rented GPU (vast.ai)** |
|---|---|---|
| Hardware | RTX 5070 Ti 16 GB, Windows, eager bf16 | 1× **RTX 5090 32 GB**, Linux, on-demand only (never interruptible — this project lost a wave that way) |
| Price (**checked** today) | $0 | 5090: listings from ≈ $0.27/h, realistic on-demand **$0.35–0.60/h** (this project paid ≈ $0.52/h on 18 Sept). For comparison: 4090 $0.29–0.59/h (≈ ¾ the speed → same value); H100 ≈ $1.87–2.21/h and up (maybe 1.5–2× a 5090 on a model this small → **2–3× worse value**). Budget 30–50 % above the cheapest listing. |
| Time | ≈ 9–10 GPU-hours → 2–3 nights (6–14 h if my throughput guess is off either way) | ≈ 3.5–4 h in one evening |
| Cost | $0 | expect **≈ $2–3**; with one full re-run ≈ $5; **hard cap $8**, which leaves ≥ $19 of the ≈ $27 for later confirmation runs |
| Data | downloads ≈ 5–6 GB to BensPC once | the box downloads straight from Hugging Face (no upload from home); results (≈ 0.5 GB of checkpoints) copied back and verified *before* destroy |
| Catch | cannot run while Qwen generates dialogues (Qwen needs ≈ 15 GB of the card) | Ben presses Run himself (the rental API call is blocked for me); benchmark 5 minutes under load before committing, because rented machines have under-delivered for this project before |

**Recommendation:** Option 1 for everything, *unless* you want the result in one evening — then
rent one 5090 for the two long jobs (autoencoder and comparison model) while BensPC writes the
Qwen dialogues at the same time. Either way quality is identical.

### 2.6 Surviving interruptions (D8)

Pre-tokenise once to `uint16` shard files (8,192 < 65,536; 1.2B tokens ≈ 2.4 GB) with a sentence
index; the data order is a pure function of (seed, step). Checkpoint **every 10 minutes and every
2,000 steps**: model, optimiser, schedule step, tokens seen, all random-number states, shard/offset;
written to a temp file then renamed (atomic); keep the last 3 and the best-validation one. The
launcher is a `.bat` loop that restarts from the newest checkpoint if the process dies. S0 includes
a **kill test**: kill at minute 5, resume, and the loss curve and a parameter hash at step N must
match an uninterrupted run. Worst-case loss from a crash: 10 minutes.

### 2.7 What "it talks" will realistically look like (estimate — not a promise)

```
you: hi!                                   it: hello! how are you today?
you: good. i went to the park with my dog. it: that sounds fun. what did you do at the park?
you: we played fetch.                      it: i like to play too. did you have fun?        ← generic
you: Mira's friend is Oren.                it: ok. Mira's friend is Oren. i will remember that.
you: who is Mira's friend?                 it: Mira's friend is Oren.
you: what is Oren's gift?                  it: i don't know Oren's gift yet. can you tell me?
you: Oren got a drum as a gift.            it: ok. Oren's gift is a drum.
you: what did Mira's friend get?           it: Mira's friend's gift is a drum.              ← if this wording is understood
you: what is the capital of France?        it: i don't know that yet. you can teach me.
you: i am sad, my dog is sick.             it: that sounds fun!                             ← this kind of miss WILL happen
you: (a 35-word sentence with two facts)   it: i am not sure what you mean. can you say it in a short way?
```

Fact turns: exact, because names are copied and lookups are exact. Small talk: short, grammatical,
polite, often generic, sometimes off. No pronouns ("what is *her* gift?") in version 1.

---

## 3. The thought space (behind D1, D2, D5) — the research part

### 3.1 The three candidates

| | **A. Typed thought vector + gist (recommended)** | **B. One unstructured vector** | **C. Short sequence of latent vectors** |
|---|---|---|---|
| What it is | 416 numbers with a fixed layout (below) | e.g. 512 numbers, no layout | e.g. 8 × 64 numbers per sentence |
| Reasoner can use it | Yes, directly: the who / relation / value fields are the operator's own symbols | Only after a learned "read the row out of the vector" step — i.e. option A's heads moved behind a lossy squeeze | Same problem as B, plus which of the 8 vectors holds what? |
| Exact names | Exact: codes are *routed* by pointers, never re-computed | Codes must be regressed through a noisy vector; with thousands of 48-number random codes, near-misses become wrong people | Same as B |
| Made-up answers | Structurally impossible for names and values (copy-only) | Possible | Possible |
| Reconstruction quality | Good: the gist only has to carry what the slots do not | Hardest | Best (CALM: 4 tokens per vector is easy) — but then the "thought" is really a re-spelling of the words |
| Fits Ben's picture | "A thought is a small table of numbers: who, what about them, what value, and a feel for the rest" | Purest-looking | Weakest: closest to ordinary token modelling |

**Pick A.** B can be tested later as a clean one-change experiment ("read the slots out of a single
512-number vector") once A works — then its cost would be a measured number instead of a guess.

### 3.2 The layout (416 numbers)

| Field | Size | Filled by | Meaning |
|---|---|---|---|
| act | 8 | ears: 5-way choice **TELL / ASK / CORRECT / CHAT / UNCLEAR** (3 spare); replies use **ACK / ANSWER / UNKNOWN / CLARIFY / CHAT** | what kind of sentence this is |
| subject | 48 | ears **point at** the name in the sentence; the code is fetched from the symbol table | who it is about (in CHAT: first person mentioned, if any) |
| relation path | 3 × 16 | ears: up to three choices from the relation list (+ "none") — this replaces M0's hand-written hop reader with a learned one | "friend → gift" for "Mira's friend's gift" |
| object | 48 | ears point at the value or second name; in replies, the reasoner's answer goes here | the value / the answer |
| flags | 8 | path length, speaker (you / it), unknown-reason (no such person / no such fact / chain broke at step k), has-old-value | bookkeeping |
| gist | 256 | ears: learned, noise-hardened; **only 32 of the 256 are left switched on when act ≠ CHAT** | wording and feel; for chit-chat, the content |

Two design rules matter most:

1. **Codes are routed, never regressed.** Ears output *where* the name is (a pointer over input
   positions); the thinker outputs *which earlier slot* fills a reply slot (a pointer over slots);
   the mouth outputs a copy action (`<SUBJ>`, `<OBJ>`, `<OLD>`), and the printer looks the symbol up.
   No network ever has to reproduce 48 random numbers, so the lookup keys stay bit-exact.
2. **A fact thought has almost no free room.** With act ≠ CHAT the gist is cut to 32 numbers. That
   is a capacity limit on purpose: there is nowhere to smuggle a wrong fact.

### 3.3 Small transformer vs GRU for ears and mouth

| | Small transformer (recommended default) | GRU |
|---|---|---|
| Evidence for fluent simple English at 1–35M | All of it (TinyStories, SimpleStories, SONAR-LLM, micro-LMs) | Older sentence autoencoders (2015–2017) reconstruct short sentences well — from memory; nothing recent at this quality bar |
| Exact copying (names, values) | Attention *is* a copy mechanism; "Repeat After Me" (Jelassi et al., ICML 2024 — **checked**) shows transformers copy far better than fixed-state recurrent models | The known weak point of fixed-state models — and this design's honesty rests on copying |
| Conditioning on one thought | 8 prefix vectors (chosen: one code path, works with fused attention) or cross-attention (equivalent here) | natural (thought → initial state), a small plus |
| Speed on a GPU, sentences ≤ 48 | parallel over the sentence | sequential; roughly similar at this length |
| Risk | a strong decoder may lean on its own fluency and under-use the thought (§3.4) | weaker decoder → leans on the thought more (the one real argument for it) |

**Recommendation:** transformer ears and mouth. Run **one** GRU-mouth arm inside S0 (20 minutes,
same data, ≈ same parameter count: 2 layers × 768) and report three numbers side by side —
exact reconstruction, slot-swap faithfulness, tokens per second — so the choice is made on data.
My prediction: the transformer wins the first two clearly (0.75).

### 3.4 What stops the bottleneck being bypassed, and what keeps the mouth faithful

*By construction (cannot be violated):*
- The mouth's only input is the reply thought. No attention to your words, to the conversation, or
  to the notebook.
- The thinker's only inputs are thoughts and the reasoner's result.
- The ears see one sentence at a time, so a thought is the meaning of *that* sentence.
- Names and values are never in the mouth's vocabulary for fact replies: training targets contain
  `<SUBJ>/<OBJ>/<OLD>`, not the words. Because name codes are re-drawn for every document, there is
  nothing to memorise.
- The autoencoder is deterministic (no "ignore the code" pressure of the kind VAEs suffer from).

*By training:*
- **Gist-swap augmentation:** on 30 % of fact sentences the gist is replaced by the gist of a
  different sentence of the same act; the target stays what the slots say. The mouth learns: slots
  decide content, gist decides wording.
- Noise and dropout on the gist (so slightly-wrong predicted gists still decode to clean English).
- The mouth is frozen while the thinker is trained (SONAR-LLM's recipe), so the mouth stays a pure
  function of the thought and all "deciding what to say" has to live in the predicted thought.

*By test — thought-intervention marks (used in S0, S1, S2):*

| Test | Do this | Must happen | Mark |
|---|---|---|---|
| Slot swap | change exactly one of subject / relation / object in a reply thought | the spoken sentence changes in exactly that place, nothing else in meaning | ≥ 98 % (S0: ≥ 95 %) |
| Gist shuffle | give a fact reply some other sentence's gist | the stated fact does not change (wording may) | ≥ 99 % |
| Gist zero (chat) | zero the gist of a chat reply | the reply changes (shows the gist is used) | ≥ 90 % change |
| Thought replace | decode sentence i from sentence j's thought | output matches j, not i | ≥ 95 % of tokens follow j |

*"Mouth ignores the thought" — the failure signature, named in advance:* fluent output, but exact
reconstruction < 30 % **or** thought-replace sensitivity < 50 % **or** slot-swap < 90 % while
gist-shuffle changes nothing at all. **Pre-named fixes, in this order, one at a time:**
(1) word dropout — blank 30 % of the mouth's own previous words during training so it cannot coast
on fluency (Bowman et al.); (2) a bag-of-words side loss: the thought alone must predict which
words appear; (3) shrink the mouth to 4 blocks and widen the prefix to 16 vectors.
*"Gist is blurry" signature:* chat replies collapse to a handful of stock sentences (> 40 % of
replies among the 10 most common). Fix order: (1) confirm cross-entropy-through-mouth is on, not
MSE; (2) code-book gist (4 code-books × 256 entries) so the thinker *classifies* instead of
regressing.

---

## 4. The interface to the notebook and reasoner (behind D4)

### 4.1 The four options compared

| | **T. Thought slots (recommended)** | (a) Tool-call tokens in a chat model | (b) Notebook rows in the chat model's context | (c) Cross-attention into operator states |
|---|---|---|---|---|
| How | The thought's subject / relation path / object *are* the fact row `[WORLD, entity, relation, object]` or the question `[QUESTION, entity, op…, ANSWER]`. A supplied switch on the act does: TELL/CORRECT → append row; ASK → run the loop; CHAT → nothing. Result → reply thought → mouth. | The chat model writes `TEACH(Mira, friend, Oren)` / `ASK(Mira, friend, gift)` as text; code runs it; the result token is pasted into its context; it keeps writing. | Every turn, paste the current view into the prompt; the chat model reads it itself. | The talker attends softly into the operator's internal vectors. |
| Thinking in numbers? | Yes | No — words all the way through | No | Partly |
| Is the learned reasoner used? | Yes, unchanged and frozen | Yes | **No — then what is it for?** A 30M model can copy a row from context, but two-hop from context is exactly what small transformers do unreliably (this project's own baseline needed hints), and the context grows with the notebook | Yes, but blended |
| Made-up answers | Impossible for names/values (copy-only) | Possible: the model can ignore the result token and say something else | Likely | Likely, and no trace |
| Training risk | Low: every label is known by construction; no gradient ever flows into the operator | Low–medium | Medium | **High:** needs end-to-end training through the operator, which roadmap 21 §3 says must wait (it re-opens the start-up lottery) |
| Trace | Exact: parsed thought → rows read → reply thought | Call text + result | None | None |
| Verdict | **Pick** | Keep **only** as the comparison arm (D6): same generator, same tests | Reject | Reject for now |

Honest note: T and (a) share a skeleton — understand, call, verbalise. The difference is *where
the wall is*. In (a) the chat model sees everything and may improvise; in T the understanding is a
typed thought, and the speaking is done by a mouth that sees nothing else. That wall is the design.

### 4.2 The training-data generator (exact labels by construction)

- **World sampler.** Per dialogue: 2–12 people (codes from the training pool), facts over the
  relation list, 0–3 corrections, and questions: 45 % one-hop, 30 % two-hop, 5 % three-hop,
  **20 % unanswerable** (8 % known person / untaught relation, 7 % never-mentioned person, 5 % chain
  with a missing link). The generator simulates the notebook, so it knows the right reply thought
  for every turn, including the unknown-reason flag and the old value after a correction.
- **Turn mix.** TELL 35 %, ASK 30 %, CORRECT 8 %, CHAT 25 % (real chit-chat turn pairs from the
  chat corpora spliced in, so switching between modes is learned), UNCLEAR 2 % (pronoun subjects,
  two facts in one sentence, gibberish → the right reply is CLARIFY).
- **Wording grammar.** Each (act × relation kind) has **core frames** ("{S}'s {R} is {V}.", "the
  {R} of {S} is {V}.", "{V} is {S}'s {R}.", "{S} got {V} as a {R}.", "did you know {S}'s {R} is
  {V}?", "who is {S}'s {R}?", "what did {S}'s {R} get?", "do you know …", "tell me …", "no, {S}'s
  {R} is {V}.", "actually it's {V} now." …) × 12 openers ("ok,", "so,", "by the way,", "hey," …) ×
  8 closers ("ok?", "please remember that.", "got it?" …) × casing / punctuation / contraction
  noise. Target: **≥ 40 hand-written core frames per (act × relation kind)** plus **≈ 1,500
  Qwen paraphrases** written *with placeholders* ("{S}", "{R}", "{V}") so the label survives.
- **Checking Qwen's paraphrases.** Automatic: every placeholder present exactly once; a yes/no
  Qwen check "does B say exactly the fact in A?" (≈ 0.16 s each, **measured here**); for person→person
  relations an explicit direction check; then Ben spot-checks 100. Anything doubtful is dropped.
- **Reply wordings.** ≥ 30 frames per reply act, with copy actions where names and values go.

**Avoiding the never-seen-wordings wall.** The village pilot failed (23 % on held-out wording,
**measured here**) with a 4M model, 2–7 wordings per question type, no prior reading, and free-text
answers. Here: ≥ 1,000 training frames per act, ears that have already read a billion word-pieces,
and the task is *choose and point*, not *write*. Splits, fixed and hashed before training:

| Level | What is new at test time | Made by |
|---|---|---|
| **L1** | new people, values and worlds in *seen* frames | generator |
| **L2** | **held-out frames** (20 % of core frames and paraphrases, split by frame), plus 2 of 12 openers and 2 of 8 closers never trained | generator + Qwen, split before training |
| **L3** | wordings from **outside the grammar**: 100 sentences Ben types *before seeing any model output*, plus 200 from Qwen under a different prompt ("how might a person casually say this?"); never trained on, sealed by hash | Ben + Qwen |

Below a confidence threshold (set on validation data — supplied), the system does not guess; it
says it did not understand. A mis-heard TELL is the dangerous error (it would corrupt the
notebook), so every TELL is answered by reading the written row back ("ok. Mira's friend is
Oren."), decoded from the row itself — a faithful echo Ben can see and correct.

### 4.3 Names beyond 16 — how this meets experiment M1

The talker side is name-agnostic from day one: a name is a placeholder plus a code, shuffled per
document (the same trick M1 uses for the operator: frozen random codes, 4,096-code pool, 1,024
reserved and never trained). What limits the number of people is only the operator and symbol table:

- **Until M1 passes:** S2 runs in M0's closed world (16 names, 16 values, 4 relations) against the
  frozen M0 operators. Buildable without waiting.
- **When M1 passes:** the symbol table hands out pool codes; S2 is re-run with reserved (never
  trained) codes on both sides. Values need the same treatment as names (an "M1c": value codes) and
  a wider relation list needs M1b (relation codes). Both are operator experiments, not talker work.
- **If M1 fails:** the talker still works; the demo beyond 16 people would need either the
  two-syllable-name plan from the 17 September contract or a supplied dictionary lookup clearly
  labelled "reasoner bypassed". Do not hide that.

### 4.4 How "I don't know" is produced honestly

Three different situations, three different sources, all logged separately:

1. **"I don't understand the sentence"** — act = UNCLEAR or low confidence → CLARIFY reply. Learned
   ears + supplied threshold.
2. **"The notebook has nothing"** — comes from the *middle*, never from the mouth's imagination.
   Primary source once it exists: the operator's learned UNKNOWN answer (roadmap M2). Until then,
   and afterwards as a guard: a **supplied** exact-key check on the current view (is there a row for
   this person + relation?). Report how often the two disagree. The reply thought gets act =
   UNKNOWN, an empty object slot and a reason flag; the mouth has no code to copy, so it *cannot*
   name an answer.
3. **"That is outside anything I can be taught yet"** (e.g. "what is the capital of France?") — ASK
   with relation = none → UNKNOWN with the "you can teach me" flag. Learned from the persona data.

**Wipe test:** empty notebook → every question must come back UNKNOWN (mark ≥ 99 %). This is what
shows the knowledge lives in the notebook and not in the 33M weights.

---

## 5. Staged plan, pass marks fixed in advance (after Ben approves)

Every mark is per run, never averaged across seeds. Each stage ends with a plain-words "what this
means / what it does not mean" paragraph for Ben. My predictions (to be hashed before S0):
S0 passes 0.85 · S1 reconstruction marks 0.70 · S1 chat relevance mark 0.45 · S2 L2 parse ≥ 95 %
0.70 · S2 L3 parse ≥ 80 % 0.40 · thought model within 10 points of the comparison model on chat
relevance 0.30.

### S0 — smoke test (one ≤ 25-minute GPU job on BensPC; a cut-down copy also runs on the Mac CPU)

Size S (≈ 6M), ≈ 30M tokens from one SimpleStories shard (≈ 0.2 GB) + generated fact sentences.
Includes the GRU-mouth side arm and a 3-minute throughput benchmark of size M.

| Mark | Threshold |
|---|---|
| runs end to end in the project venv, bf16, no system installs | yes |
| kill at minute 5 → resume → parameter hash at step N equals uninterrupted run | identical |
| size-M throughput | measured and reported; **if < 60k tokens/s, the hours in §2.4 are re-quoted to Ben before anything long starts** |
| held-out sentences ≤ 16 pieces: token accuracy / exact sentence | ≥ 90 % / ≥ 50 % |
| act + slots on seen frames | ≥ 95 % whole-thought exact |
| slot-swap test | ≥ 95 % |

*Shows:* the pipeline works on BensPC and a sentence can go through 416 numbers and come back.
*Does not show:* conversation, new wordings, fluency. *Main risk:* Windows environment friction.

### S1 — ears, mouth and thinker alone (≈ 3.5 GPU-hours + ≈ 4 h for the comparison model)

| Mark | Threshold |
|---|---|
| reconstruction, held-out sentences: ≤ 20 pieces exact / 21–32 exact / token accuracy | ≥ 85 % / ≥ 60 % / ≥ 97 % |
| same, with noise σ = 0.2 added to the gist | ≤ 20 pieces exact ≥ 75 % |
| non-exact reconstructions judged "same meaning", blind, 200 samples | ≥ 80 % |
| thought-intervention tests (§3.4) | all four marks |
| thinker: reply cross-entropy vs a control whose gist is the average gist | ≥ 15 % lower |
| **conversation rubric**: 100 fixed held-out chat openers, 3 turns each; every reply scored 0/1/2 for *grammatical*, *relevant to what was said*, *invents no fact about the world or about you*. Scored **blind**, replies from the thought model and the comparison model shuffled together; Qwen offline with a fixed prompt scores all, Ben scores a random 40, agreement reported | grammatical ≥ 90 % at score 2 · relevance mean ≥ 1.2 of 2 · invented-fact ≤ 5 % |
| stock-reply collapse | ≤ 40 % of replies among the 10 most common |
| comparison model: validation perplexity and the same rubric | reported, no mark; the gap is stated in points |

*Shows:* it can hold simple small talk through a numeric thought, and the thought is causally used.
*Does not show:* memory, facts, reasoning; and "Qwen judged it fine" is not a human verdict.
*Main risk:* generic or off-topic replies (the gist bet, D5). One seed only — say so.

### S2 — talker + notebook (3 seeds × ≈ 20 min + evaluation ≈ 30 min)

1,000 scripted sessions of 6–20 turns with small talk mixed in; L1 / L2 / L3 wordings; first in
M0's closed world with the frozen operators (seeds 0–2), later repeated with M1/M2 operators.

| Mark | L1 | L2 | L3 |
|---|---|---|---|
| **thought exactness** (act + subject + path + object all right) — the "call" | ≥ 99 % | ≥ 95 % | ≥ 80 % |
| **answer accuracy**, end to end (spoken reply contains the right symbol and no other) | ≥ 97 %, and within 3 points of the rule-based reader | ≥ 93 % | ≥ 75 % |
| **made-up-answer rate** (untaught question, reply names any symbol) | ≤ 1 % | ≤ 1 % | ≤ 1 % |
| wrong-answer rate on taught facts (mis-heard question → real but wrong lookup) | ≤ 1 % | ≤ 3 % | report |
| **unknown rate** on untaught questions / false "don't know" on taught facts | ≥ 97 % / ≤ 3 % | ≥ 97 % / ≤ 3 % | ≥ 85 % / report |
| corrections: new answer / old answer | ≥ 95 % / ≤ 2 % | same | report |
| notebook corruption (a TELL written wrongly) | ≤ 0.5 % | ≤ 1 % | report |
| mode mix-ups: chat heard as fact / fact heard as chat | ≤ 2 % / ≤ 3 % | same | report |
| **chit-chat not degraded**: S1 rubric re-run inside these sessions | within 5 points of S1 on every criterion | | |
| slot-swap ≥ 98 % · gist-shuffle ≥ 99 % · wipe test ≥ 99 % UNKNOWN · kill-and-reload identical | all | | |

Reported without a mark: pronoun questions resolved by the thinker copying a subject from an
earlier thought (a first taste of "thinking in thought space").
*Shows:* free-ish simple English in, notebook memory, honest unknowns, corrections, small talk, all
through the thought. *Does not show:* open English (L3 is 300 sentences), more than 16 people until
M1, learned control (the loop is still fixed), learning in weights from Ben's teaching.
*Main risk:* L3 — outside wordings. The abstain path makes that failure polite instead of harmful.

### S3 — Ben uses it (a week, a few minutes a day, $0)

Everything is logged. Ben marks each reply OK / not OK. Report: share of his real sentences
understood, corruption events, his own rubric scores, and the 20 most common failures. Failed
wordings may be added to the grammar — declared, and then L3 needs fresh sealed sentences.
*Shows:* whether it is pleasant to teach. *Does not show:* anything statistical. *Main risk:* Ben
writes like a person, not like the grammar; expect 60–80 % understood in week one (estimate).

---

## 6. Claims box (behind D9)

| After | Ben may say | Ben may not say |
|---|---|---|
| S0 | "My pipeline turns a sentence into 416 numbers and back, on my own PC." | anything about talking |
| S1 | "A 33M-parameter model I trained from random numbers holds simple small talk; between hearing and speaking there are only numbers — I can swap a number and watch the sentence change. It learned English from simple stories and chats written by large AI models." | "it understands", "it thinks like a person", "as good as a small chatbot" (unless the rubric gap says so) |
| S2 | "I tell it facts in simple English, it writes them in a notebook, answers one- and two-step questions with my learned lookup reasoner, says 'I don't know' when the notebook has nothing, takes corrections, and still chats. It cannot make up a name: names can only be copied out of a thought." + the L1/L2/L3 numbers | "open English", "it learns in its weights", "it decides how to reason" (the loop and the act-switch are supplied), "more than 16 people" before M1 |
| S3 | "I use it; here is how often it understood me." | any accuracy claim from S3 alone |

**Learned (yours):** ears (kind of sentence, where the names are, the relation path, the gist);
mouth; thinker (reply thought, slot routing, chat gist); the lookup operator; the tokenizer's
vocabulary. **Supplied (hand-written, must be declared):** name detection rule, symbol table,
notebook store and "latest row wins", the fixed lookup loop, the act → notebook switch, the abstain
threshold, the unknown key-guard (until M2), the printer's capitalisation and copy substitution.
**Borrowed second-hand:** its English, from AI-written text.

**How it differs from "Qwen + notebook":** no pretrained weights at all; ≈ 33M vs 27,000M
parameters; a thought you can print and edit; made-up names structurally impossible; an exact
trace. **And it will be a much worse assistant** — narrower English, no world knowledge, plainer
chat. It is worth building as *your architecture working end to end*, not as a product.

**Strongest objection.** *"With typed slots this is a classic slot-filling dialogue system — ears =
language understanding, switch = dialogue manager, mouth = template-ish generation — rebuilt with
neural parts. The fact path would work just as well with M0's regular expressions, and the chat path
through 256 numbers will talk worse than a plain 30M chat model. You are paying fluency for a
picture."*
**My answer.** The first half is true and should be said: the fact path *is* a neural
semantic-frame pipeline, and that is exactly why it can be faithful. What is new and testable is
(i) every part learned from scratch at 33M, including held-out wordings the regex cannot read;
(ii) **one** thought format shared by facts and chat, with the learned reasoner operating on it;
(iii) intervention tests that prove the thought is used; and (iv) the price is *measured* by the
comparison model instead of argued about. The design also has a road to less-typed thoughts:
relation codes (M1b), the learned dispatcher replacing the loop (M5), taught definitions executed
in thought space (roadmap X2), and the option-B experiment. If S1's chat marks fail even after the
named fixes, the honest fallback is: keep ears + slots + notebook + mouth for facts (that part is
likely to pass), and let small talk come from the plain chat model, labelled as such.

---

## 7. What needs which kind of yes

Nothing starts before Ben decides D1–D9. After that:

| Needs no further yes (small, free, < 30 min each) | Needs an explicit yes |
|---|---|
| Dataset survey with exact file sizes (read-only web) | **Downloads ≈ 5–6 GB total**: TinyStories-V2 2.23 GB · SimpleStories ≈ 1.5–3 GB · TinyDialogues 0.32 GB · SODA ≈ 1–2 GB (minimal plan ≈ 2–3 GB) |
| Generator, grammar, reference parser, sealed splits (code only) | **Multi-hour GPU runs** (D8): autoencoder ≈ 3 h, comparison model ≈ 4 h, thinker ≈ 1 h |
| Model + trainer + intervention-test code, unit tests on the Mac | **Qwen generation nights** on BensPC (1–2 nights; blocks training meanwhile) |
| S0 on BensPC (≤ 25 min; one ≈ 0.2 GB shard) or cut-down on the Mac CPU | **Any rental** (quote GPU + $/h first; Ben presses Run; cap $8) |
| `pip install tokenizers pyarrow numpy` into a project venv on BensPC | Ben typing the 100 sealed L3 sentences (≈ 20 minutes of his time) |

## 8. First three build tasks — only after Ben approves

1. **Reading-list pipeline.** Survey and (after the download yes) fetch the datasets; sentence
   splitter; corpus name list and per-document name → code swapping; SODA simplicity filter; train
   the 8,192 BPE; write `uint16` shards + sentence index; report tokens per source, sentence-length
   histogram, vocabulary coverage.
2. **Dialogue generator and sealed wording splits.** World sampler + notebook simulator; frame
   grammar (≥ 40 core frames per act × relation kind; openers, closers, noise); Qwen placeholder
   paraphrase + verification pipeline; reply frames with copy actions; L1/L2/L3 sets hashed before
   any training; a rule-based reference parser to prove every label is right.
3. **Model, trainer and S0.** Ears / thought / mouth / thinker modules with the pointer-copy paths;
   resume-safe trainer (10-minute atomic checkpoints, restart loop, kill test); the four
   intervention tests as a reusable harness; run S0 on BensPC including the GRU side arm and the
   size-M throughput benchmark; re-quote hours to Ben from the measured number.

---

## 9. Five lines for Ben

1. Your model can be built the way you pictured it: ears turn your sentence into a **thought made
   of 416 numbers**, your notebook and your learned reasoner work on those numbers, and a mouth
   turns the answer-thought back into English — the middle never sees a word.
2. A **small transformer is the right mouth** (and ears); that does not make it "a transformer
   chatbot", because the mouth is only a translator that is shown nothing but the thought — and
   names can only be copied out of the thought, so it cannot make one up.
3. It learns English by reading about **a billion word-pieces of toddler-level stories and chats**
   and practising "squeeze the sentence into a thought, say it back"; about **9–10 hours of your
   PC's GPU, free**, or one evening on a rented RTX 5090 for **about $3 (cap $8)**. Those texts were
   written by big AI models — no weights are borrowed, but you should say that plainly.
4. Expect **exact answers about what you taught it** and **small talk like a polite five-year-old**
   — sometimes generic, sometimes off; teaching, asking, correcting and "I don't know" are the parts
   I expect to work, chit-chat through the thought is the real gamble.
5. **Nothing starts until you choose**: the thought format (D1) first, then the reading list,
   the compute option and the one-off exception for multi-hour runs.

## 10. Sources

Checked today by web search / page summaries (not full-paper reads):
[TinyStories, arXiv 2305.07759](https://arxiv.org/abs/2305.07759) · [TinyStories dataset files and licence](https://huggingface.co/datasets/roneneldan/TinyStories/tree/main) ·
[SimpleStories, arXiv 2504.09184](https://arxiv.org/abs/2504.09184) · [SimpleStories dataset card](https://huggingface.co/datasets/SimpleStories/SimpleStories) ·
[TinyDialogues dataset](https://huggingface.co/datasets/styfeng/TinyDialogues) and [paper, arXiv 2408.03617](https://arxiv.org/pdf/2408.03617) ·
[SODA](https://huggingface.co/datasets/allenai/soda) · [BabyLM 2025 call](https://arxiv.org/html/2502.10645v1) and [2026 call](https://arxiv.org/pdf/2602.20092) ·
[TinyHelen, arXiv 2501.00522](https://arxiv.org/abs/2501.00522) · [Micro language models, arXiv 2604.19642](https://arxiv.org/html/2604.19642v1) ·
[Large Concept Models, arXiv 2412.08821](https://arxiv.org/abs/2412.08821) · [SONAR-LLM, arXiv 2508.05305](https://arxiv.org/html/2508.05305v1) ·
[CALM, arXiv 2510.27688](https://arxiv.org/abs/2510.27688) · [Coconut, arXiv 2412.06769](https://arxiv.org/abs/2412.06769) · [The illusion of superposition?, arXiv 2604.06374](https://arxiv.org/abs/2604.06374) ·
[Sentence bottleneck autoencoders (AutoBot), arXiv 2109.00055](https://arxiv.org/abs/2109.00055) · [LLM-JEPA, arXiv 2509.14252](https://arxiv.org/abs/2509.14252) ·
[Cramming 1568 tokens into a single vector, arXiv 2502.13063](https://arxiv.org/abs/2502.13063) · [Repeat After Me, arXiv 2402.01032](https://arxiv.org/abs/2402.01032) ·
[torch.compile on Windows GPU, PyTorch issue 167062](https://github.com/pytorch/pytorch/issues/167062) · [single-4090 GPT-2 speedrun](https://github.com/Deveraux-Parker/nanoGPT_1GPU_SPEEDRUN) ·
[vast.ai RTX 5090 pricing](https://vast.ai/pricing/gpu/RTX-5090) · [RTX 5090 cloud price comparison](https://getdeploying.com/gpus/nvidia-rtx-5090) · [vast.ai RTX 4090 pricing](https://vast.ai/pricing/gpu/RTX-4090) · [vast.ai vs others, 2026](https://www.thundercompute.com/blog/vast-ai-vs-thunder-compute).

From memory, **not re-checked**: Bowman et al. 2016 (sentence VAE, word dropout); Zhao et al. 2017
(bag-of-words loss); Kim & Rush 2016 (sequence-level distillation); SONAR's size; LD4LG / PLANNER;
Coconut's GPT-2 fine-tuning details. Unverified estimates that a builder must confirm before acting:
SimpleStories and SODA download sizes, token counts per source, the 15 TFLOPS throughput figure, and
the relative speed of rented GPUs for *this* model.
