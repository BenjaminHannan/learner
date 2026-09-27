# Checking practice chats

Each line of batch.jsonl is one chat. A user wrote the messages to an assistant.
You get:
- "earlier_messages": what the user wrote earlier in the chat, in order;
- "last_message": the user's latest message;
- "person": a name, and "role": a relation to the user (for example "landlord" or "best friend").

Answer one question for each item, from the text only:
- "stated": do the earlier messages say that this person is the user's <role> (in any words, now or at some point)?
  "yes" or "no". It is "yes" if a reader of the earlier messages could tell that this person is the user's <role>.
  It is "no" if the person is mentioned but the messages never say they are the user's <role>.

Judge only from the item itself. Do not look at any other file or folder, and do not discuss items with anyone.
Write labels/batch.jsonl in this folder: one JSON line per item, {"item": "<id>", "stated": "yes" or "no"}, every
item exactly once.
