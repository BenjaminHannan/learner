# Active state — 2026-09-27

Latest selection: Ben said "ok, do scratchpad only". Use GPT-6 Sol subagents, local M3 Pro MPS, one GPU job at a time. SELECTED-DESIGN.md is authoritative; combined/bookmark notes are historical brainstorming. No solver/card labels, hand-written arithmetic addressing, kind labels, inference search, or loss changes. Only new scripts and artifacts/codex-numbers-20260927 may be edited.

Diagnostic prerequisite is SHOWN: seed9276193 width256/2 layers reaches919/962 practice exact at20k and933/962 at25k with0/100 own-dev. Immutable25k proof checkpoint/evidence is in diagnostics/fit-gate-step25000. Updated DIAGNOSIS was committed/pushed BEFORE implementation at2c83f71bac8e5488beea040371d608526d7cbb54. Original width128/20k underfit report remains preserved at prior commit fa4a356c99cc99e118ef0239cdb4dc89d0b1f468.

Completed diagnostic: final60k seed9276193 reached962/962 practice exact+valid,0/100 dev numbers,200/200 dev sums and grids,73.8864min. Final summary/checkpoint verified. No GPU job active at this update; subsequent MPS cardcheck and bounded cardbench also completed successfully. MPS cardcheck passed all groups; benchmark candidate/baseline time ratio1.23194. Full registered eight-run sweep is estimated11–13h, with measured full-run timings to supersede this rough estimate.

The implemented scratchpad uses Wq/Wk/Wv256→16, eight learned slot address vectors, per-token value payloads, a tied biasless decoder, and learned scalar read/write gates. Added12930weights; total1659424. Wipe K,V before EVERY read from round0. Card state advances in free rounds and detaches with h. No state persists across calls. Independent CPU checks pass; see IMPLEMENTATION-CHECKS.md. Implementation and CPU checks were committed/pushed at85aa8aae09dca9f9a742769484796be7387c17d7; registration changes are being finalized.

Next: finish and push immutable PASSMARKS.md/EXPERIMENT.json/SEAL-code.json BEFORE any registered run. The independent agent is finalizing registration with unchanged settings/marks and explicit torch2.11.0 runtime pin. No registered training or fresh five-number panel exists yet.

Registered plan remains four paired seeds9276101–9276104, sealed seed9276501, original1062 practice hands, same60k/b128/d256 settings. Executor must run sequentially, freeze all8 checkpoints, create fresh5 panel after registration, then parse all5 test panels once for the fixed entire sweep and score candidate intact/wiped. N5: mean intact-minus-wiped>=10 numbers4, >=5 fresh numbers5, positive>=3/4 seeds on each. Keep old5 report-only. Source/module hashes, core-init hashes, full training streams, parameter count and final checkpoint receipts are checked by supervisor/recount.

Original358i panel files have only been listed, not evaluated in this revised stage. Earlier task version authorized scoring a generated copy of the old300 four-number hands; this exposure is disclosed in REVISION-NOTE/RESULTS. No tuning may use those300 hands now. Own962/100 split is the only number development data. Fresh5 remains the cleanest test.

Latest usage check:56% remaining (44% used). Stop if below20%. The supervisor cannot access account usage through a supported script API; parent must use Codex usage tool while orchestrating.

Protected: never open artifacts/claude-brd11-20260926 or claude-rsn358k-20260927; do not touch/use claude-rsn358u-20260927. No root notebook, handoff/queue or held, watcher, BensPC, or codex-autoroute folder. Commit only our files, pull --rebase, push main; no PR/force push. Do not stash others' changes.
