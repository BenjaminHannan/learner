# lis-318 chat training rows: writer brief

You write TRAINING rows for a small fact-reader model (a fine-tuned 1B model inside a chat assistant). The reader reads ONE user chat turn plus the assistant's previous reply, and outputs a JSON "frame". Today it was trained mostly on short tidy sentences and misreads casual chat. Your rows teach it casual chat.

Read first (all in /home/user/learner): design/v3/60-listener/frame-spec.md (the format, follow it exactly), design/v3/60-listener/frame-spec-notes-301.md (conventions, follow them exactly), design/v3/60-listener/relation-names.txt (the ONLY allowed rel names, plus "other"), and 30 rows of artifacts/claude-lis301-20260923/data/opus_w4.jsonl to see the row format.

Never read: anything under /mnt/project-files/escrow-331, any folder with "panel" in its name, any LoCoMo or LongMemEval data. Write everything from scratch (no copying from any dataset).

## Row format (one JSON object per line)
{"id": "c{W}-d{DDD}-t{T}", "prev_reply": str, "turn": str, "frame": {"act": ..., "facts": [...], "ask": ...}, "family": str}
- Rows come in short dialogs of 4 to 8 turns (same people across a dialog), so the chat feels real. d = dialog number, t = turn number.
- prev_reply = what the assistant said right before this turn. Use this assistant's real style: "" for a first turn, "Saved: your sister is Mira.", "Saved: Kofi's city is Leeds. Saved: your dog is Pip.", "Okay.", "Got it.", "Nice!", "I don't know that yet.", "Whose dog is Pip, yours or someone else's?", "I think you told me your boss is Tal, is that right?", "What's your brother's name?". Keep it consistent with the dialog.
- The reader only sees prev_reply and the turn, NOT earlier user turns. So a pronoun that points back to someone named only in an EARLIER user turn (not in this turn, not in prev_reply) cannot be resolved: per the spec notes, keep the pronoun as owner with mode UNCLEAR.

## Families (exact counts for your 500 rows)
- teach_multi 120: 2 to 4 facts in one casual turn, with asides and parentheses ("my sister Tove (the one in oslo) just got engaged to her bf Emil!!"), apposition ("my boss Kiri"), lists ("kids are Ada and Bo, 7 and 4"), in-turn pronouns ("my dad Rolf lives in hull, he's 70").
- teach_passing 60: a fact dropped in passing inside a story, complaint or joke ("ugh my landlord Dov raised the rent AGAIN").
- pets 40: pets named with a species word ("my beagle Ziggy", "zadie's hamster Sprout", "our cat" -> we). Use the table's pet relations (dog, cat, rabbit, hamster, parrot, horse, pet); a breed or species with no table relation is (Pet, other, word) per note 2.
- correct 40: casual corrections ("wait no, ama moved to leeds not york lol", "i said wynn's a paramedic, nah she's a firefighter"): the NEW value gets mode CORRECT with "old" when named; the old value is never an ASSERT fact.
- ask 80: chatty questions with filler and reasons ("the vet asked how old ziggy is and my brain is soup, what did i tell you"), yes/no checks, inverse ("whose cat is Tofu again?"), two-hop via. act ASK, facts [] unless the turn also states a fact.
- smalltalk 50: casual chat that NAMES people, pets or places but teaches nothing new ("uriah's here!! he ate all my snacks", "back at it. monday energy on a thursday"): act CHAT, facts []. These teach the reader NOT to invent facts.
- nosave 60: negation, plan/hope, hypothetical/pretend, reported ("apparently", "X says"), sarcasm, "so X is Y" checks without "?", and our/we ownership (owner "we"), each labelled with the spec's modes.
- short_answer 20: the turn answers prev_reply's question ("What's your brother's name?" -> "oh it's Tomas").
- pronoun 30: pronouns resolvable from this turn or prev_reply (resolve them), and pronouns pointing to earlier turns (UNCLEAR).
Write "family" as one of those names.

## Style
Real people texting: mostly lowercase, run-ons, "lol", "tbh", "rn", "bc", "w/", occasional typos in ordinary words (names and values are copied exactly as typed in the frame, including case), 4 to 45 words, rare emoji. Vary topics: family, work, school, pets, neighbours, hobbies, trips, health, moving house, food.
Values must be copied exactly as typed. If the user says "i drive a tram", "tram driver" is NOT typed, so there is no occupation fact (the frame spec keeps values as typed); only list facts whose value appears word for word.

## Names
All names invented and fictional (people, pets, towns, companies, schools); never a real public figure. Real countries and big cities are fine. Your name pool: {POOL}. Do not use any name in /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/dev_names.txt.

## Output
Write /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/lis318data/chat_w{W}.jsonl (append in chunks of ~50 rows so nothing is lost). Then check with a short Python script: 500 rows, unique ids, every line parses, family counts exact, every rel is in relation-names.txt or "other", every ASSERT/CORRECT value appears in the turn (or in prev_reply for short_answer), every non-"me"/"we" ASSERT owner appears in the turn or prev_reply, acts and modes are spec values. Fix any failures.
Never call WebFetch or any mcp__hearthbot__ tool. Do not run git. Final reply: counts only (rows per family, check results, file size).
