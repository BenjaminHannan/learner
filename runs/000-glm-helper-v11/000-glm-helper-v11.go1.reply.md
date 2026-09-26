Fixing the session leak — building a helper that cleans up exactly its own session.
v1 sha confirmed (`3b597086`). Creating the v1.1 helper now.
Baseline is 9 sessions (another agent cleaned one up since my earlier probe — noting it). Running selftest:
Final count is back to 9 = before. Writing the report:
Done. Report for the director:

**GLM helper v1.1 — PASS**

- **Created (additive only, v1 untouched):** `scripts/claude_glm_opencode_v11.py`, sha256 `7a067cfb…5c708c4`. v1 sha prefix confirmed `3b597086`. Required docstring line present. Both files staged (`A`), no commit/push per standing rules. Note: `artifacts/` is gitignored (`.gitignore:5`), so the REPORT needed `git add -f`.
- **Fix:** each attempt passes `--title glm11-<uuid4hex>` to `opencode run` (both `--title` and JSON session fields confirmed via `--help` and a live probe: list entries carry `title`). The run itself stays in a temp dir in default format, so reply bytes are identical to v1's path (strip ANSI chrome only). Cleanup lists sessions with cwd = worktree root derived from `__file__` (where opencode actually files them), matches exact title, deletes only those ids — never a before/after diff.
- **Tests:**
  - `--selftest`: PASS (`selftest ok`); sessions 9 → 9, 0 tagged left.
  - 16 fictional prompts in parallel (max 4 local workers): **15/16** replies contained the expected word. The one miss (call 0) was model-side behavior — it returned a "prompt-injection" refusal to the worded prompt instead of its word. Helper failure in no case: it returned the model's actual text and deleted that session too.
  - Counts (`session list -n 1000`): BEFORE 9 → AFTER 10 → FINAL 9, with **0 `glm11-` sessions** at every post-check. The transient +1 was another agent's session on this shared Mac (baseline had already drifted 10→9 pre-test; a later listing showed 9 sessions, all in this worktree, none mine). All 17 of my sessions (1 selftest + 16 parallel) were deleted by their own calls.
- **Deviations:** load 99–118 throughout (calls are network-bound; each step far under 25 min); parallelism capped at 4 workers per shared-Mac rule; disk 52 GB free; no test panels touched; no config/auth files read.
- Full details in `artifacts/claude-glm-helper-v11-20260926/REPORT.md`.
