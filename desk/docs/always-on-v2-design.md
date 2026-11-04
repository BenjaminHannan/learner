# Always-on Glim, v2 design (Ben's brainstorm, 2026-11-03 night)

Decided with Ben in the "Brainstorm: always-on Premonition" thread. v1 (phases 1–4, commits a7372af..c19090d on branch always-on) gave consent, the loop, the Learn button and hearing. v2 adds the following.

## 1. Speak-o-meter (when Glim talks)
- A tiny separate model answers one question: should Glim speak right now? It is never the 3B brain.
- Inputs: current app/window category, what Ben is doing (typing, video, game, idle), time since the last say, the urge level, and the guesser's surprise.
- Feedback, from strongest to weakest: Ben saying "not now / stop / later" in words (strong no) > the 👎 "not now" button on each message (no) > an ignored message (weak no) > a reply, a 👍, or Ben using the help (yes).
- Updated online, then retuned each night during sleep. It starts permissive for "stuck" moments (the same error seen 3 or more times, the same page for more than 10 minutes) and quiet otherwise.

## 2. Where Glim talks: the notch
- A notched Mac: the existing pill/island drops down with the message, and a click opens chat. A Mac without a notch keeps the floating pill.
- Settings has a "Use the notch" toggle. When it is off, Glim uses a macOS notification instead.
- Status icon always in the notch ear: 😴 resting · 📚 learning (+ Mote count) · 💭 thinking · 😲 just surprised. Hover shows more, e.g. "📚 black holes · Lv1 81% · 3 Motes".

## 3. Urges
- Meters that fill over time: 🥱 bored (nothing new, Ben not chatting) → learn or think. 🤔 curious (it saw something it doesn't understand) → adds it to the wonder list. 📣 wants to share → asks the speak-o-meter.
- When bored, think about: (a) Ben's Learn topics, (b) his day (things seen on screen, e.g. an error he hit), (c) the wonder list (its own mistakes and unknowns).

## 4. Motes in bored mode, gated by the memory gauge
- Many Motes run as ONE batch through the same model, which uses the GPU well with little extra memory.
- macOS memory pressure: 🟢 + Ben away + on power → full batch. 🟢 + Ben busy → a couple of Motes. 🟡 → one Mote or pause. 🔴 or swap growing → all stop.
- Ben chatting → everything stops at once (benFirst).
- The brain is Nanbeige4.2-3B with its native two loops. Extra loops stay off.

## 5. Truth-seeking
- Every thought is a `maybe` note → checked against 2 independent websites (or by Ben) → `confirmed` or `wrong`. Only confirmed notes reach sleep training. Wrong ones are kept as corrections ("I thought X; actually Y").

## 6. Prediction and surprise (the tiny guesser)
- A cheap guesser runs every ~1 s and gives probabilities, not single answers: (a) what Ben does next (the next app/window), (b) what it will see/hear next (screen/sound category), (c) facts: guess the answer before checking.
- Surprise = Bayesian surprise: how much an observation changes the guesser's beliefs (the KL divergence between its beliefs after and before), not raw error. Steady randomness such as static, shuffle or ads stops being surprising once learned.
- Big surprise → wake Nanbeige for a tick and file the moment to memory. Not surprising → already known, nothing new to save.
- Test planned with a pass mark fixed beforehand: sleep that picks memories by surprise must beat replaying everything, at the same sleep budget.

## 7. Learn button: forever, with an honest quiz score
- Click Learn → topic → study until Stop (v1). New: when a topic starts, separate "writer" Motes write a locked quiz from several websites. The "studier" Motes never see it. Answers are graded against the sources.
- Shown as a score per level: "black holes Lv1 81% · Lv2 30% · +12% this week". The score that counts is the one measured after sleep. Harder levels are added as the score rises. Ben can peek at the quiz.
- Drift guard: every study step checks "is this still about my topic?"

## 8. Other
- Diary only when asked ("Glim, what did you do?"). Very important things can still come up through the speak-o-meter.
- Privacy: ask once at startup, remember the choice, change it in Settings. No blind spots (Ben: it's all local). Keep notes, never recordings: raw screenshots and audio are not stored.
- Sleep does everything: replay surprises + confirmed notes + dream practice questions (dreamer + checker); it also retunes the speak-o-meter and the guesser.
- Senses: v1 readers now (OCR + Qwen3-VL-2B reader for pictures, Whisper for speech). Vision and sound projectors into Nanbeige are being trained on BensPC (separate track). They switch in only if they pass their pre-set tests. The projector is meant mainly for videos and pictures; OCR stays for text.

## 9. Sleep also trains the eyes and ears: cross-sense agreement (Ben, 2026-11-04 morning; not built yet)
- While watching or listening, Glim pairs its senses: eye features (SigLIP), ear features (Whisper), and text it reads (captions/subtitles, on-screen text).
- Routing: subtitles of speech → training for the ears' speech; sound tags like `[dog barks]` → training for the ears' sounds; on-screen text → training for the eyes' reading. Eyes ↔ ears agreement needs no captions at all.
- 2-of-3 rule: when two senses agree and one disagrees, the odd one out gets a practice example. When none agree, Nanbeige reasons about it and saves a `maybe`; it's never trained on.
- Text is the anchor (Ben): text it reads is believed, and every example must also make sense logically (Nanbeige check). Eyes and ears never teach each other with no text and no logic check passing; this stops echo loops. Extra context (video title, captions, on-screen words) catches shared mistakes, e.g. both senses saying "dog" for a wolf.
- What's stored is encoder features, not raw images or audio. Ben's reason is efficiency: smaller files, and no re-encoding at night. Saved features have to be rebuilt if an encoder changes.
  - Update, Ben 2026-11-04: raw screenshots and audio MAY be stored when needed as evidence (e.g. to re-encode after an encoder changes, or to check a sense lesson). Kept on the Mac only, in a short window with a size cap (the disk is tight); features stay the default.
- Seatbelt: after each sleep, rerun the fixed projector tests (V1 / A1 / VID1). If any score drops by more than 2 points, that night's projector update is undone. This guards against shared mistakes and echo loops where the senses teach each other the same error.
- Models: train during sleep against a bf16 copy of Nanbeige; run day-to-day with the q8 copy. It needs ~8 GB more disk. Check projectors and adapters on q8 after training.
- First test, pass marks fixed: one sleep trained on caption-tagged sound pairs from videos → A1 +5 points or more; V1 drops by at most 2 points. Proven wrong if A1 falls.

## 10. Desk + filing cabinet memory (Ben, 2026-11-04; Experiment M1: FAIL as built)
- **Filing cabinet (archive):** unlimited store of thought vectors. Nothing is deleted, only filed.
- **Desk:** at every step Nanbeige sees exactly 64 memory slots as soft input tokens: 32 working slots (carried from step to step) + 32 recalled slots (the archive entries most similar to "now").
- **Write:** after each step a learned write module updates the working slots from Nanbeige's hidden states (slots attend to the step's hidden states, gated update) and makes new content.
- **Filing:** each working slot has a learned keep score. New content takes the lowest-scoring slot; that slot's old content is filed into the archive with a key. One self-attention layer mixes the 64 desk slots.
- **Learning by sleep:** Nanbeige stays frozen (2 native loops). Only the memory parts train (read projector, write module, keep scores, recall query), and only in sleep between simulated days. An untrained memory is a no-op (zero-init projector, closed gate).
- Test: synthetic days (~300 observation lines, fresh names every day), questions beyond a 20-line window (recall, latest state, counting, two-hop), against no memory (B0) and today's notes file (B1, top-8 retrieved notes). PASS = M1 ≥ B1 + 20 and ≥ B0 + 20 points on held-out test days.
- Code, results and report: `~/learner-ops/premonition-memory` (REPORT.md).
- Result 2026-11-04: on 40 held-out test days M1 scored 7.3% vs notes file 68.5% and no memory 1.8%. Shuffled recall = real recall, so the cabinet was not used; it learned answer formats only. Keep the notes file.
