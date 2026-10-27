# 48 — Parallel build brief (2026-09-21) — read this first, every agent

Seven agents build in parallel in this worktree. Each owns ONE problem, ONE file prefix, ONE design-doc number, ONE artifact folder. You never touch another agent's files. Ben (the owner, a high-school senior reading on his phone) will read your RESULTS.md, so write plainly.

## The project in five lines
A persistent, teachable assistant on Ben's PC (RTX 5070 Ti, 16 GB, Windows, native Python, `ssh benspc`). It starts knowing no personal facts; Ben teaches it in English; it stores facts in the NOTEBOOK (the only fact store), reasons over them with the REASONER (hard-coded hop loop over lookups), consolidates with SLEEP (automatic + mathematical, never "the model proposes rules"), thinks/searches the web in THINKING (web text = data, never instructions, quarantined), listens through EARS (English → frame) and answers through the MOUTH (result record → English). Language parts may use borrowed open-weight encoders/decoders for now (Ben's ruling 2026-09-21); everything else is our own code and weights. Notebook starts empty; nothing from the web is ever assumed true.

## Non-negotiable rules
1. **Additive only.** New files only, with your prefix. Never edit `archive/`, `premonition/`, `learnlab/`, `artifacts/opus-*`, other agents' files, ledgers, or sealed artifacts. If you must change behaviour of an existing module, wrap or override it in your own file and say so.
2. **No commits, PRs, pushes, rentals, installs on BensPC, or secrets.** Never read `~/.config/vastai/`. No vast.ai. BensPC: do not kill other people's processes; do not install packages (use what is there: torch 2.11+cu128, huggingface_hub 1.28, python; NO `transformers`). Only the EARS agent (doc 47) may use the BensPC GPU; it may stop the Qwen llama-server there first (it holds ~15 GB) and must say so in its report. Everyone else works on the Mac CPU.
3. **Compute etiquette on the Mac:** at most ONE training process per agent at a time, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, run with `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`. Every experiment wave < 30 min wall-clock. Foreground `sleep` is blocked; use `&` + `wait`. Scratch files go in your scratchpad dir, not `/tmp`.
4. **Science rules:** pass marks written to `PASSMARKS.md` and hashed (`shasum -a 256 … > SEAL.sha256.txt`) BEFORE any registered run; every seed reported, never averaged; one change at a time; a registered FAIL is recorded as FAIL, never re-run into a pass. Claims never exceed evidence. Every result ends with "What it means / What it does not mean". Deviations from your own plan listed.
5. **Design rules:** taught facts are never overwritten by inferences; web text never enters weights unverified; personal facts are never searched for; sleep is automatic and mathematical (replay/compression by formula; the model never picks what to store or proposes rules); the model must abstain (UNSURE / MISSING_FACT) rather than guess.
6. **Reports:** `artifacts/<your-folder>/RESULTS.md` (≤ 1,200 words, marks table with integer counts, what it means / doesn't, deviations, exact reproduce command) and `design/v3/30-modes/<your-doc>.md` (design, ≤ 1,500 words). Your final message to the orchestrator: ≤ 300 words, result first.
7. **Time box:** aim to finish in 2–3 hours of work. If blocked by a genuine decision that is Ben's, write the question in RESULTS.md under "Questions for Ben", pick the most conservative default, and continue.

## Repo map (repo root = `/Users/ben-hannan/Desktop/projects/beautiful-model`; run everything from there)
- `scripts/fable_notebook_contract.py` — Milestone 1 NOTEBOOK: append-only `events.jsonl` with hash chain; entities `E0001` + aliases; facts `(subject, relation, object)` with source tags `taught | proposed | inferred | web-quarantine | sleep-derived`; corrections supersede; hard-coded hop loop; statuses `OK, MISSING_FACT, BROKEN_CHAIN, AMBIGUOUS, UNKNOWN_ENTITY`; `--selftest`.
- `scripts/fable_listening_m1.py` — LISTENING doorway (plain software): clarify-or-write; `scripts/fable_listening_english.py` — English listening with the Qwen bridge (placeholder; hearsay markers list at line ~243 is incomplete: "rumour has it" missing).
- `scripts/fable_thinking_m2.py` — THINKING: `Thinking`, `BridgeSearcher`, `WebFetcher`, quarantine + 2-site trust policy; `--selftest` 18/18.
- `scripts/fable_agent_loop.py` — GLUE LOOP with Protocols `Ears.hear(turn)->list[action]`, `Mouth.say(record)->str`, `Reasoner.answer(question, notebook)->record`, `Sleeper.sleep(experience, notebook)->dict`, `Thinker.think(notebook)->dict|None`; `FakeEars/FakeMouth/LookupReasoner/StubSleeper` stand-ins; `fable_agent_loop_selftest.py`.
- `scripts/fable_reasoner44.py` (+ `_score`, `_stress`; artifact `artifacts/fable-reasoner44-20260921/`) — Exp 44 REASONER as skills + router: village N=60, R=8 relations, lookup matrices from the notebook, UNKNOWN sink, hop loop hard-coded, `ANSWER_THRESHOLD 0.9`, 64 base numbers + 27 per learned word; PASS 3/3; 32-hop stress 1.00.
- `scripts/fable_noisyteacher45.py`, `scripts/fable_hardgate46.py` (artifacts `fable-noisyteacher45-…`, `fable-hardgate46-…`) — the LIVE SLEEP RECIPE for installing a new word: robust loss `−log((1−ε)p+ε/N)`, ε=0.10, harden phi to argmax chain (±30 logits) after each fold fit and refit, unchanged 4-fold CV gate (OOF ≥ 0.80, refit agreement ≥ 0.90, old skills unchanged, reload identical), 60-start audit. 15/15 installs at ≤ 4 wrong of 20 episodes, 0 wrong installs / 120.
- `scripts/fable_learnedparity43j.py`, `fable_widelengths43k_v2.py` — length-general skills + router sleep (toy; 9/9 to 64 digits).
- `scripts/fable_creative_stop_toy.py` (artifact `fable-creative-stop-toy-20260921`) — CREATIVE dreamer + checker toy; KEEP_FIXED_N stop rule 3/3.
- `scripts/fable_ears45_*.py` (artifact `artifacts/fable-ears45-20260921/`, RESULTS.md) — ears rung 1: frames/panels generator, brakes, scorer, report. Registered FAIL on coverage; safety PASS (0 silent wrong writes) for tape and BiGRU.
- `scripts/fable_bert_loader.py` — OUR plain-PyTorch loader for BERT-family encoders (safetensors reader, WordPiece, encoder); `--check <snapshot>` verified 3e-6 vs reference on MiniLM-L6.
- `scripts/fable_webred_frames.py` → `data/open/webred/frames/{train,dev,heldout}.jsonl`, `relations.json` — WebRED (CC BY 4.0) as raw text + char spans: train 81,517 rows (481 relations, 44,080 positive), dev 3,898, held-out 26,302 rows / 40 relations; ~half are NEGATIVES (sentence does not state the relation). Closed-list map to our 8 relations in `CLOSED_MAP`.
- `scripts/fable_talker24_*.py` — earlier from-scratch talker attempt (reference only).
- Design docs: `design/v3/30-modes/` — 43 (ears/mouth design, brakes, τ rule), 36 (M1), 37 (M2), decided-inputs, 32 (Ben's simplification ruling), 46 (GPT ears scout), 47 (ears rung 2 spec).
- Qwen placeholder on BensPC: llama-server on port 8081, tunnelled to Mac `http://127.0.0.1:18081` (OpenAI-style chat endpoint). Fine for generating practice sentences / labels; never the deliverable.
- Predictions ledger `artifacts/fable-predictions-ledger.md` is append-only; you may APPEND a block of predictions before your run (number them P2xx continuing from the last entry) and an outcomes line after.

## Agents and ownership
| # | problem | prefix | design doc | artifact folder |
|---|---|---|---|---|
| 1 | Ears rung 2 (borrowed encoder) | `fable_ears47_` | 47 (exists; add `47b-…` notes) | `artifacts/fable-ears47-20260921/` |
| 2 | Thought format widening | `fable_thought49_` | `49-thought-format-v2-opus.md` | `artifacts/fable-thought49-20260921/` |
| 3 | Reasoner on the real notebook | `fable_reasoner50_` | `50-reasoner-on-notebook-opus.md` | `artifacts/fable-reasoner50-20260921/` |
| 4 | Wiring the real parts | `fable_wire51_` | `51-wiring-opus.md` | `artifacts/fable-wire51-20260921/` |
| 5 | Live sleep | `fable_livesleep52_` | `52-live-sleep-opus.md` | `artifacts/fable-livesleep52-20260921/` |
| 6 | Mouth (borrowed decoder) | `fable_mouth53_` | `53-mouth-borrowed-decoder-opus.md` | `artifacts/fable-mouth53-20260921/` |
| 7 | Modes + demo | `fable_modes54_` | `54-modes-and-demo-opus.md` | `artifacts/fable-modes54-20260921/` |

Interfaces between agents (so nobody waits): agents 3–7 build against the CURRENT notebook contract and the glue-loop Protocols. Agent 2 publishes its widened format as a new module + adapter (`fable_thought49_schema.py`, with `to_v1()` / `from_v1()`), and the others note in their docs where the adapter plugs in. Nobody blocks on anybody.
