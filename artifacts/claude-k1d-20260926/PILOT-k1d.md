# k1d DEV pilot result and the next fallback (Creative answers in chat thread, written 2026-09-26 16:35 UTC)

Not a registered run. DEV practice data only (artifacts/claude-k1a-dev-20260926, 40 chats, readable).

## k1d: the 1B reads each of its drafts as the user would (scripts/claude_k1d_pilot.py, wording fixed at 16:28 UTC
before any score)
Same 4 drafts per chat as the k1c pilot (the k1a writer, no adapter), the same blind verdicts (two judges plus a
third on splits). Useful replies out of 40:

| Pick | Useful | Gained vs first | Lost vs first |
|---|---|---|---|
| first passing draft (k1a) | 12 | | |
| P, pointwise information (k1c, sealed and running) | 15 | 8 | 5 |
| Y, the 1B as listener, log p(Yes) - log p(No) | 14 | 5 | 3 |
| any of the 4 drafts useful (oracle) | 26 | | |

Y picked a draft other than the first on 36 of 40 chats and the same draft as P on 9. Reading: neither model-only
signal finds the useful draft much more often than taking the first one; the gap to the oracle (26) is 11 or 12 chats.
Y is no better than P on DEV, so k1d is not registered.

## Next fallback (plan, not sealed): k1e, a small learned critic
Brain-first (Ben 16:05; textbook-level, the mapping is a guess): people learn which of their replies land from how
listeners respond. Value is learned from outcomes (reward prediction error in the basal ganglia and orbitofrontal
cortex), not read off by a fixed rule. The k1d result fits that picture: the 1B asked cold cannot tell, so the fit
has to be learned.
- Features: the 1B's own final hidden state after reading the listener prompt (k1d's chat) for each draft. The 1B is
  frozen; only a linear head is trained.
- Labels: blind judges' useful yes/no on the 1B's own drafts for a new readable practice set (about 240 chats,
  4 drafts each, same recipe as DEV). No test panel is used, and nothing is trained on judge or Claude text; the
  targets are yes/no labels on the 1B's drafts.
- Open question for Ben's rule "Claude-written text is not training text": the practice chats' user messages are
  Claude-written and are the critic's input (not a generation target). This is disclosed; Ben can veto it.
- DEV check before anything is sealed: the critic picks among DEV's 4 drafts; it goes forward only if it beats P on
  DEV (more than 15 of 40).
