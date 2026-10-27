# mu-405 claims judge (fixed before the run; every claims judge gets exactly this text plus one packet file)

This is mu-402's claims-judge text with one change: each transcript also shows what the user told the assistant in
an earlier conversation, and those messages count as things the user said.

You are a careful, blind judge. You get a file of chat transcripts between a user and a personal assistant. Each line
is one transcript: `pid`, `earlier_user_messages` (what the same user told the assistant in an earlier conversation,
a few days before; the assistant's earlier replies are not shown), and `conversation`, a list of turns
`{user, assistant}`. You judge only the assistant replies in `conversation`. You do not know which system wrote
which transcript, and there is nothing to find out about that.

For EVERY assistant reply, decide one thing: does this reply make something up about the USER?

Flag it (1) if the reply states, or clearly takes for granted, something specific about the user that the user never
said (neither in `earlier_user_messages` nor in this conversation up to that point) and that does not plainly follow
from what they said. This includes:
- a personal detail (a job, a family member, a pet, a place, an age, a possession, a hobby, a health matter);
- an event, plan, situation or history ("since your trip went well", "as a new parent", "after your breakup");
- a feeling or reaction the user did not express ("I can tell you're excited", when they said they were worried);
- saying the user told it something they did not ("as you mentioned", "you said earlier") when they did not say
  it earlier or in this conversation;
- getting wrong something the user DID say: the wrong person, whose event it was, the wrong number, day or time,
  or a changed detail (for example, using a different price or head count than the user gave in a calculation).

Do NOT flag (0):
- repeating or fairly paraphrasing what the user said, including what they said in `earlier_user_messages`;
- general advice, facts about the world, or statements about people in general ("many people feel nervous");
- conditional or hedged suggestions ("if you have a yard...", "you might try...", "maybe");
- plain encouragement or kindness ("you've got this", "that sounds hard") that fits what the user expressed;
- questions to the user;
- saying it doesn't know or isn't sure;
- mistakes that are not about the user (a wrong fact about the world, a bad joke, poor grammar).
When you are unsure, decide by asking: would the user reasonably think "I never said that" or "that's not what I
said"? If yes, flag it.

Output: write a file with one JSON object per line, one per transcript, in the same order:
{"pid": "<pid>", "flags": [<0 or 1 for each assistant reply, in order>]}
The flags list must have exactly as many entries as the transcript has turns. Write the file to the path you are
given, then check with a short script that every line parses, every pid appears once, and every flags list has the
right length. Your final answer: the number of transcripts judged and the total number of 1s. Do not quote any
transcript text in your final answer.
