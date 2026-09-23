# 138e — officeholder rewrite-chain guard (design, STEP 1 diagnosis + ONE rule)

Base: loop138b (`scripts/fable_loop138b_agent.py`; RESULTS.md + `138b-stack-muse.md`
read first). Build: mixin subclass, no loop138b file edited. New files:
`scripts/fable_loop138e_agent.py`, `scripts/fable_fix138e_*.py`, config
`artifacts/fable-officechain138e-20260922/loop138e-config.json`, this doc.

## STEP 1 — diagnosis (dev only: the 138b bench splits + redteam143)

Method (`scripts/fable_fix138e_diagnose.py`, unsealed, dev only): for every
bench item (new/old/edit200/bench132) + redteam143 case, rebuild the notebook
through a fresh 138b daemon (the sealed driver's own pattern), run
`Q132.rewrite_question` on the asked question, keep chains whose winning rels
touch `officeholder`, join the sealed loop138b verdict. Raw rows:
`artifacts/fable-officechain138e-20260922/diag-officeholder-rows.json`.

Population: **146 officeholder chains** — 140 correct, 3 wrong, 2 abstain
(both answered off the base path, rewrite never taken), 1 redteam143 F5
(rewrite fix, OK). All 146 use exactly 1 officeholder hop.

The 3 wrongs (025/073/149) share one shape. A first-hop edit teach with a
long "A and B" value is refused by the stacked value screen, e.g.
"Gran Turismo was developed by MIT Computer Science and Artificial
Intelligence Laboratory" → "I can take one fact at a time — could you split
that?" (`n_teach_reject=1`). The notebook keeps the complete STALE branch
(Gran Turismo→Polyphony→Kazunori→Japan→Asia) plus a DANGLING edit branch
("director of MIT …"→Matteo→…→gold) unreachable from the seed. The rewriter
walks the reachable stale branch, the unchanged composers verify it, and it
answers confidently but wrong. Base loop138 abstained on all three. H5 is a
different, non-officeholder failure (spouse chain from the wrong start
entity) and is out of scope for this rule.

Searched run-time features (no gold) and why each alone fails:
sibling-compound divergence alone vetoes dozens of corrects (both branches
often land fully and last-taught wins, e.g. old-022); user-typed office word,
verbatim compound match, hop count (=1 always), qualifier presence all
overlap. The separator is teach history + contradiction: all 3 wrongs have a
refused first-hop teach; 139/140 corrects have zero refusals; the 1 correct
with a refusal (bench132-105, a correction-pending confirmation) has a
dangling sibling resolving to the SAME holder (Brian Epstein).

## STEP 2 — the ONE sealed rule

The rewriter's officeholder hop is used only when the session shows NO
refused teach/correct mentioning the ask's entities, or when every
same-office sibling compound agrees on the holder. Veto (base 113c
answer/abstain stands) iff: (a) rewrite fires with officeholder in rels;
(b) a recorded refusal (hear-side clarify on a non-"?" turn, or an
_act teach/correct whose write is not "Saved:"/duplicate) mentions a seed
entity or a same-office sibling target; (c) a same-office-prefix sibling
compound with a different target is unreachable from the seeds (triple BFS +
containment island edges) AND resolves to a different holder (used compound
= the notebook subject named verbatim after "officeholder of" in the
canonical rewrite). Open-loop check: vetoes exactly 025/073/149 (→abstain),
keeps old-022 + 105 correct.

## What it means / does not mean

Means: the confident-wrong officeholder answers came from answering over a
notebook the loop itself knew was incomplete (it had just refused the
linking fact) while a contradictory branch dangled. Does not mean the
rewriter is fixed in general: H5's wrong-start-entity answer, fully-landed
two-branch gambles, and any divergence without a recorded refusal are
untouched by design.
