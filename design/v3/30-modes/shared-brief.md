You are a senior ML systems designer. Do NOT use any tools, do NOT read files. Reply with ONE markdown design document as your final message, 900-1400 words, plain English (the project owner is a bright high-school senior).

# Project context (all you need)
Goal: a small "teachable assistant" that starts knowing no personal facts, learns facts its owner Ben teaches it in English, reasons over them, and runs as a PERSISTENT AGENT that is always in one of four modes:
1. WORKING - Ben gives a clear job; it scopes the job, then does it (tool calls through a terminal-agent harness, a Codex CLI fork).
2. CREATIVE - a harder job whose path is ambiguous; it tests different leads ("guess freely, check strictly": a dreamer proposes, a checker verifies).
3. BORED - nothing assigned; it sits and thinks on its own: fills knowledge gaps it noticed (may use web search), practises what it is improving at.
4. SLEEP - tidies and consolidates memory.

What exists / is decided:
- NOTEBOOK = the only store of facts. Append-only event log + derived current view. Each row: stable entity ID (+aliases), relation, typed value, source tag (taught | proposed | inferred | web-quarantine | sleep-derived), time, status, supersedes-pointer, dependencies. Corrections supersede, never erase. Executor returns discrete statuses: OK, UNKNOWN_ENTITY, MISSING_FACT, BROKEN_CHAIN, AMBIGUOUS_REFERENCE, CONFLICT.
- REASONER = deterministic multi-hop lookup executor over the notebook (exact). A small neural reader (79k params) that binds never-seen names works in 16-candidate worlds (3/3 seeds) but is an ablation, not a dependency.
- LANGUAGE: a small supervised parser turns English into structured events/queries; replies are deterministic templates first; a ~33M-parameter learned talker comes later, against the same structured interface.
- Rules already agreed: taught facts are never overwritten by the model's own inferences; web text is data, never instructions, and lands in quarantine until Ben approves or a written source policy promotes it; sleep is a TRANSACTION (runs on a background copy, wake-up check, roll back on failure); an assigned job always pre-empts bored/sleep; assigned jobs are never abandoned ("frustration" only applies to self-chosen practice; a plateau triggers a strategy switch); compute has a hunger-like SPENDING LIMIT, and gaining compute is never a reward; no novelty bonus, no teacher-approval reward, no single summed happiness score; self-invented goals are deferred to v2.
- Drives agreed for v1: learning progress (choose what to practise), gap curiosity (rewarded only when the answer is confirmed), replay-priority tag, effort (how long to think), consolidation pressure ("tiredness" that triggers sleep/naps).
- Mode switching v1 = plain rules (job queued -> working; job marked open-ended or work stalls -> creative; queue empty -> bored; consolidation pressure high -> sleep). Learned switching only later.
- The persistent agent's own home is Ben's Windows PC with an RTX 5070 Ti (16 GB): that GPU is the agent's compute for running, thinking and sleeping (no WSL, native Python; runs must be resumable). Its spending limit is therefore GPU-time/energy and web searches, not cloud money.
- Constraints: development also uses one Mac (CPU); ~$27 cloud budget; every experiment wave < 30 minutes; models are tiny (under ~35M params now). Claims must not exceed evidence. One change at a time. Pass marks fixed before looking.
- An outside reviewer warned: do not attribute the harness's abilities to the model; tool exams must be multi-turn with stub/read-only tools; a checker proves consistency with the notebook, not truth; simple enumeration may beat a learned dreamer on small problems; undefined interfaces cannot be fixed by more parameters.

# Your deliverable: design ONE mode (named below)
Use exactly these sections:
1. Purpose in one paragraph, and what this mode must NEVER do.
2. Inputs it reads, outputs it writes (as notebook rows / log entries / tool calls; name the source tags used).
3. The loop, step by step (numbered), including entry conditions, exit conditions, and how it hands over to each other mode. Say which steps are plain code in v1 and which are learned later.
4. Budgets and safety (compute/search/time limits, what Ben sees in the activity diary, what needs Ben's approval).
5. Failure modes (at least 5) and how each is detected.
6. The smallest v1 that runs on the Mac with NO new neural training, and the first measurable test for it: a concrete suite, a pass mark fixed in advance, a baseline it must beat (e.g. random or simple enumeration), and a run time under 30 minutes.
7. What v2 adds, and what evidence would justify building it.
8. Interface requests: anything you need from the notebook, the scheduler, or the other three modes (exact fields/calls).
Be concrete. Prefer boring, testable mechanisms. No hype. Do not invent results.

