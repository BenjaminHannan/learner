Rent run 336 — fetching sealed specs and verifying budget.
Pre-flight looks good — checking credit and building the sealed tree.
Found a candidate GPU — verifying the sealed code tree before renting.
Both seals pass locally — proceeding to rental.
No conflicts — searching for the cheapest 5090 and renting.
Instance is booting — preparing weights and model files meanwhile.
GPU is live — copying code and reader weights.
Files verified — setting up the run environment.
Setup pattern is clear — unpacking and provisioning the GPU.
Reader assembled — installing dependencies and downloading base model.
Seals pass on the rental — starting the three registered arms.
Arm P is running — monitoring progress.
Arm P done (40/40 lives) — launching arm T.
Arm T done — launching arm B.
All three arms finished — running the scorer.
Scoring complete — copying results back to the Mac.
All files verified — destroying the instance.
Results filed — appending the ledger line.
Push paths are staged — final verification.
Verdict: RAN — rent-336-registered executed once on a rented RTX 5090. No DUPLICATE, no SEAL-MISMATCH, no BUDGET-STOP. All PUSH files are on disk for the watcher.

Marks table (integer counts, scorer's mechanical lines only — pass/fail is for the thread's blind judges, not me):

| Item | Count |
|---|---|
| SEAL-code on rental | 223/223 OK, 0 failures |
| Bank SEAL on rental | 3/3 OK |
| Twin-b banner first line | 3/3 arms |
| P lives / rows | 40/40, 850 rows (663 user + 187 confirm) |
| T lives / rows | 40/40, 663 rows (663 user + 0 confirm) |
| B lives / rows | 40/40, 663 rows (663 user + 0 confirm) |
| P facts_saved / facts_total | 182/318 |
| P confirm_rows / clarify | 187 / 34 |
| P most_common_reply / distinct | 23 / 449 |
| P ms median / p90 | 770.3 / 1200.4 |
| P day1 kept / day1 saved | 121 / 125 |
| P creative with writes | 0/40; nosave with writes 0 |
| T facts_saved | 0/318; WRONG_CANDIDATE 187/242 asks |
| B clarify / most_common | 523 / 280; ms median 8.2 |
| Tracebacks (P, T, B, scorer) | 0, 0, 0, exit 0 |
| Files copied back, size+sha256 match | 13/13 |
| GPU / hours / dollars | RTX 5090 / 1.075 h / ~$0.54 (budget $4.00) |
| BASE commit / READER / self122 | 87179e5c… (match) / b4fd93a2… (match) / 5ca02173… (match) |
| Wall: P 602 s, T ~200 s, B 8 s, scorer ~20 s | exit 0 all |
| rent-336-registered live after destroy | 0 |

Every move: fetched; confirmed no run on builder-outbox; read all three mark files; offer-searched (5090, picked 45669065 at $0.5037 dph); rented 1/4 allowed (contract 52466807, 18:44:05Z); built combined tree (builder-outbox + main + self122 pt); verified seals locally then on rental; scp'd tree + READER (2 passes, sha match); pip + HF downloads; self122 route OK; ran P, T, B sequentially; scored; copied back; verified; destroyed 19:48:35Z; ledger appended; RESULTS-rent.md written. Never opened the bank, any judge_*.jsonl, or grammar_*.jsonl; quoted no reply; edited no sealed file.

Misses/deviations: (1) first P launch ssh timed out locally but had started remotely, so two identical P processes ran ~5 min; killed the older (PID 794), kept the banner-confirmed one (836) which finished 40/40 alone — T and B each ran once, sequentially. (2) READER upload needed a second scp pass. (3) I mis-transcribed one scorer number into RESULTS-rent.md (wrote 3, fixed to 16) before finishing — the filed line now matches score.log exactly.

What it means in plain English: the registered 40-life run actually happened, end to end, with all seals green and every file back on the Mac byte-checked. The joined agent (P) saved 182 of 318 facts and asked 187 follow-up confirmations; the plain twin (T) saved 0 facts; the base (B) asked 523 clarifying questions. This says the run is valid and ready for judging — it does not say the agent passes any mark, since the blind judges haven't graded anything here.

PUSH: artifacts/claude-e2e336-20260924/RESULTS-rent.md artifacts/claude-e2e336-20260924/run artifacts/claude-e2e336-20260924/score artifacts/fable-predictions-ledger.md
