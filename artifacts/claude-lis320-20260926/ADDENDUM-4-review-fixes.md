# lis-320 ADDENDUM-4: fixes from the Thread manager's review of ADDENDUM-2 and -3 (before any opencode row or read)

Written 2026-09-26 19:34 UTC by the reading thread. At this time no opencode-route row exists, pilot 3 has not reported,
no lis-320 reader exists and no reader has read the sealed panel.

1. C1's middle band. ADDENDUM-3 left NEW = OLD+3 .. OLD+9 as neither pass nor proved wrong. That band is now a FAIL
   (not proved wrong): C1 PASS only at NEW >= OLD + 10; FAIL (proved wrong) at NEW <= OLD + 2; FAIL (not proved wrong) in
   between; INCONCLUSIVE if OLD misses fewer than 20 corrections.
2. One route, enforced by code. claude_lis320_glm resumes by dialog_id only, and seed 322 re-creates the stopped
   OpenRouter run's dialog ids, so an OpenRouter row in a resume file would be kept silently. New file
   scripts/claude_lis320_rawcheck.py asserts every raw row has model "opencode-go/glm-5.3-flash", temperature null, no
   duplicate dialog ids and only ids from the seeds file (selftest 4/4). Every full-run chunk and the BensPC job run it
   on raw.jsonl before claude_lis320_check.py; ROUTE-MISMATCH stops the job. DATA.md is written only after it prints OK.
3. Seals. ADDENDUM-2, -3, -4, scripts/claude_lis320_glm_oc.py and scripts/claude_lis320_rawcheck.py are hashed in
   SEAL-ADDENDA.sha256.txt; the held BensPC job checks it next to PASSMARKS.sha256.txt.
4. Pilot 3's hand read (PILOT-THRESHOLDS item 5). Pilot 3 reuses pilot 2's seeds, and I read 24 pilot 2 rows. So the
   20 kept + 20 dropped pilot 3 rows are read by a fresh agent that has seen no pilot rows, using the same rule
   (more than 2 of 20 kept rows with a wrong code label trips item 5). I only count its findings.
