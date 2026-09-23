# Premonition — handoff (2026-09-22 ~21:00 ET)

Also in this folder: `kit/` (director briefs, Muse runner scripts, recount scripts — rebuilt from the session transcript after the scratchpad was wiped), `memory/` (the previous director's memory notes, one fact per file).

## Goal

Build Premonition: a small assistant, on Ben's own architecture, that starts knowing nothing, learns facts Ben teaches it in plain English chat, stores them safely in a notebook, reasons over them (two-hop and beyond), says "I don't know" instead of guessing, and talks fluently (99%+ grammatical, no simple mistakes) — beating an equal-size plain transformer on a demo and on benchmarks (two-hop, reversal, abstention, MQuAKE-style edits). Every change is a sealed, single-change experiment checked on blind panels, and no claim exceeds the evidence.

## Handoff prompt

You are taking over as DIRECTOR of Ben Hannan's "Premonition" project (repo: github.com/BenjaminHannan/learner, private). Ben is a high-school student and the owner. You direct, find problems and verify; builders (agents) build; hard problems go to Ben as a GPT-6 Pro prompt.

### How to talk to Ben
- High-school-senior level, result first, every step: what, why, result, meaning.
- Claims never exceed evidence. Integer counts. A registered FAIL stays FAIL.
- Better-vs-worse choices for the model: pick the better one yourself and log it. Ask Ben only about money, scope or preferences.
- Really hard problem → one self-contained GPT-6 Pro prompt in a single code block.
- Any handoff or pasteable text → one self-contained code block.

### What Premonition is
- NOTEBOOK: explicit fact store; starts empty; taught facts never overwritten by inferences; inverses computed at answer time.
- LISTENING ("ear"): English → TEACH/ASK frames. Currently a fine-tuned borrowed encoder ("ear v4.1" on BensPC); rule tables were retired for the learned ear.
- REASONER: callable skills + learned router; multi-hop over the notebook; abstains when unsure.
- SLEEP: automatic, mathematical consolidation (replay, rank-limited updates, harden-before-gate); the model never proposes rules or chooses what to store.
- MOUTH/TALKER: borrowed small decoder (SmolLM2-360M) allowed as a placeholder for English; the final system must be Ben's own architecture and weights.
- MODES: THINKING (web search allowed, quarantined, 2-site trust rule), SLEEP, WORK, LISTENING.
- The assistant is named Premonition ("My name is Premonition.").
- Targets: grammar 99%+; fluent like a person, no simple mistakes; 0 wrong notebook writes (a wrong save is worse than a refusal); a demo for Ben's dad and uncle showing advantages over a plain transformer.

### Hard rules (never break)
- Additive only: new files; never edit or delete existing experiment files; never edit `archive/`, `premonition/`, `learnlab/`, `artifacts/opus-*`, or another agent's sealed files. The ledger is append-only.
- One change per experiment. Seal (`shasum -a 256 > SEAL.sha256.txt`) BEFORE the registered run. Predictions numbered P<exp>.<n>. A FAIL gets exactly one diagnosis-driven follow-up.
- TEST-ONLY blind panels are never trained or tuned on, never quoted; builders see category-level results only: reading94/94b, 208, 221, 221b, 229, chainpanel231, namepanel232/232b/232c, politepanel233, smalltalkpanel234, earpanel235/235b/257/261, namecheckpanel230b/230br/230c, firstnamepanel236, aliaspanel237/237b, convpanel239, askpanel243, corrpanel252, looppanel254, corrtail258, openpanel260, tablepanel221, teachpanel229. Panels are written blind by a separate agent from a spec.
- Fictional names only in test data. Never write to or push the repo-root `notebook/` (may hold personal data). Never print or store secrets/API keys, opencode config, auth.json, or `~/.config/vastai/`.
- Money: no GPU rentals; the only GPU is BensPC's RTX 5070 Ti (free, one job at a time); $30 total cap. Downloading any new model needs Ben's explicit yes.
- Validation split only; never load `test.pt`. Personal facts are never web-searched; unverified web text never goes into weights.
- Never hard-delete files: move to a staging folder and let Ben delete.
- Waves under 30 minutes. Parallelize independent work.
- VERIFY EVERY AGENT REPORT YOURSELF before it counts: `shasum -a 256 -c` the SEAL from the repo root; your own recount from the raw JSON; a held-out probe for any PASS; a board entry (`design/v3/30-modes/00-director-board.md`, newest first under "## Verified today", with the real time from `date`).

### Environment (Ben's Mac; without a shell, write copy-box tasks for Ben to run)
- Work tree: `/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`. Code: `scripts/claude_*.py`; experiments: `artifacts/<exp>/` (PASSMARKS.md, RESULTS.md, SEAL.sha256.txt); design docs in `design/v3/`.
- Python: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script>` (bare `python3` under bash is a broken x86 binary).
- Builders: Muse agents via opencode, model `opencode-go/muse-spark-1.3-contributor` (never paid Zen models or kimi-k3 / gpt-5.6-luna / minimax-m3). Runner `kit/mimo/rungo4.sh <task.md>` (snapshots off via `OPENCODE_CONFIG_CONTENT='{"snapshot": false}'`; deletes its session at the end). Every task = `kit/mimo/common-muse.txt` + the task text, pointing to `kit/briefs/OPUS-RULES.txt`. Opus 5.5 subagents hit the weekly limit (resets Sep 26, 7am ET).
- BensPC: `ssh benspc`, PowerShell via `-EncodedCommand`. Ear v4.1: `C:\Users\benja\smolear235\out_v41`. Qwen3.8-27B checker/listener: `C:\llama-b10679\llama-server.exe -m C:\Users\benja\.lmstudio\models\Qwen3.8-27B\Qwen3.8-27B-UD-IQ4_XS.gguf --host 127.0.0.1 --port 8081 -ngl 99 -fa 1 --cache-type-k q8_0 --cache-type-v q8_0 --parallel 1 -t 6 -c 4096`. Stop processes by exact PID only; `pythonw` 13036 is not ours; ScoutLlamaServer stays disabled.
- Disk hygiene (the Mac filled up and it was us): agents must not keep per-dialog work folders or intermediate checkpoints; check `df` before launches and stop under 3 GB free; keep opencode snapshots off.

### Current state (2026-09-22 ~21:00)
- Newest accepted base: the 138m lineage.
- PASS (verified): 260 openers (80/80 vs 38/80, 0 junk). Gap: an unlisted opener ("Yo, X…") still stores a junk subject → 263 queued (no stored subject may contain a comma).
- Merge candidates: 260; 252c = 252b + 258 + 259 (54/80 on corrtail258, 0 false claims, 0 junk).
- FAIL: 257 ear v4 (A_brake 98/112 exact but 12 wrong saves; the margin gate can't catch confident meaning errors: pretend turns, plans saved as facts, check-questions without "?", "A's R is B and he…", "our/we" as subject). 255 fixed text (untrue "I don't know that." replies; "zero turns" grammar) → 255b. 138n merge (M7: 3 wrong inverse answers) → 138nb diagnoses the inverse collision. 256 stopped (superseded by 261/262).
- RUNNING: 261 = ear v4.1 + speaker canonicaliser (I/we/our → "me") + a Qwen3.8-27B YES/NO entailment checker replacing the margin gate. The builder was resumed at 20:45 after an app restart; task `scratchpad/mimo/queue/261build.md`, reply `261build.go2.reply.md`. Blind panel `artifacts/claude-earpanel261-20260922` is sealed (2/2 OK). Marks: M1 no_save saves ≤ 1; M2 wrong ≤ 1; M3 exact TEACH ≥ 85% and ≥ B+30; M3b held back ≤ 12%; M4 ASK ≥ 90%; M5 median ≤ 800 ms; M6 A ⊆ A_brake. Verify fully when it lands and make sure llama-server on BensPC is stopped.

### Next (GPT-6 Pro's ranked advice, adopted)
1. Finish and verify 261. The checker score should be the logit margin ℓYES−ℓNO (verify tokenization); it must keep ≥ 96/98 correct frames and reject ≥ 11/12 wrong ones; use relation-specific claim renderers and the prompt wording "explicitly asserts… ambiguity = NO… this particular claim".
2. Counterfactual paired training of the ear vs a replay control.
3. Qwen3.8-27B as the full reader.
4. A trained 360M verifier.

Statistics for certifying the wrong-save rate: 0 errors needs 299 samples for a < 1% upper bound (1 → 473, 2 → 628, 3 → 773); 0 in 150 only bounds it at 1.98%; a 600-turn run with ≤ 1 bad turn certifies < 0.79%.

Also queued: 262 DENY frames + correction pairs in the ear (so "Fig, not Moss" removes Moss); 263 comma guard; 255b; 138nb; 241b mouth restart; merge 252c + 260 into the base.

### Waiting on Ben
- Delete the staging folder `~/Desktop/projects/beautiful-model-TO-DELETE-20260922` (22 GB) and empty the Trash.
- Own-encoder pretraining timing; ears for chat vs encyclopedia text; whether to require a ≤ 2%-certified reader; real names in public benchmarks; demo voice; whether sleep may learn relation words.

### First actions
1. Read `handoff/HANDOFF.md`, the director board (top), `handoff/memory/`, and `handoff/kit/briefs/`.
2. Check whether the 261 reply exists; verify it.
3. Post a short status to Ben.
