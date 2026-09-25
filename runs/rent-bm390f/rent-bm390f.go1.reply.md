Renting the RTX GPU for the finishing run — fetching specs, seals, and credit gate.
Credit and duplicate checks are next.
Gates passed — building the code tree and hunting for an RTX 5090.
Cheapest reliable 5090 found — checking rental options.
RTX 5090 is live — copying the code tree and setting up.
Environment ready (torch 2.8.0, transformers 5.17.0) — downloading the three models.
Models downloading — waiting for all three snapshots.
All three models cached — running seal checks then data fetch.
Seals 8/8 and 4/4 OK — fetching benchmark samples.
Fetch is running — waiting for the sample hashes.
Fetch matches (1986/300/300, Linux hashes) — running rival load checks.
Quoting mangled that command — retrying via base64 to run it exactly.
Q2 loads (1881825088 params, as expected) — checking L12.
Both rivals load — running the long-prompt check on BASE.
BASE fits (3.95 GiB ≤ 8) — MODE=registered. Checking Q2 and L12.
All longctx pass — MODE=registered. Running smoke.
Smoke passes — launching the three registered lanes.
Lane 1 moving fast (27 GB free) — starting lane 2.
Both lanes healthy, 21 GB free — verifying Q2 part syntax before lane 3.
All three lanes running — monitoring progress.
Q2 part 1 done (rows=304 as expected) — launching part 2.
T, L12, Q2p2 all done with expected rows — chaining C, L12m, Q2p3.
L12m done (rows=300) — chaining L12g.
C done (rows=1986) — chaining Tm.
Lane 2 complete; Tm and Q2p3 done — chaining Tg and Q2p4.
Lane 1 complete; Q2p4 done (rows=429) — launching Q2p5.
Q2 locomo complete (all 5 parts) — chaining Q2m.
Q2m done — launching the final command, Q2g.
All 14 commands done, exit 0 — copying run2 back.
All 14 files verified — collecting log details before destroying.
All counts match — destroying the instance.
Instance destroyed and confirmed gone — appending ledger and writing results.
Verdict: COMPLETE. rent-bm390f, the finishing run of bm-390, ran all 14 registered commands once each on a rented RTX 5090, all exit 0 with expected row counts. No SEAL-MISMATCH, DATA-MISMATCH, LONGCTX-FAIL, SMOKE-FAIL, CREDIT-STOP, BUDGET-STOP, or DUPLICATE. No file edited (new files only: run2/, RESULTS-rent2.md; ledger appended). Fictional names only in prompts. TEST-ONLY panels never opened, printed, or quoted — benchmark files only row-counted and hashed, never read item-by-item.

Report:

- Credit gate: 8.683039608599906 at first check; 8.651363460599903 re-check before rent. Above $5.00 both times.
- Duplicate gate: PASS (no run2 or RESULTS-rent2.md on origin/builder-outbox; no live rent-bm390f instance).
- Seals (tree root, before anything else): SEAL-code 8/8 OK; SEAL-finish 4/4 OK.
- Setup: tree = builder-outbox + main on top (161 MB tgz). pip = kit line + pyarrow (nothing else). torch 2.8.0+cu128, transformers 5.17.0. Only downloads: the 3 approved snapshots. BASE = models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc; Q2DIR = models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc; L12DIR = models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b. HF_HUB_OFFLINE=1 etc. after; every command under setsid/nohup with own log.
- Fetch (exit 0, 17:54:34Z–17:55:39Z), verbatim: {"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}
- Load checks: Q2 `Qwen3_5ForCausalLM 1881825088` exit 0 (17:59:16Z–17:59:21Z); L12 `Lfm2ForCausalLM 1170340608` exit 0 (18:00:58Z–18:01:01Z). Both RUN. (First Q2 attempt exit 1 `SyntaxError: invalid decimal literal` — my Mac-side shell quoting mangled the one-liner, not a model failure; retried via base64 pipe.)
- Long-prompt JSONs: BASE peak_gib 3.95, ok true (18:02:11Z–18:02:17Z) → MODE = registered, plain `python3 -B`, no wrapper. Q2 peak 8.0 ok true → RUN. L12 peak 4.57 ok true → RUN.
- Smoke: exit 0 (18:08:30Z–18:08:34Z), first `[bm390] smoke-1 plain questions=5`, last `wrote locomo_T.jsonl rows=5 convs=1`.
- Registered commands (each launched once, all exit 0): T 18:09:59Z–18:57:54Z rows=1986; C 18:59:11Z–19:05:19Z rows=1986; Tm 19:09:17Z–19:10:26Z rows=300; Tg 19:14:07Z–19:26:15Z rows=300; L12 18:13:11Z–18:55:34Z rows=1986; L12m 18:59:20Z–18:59:29Z rows=300; L12g 19:04:25Z–19:12:55Z rows=300; Q2p1 18:16:26Z–18:28:18Z rows=304; Q2p2 18:30:26Z–18:55:42Z rows=453; Q2p3 18:59:28Z–19:13:04Z rows=400; Q2p4 19:14:12Z–19:26:54Z rows=429; Q2p5 19:27:23Z–19:35:30Z rows=400; Q2m 19:37:03Z–19:37:30Z rows=300; Q2g 19:41:53Z–19:59:41Z rows=300. First lines: `[bm390] conv-26 …` (locomo) or transformers fallback warnings (L12/Q2/general). Last lines: the `wrote …` lines above.
- run2/*.jsonl rows (Mac wc -l, sizes+sha256 ALL_MATCH vs box): locomo_T 1986, locomo_C 1986, mmlu_T 300, gsm8k_T 300, locomo_L12 1986, mmlu_L12 300, gsm8k_L12 300, Q2 parts 304/453/400/429/400 (=1986), mmlu_Q2 300, gsm8k_Q2 300. Total 9744.
- Lanes: lane 1 18:09:59Z; lane 2 18:13:11Z with 27036 MiB free; lane 3 18:16:26Z with 21273 MiB free; no lane ever waited. Peak GPU sampled 20668 MiB used.
- Money: RTX 5090 32 GB, instance 52625917, 2.29 h × $0.494444/h = ~$1.13 of $3.00 budget (never near $2.60 stop; 1 rental). Copied back before destroy; destroy confirmed (0 rent-bm390f live); ledger appended.
- Tracebacks: none in any registered command (14/14 exit 0).

Deviations: (1) first Q2 load attempt failed on Mac-side quoting (reported above; retry clean); (2) Q2p2 had a ~12 min log gap (conv-41→conv-42) but was verified active (CPU TIME == elapsed, GPU 99%), so no watchdog destroy — finished normally; (3) Mac-side launch-ssh twice hit the 60 s tool timeout but launches were confirmed via polling (no duplicate launches; ps checked before every chained launch).

What this means in plain high-school English: the three missing arms finally ran to completion on a bigger Linux GPU where the memory problem from BensPC doesn't happen. The plain 1B model, the closed-book check, and both rival models all produced full answer files, plus the general-knowledge tests. Nothing was judged here — the files are just copied back so the benchmarks thread can score them. It doesn't change the FAIL on M1 against Rb; it fills in the numbers M4 and the rival comparison need.

PUSH: artifacts/claude-bm390-20260925/RESULTS-rent2.md artifacts/claude-bm390-20260925/run2 artifacts/fable-predictions-ledger.md
