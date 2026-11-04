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
