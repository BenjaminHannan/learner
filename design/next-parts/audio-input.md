# Audio input for Premonition (speech and other sounds)

Status: design + CPU plumbing only. **No experiment in this file has been run.**
Date: 2026-10-03. Code: `premonition/audio/`. Tests: `tests/test_audio_frontend.py`, `tests/test_audio_adapter.py`.

Labels: **SHOWN** = checked in code, a test, or a source I actually read (cited). **SUGGESTED** = reasoned, not checked. **UNTESTED** = a claim about behaviour nobody has measured.

---

## (g) Summary for Ben (read this first)

- Sound goes in like this: microphone wave -> a borrowed, frozen "ear" (Whisper-base's encoder) turns every 20 ms into a list of 512 numbers -> a small "adapter" we train glues 4 of those together (80 ms), squeezes them to 256 numbers, and hands them to the reasoner as a row of slots. That is the same shape the reasoner already gets from text.
- The adapter is only a translator. It does no thinking. The reasoner thinks.
- The adapter is built so that text, audio and (later) vision all plug in the same way. Every vector carries a label pair (its job, such as question or notebook, and where it came from, such as audio) plus its time and a real/padding flag, in the same record vision uses.
- The main test of whether it works is a **parity test**: ask the same question as text and as speech. If the reasoner reasons equally well both ways, audio works. If it only does well on audio when it can cheat (voice, loudness, recording quirks), it does not.
- What exists today: a numpy sound-to-features front end, the adapter's reference code, and 46 tests. The tests show the pipes are connected correctly. **They say nothing about whether the model can reason about sound.** That needs GPU runs, which wait until the English pilot is done.

---

## (a) What "audio into the reasoner" means

Two kinds of sound, one route.

| | Speech | Other sound (door, alarm, music, footsteps) |
|---|---|---|
| What the reasoner needs | the words, plus some extras text loses: who speaks, tone, pauses, emphasis | what happened, when, in what order, how loud, how often |
| Reference answer for training | the transcript (text) | a caption ("a dog barks twice, then a car passes") or a label |
| Parity target | the text path on the transcript | none exists; judged on questions about the sound |

The reasoner never gets a transcript from the audio path. It gets slot vectors. A transcript-first route (speech recogniser -> text -> text path) is kept as a **baseline**, not as the design, because it throws away tone and every non-speech sound (SUGGESTED).

---

## What the reasoner accepts today (SHOWN, read in code)

- `scripts/sol_translator_grounding_v6.py` lines 42-49, `HumanInputProjection`: `LayerNorm(2048) -> Linear(2048,32) -> GELU -> Linear(32,256)`, output multiplied by the valid mask, then `.unsqueeze(1)` -> `[B,1,T,256]`. 2048 is the LM width: LFM2.5-1.2B-Base `hidden_size` = 2048 (SHOWN, huggingface.co/LiquidAI/LFM2.5-1.2B-Base config.json). Reader parameters: 4,096 + 65,568 + 8,448 = 78,112 (SUGGESTED arithmetic from those shapes).
- `scripts/sol_spatial_attention_core.py` `begin_latent`: requires `[B,H,W,256]`; a notebook `[B,M,256]` is appended with a neutral relative-position index. The grounding script calls it per row (batch of 1), with the question as `[1,1,T,256]` and context as notebook.
- `scripts/claude_fewex_net.py` `Block`: 8 heads, width 256, 2 blocks per loop. Position enters only as a learned **relative** bias, clipped at +/-4 slots (`CLIP=4`); half the heads see only +/-1 slot in the W direction (`WINDOW=1`). There are **no absolute positions** and **no padding mask**: padded rows are zeros but still take part in attention.
- Output side (`scripts/sol_translator_english_v6.py` `StatePrefix`): per-slot `Linear(256+3, 32) -> GELU -> Linear(32, 2048)` then `adaptive_avg_pool1d` to **8 prefix vectors**. So the output side is also a 32-wide pipe, and its output length (8) does not depend on how many input slots there were.

Consequences for audio (SUGGESTED): (1) one clip per forward, or drop padding before the core; (2) at 12.5 slots/s, the +/-4 relative window spans +/-320 ms, roughly one word, while for text it spans about 4 tokens; (3) because the output is always 8 vectors, the text path and audio path can be compared at the 8 prefix vectors even though their slot counts differ. This is used for training stage 1b and the parity test.

---

## (b) Frozen encoder options

Parameter counts marked SHOWN were read from the published safetensors headers (byte-range request, no weights downloaded) or from the HF API; "~" means estimated from checkpoint file size / 4 bytes (fp32), so it includes everything in the file.

| Option | Params (encoder) | Licence | Frame rate, width | CPU fit | Notes |
|---|---|---|---|---|---|
| Whisper-tiny encoder | 8,208,384 (SHOWN) | MIT per github.com/openai/whisper README; HF card tag says apache-2.0 (both SHOWN; mismatch noted) | 50 Hz, d=384 (SHOWN, config + conv stride 2) | good | must pad every clip to 30 s / 3000 mel frames (SHOWN: `assert` in whisper/model.py) |
| **Whisper-base encoder** | 20,590,592 (SHOWN) | same as above | 50 Hz, d=512 (SHOWN) | OK; cost fixed at 30 s per clip (SUGGESTED) | trained on 680k h of weakly labelled audio (from memory, not re-checked) |
| Moonshine-base encoder | 20,153,120 (SHOWN); tiny 7,681,248 | MIT (SHOWN, HF card) | ~41.67 Hz, d=416 (SHOWN, arXiv 2410.15608) | best: raw wave in, variable length, no 30 s pad (SHOWN, paper) | English speech only (SHOWN, card); untested on non-speech |
| wav2vec2-base / HuBERT-base / WavLM-base+ | ~95.1M / ~94.4M / ~94.4M (file size) | Apache-2.0 / Apache-2.0 / not stated on HF card (SHOWN) | 50 Hz, d=768 (SHOWN: conv strides 5,2,2,2,2,2,2) | heavy (~10x the reasoner) | self-supervised; strong on phonetics (from memory) |
| AST (AudioSet) | 86,594,063 (SHOWN) | BSD-3-Clause (SHOWN) | 16x16 patches, stride 10, 128 mel, max 1024 frames (SHOWN, config) | heavy | general sound; outputs patches, not a time row |
| BEATs | not verified (HF API refused) | not verified | - | - | used with Whisper in SALMONN (SHOWN, arXiv 2310.13289 search abstract) |
| LAION CLAP (htsat-unfused) | ~153.6M **whole model incl. text tower** (file size); audio tower alone not verified | Apache-2.0 (SHOWN) | - | heavy | gives one vector per clip; weak on order in time (SUGGESTED) |
| Mimi codec | 96,151,393 (SHOWN) | CC-BY-4.0 (SHOWN) | 12.5 Hz, 1.1 kbps (SHOWN, card) | heavy | built for speech generation; good later for the talker's voice |
| EnCodec 24 kHz | 23,273,218 (SHOWN) | not stated on HF card | - | OK | acoustic tokens; little meaning per token (SUGGESTED) |
| LFM2-Audio-1.5B's encoder | FastConformer 115M (SHOWN, card) | LFM Open License v1.0 for the model (SHOWN, card) | - | heavy | already mapped into LFM2's space, but LFM2, not LFM2.5 (compatibility UNTESTED) |
| Plain log-mel + small conv (ours) | ~0.1-1M (SUGGESTED) | ours | 100 Hz in, any rate out | best | learns an ear from scratch: needs much more audio. Keep as a **control** |

**Recommendation: Whisper-base encoder, frozen,** for both speech and first non-speech tests.
Why (SUGGESTED): smallest well-known encoder that is (1) trained on a huge, varied audio set, (2) permissively licensed, (3) fed by a log-mel front end we can reproduce in numpy (`premonition/audio/frontend.py`), (4) the usual choice for audio-LLM work (SALMONN uses a Whisper encoder; SHOWN from the arXiv abstract). Width 512 at 50 Hz fits the adapter cheaply.
Fallback: Moonshine-base if the 30-second padding cost hurts CPU or latency; it is the same size and handles variable length. Second encoder for general sound (BEATs or AST) only if experiment E4 shows Whisper features miss non-speech events. Mimi is for **speech output** later, not input.

---

## (c) The interface contract: audio fills the shared Workspace

Audio does **not** define its own contract. It fills the shared `Workspace` record settled in PR #23 (reasoner design §6, commit bb4d2efe4) and already used by vision (PR #22, `design/next-parts/vision/workspace.py`, commit 912bfe7de). Both read from `origin` on 2026-10-03; both PRs are still open, so fields may move (SHOWN for what the branches said then).

| Workspace field (shared) | Audio value | Where in code |
|---|---|---|
| `tokens [B,N,256]` float | projected slot vectors, float32; padded rows exactly 0 | `adapt()` |
| `segment [B,N,2]` long = (role id, modality id) | (question / notebook / example / tool_result, `audio`=7) from the shared `SEGMENTS` table (`question 0, notebook 1, example 2, tool_result 3, register 4, text 5, image 6, audio 7`) | built only in `audio_segment()`, so a switch to one combined id touches one function |
| `coords [B,N,3]` float (row, col, time) | `(0, 0, t)`, **t = slot centre in seconds** = `(j + 0.5) * k * frame_period` | `adapt()` / `slot_times()` |
| `valid [B,N]` bool | True = real audio, False = right padding | `adapt()`, `batch()` |

Pipeline (numpy reference in `premonition/audio/adapter.py`):

```
encoder frames [T_in, D_enc] + valid [T_in] (right padding only)
  -> per-frame LayerNorm (no affine)
  -> downsample by k: "stack" (concat k frames) or "mean" (valid frames only)
  -> MLP: Linear(k*D_enc, hidden) -> GELU -> Linear(hidden, 256)   (hidden=None: one Linear)
  -> optional + pos_scale * sinusoid(t)      (off by default)
  -> rows with valid False set to 0
out (one clip): tokens float32 [N,256], segment int64 [N,2], coords float32 [N,3], valid bool [N]
     N = ceil(T_in / k); batch() pads clips to [B, N_max, ...]
```

What the adapter does **not** do: it adds no role or modality vector. PR #23 puts `Embedding(role) + Embedding(modality)` (both zero-init) in the core, so audio needs one new modality id and no new roles (SHOWN in the PR text).

Defaults for audio (all SUGGESTED, none trained):
- Encoder: Whisper-base, D_enc=512, 50 Hz. k=4 -> **12.5 slots/s** (80 ms). A 10 s spoken question gives 125 slots; the same question as text is about 30-40 tokens (assumes ~150 words/min; SUGGESTED). k=8 is experiment E3.
- **Time unit: seconds, not frame index.** Encoders at 50 Hz and 41.67 Hz then agree on "when" (SHOWN by a test for equal slot spans). Row and col are fixed at 0, so audio order lives only in the time coordinate. How the core turns float seconds into relative-bias indices (bucket size) is PR #23's call; 80 ms buckets would give one index per slot.
- **hidden=256, not 32.** The 32-wide pipe in the text reader may cap capacity (fair-scaling thread). Stacked audio frames carry more than one token does. Adapter size: 590,336 parameters with stack k=4, hidden=256; 74,016 at hidden=32; 197,120 with mean-pool (SHOWN by `parameter_count()`). Whether the text reader should widen is its own experiment (E0), text path only.
- Sinusoid in tokens: off (`pos_scale=0`). Order should travel in `coords`. Turn it on only while audio sits in today's notebook, which ignores position (as PR #22 does with its `pos2d` for notebook images). That is experiment E5.
- Role: a spoken question is `question`; a sound to reason about next to a text question is `notebook`.
- Today's core takes no segment, coords or mask. `to_core_layout()` is the shim: role question -> `[1,1,N_valid,256]` latent, other roles -> `[1,N_valid,256]` notebook, padded slots dropped (one clip per forward, as grounding v6 already does per row).

Text under the same contract: frames = frozen LM token embeddings (D_enc=2048), k=1, segment (question or notebook, text=5). With `hidden=32` this matches today's `HumanInputProjection` except that its LayerNorm has learned scale and bias (SUGGESTED; not built here).

---

## (d) Training stages

Encoder, LM and (in stage 1) reasoner stay frozen. Only the adapter trains.

**Stage 1a: adapter alignment (no reasoner).** Speech-text pairs (e.g. LibriSpeech; licence to check) and audio-caption pairs (e.g. AudioCaps, Clotho; licences to check).
- Contrastive loss between mean-pooled audio slots and mean-pooled text-reader slots of the transcript/caption (CLIP-style, in the 256 space).
- Auxiliary CTC loss: a throwaway `Linear(256, 2048)` scored against the frozen LM's tied embedding table, so audio slots learn to sit near the words they contain. Speech only; the head is discarded after stage 1.
Pass gate before stage 1b: retrieval test in E1.

**Stage 1b: parity distillation through the frozen reasoner.** Needs a trained text path (after the English pilot). Feed the transcript through text reader -> core -> `StatePrefix`, and the audio through audio adapter -> same core -> same `StatePrefix`. Loss: match the 8 prefix vectors (and the LM's answer distribution). Possible because the output is always 8 vectors (SHOWN above). PR #23 proposes replacing the pooling with 8 draft registers `[B,8,256]`; that output is also length-independent, so the same loss applies to the registers (SUGGESTED). Only the audio adapter learns.

**Stage 2: skills through audio.** Unfreeze the reasoner, mixed batches of text and audio versions of the same skill tasks, plus sound-only tasks (order of events, counting, "which came first"). Keep a fixed share of text-only batches so the text skills do not drift.

**Keeping the reasoner from learning audio-only tricks** (SUGGESTED rules):
1. Every audio training item that has a text twin trains with its twin in the same batch, with a parity loss on the 8 prefix vectors.
2. Voices, rooms, noise levels and speaking speed vary in training; the sealed test uses **held-out voices and real recordings**, not only the TTS engine used in training.
3. Content-swap control: audio of question A plus a text notebook built for question B; the answer must follow A.
4. Label leakage check: a tiny probe trained on adapter output must not predict the answer better than chance on questions whose answer is not in the audio.
5. The modality-embedding ablation (core's audio id zeroed) and shuffled-audio controls in E2.

---

## (e) Risks, and what would prove the design wrong

| Risk | Signal that the design is wrong |
|---|---|
| Whisper features are mostly about words, so non-speech is lost | E4: event-order accuracy on sound-only items no better than the log-mel control |
| 12.5 slots/s is too stretched for a core tuned to text spacing (+/-4 slot window) | E3: k=8 beats k=4 by the pass mark, or audio parity falls as clip length grows while text does not |
| Adapter learns surface cues (voice, TTS artefacts) | parity on held-out human voices below parity on TTS voices by more than the margin in E2 |
| The direct path adds nothing over a cascade | E2: cascade (ASR -> text path) beats direct audio on spoken questions and direct audio does not win on tone or sound items |
| The 30 s padding of Whisper makes CPU cost too high | measured encoder time per clip > the budget set before E1 (open question 2) |
| Contract is not really modality-agnostic | the redesigned reasoner needs per-modality code paths beyond the modality id |

---

## (f) Experiments (ALL NOT RUN; one change each; pass marks fixed here)

Every eval set is a fresh sealed set (section i). Chance levels are stated so a pass cannot be luck.

| ID | One change | Setup | Pass mark (fixed now) | Result that proves it wrong |
|---|---|---|---|---|
| A0 | none: frontend parity | numpy `log_mel` vs Whisper's own `log_mel_spectrogram` on 20 clips | max abs diff < 1e-3 after normalisation | larger diff: our frontend is not Whisper-compatible, fix before any encoder run |
| E0 | text reader hidden 32 -> 256 (text path only, no audio) | English pilot recipe, 3 seeds | mean dev metric up by more than 2x the seed std | no gain: the 32 pipe is not the cap; keep 32 |
| E1 | add audio adapter, stage 1a only | Whisper-base frozen, k=4, hidden=256, mean-pooled retrieval among 100 transcripts | top-1 >= 0.60 on sealed speech set (chance 0.01); log-mel+conv control below 0.30 | < 0.30, or control within 0.05 of it: adapter is not aligning |
| E2 | stage 1b parity distillation | same questions as text and as speech; reasoner frozen | audio accuracy >= text accuracy - 5 points; same-answer agreement >= 85%; shuffled-audio control <= chance + 5 | shuffled-audio within 5 points of real audio (reasoner ignores audio), or held-out human voices > 10 points worse than TTS voices |
| E3 | k=4 -> k=8 | as E2 | adopt k=8 only if parity improves >= 3 points | otherwise keep k=4 |
| E4 | sound-only items, Whisper features vs log-mel+conv control | event order / count questions on synthetic + recorded sounds | Whisper path >= control + 10 points | not met: add a general-sound encoder (BEATs/AST) as the next single change |
| E5 | `pos_scale` 0 -> learned | as E2, long clips (> 20 s) | parity on long clips up >= 3 points, short clips not down > 1 | otherwise leave positions off |
| E6 | stage 2: unfreeze reasoner, mixed batches | skills set as text and audio | audio skill score up >= 5 points; text skill score not down > 1 point | text score drops > 1 point: audio is eating text skills |
| E7 | few-example learning through audio | teach a new rule with 5 spoken examples | within 5 points of the same 5 examples as text | gap > 10 points |

---

## (h) Roadmap

- **Now (CPU, done here):** frontend, adapter contract, synthetic signals, 46 plumbing tests. Design reviewed.
- **Next (after the English pilot frees the GPU):** A0, then E0 (text only), then E1, E2. Fresh sealed sets for E1/E2 authored and checked first.
- **Later:** E3-E7; a general-sound encoder if E4 says so; Mimi for spoken output in the talker; once the redesigned core reads `segment`, `coords` and `valid`, retire the `to_core_layout` shim; vision through the same contract. Ben's long-term Minecraft test (screen in, keyboard/mouse out) is a natural later use of the sound path: mob noises, footsteps and damage cues as sound-only events. This does not change the first step.

### Open questions and chosen defaults

1. **Where do modalities meet: LM-embedding space (2048) or reasoner slot space (256)?** Default: the shared 256-wide Workspace (now the cross-thread contract), per-modality adapters. Meeting in 2048 would give parity for free but forces sound through word-shaped vectors and the 32-wide reader.
2. **CPU budget per clip?** Default: encoder + adapter <= 1 s per 10 s clip on one laptop CPU; if Whisper-base misses it, switch to Moonshine-base (one change).
3. **How many slots per second?** Default 12.5 (k=4); E3 tests 6.25.
4. **Time unit in `coords`?** Default: seconds (float). Frame index would tie the meaning of a coordinate to one encoder's frame rate.
5. **Modality embedding:** lives in the core (PR #23), zero-init; ablated in E2.
6. **Segment encoding:** pair (role, modality) as settled in PR #23; kept behind `audio_segment()` in case it changes.

---

## (i) Fresh-eval protocol for audio (protocol only; no set authored here)

1. **Author agent** writes the items: question text, the answer, and for audio items a recording plan (voice ID, room, noise level). Sound-only items list the events and their times. It also writes the generation script and records all seeds.
2. **Independent checker agent** (never saw training data choices) re-derives every answer from the audio and text alone, checks sound-only answers against independent event times ( from the synth script or human labels), checks no item or voice overlaps training (by transcript hash, speaker ID, and audio fingerprint), and checks that held-out voices include real human recordings.
3. **Seal:** a manifest lists every file with its SHA-256; the manifest's own SHA-256 is recorded in the experiment plan **before** any training run starts. Pass marks from section (f) are copied into the same plan.
4. **Open once:** the scorer verifies hashes, scores, and writes the result next to the seal. Any change to the set means a new set and a new hash.
5. Required item mix: speech questions with text twins; tone/prosody questions with no text answer; sound-only order/count items; distractor-noise versions; shuffled-audio and content-swap controls.

---

## What the CPU tests show and do not show

SHOWN by `python3 -m pytest tests/test_audio_frontend.py tests/test_audio_adapter.py` (46 passed): frame-count arithmetic (30 s -> 3000 frames), a pure sine peaks in the nearest mel bin (within 1) for 250 Hz-6 kHz, chirps rise, noise bursts are localised in time, determinism, silence and tone are separable by mean energy (frontend) and by slot norm (adapter), downsample length = ceil(T/k), padded rows are exactly zero and padded content cannot leak, mean-pool ignores padded frames, slot coordinates match across frame rates, 30 s of slots get distinct position codes, segment = (role, audio) pair with ids matching PR #22's table, coords = (0, 0, seconds), the adapter adds no role/modality vector, batching pads with valid False, strict shape and dtype errors.

**These tests show the plumbing works. They say nothing about whether audio reasoning works.** Bit-exact match with Whisper's own frontend is UNTESTED (experiment A0).

Sources read: github.com/openai/whisper (README, whisper/audio.py, whisper/model.py); librosa filters.py and core/convert.py; HF config/cards/API for LiquidAI/LFM2.5-1.2B-Base, LiquidAI/LFM2-Audio-1.5B, openai/whisper-tiny, openai/whisper-base, UsefulSensors/moonshine-tiny/-base, facebook/wav2vec2-base, facebook/hubert-base-ls960, microsoft/wavlm-base-plus, MIT/ast-finetuned-audioset-10-10-0.4593, laion/clap-htsat-unfused, kyutai/mimi, facebook/encodec_24khz; arXiv 2410.15608 (Moonshine); arXiv 2310.13289 (SALMONN, abstract via search).
