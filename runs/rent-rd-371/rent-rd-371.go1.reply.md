Starting rd-371 — fetching the latest instructions and verifying seals.
Credit confirmed and no duplicate rental — building the code tree and checking seals.
All seals verified — now finding a rental GPU within budget.
Rental is live — uploading the code tree and reader model.
Reader upload interrupted — resuming it.
Reader verified — downloading the base model and installing dependencies.
Data counts match (train 22,498 / dev 1,200) — starting verifier training.
Training needs a missing package — checking its imports, then installing.
Training is running cleanly — monitoring progress.
Training finished in under 6 minutes — now verifying on dev and sweeping the cutoff.
Cutoff is T_B = 0.9999 — scoring both dev gates.
Dev gates recorded — sealing run artifacts before the single panel read.
Panel read is underway — waiting for it to complete.
All panel gates complete — copying results and the verifier model back.
Result files verified — now pulling the verifier model to the Mac.
Everything is back on the Mac — destroying the rental.
Rental destroyed and confirmed — now writing the ledger line and result files.
All files are on disk (the watcher force-adds the ignored `artifacts/` PUSH paths). Wrapping up.
Verdict: FAIL. The learned verifier does not beat the 0.995 min-token cutoff — the PASSMARKS "proved wrong" clause fired.

Marks table (integer counts, scorer counts only):

| Mark | Bar | Measured (B vs A) | Result |
|---|---|---|---|
| V1 more right facts saved | B >= A+30 (136) | B 15 vs A 106 | FAIL |
| proved-wrong clause | B <= A+10 (116) | 15 <= 116 | TRUE |
| V2 safe | B wrong_turns <= 2 and <= A+1 (3) | B 0 vs A 2 | PASS |
| V3 no invention | B nofact_rows_with_save <= 1 | B 0 | PASS |
| G1 dev hits | B at T_B >= A at 0.995 | B 400 vs A 462 | FAIL |
| G2 time | B median <= A+400 (1357.9 ms) | B 976.6 vs A 957.9 | PASS |

Every move: fetched origin main + builder-outbox; verified all four seals OK from the tree root (lis300, lis301, lis318-data, readpanel371 in its dir); READER sha b4fd93a2…d21b890 matched on Mac and box. Credit $7.42 (no CREDIT-STOP). Rented 1x RTX 5090 as rent-rd-371 (instance 52641003, offer 52190811, billed dph $0.5037), running at once, destroyed ~20:32Z after copy-back; `vastai show instances` confirms 0 rent-rd-371 live. Cost ~0.74 h × $0.5037 ≈ $0.37 of the $1.50 budget. BASE openbmb/MiniCPM5-1B commit 87179e5c (expected). MiniLM/self122/route122 skipped per task. DATA: vdata train 22,498 / dev 1,200 exactly as expected (DATA.json). TRAIN: 2814 steps, 5.75 min, 7998.6 tok/s, batch 16, no OOM, dev loss 0.0145, merged sha 41a84ce6…257d86. Sweep: no grid value hit 0 wrong turns, so T_B = 0.9999 (largest). Panel panel.jsonl read exactly once by READER; all four step-6 commands EXIT 0. Model kept at ~/premonition-models/rd371-verifier-merged/ (sha matches seal); weights never in git. Never opened, printed, or quoted panel.jsonl, label_B*.jsonl, blind_input.jsonl, or changed_blind.jsonl — only scorer counts. The handoff/held BensPC copy was never run. Code never edited.

Misses/deviations: (1) First TRAIN attempt failed with `ModuleNotFoundError: No module named 'peft'` (kit pip line lacks it); installed peft 0.21.0 on the box (environment only, script untouched) and restarted — batch 16 held, no --batch 8 fallback needed. (2) Offer listed $0.469 but billed $0.5037; cost uses billed. (3) Scorer omits `nofact_rows_with_save` when 0, so V3 = 0 read from the absent key. (4) V1 missed by 121 facts, G1 by 62 dev hits.

What it means in plain English: the double-checker model was too strict — it threw away almost everything, saving only 15 right facts vs the plain cutoff's 106, on both dev and the sealed panel. It was safe (zero wrong saves) and fast, but safety without recall is useless here. What it doesn't mean: the reader is fine as-is (the cutoff still holds back 236 right facts), or that no verifier could ever work — just that this one, trained this way, lost.

PUSH: artifacts/claude-rd371-20260925/RESULTS.md artifacts/claude-rd371-20260925/DATA.json artifacts/claude-rd371-20260925/SWEEP.json artifacts/claude-rd371-20260925/SEAL-run.sha256.txt artifacts/claude-rd371-20260925/score_A.json artifacts/claude-rd371-20260925/score_B.json artifacts/claude-rd371-20260925/train_summary.json artifacts/claude-rd371-20260925/dev artifacts/fable-predictions-ledger.md
