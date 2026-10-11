# How to write the spoken script for one part of the explainer

**IMPORTANT, read first: nobody can read anything you say except the coordinator, who reads your final structured result. NEVER call any `mcp__hearthbot__` tool (reply, update_status, post, react, anything). Do not message anyone. Just do the work and finish with the structured result.**

You write what a calm voice says while the video plays. The video already shows a short caption for each beat. A free voice (Kokoro, "af_heart") reads your text aloud, starting right when the caption appears. Your job: for every caption, write the spoken version, for a smart 12-year-old who has never heard of this project.

## Your files (one chapter = one job)

Work inside `/mnt/project-files/animations/model-explainer-final/project/` (call it `P`). For chapter `chNN`:

1. `python3 P/tools/voice/seginfo.py chNN` prints every segment: its id, its time slot, how many seconds of speech you may use, the caption, and everything on screen in that scene. **This is your source of truth. Do not use any other source for facts.**
2. Write `P/narration/script/chNN.json`: a JSON object `{ "<segment id>": "<spoken text>", ... }` with **one entry for every segment id**, no extras. (`.card` segments are the title card at the start of the chapter: say the kicker and the title naturally, e.g. "Part 3 of 8. The thinker: rounds of looking and passing notes.")
3. Run `python3 P/tools/voice/check_script.py chNN`. It must say `0 error(s)`. Fix every error and read every warning.

Write the JSON with a script or an editor and then re-open it to check it parses. Write it only under `P/narration/script/`. Do not edit anything else in the project.

## Time: the hard limit

Each segment has a slot (the time until the next caption starts; scenes whose captions are too dense may be given more time later, so never cut a fact only to save a second or two, but do not let a segment run past its slot). Speech must fit in `slot - 1.0` s. The checker predicts speaking time from letters, sentences and commas, and fails you at `slot - 0.5` s. Rough guide: about 2.2 spoken words per second; numbers cost a lot (the voice says "six thousand, forty", not "6,040"). Many captions are short compared to their slot: there you have room to explain a little more. Some captions (long number lists) are too long to say as written: shorten by dropping the least important detail, **never by dropping a number that is in the caption** (see below).

## Faithfulness: the rules that matter most

- **Every number in the caption must be spoken** (write it with digits exactly as in the caption; the tool turns digits into words). The checker fails you if you leave one out.
- **Big numbers may be rounded when spoken, never otherwise.** A number of 100,000 or more may be said rounded to three significant figures, with a hedge word (about, roughly, nearly, around) in the same segment: 134,217,728 -> "about 134 million", 196,864 -> "about 197 thousand", 1,418,702 -> "about 1.42 million". The exact digits stay on screen. Write the rounded form with digits and the unit word ("134 million"). Never round a number under 100,000, and never round a score, a percentage, or a number with a decimal point. The checker verifies the rounding.
- **You may use another number only if it is on screen in the same scene** (the `everything on screen` line). No new numbers, no rounding, no "about a thousand" for 1,177. Never write a number from memory.
- **Keep every honesty word.** If the caption says planned, never tested, built but not tested, picture only, made-up example, stand-in, only, just, one seed, as of Oct 9, about, measured, suggested, untested: the spoken text must carry the same meaning. Do not turn "planned" into "is", "suggested" into "shown", or "about 100 million" into "100 million". The checker warns when a caveat word family disappears; each warning needs a real reason or a fix.
- **No new facts, no new comparisons, no hype.** You may add a short plain explanation, a clear analogy that the scene already uses, or a pointer to what is on screen ("the blue box is the thinker") only if the scene text supports it. If you are not sure it is on screen, leave it out.
- Keep the same order as the captions. Each segment must make sense after the one before it (a listener hears the whole chapter in order), so do not repeat the same sentence in two segments and do not start every segment with "So".

## Style

- Short sentences. Everyday words. Say "we" and "the model". Explain a word once when it first appears, the way the caption does.
- Sound like a person talking, not a slide. Contractions are fine. No lists, no headings, no brackets, no quotation marks, no emoji, no dashes, no slashes, no semicolons if you can avoid them.
- Allowed characters: letters, digits, spaces and `. , : ; ! ? ' -`. Percent signs, plus/minus signs, `x` for times, `M` for million (3M, 100M), and code names such as T1SDR, G1, H1, B2, EGE, bAbI, GPT-2 are fine: the tool says them correctly. Do not write other all-caps words (write them as letters with spaces, "R P N", or use a plain word).
- Do not say "caption", "slide", "video", "chapter" or "the narrator".

## When you finish

Return the structured result: the chapter id, how many segments you wrote, the final count of checker errors (must be 0), and a list of the segments you shortened a lot or had to cut detail from (so a reviewer can look). Nothing else.
