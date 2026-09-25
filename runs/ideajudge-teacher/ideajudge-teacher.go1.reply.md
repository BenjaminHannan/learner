Verdict task locked — running your teacher agreement check now.
Files confirmed — staging them for the run.
Staged 10 requests for labeling — starting the teacher run.
The run hit API errors — digging into the exact cause.
Confirmed the blocker and verified no key exposure — finalizing the report.
FAIL — ideajudge-teacher DEV agreement check blocked, 0 teacher labels written.

counts: dev_items 70, blurt_rows 40, labels0 150, labels1 150, teacher_success 0, unparsed_observed 18, failed_tries_observed 150, output_files 0

exact error (script unedited, run from origin/main via `git archive` in temp dir with `uv run --offline --no-project --python 3.12 python -B`):
- every call prints `[teacher] try N failed: HTTPError HTTP Error 400: Bad Request` then `[teacher] dcre-XX unparsed`
- direct probe of same model/payload returns HTTP 400 body: `{"error":{"message":"Reasoning is mandatory for this endpoint and cannot be disabled.","code":400,...}}`
- cause: `scripts/claude_ideajudge_teacher.py` sends `"reasoning": {"enabled": False}` which `z-ai/glm-5.3-flash` on OpenRouter rejects. Per rules I did not edit the script and stopped.
- last printed line before 20-min timeout kill: `[teacher] try 2 failed: HTTPError HTTP Error 400: Bad Request`
- key in `~/.config/openrouter/key` only, never printed/logged/copied; console log contains 0 key strings.
- worktree untouched for this task: `artifacts/claude-blurt2-20260925/teacher/` not created, nothing pushed.
