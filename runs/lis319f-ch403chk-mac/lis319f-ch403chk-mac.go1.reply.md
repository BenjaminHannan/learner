Checking your DEV double-read — setting up isolated tree and verifying readers.
Your task file is confirmed and panels are clear — now staging the code tree and checking models.
Both model checksums match — now reading the 2 DEV turns with each reader.
Both readers finished — now compiling verbatim results.
Cleanup verified — final check that outputs are staged for pickup.
Verdict: DONE — 2 DEV turns read by both readers; ch-403 false-save lead confirmed (OLD saves the probe as fact, NEW does not).

Marks (integer counts):
- git fetch origin main: 1/1 OK
- common-rules lines read (lis-302-gpu.md 1–13): 13/13 (additive-only, fictional names, TEST-ONLY never read, report in reply)
- scratch trees created: 1 (`/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.LRXJ8Wx0aD`, 29 MB, 2 rows); removed by exact path: 1/1, confirmed gone (ls exits 1)
- model sha checks: 2/2 MATCH (OLD e688e1b2…776a76, NEW 970ef0ac…4aa6b4f9b); READER-FAILs: 0
- reader gate (lis319o-panel-mac / one job at a time): 1/1 clear, no reader process running at start
- OLD run: exit 0, 2/2 rows, device mps; NEW run: exit 0, 2/2 rows, device mps
- TEST-ONLY panels touched/quoted/tuned: 0
- PUSH files in worktree: 3/3 (`chk_ch403/RESULTS.md`, `reads_old.jsonl` 2 lines, `reads_new.jsonl` 2 lines); branches checked out/pushed by me: 0

Moves: archive→tree, shasum both models, OLD read, NEW read, copied both outputs (did not copy rows.jsonl — already on origin/main), wrote RESULTS.md with verbatim acts/facts/confs, rm -rf exact $D. Misses: 0. Deviations: 1 minor — dropped a redundant rows.jsonl copy to keep exactly the PUSH set (source of truth unchanged on origin/main).

What it means in plain English: on the "I'm 19" turn both readers agree (STATE me/age/19 ASSERT, conf ~0.9998 OLD vs ~0.9995 NEW). On the goodnight turn after the assistant asked "is Kim's occupation marine biology?", OLD wrongly saves Kim/occupation/marine-biology ASSERT (conf 0.9517) while NEW correctly saves nothing (CHAT, 0 facts). Total facts: OLD 2, NEW 1 across 2 rows. So the new reader fixes this one false save; it says nothing about anything else.
