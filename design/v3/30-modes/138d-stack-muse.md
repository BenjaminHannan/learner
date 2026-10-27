# 138d — stacking the verified late fixes onto loop138b (design)

One new file (`scripts/fable_loop138d_agent.py`) subclasses the frozen
loop138b agent. Loop138b's L2 (`turn()`, the 127 router + Self99 live
answers + decline rule) is REPLACED by the sealed 138c serving rule (piece
2 owns the self layer by director order). Everything else is a port of a
verified mixin, reused read-only, composed in one place so the vetoes
agree with each other.

## Where each piece hooks into loop138b (file:line in fable_loop138b_agent.py)

- Loop138bEars.hear (:126) — the whole teach/question stack runs inside
  `super().hear()` of the 138d ears. The 135 patch window, 140 clean,
  139b value veto, 150 subject veto, 137/144 upgrades and the 132 rewrite
  all run UNCHANGED, innermost.
- Loop138bAgentLoop._act (:270) + _ask138b (:257) — the 138d loop `_act`
  chain runs Doubt146b record/clear, then the 150b clause guard, then
  `super()._act()` (the 138b guards). Tagged asks still take `_ask138b`.
- turn() — inherited verbatim from loop138 in 138b; in 138d it carries
  the 138c rule (base = L134 turn on self, i.e. the full 138d loop path;
  self answer only on non-DECLINE + grounded, else base verbatim).
- build_agent138b (:318) — mirrored by build_agent138d with the 138d
  ears/loop/reasoner classes, the IndexedLoopNotebook lower layer, the
  142 teach/chain patches, the doubt store, and the sleep145 retrofit.
- Loop138bDaemon (:364) — subclassed as Loop138dDaemon (settle gate +
  exactly-once `process_file` inherited); only the build call changes.
- Reasoner (ScreenStatusReasoner148b in 138b's build) — replaced by
  Reasoner138d (148b tag logic over FastReasoner142 + one 159 fallback).

## Same-shape pairs, chosen order, why

Outer → inner at ears: Qform158 > Filler157 > Smalltalk156b > Doubt146b >
Subject150B > Inverted155 > Reverse153 > Loop138bEars. All are super-first
cooperative, so the inner 138b core decides first and each outer layer
only rewrites its own sealed leftover shape:

1. "?" asks — 148b screen (inner, tags neg/time) vs 132 rewriter (inner,
   clarify→ask) vs Reverse153 (miss + Whose/Who-is-X-of/Which-has frame →
   answer) vs YesNo154 (loop level, miss + Is-shape → wh-run) vs Qform158
   (outer probe: what's/tell-me/??? candidate used only if inner parses
   it as ask) vs Hop159 (reasoner fallback on untagged non-OK). Frames are
   disjoint by construction (reverse never starts with Is; yesno only
   Is; qform only changes what's/tell-me/??? surfaces), and each fires on
   a strictly narrower leftover, so at most one answers per turn.
2. Teaches — 138b guards inner; Inverted155 converts leftover clarifies
   to teaches (x135: officeholder frames return base — the 135 guard runs
   in the core beneath it); Subject150B outer re-guards everything
   including 155's products; Doubt146b outermost sees the final
   clarify/teach for first-person record vs hearsay-exempt vs clear.
3. Fallthrough clarify — Smalltalk156b converts only the exact generic
   fallthrough for whole-message small talk; Filler157 (outer) sees the
   class reply as non-complete, tries one strip, keeps base unless the
   remainder parses complete. A filler-stripped remainder re-enters
   INNER layers only (sealed 157 one-strip, no upward reentry), so
   "btw, what's X's R?" keeps the clarify — known edge, listed.
4. Subjects — 150 (inner) and 150b (outer) both screen; 150b is monotone
   stricter (relation cues + lowercase verbs, single tokens exempt), so no
   150-accepted teach is newly refused except clause-swallow shapes.
5. Refusals → doubts — 139b/150/150b act-level refusals with known
   subject + relation record first-person doubts (the 146d rule on the
   wider 138b refusal surface); hearsay-shaped turns never record.
6. Yes/no vs self — yes/no Yes/No/only-know replies are clarify-kind
   WITHOUT the miss bit and honest abstains are answer-kind, so
   `notebook_missed` is False and the self path never hijacks a yes/no
   turn; only true misses reach the router.
7. Tagged asks vs doubt — Doubt146bMixin.hear runs verbatim (doubt wins
   an overlap); overlap needs a doubted hop inside a neg/time question,
   absent from every sealed suite; predicted zero moves.
8. Sleep145Reasoner wraps Reasoner138d (taught-first for word episodes
   only); the 159 fallback sits underneath and only converts untagged
   non-OK records, so word asks are untouched.

## What was left OUT, and why

FastQuestionMixin142 (the 142 "?" reroute) is OUT. It answers "?" turns
without ever calling the inner ears, which would bypass 138b's sealed
148b neg/time screen AND the 132 rewriter for every question (both live
inside Loop138bEars.hear on the "?" path; the rewriter alone repairs
57+54 bench items on 138b). Porting it changes two other pieces'
behaviour — an honest OUT beats a silent conflict. IN from 142 is the
allowed lower-layer swap: IndexedLoopNotebook + FastReasoner142 +
patch_chain142 + patch_loop121_teach + _patch_relation (all verified
reply-identical on their own base), plus the 142 empty-subject guard.

## Known edges (inherited, not introduced)

137 discourse-led subjects, the 150 "I Believe" hedge, officeholder
rewriter guesses + H5, 138c S1-by-design, 154's 3 honest-reply moves,
155's author_of readings, 159's loose-match abstains — all behave as on
their own bases; every move vs 138b rows is itemised in RESULTS.md.
