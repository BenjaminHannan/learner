# Active state — 2026-09-27

Latest selection: Ben said "ok, do scratchpad only". Use GPT-6 Sol subagents, local M3 Pro MPS, one GPU job at a time. SELECTED-DESIGN.md is authoritative; combined/bookmark notes are historical brainstorming. No solver/card labels, hand-written arithmetic addressing, kind labels, inference search, or loss changes. Only new scripts and artifacts/codex-numbers-20260927 may be edited.

Diagnostic prerequisite is SHOWN: seed9276193 width256/2 layers reaches919/962 practice exact at20k and933/962 at25k with0/100 own-dev. Immutable25k proof checkpoint/evidence is in diagnostics/fit-gate-step25000. Updated DIAGNOSIS was committed/pushed BEFORE implementation at2c83f71bac8e5488beea040371d608526d7cbb54. Original width128/20k underfit report remains preserved at prior commit fa4a356c99cc99e118ef0239cdb4dc89d0b1f468.

Active GPU job: original fixed60k diagnostic continues, seed9276193, width256/layers2/heads8, batch128, lr3e-4, warmup1000, Latin pool20000, devholdout100, devseed9276601, devsum9276611/devgrid9276621. Probe every5000. Output diagnostics/fit-baseline-s9276193; stdout diagnostics/fit-baseline-s9276193.log. Frozen source snapshot diagnostics/fit-baseline-runner-snapshot.py. Tool exec session92723. Do not launch another GPU job until it finishes and process scan is clear. Do not stop processes belonging to anyone else.

The implemented scratchpad uses Wq/Wk/Wv256→16, eight learned slot address vectors, per-token value payloads, a tied biasless decoder, and learned scalar read/write gates. Added12930weights; total1659424. Wipe K,V before EVERY read from round0. Card state advances in free rounds and detaches with h. No state persists across calls. Independent CPU checks pass; see IMPLEMENTATION-CHECKS.md. New code changes are not yet committed at this state update.

Next: wait for diagnostic final summary/checkpoint, confirm final>=.95 practice exact (executor requires this in addition to interim permission to implement), clear GPU process scan, run cardcheck --device mps and bounded cardbench --device mps. Then finish and push immutable PASSMARKS.md/EXPERIMENT.json/SEAL-code.json BEFORE any registered run. PASSMARKS-DRAFT.md exists only as a draft. No registered run or fresh five-number panel exists.

Registered plan remains four paired seeds9276101–9276104, sealed seed9276501, original1062 practice hands, same60k/b128/d256 settings. Executor must run sequentially, freeze all8 checkpoints, create fresh5 panel after registration, then parse all5 test panels once for the fixed entire sweep and score candidate intact/wiped. N5: mean intact-minus-wiped>=10 numbers4, >=5 fresh numbers5, positive>=3/4 seeds on each. Keep old5 report-only. Source/module hashes, core-init hashes, full training streams, parameter count and final checkpoint receipts are checked by supervisor/recount.

Original358i panel files have only been listed, not evaluated in this revised stage. Earlier task version authorized scoring a generated copy of the old300 four-number hands; this exposure is disclosed in REVISION-NOTE/RESULTS. No tuning may use those300 hands now. Own962/100 split is the only number development data. Fresh5 remains the cleanest test.

Latest usage check:64% remaining (36% used). Stop if below20%. The supervisor cannot access account usage through a supported script API; parent must use Codex usage tool while orchestrating.

Protected: never open artifacts/claude-brd11-20260926 or claude-rsn358k-20260927; do not touch/use claude-rsn358u-20260927. No root notebook, handoff/queue or held, watcher, BensPC, or codex-autoroute folder. Commit only our files, pull --rebase, push main; no PR/force push. Do not stash others' changes.
