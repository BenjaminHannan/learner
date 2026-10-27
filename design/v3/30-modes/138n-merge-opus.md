# Merge 138n: 138m plus the reading line (Opus build)

**Base:** 138m (`scripts/claude_loop138m_agent.py`, `artifacts/claude-merge138m-20260922/loop138m-config.json`, saved rows in `artifacts/claude-merge138m-20260922/run/`).

**Added:** 221, 221b, 221c, 229, 237 (the line piece only, not 237b), 232c (replaces 232b) and 236.

**Agent:** `scripts/claude_loop138n_agent.py`, config `artifacts/claude-merge138n-20260922/loop138n-config.json`.

**Evidence:** `artifacts/claude-merge138n-20260922/` (PASSMARKS.md, predicted_moves138n.json, SEAL.sha256.txt, run/, m7/, RESULTS.md).

**Honest note on order.** The brief asks for this interaction analysis before the build. I drafted the layer order first, built it, and wrote this note in full after the first pilot, because the first pilot found two cross-piece bugs (G1, G2 below) that the paper analysis had missed. Nothing in this note was chosen from blind-panel items. I did see some item text in piece RESULTS files before the director's note (see RESULTS.md, "Disclosure"); it was not used for the layer order or the M7 predictions.

## Layer order (outermost first)

### Ears

| # | Layer | Acts on | Why here |
|---|---|---|---|
| 1 | 221c `QNorm221cMixin` | turns ending "?" | Normalises the question once, so every reader below sees the plain form. It re-hears the rewrite only when that gives one table reading and no write. |
| 2 | G1 `FirstName138nMixin` → 236 `FirstName236Mixin` | questions with a lone first name | Resolves "Orrin" to the one stored full name before 221b/237 read it. G1 drops candidates that are really the first word of a 232c particle name ("Sela ben Tamsin"). |
| 3 | 221b `StoredRel221bMixin` | one-hop asks the table missed or abstained on | Same place as on 221b's own stack; it only asks, never writes. |
| 4 | 237 `TableAsk237Mixin` (221's reader, table v1.1) | table-shaped questions | The main question reader. Inverse answers are labelled "(worked out backwards)" and are never stored. |
| 5 | G2 `TableTeach138nMixin` → 229 `TableTeach229Mixin` (table v1) | statements the whole 138m ears stack left as "not understood" | Fires last, so any 138m gate that stops a write (209 screen, 222/215 refusals, 167b, 150 subject veto) has already returned its own clarify, and 229 never sees that turn. 229's own write goes back through all of those gates. |
| 6 | 138m ears (`Loop138lEars` …) with 232c's `Verb232Mixin` between Typo165 and ValueScreen167b | everything else | 232c sits exactly where it sits on its own stack. `install232c()` rebinds the 232 subject rule. |

### Loop

| # | Layer | Why |
|---|---|---|
| 1 | G3 `Cap138nMixin` | Capitalises a reply that starts "your " (237's USER template gives "your city is …"). It changes text only. |
| 2 | 138m's full loop order, unchanged (224c/224, 233, 226, 234, NameLine230c, Identity227c, 212, 216, 209 …) | Every 138m turn decision still runs around the ears as in 138m. |
| 3 | 232's `Loop232AgentLoop` parity step, directly above `Loop138iAgentLoop` | Where it sits on 232c's own stack. |

The MRO is asserted at import. The 228 source guard is installed at import and is first in the daemon.

## Order rules checked

- **A notebook-answering layer never overrides a write/ghost gate.** Every reading layer (221c, 236, 221b, 237) acts only on "?" turns and emits ask/clarify, never a write. 229 acts only on the not-understood clarify.
- **Questions never write.** Checked on M1 (0 write diffs on question turns), M2 and M6 (0 write changes). M7 counts it again.
- **224c's decline stays the fallback.** Nothing sits outside 224c on the loop. The reading layers only turn a miss into an answer or a more exact abstain.
- **Inferred facts are never stored.** Inverse answers are clarify text only, and 221b/236 only ask.

## Pairwise interactions (turns both claim, who wins, why)

| Pair | Shared turns | Winner | Why better |
|---|---|---|---|
| 221 / 237 | the same reader | 237 (v1.1 table) | 237 is 221 with a bigger alias table. Using v1.1 for questions only keeps 221's behaviour on v1 keys. |
| 237 / 221b | ambiguous wordings ("When was X founded?", "Who coaches X?") | 237 | 221b abstains on its own when two keys could fit. v1.1 maps the wording to the table's canonical key and answers a fact that was taught (221b A01, A02, A03, A05, A08; G06 doctor→physician; G09 native language). It never invents: the answer is a stored triple. |
| 221c / 237 | wrapped questions ("Could you tell me who X's boss is?") | 221c rewrites, 237 answers | As on 221c's own stack. |
| 221c / 237 v1.1 | "Who are X's bosses?" (d221c-057) | 237 | v1.1 reads "bosses" as boss and gives the single stored boss. 221c's gold was abstain. **Known cost:** it is a true stored fact, but a plural question gets a singular answer. |
| 236 / 232c | first name that starts a particle name ("Where does Sela ben Tamsin live?") | 232c (G1 skips it) | Without G1, 236 read "Sela" as a lone first name and answered "I don't know anyone called Sela ben Arom ben Tamsin." (pilot, d232c-102). |
| 236 / 232c save | "Orrin Vask lives in Brindle." then "Where does Orrin live?" (d236-04, d236-21) | both | 232c now saves the statement, which 236's own stack could not. 236 then resolves "Orrin" to it. This is better: a true taught fact is found. |
| 229 / 232c | a statement with a 232c multi-word subject that 229 still sees | 232c's subject rule decides the name, G2 decides the reason text | 229 said "Orrin ben Vask does not look like a name", which is false for a name 232c accepts. G2 keeps the no-save and gives the real reason (the value check, or "I could not store it that way"). This changes text only. |
| 229 / 232c | unsupported names ("do", 5-token names, conjunctions) | 229 nosave clarify (no write) | 232c's own stack gave its combined fallback. The 229 clarify is more specific and still does not write. |
| 229 / 221b / 237 | none | — | 229 acts on statements only. The readers act on questions only. |
| 221b / 236 | a first-name one-hop ask | 236 resolves first, 221b reads | 221b sees a full name. |

## Each piece vs 138m's layers

| 138m layer | Interaction | Result |
|---|---|---|
| 224c declines | Readers turn some Q2 declines into answers or exact abstains ("I don't know X's R."). | 224c stays the fallback for every turn the readers miss. rt143 verdicts: P1, P2, Q1, Q2 go MISSED→OK. The other moves are abstain→abstain wording. |
| 227c identity | Identity questions ("What is your name?", "Who made you?") never reach the readers. The identity layer answers first, as in 138m. | 221 S1/S2/S3, 221c d221c-058, 236 d236-22 get 138m's identity replies (base138m). |
| 230c name line | "Where do I live?" (USER) is now answered by 237's USER template instead of 138m's Q2. | M6 p3-dialogs d05 t03: "Your city is Harlow Cross." (G3 capital). |
| 233 / 234 fixed replies | Small talk (d221c-059) gets 234's reply. 233 rewrites politeness before any reader. | Same as 138m. |
| 212 / 216 gates | The readers are ears stages, so the gates route exactly as in 138m. | No change to what the gates block. |
| 209 write screen | 229 only fires on the not-understood clarify, so 209's split clarify wins. 229's writes pass 209 again. | No bypass. |
| 226 sources | Unchanged, and still outside the ears. | Same. |
| 222 teaches | 222 claims "X is the R of Y" statements first, as in 138m, so 229 sees them only when 222 misses. | 229's dev cases get 138m's records (26 base138m moves). Raw-key saves (grandma, coworker, co-worker, neighbor, manager) come from 222. The 229-055 "He" save is an inherited 138m defect. |

## Decisions

1. **229 keeps table v1, questions use v1.1.** 229 was built and sealed on v1. v1.1 is 237's reader change and was tested only for questions.
2. **237 over 221b on ambiguous keys.** See the table above.
3. **G1, G2, G3 are the only new behaviour.** Each is text- or routing-only glue, and each is listed in the config (`merge138n.glue`).

## Known costs (not fixed here)

1. **d229-055, inherited from 138m:** "He is the boss of Kip Dunmore." saves "Kip Dunmore's boss is He." 229 alone refused it, but 138m's 222 claims it first. 138n == 138m.
2. **Raw-key saves from 222** (grandma / coworker / neighbor …): 229 alone normalised these keys. Inherited from 138m.
3. **rt143 S5:** "Bram Kite's spouse is Cora Lind." A true taught fact, but the suite's gold is abstain (it is a 2-cycle loop test). 221's own RESULTS flagged the same case.
4. **d221c-057:** plural "bosses" is read as boss (see above).
5. **Abstain wording changes:** several 138m Q2 replies become "I don't know X's R." or "I don't know anyone called X." These are abstain→abstain. Two M1 turns flip from a non-answer fixed reply to an abstain (232c d232c-098 t1, 232cp p31 "Orrin ben Vask" t0). Both are predicted by id.
