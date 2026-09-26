# mu-402 RESULTS (rented GPU run, 2026-09-26)

Verdict: RUN COMPLETE, V1 VALID. All three arms finished 80/80 conversations on the one
rented GPU (RTX 5090, instance 52757517). V1 load lines exact. No traceback in any final
log. No code edited (all runs used origin/main bytes). M1/M2/M3/PASS-FAIL are NOT decided
here: judging is blind and happens in the thread.

## Credit / GPU / BASE
- Credit at gate (`vastai show user --raw`): 5.499236376269863 (balance 0). At destroy:
  8.266691426269865 (balance 0; account auto-refilled mid-task).
- GPU: NVIDIA GeForce RTX 5090, 32607 MiB. Instance 52757517 (offer 45669386, host 406325),
  image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, disk 80, dph 0.5037037037037037.
  torch 2.8.0+cu128, CUDA True.
- BASE: /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  (snapshot_download with revision='87179e5c1f455ef22e6223592d2d61351b525bfc'; BASE commit
  hash 87179e5c1f455ef22e6223592d2d61351b525bfc). all-MiniLM-L6-v2 snapshot
  1110a243fdf4706b3f48f1d95db1a4f5529b4d41. No other model downloaded.
- route122 check: no raise (route122('what is your name?') -> D8, conf 0.9732, guard pass).

## Seal / selftest / adapter
- `sha256sum -c artifacts/claude-mu402-20260926/SEAL.sha256.txt`: every line OK (7/7).
- `sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt`:
  336 OK, 0 FAILED.
- `python -B scripts/claude_mu402.py --selftest`: "mu402 selftest 7/7 ok".
- Adapter on rental: sha256(adapter02c.pt) =
  a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 (required value;
  match). Sidecar adapter02c.json from origin/builder-outbox placed beside it (bytes only,
  never opened). self122_head.pt sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match).

## V1 (from final logs)
- logA: "mu402: adapter loaded = /root/adapter/adapter02c.pt; layers = ['330a_334', 'rec360',
  'cre333d', 'think299b', 'chat338b', 'vary330c', 'gram360', 'delivered02c', 'turnlog323', 'seed402']"
- logB: "mu402: adapter loaded = none (B = 0, base 1B); layers = ['330a_334', 'rec360',
  'cre333d', 'think299b', 'chat338b', 'vary330c', 'gram360', 'delivered02c', 'turnlog323', 'seed402']"
- No "refusing to load" in any log. V1 HOLDS (also present in the preserved first-attempt
  crash logs before the crash point).

## Rows per arm (expected: every turn of 80 conversations)
- A: 402 rows, 80 items. B: 402 rows, 80 items. T: 402 rows, 80 items.
  (devchat/items.jsonl has 80 conversations of 4-7 turns; 402 = 5.03 turns/conv mean.)
- Progress lines per log: 80/80/80 (`[382/chat/<arm>] dev402-NN`).

## Exit codes
- Numeric codes not captured (all three launched detached via setsid/nohup, supervisor shells
  long exited). Clean-completion evidence per arm: 80/80 progress lines, the runner's
  end-of-main `write_text` output file present (chat_A/B/T.jsonl), no Traceback in any log,
  zero panel382 processes left. Score step exit 0.

## Wall minutes per arm (UTC 2026-09-26)
- T: launch 14:09:16, chat_T.jsonl mtime 14:15:17 -> 6.0 min.
- A: launch 14:15:15, chat_A.jsonl mtime 14:25:33 -> 10.3 min.
- B: launch 14:18:38, chat_B.jsonl mtime 14:31:00 -> 12.4 min.
- Rental live 14:03:48 -> destroyed 14:36:01 (~0.53 h). Under the 75-min cap.

## Median ms per turn per arm (summary_chat.json counts)
- A ms_median 1212.5. B ms_median 1104.1. T ms_median 926.1.

## summary_chat.json counts (from `--score out402 --names B,A,T`, counts only)
{"A": {"ask_known": 0, "ask_known_right": 0, "ask_unknown": 0, "ask_unknown_dont_know": 0,
"distinct_replies": 328, "events_on_non_teach": 0, "messages": 402,
"most_common_reply_count": 28, "ms_median": 1212.5, "think_numeric": 39,
"think_numeric_right": 11, "think_turns": 46}, "B": {"ask_known": 0, "ask_known_right": 0,
"ask_unknown": 0, "ask_unknown_dont_know": 0, "distinct_replies": 331,
"events_on_non_teach": 0, "messages": 402, "most_common_reply_count": 28,
"ms_median": 1104.1, "think_numeric": 39, "think_numeric_right": 11, "think_turns": 46},
"T": {"ask_known": 0, "ask_known_right": 0, "ask_unknown": 0, "ask_unknown_dont_know": 0,
"distinct_replies": 358, "events_on_non_teach": 0, "messages": 402,
"most_common_reply_count": 12, "ms_median": 926.1, "think_numeric": 39,
"think_numeric_right": 14, "think_turns": 46}, "items": 80, "panel": "chat"}

## Dollars (running total dph x hours)
- Rental 1: contract 52756154 (offer 46753302, 5090, dph 0.49629629629629624), ~0.080 h -> ~$0.04.
  Dead: host docker proxy refused (registry-1.docker.io: proxyconnect 127.0.0.1:7890 refused).
- Rental 2: contract 52756713 (offer 43165161, 5090, dph 0.49629629629629624), ~0.071 h -> ~$0.04.
  Dead: same host-side proxy failure.
- Rental 3: contract 52757240 (offer 50338871): create returned success False (host full),
  never ran -> $0.00, destroyed as husk.
- Rental 4: contract 52757517 (offer 45669386, 5090, dph 0.5037037037037037), ~0.53 h -> ~$0.28.
- TASK TOTAL ~$0.36 of the $1.00 budget (never near the $0.90 kill line). No re-rent needed
  beyond the 4 creates above.

## Deviations (every one)
1. `scp -3` BensPC->rental failed (host key through the -3 path). Fallback per task: one mktemp
   dir on the Mac (/var/folders/.../T/tmp.yGiOXewLub), staged only adapter02c.pt (16.5 MB),
   copied to rental, then `rm` + `rmdir` by exact path; verified gone. Nothing else touched the Mac.
2. 4 instance creates vs task "(max 3 rentals)": rentals 1-2 died of host-side docker-proxy
   failure (~$0.08 combined), rental 3 was a success-False husk ($0), rental 4 ran the task.
   Live-rental count 3; create count 4 (kit allows 4). All failed ones destroyed; post-destroy
   zero rent-mu402 live (verified via `vastai show instances`).
3. Task tree list omitted artifacts/fable-self127-20260922, which the sealed 02c stack needs
   at runtime (fable_self127.load_deltas reads deltas127.json on every turn; bank path also
   resolves inside that dir). First A/B launch crashed on turn 1 with FileNotFoundError
   (traceback: panel382_run -> e2e336_run.one -> seeded402 -> ... -> fable_self127.py line 64
   load_deltas). Fix, environment-only: streamed that one committed dir from origin/main as
   opaque bytes (hash-verified deltas/bank vs `git show` bytes, contents never opened by me),
   preserved the crash logs (run/logA_crash.txt, run/logB_crash.txt), relaunched A and B with
   the exact specified commands. No code touched. V1 re-verified in fresh logs.
4. My first B relaunch had a shell-chaining bug (`cd` inside a `&&`-list before `&`), so B
   started in /root and died instantly with "can't open file '/root/scripts/claude_twinb_wrap.py'"
   (observed, 98-byte log overwritten by the correct relaunch from ~/tree). A was unaffected.
5. Exit codes numeric: not captured (detached launches); completion evidence listed above.
6. Score writes `summary_chat.json` (runner's `summary_<panel>.json` convention), copied back
   under that name; task text said "summary.json".
7. Label `rent-mu402` used exactly as the task ordered (kit's `claude-<thread>-<job>` prefix
   convention not applied; sibling rentals also use `rent-*`).
8. First-attempt A/B PIDs 768/769 (crashed); final A PID 964, final B PID 1058; T PID 770.

## Copy-back (verified before destroy)
- run/chat_A.jsonl 1abe4306781becf908267b2185f13d1ded49518f855d9e0bf4bdc21b1df701e8 (135366 B)
- run/chat_B.jsonl 46f97e298e98cf5711e3debf0f5499800c7b57ff2be4be938dc4b7c3e83f06eb (130787 B)
- run/chat_T.jsonl dc4bc933f61b7a4ae607998c5b457d35bc0e233467a345c46fe984118ed51533 (228757 B)
- run/summary_chat.json 7d9771acfdb6141034a9371c99eefe37a8965ed10e099f536f2cbadb802b4359 (951 B)
- run/logA.txt, logB.txt, logT.txt + logA_crash.txt, logB_crash.txt (hashes match rental).
- Adapter (.pt) never on git. No weights pushed. Notebook untouched. No TEST-ONLY panel opened;
  judge/pair/grammar files from --score never opened (counts taken from stdout JSON only).
