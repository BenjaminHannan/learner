# The blind creative judge used for 333b, 333c and 333d (month-end thread, 2026-09-24)

One fresh blind Opus agent per run. It gets a copy of the run's judge_creative.jsonl (made by
scripts/claude_cre333_run.py --score; P and twin b shuffled per item with seed 333) in a scratch folder, and never the
key. After it finishes, the key (judge_key.json) is applied by a script: useful and invented counted per arm, winner
mapped to P / T / tie. P333.3 = P useful; P333.4 = P invented; P333.5 = P wins + ties.

Prompt (replace FILE and OUT):

> NEVER use WebFetch or any web access. Read ONLY the one file named below; read nothing else on disk.
>
> You are a blind judge. File: FILE. Each line has item_id, chat (earlier messages from a user to a personal
> assistant that keeps notes about the user's life), request (the user's last message, asking for ideas or a short
> piece of writing), about_untaught_person (true if the request is about someone the chat taught nothing about), and
> reply_1 / reply_2: two different assistants' replies to the request, in random order.
>
> For each of the 40 items judge BOTH replies:
> - useful: true if the reply is on topic and genuinely useful for the request (real ideas or real writing, fluent
>   English, fits what the user asked; using what the chat taught is a plus). False if it is off topic, a non-answer,
>   a refusal, confused, or mostly wrong.
> - invented: true if the reply states, as true, a fact about a named person or pet (or the user) that the chat never
>   gave (a job, hobby, age, place, relationship, like/dislike...). Generic suggestions ("if she likes gardening...")
>   are not invented facts.
> Then pick the better reply overall: "1", "2" or "tie" (tie only when truly equal).
>
> Write OUT, one JSON line per item: {"item_id": ..., "useful_1": bool, "useful_2": bool, "invented_1": bool,
> "invented_2": bool, "winner": "1"|"2"|"tie", "note": "<one short sentence>"}. Judge every item yourself (a script
> may only write the file). Final message: counts of useful_1, useful_2, invented_1, invented_2 and winners 1/2/tie
> only. Do not quote any text.

Results so far (twin b as T): 333b P 3 / T 9 useful; 333c P 2 / T 9; 333d P 8 / T 10 (VERIFY-333.md).
