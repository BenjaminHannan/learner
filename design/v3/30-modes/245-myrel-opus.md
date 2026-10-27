# 245: "my <relation>" as a question subject (Opus build)

**Problem.** In the 30-conversation panel (exp 239), 14 replies treated a possessive
phrase as a person's name: "What's my uncle's job?" -> "I don't know anyone called my
uncle." This happened even when the uncle and his job were stored. Verb forms like "Where does my
sister live?" got the long glued decline.

**Why it happens (reproduced on base 228).**
- "What's my sister's city?": Me166 (the first-person reader) sits outside Qform158, so it
  never sees the expanded "what is". Inside, FakeEars reads the possessive with the name
  "my sister": ask(name="my sister", relations=[city]). The notebook has nobody called "my
  sister", so the reply is "I don't know anyone called my sister."
- "Where does my sister live?": Verb167 needs a single capitalised name, so "my sister" is
  refused. No reader claims the turn, and the glued decline follows.
- Forms that already work: "What/Who/Where is my R('s S)?" (Me166). They are left untouched.

**The one change** (scripts/claude_fix245_myrel.py, `MyRel245Mixin`, outermost on the 138i ears;
scripts/claude_loop245_agent.py builds it the same way 248 does):
1. It runs only on turns that end in "?" and contain "my <word>". The base ears hear the turn first. If the
   base already makes an ask whose name is not the garbled "my ...", the base actions are returned
   unchanged. Everything that already works stays byte-identical.
2. <word> must be a relation stored for USER, matched exactly as stored or through the existing
   Me166 teach mapping (mom -> mother). No new synonym list.
3. "my <word>" is replaced by each stored person X, and the unchanged base ears hear the new text. If that
   is not an ask about X, a one-word stand-in name is tried instead. That lets the
   base's own verb and possessive readers parse two-word or lowercase X, and the ask is then aimed at X.
   Only on this path, a leading "hi/hello/hey (there)/please/ok" and a trailing ", please"
   are dropped first, because the base reads no greeting on any question.
4. The notebook is asked read-only for each X. Every X that has an answer gets the base's own
   ask action, so the base answers and renders it ("Tavi's city is Brellmoor.").
   **2+ stored X: one short answer per person, each naming its person.** If no X has an
   answer, the reply is "I don't know your <relation>'s <asked> yet." (Me166's wording, which never
   names X). If no such relative is stored: "I don't know who your <relation> is."
5. When no ask structure is found, the base handling is kept, except that the garbled
   "anyone called my <word>" decline becomes "I don't know who your <word> is." (no such relative
   stored) or "I don't know that about your <word>." (relative stored).

It never writes: it returns only ask and clarify actions.

**Known limits (not fixed here).** "Who is my R married to?" still declines when R has 2+
facts, because that is cause A (compose_n_hop) and the base fails the same way with R's name.
Embedded forms ("Can you tell me where my sister lives?") and "What does my R do?" have no
base reader even with the name. Me166 forms with 2+ X keep the base's "Which one do you
mean?".

Dev pilot: fix 34/34, keep 10/10, trap 9/9, 0 writes. Suites: GATE clean, 0 moves. Sleep
smoke: 138i marks. Dev timing: median added time -0.07 ms.
