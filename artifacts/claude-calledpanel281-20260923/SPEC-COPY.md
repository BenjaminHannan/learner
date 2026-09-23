# SPEC-COPY for calledpanel281 (exp 281)

Source: `design/v3/30-modes/280-282-chat-fixes.md` from `origin/main`, section "## 281" copied verbatim below. No other file was opened.

---

## 281: "What is Ana's cat called?" is read as "What is Ana's cat?"

Problem: t04-t5 and t12-t4: "What is X's R called/named?" gives "I don't know X's R called." while X/R/V is
stored. It is systematic.
The one change: on question turns only, a trailing "called" / "named" after a possessive relation phrase
("X's R called?", "X's R named?", "what do you call X's R?", "what's the name of X's R?") is read as asking for
X's R. Teach turns and writes are untouched.
Marks: M1 calledpanel281: at least 90% of stored-answer items answered exactly (260 arm shown); 0 wrong answers;
not-stored items still abstain (0 new guesses); 0 writes on question items. M2 frozen suites as in 280. M3 0 notebook
changes except on the panel's teach turns, identical to 260's.
Report-only: "I don't know X's R called." style broken abstains that remain.

Panel spec (calledpanel281, 60 turns): 25 stored-answer questions in called/named/name-of wording (varied
relations: pets, boats, bands, streets, teachers), 10 same questions where the fact was never taught, 10 where
"called" belongs to the value or name itself ("Who is Ana's friend called Bo?" style, ambiguous on purpose),
15 controls (plain possessive questions and teaches). Fictional names only.
