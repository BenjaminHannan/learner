# ocdiag2 report (label lis320-ocdiag2, diagnosis only, nothing changed)

## Verdict

This job separates **helper version** (v1 vs v1.1) at low-to-moderate Mac load,
and it separates **moderate concurrency** (4 simultaneous v1.1 calls) from the
sequential case. It cannot separate **extreme load** (pilot 3 ran near load 185;
this job saw 1-minute loads of 22-87) and it cannot separate **prompt form**
(every prompt here is a real lis-320 dialog prompt, so there is no non-lis-320
control).

Counts: sequential v1 ok 2/2, parsed 2/2 (62.0 s, 337.7 s; 1-min loads 55.58,
47.05); sequential v11 ok 2/2, parsed 2/2 (92.0 s, 125.5 s; loads 47.46,
87.35); parallel v11 (4x same prompt, launch load 47.99) ok 4/4, parsed 4/4
(156.9 s, 457.7 s, 404.7 s, 71.3 s). Zero failures in 8 calls: helper version
alone does not explain pilot 3's 30/32 failures at the loads observed here,
and 4-way concurrency alone does not break v1.1 either. The remaining
un-separated suspects are extreme load (~185) and prompt-form x load
interaction. Note the slowness signal: one sequential v1 call took 337.7 s and
two parallel v11 calls took over 400 s yet still succeeded, matching the
"0 failures, only slow calls" pattern seen in the other threads.

## Provenance

- origin/main rev: 9c7c0de0557c0ca6a7dc080625b120f1f3e3808e
- helper shasums verified before any call: claude_glm_opencode.py
  3b597086511d18270cea2d2614027ea54f0e4142cf87e9a2c30a68b2ad4c5ad2,
  claude_glm_opencode_v11.py
  7a067cfba8fd147f342d46ed71449ab3e065c46eee3615a9b263a22da5c708c4 (both match).
- Job run window: 2026-09-26T21:08:36Z (task start) to 2026-09-26T21:33:45Z
  (last parallel call done). Waited for 000-lis320-ocdiag-mac to finish first
  (it ended ~21:14Z; this job's first GLM call started 21:15:32Z).
- GLM 5.3 Flash calls used: 8 of at most 10 (4 sequential + 4 parallel).
- Redaction: 0 lines matching key|token|auth|bearer|sk- (case-insensitive)
  found in any file copied to the repo, so 0 lines dropped; file paths in
  error/reply fields replaced with <path> (error fields were all empty).
- No TEST-ONLY panels read. All names in prompts/replies are the fictional
  seed names. Quoted reply text below is GLM model output, not Claude text.

## Sequential (one process, back to back)

1-min load is the load average printed by `uptime` immediately before each call.

- v1 s320-321-00004: load 55.58, 62.0 s, ok, parses.
- v11 s320-321-00004: load 47.46, 92.0 s, ok, parses.
- v1 s320-321-00001: load 47.05, 337.7 s, ok, parses (slow but succeeded).
- v11 s320-321-00001: load 87.35, 125.5 s, ok, parses.

## Parallel (4x v11 on p_s320-321-00004, launched at the same moment)

- Launch load (1-min): 47.99 at 21:26Z. End load after all 4 done: 22.66.
- par_1: 156.9 s, ok, parses. par_2: 457.7 s, ok, parses. par_3: 404.7 s,
  ok, parses. par_4: 71.3 s, ok, parses.
- DEVIATION: the 300 s per-process running-time cap was not enforced with a
  kill timer (plain `wait` was used), so par_2 (457.7 s) and par_3 (404.7 s)
  ran past 300 s and were not stopped by PID. All 4 finished on their own, so
  no process was killed; the overrun data is reported as-is.

## Cleanup

- `opencode session list -n 1000 --format json` run from the worktree root,
  from $D, and from a fresh plain temp dir: identical 9 sessions each time,
  all with directory under the worktree and none with a glm11- title or a
  directory under $D or under any temp dir this job's calls used. The helpers
  removed their own sessions (v1 by before/after diff, v11 by uuid title), so
  0 sessions matched this job's deletion criteria.
- Deleted 0 sessions based on the worktree-root listing; deleted 0 based on
  the fresh-temp-dir listing. Confirmed none of this job's 8 calls' sessions
  remain (no glm11-* titles created in the run window; only pre-existing and
  other-job sessions listed, which were left untouched).

## JSON lines (steps 4-5, verbatim)

{"helper": "v1", "id": "s320-321-00004", "ok": true, "seconds": 62.0, "reply_chars": 983, "reply_head": "{\"turns\": [{\"n\": 1, \"reply_before\": \"Hey! Ready when you are.\", \"user\": \"ok so heres a fun fact to start, my uncle is called Saim, thats it thats the intro lol\"}, {\"n\": 2, \"reply_before\": \"Nice, noted", "parses": true, "error": ""}
{"helper": "v11", "id": "s320-321-00004", "ok": true, "seconds": 92.0, "reply_chars": 888, "reply_head": "{\"turns\": [{\"n\": 1, \"reply_before\": \"Hi there! Happy to chat whenever you like.\", \"user\": \"hey quick one, my uncle is called saim, thought id share that with you\"}, {\"n\": 2, \"reply_before\": \"Got it, n", "parses": true, "error": ""}
{"helper": "v1", "id": "s320-321-00001", "ok": true, "seconds": 337.7, "reply_chars": 1494, "reply_head": "```json\n{\n  \"turns\": [\n    {\n      \"n\": 1,\n      \"reply_before\": \"\",\n      \"user\": \"hey so quick thing, i want you to know my nephew's name is migalek, thats my brothers kid, just so it's on file\"\n   ", "parses": true, "error": ""}
{"helper": "v11", "id": "s320-321-00001", "ok": true, "seconds": 125.5, "reply_chars": 1643, "reply_head": "```json\n{\n  \"turns\": [\n    {\n      \"n\": 1,\n      \"reply_before\": \"\",\n      \"user\": \"so my nephew is called migalek, thought you should know that\"\n    },\n    {\n      \"n\": 2,\n      \"reply_before\": \"note", "parses": true, "error": ""}
{"helper": "v11", "id": "s320-321-00004", "ok": true, "seconds": 156.9, "reply_chars": 1249, "reply_head": "```json\n{\n  \"turns\": [\n    {\n      \"n\": 1,\n      \"reply_before\": \"hey there! im all ears, go ahead\",\n      \"user\": \"alright so let me start, my uncle is called Saim. just covering the basics here\"\n   ", "parses": true, "error": ""}
{"helper": "v11", "id": "s320-321-00004", "ok": true, "seconds": 457.7, "reply_chars": 1266, "reply_head": "```json\n{\n  \"turns\": [\n    {\n      \"n\": 1,\n      \"reply_before\": \"Hey there, good to see you! What's on your mind?\",\n      \"user\": \"oh hey, so quick heads up, my uncle is called saim, figured id start", "parses": true, "error": ""}
{"helper": "v11", "id": "s320-321-00004", "ok": true, "seconds": 404.7, "reply_chars": 992, "reply_head": "{\"turns\": [{\"n\": 1, \"reply_before\": \"hey there, good to see you!\", \"user\": \"hey so did i ever tell you about my uncle, his name is saim\"}, {\"n\": 2, \"reply_before\": \"oh nice, thanks for telling", "parses": true, "error": ""}
{"helper": "v11", "id": "s320-321-00004", "ok": true, "seconds": 71.3, "reply_chars": 871, "reply_head": "{\"turns\": [{\"n\": 1, \"reply_before\": \"hey, ready whenever you are\", \"user\": \"btw my uncle's name is saim, thought you should know that going forward\"}, {\"n\": 2, \"reply_before\": \"got it, noted!\"", "parses": true, "error": ""}
