# Standing research 05: joining the reader, the reasoner and the talker

Written 2026-09-28 (standing research helper, Sonnet). Nothing here was run. Link tags: **A** = abstract page fetched and read on 09-28; **T** = title page only; **M** = from memory, not opened. Labels: shown / suggested / untested.

## What is on main (so I do not repeat it)
`artifacts/claude-dir-h4-e2e-20260928/PLAN.md` (H4) audits the chain and `artifacts/claude-dir-h5-e2e-glue-20260928/` (H5) builds the panel, scorer and glue. The parts of H4's audit I lean on (shown there, quoted, not re-checked by me):
- Nothing has run end to end with learned parts (PLAN.md section 0, item 1). Reader, reasoner and talker have three different input formats (item 3).
- Learned counterparts still owed (section 2): the puzzle detector (hand-written `read_latin`), the reasoner's stop rule (hand rule), the reasoner's "am I sure" (a code check), "I don't know" (a prompt line; y1t's trained doubt was NO-GO on its own dev: 22 right, 20 wrong candidates, `artifacts/claude-y1t-20260926/VERIFY-y1t.md`), and a talker that faithfully retells the reasoner's grid (untested; the plain 1B failed at copying, 25/39/28 of 100, `artifacts/claude-rsn358b2-20260926/VERIFY-recount.md`).
- Director default for the routing gap: gate the reasoner call on the reader's learned `act` field (`handoff/director-roadmap.md`, 19:50 update).

## Sources
| source | what it says | tag |
|---|---|---|
| Agents Thinking Fast and Slow: Talker-Reasoner, https://arxiv.org/abs/2410.08328 | A fast "Talker" that converses and a slow "Reasoner" that plans, joined through shared memory; named after Kahneman. Same shape as reader to reasoner to talker. Opening only. | A (opening only) |
| BLIP-2, https://arxiv.org/abs/2301.12597 | A small trained "Querying Transformer" bridges a frozen encoder and a frozen language model; only the bridge is trained. | A |
| Flamingo, https://arxiv.org/abs/2204.14198; LLaVA, https://arxiv.org/abs/2304.08485 | Same pattern: frozen parts plus a small trained connector. | T |
| Toolformer, https://arxiv.org/abs/2302.04761 | The model decides which tool to call, when, and how to use the result, trained self-supervised (keeps calls that help predict later text). Names arithmetic as a weakness tools fix. | A |
| ReAct, https://arxiv.org/abs/2210.03629 | Interleaved reasoning and tool actions. | T |
| R-Tuning, https://arxiv.org/abs/2311.09677 | Trains a model to refuse questions outside what it knows, by first finding what it gets wrong. Opening only. | A (opening only) |
| Pointer-generator, https://arxiv.org/abs/1704.04368 | A copy mechanism so output can reproduce input spans exactly. | T |
| Deep Learning and the Global Workspace Theory, https://arxiv.org/abs/2012.10390 | Proposes a shared workspace joining specialist modules through learned translation between their latent spaces. | A |
| Semi-supervised multimodal representation learning through a Global Workspace, https://arxiv.org/abs/2306.15711 | A global-workspace architecture learns to align modalities from only sparse matched pairs. | A (opening only) |
| Neural Module Networks, https://arxiv.org/abs/1511.02799 | Compose small learned modules per question. | T |
| Perceiver IO, https://arxiv.org/abs/2107.14795 | One fixed-size latent that many input and output types read and write. | T |
| Lambon Ralph et al. 2017, hub-and-spoke semantic memory | One amodal hub links modality-specific areas, so words, pictures and sounds share a meaning store. | M |
| Fedorenko, Piantadosi, Gibson 2024, "Language is primarily a tool for communication rather than thought", Nature | Reasoning networks in the brain work without the language network. | M |
| Baars; Dehaene, global workspace | Specialists broadcast into one shared workspace. | M |

## Brain angle (suggested, simplified, not checked here)
- Language and reasoning are separate systems in the brain, joined through a shared meaning store, not through a pairwise text protocol. That is Ben's design (reasoner is the model; reader and talker are translators).
- Where silicon does better: exact copying of a checked result into the reply, and an exact checker (a verification tool) whose verdict is a label. Both are on the goals page's "silicon can improve biology" list (`design/v3/30-modes/ben-goals-2026-09-26.md`, lines 62-67).

## Leads, ranked (guesses mine, not measured). Each is a single change against H4's sealed panel; they touch different owed pieces.

**Lead 0 (read-only, cheapest): can the plain talker retell a checked grid?** Give the LFM talker 100 checked grids (code-made truth) as the fixed reasoner note and score exact retelling. Wrong to worry if 95 of 100 or more are exact. If it is low, the learned fix is a small copy-trained talker adapter on code-made note-to-reply rows (Luna-worded), not a rule. Untested. Why first: H4 marks this untested and every chain score depends on it.

**Lead 1 (guess 35%, my top pick because "I don't know" is still unlearned): doubt read from the reasoner's own state, not from text.** y1t failed because it asked a text model to judge a candidate from chat text. Change only where the doubt signal comes from: a small head reading the reasoner's state (answer flips, gap between top answers, state movement in the last rounds, as in topic 02 Lead 3) with labels made by the code check (does the filled grid solve the copied square?). The talker then gets a fixed disclosed line ("unsure") when the head fires, replacing the prompt-only line. Judge alone first: AUROC and coverage-versus-risk on a fresh panel of solvable and unsolvable squares. Wrong if AUROC is below 0.7 in either seed, or if false doubt on solved squares exceeds 20%. Depends on topic 02 Lead 3 showing at least one useful signal. Untested.

**Lead 2 (guess 40%; near the Director default, so low novelty but highest chance): two learned votes replace `read_latin`.** Route to the reasoner only when the reader's `act` field says puzzle and the learned copier (gr-9) returns rows, not `none`; if the two disagree, the reply asks the user to resend. Change is only the router. Measure miss rate and false-call rate on the panel against `read_latin` as disclosed scaffolding. Wrong if false calls or misses are worse than `read_latin` by more than the panel noise. Depends on lis-320 weights and gr-9 passing its sealed panel (H4: gr-9 is DEV-FAIL, 197 of 200 vs bar 199). Untested.

**Lead 3 (guess 10%, later): a shared workspace instead of pairwise formats.** One fixed-size latent (Perceiver IO style) that the reader writes and the reasoner and talker read, with learned translators trained from few matched pairs (Global Workspace papers, BLIP-2 for the frozen-part pattern). It removes H4's "three formats, no shared one" gap at the root, but it is a new architecture (needs Ben's yes) and the reasoner takes integer tokens today. Not for the first joined demo. Untested.

## Marks reminders (H8 checklist)
Each lead needs a plain-twin row (the same chain with the plain talker/router) and a check that the gain is not memorisation of the 60 lives; bars above measured noise (unknown for the chain: run two seeds of the whole panel before setting bars).

## Not checked / risks
- Opening-page reads only for the Talker-Reasoner, R-Tuning and workspace papers; those systems are built on large LMs and none was tried on a tiny loop reasoner.
- I did not read the panel spec (`PANEL-SPEC.md`), so I do not know which of the 11 marks each lead would touch.
- Lead 1's labels come from a code check on a Latin-square task; a check for other kinds does not exist yet, so this lead is scoped to squares.
