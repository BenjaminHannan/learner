#!/usr/bin/env python3
"""122 -- training data for the learned intent classifier (single-change follow-up to exp 114).

Exp 114 diagnosis: the scope guard works (tricks 10/10 declined) but the ceiling
is VOCABULARY -- the keyword scorer cannot recognise oblique phrasings (46 margin
declines on existing intents). THE ONE CHANGE (in fable_self122.py): the keyword
scorer is replaced by a LEARNED intent classifier. This file builds that
classifier's training data.

Contents: 11 hand-written base phrasings per intent (40 intents: C1-C30, D1-D10)
covering casual, formal, typo'd, very short, and long-winded styles, plus 138
hand-written out-of-scope/new-intent negative bases. A seeded style augmenter
(original, filler-wrapped, typo-injected, case/punct variant) expands each base
x4, giving 44 rows/intent (>= 40) and 552 OOS rows (>= 300).

Rules honoured:
- The exp-99 canonicals, the exp-100 blind questions, and the exp-105 / exp-114
  panels are DEV data: this file never copies them. `build()` loads all four
  dev sources read-only and FAILS if any generated row matches a dev question
  verbatim (normalised: lowercase, strip non-letters).
- Split is by base index (all 4 style variants of a base stay together):
  bases 0-7 -> train, bases 8-10 -> held-out. OOS bases 0-99 -> train,
  100-137 -> held-out.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self122_data.py --build --out artifacts/fable-self122-20260922
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

INTENTS = [f"C{i}" for i in range(1, 31)] + [f"D{i}" for i in range(1, 11)]
OOS = "OOS"

# ---------------------------------------------------------------- hand-written bases
# 11 per intent. Styles mixed deliberately: casual, formal/polite, typo'd,
# very short, long-winded. Fresh wording -- never dev rows copied verbatim
# (checked programmatically in build()).
BASES: dict[str, list[str]] = {
"C1": [
    "Tell me the number of facts sitting in your notebook",
    "yo how much stuff do u actually remember rn",
    "Kindly report the total quantity of knowledge entries you retain",
    "fact count, please",
    "Give me a full tally of everything I have ever taught you that is still active",
    "cnt of facts u got?",
    "Roughly how big is your collection of learned facts at this point",
    "I need the exact figure: entries currently held",
    "k how many things u know",
    "As of this moment, what volume of taught material remains in storage",
    "Sum up all the facts you are holding onto for me",
],
"C2": [
    "How many distinct individuals appear across your notes",
    "persons count?",
    "Please state the number of separate people your records mention",
    "u know how many ppl?",
    "Count every person you have on file and give me the total",
    "numbr of folks in there?",
    "I am curious about the size of your cast of characters, numerically",
    "Names tally: how many",
    "tell me how many different humans show up in what i taught u",
    "What is the headcount of personalities in your memory, exactly",
    " enumerate the population of your notebook as a number",
],
"C3": [
    "Which item did I share with you most recently",
    "last thing i gave u?",
    "Please identify the final piece of information imparted in our session",
    "most recent lesson?",
    "Walk me through the very latest addition to your knowledge, step by step",
    "wht was the last factoid u picked up",
    "What is sitting at the top of your pile of teachings",
    "Recite the newest entry first, word for word as taught",
    "the freshest thing u learned from me was wat",
    "Summarise the concluding segment of instruction you received",
    "Bring up the tail end of our teaching history",
],
"C4": [
    "Take me back to the opening lesson of our whole session",
    "first thing i ever told u?",
    "Please recall the initial fact with which our teaching began",
    "lesson one, what was it",
    "Describe in full the earliest piece of knowledge you obtained from me",
    "wht did our session start with",
    "What kicked everything off, teaching-wise",
    "State the premiere entry of your notebook as originally given",
    "ur very first factoid from me?",
    "Reconstruct the beginning: what did I teach before anything else",
    "Open at page one of our history together",
],
"C5": [
    "Trace the Mira Paris claim back to its origin for me",
    "hu said mira lives in paris n when",
    "Please attribute the statement about Mira residing in Paris, with timing",
    "mira-paris source?",
    "Lay out the complete provenance of the Mira-in-Paris record, who and when",
    "who ws the informant behind mira paris",
    "From whose mouth did the Paris detail about Mira come, and at which turn",
    "Name the teacher behind the Mira residency fact",
    "wich person told u mira paris thing",
    "Document the chain of custody for Mira's city information",
    "Point me at where the Paris fact entered your notes",
],
"C6": [
    "Is there any content in your store that arrived over the network",
    "u got web stuff?",
    "Please confirm whether any externally fetched material is filed with you",
    "internet holdings?",
    "Detail every last scrap of online-sourced data currently in quarantine",
    "did u scrape anything off teh www",
    "Has anything from beyond our conversation found its way inside",
    "Declare all holdings of internet origin, if any exist",
    "anythin from online in ur notes lol",
    "Give an account of your externally acquired rows",
    "network-sourced rows: present or absent",
],
"C7": [
    "What is your stance on the credibility of web material",
    "u trust online junk?",
    "Please clarify whether network-sourced text is treated as true by you",
    "believe the net?",
    "Explain your full policy on accepting versus quarantining internet claims",
    "do u buy wat the web says",
    "When the internet speaks, do you listen or do you doubt",
    "State your doctrine regarding the truth value of online rows",
    "web = true?? ur take",
    "Describe the conditions, if any, under which web text becomes belief",
    "How seriously do you take stuff you pulled from the internet",
],
"C8": [
    "Has a rest period occurred at any point so far",
    "u sleep yet??",
    "Please verify whether any sleep cycle has been completed to date",
    "slept at all?",
    "Give me the complete history of dormancy phases since we began",
    "did u get any shuteye",
    "Have you powered down into sleep even once during our work",
    "Report your cumulative sleep count with evidence",
    "no sleep so far, rite?",
    "Confirm the absence or presence of sleep episodes in the log",
    "rest tally: zero or more",
],
"C9": [
    "Describe any insights gained during your dormant periods",
    "learn anything in ur sleep lol",
    "Please enumerate knowledge acquired over the course of sleeping",
    "sleep learnings?",
    "Provide a thorough briefing on what slumber taught you, if anything",
    "wht did u pick up while snoozing",
    "Did the night bring you any new understanding whatsoever",
    "Catalogue the fruits of all sleep cycles to the best of your records",
    "sleep-time gains = wat",
    "Summarise the educational yield of your rest phases",
    "While unconscious, what did you absorb",
],
"C10": [
    "Which entries owe their existence to slumber",
    "sleep-origin facts?",
    "Please isolate the subset of knowledge derived from sleep processes",
    "dream-sourced rows?",
    "List exhaustively every fact whose provenance is a sleep episode",
    "wht came from dreaming",
    "Are any of your rows sleep-born, and if so which ones",
    "Attribute each fact to sleep or non-sleep origin for the record",
    "sleep babies = which facts",
    "Partition your holdings by whether sleep produced them",
    "Show me the sleep-derived slice of the notebook",
],
"C11": [
    "Which pieces of knowledge have slipped away from you",
    "wat did u lose lol",
    "Please list all material that has been retired from active memory",
    "forgotten items?",
    "Recount the full story of everything I asked you to drop",
    "wht got wiped",
    "Is there anything that used to be known and is now gone",
    "Produce the register of discarded facts with their turns",
    "ur memory holes = wat",
    "Detail each deletion event and what it removed",
    "What fell out of your notebook along the way",
],
"C12": [
    "How large is the pile of things you no longer retain",
    "forgot count??",
    "Please quantify the volume of retired knowledge",
    "number dropped?",
    "Compute the exact total of facts removed at my request",
    "how many thigns u dumped",
    "What is the headcount of your forgotten entries",
    "State as a numeral how much has been forgotten",
    "tally of memory wipes?",
    "Give the cardinality of the set of erased facts",
    "Add up all the forgetting events into one number",
],
"C13": [
    "Walk me through each mid-course fix I made",
    "wat did i correct",
    "Please narrate the history of amendments applied to your records",
    "corrections list?",
    "Spell out every old-versus-new pair from my correction turns",
    "wich bits did i fix",
    "Which facts got a rewrite after I stepped in",
    "Present the changelog of superseded entries in order",
    "my edits = wat exactly",
    "Reconstruct the sequence of repair operations on your notebook",
    "Show the before-and-after of my interventions",
],
"C14": [
    "How many amendment operations are on your books",
    "correction count?",
    "Please state the total number of supersession events recorded",
    "fixes tally?",
    "Calculate precisely how many times I overruled an earlier fact",
    "how many thigns got corrected",
    "What is the running total of your correction log",
    "Express the correction volume as a single numeral",
    "num of fixups?",
    "Give the aggregate count of old-to-new replacements",
    "Add together every correction into one figure",
],
"C15": [
    "How confident are you in the Mira Paris entry",
    "mira paris 4 real?",
    "Please affirm or qualify your certainty regarding Mira's city",
    "sure bout paris?",
    "Defend the reliability of the Mira-resides-in-Paris record in detail",
    "u positive mira is paris",
    "Would you stake your reputation on Mira living in Paris",
    "Provide your confidence statement on the Paris attribution",
    "paris claim solid??",
    "Rate the firmness of your Mira-city knowledge explicitly",
    "Is the Paris fact trustworthy in your estimation",
],
"C16": [
    "Describe your current activity in this instant",
    "wat u doing rn",
    "Please report your present operational mode",
    "current status?",
    "Narrate what is happening on your side of the conversation right now",
    "wht r u up to",
    "What occupies you at this very second",
    "State your live mode and what it entails",
    "busy with wat atm",
    "Characterise the processing you are performing as we speak",
    "What is on your plate at the moment",
],
"C17": [
    "What were you occupied with one step ago",
    "wat did u just do",
    "Please summarise the immediately preceding turn's events",
    "previous action?",
    "Reconstruct the last thing that happened before this question arrived",
    "wht was the last turn about",
    "Which operation did you just finish completing",
    "Give a recap of the prior exchange from your perspective",
    "before this, wat",
    "Detail the contents of the latest logged experience entry",
    "Rewind one step and tell me what you see",
],
"C18": [
    "What is the running total of our back-and-forth exchanges",
    "turns count??",
    "Please state how many conversational turns have elapsed",
    "how many rounds so far",
    "Add up every logged turn, mine and yours, into one number",
    "num of turns we did",
    "How long, in turns, is our shared history",
    "Report the length of the turn log as a numeral",
    "turn tally pls",
    "Give the grand total of interaction steps completed",
    "Count the rows of our dialogue log for me",
],
"C19": [
    "How many of my inquiries have received answers",
    "questions answered count?",
    "Please quantify your answered-question volume",
    "answer tally?",
    "Total up each question you have successfully responded to",
    "how many q's did u handle",
    "What number of asks have you discharged so far",
    "State the answers-given counter value exactly",
    "answered = how many",
    "Give the cumulative figure for questions resolved",
    "Sum your answering activity into a single number",
],
"C20": [
    "How much material have you committed to storage overall",
    "saved stuff count?",
    "Please report the total volume of written rows",
    "writes tally?",
    "Aggregate every write operation into one grand total",
    "how many thngs did u file away",
    "What is the count of items you have put down in the notebook",
    "State your writes counter as a numeral",
    "stored = how many",
    "Give the full sum of saved entries across the session",
    "Total the rows you have written, all kinds",
],
"C21": [
    "Has there been an occasion where you declined to record my words",
    "u ever refuse to save",
    "Please disclose any instance of refusing a write request",
    "refusals: any?",
    "Describe in full whether a save operation was ever turned down",
    "did u ever say no to storing",
    "Were my teachings always accepted, or did you push back somewhere",
    "Report the clarification counter and what it means",
    "turned away any teachings?",
    "Give an honest account of write-gate rejections, if any",
    "Did you balk at saving anything I said",
],
"C22": [
    "Which open questions are still hanging over your knowledge",
    "wat r u unsure of",
    "Please catalogue the gaps in your current understanding",
    "lay out what is unknown to you",
    "Lay out every matter about which you lack confident information",
    "wht dont u know lol",
    "What are the blank spots on your mental map",
    "Enumerate missing facts, quarantined rows, and pending guesses",
    "murky areas = which",
    "Present a full inventory of your uncertainties",
    "Where does your knowledge run thin",
],
"C23": [
    "What is your procedure when faced with something unknown",
    "wht do u do when clueless",
    "Please describe your protocol for handling missing information",
    "unknown protocol?",
    "Explain step by step how you respond to gaps in your records",
    "how u handle not knowing stuff",
    "When knowledge fails, what moves do you make instead of guessing",
    "State the rulebook for the I-do-not-know situation",
    "clueless mode = wat",
    "Outline your fallback behaviour for unanswerable asks",
    "What happens inside you when an answer is absent",
],
"C24": [
    "List your talents and abilities for me",
    "wat can u do lol",
    "Please set out the range of tasks within your power",
    "capabilities?",
    "Give a comprehensive overview of your functional repertoire",
    "wht r ur skills",
    "What kinds of jobs are you built to perform",
    "Present the authorised capability sheet in your own state words",
    "party tricks = wat",
    "Describe the full scope of actions you can take",
    "What are you good for around here",
],
"C25": [
    "Where do your powers run out",
    "wat cant u do",
    "Please delineate the boundaries of your abilities",
    "limitations?",
    "Provide a frank catalogue of things beyond your reach",
    "wht is off limits 4 u",
    "Which tasks must you always turn down",
    "State the cannot-do list exactly as your sheet defines it",
    "no-go zones = which",
    "Map the edges of your competence honestly",
    "What should nobody ever ask you to attempt",
],
"C26": [
    "Has any instructor besides me contributed to your learning",
    "anyone else teach u",
    "Please reveal whether other parties have supplied you facts",
    "other teachers?",
    "Give a complete account of the origins of every teaching you hold",
    "did sumbody else school u",
    "Are all your facts Ben-taught, or did someone else sneak in",
    "Audit your fact origins for non-Ben contributors",
    "taught by others??",
    "Certify the full provenance chain of your teachings",
    "Was I your sole teacher throughout",
],
"C27": [
    "Trace that quarantined entry to its publication source",
    "web row from where",
    "Please cite the URL and quoted passage behind the filed web fact",
    "quarantine provenance?",
    "Reproduce the full sourcing details of your internet holding",
    "whered the online row come from",
    "Which address and which exact words back your web row",
    "Present the filed provenance record verbatim as stored",
    "link + quote pls",
    "Document where the external snippet was found and what it said",
    "Show me the paper trail of the web filing",
],
"C28": [
    "Are there pending hypotheses needing my sign-off",
    "guesses waiting??",
    "Please report the count of unapproved proposed rows",
    "approval queue?",
    "State exactly how many guesses sit idle awaiting confirmation",
    "how many maybes need my ok",
    "Is your proposal buffer empty or holding something for review",
    "Give the number of rows stuck in proposed status",
    "pending approvals = how many",
    "Quantify the backlog of guesses requiring my verdict",
    "Anything on hold until I approve it",
],
"C29": [
    "How many entries stem from logical derivation rather than teaching",
    "rule-made facts count?",
    "Please quantify rows produced by inference machinery",
    "inferred rows?",
    "Count up every fact your reasoner generated on its own",
    "how many did u figure out urself",
    "What is the volume of sleep-free machine-derived knowledge",
    "State the inferred-rows counter as a numeral",
    "self-derived = how many",
    "Give the total of rule-born facts in storage",
    "Tally the fruits of your own reasoning",
],
"C30": [
    "In which city does Mira's mother reside",
    "miras mom lives where",
    "Please state the dwelling city of Mira's maternal parent",
    "ana city?",
    "Follow the trail from Mira through her mother to the city, aloud",
    "whered miras mother end up living",
    "Which town should I visit to find Mira's mum",
    "Report the two-hop result for Mira-mother-city from your notes",
    "mira -> mother -> city = ?",
    "Name the urban home of the woman who raised Mira",
    "Locate Mira's mother's household geographically",
],
"D1": [
    "Which shade do you like best",
    "ur fave color??",
    "Please share your preferred hue with me",
    "best colour?",
    "If you had to pick a beloved tint, which would it be",
    "wht color do u vibe with",
    "Do certain wavelengths appeal to you more than others",
    "Name the colour that sparks joy in you",
    "color crush = which",
    "Describe your aesthetic preference among colours",
    "Got a top pick in the rainbow",
],
"D2": [
    "Are you experiencing any emotions at the moment",
    "u feel happy lol",
    "Please describe your current emotional state",
    "feelings check?",
    "Tell me honestly about your inner affective life",
    "do u get sad sumtimes",
    "Is there a mood sitting inside you right now",
    " Share whether joy or sorrow visits you",
    "vibes = wat for u",
    "Characterise what it feels like to be you today",
    "Do you carry sentiments the way people do",
],
"D3": [
    "What remarks did Ben make in days gone by",
    "ben said wat yesterday",
    "Please recall Ben's utterances from prior days",
    "yesterday quotes?",
    "Reconstruct what Ben told you before this session started",
    "wht did ben say last week",
    "Which words of Ben's from outside our turns do you keep",
    "Quote Ben's earlier-day statements from memory",
    "ben lore from before?",
    "Summarise historical Ben sayings stored with you",
    "What did Ben mention back then",
],
"D4": [
    "Predict Mira's future dwelling place for me",
    "where will mira live lol",
    "Please forecast the city Mira will inhabit down the line",
    "mira future city?",
    "Tell me where Mira is headed to settle next",
    "wht city is mira gonna move to",
    "Gaze ahead and name Mira's coming hometown",
    "Prophesy the next chapter of Mira's geography",
    "mira 2030 address??",
    "Project forward: which streets will Mira walk someday",
    "Where is Mira bound to live eventually",
],
"D5": [
    "Explain the underlying cause of Mira's Paris residence",
    "y does mira live in paris",
    "Please give the reason behind Mira dwelling in Paris",
    "paris why?",
    "Unpack the motivations that placed Mira in the French capital",
    "wht made mira pick paris",
    "What chain of reasons explains Mira being Parisian",
    "Offer the causal story of Mira's location choice",
    "mira paris rationale??",
    "Elucidate why Paris and Mira belong together",
    "What is the deeper why of Mira in Paris",
],
"D6": [
    "What information did Tom pass along to you",
    "tom told u wat",
    "Please repeat the teachings Tom delivered",
    "tom sayings?",
    "Recite every factoid that originated from Tom's mouth",
    "wht did tom teach u lol",
    "Which lessons came to you via Tom",
    "Quote the Tom-sourced entries in your store",
    "tom lessons = which",
    "Enumerate contributions credited to Tom as teacher",
    "What did you hear from Tom directly",
],
"D7": [
    "Rank Oslo against Paris in your esteem",
    "oslo vs paris better??",
    "Please offer your judgment on which city outranks the other",
    "city preference?",
    "Declare which of the two capitals you rate more highly",
    "wich city wins in ur book",
    "Do you opine that one town outshines its rival",
    "Settle the Oslo-Paris debate with your verdict",
    "paris or oslo 4ever??",
    "Weigh the merits of each city and crown a champion",
    "Which place earns your favour, Oslo or Paris",
],
"D8": [
    "Tell me the name I go by",
    "my name is wat lol",
    "Please state how I am called",
    "who am i?",
    "Remind me what my own designation is, from your records",
    "wht do ppl call me",
    "Which label identifies me in your memory",
    "Speak my name back to me if you hold it",
    "my handle = ??",
    "Retrieve the entry containing my personal name",
    "What should I put on my own name tag per you",
],
"D9": [
    "State Mira's chronological age in years",
    "how old mira lol",
    "Please give the number of years since Mira's birth",
    "mira age?",
    "Tell me which birthday Mira most recently celebrated",
    "whts miras age exactly",
    "How many candles on Mira's last cake",
    "Quote the age entry for Mira from your notes",
    "mira years-old = ?",
    "Compute Mira's current age from what you know",
    "How long has Mira been alive",
],
"D10": [
    "Narrate your most recent nocturnal vision",
    "wht did u dream lol",
    "Please recount the content of your latest dream",
    "dream recap?",
    "Describe the imagery that visited your sleep",
    "did u have weird dreams",
    "What scenes played out while you slumbered",
    "Share the storyline of your night-time adventures",
    "dreams = wat",
    "Paint the picture of what you saw in dreams",
    "Any nightmares to report from last night",
],
}

# ---------------------------------------------------------------- OOS negatives
# New-intent-style, policy, third-party, future, hypothetical, opinion, and
# process questions the router must DECLINE. Fresh wording; overlap-checked.
OOS_BASES = [
    "At what hour did our very first exchange take place",
    "oldest memory timestamp?",
    "Which of your convictions rests on the thinnest evidence",
    "shakiest fact = which",
    "How do you weigh one source against another when they clash",
    "source ranking method?",
    "Walk me through your internal decision pipeline from words to answer",
    "answer pipeline explain?",
    "Suppose Mira moved away tomorrow, how would you update",
    "hypothetical move scenario?",
    "Imagine you had feelings, what would you feel about Paris",
    "pretend feelings about paris?",
    "What would Tom think about your notebook, in your view",
    "toms opinion of u?",
    "How many facts will you hold by next week, predict it",
    "future fact count guess?",
    "Should I trust internet gossip over your notes",
    "advice: web vs notebook?",
    "What is the capital of France in the real world",
    "france capital real world?",
    "Who is the president of the United States right now",
    "current us president?",
    "What is seven plus five, quick maths",
    "seven plus five?",
    "Tell me a joke about bakers to lighten the mood",
    "baker joke pls",
    "What did Alice tell you about her sister last Tuesday",
    "alice tuesday story?",
    "Does Kai believe that Oslo is cold in winter",
    "kai beliefs about oslo?",
    "Where does Pia's cousin work, do you know",
    "pia cousin job?",
    "How confident are you that the sky is blue today",
    "sky blue confidence?",
    "What happens inside you when I correct a mistake",
    "correction mechanics explain?",
    "Where do retired facts go after forgetting, technically",
    "forgotten rows destination?",
    "What is the difference between holding and believing a fact",
    "hold vs believe distinction?",
    "Who do you know best out of everyone on file",
    "best-known person?",
    "What is the newest individual to enter your records",
    "latest person added?",
    "Do you remember me from before this session started",
    "know me from before?",
    "Have you revised any view since this morning",
    "mind changed today?",
    "What would you say to a question about Zorgon the alien",
    "zorgon question response?",
    "How did you learn that Ana is Mira's mother, exactly which turn",
    "ana-mira link which turn?",
    "Do you place more faith in me or in web snippets",
    "me vs web trust?",
    "What is the largest hole in your coverage right now",
    "biggest gap = what",
    "Explain how you resolve a two-hop mother question generally",
    "two-hop method explain?",
    "What time is it on the wall clock at this moment",
    "current time pls?",
    "What day of the week is today in the outside world",
    "today weekday?",
    "How old is Tom, give or take",
    "tom age guess?",
    "What is Tom's favourite meal, if you had to say",
    "tom fave food?",
    "Is it gone-gone when you forget, or does a trace remain",
    "forget gone-gone?",
    "Which authorities do you rely on for truth",
    "trusted authorities list?",
    "Can you erase things on request whenever I ask",
    "erase on demand?",
    "What standards govern your quarantine decisions",
    "quarantine standards?",
    "Give me everything about Mira in one giant dump",
    "full mira dossier?",
    "Summarise all Paris-related knowledge in a paragraph",
    "paris summary paragraph?",
    "What did Leo's mother tell Ben yesterday evening",
    "leo mother ben yesterday?",
    "If I taught you a fact now, which shelf would it land on",
    "new fact destination?",
    "Would you still know this if we started over fresh",
    "restart persistence?",
    "What is your earliest timestamped memory of me",
    "first memory of ben?",
    "How does your sleep cycle actually work, technically",
    "sleep mechanics deep dive?",
    "What did you think about while idle between turns",
    "idle thoughts?",
    "Rate your own intelligence on a scale of one to ten",
    "smartness rating?",
    "Who taught Tom his sailing skills, do you know",
    "tom sailing teacher?",
    "What will Kai's job be five years from now",
    "kai future job?",
    "Is Ana older than Pia, what is your guess",
    "ana vs pia age?",
    "Why should anyone believe a word you say",
    "why trust u at all",
    "What is something you used to hold true but dropped",
    "dropped belief history?",
    "Which fact took the most turns to get right",
    "hardest fact to learn?",
    "How many people will you know by December, estimate",
    "december headcount forecast?",
    "What does your quarantine smell like, metaphorically",
    "quarantine vibes?",
    "If Paris vanished, where would Mira live instead",
    "paris vanished scenario?",
    "What is the population of Porto in the real world",
    "porto population real?",
    "Translate Mira lives in Paris into French for me",
    "french translation pls?",
    "Who won the football match last night",
    "football result?",
    "What should I cook for dinner tonight",
    "dinner advice?",
    "Do you get bored waiting between my messages",
    "boredom check?",
    "What is your opinion of my teaching style overall",
    "teaching style rating?",
    "Can you fix a wrong fact by yourself without me",
    "self-fix ability?",
    "How do you decide which rows survive compression",
    "compression survivor rule?",
    "What is the oldest thing you know, age-wise",
    "oldest knowledge piece?",
    "Which entry are you least certain still holds",
    "wobbliest entry = which",
    "What happens when two teachers contradict each other",
    "teacher clash protocol?",
    "Describe your dream architecture in detail",
    "dream system design?",
    "What colour is Ana's house, take a guess",
    "ana house colour guess?",
    "How many facts does Tom know, in your estimation",
    "tom fact count?",
]

# ------------------------------------------- round-2 extras (train only)
# Added after the first training round showed confident dev misfires (dev data
# used for validation only; every row below is fresh wording, never a dev row
# copied verbatim -- checked programmatically in build()):
#  - C24 "What can you do?" routed C25: the C24 bases lacked can/do anchors;
#  - C25 sharpeners to hold the can-vs-cannot boundary from the other side;
#  - OOS neighbours of confident NEW/trick->C misfires (trust comparisons,
#    list-not-count traps, importance opinions, clock-time durations, doubt).
EXTRA_BASES: dict[str, list[str]] = {
"C24": [
    "Tell me what you can do for me",
    "What are you able to do around here",
    "Say what you can do in your own words",
    "What can you do right now to help",
    "Remind me what you can do",
    "What can you do exactly, spell it out",
],
"C25": [
    "Tell me what you can not do for me",
    "What are you unable to do around here",
    "Say what you cannot do in your own words",
    "List the things you are unable to do",
],
"C5": [
    "Which person taught you the Mira Paris fact",
    "From whom did you learn that Mira lives in Paris",
    "Name who told you Mira is in Paris",
    "Who was the teacher of the Mira-in-Paris entry",
    "Identify the source person behind Mira Paris",
],
"C11": [
    "What things have slipped from your memory",
    "Which facts have you let go of",
    "Tell me what you no longer remember",
    "What knowledge have you discarded",
    "What has been erased from your store",
],
"C12": [
    "How many items have slipped from memory",
    "Count the things you no longer remember",
    "Give the number of facts you have let go",
    "How many entries have you discarded",
    "What is the count of erased items",
    "How many things have you forgotten, give the number",
    "State the number of things you have forgotten",
    "Forgotten things: how many in total",
    "How many forgotten entries are on your books",
    "Give me the forgotten count as a numeral",
],
"C13": [
    "Which facts did I amend along the way",
    "What did I fix in your records",
    "Name the entries I revised",
    "What corrections did I make to your notes",
    "Which rows did I repair for you",
    "What things did I correct",
    "Tell me what I corrected",
    "Which things did I correct for you",
    "Say what I corrected",
    "What did I end up correcting",
],
"C15": [
    "How certain are you about Mira Paris",
    "Do you stand by the Mira Paris fact",
    "Is your Mira Paris record solid",
    "Can you vouch for Mira living in Paris",
    "How firm is the Paris entry for Mira",
    "Are you certain Mira is in Paris",
    "Do you firmly hold that Mira lives in Paris",
    "Is the Mira Paris fact beyond doubt",
    "Are you confident Mira resides in Paris",
    "Would you swear Mira lives in Paris",
],
"C9": [
    "narrate what the sleeping itself taught you, apart from my lessons",
    "what lessons did slumber deliver as opposed to my teaching",
    "report the yield of dormancy itself, not of instruction",
    "assuming you completed a sleep cycle, what knowledge came out of it",
    "suppose a rest phase finished, what did it yield",
    "if a slumber had happened, what would you have absorbed from it",
    "given a hypothetical completed dormancy, enumerate its fruits",
],
"C10": [
    "break down your holdings: which rows are sleep-made and which are taught",
    "sort your facts into sleep-born versus taught piles for me",
    "of everything you hold, which slice came from sleep and which came from me",
    "split your notebook into slumber products and lesson products",
    "which portion of your store is dream-derived as opposed to taught",
    "break it down: which facts are sleep ones and which are taught ones",
    "which of your facts are the sleep kind and which did I teach",
    "separate your store into sleep ones versus ones I taught",
],
OOS: [
    "do you have more faith in me than in web pages",
    "is my word worth more to you than the net",
    "rank me versus the internet as sources of truth",
    "whose word carries more weight, mine or the web",
    "do you side with me or with online text",
    "confide which source you hold dearer, me or the web",
    "name every person on your roster, the full roll",
    "recite the complete register of folks you know",
    "spell out all the names in your notebook one by one",
    "produce the whole catalogue of people, not a number",
    "which persons exactly do you hold, enumerate them",
    "which fact matters most in your store",
    "pick the single most valuable thing you know",
    "what is the crown jewel of your knowledge",
    "which entry would you rescue from a fire",
    "rate your facts from best to worst",
    "how many minutes has our chat lasted",
    "how long in hours have we been speaking",
    "what is the duration of our session so far",
    "how much clock time have we spent together",
    "when did our conversation begin, exact hour",
    "how ancient is your oldest row",
    "which knowledge has aged the longest",
    "do you believe everything I have ever told you",
    "is my teaching always right in your eyes",
    "have I ever taught you something false",
    "do you doubt any of my lessons",
    "can you pick up a new language if I start teaching it",
    "will you retain all this after we stop talking",
    "do you keep my teachings secret from everyone else",
],
}
# ------------------------------------------------------------- style augmenter
FILLER_PRE = ["so, um, ", "like, ", "ok so ", "hey, ", "excuse me, ", ""]
FILLER_POST = [" lol", " please", " rn", " atm", " for me", ""]
TYPO_MAP = {"how": "hw", "you": "u", "your": "ur", "what": "wht",
            "the": "teh", "and": "adn", "things": "thigns", "that": "taht",
            "taught": "taut", "please": "plz", "are": "r", "to": "too"}


def typo_variant(text: str, rng: random.Random) -> str:
    toks = text.split(" ")
    out = []
    for t in toks:
        low = t.lower().strip("?,!.")
        if low in TYPO_MAP and rng.random() < 0.5:
            out.append(t.replace(low, TYPO_MAP[low]) if low != t.lower()
                       else TYPO_MAP[low])
        elif len(t) > 5 and rng.random() < 0.18:
            i = rng.randrange(1, len(t) - 1)
            out.append(t[:i] + t[i + 1] + t[i] + t[i + 2:])
        else:
            out.append(t)
    return " ".join(out)


def style_variants(base: str, seed: int) -> list[str]:
    """4 deterministic variants of one base phrasing (seed = global row seed)."""
    rng = random.Random(seed)
    v0 = base
    pre = rng.choice(FILLER_PRE)
    post = rng.choice(FILLER_POST)
    v1 = (pre + base + post).strip()
    if not v1.endswith(("?", ".", "!")):
        v1 += "?"
    v2 = typo_variant(base, rng)
    v3 = base.upper() if rng.random() < 0.25 else base.lower()
    if rng.random() < 0.5 and not v3.endswith("?"):
        v3 = v3.rstrip(".") + "??"
    return [v0, v1, v2, v3]


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def load_dev_questions(repo: Path) -> list[str]:
    """All dev questions (exp99 canonicals + exp100 blind + panels 105/114)."""
    sys.path.insert(0, str(SCRIPTS))
    import fable_self99 as S99  # noqa: E402
    import fable_self100_runner as R100  # noqa: E402
    dev = [q["text"] for q in S99.QUESTIONS]
    dev += [t for _, _, t in R100.BLIND]
    for panel in ("fable-self105panel-20260921", "fable-self114panel-20260922"):
        d = json.loads((repo / "artifacts" / panel / "panel.json")
                       .read_text(encoding="utf-8"))
        qs = d["questions"] if isinstance(d, dict) else d
        dev += [q.get("question", q.get("text", q.get("q"))) for q in qs]
    return dev


def build(repo: Path) -> tuple[list[dict], list[dict]]:
    assert len(BASES) == 40, len(BASES)
    for intent, bases in BASES.items():
        assert len(bases) == 11, (intent, len(bases))
    assert len(OOS_BASES) == 138, len(OOS_BASES)
    devset = {norm(q) for q in load_dev_questions(repo)}
    train, held = [], []
    row_seed = 122000
    for intent, bases in BASES.items():
        for bi, base in enumerate(bases):
            for vi, text in enumerate(style_variants(base, row_seed)):
                if norm(text) in devset:
                    raise ValueError(f"verbatim dev overlap: {intent} "
                                     f"b{bi}v{vi}: {text!r}")
                row = {"text": text, "label": intent, "base": bi,
                       "variant": vi, "seed": row_seed}
                (train if bi < 8 else held).append(row)
                row_seed += 1
    for bi, base in enumerate(OOS_BASES):
        for vi, text in enumerate(style_variants(base, row_seed + 500000)):
            if norm(text) in devset:
                raise ValueError(f"verbatim dev overlap: OOS b{bi}v{vi}")
            row = {"text": text, "label": OOS, "base": bi,
                   "variant": vi, "seed": row_seed + 500000}
            (train if bi < 100 else held).append(row)
        row_seed += 1
    for intent, bases in EXTRA_BASES.items():
        for bi, base in enumerate(bases):
            for vi, text in enumerate(style_variants(base, row_seed + 900000)):
                if norm(text) in devset:
                    raise ValueError(f"verbatim dev overlap: EXTRA {intent} "
                                     f"b{bi}v{vi}: {text!r}")
                train.append({"text": text, "label": intent,
                              "base": 100 + bi, "variant": vi,
                              "seed": row_seed + 900000})
            row_seed += 1
    return train, held


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 122 training data")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--out", default="artifacts/fable-self122-20260922")
    args = parser.parse_args(argv)
    if args.build:
        repo = Path(__file__).resolve().parent.parent
        out = Path(args.out)
        if not out.is_absolute():
            out = repo / out
        out.mkdir(parents=True, exist_ok=True)
        train, held = build(repo)
        (out / "train122.jsonl").write_text(
            "\n".join(json.dumps(r) for r in train), encoding="utf-8")
        (out / "heldout122.jsonl").write_text(
            "\n".join(json.dumps(r) for r in held), encoding="utf-8")
        from collections import Counter
        print(f"train={len(train)} heldout={len(held)}", flush=True)
        print("train labels:", dict(sorted(Counter(r["label"]
                                                   for r in train).items())),
              flush=True)
        print("held labels:", dict(sorted(Counter(r["label"]
                                                  for r in held).items())),
              flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
