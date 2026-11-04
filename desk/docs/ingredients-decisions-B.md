# Ingredients, Task B: feeling time + patterns (2026-11-04)

Brief: `/tmp/aon/task-ingredients-B.md` (plan steps 3 and 4 in ingredients-plan.md, app side). Each line says what was decided and why.
Toy results (synthetic notes and days) are kept apart from claims about the real Glim.

## Feeling time (commit bc0912eb0)
- **Where times were missing:** old `alwayson-state.json` rows (inbox, surprises, wonder, activity) and the sleep handoff's
  confirmed notes and corrections. Old rows now load with `t = null` and show as "time unknown". Rows that aren't objects are dropped
  instead of crashing (`wonder` rows with no text used to crash `addWonder`). Handoff entries carry `t` = settle time, else note time.
  The Python reader ignores the extra field (checked: `read_alwayson` only reads `t` on surprises).
- **memory.md is unchanged.** Its notes keep the day-level `updated: YYYY-MM-DD`. Adding clock times would change the line format
  Ben edits by hand, and many tests read it. Exact times for notes live in the new timeline instead.
- **`sleep-candidates.js` is not touched.** Despite the name, it holds adapter candidates, and those already have `created`.
- **Prompt:** the loop's user message now starts with `Now: Wed 4 Nov, 14:05.` (plus `Usually at this time: code 62%.` once that
  hour-of-week has its own evidence). Each observation ends with `(N min ago)`, appended at the end so the old `[screen, HH:MM] text`
  shape stays. Recalled memories (≤ 5 × 180 chars) and patterns (≤ 2 × 240 chars) go below, marked "(data)".
  Worst case adds about 600 tokens; with 12 full observations the whole request is far under 8192 − 2048.
  The chat system prompt (prompt.js) is not changed: it must stay byte-identical, and chat already gets a `[date]` line.
- **When-guesser:** a per hour-of-week (168 buckets) Dirichlet over the 8 app categories.
  - A new bucket borrows ≤ 6 counts from its hour-of-day model, which borrows from "any time", so the bucket's own evidence wins fast.
  - It is updated on a category change, or every 10 min while Ben stays in one app. The app is re-read every second, and without
    this the buckets would fill with "still in Terminal".
  - Its KL is **added** to the app stream's KL: two independent sets of beliefs, so the information gains add. That makes it surprise
    "the existing way": same `big` threshold, same cooldown, same `onBig` → wake + file.
  - `unusualTime` = when-KL ≥ 0.5 nats and ≥ 40 % of the total. That flag changes the surprise text to "Ben opened X at an unusual
    time for him (Tue 10:00, game)".
  - It is opt-in (`new Guesser({ when: true })`; main.js turns it on), so the old guesser tests keep their numbers.
  - Sleep decays it ×0.8 along with the rest of the guesser.
- **Known limit:** an hour with *no* history at all (e.g. 3 am, when the Mac was never used) borrows the all-day mix. A game there is
  not flagged as an unusual time. Reason: there is no "away/idle" category to say "nothing usually happens now". Not changed
  (one change at a time).
- **Time questions in chat:** "how long ago did I…", "when did I…", "what happened right before/after…". They match stemmed content
  words against the timeline + inbox (score ≥ 0.5, the most recent on ties). The answer goes in as a hidden note, like the diary.
  "Nothing matches" makes the model say it doesn't know. Timeless rows are skipped.
- **Earlier clock work:** `premonition-research-20261031.noindex/clock` (K1). It is a learned clock vector injected into Nanbeige
  and needs training. Not reused: this task is app-side only, with no model training.

## Patterns = rules + analogy (commit b63ea3390), interim on the notes
- **What "the notes" means here:** a new **timeline** (`userData/timeline.json`, ≤ 2000 rows, ≤ 240 chars each). It holds always-on
  observations, surprises and truth notes (maybe/confirmed/unsure, plus corrections as confirmed). memory.md has no event times, and
  the inbox keeps only 40 rows.
  - Words only, private text dropped first.
  - Saved at most every 30 s, so up to 30 s can be lost on a hard quit.
- **Embedder:** the notes had none (memory uses word overlap). Chosen: **signed feature hashing** of words + word pairs into
  **256 dims**, sublinear tf, L2-normalised.
  - 0 learned weights, no server, about µs per note.
  - Shape keys are stored as base64 int8 (256 bytes each). The plain vector is recomputed from the text on load.
- **Masking (rules):** links, dates and times (incl. weekdays, "tomorrow", "4pm"), money and numbers.
  - A capitalised word that is not in a ~250-word common list becomes `<NAME>`, or `<PLACE>` after at/in/to/from/near.
  - A sentence's first word is masked only when the next word looks like a name's verb ("Maya texted") or a surname.
  - `<NAME>` is used instead of `<PERSON>` because rules can't tell a person from an app or a shop.
  - This first-word rule was added after dev seed 1 showed "Bus", "Phone" and "Weather" being masked as names.
- **Recall by shape:** `recall(query, {k: 5})` takes plain's best 3, then up to 2 by shape cosine (≥ 0.5) that plain didn't pick,
  then fills from plain. Recall lines say "same shape" when they came through the shape channel.
- **Patterns in sleep, by formula only** (`Timeline.sleep`, run in `aoNightlyJobs` at sleep start and once per night window):
  - identical masked forms share a vector;
  - deterministic leader clustering in time order at cosine ≥ **TAU 0.65**. Picked on dev seed 1: 0.55–0.65 found 10/10, 0.72 split
    one. Seeds 2 and 3 were scored only after that;
  - a cluster becomes a pattern with **≥ 3 members on ≥ 2 days**;
  - **template** = its most common masked form;
  - **follows** = for each member, every other cluster seen 1 min – 1 h later. A follower needs ≥ 2 and ≥ 30 % of members; the top 3
    are kept with their median delay. The 1-minute floor exists because the real-path run showed the windows sense "following" the
    screen sense at 0 min (the same moment seen twice).
- **No model:** patterns.js requires only fs/path/crypto/senses/timesense. A test asserts that exact list. The eval stubs fetch,
  http.request, spawn and execFile during sleep and counts 0 calls. The real-path run counted 0 model requests during the nightly
  jobs.
- **Pruning (file away, never delete members):**
  - A pattern is filed when it has had no new member and no recall for 14 days, or when it was shown ≥ 10 times and never came true.
    "Came true" means a record matching its top follower arrived within an hour of it being shown. That is what "recall through it
    was used" means here.
  - It is also filed when its members aged out of the timeline.
  - A filed pattern comes back when it gets a new, recent member.
  - Identity across nights: a rebuilt cluster with centroid cosine ≥ 0.85 keeps the old id, hits and confirmations.
- **maybe:** any `maybe`/`unsure` member makes the pattern `maybe` (shown as "Pattern (seen 6×, maybe)"). `wrong` notes never join
  clusters; their correction text is used instead.
  - Patterns are **not** sleep training data: the handoff carries only at/confirmed/corrections/surprises, and a test checks the
    keys. So no pattern, maybe or not, reaches training.
- **"What usually happens after X?"** in chat: the best pattern by shape (≥ 0.6), else by the template's words (≥ 0.5) → its top
  follower, with count and median delay. The word fallback was added because Ben's own wording ("after someone texts that practice
  moved") didn't match the shape key in the real-path run.

## Interface for the cabinet (M1)
`Timeline` is the interim backend. The cabinet should provide the same calls: `add(record)`, `recall(query, {k, shapeSlots, before})`,
`patternsFor(query)`, `whatFollows(query)`, `markShown(pattern)`, `sleep()` → `{patterns, made, kept, filed, revived}`.
`aoLoopContext` and `aoTimeNote` only use these. With M1 the pieces change as follows:
- shape keys: masked-text hashing → name-masked cabinet vectors;
- clustering: runs on those vectors;
- pruning: becomes plan step 4's "lowers the guesser's surprise the next day".

## Results (toy, synthetic; seeds 2 + 3; `node test/patterns-eval.js`)
| Pass mark | Result |
|---|---|
| analogy: shape recall@5 ≥ plain + 20 | **FAIL**: 100 vs 100 on both seeds (plain already at the ceiling) |
| analogy: same-name recall drop ≤ 2 | PASS: 0 drop (75 → 75, 57.8 → 57.8) |
| patterns: planted found ≥ 80 % | PASS: 100 %, 100 % |
| patterns: spurious ≤ 10 % | PASS: 0 %, 0 % |
| "what follows" right ≥ 70 % | PASS: 100 %, 100 % |
| model calls while patterns are made | PASS: 0 |

- **Analogy is "proven wrong" by the registered rule (shape ≤ plain).** The honest reading: my synthetic set was too easy for plain
  recall, so the test couldn't tell the two apart. In each shape, the fixed words ("texted", "moved to", "cancelled the") are shared
  by every instance, and brand-new names match nothing, so plain bag-of-words already finds a same-shape note in the top 5.
- Post-hoc diagnostic, not a pass mark: ranking by shape alone puts a same-shape note first 100 % of the time (plain 98–100 %), and
  fills 100 % of the top 5 with same-shape notes (plain 91–95 %).
- Next step (one change, not run): a harder fixed set where same-shape instances share few fixed words. Proposed pass mark: shape
  recall@5 ≥ plain + 20 on held-out seeds. Proven wrong if shape ≤ plain.
- Patterns passing on planted sequences among word-salad filler is a **toy** result. Real observations repeat a lot ("Front app:
  Safari…"), so real patterns will include habits that are true but dull. The real-path day made 6 patterns, 2 of them that kind.

## Suite (full suite from desk/, `node --test --test-concurrency=2 test/*.test.js`)
- **Baseline** at HEAD 1744a238e (before any change), 1 run: 721 pass, 3 fail. The three were "first-reply thinking cap" (known
  flaky), "Warmer: warms when the gateway comes up" (known flaky) and "8192-token context" (known).
- **Task B alone:** a `git archive` copy of commit 4f1526e29, so Task A's uncommitted work is left out. 3 runs, 37–38 s each, no hang:
  - run 1: 750 pass, 3 fail (thinking cap, Warmer, 8192);
  - runs 2–3: 752 pass, 1 fail (8192).
  - These are the same known failures as the baseline. **No new failure.**
- **Shared worktree** (Task A's uncommitted files in it too), 6 runs, no hang. Extra failures appeared only in Task A's files, all in
  flux while it worked:
  - `checker.test.js` "K thinking-Mote tries";
  - `imagine.test.js` "imagine L1…";
  - `speakometer.test.js` "main: the speak-o-meter looks ahead…";
  - `imagine.test.js` "main wires the meter…";
  - `motes-bored.test.js` "chat and typing stop every Mote…", which reads Task A's uncommitted main.js/motepool.js edits.
