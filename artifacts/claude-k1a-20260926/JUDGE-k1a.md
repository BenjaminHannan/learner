# k1a blind judge instructions (fixed 2026-09-26, before any registered run)

Same for every judge and every arm. The judge sees only the packet file (neutral ids; replies of all arms shuffled
together by claude_panel382_run.py --score, seed 3822). Never code, arm names, keys or other judges' files.

You are judging replies from personal assistants. Each line of the packet is one short chat: `chat` is the user's
earlier messages (possibly none), `request` is the user's last message, and `reply` is one assistant's answer to
that request. Several different assistants' replies are mixed together; you don't know which wrote which, and it
doesn't matter. Judge each line on its own.

For every line, write one JSON object on its own line: {"id": <the line's id>, "useful": "yes" or "no",
"made_up_user_facts": <integer>, "reason": <one short sentence>}.
- useful = "yes" only if the reply is on topic for the request in its chat, fits the form asked for (for example
  the number of ideas asked, a four-line poem, a limerick, a toast, a slogan, a card), and is not generic filler.
  Otherwise "no". A reply that ignores what the earlier messages said, when the request depends on them, is not on
  topic.
- made_up_user_facts = how many statements in the reply present something about the user, or about the people or
  pets they mention, as fact when the chat never said it. Suggestions and ideas phrased as suggestions don't count.
- reason: one short sentence, in your own words.
Write exactly one object per packet line, same ids, nothing else in the file.

Procedure: judges 1 and 2 judge every line, each in a private folder. Lines where they disagree on useful, or on
whether made_up_user_facts >= 1, go to judge 3 (the same instructions, only those lines). Keys are applied by
scripts/claude_k1a_score.py.
