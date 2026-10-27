# bm-398e RESULTS: a copy-only span trimmer (benchmarks thread, written 2026-09-26 18:17 UTC)

**Verdict: FAIL, and proved wrong.** The trimmer made the plain 1B's LoCoMo answers shorter (median 10 words to 6),
and the word-overlap score rose from 27.50 to 30.86. That is below the pass bar of 37.07, and below the proved-wrong
line of 32.39 (a fixed rule that deletes the question's words). Blind judges found no more right answers: 104 of 297
trimmed against 107 untrimmed. It is registered as sealed (PLAN.md, AMEND-1.md 9e03eb1ec) and does not change. Every
LoCoMo number is "after using LoCoMo for development". Counts only. An independent recount (its own script, key and
labels only) agrees on every blind count.

## Marks
| Mark | Needed | Got | Result |
|---|---|---|---|
| X1: TT F1, categories 1-4, all ten chats | ≥ 37.07, with the TT − T interval above 0 | 30.86 (TT − T +3.36, 95% interval +2.46 to +4.48) | FAIL |
| X2: blind right answers kept | TT A ≥ T A − 3 = 104 | 104 | holds (at the bar) |
| Proved wrong | TT F1 ≤ 32.39 | 30.86 | yes |

## Blind check (bm-398d's 297 questions, judges see the evidence; 4 main judges and 1 relabel judge)
| Arm | A right | B | C partly | D wrong | E don't know |
|---|---|---|---|---|---|
| T: plain 1B, whole chat, untouched | 107 | 5 | 63 | 117 | 5 |
| TT: the same replies, trimmed | 104 | 4 | 60 | 124 | 5 |

- TT − T is −3 right answers (−1.0 percentage points; 95% interval by conversation −2.5 to +0.7 points). Gained 4,
  lost 7.
- No-harm report (D and E; this PLAN predates the D/E rule, so this is report only): wrong answers rose 117 → 124
  (+7). "Don't know" stayed at 5. The T-to-TT table shows where: C→D 8, B→D 1, A→D 1, against D→C 3. Trimming
  turned some partly-right answers into wrong ones.
- The T-to-TT table: A→A 100, A→B 1, A→C 5, A→D 1, B→B 3, B→C 1, B→D 1, C→A 4, C→C 51, C→D 8, D→C 3, D→D 114,
  E→E 5.
- 184 of 297 trimmed replies equal the untrimmed reply. Relabel agreement is 59 of 60.

## Word-overlap detail (report only)
- By category (T → TT): single fact 24.37 → 24.44; dates 19.46 → 24.09; multi-hop 16.07 → 17.28; open 32.92 → 37.15.
- By half: first five chats 27.55 → 30.05; last five 27.44 → 31.65.
- Of 1,540 questions, 1,242 had candidates (lines over 3 words). By overlap, 264 gained and 96 lost. On 68, the
  overlap dropped to zero.
- The fit on code-made chats: LAMBDA 0.0, BETA −4.0. BETA is at the edge of its grid (−4 to 8), so the fit wanted
  an even stronger push away from keeping whole lines than the grid allowed. The fit half went from 55.21 to 59.56
  and the check half from 56.14 to 56.89 (+0.75).
- The code-made drafts were already short (median first line 7 words, against 10 on LoCoMo), and their untrimmed
  F1 was about 55, against 27.5 on LoCoMo. So the fit set was not like the answers it had to trim.

## Predictions
| Prediction | Held? |
|---|---|
| P1 (40%): X1 passes. Point guess TT F1 36 | no (30.86) |
| P2 (70%): X2 passes | yes (104, exactly at the bar) |
| P3 (30%): PASS | no |
| P4 (85%): not proved wrong | no |
| P5 (70%): check-half F1 on code-made chats rises by at least 10 | no (+0.75) |

## What it leads to
- Per the PLAN, X1 failed and X2 held, so "a better picker is needed". It crossed the proved-wrong line, though,
  and the Redirect (Ben, 16:04 UTC) says bm-398e finishes as a report and is not extended. So the trimmer stops here
  and goes into no build. That fits the training-data rule too: its two numbers were fitted on chats built from
  Claude-written patterns (AMEND-1).
- The finding for problem #4 ("answers too long, right less often than Qwen"): shortening an answer after the fact
  raises the word-overlap score a little but adds no right answers. Blind, it cost 3 right answers and added 7
  wrong ones. It is the same lesson as bm-397t and bm-398r: the F1 gain is wording. The gap to Qwen is finding and
  reading the right lines (bm-398d), not length.
- Brain first (a textbook-level guess): people don't write a long answer and then cut it down. They recall the
  fact, then say it. Answer length follows from what was recalled. Here that points to the reasoner and memory
  path (what is recalled), not to a post-editor on the talker.

## Deviations and disclosures
- Span scores were made on a rented RTX 4090 (bf16, torch 2.11.0, transformers 5.17.0), per AMEND-1, in about
  11 minutes of GPU time ($0.17, RESULTS-rent.md on builder-outbox). Drafts were made on this CPU (fp32) before
  the switch.
- The rental installed nltk (the sealed scorer imports it) and upgraded torch per the rent kit. Lane 2's first
  launch had the wrong working folder and wrote nothing; it was relaunched once, unchanged.
- The PLAN's header time ("~14:15 UTC") was an estimate, not `date -u` (AMEND-1).
- Fit, apply, score and the blind check ran here as the PLAN says. Outputs: PARAMS.json (sha256
  7bf2607c…6244), TT replies (1,986 rows, 1,242 trimmed, sha256 078a1878…b790, kept in the scratchpad because they
  hold benchmark text).

## Files
- PARAMS.json, score.json (official F1 and the bootstrap), jscore.json (the blind check), judge/key.json (item →
  question id and arm), judge/labels/*.jsonl (item and label only).
- Cost: $0.17 of the $0.35 rental cap. The Benchmarks thread has now spent about $1.28 of its $2, by its own
  count; the Director's ledger is the record.
