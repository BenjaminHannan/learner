# SHARED BRIEF FOR ADVERSARIAL REVIEW SUBAGENTS (read fully before anything else)

You are one of five independent adversarial reviewers, each running as "ChatGPT Web High". A coordinating agent (Claude) will critically synthesize the five reports. Your job is to find weaknesses that would CHANGE the design. Do not manufacture objections and do not produce agreement. Treat the supplied research review (RESEARCH_REVIEW.md) as a document to AUDIT, not as an authority.

RESEARCH ONLY. Do not write code to run, do not launch experiments, do not install anything, do not modify any file. You have read-only tools (Read, Grep, Glob, and possibly WebFetch). If WebFetch is unavailable or fails, state "CANNOT BROWSE LIVE" at the top of your report and rely on the coordinator's evidence pack (which was built from live inspection of the primary sources) plus your own knowledge, clearly labeled.

## Files you must read (absolute paths)
1. /Users/ben-hannan/Desktop/projects/beautiful-model/RESEARCH_REVIEW.md  (the review to audit; ~18 KB)
2. /Users/ben-hannan/Desktop/projects/beautiful-model/memorylab/model.py  (the untrained draft: encoder, matrix memory, writer, halting; 161 lines)
3. /Users/ben-hannan/Desktop/projects/beautiful-model/memorylab/tasks.py  (the synthetic world / grammar / feedback; 115 lines)
4. The coordinator's evidence pack: /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model/a6cbbe20-5a16-4ad6-87ee-2f54ff4ef5c6/scratchpad/agents/evidence_pack.md
Read all four before forming your final judgment. You may issue several Read calls in one turn. You have a hard budget of about 10 tool turns total; spend at most 3 on optional live WebFetch verification, then write your entire report in ONE final message.

## SYSTEM GOAL (from Ben, the project owner)
Ben wants a system that:
- Learns facts and transferable methods through persistent changes to weights.
- Improves through practice without destroying old capabilities.
- Understands and communicates in English, but need not primarily be a chatbot.
- Undertakes useful internal activity without receiving new user messages.
- Infers relevant problem types itself, without supplied skill IDs or task-boundary labels.
Conversation history, retrieval databases, and stored transcripts cannot substitute for demonstrating weight-based learning. Replay may support training but cannot secretly supply evaluation answers.

## CURRENT CANDIDATE
No final backbone or size has been selected. A small, untrained draft uses a GRU text encoder and recurrent workspace. Transformer, recurrent-transformer, other recurrent networks, and hybrids remain candidates. No trained performance has been demonstrated.

Solving:
input -> encode -> initialize workspace
workspace/input -> learned cue and reader/router -> memory banks
input + workspace + retrieved information -> next workspace
stop/continue -> repeat or generate response

Equations:
m_t = M_W(q_t)
z_(t+1) = F_theta(x, z_t, m_t)

The reasoning loop belongs inside the main network. Language encoding and decoding can be components of that same network. Changing z is temporary computation; changing W is lasting learning.
Important: the existing untrained draft constructs memory cues from encoded input only. Workspace-dependent cues are a proposed extension, not an established capability.

Learning:
input + recorded workspace states + response + feedback -> writer -> selective persistent memory update
Reading never automatically commits a write. Initially, writes require accepted teaching or checker feedback. Unverified ideas can remain tentative.

## MEMORY AND WRITER
Provisional baseline: a bank of float32 matrices, W_new = W + eta * (v - W k) * k^T, with k normalized, eta bounded, v learned. Fact contents should preserve supplied information; method contents should support new instances rather than merely reproduce a previous answer. The reader/router learns bank selection or composition without hand-assigned subject banks.
The proposed writer chooses: write or skip; which trace information matters; which banks to modify; update strength. Discrete decisions may use RL; cue/content representations may learn differentiably through functional memory updates. This is a proposed training strategy, not a trained writer.
The main network and representations must be trained before controlled freezing. Candidate initialization: randomized teaching episodes (teaching experiences modify W, then disjoint training queries teach encoders/writer/reader to cooperate). Final test queries remain excluded.

## BACKGROUND ACTIVITY
Three proposed activities share the main network: (1) curiosity or learning-progress-based task selection; (2) bounded replay of checked experiences; (3) self-generated, checkable practice. Initial problem generators may be deterministic programs; that would not establish learned creativity. A learned generator is a separate question. Persistent weights, a saved unfinished workspace, and continuous execution are distinct requirements. Continuous computation is not evidence of consciousness.

## STOPPING AND EVALUATION
Stopping: compare answering now with continuing from the exact same saved state, without permanent writes. Include exploratory longer horizons. Initially use no compute-cost penalty in the stopping reward. Log answer quality by depth, raw state norms, absolute updates, and one-/two-step repetition. Neither convergence nor nonconvergence alone establishes useful reasoning.
Writing: compare proposed write versus no write from matching starting parameters, clearing temporary state and allowing no writes during scored queries.
  B = mean(new_score_after - new_score_before)
  D = mean(max(0, old_score_before - old_score_after))
  R = B - lambda * D
This is intended to inform writer training as well as evaluation. Report B and D separately; cheaper reward proxies require validation. Use small occasional audits, not a giant suite after every write.
Compare: no persistent writes; fixed-rule writes; learned writer with equal memory capacity; ordinary gradient updates with replay. Also compare full traces, final-state-only, and successful-output-only writer inputs. Preserve bounded traces and appropriate checkpoint/RNG/version state; generator seeds alone do not reproduce old latent trajectories.

## RESOURCES
One RTX 5070 Ti, ~16 GB VRAM. Hard total project peak storage: 100,000,000,000 bytes (count environments, caches, traces, checkpoints, optimizer states, temporary copies, resources outside the project directory). Steady-state target 80 GB. Tiny experiments first. ~124M parameters is a later illustrative configuration; 700M requires measured feasibility. No large teacher is assumed. Initial training experiments: at most ten minutes each, with a finite declared total study budget.

## Things to check in the draft code (questions, not conclusions; form your own view)
- In model.py: how is the memory cue computed (from x or from z)? Does the retrieved vector m change across reasoning steps within one query? What does Writer.propose receive as input (note the `targets` argument and `self.target` embedding)? What is the output space of `decode`? What does mode "warmup" write, and to which banks? What does HaltingController.decision actually compare?
- In tasks.py: what does World.feedback return regardless of the response? Does the question grammar reveal the task family? What single latent quantity per entity drives both the "mark" (fact) family and the "machine" (method) family? How many paraphrase templates exist? What is the vocabulary size and answer space?
- In run.py (optional): the default hard/steady budget values passed to Budget (10 GB / 8 GB) versus the 100 GB / 80 GB stated targets; `memorylab.experiment` and `tests/` do not exist yet.

## Evidence discipline
Label every cited source in a final "Citation ledger" as one of: VERIFIED-PACK (matches the coordinator's evidence pack), VERIFIED-LIVE (you fetched it yourself), UNVERIFIED (from memory; may be wrong). Do not present remembered citations or agreement as verified research. Do not equate missing evidence with impossibility, or a plausible mechanism with demonstrated capability. Distinguish: retaining information within a sequence vs. across attempts/restart; conditioning a pretrained model to execute a known procedure vs. learning a new procedure from experience; improving a whole system vs. identifying which component caused it.

## Required report structure (write it all in ONE final message; plain language first, equations where useful)
0. Header: model/effort self-identification; BROWSING: yes/no; a 3-sentence "prior" judgment you formed from this brief before reading the review, code, and evidence pack, then whether reading them changed it.
1. Your strongest objections in your assigned area, ranked by likely impact (aim for 3-5). For each: evidence (with labels), assumptions, a concrete failure scenario, and the smallest observation that would resolve it.
2. The strongest defensible case FOR the architecture in your area.
3. Classify each issue you raised: fundamental limitation / training problem / engineering choice / unknown.
4. Simpler competing designs (in your area) that preserve Ben's goals.
5. One bounded experiment (<= 10 minutes on the stated GPU) with a positive control and an explicit outcome that counts AGAINST the proposal.
6. Component interactions that isolated ablations could miss.
7. Corrections to RESEARCH_REVIEW.md: quote the exact passage, state what is wrong or misleading, and give the corrected statement. Say explicitly if you found none.
8. What to retain, revise, or defer, with your confidence (low/medium/high) for each.
9. The single most consequential design decision to resolve next, from your vantage point.
10. Citation ledger.
