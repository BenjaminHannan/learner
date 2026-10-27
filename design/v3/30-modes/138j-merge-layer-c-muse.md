# 138j — merge layer C onto loop138i (Muse)

Base: loop138i (layer B part 2: 154e/172b/171b/173b/167e/167d/154d/174/170
on 138h; no 155 — checked in its MRO). This experiment ports the 10
remaining director-verified pieces as mixins only, following 138i's merge
method. Loop155 stays OUT (asserted in every M1 run: no 155 class in the
ears MRO, no `fable_loop155` module imported).

## Port plan (written before building)

Each piece's mixin, file:line, the base it was built on, and its slot in
the 138j collision order (outside-in). All rule bodies imported read-only;
behaviour deltas vs the piece-own agent live in `scripts/`
`fable_loop138j_agent.py` only, as new wrappers (the 138i pattern).

| # | Piece | Mixin (file:line) | Built on | 138j slot |
|---|-------|-------------------|----------|-----------|
| 1 | 180b silent case-insensitive known-name match | `Case180bMixin` (`scripts/fable_loop180b_agent.py:223`; helpers `notebook_names180b` :128, `resolve180b` :185, `is_say180b` :215) + loop display pass (`Loop180bAgentLoop._listening_tick` :253) | 138h | OUTERMOST ears; display pass outermost tick |
| 2 | 193 missing-apostrophe possessives | `Apos193Mixin` (`scripts/fable_fix193_apos.py:210`; `rewrite_apos193` :154) | 138h | ears #2 (inside 180b) |
| 3 | 164b "Tell me about Kim." | `About164bMixin` (`scripts/fable_loop164b_agent.py:154`; `_match164b` :101, `_render_user164b` :127) + tick safety net (:221) | 138h | ears #3 (inside 193); tick inside 180b display |
| 4 | 189 + 189b repeat requests | turn-level (`scripts/fable_loop189_agent.py:100`; widened `is_repeat189b` `scripts/fable_loop189b_agent.py:137`, `NO_PREV189B` :100) | 138g / 189 | OUTERMOST turn check (189b grammar is a strict superset: one check covers both) |
| 5 | 190 + 190b reverse questions | `Reverse190Mixin` (`scripts/fable_fix190_reverse.py:207`) + `Reverse190bMixin` (`scripts/fable_loop190b_agent.py:61`) | 138g / 190 | ears #4/#5 (190b outside 190; both super-first, fire only on all-clarify) |
| 6 | 187b self questions | turn-level gate (`scripts/fable_loop187_agent.py:186`; `classify_self187` :135, `self187_answer` :165, fixed replies :95-103, cando via `fable_fix168_ground`) | 138g (via 187) | inside the repeat check, on the notebook-missed path before route127 (exactly where loop187 puts it) |
| 7 | 192 corrections | `CorrectReply192Mixin` (`scripts/fable_fix192_correctreply.py:176`; tick :189, `_apply_correctreply192` :198) | 167e | loop tick (inside 164b tick, outside the 138i chain). Reply-only |
| 8 | 154f plain negation | ears prescan + `_act` (`scripts/fable_loop154f_agent.py:51` + :82; `parse_negate154f` in `scripts/fable_fix154f_negate.py:49`) | 154e | ears #6 (inside reverse); `_act` outside the 138i multi |
| 9 | 154g No/Actually/Correction | ears divert + `_act` (`scripts/fable_loop154g_agent.py:60` + :203; `parse_bare_correction154g` in `scripts/fable_fix154g_nocorrect.py:58`, `replace_question154g` :97) | 154e | ears #7 (inside 154f, outside 138i chain); `_act` outside the 138i multi |
| 10 | 188 statement fallback | turn-level swap (`scripts/fable_loop188_agent.py:126`; `QUESTION_FALLBACK188` :75, `STATEMENT_FALLBACK188` :85, `is_statement_shaped188` :110) | 138g | applied LAST to the final reply (byte-equality gate: fires only when nothing else parsed) |

Collision order (outside-in). Turn: repeat-189b check > 138g-body turn
with the 187 gate on the notebook-missed path > 188 swap applied to the
final reply. Ears: 180b > 193 > About164b > Reverse190b > Reverse190 >
Negate154f > Replace154g > Loop138iEars. Loop `_act`: Replace154g +
Negate154f outside the 138i chain (distinct act names; no overlap with
Multival154e). Tick (outside-in): 180b display > 164b safety >
CorrectReply192 > 138i chain (154d peek inside).

## Why this order

Every sealed relative order is preserved (190b>190; 189b>189 by grammar
superset in a single check; 154f/154g prescans outside the 154e-owned
chain they extend). 180b and 193 normalise the input first (ears-only,
silent rewrites that re-enter every inner stage via `super().hear()`),
so G3a ("what is odas boss's city?") composes: 180b restores "Oda",
193 restores "Oda's", the base two-hop answers. Every specific handler
(about, reverse, negate, replace, self, repeat) claims before 188's
generic fallback, which is a byte-equality check on the final reply and
so fires only when the whole stack declined. 187's gate sits exactly
where loop187 put it (notebook-missed path before route127), replicated
onto the 138i turn body together with 138h's raw-USER backstop.

## Director decision (one wording for every replacement)

192 answers "Updated: Kim's boss is Lee (it was Sam)." In 138j EVERY
replacement uses 192's template — including 154g's one-value replace
("Updated: Omar's language is Farsi (it was Urdu).") and the
confirmation after the user names one value from the 2+-value question.
Mechanics (teach + retract, ask flow, stored facts) are 154g-own
byte-identical; only the reply line moves (Saved -> Updated), so every
moved 154g/192 reply is listed by id in PASSMARKS as a predicted
reply-only class. 154g's 2+-value question ("Which one should Farsi
replace: Urdu or Hindi?") stays as sealed.

## Compositions expected (predicted pre-seal, piloted)

180b x 193 x base two-hop (G3a). 154g x 192-template (G3c; 192's own
tick never fires on 154g replaces: multi keys set no `supersedes`, and
the Updated line matches no Saved guard). 154f x 154e multi (G3d:
retracts Hindi only). 164b x 167d verbs (G3e: employer listed) and
164b x 173b (G3h: "about me" reads USER facts). 189b echo of any prior
reply incl. 188-swapped text (G3f). 190/190b whose-wording on city
(G3g). 187b identity vs 188 fallback split (G3i). Older-base rows
(192 on 167e: "My city…", verbs, of-chains now understood) move by id.

## Run order used

M1 pieces -> M2 (138i M1/M2/G3) -> G3/G4 -> rt/sessions -> bench-v3
both arms -> marks123. One suite at a time, Mac CPU,
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, temp state dirs, daemon
`idle_seconds=3600`. Ledger P138j.* appended before the runs; seal
before any registered run; seal re-verified OK after.

## Limits

Bench edits need a confirming "yes" under v3 (172b precedent). Nothing
here tests learned-word sleep episodes; the sleeper stays armed-idle
per 138i.

What it means: layer C is fully merged — one loop carries all ten
behaviours with every interaction named and verified.
What it does not mean: the Updated template never invents an old
value; unconfirmed re-teaches still score stale by design.
