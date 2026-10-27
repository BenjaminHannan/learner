# Handoff: the card-experiment track (from Claude's experiment session, 19 Sept 2026, ~6:30 pm EDT)

You are taking over my responsibilities on **Premonition** in `/Users/ben-hannan/Desktop/projects/beautiful-model`. Read this
whole file, then `CLAUDE.md`, then the memory index at
`~/.claude/projects/-Users-ben-hannan-Desktop-projects-beautiful-model/memory/MEMORY.md` (shared across sessions in this folder).
Check every factual claim below against the files before acting on it; I made mistakes today that reviewers caught.

## Who you work for and how
Ben is a high-school senior building his own small, genuinely-learning model (reasoning first, language second). He reads on
his phone and replies fast.
- Explain every action at high-school-senior level: what, why, result, meaning. Lead with the result. Short.
- Claims no stronger than the evidence. Label **shown / suggested / untested**. Keep the **small card experiments** and the
  **village model** strictly separate.
- A short prioritised sequence, never a catalogue. **One change at a time**, pass marks and the falsifying result fixed BEFORE
  looking, every seed reported, fraction of seeds succeeding stated. 5 seeds = a screen; 40 vs 40 detects only large effects.
- Milestone Ben set: **dependable two-hop reasoning in fresh worlds** (right across seeds, changes when a relevant fact
  changes, resists irrelevant changes). Astra's bar for "dependable": a frozen recipe passes the full fresh-world suite in
  **>= 77 of 80** fresh training runs.
- Ben prefers Opus sub-agents (medium effort) for engineering; I only synthesised and decided. Agents cannot write `.md`
  files here; write reports yourself from their output. Multi-agent workflows only for research, and only when asked.
- Outside opinions: write prompts under `reviews/`, Ben relays them (Astra = lead, on Codex with repo access, research-only
  prompts; GPT web = self-contained prompts). See `CLAUDE.md`.
- New rule in memory (from another session today): every experiment wave under 30 minutes wall-clock unless that costs > $2.

## Hard rules
- **Additive only.** Never edit `archive/`, `premonition/`, `learnlab/`, `artifacts/opus-*`, Astra's or Opus's files, ledgers.
  The model code is a hash-checked frozen snapshot (`archive/opus-ovn-20260918-235851/frozen`) loaded by `L.bootstrap()`. New
  work = new files in `scripts/`, `tests/`, `artifacts/claude-*`, `reviews/`. Files I own and you may edit:
  `scripts/premonition_{gpu_port,first_card_probe,pool_mass_probe,stuck_probe,person_probe,key_pool,wave_table,handoff_diag,pair_suite,relation_shortcut,ordered_evidence,ladder6,seed_screen_report}.py` and their tests.
- **Validation split only; never load `test.pt`.**
- **BensPC** (`ssh benspc`, RTX 5070 Ti, Windows): free to use; do not kill other people's processes or install anything.
- **Money.** vast.ai key is at `~/.config/vastai/vast_api_key`: never print, cat, copy or write it; use only
  `-H "Authorization: Bearer $(cat ~/.config/vastai/vast_api_key)"`. Any rental needs Ben's explicit yes with GPU type and
  price. About **$3 was spent today** (his cap for today was $3.25; lifetime cloud cap $30). All instances are destroyed; the
  account shows none. Rental recipe and lessons (on-demand only, CUDA MPS doubles speed, many cores + several GPUs) are in
  memory file `compute-availability.md`.
- **Another Claude session is active in this repo** (it made `scripts/premonition_softread.py`,
  `scripts/premonition_pointer_ablation.py`, `artifacts/claude-{softread,pointer-ablation,goldzero,interface-probes}-20260919`,
  a "mini-village" plan). Those are not mine; I know nothing about their state. Do not touch them without asking Ben, and
  watch for CPU contention on the Mac.

## How to run things
Mac (M1 Pro; probes and eval only):
```
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
export PYTHONPATH=$(python3 -c "import json;print(':'.join(json.load(open('runtime.local.json'))['import_roots']))")
$PY -B scripts/<name>.py        # tests: $PY -B tests/<name>.py
```
Training (GPU; compare GPU with GPU only, fp32): `scripts/premonition_gpu_port.py --device cuda --autocast off --arm bypass-k1
--steps 12000 --gold-until 0.10 --teacher-until 0.1833 --ramp-until 0.2667 --seed S --name N --out DIR` plus one of
`--relation-shortcut`, `--key-pool`, `--width W`, `--no-step-emb`, `--ordered-evidence`, `--lr-cooldown F`, `--ladder6`.
BensPC python: `C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe`, repo `C:/Users/benja/beautiful-model`
(scp changed scripts there first). Runs print nothing until they finish; results = `runs/*.json` + `ckpt/*.pt`.
Scoring: `python3 scripts/premonition_wave_table.py <runs_dir>...` (old marks) and
`$PY -B scripts/premonition_pair_suite.py score --ckpt-dir ... --workers 5` then `... table --group NAME=DIR --runs NAME=DIR
--compare A B` (strict fresh-world suite; **never re-run `gen`**, it would invalidate all scored rows).

## The model and task in two sentences
~80k-parameter "D" design: recurrent reader -> every fact line becomes a card (key + value from a pooled line summary) ->
a Think loop writes a search slip from register 0, the store returns the best card (hard top-1, not differentiable for the
answer loss), up to 3 fetches, then a decoder answers. Task: one-step ("Mira shoes?") and two-step ("Mira friend shoes?")
questions in freshly generated stories; **held-out** = a relation seen one-step but never in two-step training.

## Where the evidence stands (all card track; read the reports, do not trust this summary blindly)
1. Reading/combining given the right cards is ~100%; the failures are in building requests.
   `artifacts/claude-firstcard-20260919/`, screens 1-6b in `artifacts/claude-{seeds,ordered,cooldown,ladder6,long,relcut,relcut-long}-20260919/REPORT.md`.
2. **Stuck runs** (never learn whose card to fetch): right KIND of card 100%, right PERSON at chance; identity is readable at the
   card's name token but not in keys/queries. `artifacts/claude-relcut-long-20260919/STUCK_PROBE.md` (includes corrections
   after Astra's audit) and `CONTROLS_15.md` (BensPC, 15 seeds: plain 4/15 stuck, wire 7/15 stuck; wire passes held-out in
   8/8 learned runs; all-three 1/15 vs 7/15).
3. **Relation shortcut wire** (545 params; copies the question's relation token, found at a known position, into the search
   slip): fixes the held-out relation error in runs that learn. It is a crutch (position parsing) to be replaced later.
4. **Separate key pooling ("search-label fix")**, 40 seeds per arm, both recipes, plus a width test:
   `artifacts/claude-keypool-20260919/REPORT.md`. Stuck: wire 16/40 -> 6/40 (pre-registered Fisher p = 0.023, passes); plain
   7/40 -> 1/40 (p = 0.057, does not pass). **But full-suite passes do not rise** (wire 21/40 -> 23/40; plain 0 -> 3): rescued
   runs sit near 70% on held-out because their FIRST request on a held-out question is not the friend link (the wire writes the
   relation into request 1 too); ~29% of the time they then stop asking early. Wider models stick more (width 64: 7/20, width
   128: 15/20, same lr/init; retuned lr untested).
5. **Strict fresh-world suite** (gate G, six cells incl. three "change one fact" pair tests, Astra's exact cut-offs):
   `scripts/premonition_pair_suite.py`, `artifacts/claude-pairsuite-20260919/{rows.jsonl,table.txt,manifest.json}`.
6. **Lead's handoff diagnostic D0-D1**: `artifacts/claude-handoff-20260919/REPORT.md`. Verdict by its own rules:
   inconclusive on the wire panel (one seed carries the effect), no useful effect on the plain panel. D2 stays sealed.
7. Reviews and prompts: `reviews/astra-deep-dive-2026-09-19/report.md` (Astra's audit + decision tree E1-E6 + reliability
   maths; treat as the plan of record), `reviews/premonition-discovery-2026-09-19/`, `reviews/newidea-*`,
   `reviews/astra-*-prompt-*.md`, `reviews/gpt-diagnose-second-request-2026-09-19.md`. Two independent "new idea" searches
   found nothing new that survives; the useful known idea is residual-question closure (H2).

## Mistakes I made today (do not repeat)
- Read "ASK loss 2.07" as ln 8; it is BCE + set CE averaged over loops. Said the gold phase ends at step 1,225; it ends near
  1,850 (phases follow FLOP share). Said "97-99% of pooling on the value token" for all stuck runs; true of one.
- Declared the wire's first-request side effect "undertraining, gone at 12k" from 3 seeds; 40 seeds showed it in ~1/5 of
  learned runs. Small panels mislead.
- `premonition_wave_table.py` counted "all three" with one-step instead of READS (fixed; 7/15 not 8/15).
- Used an interruptible rental; it was paused mid-wave and the wave was lost. `pkill -f` over ssh killed my own shell.

## Open decision and next steps (in order; one at a time, pre-register, 40 vs 40, score with BOTH the old marks and the suite)
0. **Pending with Ben:** I proposed, and he has not yet answered, experiment **"wire off on request 1"**: control = wire + key
   pool; change = the relation shortcut contributes nothing before the first fetch (hold its gate at zero on loop 0 for
   two-step questions, or feed the gate the loop index; zero-cost, needs parity tests like `tests/test_premonition_relation_shortcut.py`).
   Pass: more seeds pass suite G (Fisher p < 0.05) with no rise in stuck runs; falsifier: the 70% mode persists at the same
   rate. One-step questions still need the wire on request 1, so gate by question type or learn it. Cost ~$0.90 per 40-vs-40
   wave on a 4-GPU on-demand rental (needs Ben's yes), or free but slow on BensPC (~90 min per 10 runs).
1. Remaining stuck runs (6/40, 1/40): Astra's **E1**, empty-workspace one-step search supervision during the gold phase, with a
   zero-weight control that still computes the extra pass.
2. **H2 / residual-question closure** as the general replacement for the position-reading wire (Astra's E3 spec, with an
   extra-evidence-CE control).
3. Re-run the handoff diagnostic only if the new parent recipe leaves eligible second-request errors.
4. Freeze a recipe, then **certify: 77 of 80 fresh training + data seeds pass G**.
5. Then, per Ben's original priorities: bounded fair trial of the Think loop (accuracy per extra compute), the early retention
   experiment (A then B, explicit storage/replay budgets, say whether knowledge lives in weights or cards), replace the wire's
   fixed position with learned selection (E6), and only then anything village-scale. My honest estimate to a working
   village-scale model was 2-6 weeks, gated on the bridge from fixed-template cards to real text.

## State at handoff
No background jobs of mine are running. No rentals exist. BensPC GPU is idle. Nothing is committed to git (the repo has one
initial commit; everything today is untracked); ask Ben before committing. My todo list is empty except item 0 above.
