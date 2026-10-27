# Independent check of exp 232c (multi-word names): findings

**Verdict: CONFIRMED, with one inherited safety concern.** No wrong or junk writes and no question writes. One-word replies are unchanged. Every trap wrote nothing. One reply gave a value the user had denied. That comes from a retraction gap the whole stack already has (one-word names fail the same way on both arms), but 232c now exposes it for multi-word names.

**Setup:**
- 20 fresh dialogs (`dialogs.py`, 118 turns, 71 questions) and 8 follow-up control dialogs (`controls.py`). All names are fictional.
- Each dialog ran on both arms, each in a fresh work dir:
  - the base: `scripts/claude_loop228_agent.py` with `artifacts/claude-determinism228-20260922/loop228-config.json`;
  - 232c: `scripts/claude_loop232c_agent.py` with `artifacts/claude-fullname232-20260922/loop232-config.json`, which is the config PASSMARKS names.
- The runner is a per-turn version of `dialog_nb.py`. After every turn it records the reply and all stored facts, both active and superseded.
- The 1-minute load was 15–22 at the start. Total run time was under 1 minute.
- I opened no panel folder and not `dev232c.jsonl`.

**Files:**
- `rows_base228.json` and `rows_232c.json`: every turn, the reply, and the stored triples after that turn;
- `rows_controls_*.json`: the same for the control dialogs;
- `score.py` → `counts.json`.

## Counts (20 dialogs, 71 questions)

| Count | base 228 | 232c |
|---|---|---|
| questions right | 33 | 64 |
| replies with a wrong value | 0 | 1 |
| wrong or junk writes | 0 | 0 |
| writes on question turns | 0 | 0 |
| right on base, lost on 232c | – | 1 (v13 t2) |
| one-word replies changed (14 turns) | – | 0 |

## Every 232c failure (verbatim) and its cause

1. **v13 t2.** The dialog was "Ines da Varrow works at Brindlecorp." → "That's not true, Ines da Varrow doesn't work at Brindlecorp." → "Where does Ines da Varrow work?" 232c replied **"Ines da Varrow's employer is Brindlecorp."**
   - Cause: the retraction turn is not understood. It gets the generic decline and the fact stays active.
   - This is a limit of the whole stack. Controls c00–c04 show that the one-word version ("Ines …") and the phrasings "Ines doesn't work at Brindlecorp." and "That's wrong." fail identically on 228 and 232c.
   - The base "got it right" only because it never saved the multi-word fact in the first place.
2. **v02 t3.** "Which language does Tariq bin Qasrel speak?" got the generic decline. Cause: the stack does not handle the "Which language" wording. Control c05 shows that "Which language does Tessa speak?" fails on both arms.
3. **v07 t5.** "In which city was Emil von Tarrow born?" got the generic decline. Cause: the same wording gap; the one-word version fails on both arms (c05).
4. **v07 t6.** "What does Emil von Tarrow speak?" got the generic decline. Cause: the same wording gap; the one-word version fails on both arms (c05).
5. **v04 t5.** "What language does Pierre d'Arvenne speak?" got the generic decline. The teach turn "Pierre d'Arvenne speaks Norric." was not saved either.
   - Cause: this gap belongs to 232c. A lowercase `d'X` is not accepted as a name word. A capital `D'X` works (control c06: saved and answered).
   - It fails safe, with no write.
6. **v17 t2.** "Where does Joao do Riomar live?" got the decline, and the teach was not saved. Cause: "do" names are a limit declared in PASSMARKS (the 150b guard).
7. **v17 t3.** "What language does Ana do Carvel speak?" Same cause as item 6.

## What held up

- **Particles:** van der, de la, bin, ibn, al, ap, O', Mac (as a split word), MacX, D' and von all taught and answered correctly.
- **Name shapes:** hyphenated first and last names, 3-word names and 4-word names worked.
- **Verbs:** all five verbs saved. Where/who/what wordings answered.
- **Similar names:** people sharing a particle and surname (Liesl / Maarten van Dorrick) or a first name and particle (Omar bin Rashel / Omar bin Kaddel) were kept apart. An untaught sibling (Joost van Dorrick, Omar bin Sallow) was declined.
- **One-word and multi-word together:** "Tessa" and "Tessa de la Morrow" in the same notebook kept separate values.
- **Correction:** "No, Oskar van Heerlend lives in Quellport." superseded the old value correctly.
- **Forget:** "Forget Rafael de Sollan's language." worked and kept the city.
- **Traps: 0 writes on all of them.**
  - Compound subjects with and / with / or. This includes "Sven al Harrow and Liv al Harrow speak Norric.", where a later separate teach about Liv did not pick up the language.
  - 5- and 6-word names.
  - "do" names.
  - Untaught verbs for a stored name: all 4 declined as "I don't know X's employer/language/…".
  - A partial name ("Oskar Brelling", "Lucia Farrow") was declined rather than matched.

## Concerns for merging

- **Retraction and negation are not handled anywhere in the stack.** Widening what can be saved (multi-word names) widens where a denied fact is still asserted. This is not a regression by 232c's own rules: the one-word behaviour is identical. It is worth a follow-up task.
- **Lowercase "d'" is a coverage gap** in the particle list/name-token rule, even though PASSMARKS says D'X is covered. It fails safe.
- **A base quirk, not 232c's:** "Marta de la Pell with Joris lives in Osterby." and "Juan Carlos de la Mondreva lives in Osterby." get "You never told me why. I only store what you state, not reasons." on both arms. On 228, "Rafael de Sollan lives in Osterby." gets the same reply. It writes nothing, but the reply is nonsense.
- **Common question wordings fail on both arms:** "Which language…", "In which city was X born?" and "What does X speak?".
