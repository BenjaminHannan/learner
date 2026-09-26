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
