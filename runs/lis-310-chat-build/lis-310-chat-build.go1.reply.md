Building your listener plug-in — wiring the chat agent to save only verified facts.
I've got the listener and base specs mapped — now digging into how self-owned facts are stored.
Worktree lacks the lis-300 modules — I'll shim those via `git show` copies. Now probing how the base stores facts.
Screens mapped. Now probing the live base to see how "my" facts are stored.
Base stores "my" facts as `USER`. Checking the server's agent-loading contract before writing code.
No published threshold, so default 0.99 applies. Probing candidate test turns on the raw base.
Probes confirm the design. Setting up the build.
Now writing the agent.
Now the test and demo files — checking the daemon mailbox API first.
The file tail was truncated — appending the missing section.
7/10 pilot. Two bugs to fix (double possessive; base no-op writes swallowed) plus one mystery (mouth says "USER's" vs "your"). Probing the mystery first.
Found it — Me166 renders `USER`→`your` at turn level. Checking contract status values, then fixing all three issues.
All 10 pass. Adding one more pilot test for the pending-drop fall-through path before sealing.
Pilot green (11/11) and demo smoke works. Sealing now.
Verdict: PASS.

lis-310 (291 + listener) built, sealed, registered run green. New files only; no existing file edited (ledger append-only via cat >>); no TEST-ONLY panel touched; all names fictional.

Marks table (integer counts):

| Mark | Bar | Got |
|---|---|---|
| P310.1 all sealed unit tests pass | 11/11, exit 0 | 11/11, exit 0 |
| P310.2 base-chain writes in T7 (5 turns) | 0 | 0 |

Every move (registered run, StubReader, threshold 0.99):
- T1 2-facts-save-2: PASS, saved 2 triples, base Saved reply.
- T2 whose-ask: PASS, exact "Whose dog is Pip, yours or someone else's?", 0 saved.
- T3a ask-back then yes: PASS, exact ask-back, 0 saved, yes saved exactly 1.
- T3b ask-back then no: PASS, 0 saved.
- T3c ask-back then other turn: PASS, pending dropped, new turn saved normally.
- T4 negation: PASS, 0 saved, base reply used.
- T5 CHECK "so X is Y": PASS, base answered "I already have that.", 0 new events.
- T6 question: PASS, answered from notebook, 0 new events.
- T7 five rule-chain-teachable turns (SUPPOSE/NEGATE/PLAN/REPORTED/CHECK frames): PASS, each verified in-run to write on raw 291 first, then 0 events/0 triples under 310.
- T8 unparsed: PASS, exact sorry-reply, 0 saved.
- T9 chatdemo-load: PASS, Loop310Daemon + build_agent310 + DEFAULT_CONFIG310 loadable server-style; demo mailbox turn saved 2. Server not edited.
- Misses: 0. Deviations: 0. Seal 4/4 OK post-run.

What it means (plain high-school English): the chat agent now saves facts from the listener instead of hand-written rules, saving exactly what it should and nothing else; questions still come from the notebook; the old rule chain cannot sneak in a save. "My sister is Mira" stores as subject USER and reads back "your sister", exactly like the base, so old and new saves mix.

What it doesn't mean: it used a stub reader, not the real fine-tuned model, so nothing about real hearing quality; median/p90 ms unmeasured. Real-model 20-turn chat skipped: ~/premonition-models/lis300-merged/ does not exist.

Notes for the director: hook = turn310 outside turn291 (outermost wrapper); me→USER with the base's Me166 render (confirmations byte-identical to base); 209 + 252b screens gate every listener save (0 hits in tests); every turn logged to state_dir/lis310_log.jsonl. Disk 12 GB free; load was ~89 (shared Mac) but the light CPU suite ran fine. PUSH paths in place: artifacts/claude-lis310-20260923 scripts/claude_lis310_agent.py scripts/claude_lis310_test.py scripts/claude_lis310_demo.py artifacts/fable-predictions-ledger.md.
