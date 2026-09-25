# 390 public benchmarks: Premonition against models its size (benchmarks thread, 2026-09-25)

Ben, 01:49 UTC 2026-09-25 (/goal): "Make this model perform better on public benchmarks than other models its size."
Ben, 02:12 UTC: rivals under our own harness = both Qwen3.5-2B and LFM2.5-1.2B-Instruct.
Numbers for this line: bm-390 to bm-399 (rd-370..379 belong to the reading thread, 380 to the joined agent).

## Where things stand (checked today)
- Premonition 0.1 = lis-301 reader (a fine-tuned MiniCPM5-1B, 1.08B) + the base MiniCPM5-1B (1.08B, used by
  creative, think299b and chat338b) + MiniLM router (22M) + the notebook, hand-written reasoner and sleep.
  About 2.2B parameters in all, so fair rivals go up to ~2B.
- General tests: the base model is already the 1B-class leader on its makers' table (model card image
  public_leaderboard_en.png, thinking mode): MMLU-Redux 70.06 vs LFM2.5-1.2B 66.08, Qwen3.5-0.8B 61.50,
  Qwen3-0.6B 55.47; BBH 71.89 vs 57.32 / 54.58 / 47.86. That is OpenBMB's result, not ours. 0.1 calls the 1B
  with thinking off and starts knowing nothing, so on general tests our parts can only match it or lose.
  Our job there is "no harm".
- Memory tests are where our parts can win or lose on their own. LoCoMo (Maharana et al., ACL 2024; repo
  snap-research/locomo, CC BY-NC 4.0): 10 long chats between made-up people (5,882 turns), 1,986 questions in
  5 categories (1 multi-hop 282, 2 temporal 321, 3 open-domain 96, 4 single-hop 841, 5 adversarial 446).
  Official metric: stemmed token F1 (evaluation.py). Category 5 is a two-option choice whose official score
  gives full marks for any reply without "(a)" when option (b) is "No information available", so an agent
  that always abstains gets about half of it free. It is reported but never counted as a win.
- Published same-size LoCoMo numbers (A-Mem, arXiv 2502.12110, Table 1, checked in the PDF today; a different
  harness: their prompts, Ollama, top-k tuned per category), F1 for categories 1 / 2 / 3 / 4 / 5:
  Llama 3.2 1B + A-Mem 19.06 / 17.80 / 17.55 / 28.51 / 58.81; Llama 3.2 1B full context 11.25 / 7.38 / 11.90 /
  12.86 / 51.89; Qwen2.5-1.5B + A-Mem 18.23 / 24.32 / 16.48 / 23.63 / 46.00. Cited, never mixed into our marks.
- ARC-AGI-1 (asked by Ben 01:53): public (400 training + 400 evaluation tasks). TRM, 7M parameters, 44.6% on
  the public evaluation set with 2 tries (arXiv 2510.04871, Table 5, checked) after about 3 days on 4 H100s.
  Far over our $30 cap, and the loop reasoner belongs to the sleep research thread. Parked.

## The plan
1. bm-390 (tonight, BensPC; Ben asked for no rentals tonight). The starting line, nothing tuned: Premonition
   0.1 exactly as sealed for 336/336b (claude_e2e330c:build_330c) against plain MiniCPM5-1B with the whole
   chat in its prompt (T), the same model with the 10 best BM25 turns (Rb, "is it just a search engine?"),
   and the same model with no chat (C, contamination check). Plus the no-harm check: P and T on 300 seeded
   MMLU-Redux-2.0 items (error_type "ok" only) and 300 seeded GSM8K test items. Marks:
   artifacts/claude-bm390-20260925/PASSMARKS.md.
2. The two rivals Ben approved run in the same job on BensPC (downloaded there; Ben asked for no rentals
   tonight): Qwen3.5-2B (text model 1.88B) and LFM2.5-1.2B-Instruct (1.17B), thinking off, same code and marks.
   A rival that will not load on Windows with the job's Python is reported as not run.
3. After bm-390, LoCoMo becomes our practice test. Every later LoCoMo number is labelled "after using LoCoMo
   for development". Only aggregate counts from bm-390 go to other threads; nobody trains on LoCoMo text.
   Changes come one at a time from the owning threads (reader: rd-370..379; grammar; sleep; reasoner), through
   the coordinator, each with its own registered PASS first.
4. The final exam is LongMemEval (Wu et al., ICLR 2025; 500 questions: extraction, multi-session reasoning,
   knowledge updates, time, abstention). Nobody downloads or reads it until a 0.x build beats every same-size
   arm on LoCoMo practice. Then it is registered and run once, against the same rivals.

## Honest expectations (predictions are in the PASSMARKS)
- The reader is the bottleneck (336: 57% of taught facts saved; lis-317: the gate keeps 20 of 89 right reads),
  and LoCoMo's facts are chattier than our banks. Expect P to lose on F1 and win on not making things up.
- On general tests expect P at or below T: 0.1 routes some questions to "I'm not sure".
- What would count against the memory approach at this stage: P below T on single-hop questions (category 4)
  even in the question-only variant (P_bare). That would say storing facts with today's reader does not beat
  "keep the whole chat in the prompt" at 1B scale, and the reader work must close that gap before anything else
  is worth measuring.
