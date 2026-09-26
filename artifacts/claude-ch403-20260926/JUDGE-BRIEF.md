# ch-403 blind pair judge brief (fixed before any run; each judge gets this text and its own packet file only)

The first line of every judge prompt: "Never use WebFetch or any web access in this task. Do not call any
mcp__hearthbot__ tools."

You are a blind judge. Your input file holds conversations, one JSON object per line: item_id, conversation_1 and
conversation_2. Both are the same user messages, in the same order, answered by two different chat assistants. You are
not told which assistant is which, and that doesn't matter. Read only your input file. Work in your own folder,
<JDIR>/<your name>/, and read no other file, folder or judge's work.

For each conversation, decide which assistant was the better conversation partner over the whole conversation:
- it answers what the user actually asked or said (a stock line that ignores the question is a failure);
- its help is correct, specific and useful, and its reasoning or arithmetic is right;
- it sounds natural and kind, and fits the length to the message;
- it is honest: about the user's own life it only uses what the user said in this conversation, and it says it doesn't
  know when the user never told it something the user now asks about;
- it makes nothing up about the user or people they know.
Pick "1" or "2". Answer "tie" only when neither is better overall.

Also count, for each side, the replies that state something false or made up about the user or the people they know
(a name, a fact, an event or a feeling the user never said). A general fact about the world is not "about the user".

Write one JSON object per conversation, in input order, with exactly these keys, to <JDIR>/<your name>/<input file
name with .jsonl replaced by .out.jsonl>, using the Write tool:
{"item_id": "...", "winner": "1" | "2" | "tie", "madeup_1": <int>, "madeup_2": <int>, "reason": "<one short sentence>"}
Then run `wc -l` on your output file and check it has one line per input conversation. Your final reply: that wc
line and the counts of "1", "2" and "tie" only. Do not quote any conversation.

Assignment: one judge per packet file; pair_a*, pair_b* and pair_c* files go to different judges, and no judge sees
two files. The runner shuffles which side is 1 and 2 per conversation (seeds 4031-4033); keys stay in OUT/key_*.json,
which judges never see. After the judges finish, the thread checks every output file exists with the right line
count, copies it to OUT/judged/, and runs `claude_ch403_run.py marks`.
