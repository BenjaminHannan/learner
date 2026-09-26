# Why does my small "is this note true?" checker reject almost everything? (no code or file access needed)

You are an expert in LLM verification, NLI/fact-checking and calibration. You cannot see my code; everything is below. Do not
ask me to run anything first. Label every claim **shown by the data below**, **suggested**, or **untested**. End with a
plain-language summary for me (a high-school senior). Scope: only the chat note writer and its checker. My project also has
small puzzle ("card") experiments and a simulated village; do not mix those in.

## Setup
- A personal assistant reads chats. A note writer (MiniCPM5-1B + LoRA) writes 0-3 plain third-person sentences per message
  ("Lenka started at Orrin Labs in March"), each citing the turns it came from. Blind LLM judges grade each note: ok,
  unsupported (a guess, inference, wrong detail or wrong person), bad_cite, bad_when, bad_form.
- The writer's notes are often untrue: 113/360 unsupported on one sealed test; 96/277 on dev; 993 of 2,054 (48%) on 120
  fresh training dialogs (greedy + one temperature-0.8 sample per message); 145 of 277 (52%) on the newest sealed test.
- Checker: a second MiniCPM5-1B + LoRA (rank 32, 2 epochs, lr 2e-4, batch 16, max 512 tokens). Prompt: "Does the conversation
  state everything in this sentence (no guess, no wrong person, time or detail)? Answer yes or no." + date + up to 6
  earlier turns + latest turn + the sentence. Score = softmax over the first-token logits of "yes" and "no".
- Training rows (2,257 train / 218 dev, split by dialog): the writer's own judged notes (ok/bad_cite -> yes; unsupported/
  bad_when -> no; bad_form skipped) plus 472 code-made negatives (a name from the window swapped in, or a number changed).
  Totals: 965 yes, 1,510 no. Training ran 284 steps, 3.25 min, dev loss 0.198.
- Bar rule (fixed before training): the lowest value in a grid (0.1 ... 0.9999) where accepted dev notes are <= 4%
  unsupported; dev = 277 judged notes from an older set of dialogs.

## Result (sealed test, 30 fresh dialogs, 314 notes; key = notes both blind judges agree on: 132 ok, 145 unsupported, 37 excluded)
- The rule picked 0.98; at 0.98 the checker accepted 6 of 277 dev notes (0 unsupported, 6 of 167 ok).
- Test at 0.98: kept 1 of 132 true notes (C2 needed >= 80%); the one kept note was true. FAIL.
- An earlier checker (rd-371, trained on relation facts made into short texts with code-made negatives) also collapsed:
  it saved 15 facts vs 106 for plain min-token confidence.

## Questions
1. Most likely reasons, ranked: weak separation (the scores do not rank true above untrue), a class/threshold problem
   (60% "no", a 4% target on a 50%-untrue stream), label noise, prompt/first-token scoring, too little data (about 1,900
   real rows), or the perturbation negatives. For each, what number in the data above supports or weakens it, and what
   single cheap measurement on the dev predictions would tell them apart (e.g. AUC, score histograms by verdict)?
2. Is "keep >= 80% of true notes with <= 5% of kept notes untrue" realistic for a 1B checker when half the stream is
   untrue? What does it require of the ROC curve? Suggest an honest target.
3. The next single experiment (one change), with pass marks fixed in advance and the result that would prove it wrong.
   Consider: balanced classes, dropping the synthetic negatives, sequence-level scoring, several samples of the writer
   agreeing, training the writer itself to write fewer untrue notes (e.g. preference training on judged own drafts),
   or dropping the checker and treating notes purely as search pointers back to the original messages.
4. Plain-language summary for me: five to eight sentences, no jargon.
