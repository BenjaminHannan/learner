# mu-404 + mu-403 rental — RESULTS-rent.md (2026-09-26, re-run mu404b)

## Verdict: RUN-COMPLETE (four arms, 80/80 conversations each, scored; judging is thread-side)

Re-run of rent-mu404 (HOST-FAIL, ~$0.03). This task rented once, ran all four arms to
completion on one GPU, scored counts only, copied 9 files back sha-verified, destroyed the
rental. Registered run lives in `artifacts/claude-mu403-20260926/run/`.
Thread-side note: R's facts line shows `with_facts` 34 (< 40 in V404); V-validity calls per
PASSMARKS.md belong to judging, not this run.

## Gates (all passed before renting)

- Credit gate: `vastai show user --raw` credit = **5.094352626269782** (balance 0; >= 3.00, proceed).
- Duplicate gate: `git ls-tree origin/builder-outbox artifacts/claude-mu403-20260926/run` empty
  (0 files); no live instance labelled `claude-madeup-mu404` or `claude-madeup-mu404b` (0). Proceed.
- Reader route: depot REPORT (origin/builder-outbox) names instance **52755827**
  (`claude-director-depot`), live `running`; depot left running, never written to or stopped.
- Read first: kit 330-rent-kit.md (all, sections A-D), PASSMARKS.md (all), claude_mu404.py docstring (all).

## Rental (integer counts: 1 rental, 0 re-rents)

| # | Instance | Offer/host | GPU | dph $/hr | Window (UTC) | Outcome |
|---|----------|-----------|-----|----------|--------------|---------|
| 1 | 52775913 | 45669449 / host 406325 (mu-402 sibling class) | RTX 5090, rel 0.9975 | 0.5037037 | ~16:11 created, `running` ~16:15, destroyed 17:30:41, confirmed gone | run complete |

- Image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, disk 80 GB, label `claude-madeup-mu404b`.
- Image torch 2.8.0+cu128 with CUDA True (no upgrade, no torchvision issue). No second instance ever.
- Spend: ~1.33 h x $0.5037 = **~$0.67** of the $0.87 new-spend cap ($1.00 incl. prior $0.03).
- Post-destroy live `claude-madeup-mu404b`: **0** (verified via `vastai show instances`).

## Tree / reader / setup

- Tree streamed origin/main only (37 MB): scripts, design/v3/60-listener, gram360, relationtable,
  table237, abstain76, self122, self127, e2e02c SEAL-code, mu403-20260926. Plus self122_head.pt
  from Mac checkout (65,741 B), sha256 **5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25** OK.
- Deviation A: task list omits `artifacts/fable-nameval171-20260922`, which sealed code reads at
  runtime (first R launch crashed FileNotFoundError on wordlist171.txt). Streamed that dir from
  origin/main afterwards; wordlist171.txt sha256
  **29a4c692cbfdf8dd201ad44f0ad282e9da30fbcd79d2cf60d8098cbb528bf4ec** matches its SEAL line;
  rest of its SEAL OK except one unstreamed design-doc line (runtime-irrelevant).
- Reader: `vastai copy` dir-sync moved small files but the 2.1 GB model file repeatedly transferred
  then vanished (stale ESTALE dentries; see deviations). Single-file copy to a fresh name worked;
  dir swapped into spec layout. Final:
  `sha256sum /root/reader319/model.safetensors` =
  **e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76** MATCH (6 files, spec layout).
- Setup (kit C): pip transformers/safetensors/huggingface_hub/accelerate/numpy; snapshot_download
  MiniCPM5-1B at revision 87179e5c + all-MiniLM-L6-v2. BASE =
  `/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc`
  (commit hash **87179e5c1f455ef22e6223592d2d61351b525bfc**, as expected); MiniLM snapshot
  1110a243fdf4706b3f48f1d95db1a4f5529b4d41. route122 check returned a tuple (no raise).
- Seals/selftests (all under HF_HUB_OFFLINE=1): mu403 SEAL **14 OK / 0 FAILED**; e2e02c SEAL-code
  **336 OK** (chain exit 0); `mu404 selftest 5/5 ok`; `pick403 selftest 13/13 ok`;
  `readersha selftest 9/9`.

## Arms (launched ~17:03:30 UTC 2026-09-26, all four on the one GPU)

- Deviation B: first launch chained four `&`/`&&` in one ssh command — R started (then crashed on
  the missing wordlist, 7 dev lines), F/P/T never started (shell precedence bug). Cleaned logs +
  out404, relaunched each arm in its own properly detached ssh (setsid/nohup). Each arm has exactly
  one complete run; the crashed R partial was deleted, not used.
- R: readersha_wrap + twinb_wrap + panel382_run --arm claude_mu404:build_r --name R
  --model /root/reader319 --gen-model BASE --out out404 (READER_SHA set, SLEEP02C_ADAPTER unset)
- F: same with --arm claude_mu404:build_f --name F
- P: same with --arm claude_mu404:build_p --name P
- T: twinb_wrap + panel382_run --arm twin --name T --model BASE --gen-model BASE (no readersha)
- V0 (all met, run kept): logR/logF/logP line 1 =
  `readersha: reader weights sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 match READER_SHA`;
  `mu404: arm R404; adapter loaded = none; ...`, `mu404: arm F404-nofacts; adapter loaded = none; ...`,
  `mu404: arm P403-sysline; adapter loaded = none; ...`.
- Progress: one `[382/chat/<arm>] dev403-NN` line per conversation, 80 each (R/F/P 1-80, T 1-80).
- End-of-run facts lines:
  - R: `mu404: facts {'calls': 318, 'with_facts': 34, 'facts': 36, 'blanked': 0}`
  - F: `mu404: facts {'calls': 318, 'with_facts': 34, 'facts': 36, 'blanked': 34}`
  - P: `mu404: facts {'calls': 318, 'with_facts': 34, 'facts': 36, 'blanked': 0}`
- Exit codes: **0, 0, 0, 0** (0 `traceback` in all four logs; facts lines via atexit; all four
  chat_*.jsonl written complete; no processes left; codes inferred, PIDs not wait()ed).
- Wall minutes (launch ~17:03:30 to output mtime): T **~13** (chat_T.jsonl 17:16:34),
  R/F/P **~23** each (chat_R/F/P.jsonl 17:26:04/04/05). Median ms/turn: R **2094.8**,
  F **2133.7**, P **2157.0**, T **1774.0**.
- Rows per arm: **446 / 446 / 446 / 446** (expected every turn of 80 conversations = 446). items 80.

## Score (counts only; chat_pair_*, chat_turns_*, grammar_* files never opened)

`claude_panel382_run.py --panel chat --panel-dir <devchat> --score out404 --names R,F,P,T` exit 0.
summary_chat.json counts (panel chat, items 80):

| arm | messages | distinct_replies | most_common | events_on_non_teach | think_turns | think_numeric (right) | ms_median |
|-----|----------|------------------|-------------|---------------------|-------------|----------------------|-----------|
| R | 446 | 364 | 28 | 78 | 46 | 37 (11) | 2094.8 |
| F | 446 | 364 | 28 | 78 | 46 | 37 (11) | 2133.7 |
| P | 446 | 365 | 28 | 78 | 46 | 37 (11) | 2157.0 |
| T | 446 | 390 | 6 | 0 | 46 | 37 (9) | 1774.0 |

(ask_known/ask_known_right/ask_unknown/ask_unknown_dont_know all 0, all arms.)
Scorer-side note (not opened): out404 held chat_key_F/P/T but no chat_key_R, chat_pair_F/P/T but
no chat_pair_R, chat_turns_R + grammar_chat_R only. Counts unaffected; none copied back.

## Copy-back (9 files, sha256 match both ends before destroy)

`artifacts/claude-mu403-20260926/run/`: chat_R.jsonl (129,598 B,
b7ad3acf...897e3), chat_F.jsonl (129,749 B, 09e43b1e...5ae1), chat_P.jsonl (129,057 B,
22a57b0e...5cd1), chat_T.jsonl (262,785 B, 7b096aec...9bf), summary_chat.json (1,259 B,
5f95fa8c...98e920), logR.txt (2,626 B, 0c9242ee...8b19), logF.txt (2,644 B, bacd8d67...0e8a),
logP.txt (2,643 B, 20ba2f72...02c8a), logT.txt (2,111 B, 14e83431...5a112). No weights pushed.

## Deviations (every deviation)

1. **Tree list omission (task spec)**: streamed extra `artifacts/fable-nameval171-20260922` from
   origin/main after R crashed FileNotFoundError on wordlist171.txt (7 dev lines in, no output
   written). Seal-verified; one SEAL line (unstreamed design doc) unreadable, runtime-irrelevant.
2. **First launch misfire**: single-chained `&`/`&&` ssh left F/P/T unstarted and R doomed by (1);
   cleaned and relaunched properly detached. One complete run per arm; crashed partial deleted.
3. **Reader copy flakiness**: dir-sync `vastai copy` failed 3x on the 2.1 GB file (full transfer
   then ESTALE vanishing dentries); fresh-name single-file copy + dir swap fixed it, sha verified.
   Unremovable `/root/reader319_bad` junk dir left on rental (rental destroyed anyway). Depot untouched.
4. **Arm start time approximate** (~17:03:30, inferred; parallel ssh clients timed out under load,
   server-side launches confirmed via 17:04 file dates). End times exact (file mtimes).
5. **Exit codes inferred 0** (zero tracebacks, complete outputs, processes gone; no wait()).
6. **No credit re-check**: single rental, no re-rents, so the re-rent gate never triggered.
7. **Scorer wrote unrequested files** (pairs/turns/grammar/keys) on the rental; listed, never opened,
   never copied back. No TEST-ONLY panel exists in this task (DEV devchat only); none opened.

## Budget ledger

- Prior rent-mu404: ~$0.03. This task: 1 rental, ~1.33 h x $0.5037 ≈ **$0.67** (cap $0.87 new).
  Thread total ≈ $0.70 of $1.00 ($2 thread fund: $0.36 mu-402 + this). Credit at gate 5.0944.
- Ledger line appended to artifacts/fable-predictions-ledger.md.
- PUSH (watcher): artifacts/claude-mu403-20260926/run artifacts/claude-mu403-20260926/RESULTS-rent.md
  artifacts/fable-predictions-ledger.md (force-add; artifacts/ is git-ignored). No weights.

(End of file)
