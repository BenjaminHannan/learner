Verifying the practice run — clean export, base model check, and both dev arms.
Selftest passed. Now checking the base model and running both arms.
The default cache doesn't have the model. Searching for the venv the earlier tasks used.
Still hunting the right Python environment. Checking the earlier run transcripts.
Base isn't in the default cache. Checking alternate locations before declaring NO-BASE.
One last sweep for any local copy of the weights.
VERDICT: NO-BASE. Stopped at step 2 as ordered — openbmb/MiniCPM5-1B is not on this Mac, so neither arm was run and nothing was downloaded.

MARKS TABLE (integer counts, nothing estimated):

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| Step 1: clean export + tool selftest prints "selftest ok" | 1/1 | 1/1 | PASS |
| Step 2: BASE snapshot resolves locally | 1 | 0 | NO-BASE → STOP |
| Step 3: arm P on 16 dev items | 16 | 0 run | NOT RUN |
| Step 3: arm T on 16 dev items | 16 | 0 run | NOT RUN |
| Step 3: score JSON | 1 | 0 | NOT RUN |
| Step 4: score JSON, snapshot hash, per-arm median s/item, steps for d01/d04/d07/d10/d13/d15 both arms | all | none | NOTHING TO REPORT |

EVERY MOVE:
1. Ran `git fetch -q origin main` (quiet, no output) and confirmed the plan files exist on origin/main (`scripts/claude_rsn299_tool.py`, `scripts/claude_rsn299_run.py`, `artifacts/claude-rsn299-20260924/dev.jsonl` with 16 lines).
2. Exported a clean tree with `git archive origin/main | tar -x -C /tmp/rsn299dev` and ran from there: `scripts/claude_rsn299_tool.py` printed exactly `selftest ok` (1/1).
3. Checked `uptime` (load ~120, high but not a stop condition) and `df -g /` (58 GB free, over the 3 GB floor), so disk/load did not block anything.
4. BASE check, exactly as specified: `snapshot_download('openbmb/MiniCPM5-1B', local_files_only=True)` in a uv venv with transformers (`uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with huggingface_hub`). Result: `LocalEntryNotFoundError` — no cached snapshot on local disk. The default HF cache holds only `models--sentence-transformers--all-MiniLM-L6-v2` (1 entry).
5. Swept likely alternates before stopping: `~/premonition-models/` (lis300-merged, lis301-merged, minilm, own-m1 mouths, rsn294/296/296b only), `~/premonition-weights/` (smolear235_v41 only), `~/premonition-chat/`, `~/.lmstudio/hub/models/` (empty), `/private/tmp/`, `/tmp/`, `/root/model-minicpm5-1b` (absent). The only MiniCPM hit on disk is the helper script `/private/tmp/own-m1b-bundle/extra/claude_dl_minicpm5.py`, which downloads to `/root/...` (a non-Mac path) — code, not weights. 0 weight files found in every location checked.
6. Per "do not download", stopped. No arm ran, no score file exists, no worktree files were created or edited, so there is no PUSH payload (`artifacts/claude-rsn299-20260924/dev-mac` was never created).

EVERY MISS / DEVIATION:
- Miss: the OPUS-RULES.txt path in the task does not exist on this machine (`scratchpad/briefs/` is absent; `scratchpad/` holds other items). I followed the key-points summary quoted in the task itself instead (additive-only, no downloads, offline uv python, report-everything). 1 missing file, 0 rules broken on my side.
- Deviation: none from the task sequence. I added `--with transformers --with huggingface_hub` to the uv venv for the BASE check only, since the BASE check itself requires them (same precedent as the lis-313 builder note); the mandated `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` and `--offline` were kept. No code edited, no branch checked out/merged/pushed.
- No TEST-ONLY panel exists for this task (dev items are explicitly "not blind"); nothing sealed was opened. The 60-minute cap never came into play (0 seconds of model runtime).

WHAT IT MEANS / DOESN'T MEAN (plain English): Think of it like being asked to test-drive two versions of a recipe but the main ingredient was never delivered to this kitchen — I verified the kitchen tools work (selftest 1/1) but cooked 0 of 16 dishes in each version because the rulebook says to stop, not to go shopping. This says nothing good or bad about the P-vs-T prompt format or the tool; that question is still fully open. It also doesn't mean the model is gone everywhere — only that this Mac has no local copy. Next step for the director: either point this task at a machine/path that holds the weights, or authorize a download.
