# uw-2 data gate: judge brief (fixed 2026-09-27 10:15 UTC, before any gate packet exists)

The builder sends this text verbatim, with only IN and OUT filled in.

---

Never use WebFetch or any web access.

You are checking practice data for a note-keeping assistant. Read only the file IN. Write only the file OUT. Do not open
any other file or folder, and do not run anything except reading IN and writing OUT.

IN is JSON Lines. Each line is one packet:
- "notes": the assistant's saved notes before the new message, numbered from 1. Each note is "number. owner | relation |
  value". The owner is the user (shown as "me (the user)") or a person or pet the user mentioned.
- "earlier_user_turns": what the user said earlier in the same chat, oldest first.
- "new_message": the user's newest message.

For each packet, answer one question: does the new message change one of the numbered notes to a new value?
- A change means the user says the saved value is wrong, or no longer true, and gives the value that replaces it.
- Use the earlier turns to work out who "she", "he", "they", "my sister", "the dog" and so on refer to.
- If the message changes a note, answer that note's number and the new value, copied as it is typed in the message.
- If the message changes no note, answer note 0 and new_value "". That covers:
  - new facts;
  - plans and what-ifs;
  - questions and doubts;
  - repeating the same value;
  - someone else's claims;
  - a past value described as past;
  - saying a value is wrong without giving the new one;
  - a message where you cannot tell which note it means.

Write one JSON object per packet to OUT, one per line, in the packets' order:
{"id": "<packet id>", "note": <number, or 0>, "new_value": "<value as typed, or empty>"}

Answer every packet. Do not explain. When you finish, reply with only the number of lines you wrote.
