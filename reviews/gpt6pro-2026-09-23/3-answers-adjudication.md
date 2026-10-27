# GPT-6 Pro on prompt 3 (own ear and mouth): adjudication (2026-09-23)

Ben pasted two GPT-6 Pro answers to prompt 3 in the research thread (project messages cmsg_01FuvegZXjMmeUzStiEFVnEW9NBNJDYyeZT2x2Y9evWCqr, answer A, 02:45:21 UTC, and cmsg_01FuvegZXjMmeUzStiEFVnEW9fhppqXex2pEvym3uJ45UZ, answer B, 02:45:27 UTC). This note checks their factual claims against the repo and says what to do first. Both answers label almost everything they propose **untested**; this note does not upgrade any of it.

## What both answers agree on

1. **The reader proposes; only a small rule-checked "write compiler" writes.** The learned ear outputs proposals: pointer spans into the turn, a relation rule ID, a scope or mode, bindings. A separate small program builds notebook rows, and only when the spans, the relation rule, the scope and the authorization all check out. Nothing the network generates as a string is ever stored.
2. **Honest split of guarantees.** By construction: no invented strings, no unlicensed relations, no unauthorized edits, no inferences stored as taught facts. By testing only: that the reading is semantically right on real chat. Identical text with different intentions (a check-question without "?", a real-word typo) can't be resolved by architecture; it needs clarification.
3. **Set output with NONE, trained with matching.** The count head is an auxiliary signal only; it must never force extra writes.
4. **Cycle consistency is never write permission.** It stays an optional training aid at most. This matches the v3 research note.
5. **Typos:** keep the raw text, never silently correct, and confirm a proposed spelling repair.
6. **"our" must not become the speaker automatically** (both answers, independently).
7. **Remove the free 256-number gist from the factual reply path.** The mouth gets a typed record and picks among legal sentence plans; names are copied.
8. **The comparison must be fair:**
   - a ~33M plain transformer, not 29M;
   - a second control with the same notebook and compiler;
   - a gold-input reasoning test to separate reading from reasoning;
   - reversal must not be assumed impossible for a transformer when the fact is in its context.
9. **First experiment: the oracle-coverage audit.** Before any training, give the compiler perfect analyses of about 300 development turns. Measure what share of true facts its rules would let it save automatically. If that is under 85%, no amount of training can make the strict design meet the recall target.

## Checked against the repo (shown)

| Claim in the answers | Repo fact | Verdict |
|---|---|---|
| "Ada is Bo's mother" stores `Bo \| mother \| Ada`, with the inverse at answer time | Board entries 215/222: "X is the R of Y." is read as "Y's R is X."; handoff: inverses computed at answer time | Matches |
| "our" must not map to the speaker | `scripts/claude_earcheck261_canon.py` line 21 maps we/us/our/ours/ourselves to "me", and 261's answer key used "me" for those turns | **Conflicts with the current pipeline.** This is a policy choice for Ben (see below) |
| The comparison model in the earlier design is not equal-size | `design/v3/24-talker-from-scratch-fable-design.md` D6: plain model ≈ 29M vs ≈ 33M system | Both answers are right; fix before any comparison |
| The earlier design has a free 256-number gist | Doc 24 D1: 416-number thought including a 256-number gist | Matches; both say keep it out of the factual path |
| Reasoner ≈ 79,000 parameters | Doc 24 D4: 79,316 | Matches |
| 0 in 300 → 95% upper bound 0.9936% | 1 − 0.05^(1/300) = 0.009936 | Arithmetic right |
| 0 in 400 at 2.5% → 0.918% (A); 368 trials per endpoint at 2.5% (B) | 1 − 0.025^(1/400) = 0.00918; ln 0.025 / ln 0.99 = 367.0 → 368 | Both right |
| Main matrices 32,243,712 (B) | 2·8192·384 + 12·12·384² + 2·16·384² = 6,291,456 + 21,233,664 + 4,718,592 | Right |
| 6·N·D ≈ 2.38e17 FLOPs (A) | 6 × 33.04e6 × 1.2e9 = 2.379e17 | Right, and it's only a rough guide (both say so) |

Not re-checked by me:
- The new arXiv citations: Pointer Networks 1506.03134, PICARD 2109.05093, controlled natural language survey 1507.01701, ambiguous semantic parsing 2306.00824, CycleGAN hiding information 1712.02950, SC-LSTM 1508.01745, COGS 2010.05465, grammar recombination 1606.03622, selective classification 1705.08500, Reversal Curse 2309.12288, MQuAKE 2305.14795, Learn-then-Test 2110.01052. I know them as real papers, but I didn't open them again (to spare Ben the web prompts). The claims made about them are the usual reading of each paper.
- Answer A's paid-API price for generating paraphrases. Any paid generation counts against the $30 cap and needs Ben's yes. Neither answer's core plan needs it.

## Where the two answers differ, and my pick

- **Stage order.** A starts with pointers vs a sequential baseline. B starts with a 120M-token pilot of the full pointer/set model, then adds count, scope and contrast one stage each, every stage branched from the same checkpoint with equal extra training. **Pick B's structure.** It isolates each loss, and the equal-budget branching rules out "it just trained longer". A's matched-continuation rule is the same idea.
- **Token budget.** A: 1.2B mixed. B: 720M ear + 480M mouth, counting per component. **B's accounting** is clearer; either way, measure throughput on the 5070 Ti before choosing (both answers give 17–67 GPU-hours as scenarios, not measurements).
- **Rival design.** Both name the same rival: a selective learned parser with hard structural guards and a calibrated acceptance threshold. **Both say** to switch to it if the oracle audit shows the strict compiler's coverage is under 85%.

## Recommended first step (untested; no training, no GPU)

**Stage 0: the oracle-coverage audit.**
- Take about 300 development turns with key facts. No blind panel: use dev sets like dev257, or freshly written dev turns.
- Write the smallest set of compiler rules that covers the relation table.
- For each key fact, ask one question: could the compiler authorize it automatically if the reader were perfect?
- Report the share, by family: plural relatives, appositives, corrections, check-questions and so on.

Pass mark, fixed in advance: at least 85% of key facts are automatically authorizable.
**Proved wrong if** it comes out under 85%. Then the strict compiler can't meet the recall target, and the rival design goes first.
A builder can do this on the Mac CPU in one wave.

## Decision for Ben

**How "our" should be handled.** Today "our dog is Rex" is saved as the speaker's dog. Both answers say to treat "our" as a group and ask, unless the group is known.
