Starting the rd-378u run — fetching refs and checking gates.
Duplicate gates clear — now pulling the proven setup details.
Setup recipe recovered — now starting the rd-378u rental run.
Rental 52779987 requested — waiting for it to boot.
GPU live — streaming the sealed tree and adapter.
Tree and adapter verified — installing the environment.
Environment passes — downloading base models.
Seals and self-tests pass — fetching data.
Data ready (3122 turns on convs 5-9) — rebuilding the writer.
Writer confirmed (dbcc8db5, rebuild route) — launching the notes write.
Write is running and the notes file is growing — entering the monitor loop.
Write complete (3122 turns) — running the score step.
Score done — reading the counts for the results table.
All compute done — copying back before destroy.
All hashes match on both ends — destroying the rental.
Rental destroyed and confirmed gone — writing the ledger line and results.
Verdict: rd-378u PASS — U1 and U2 both pass on the five unseen chats (5-9) through store v4; proved-wrong clause not triggered.

Marks table (any@10, categories 1-4, n=772, integer counts):

| Mark | Bar | A | B | Diff (points) | Result |
|---|---|---|---|---|---|
| U1 | B any@10 ≥ A+5 | 489 (63.3%) | 585 (75.8%) | +12.4 | PASS |
| U2 | no cat >3 below A | — | c1 +7.9, c2 +10.4, c3 +22.2, c4 +13.7 | worst +7.9 | PASS |
| proved-wrong | B ≤ A+1 | 63.3 (+1 = 64.3) | 75.8 | — | not triggered |

Per-category any@10: c1 A 85/140 → B 96/140; c2 A 109/164 → B 126/164; c3 A 18/45 → B 28/45; c4 A 277/423 → B 335/423. Report-only: @5 A 410/B 513, @20 A 569/B 646; lines@10 both 7720 (same lines shown, as designed); B via_note@10 6297; notes 2866 / turns 3122 (16 unparsed); write ms median 319.2, p90 595.8.

Every move: duplicate gate clear (no RESULTS.md on origin/main or builder-outbox, no live claude-notes-rd378u). Credit balance number: 7.912477276269769. Rented 1 of max 3: instance 52779987 (offer 39904635), RTX 5090, 16:38:31–17:24:54Z ≈0.773h × $0.5037 ≈ $0.39 of $0.80 ($0.72 kill line never reached). COMMIT c4f1bfca91fec9c299e18b10c0fd501ce54bb56b. TREE streamed, no Mac staging. ADAPTER streamed BensPC→rental through Mac with no copy kept, 6/6 hashes matched file-for-file. SETUP exact per spec. Import check: `2.11.0+cu128 5.17.0 0.21.0 NVIDIA GeForce RTX 5090 torchvision None`. BASE MiniCPM path + MiniLM exact path both confirmed. SEAL 13/13 OK; all 4 selftests PASS (RD378U, EP382-V4, RD378L, RD378L-REBUILD). DATA hash 79fa87e9… matched (MMLU pyarrow failure, immaterial as stated). Dialogs line: {"turns": 3122}. WRITER exit 0 via rebuild route, {"sha256": "dbcc8db5…88510", "match": true, …} + separate sha256 confirmed; Mac fallback unused. WRITE ran once: "wrote notes for 3122 turns on cuda" (~16.4 min, steady byte growth, no 10-min stall). SCORE line reported verbatim in RESULTS.md. Copy-back: all 5 files sha256-identical on both ends BEFORE destroy; destroy confirmed (still_there=False); one ledger line appended via cat >>; PUSH set force-staged (RESULTS.md, notes_confirm.json, ranked_turns.jsonl, ledger). Private files (dialogs59, notes59, per_question) in ~/rd378u-private/, outside git, never printed. No LoCoMo or note text quoted anywhere.

Deviations/misses: (1) three ssh foreground launches with trailing `&` kept the local session open until timeout — each command had started correctly, verified via ps/log before proceeding; (2) one transient ssh failure ("Undefined error: 0") on a status poll, retried fine; (3) created artifacts/claude-rd378u-20260926/ locally with mkdir -p since the worktree checkout predates that dir — new files only; (4) actual dph $0.5037 vs $0.469 search estimate. No step needed a retry; no budget pressure.

Compliance with the first-13-lines rules: additive only (3 new artifact files, 1 new private dir + contents, 1 ledger line via cat >>; nothing edited or deleted); fictional names only (no real names used); no secrets printed (key read only as $(cat …)); TEST-ONLY panels never touched; every move and miss reported here.

What it means in plain high-school English: on five brand-new long chats the search with notes found the right message for 96 more questions out of 772 than search without notes, while showing exactly the same number of messages, and it won in every question category. The "notes only looked good because they show more" worry doesn't apply here — both sides showed the same count. So the rd-378L gain holds up on unseen chats through the store the build would actually call, and store v4 goes to Month-end for the joined build per the registered plan.
