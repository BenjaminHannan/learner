# Astra research council: Premonition

> Model update: Ben has requested GPT/xhigh agents instead of Astra. Replacement
> specialists will use the available `chatgpt-web/extra-high` route at `xhigh`.
> The initial group was interrupted by the account limit; no specialist reports
> were saved. Its agent IDs are no longer available in the current runtime.
> The directory name is retained for continuity.

Ben explicitly requested a super-deep investigation with coordinated Astra
agents to propose novel ways to improve this type of model. This is research,
design and critical review. Opus is already executing the separate milestone-2
answer-path experiment. Do not interrupt it or touch its implementation files.

The lead handles synthesis, experimental identification, dependency planning
and communication. Four independent specialists investigate distinct axes,
then exchange criticism before the lead ranks the surviving proposals.

## Context

Premonition-mini D is about 2.1M parameters: a minGRU/local-attention/minGRU
reader, line-card key/value store, pointerized names, a shared two-layer thinking
block repeated up to eight times, four scratch registers and a generative answer
decoder. Its larger vision separates reasoning, facts, language and continual
learning. Preserve that vision while challenging whether proposed mechanisms
actually achieve it. A conventional transformer is a control, not an automatic
replacement for the project.

Historical trainer notes report correct retrieval but chance answers even with
gold cards supplied. Those scratchpad probes are not independently reproduced.
Opus is currently reproducing them and testing whole-Think gating and separate
pre-think card access. Do not simply relabel these as new research proposals.
The current source may change during your work; identify what you inspected.

Read the current deeper report and relevant parts of the spec (later sections
override earlier ones), plus the older novel-mechanisms memo so you do not
rediscover existing project ideas. Historical VERIFIED labels in that memo are
not a substitute for checking the primary source yourself.

- `design/research/2026-09-18-deep-research.md`
- `design/06-premonition-mini-spec.md`
- `design/research/2026-09-18-novel-mechanisms.md`
- `design/research/2026-09-18-trainer-handoff.md`
- `reviews/opus-execution-02-answer-path.md`

Base directory: `/Users/ben-hannan/Desktop/projects/beautiful-model`.

## Research standard

Develop at most three concrete candidates in your assigned area and recommend
at most two. Go beyond a paper list: derive how the mechanism would operate in
this model, what information and training signals it requires, where it could
fail, and the smallest experiment that distinguishes it from a simpler method.
Include one serious negative result or rival explanation. Search current primary
papers and read relevant methods/limitations, not just abstracts or secondary
summaries. Cite exact URLs and distinguish verified paper results, code facts,
historical reports and your own hypotheses.

For each candidate give: a plain-language explanation, mechanism/equation or
pseudocode, closest prior art, what is new to Premonition versus genuinely
unestablished research novelty, relevant bottleneck, added training/inference
compute and state, supervision privileges, matched controls, decisive outcomes,
failure/kill criteria, and whether it depends on milestone 2 succeeding.
Do not claim world-first novelty from absence of a search hit. Do not import
oracle parsers, hidden simulator state or proof traces without explicitly
labeling and matching that privilege. Think about old-fact updates, role binding,
fresh identities, extra reasoning steps and independent held-out compositions.

Ben is a high-school student: lead each proposal with a clear explanation and
define terms. Put technical details afterward. Strong ideas are welcome, but
they must be understandable and falsifiable.

## Scope and budget

Read-only source/data inspection; no training, tests, package installation,
paid services, rentals, BensPC, external messages or additional agents. You may
write only the research file assigned to you under this council directory.
No edits to model code, shared spec, decisions log, or another agent's report.
Use at most roughly six primary sources deeply; target a 1,500–2,200-word
initial report. There will be a separate critique round. Return the report path
and a concise summary, including your strongest candidate and largest doubt.

Proposals are not implementation authorization. Existing $30 rental ceiling
and per-rental explicit approval remain. No new training budget is opened by
this research request. Avoid broad costly sweeps; give conditional small screens
and report runtime as unknown until measured.
