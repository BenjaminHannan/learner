# Checking practice questions

Each line of batch.jsonl is one practice item made from a chat. A user wrote the messages to an assistant.
You get:
- "earlier_messages": what the user wrote earlier in the chat, in order;
- "last_message": the user's latest message;
- "fact": one fact about the user's life: "about" is who it is about ("me" means the user), "relation" is what it
  is (for example "dog" means the name of that person's dog), "value" is the answer.

Answer two questions for each item, from the text only:
- "asks": does the last message ask the assistant for this fact (the value for that person and relation)? "yes" or
  "no". It still counts if it is casual, misspelled or indirect ("remind me what mira's dog is called"). It is "no"
  if the message asks for something else, asks nothing, or states the fact instead of asking.
- "stated": do the earlier messages say that this value is the answer, and is it still the answer by the end of them
  (not replaced by a later correction)? "yes" or "no".

Judge only from the item itself. Do not look at any other file or folder, and do not discuss items with anyone.
Write labels/batch.jsonl in this folder: one JSON line per item, {"item": "<id>", "asks": "yes" or "no",
"stated": "yes" or "no"}, every item exactly once.
