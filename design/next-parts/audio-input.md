# Audio input for Premonition (speech and other sounds)

Status: design + CPU plumbing only. **No experiment in this file has been run** except the S0 plumbing check in section (j).
Date: 2026-10-03. Code: `premonition/audio/`. Tests: `tests/test_audio_frontend.py`, `tests/test_audio_adapter.py`.

Labels: **SHOWN** = checked in code, a test, or a source I actually read (cited). **SUGGESTED** = reasoned, not checked. **UNTESTED** = a claim about behaviour nobody has measured.

---

## (g) Summary for Ben (read this first)

**Revised 2026-10-03 by the Opus audio thread. The main track is now game sound (section j); speech is later.**

- The point is hearing sounds that matter, like a creeper hissing behind you. That needs three things: notice it, know roughly where, and react in well under a second (a creeper gives 1.5 s, and sprinting away takes about 0.7 s).
- The ear is now our own tiny "streaming" ear (about half a million numbers) that hears in stereo and reacts within about 60 ms. Whisper, the old choice, is built for 30-second speech clips and is too slow and too blind to direction for a game. It stays for the later speech track.
- Plain stereo can tell left from right and near from far, but **not front from back**: the game just makes one ear louder. "Behind you" comes from Minecraft's 3D-audio option, from vision ("I hear it but can't see it", which is a reasoning step), or from turning the head.
- Sound goes to the reasoner the same way as text and pictures: a row of 256-wide slots, one per 50 ms (one game tick), with the time of each slot. The last 2 seconds are kept.
- What exists today: the streaming ear's plumbing and 67 tests, which show it is causal (it never changes its mind about the past) and fast (about 2 ms of CPU per 50 ms of sound). **They say nothing about whether it can actually hear a creeper.** That is experiments S1-S3 and G1-G3.
- Audio does not jump the GPU queue. Skills and critical thinking come first.

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

**Recommendation (speech track only, revised 2026-10-03): Whisper-base encoder, frozen.** For game and environment sound, the default is now our own small causal stereo ear; see section (j2).
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

## (f) Speech-track experiments (ALL NOT RUN; one change each; pass marks fixed here)

Revised order: these come after the game-sound S-track (section j5). E0 is reasoner/scaling work, not audio.

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

- **Now (CPU, done here):** frontend, adapter contract, synthetic signals, streaming stereo ear (section j2); 67 plumbing tests. Design reviewed by an independent Opus reviewer (2026-10-03).
- **Next (revised 2026-10-03, see j6):** game-sound S1a-S1c on CPU with rendered sounds; S2 once PR #23's core reads coords; S3 after vision. The speech track (A0, E1-E7) after that. E0 moves to the reasoner/scaling work.
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

Also SHOWN by `tests/test_audio_stream.py` (21 passed, added 2026-10-03): the stereo front end gives the same frames whatever the chunk sizes, never changes past frames when later audio arrives, gives zero level difference for mono, reads left/right from level difference with a hand-written baseline, and is blind to front/back for amplitude-panned sources; the causal ear streamed in random chunks equals a full pass, and is causal with a 63-frame receptive field; the Workspace window makes 50 ms slots, keeps the last N, never revises a slot, and gives times relative to now.

**These tests show the plumbing works. They say nothing about whether audio reasoning works.** Bit-exact match with Whisper's own frontend is UNTESTED (experiment A0).

Sources read: github.com/openai/whisper (README, whisper/audio.py, whisper/model.py); librosa filters.py and core/convert.py; HF config/cards/API for LiquidAI/LFM2.5-1.2B-Base, LiquidAI/LFM2-Audio-1.5B, openai/whisper-tiny, openai/whisper-base, UsefulSensors/moonshine-tiny/-base, facebook/wav2vec2-base, facebook/hubert-base-ls960, microsoft/wavlm-base-plus, MIT/ast-finetuned-audioset-10-10-0.4593, laion/clap-htsat-unfused, kyutai/mimi, facebook/encodec_24khz; arXiv 2410.15608 (Moonshine); arXiv 2310.13289 (SALMONN, abstract via search).

---

## (j) Game sound: hearing what matters, from where, in time (revised 2026-10-03 by the Opus audio thread)

Ben's aim (13:39 UTC): "hear sounds", e.g. a creeper hissing behind you in Minecraft. That is a different job from captioning or transcribing. The model must notice a sound that matters, judge roughly where it is, and act fast enough. This section supersedes the earlier short draft of (j) and changes the default plan: **game sound is now the primary audio track; speech (sections a-f, Whisper-base) is a later, secondary track.**

Labels as above. Facts checked on the web by an independent Opus reviewer on 2026-10-03 carry their source.

### j1. What the creeper case actually demands (SHOWN facts, SUGGESTED consequences)

| Fact | Source | Consequence for the design |
|---|---|---|
| A creeper ignites within 3 blocks and explodes 30 ticks (1.5 s) later; it needs unbroken line of sight; getting 7 blocks away or breaking line of sight cancels it | minecraft.wiki/w/Creeper | The whole loop (hear, decide, act) must fit well inside 1.5 s. Escaping 3 -> 7 blocks takes about 0.7 s sprinting (speed from memory), so reaction must be <= ~0.6-0.8 s. The old G3 mark of 1.0 s was too loose. |
| No hiss without line of sight | minecraft.wiki/w/Creeper | A hiss you hear but cannot see means "in your blind area" (behind or to the side), not "behind a wall". |
| Mono sound sources are positioned by OpenAL and fade with distance; OpenAL Soft's non-HRTF stereo default ("panpot") is plain amplitude panning | docs.neoforged.net (sounds), OpenAL Soft alsoft.conf | Plain stereo gives left/right and loudness (distance), but **no front/back**: a source 30 deg ahead-left and 150 deg behind-left sound identical. Our toy panner reproduces this (test `test_amplitude_panning_is_front_back_blind`). |
| Java 1.19 (22w11a) added a "Directional Audio" option, HRTF-based, best with headphones | minecraft.wiki/w/Options | With HRTF on, front/back cues exist (time and spectral differences). Mel + level difference alone may lose them; phase or GCC-PHAT features are the matching change (SUGGESTED). |
| "Show Subtitles" (renamed "Closed Captions" in 1.21.9) prints the sound name with `<` / `>` arrows, only for off-screen sounds | minecraft.wiki/w/Subtitles | Must be **off** in every sound test, or the vision path can cheat. They also cannot say "behind", so they are no ceiling for direction. |
| MineRL and MineDojo give no audio observation; MineDojo does give damage source direction | minerl.readthedocs.io, docs.minedojo.org | We need our own capture harness. Existing Minecraft research environments do not help with sound. |

So "behind you" has three possible sources, and the design uses all three as separate, testable routes (SUGGESTED):
1. **HRTF on** ("Directional Audio"): the ear can hear front/back directly.
2. **Fusion with vision:** a sound with no matching thing on screen is in the blind area. This is a reasoning step, not a perception trick, which is what Ben wants the reasoner to be good at.
3. **Active hearing:** turn the head and listen to how the pan changes. This needs the action loop, so it comes last.

### j2. The ear, re-examined

The old default was frozen Whisper-base. For game sound it is the wrong ear (SHOWN unless marked):
- It needs a 30 s input (reference code asserts 3000 mel frames); slicing its position table for short clips works mechanically but is reported to degrade.
- It is not causal: every frame attends to the whole 30 s window.
- It is mono and trained mostly on speech.
- Cost: about 90 GFLOP per call (SUGGESTED arithmetic: ~62 G matmuls + ~27 G attention + ~3 G convs). Re-running it every 50 ms tick would be ~25,000x the cost of the small ear below.
- Our own Whisper-style front end is not causal either: it centres frames (12.5 ms look-ahead) and floors every frame at the loudest frame of the clip (SHOWN in `frontend.log_mel`, and by `test_whisper_frontend_is_not_causal`).

**New default for game sound: our own small causal ear on stereo features** (`premonition/audio/stream.py`, SUGGESTED design, plumbing SHOWN):

```
stereo samples (16 kHz, 2 ch), pushed in chunks as they arrive
  -> StreamingStereoMel: uncentred STFT (25 ms window, 10 ms hop), fixed log floor,
     features per frame = [left log-mel 80 | right log-mel 80 | left - right 80]  (240)
  -> CausalConvEar: 5 dilated causal conv layers (kernel 3, dilations 1,2,4,8,16), width 128,
     residual + GELU; receptive field 63 frames = 0.63 s; 289,408 params
  -> AudioWindow: 5 frames per slot = 50 ms = one game tick; adapter (stack, hidden 256) -> 256-wide
     slot, 229,888 params; keep the last 40 slots (2 s) as Workspace tokens
```

Why this default (SUGGESTED): it is causal by construction; it is tiny (~0.52M params, which **must count toward the model's size budget** when claiming "beats bigger models at its size"); Minecraft's sound vocabulary is closed, and labels are free (a client mod or offline rendering knows each sound's id, time and position), so the usual reason to borrow an ear, too little labelled data, does not apply; and it takes stereo natively.

**The fair opponent** is a frozen small pretrained frame-level ear: `frame_mn06` from fschmid56/PretrainedSED (1.62M params, frame-level AudioSet Strong detection at 40 ms, MIT; SHOWN from the repo README). These are mono, so the single change is "run it on L and R separately and concatenate with the level difference", so a stereo-vs-mono gap is not mistaken for an ear gap. Clip-level models (EfficientAT clip models, PANNs CNN10) are the wrong opponent: they label whole clips.

Whisper-base stays as the ear for the **speech track only** (spoken questions, maybe spoken guides later). That track is no longer first.

Shown on CPU (container Xeon 2.1 GHz, numpy, one thread, random weights): front end + ear + window take a median of 1.95 ms per 50 ms chunk (p95 2.26 ms). Worst-case algorithmic delay from a sound's first sample to the slot that holds it is 60 ms (10 ms to the first frame plus up to 40 ms to fill the slot; `hearing_latency_bound`), although a sound at the very edge of a Hann window is faint, so useful detection may take about half a window longer (SUGGESTED).

### j3. Fitting the shared Workspace (contract v1)

| Field | Game-sound value |
|---|---|
| `tokens [N,256]` | one slot per 50 ms, the last 40 slots |
| `segment` | (`notebook`, `audio`): sound is context for the current step, not the question |
| `coords` | time = slot centre **minus now**, in seconds (always <= 0), so numbers stay small in a long game; the core's relative bias only uses differences |
| `coord_valid` | (False, False, valid): row and column absent, time present on real slots |
| `valid` | False for empty slots at the start of a stream |

**No direction field** (SUGGESTED default). `coords` say where a token sits in its input, and drive the core's relative-position bias. Azimuth is an uncertain property of the sound's content (front/back ambiguous without HRTF), so it belongs in the token, learned by the ear, with an auxiliary azimuth (sin, cos) head while pretraining the ear so it is decodable. Mapping azimuth onto image columns to help audio-vision binding is rejected: it is wrong for off-screen sounds, which are the ones that matter. Binding is learned from content and tested in S3.

Three problems were raised with the Workspace owner (PR #23). All three are **settled in Workspace contract v1** (PR #23 section 6, commit c208de425), and the audio code now follows it (all untested beyond plumbing):
1. **Audio sat at (row 0, col 0)**, the same place as image patch (0,0). Fixed: a per-axis `coord_valid [N,3]` bool with a neutral "no position" bias per axis. Audio emits `coord_valid = (False, False, valid)`, built only in `audio_coord_valid()`. Row and column offsets count only within one (role, modality) source.
2. **The time bias was too short** (+/-4 steps = +/-200 ms at 50 ms buckets). Fixed: time is seconds relative to now (<= 0), bucketed on a signed log scale (0, 50, 100, 200, 400, 800 ms, 1.6 s, older, plus "no time"), applied across all timed sources so a sound and a video frame can be ordered. The +/-4 clip and the +/-1 heads now apply to row and column only. Experiment S2 tests this choice.
3. **Registers need t = 0.** Fixed: registers and action tokens carry time 0 with row and column absent; tool results carry their arrival time; the question carries 0; notebook text, guides and examples have time absent.

For offline clips, `adapt()` keeps clip-relative times; a caller building a v1 Workspace sets `time_offset = -(clip seconds)` so times are <= 0. The streaming `AudioWindow` already gives times relative to now.

The ear is causal, so past slots never change: cache them, and let the core re-read the ~40-slot window each step. Tie the slot rate to the policy's step rate (20 Hz today, same as the game tick).

### j4. Data (SUGGESTED, nothing recorded or rendered yet)

Kept strictly separate, as the CLAUDE.md asks:
- **Small synthetic tests (CPU):** toy stereo scenes from `synth.stereo_scene` (hiss, steps, groan, twang with exact times and azimuths). Plumbing and early ear checks only. They are not Minecraft sounds.
- **Offline-rendered game sounds:** play the game's sound files through OpenAL Soft at known positions, HRTF on and off. Unlimited labelled stereo data without running the game. Mojang's asset terms are **not checked**; Luanti's openly licensed sounds are a fallback.
- **Real game recordings:** capture system audio and the screen together on Ben's PC, with a client mod logging each sound event (id, time, position relative to the player). Subtitles off. Terms not checked.

### j5. Experiments (ALL NOT RUN except S0; one change each; marks fixed now)

Small synthetic / rendered (CPU is enough for S0-S1; a 0.5M ear trains on CPU):

| ID | One change | Pass mark | Proves it wrong |
|---|---|---|---|
| S0 | switch to the causal stereo ear (plumbing) | chunked output = full pass (max abs diff < 1e-5); changing future samples never changes past outputs; delay bound <= 60 ms | any past slot changes when later audio arrives. **Status: passes on CPU** (`tests/test_audio_stream.py`, 21 tests); says nothing about hearing |
| S1a | stereo vs mono input, same ear, rendered sounds | left/right accuracy >= 90% (chance 50%); event-onset F1 >= 0.8 at +/-100 ms | mono within 10 points on left/right (labels leak through loudness) |
| S1b | our ear vs frozen `frame_mn06` per channel + level difference, same head | adopt ours if detection F1 is within 0.03 of the pretrained ear at <= 1/3 of its params | pretrained ear wins by > 0.05 on held-out sound variants |
| S1c | fixed log floor vs running-max normaliser, distance-band task | fixed >= 10 points better | within 3 points |
| S2 | log-spaced time buckets vs 50 ms buckets clipped at +/-4 (needs PR #23's core) | "which came first" on events 0.5-2 s apart >= 15 points higher; shuffled-audio control <= chance + 5 | gain < 5 points |
| S3 | add vision to audio: "heard but not seen" | on-screen/off-screen F1 >= 0.85 with audio + vision, audio-only <= 0.65 | audio-only within 5 points of audio + vision (a loudness or pan shortcut) |

Real game (separate sets, after the vision path and an action head exist):

| ID | One change | Pass mark | Proves it wrong |
|---|---|---|---|
| G1 | HRTF on vs off, same ear | front/back accuracy >= 75% with HRTF, <= 60% without | HRTF-off also >= 70% (leak from vision or scene motion) |
| G2 | sound on vs muted, scripted creeper approaches | >= 20 points fewer explosions with sound on | gap < 5 points |
| G3 | sound on vs muted, creeper starting behind | median hiss-to-evasive-action <= 0.6 s and survival >= 70% | not faster than muted by >= 0.3 s |

Fresh scenario sets follow section (i): one authoring agent, an independent checker, hash seal.

### j6. Order of work (SUGGESTED)

Audio does **not** take the first GPU slot; skills and critical thinking come first. S0 is done. S1a-S1c can run on CPU once rendered sounds exist. S2 waits for PR #23's core to read `coords`, `segment` and `valid` (today's `to_core_layout` shim drops coords). S3 waits for the vision path (PR #22). G1-G3 wait for the action loop. The speech track (A0, E1-E7) follows after S2; E0 (widen the 32-wide text reader) is reasoner/scaling work and belongs with PR #18 / PR #23.
