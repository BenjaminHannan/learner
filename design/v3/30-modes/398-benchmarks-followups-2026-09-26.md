# Benchmarks: what was taken from the evaluator's reply (Ben, 02:11 UTC 2026-09-26), and what is queued

Sections 7 (retrieval), 9 and 10 (resources). Every claim was checked against the code first. No registration was
touched. Ben's overnight goal comes first; the queued items run after it, with their marks fixed here.

## Taken now (before the 07:30 UTC cutoff)
- Heard-only answers and a crash-safe store (sec 7, sec 10). scripts/claude_ep382_store_v3.py (7b9345d79, selftest
  10/10) makes recall() heard-only by default: notes can come back only when asked for explicitly. A torn last line
  is kept aside instead of stopping start-up, and every write is fsynced. Month-end took it into 0.2c (346fdad83).
  With no notes and no torn line, it returns exactly what v2 returns.
- bm-397 finishes as registered (sec 9). Its F2 audit already counts the reviewer's worry about picking one side of a
  contradiction ("picked": draft B becoming final A, bar ≤ 3). It also judges the draft's and the final's
  correctness separately, blind, and counts "lost" (right becoming wrong). Format is the scorer's job, and it is the
  same for every arm.
- Resources are reported beside every benchmark result from now on (sec 10, report only), for each arm:
  models resident, total parameters, context used, sampling (greedy or n samples at temperature T), median ms per
  question and the hardware. The first use is bm-391's scorecard and 0.2c's rows.

## Queued (register as written here before any run; nothing runs before 11:00 UTC)
### bm-398: evidence expansion around recalled lines (sec 7)
- One change: each recalled heard line brings its neighbours (one before, one after, same session), with speaker and
  date. It stays inside the same context-token budget as today's top 20: fewer lines are recalled so the total
  fits. Everything else stays fixed: store v3, answer prompt, guards, route, trim.
- Test bank: fresh long conversations with labelled evidence lines, written blind by agents, sealed before any run.
  Not LoCoMo (practice) and not LongMemEval (final exam).
- Marks: complete-evidence recall +10 points or more AND blind-judged correct answers +5 points or more, both vs
  today's top 20 at the same budget.
- Proved wrong if complete-evidence recall rises but correct answers do not. That would mean expansion only adds
  distracting text.
- Prediction: recall +10 passes 60%; answers +5 passes 35%.

### bm-397b: an explicit final-answer field (sec 9), only if bm-397 leaves a gap
- One change: the answering prompt asks for a separate final-answer line, and code keeps the explanation apart from
  it. The same rule is used for every compared model.
- Marks: +5 F1 or more on fresh answer-extraction data (not LoCoMo); a loss of at most 1 point in blind-judged
  correctness; 0 final answers deleted across at least 60 constructed cases (numbers, option letters, names, dates,
  lists).
- Proved wrong if overlap rises while judged correctness falls.

## Where the reply is wrong or out of date (checked)
- "Crash-safe episodic writes remain open": now fixed in 0.2c (store v3). The larger idea, building the index from
  the notebook's durable log with idempotent indexing, is still open. It belongs to Month-end and the Director.
- "No notes today does not make the unrestricted path safe": agreed, and it is now closed structurally, because the
  answer path is heard-only by default.
- "Qwen is about twice the chat generator's size": true for the generator alone. But the joined assistant also keeps
  a second full MiniCPM5-1B, the fine-tuned reader (lis-300 PASSMARKS: base openbmb/MiniCPM5-1B). So its resident
  weights are about 2B, the same size class as Qwen3.5-2B. The plain-1B rows (T) are the 1B-vs-2B comparison; the
  agent rows are roughly 2B vs 2B.

Correction (02:16 UTC): the third point above misreads the reply. Its section 10 already says the complete assistant
also holds a separately fine-tuned reader, and asks us to stop calling the whole system "1B". That is the same point,
not an error. Only the first two are out of date, and both have been fixed since the reply was written.

## Also queued (02:20 UTC; section 7's answer-boundary parts, agreed with Reading facts, which owns the note checker)
- The evidence set per personal claim: each memory answer internally records the claim, the supporting heard-line
  ids and spans, the speaker, the time, and any derivation. A word-overlap check is not a support check.
- Notes reach answers only through their cited heard lines. Recall itself is already heard-only (store v3).
- An attributed-quote fallback until a support check passes: "On <date>, <speaker> said: '<exact line>'", given
  instead of an unsupported paraphrase. It needs its own test, with marks fixed before any run: unsupported
  personal answers must not rise, and useful answers must rise. It is registered separately from bm-398.

## Queued after bm-397's FAIL (03:00 UTC): teach the answerer to answer short (bm-397's registered next step)
bm-397 failed (+0.28 F1; the prompted 1B handed back its draft unchanged 1,019 of 1,533 times). Its plan, registered
before the run, sends the next dollar to evidence-conditioned training, not to more prompt-shortening.
- One change: a LoRA on the plain MiniCPM5-1B, trained to answer a question from given chat lines in the fewest
  words that carry the answer. Training data comes only from non-benchmark conversations (the project's own
  fictional banks, or code-made from templates), with short answers taken from code-made labels or the GLM teacher.
  Never Claude-written answers, and never LoCoMo, LongMemEval, GSM8K or MMLU items.
- Marks, fixed before any run:
  - LoCoMo cat 1-4 F1 of the trained 1B, whole chat, ≥ T + 5.0 (32.50), with the conversation-level interval above 0;
  - GSM8K and MMLU within T − 3 points (bm-390's M4);
  - blind-judged correctness on 300 sampled LoCoMo questions no lower than T's (the same A–E labels as bm-397 F2);
  - it must not become an "I don't know" machine: abstentions on cat 1-4 ≤ T's + 20.
- Proved wrong if F1 gains under +2: then training for brevity does not reach the content either.
- Needs a GPU (BensPC or a rental). Not before Ben's OK on money.

## bm-397t result (05:20 UTC) and what is queued next
bm-397t ran that step (artifacts/claude-bm397t-20260926/RESULTS-score.md): registered FAIL.
- LoCoMo F1 rose 27.50 → 37.07 (A1 passed), and abstentions stayed within the bar (A4 passed).
- GSM8K fell 191 → 42 (A2 failed): the model stopped showing its working.
- Blind correctness went 112 → 107 of 300 against a bar of 109 (A3 failed). The F1 gain is shorter wording, not more
  right answers.
Queued, each one change, registered before any run, nothing before Ben's OK on money:
- bm-397u (training mix):
  - Change: the same recipe, plus two code-made parts. The first is made-up arithmetic word problems whose target is
    the base 1B's own step-by-step working, kept only when its final number is right (graded own drafts). The
    second is made-up unanswerable questions about the made-up chats, labelled "not mentioned".
  - Marks: bm-397t's A1-A4, plus confident wrong ≤ T's.
  - Proved wrong if GSM8K still drops below 182 while LoCoMo gains.
- bm-397m (routing):
  - Change: the bm-397t adapter is switched on only when answering from a chat (the memory path) inside the joined
    agent, and never for math or general questions.
  - Scoring: on the agent, not the plain 1B, after 0.2c.
  - Needs a check that the switch itself picks the right path. Month-end owns the agent; this does not join 0.2c.
- The next real gain on LoCoMo needs more right answers, not fewer words. bm-398 (evidence expansion) is the
  candidate.

## Revised after the outside review (Ben, 11:50 UTC; claims checked, see bm-397t RESULTS-score.md)
The review's order is taken. The "bm-397u" line above is withdrawn: it changed two things at once (math replay AND
unanswerable questions). Each experiment below is one change, registered before its run.
1. **bm-398d, evidence diagnostic (registered next, $0 CPU; artifacts/claude-bm398d-20260926/PLAN.md).**
   - The same judged 300 LoCoMo questions (those with annotated evidence) are answered by the plain 1B from four
     inputs: the right evidence lines (G), the right lines plus retrieved distractors up to 20 lines (GD), the
     store's top 20 (E20, exists), and the whole chat (T, exists). Qwen's whole-chat replies (Q2, exist) are added.
   - All five are blind-judged together; judges also see the annotated evidence lines.
   - It says whether finding, distraction or reading costs the most right answers. A fresh, independently written
     bank with evidence recorded at construction confirms it afterwards.
2. **Adapter isolation and routing.** Keep the base frozen and the LoRA unmerged, with an explicit bypass. Pass:
   bypass reproduces the base exactly, and switching between requests changes no later general answer. Two
   separate decisions: needs memory? needs calculation? Memory + math questions keep their working.
3. **Evidence-trained memory adapter.**
   - Practice: new code-made chats with similar facts about different people, corrections, negations,
     former vs current facts, lists of varying length, relative dates, arithmetic over remembered facts, and
     missing, partial and conflicting evidence. Lengths nearer LoCoMo's, with evidence at different positions.
   - Target: the shortest complete supported answer, with no word cap.
   - Held out: templates, entities and reasoning patterns, not only seeds.
   - Dev check: a real semantic checker (negation and alternatives count as wrong).
4. **Math replay, separately, only if 2 does not already protect math.** Verified worked solutions (code-checked
   steps); explicit task weights; report supervised tokens per task; pick checkpoints on memory correctness AND
   reasoning, not training loss.
- The copy-only finaliser is dropped. It checks vocabulary, not meaning.
- The next semantic audits include supporting context and Qwen.
- A replacement for the MMLU no-harm baseline gets its own registered evaluation. T's 50/300 mostly measures
  missing letters, so holding 50 protects nothing.

## bm-398d result (13:25 UTC; artifacts/claude-bm398d-20260926/RESULTS.md, recount agrees)
- D1 = "both". Right lines only: 137 of 297 blind-right; whole chat: 109; Qwen whole chat: 138.
- Even with the right lines, 160 are not fully right. Dates (cat 2) reach 17% and multi-hop (cat 1) 23%.
- D3 true, two questions from its line. Where the store missed evidence, adding it back gains +30.6 on 111 questions.
- D2 false (−6.1).
- Order kept, as the sealed plan says for "both":
  - the evidence-trained reader adapter first (step 3 above, with dates and multi-part questions weighted);
  - a retrieval change registered alongside at $0;
  - adapter isolation (step 2) as bm-398i, $0 on CPU. Month-end owns the router and bm-397m (agreed 12:50 UTC).

## After the Mac agent's report (Ben pasted 12:54 UTC; checked, reviews/mac-agent-locomo-length-2026-09-26.md)
Holds:
- the single-hop gap (cat 4: TS 42.5 vs Qwen 60.7);
- TS's far-fact loss, on cat 4 only (−10.2);
- the "the week before" habit (203 of 321 date replies);
- the practice chats were short (median 1.6k tokens against ~24k).

Corrected:
- Only 3 of the 203 "week before" replies are fully right, not 28.
- The question-word rule gives +4.9 over all 10 chats. It helps only T and lowers Qwen and TS.
- The proxy counts are T 110, TS 103, Qwen 128 (not 98, 86, 114).

Superseded: Qwen is now blind-judged (bm-398d: 138 vs T 109).

Not checkable here: GSM8K 188 with an extract step, and the six-tries headroom (68 vs 44 of 200).

Taken, one change each:
- **bm-398e (next, $0 CPU): a learned copy-only span trimmer on the plain 1B's untouched replies.** This is the
  direct fix for problem #4 (answers too long).
  - It is trained on the 1B's own drafts to made-up chats, never on LoCoMo.
  - Marks: F1 above the fixed rule (32.39 over all 10), no fewer blind-right answers than T, and GSM8K untouched
    (it never runs on math).
  - It is not the dropped bm-397 finaliser: it picks one contiguous span, so it can't delete a word from the
    middle. The blind check guards meaning.
- **The reader adapter (step 3) takes the report's causes into its practice set:** chats near LoCoMo length with
  evidence at every distance; many date phrasings, not one template; and why/how questions. It needs a GPU, from
  this thread's $2 (Ben 12:59 UTC; spent through the Director).
- **E3 (a picker over several tries):** waits until the six-tries headroom is measured here, with a registered
  plan.
- **E2:** done by bm-398d for Qwen. The MMLU letter-only baseline is already queued.
