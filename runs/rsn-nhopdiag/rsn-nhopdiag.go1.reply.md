Diagnosing the backwards-answer bug — reproducing dialogs and tracing the loop code.
I see the symptom stage naming — now hunting the exact handler that swaps the question direction.
The forward-only walk looks like the culprit — now setting up a clean reproduction.
Pilot first to confirm which phrasings the agent actually stores.
Full run finished — pulling the first half of results to confirm the head of the table.
Cause chain confirmed — checking the correct fallback path for contrast.
VERDICT: REPRODUCED and CAUSE FOUND. The `loop138-nhop` stage answers backwards questions with the forward fact about the value. Stored facts are intact in all 36 dialogs — only the reply is wrong.

CAUSE (two cooperating defects, both forward-only with no direction check):
1. `scripts/fable_bench92_english_arm.py:222` — `compose_n_hop` walks forward only (`if s == cur`); no `o == cur` backward branch exists. For "Whose spouse is Dana Holt?" the only mentioned entity is the VALUE, so the walk starts at Dana Holt and follows her outgoing edge to Ravi Stone. The coverage gate (`:237-239`) checks the relation is mentioned, not its direction.
2. `scripts/fable_loop138_agent.py:122-131` — the nhop branch asks `(name=start=value, rels)` first, so the notebook resolves forward and the correct reverse path below it (`Reverse190Mixin`, `scripts/fable_fix190_reverse.py:207-234`) never fires. 138n inherits this branch unchanged.

MARKS TABLE (36 dialogs / 102 turns, fresh agent each, CPU only):

| mark | n |
|---|---|
| dev dialogs (34 own + 2 director anchors) | 36 |
| teach turns stored correctly | 66/66 |
| backwards chain questions WRONG from `loop138-nhop` | 12 |
| controls CORRECT (gold match) | 13 |
| RECORD-only (abstains / other stages) | 9 |
| MISMATCH vs my gold (extra finding, see below) | 2 |
| stored triples wrong anywhere | 0 |

EVERY MOVE (final turns): WRONG (12, all `loop138-nhop`, reply = forward fact): d01, d02 (director spouse anchors), d03, d04, d05 (husband), d06 (wife), d11 (director author anchor), d12, d16 (founder), d29 (3-link chain), d33 (author "whose"), d34 (founder "whose"). CORRECT (13): d07, d31 (spouse reverse), d10, d30 (spouse forward), d20, d21 (boss), d22 (boss fwd), d23, d24 (mother), d25 (mother fwd), d26, d27 (friend), d28 (friend fwd). RECORD (9): d08, d09, d15, d19, d35 (2-subject → `none` abstain), d14 (author no-chain → abstain), d32 (`bench73` "Was that a question?"), d36 (`fake` abstain), d18 (founder no-chain → correct `loop221-table-inverse` with "(worked out backwards)").

MISSES/DEVIATIONS: d13 "Who wrote Salt Harbor?" → "Salt Harbor's author's author is Milo Hart."; d17 "Who founded Ember Bay?" → "Ember Bay's founder's founder is Daro Venn." Same family (walk-to-sink loop `:221-234` over-walks 1-hop forward questions into 2-hop answers) — reported, not claimed fixed.

RELATIONS: trigger is NOT symmetry, it's composer cue coverage (38 cued relations: spouse, author, founder, founded_by, employer, child…). Cue-less relations (boss/mother/friend) fall through to `loop190-reverse`, 8/8 correct. Bug needs all three: cued relation + real chain (value has an outgoing edge) + exactly 1 entity named.

PROPOSED ONE CHANGE (not built): direction guard at the nhop branch (`fable_loop138_agent.py:122-131`, or additive wrapper above it): when the question is reverse-shaped about `start` ("whose R is V", "who is married to V", "what has V written", "what did V found"), return None so it falls to the proven `loop190-reverse`/table-inverse path. Question-side only. PASS MARKS: same 36 dialogs → 12/12 flip to gold reverse reply, 13/13 byte-identical, 9/9 RECORD unchanged, 66/66 teaches saved. FALSIFIER: any of the 12 still answers forward, or any of the 13 controls changes, kills the proposal.

WHAT IT MEANS (high-school plain): with verbs like married/wrote/founded, asking "who's on the other end?" makes the agent look the wrong way down the chain — but your saved facts are fine (0/36 corrupted). WHAT IT DOESN'T MEAN: data isn't corrupted; boss/mother/friend aren't broken (8/8 right); forward questions work; longer chains aren't safe (d29 fails too).

OUTPUT: `artifacts/claude-nhopdiag-20260923/` (DIAG.md + dev_dialogs.json + raw_replies.json, 102 rows with stage/reply/triples per turn) plus drivers `scripts/claude_nhopdiag_20260923_{pilot,repro}.py`. New files only, staged not committed (OPUS-RULES forbids pushes, so the `PUSH:` line is satisfied by staging the directory in the worktree for collection). No panel touched, 1 process used, disk was 17 GB free.
