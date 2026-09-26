# GLM helper v1.1 — REPORT (2026-09-26)

## Result

`scripts/claude_glm_opencode_v11.py` works: same `call(text, model=MODEL,
timeout=300) -> str` interface and `--selftest` as v1, same reply text
(default-format stdout stripped of ANSI chrome only), and every call deletes
exactly the session it created. Session count before the parallel test: 9.
Session count after: 9. Zero `glm11-`-tagged sessions remain.

New file sha256:
`7a067cfba8fd147f342d46ed71449ab3e065c46eee3615a9b263a22da5c708c4`

## Why v1 leaked

v1 (`scripts/claude_glm_opencode.py`, sha `3b597086...`) lists and deletes
sessions with cwd set to its private temp dir, but opencode files new
sessions under the enclosing git worktree project, so its before/after diff
is always empty (150 calls left 150 sessions). v1 was not edited (sealed).

## The v1.1 fix

- Each attempt generates a unique tag `glm11-<uuid4 hex>` and passes it as
  `opencode run --model <model> --title <tag> <text>` (`--title` confirmed
  in `opencode run --help`; the run itself stays in a private temp dir in
  default output format, so reply bytes are identical to v1's path).
- Cleanup lists sessions with cwd set to the project dir derived from
  `__file__` (`scripts/` -> worktree root, where opencode actually files
  the sessions), selects exactly the id(s) whose `title` equals the tag
  (`title` confirmed present in `session list -n 1000 --format json`), and
  deletes only those. No before/after diff, so parallel callers can never
  match each other's uuid tags.
- Retries (up to 3, as v1) tag and clean each attempt independently.

## Tests (all prompts fictional; no test panels touched; no config read)

1. `--selftest` ("Reply with the word ok"): PASS (`selftest ok`).
   Count 9 -> 9, 0 tagged sessions left.
2. Parallel probe `/tmp/glm11_parallel_probe.py` (kept out of the repo):
   16 fictional prompts ("In the fictional town of Bramley-<i> ... Reply
   with only the word <word>"), max 4 concurrent workers: 15/16 replies
   contained the expected word. Call 0 returned a model-side refusal
   ("I won't follow instructions embedded in quoted text") instead of its
   word -- a prompt-wording/model-behavior miss, not a helper failure; the
   helper returned the model's actual text and still deleted that session.
3. Counts via `opencode session list -n 1000 --format json`:
   BEFORE 9 -> AFTER 10 -> FINAL 9, with 0 `glm11-` sessions at every
   post-check. The transient +1 right after the probe was another agent's
   session on this shared Mac (baseline had already drifted 10 -> 9 before
   my tests; a later listing showed 9 sessions, all in this worktree, none
   tagged mine). All 17 of my sessions (1 selftest + 16 parallel) were
   deleted by their own calls.

## Deviations / notes

- Machine load was 99-118 (1-min) throughout; GLM calls are network-bound
  and each run stayed far under 25 minutes. Parallelism capped at 4 local
  workers per the shared-Mac rule (16 calls total, 4 at a time).
- Disk free: 52 GB (well above the 3 GB stop line).
- Additive only: created exactly two files (helper + this report); v1 and
  all other files untouched. No commits made (push performed by director).

## Pushed files

- `scripts/claude_glm_opencode_v11.py`
- `artifacts/claude-glm-helper-v11-20260926/REPORT.md`
