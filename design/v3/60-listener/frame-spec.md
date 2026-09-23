# Listener frame spec v1 (lis- line, exps 300-319, 2026-09-23)

This is the target format for the listener. The listener is Qwen3.5-0.8B, fine-tuned (Ben's 10:55 UTC decision). It reads one chat turn, plus the assistant's previous reply, and writes **one JSON object**. It proposes; plain code (the write compiler, `scripts/claude_lis300_compiler.py`) decides what gets saved. Key-writing rules in `design/v3/30-modes/key-writing-rules.md` apply in full.

## Output

```json
{"act": "STATE", "facts": [{"owner": "Mira", "rel": "dog", "value": "Pip", "mode": "ASSERT"}], "ask": null}
```

- `act` (whole turn): one of `STATE`, `CORRECT`, `ASK`, `CHECK`, `NEGATE`, `SUPPOSE`, `PLAN`, `CHAT`, `UNCLEAR`.
  - A turn that both states and asks gets the act of its first clause. Each fact still carries its own mode.
- `facts`: every fact the turn mentions, including facts that must not be saved (for those, the mode says why). Order them as they appear in the turn. The list is `[]` when there is none.
  - `owner`:
    - `"me"` for I / me / my / mine.
    - `"we"` for we / us / our / ours. Never map "our" to "me"; the compiler asks whose.
    - Otherwise, the owner's name **exactly as typed**, with the same case and any typo.
    - A pronoun ("he", "she", "they") is resolved to the name it refers to, but only when that is clear from this turn or the previous reply. If it isn't clear, use mode `UNCLEAR`.
  - `rel`: a name from `design/v3/60-listener/relation-names.txt` (153 names), or `"other"`. Pick the most specific name the words support ("dog", not "pet", when the turn says dog).
  - `value`: exactly as typed. Keep the case and any typos; never fix spelling.
  - `mode`, one per fact:
    - `ASSERT`: the speaker tells it as true.
    - `CORRECT`: it replaces an earlier value. Add `"old": "<old value as typed>"` when the turn names it.
    - `NEGATED`: "doesn't have", "isn't", "no longer".
    - `CHECK`: the speaker is checking it. This covers "so X is Y" without "?", "X is Y right", and "X is Y, yeah".
    - `SUPPOSE`: pretend, suppose, imagine, "let's say", "what if".
    - `PLAN`: wants, plans, will, hopes, might.
    - `REPORTED`: someone else claims it ("Tal says...", "I heard...").
    - `QUESTION`: part of a question.
    - `UNCLEAR`: the owner or value can't be pinned down.
- `ask`: `null` unless the turn asks a question. For a question, `{"owner": ..., "rel": ..., "inverse": false}`.
  - `inverse: true` means the question asks for the owner. For example, "Whose dog is Pip?" is `{"owner": "Pip", "rel": "dog", "inverse": true}`.
  - For a yes/no question ("Is Mira's dog Pip?"), add `"value": "Pip"`.

- Two-hop questions ("who is my sister's husband") use `"via"` for the first hop: `{"owner": "me", "via": "sister", "rel": "husband", "inverse": false}`.
- Negations that name no value ("Kofi has no kids") have `facts: []` and act `NEGATE`. A reported fact ("Dev says his boss is Mara") has act `STATE`, and its fact has mode `REPORTED`.

## One fact per value

"My sisters are Mira and Tal" gives two facts: (me, sister, Mira) and (me, sister, Tal).
"My boss, Tal, has a cat named Fig" gives (me, boss, Tal) and (Tal, cat, Fig).

## What the compiler writes (for reference; the listener never decides this)

A turn's facts are written all together or not at all. A fact is written only if **all** of these hold:
1. Its mode is `ASSERT` or `CORRECT`.
2. Its owner is `me`, or a whole-word span of the turn or the previous reply. `we` is never written: the system asks whose.
3. Its value is a whole-word span of the turn.
4. Its relation is in the table.
5. The reader's confidence clears the threshold set on dev. Below it, the system asks back.

Anything else writes nothing: `NEGATED`, `CHECK`, `SUPPOSE`, `PLAN`, `REPORTED`, `QUESTION` and `UNCLEAR` never write.
