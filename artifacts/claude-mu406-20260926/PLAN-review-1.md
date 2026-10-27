# mu-406 plan, review 1 (written 2026-09-26 19:33:42 UTC by date -u; the draft stays unsealed)

The Thread manager reviewed PLAN-draft.md at 19:33 UTC. Changes adopted for the sealed version:
- Second filter on kept replies (the Thread manager's objection: with a G1 pass at 70%, up to 3 in 10 made-up claims
  could pass GLM and be trained on as clean). A kept reply is also dropped by code when it names a fact-like value that
  appears in none of the chat's user turns, from either session, and not in the notebook input. "Fact-like value" means any value in the fact generator's
  slot lists (scripts/claude_mu405_facts.py: names, pet names, jobs, home towns, events, days, allergies, hobbies),
  matched case-insensitively as whole words. The sealed plan reports the share of GLM-kept replies this removes. Limit,
  stated: it catches made-up values of those slots, not made-up feelings or situations. If g406 fails, this code filter
  is the only filter, as the draft already said.
- The test panel (60 fresh two-session DEV chats, fictional names) is written, checked, sealed and kept blind before
  any practice data is generated or any training starts, never after.
