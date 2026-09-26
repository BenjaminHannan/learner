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
