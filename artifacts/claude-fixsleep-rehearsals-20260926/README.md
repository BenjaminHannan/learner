# Fix-sleep CPU rehearsals, night of 2026-09-26 (plumbing only; no registered results)
These are the throwaway CPU checks run before each registered run was sealed. Kept at Ben's request, 12:37 UTC.
No weights are included.

| File | What it checked |
|---|---|
| qtest.py | Asking prompts for dl-3's base-written questions, and how often answers finish within the token cap. It led to the two alternating prompts, the 48-token question cap, and training cut answers without an end token. |
| trtest.py | dl-3's pool builder and mixed puzzle + replay training on the real 1B: 3 puzzle + 3 replay items; the end token only on finished answers. |
| anctest.py | dl-4's KL anchor. KL to the base is exactly 0 on a fresh adapter, and small but positive after training. |
| dl3-dev/ | dl-3's --dev rehearsal output: first-prompt pool of 6 assistant-style questions, which is why the prompts were changed. |

The registered results are in artifacts/claude-dl2-20260926, claude-dl3-20260926, claude-dl4-20260926 and
claude-nightproc-20260926.
