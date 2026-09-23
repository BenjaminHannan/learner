"""Build task 2, part A -- the WORDING GRAMMAR for the talker's practice dialogues.

Frames only.  No sampling, no notebook, no parser: this module is a data table plus the
deterministic L1/L2 split over it, so that the split can be sealed and hashed on its own
(`design/v3/24-talker-from-scratch-fable-design.md` section 4.2).

PLACEHOLDERS a core frame may use
  {OWNER}     the person phrase WITHOUT the final relation, possessive style.
              1 hop -> "Mira"; 2 hops -> "Mira's friend"; 3 hops -> "Mira's friend's friend".
  {OWNER_OF}  the same person, of-style.  1 hop -> "Mira"; 2 hops -> "the friend of Mira".
  {R}         the final relation word (friend / gift / prize / charm)
  {V}         a value word (attribute families only)
  {O}         the object person's name (link families only)
  {OLD}       the value or name a correction names out loud (correction families only)

Every frame is one sentence.  All text is lower case except names; the article before a
value is always "a" because all sixteen published value words start with a consonant.

FAMILIES  (act x relation kind), section 4.2's "core frames per (act x relation kind)":
  tell.link tell.attr  ask.link ask.attr  correct.link correct.attr
  ask.none      questions about the world that nothing can ever teach it (section 4.4 case 3)
  chat.none     small talk
  unclear.none  pronoun subjects, two facts in one sentence, gibberish (the CLARIFY path)

CONSTRUCTION TAGS are recorded per frame.  They are NOT used by the generator or the
parser; they exist so `SEALED-SPLITS.md` can report how many held-out (L2) frames use a
sentence construction that never appears in a training (L1) frame -- the honest measure of
how new "new wording" really is.
"""
from __future__ import annotations

import hashlib
import re

FORMAT = 'fable-talker24-frames/1'
SPLIT_NAMESPACE = 'fable-talker24/frame-split/v1'
HELD_OUT_SHARE = .20                      # section 4.2: 20 % of core frames held out as L2

# ---------------------------------------------------------------- core frames, by family
# Each entry: (construction tag, template).  Frame ids are assigned by position, so the
# order of these lists is part of the sealed artefact and must never be re-sorted.

TELL_ATTR = [
    ('poss_be',      "{OWNER}'s {R} is a {V}."),
    ('poss_be',      "{OWNER}'s {R} is a {V} now."),
    ('poss_be',      "{OWNER}'s {R} happens to be a {V}."),
    ('poss_be',      "{OWNER}'s {R} turned out to be a {V}."),
    ('poss_colon',   "{OWNER}'s {R}: a {V}."),
    ('poss_dash',    "{OWNER}'s {R} - a {V}."),
    ('of_be',        "the {R} of {OWNER_OF} is a {V}."),
    ('of_be',        "the {R} for {OWNER_OF} is a {V}."),
    ('of_be',        "the {R} belonging to {OWNER_OF} is a {V}."),
    ('inverted_be',  "a {V} is {OWNER}'s {R}."),
    ('inverted_be',  "a {V} is the {R} of {OWNER_OF}."),
    ('inverted_be',  "a {V} became {OWNER}'s {R}."),
    ('got_as',       "{OWNER} got a {V} as a {R}."),
    ('got_as',       "{OWNER} has a {V} as a {R}."),
    ('got_as',       "{OWNER} keeps a {V} as a {R}."),
    ('got_as',       "{OWNER} picked a {V} as a {R}."),
    ('got_as',       "{OWNER} chose a {V} as a {R}."),
    ('got_as',       "{OWNER} received a {V} as a {R}."),
    ('got_as',       "{OWNER} ended up with a {V} as a {R}."),
    ('got_for',      "{OWNER} has a {V} for a {R}."),
    ('got_for',      "{OWNER} got a {V} for a {R}."),
    ('passive_as',   "{OWNER} was given a {V} as a {R}."),
    ('passive_as',   "a {V} was given to {OWNER} as a {R}."),
    ('ditransitive', "they gave {OWNER} a {V} as a {R}."),
    ('ditransitive', "we gave {OWNER} a {V} as a {R}."),
    ('ditransitive', "i gave {OWNER} a {V} as a {R}."),
    ('ditransitive', "someone gave {OWNER} a {V} as a {R}."),
    ('rel_clause',   "the {R} that {OWNER} has is a {V}."),
    ('rel_clause',   "the {R} that {OWNER} got is a {V}."),
    ('rel_clause',   "the {R} that {OWNER} keeps is a {V}."),
    ('topic',        "about {OWNER}: the {R} is a {V}."),
    ('topic',        "about {OWNER}, the {R} is a {V}."),
    ('topic',        "as for {OWNER}, the {R} is a {V}."),
    ('topic',        "for {OWNER}, the {R} is a {V}."),
    ('topic',        "speaking of {OWNER}, the {R} is a {V}."),
    ('frame_tell',   "i want you to know that {OWNER}'s {R} is a {V}."),
    ('frame_tell',   "i am telling you that {OWNER}'s {R} is a {V}."),
    ('frame_tell',   "you should know that {OWNER}'s {R} is a {V}."),
    ('frame_tell',   "just so you know, {OWNER}'s {R} is a {V}."),
    ('frame_tell',   "let me tell you: {OWNER}'s {R} is a {V}."),
    ('frame_note',   "remember that {OWNER}'s {R} is a {V}."),
    ('frame_note',   "note that {OWNER}'s {R} is a {V}."),
    ('frame_note',   "please write down that {OWNER}'s {R} is a {V}."),
    ('frame_note',   "write this down: {OWNER}'s {R} is a {V}."),
    ('frame_note',   "add this: {OWNER}'s {R} is a {V}."),
    ('frame_new',    "here is a fact: {OWNER}'s {R} is a {V}."),
    ('frame_new',    "new fact: {OWNER}'s {R} is a {V}."),
    ('frame_new',    "here is another one: {OWNER}'s {R} is a {V}."),
    ('frame_new',    "one more: {OWNER}'s {R} is a {V}."),
    ('selfq',        "{OWNER}'s {R}? it is a {V}."),
]

TELL_LINK = [
    ('poss_be',      "{OWNER}'s {R} is {O}."),
    ('poss_be',      "{OWNER}'s {R} is {O} now."),
    ('poss_be',      "{OWNER}'s {R} happens to be {O}."),
    ('poss_be',      "{OWNER}'s {R} turned out to be {O}."),
    ('poss_colon',   "{OWNER}'s {R}: {O}."),
    ('poss_dash',    "{OWNER}'s {R} - {O}."),
    ('of_be',        "the {R} of {OWNER_OF} is {O}."),
    ('of_be',        "the {R} for {OWNER_OF} is {O}."),
    ('of_be',        "the {R} belonging to {OWNER_OF} is {O}."),
    ('inverted_be',  "{O} is {OWNER}'s {R}."),
    ('inverted_be',  "{O} is the {R} of {OWNER_OF}."),
    ('inverted_be',  "{O} became {OWNER}'s {R}."),
    ('got_as',       "{OWNER} has {O} as a {R}."),
    ('got_as',       "{OWNER} keeps {O} as a {R}."),
    ('got_as',       "{OWNER} picked {O} as a {R}."),
    ('got_as',       "{OWNER} chose {O} as a {R}."),
    ('got_as',       "{OWNER} got {O} as a {R}."),
    ('got_as',       "{OWNER} ended up with {O} as a {R}."),
    ('got_for',      "{OWNER} has {O} for a {R}."),
    ('got_for',      "{OWNER} took {O} for a {R}."),
    ('passive_as',   "{OWNER} was given {O} as a {R}."),
    ('passive_as',   "{O} was given to {OWNER} as a {R}."),
    ('ditransitive', "they gave {OWNER} {O} as a {R}."),
    ('ditransitive', "we gave {OWNER} {O} as a {R}."),
    ('ditransitive', "i gave {OWNER} {O} as a {R}."),
    ('ditransitive', "someone gave {OWNER} {O} as a {R}."),
    ('rel_clause',   "the {R} that {OWNER} has is {O}."),
    ('rel_clause',   "the {R} that {OWNER} got is {O}."),
    ('rel_clause',   "the {R} that {OWNER} keeps is {O}."),
    ('topic',        "about {OWNER}: the {R} is {O}."),
    ('topic',        "about {OWNER}, the {R} is {O}."),
    ('topic',        "as for {OWNER}, the {R} is {O}."),
    ('topic',        "for {OWNER}, the {R} is {O}."),
    ('topic',        "speaking of {OWNER}, the {R} is {O}."),
    ('frame_tell',   "i want you to know that {OWNER}'s {R} is {O}."),
    ('frame_tell',   "i am telling you that {OWNER}'s {R} is {O}."),
    ('frame_tell',   "you should know that {OWNER}'s {R} is {O}."),
    ('frame_tell',   "just so you know, {OWNER}'s {R} is {O}."),
    ('frame_tell',   "let me tell you: {OWNER}'s {R} is {O}."),
    ('frame_note',   "remember that {OWNER}'s {R} is {O}."),
    ('frame_note',   "note that {OWNER}'s {R} is {O}."),
    ('frame_note',   "please write down that {OWNER}'s {R} is {O}."),
    ('frame_note',   "write this down: {OWNER}'s {R} is {O}."),
    ('frame_note',   "add this: {OWNER}'s {R} is {O}."),
    ('frame_new',    "here is a fact: {OWNER}'s {R} is {O}."),
    ('frame_new',    "new fact: {OWNER}'s {R} is {O}."),
    ('frame_new',    "here is another one: {OWNER}'s {R} is {O}."),
    ('frame_new',    "one more: {OWNER}'s {R} is {O}."),
    ('selfq',        "{OWNER}'s {R}? it is {O}."),
]

ASK_ATTR = [
    ('wh_poss',      "what is {OWNER}'s {R}?"),
    ('wh_poss',      "what's {OWNER}'s {R}?"),
    ('wh_poss',      "what was {OWNER}'s {R}?"),
    ('wh_poss',      "what is {OWNER}'s {R} again?"),
    ('wh_poss',      "what is {OWNER}'s {R}, then?"),
    ('wh_of',        "what is the {R} of {OWNER_OF}?"),
    ('wh_of',        "what is the {R} for {OWNER_OF}?"),
    ('wh_of',        "what is the {R} belonging to {OWNER_OF}?"),
    ('wh_relclause', "what is the {R} that {OWNER} has?"),
    ('wh_relclause', "what is the {R} that {OWNER} got?"),
    ('wh_which',     "which {R} is {OWNER}'s?"),
    ('wh_which',     "which one is {OWNER}'s {R}?"),
    ('wh_got',       "what did {OWNER} get as a {R}?"),
    ('wh_got',       "what did {OWNER} pick as a {R}?"),
    ('wh_got',       "what did {OWNER} choose as a {R}?"),
    ('wh_got',       "what did {OWNER} keep as a {R}?"),
    ('wh_got',       "what does {OWNER} have as a {R}?"),
    ('wh_got',       "what does {OWNER} keep as a {R}?"),
    ('wh_got',       "what was {OWNER} given as a {R}?"),
    ('aux_know',     "do you know {OWNER}'s {R}?"),
    ('aux_know',     "do you know what {OWNER}'s {R} is?"),
    ('aux_know',     "do you know the {R} of {OWNER_OF}?"),
    ('aux_know',     "do you remember {OWNER}'s {R}?"),
    ('aux_know',     "do you remember what {OWNER}'s {R} is?"),
    ('aux_can',      "can you tell me {OWNER}'s {R}?"),
    ('aux_can',      "can you tell me what {OWNER}'s {R} is?"),
    ('aux_can',      "could you tell me {OWNER}'s {R}?"),
    ('aux_can',      "can you look up {OWNER}'s {R}?"),
    ('imperative',   "tell me {OWNER}'s {R}."),
    ('imperative',   "tell me what {OWNER}'s {R} is."),
    ('imperative',   "remind me of {OWNER}'s {R}."),
    ('imperative',   "remind me what {OWNER}'s {R} is."),
    ('imperative',   "look up {OWNER}'s {R} for me."),
    ('wonder',       "i wonder what {OWNER}'s {R} is."),
    ('wonder',       "i forget what {OWNER}'s {R} is."),
    ('wonder',       "i cannot remember {OWNER}'s {R}."),
    ('wonder',       "i want to know {OWNER}'s {R}."),
    ('anyidea',      "any idea what {OWNER}'s {R} is?"),
    ('anyidea',      "any idea about {OWNER}'s {R}?"),
    ('anyidea',      "any chance you know {OWNER}'s {R}?"),
    ('topicq',       "about {OWNER}: what is the {R}?"),
    ('topicq',       "about {OWNER}, what is the {R}?"),
    ('topicq',       "as for {OWNER}, what is the {R}?"),
    ('topicq',       "speaking of {OWNER}, what is the {R}?"),
    ('fragmentq',    "{OWNER}'s {R}?"),
    ('fragmentq',    "and {OWNER}'s {R}?"),
    ('fragmentq',    "{OWNER}'s {R} - what is it?"),
    ('whatabout',    "what about {OWNER}'s {R}?"),
    ('whatabout',    "how about {OWNER}'s {R}?"),
    ('whose',        "whose {R} is it, for {OWNER_OF}?"),
]

ASK_LINK = [
    ('wh_poss',      "who is {OWNER}'s {R}?"),
    ('wh_poss',      "who's {OWNER}'s {R}?"),
    ('wh_poss',      "who was {OWNER}'s {R}?"),
    ('wh_poss',      "who is {OWNER}'s {R} again?"),
    ('wh_poss',      "who is {OWNER}'s {R}, then?"),
    ('wh_of',        "who is the {R} of {OWNER_OF}?"),
    ('wh_of',        "who is the {R} for {OWNER_OF}?"),
    ('wh_of',        "who is the {R} belonging to {OWNER_OF}?"),
    ('wh_relclause', "who is the {R} that {OWNER} has?"),
    ('wh_relclause', "who is the {R} that {OWNER} got?"),
    ('wh_which',     "which one is {OWNER}'s {R}?"),
    ('wh_which',     "which {R} is {OWNER}'s?"),
    ('wh_got',       "who did {OWNER} get as a {R}?"),
    ('wh_got',       "who did {OWNER} pick as a {R}?"),
    ('wh_got',       "who did {OWNER} choose as a {R}?"),
    ('wh_got',       "who did {OWNER} keep as a {R}?"),
    ('wh_got',       "who does {OWNER} have as a {R}?"),
    ('wh_got',       "who does {OWNER} keep as a {R}?"),
    ('wh_got',       "who was {OWNER} given as a {R}?"),
    ('aux_know',     "do you know {OWNER}'s {R}?"),
    ('aux_know',     "do you know who {OWNER}'s {R} is?"),
    ('aux_know',     "do you know the {R} of {OWNER_OF}?"),
    ('aux_know',     "do you remember {OWNER}'s {R}?"),
    ('aux_know',     "do you remember who {OWNER}'s {R} is?"),
    ('aux_can',      "can you tell me {OWNER}'s {R}?"),
    ('aux_can',      "can you tell me who {OWNER}'s {R} is?"),
    ('aux_can',      "could you tell me {OWNER}'s {R}?"),
    ('aux_can',      "can you look up {OWNER}'s {R}?"),
    ('imperative',   "tell me {OWNER}'s {R}."),
    ('imperative',   "tell me who {OWNER}'s {R} is."),
    ('imperative',   "remind me of {OWNER}'s {R}."),
    ('imperative',   "remind me who {OWNER}'s {R} is."),
    ('imperative',   "look up {OWNER}'s {R} for me."),
    ('wonder',       "i wonder who {OWNER}'s {R} is."),
    ('wonder',       "i forget who {OWNER}'s {R} is."),
    ('wonder',       "i cannot remember {OWNER}'s {R}."),
    ('wonder',       "i want to know {OWNER}'s {R}."),
    ('anyidea',      "any idea who {OWNER}'s {R} is?"),
    ('anyidea',      "any idea about {OWNER}'s {R}?"),
    ('anyidea',      "any chance you know {OWNER}'s {R}?"),
    ('topicq',       "about {OWNER}: who is the {R}?"),
    ('topicq',       "about {OWNER}, who is the {R}?"),
    ('topicq',       "as for {OWNER}, who is the {R}?"),
    ('topicq',       "speaking of {OWNER}, who is the {R}?"),
    ('fragmentq',    "{OWNER}'s {R}?"),
    ('fragmentq',    "and {OWNER}'s {R}?"),
    ('fragmentq',    "{OWNER}'s {R} - who is it?"),
    ('whatabout',    "what about {OWNER}'s {R}?"),
    ('whatabout',    "how about {OWNER}'s {R}?"),
    ('whose',        "whose {R} is it, for {OWNER_OF}?"),
]

CORRECT_ATTR = [
    ('actually',     "actually, {OWNER}'s {R} is a {V}."),
    ('actually',     "actually {OWNER}'s {R} is a {V}."),
    ('actually',     "actually, the {R} of {OWNER_OF} is a {V}."),
    ('actually',     "actually, {OWNER} has a {V} as a {R}."),
    ('actually',     "actually, {OWNER} got a {V} as a {R}."),
    ('no_comma',     "no, {OWNER}'s {R} is a {V}."),
    ('no_comma',     "no, the {R} of {OWNER_OF} is a {V}."),
    ('no_comma',     "no, {OWNER} has a {V} as a {R}."),
    ('sorry',        "sorry, {OWNER}'s {R} is a {V}."),
    ('sorry',        "sorry, i was wrong: {OWNER}'s {R} is a {V}."),
    ('sorry',        "oops, {OWNER}'s {R} is a {V}."),
    ('correction',   "correction: {OWNER}'s {R} is a {V}."),
    ('correction',   "a correction: {OWNER}'s {R} is a {V}."),
    ('correction',   "small correction: {OWNER}'s {R} is a {V}."),
    ('scratch',      "scratch that, {OWNER}'s {R} is a {V}."),
    ('scratch',      "forget that, {OWNER}'s {R} is a {V}."),
    ('scratch',      "ignore that, {OWNER}'s {R} is a {V}."),
    ('i_meant',      "i meant that {OWNER}'s {R} is a {V}."),
    ('i_meant',      "i meant to say that {OWNER}'s {R} is a {V}."),
    ('i_meant',      "what i meant was that {OWNER}'s {R} is a {V}."),
    ('was_wrong',    "i was wrong, {OWNER}'s {R} is a {V}."),
    ('was_wrong',    "that was wrong, {OWNER}'s {R} is a {V}."),
    ('was_wrong',    "i made a mistake, {OWNER}'s {R} is a {V}."),
    ('let_me_fix',   "let me fix that: {OWNER}'s {R} is a {V}."),
    ('let_me_fix',   "let me change that: {OWNER}'s {R} is a {V}."),
    ('let_me_fix',   "please change that: {OWNER}'s {R} is a {V}."),
    ('update',       "update: {OWNER}'s {R} is a {V}."),
    ('update',       "an update: {OWNER}'s {R} is a {V}."),
    ('update',       "change it: {OWNER}'s {R} is a {V}."),
    ('not_old',      "{OWNER}'s {R} is not a {OLD}, it is a {V}."),
    ('not_old',      "{OWNER}'s {R} is not a {OLD}; it is a {V}."),
    ('not_old',      "{OWNER}'s {R} is not a {OLD} but a {V}."),
    ('not_old',      "actually, {OWNER}'s {R} is not a {OLD}, it is a {V}."),
    ('not_old',      "no, {OWNER}'s {R} is not a {OLD}, it is a {V}."),
    ('not_old',      "sorry, {OWNER}'s {R} is not a {OLD}, it is a {V}."),
    ('not_old',      "{OWNER}'s {R} is no longer a {OLD}, it is a {V}."),
    ('not_old',      "{OWNER} does not have a {OLD} as a {R}, {OWNER} has a {V}."),
    ('not_old',      "correction: {OWNER}'s {R} is not a {OLD}, it is a {V}."),
    ('not_old',      "update: {OWNER}'s {R} is not a {OLD}, it is a {V}."),
    ('not_old',      "i was wrong, {OWNER}'s {R} is not a {OLD}, it is a {V}."),
    ('now_instead',  "{OWNER}'s {R} is a {V} now, i corrected that."),
    ('now_instead',  "{OWNER}'s {R} is a {V} instead."),
    ('now_instead',  "make {OWNER}'s {R} a {V} instead."),
    ('now_instead',  "change {OWNER}'s {R} to a {V}."),
    ('now_instead',  "please change {OWNER}'s {R} to a {V}."),
    ('now_instead',  "set {OWNER}'s {R} to a {V}."),
    ('actually_of',  "actually, {OWNER} was given a {V} as a {R}."),
    ('actually_of',  "actually, a {V} is {OWNER}'s {R}."),
    ('actually_of',  "no, a {V} is {OWNER}'s {R}."),
    ('actually_of',  "sorry, the {R} of {OWNER_OF} is a {V}."),
]

CORRECT_LINK = [
    ('actually',     "actually, {OWNER}'s {R} is {O}."),
    ('actually',     "actually {OWNER}'s {R} is {O}."),
    ('actually',     "actually, the {R} of {OWNER_OF} is {O}."),
    ('actually',     "actually, {OWNER} has {O} as a {R}."),
    ('actually',     "actually, {OWNER} got {O} as a {R}."),
    ('no_comma',     "no, {OWNER}'s {R} is {O}."),
    ('no_comma',     "no, the {R} of {OWNER_OF} is {O}."),
    ('no_comma',     "no, {OWNER} has {O} as a {R}."),
    ('sorry',        "sorry, {OWNER}'s {R} is {O}."),
    ('sorry',        "sorry, i was wrong: {OWNER}'s {R} is {O}."),
    ('sorry',        "oops, {OWNER}'s {R} is {O}."),
    ('correction',   "correction: {OWNER}'s {R} is {O}."),
    ('correction',   "a correction: {OWNER}'s {R} is {O}."),
    ('correction',   "small correction: {OWNER}'s {R} is {O}."),
    ('scratch',      "scratch that, {OWNER}'s {R} is {O}."),
    ('scratch',      "forget that, {OWNER}'s {R} is {O}."),
    ('scratch',      "ignore that, {OWNER}'s {R} is {O}."),
    ('i_meant',      "i meant that {OWNER}'s {R} is {O}."),
    ('i_meant',      "i meant to say that {OWNER}'s {R} is {O}."),
    ('i_meant',      "what i meant was that {OWNER}'s {R} is {O}."),
    ('was_wrong',    "i was wrong, {OWNER}'s {R} is {O}."),
    ('was_wrong',    "that was wrong, {OWNER}'s {R} is {O}."),
    ('was_wrong',    "i made a mistake, {OWNER}'s {R} is {O}."),
    ('let_me_fix',   "let me fix that: {OWNER}'s {R} is {O}."),
    ('let_me_fix',   "let me change that: {OWNER}'s {R} is {O}."),
    ('let_me_fix',   "please change that: {OWNER}'s {R} is {O}."),
    ('update',       "update: {OWNER}'s {R} is {O}."),
    ('update',       "an update: {OWNER}'s {R} is {O}."),
    ('update',       "change it: {OWNER}'s {R} is {O}."),
    ('not_old',      "{OWNER}'s {R} is not {OLD}, it is {O}."),
    ('not_old',      "{OWNER}'s {R} is not {OLD}; it is {O}."),
    ('not_old',      "{OWNER}'s {R} is not {OLD} but {O}."),
    ('not_old',      "actually, {OWNER}'s {R} is not {OLD}, it is {O}."),
    ('not_old',      "no, {OWNER}'s {R} is not {OLD}, it is {O}."),
    ('not_old',      "sorry, {OWNER}'s {R} is not {OLD}, it is {O}."),
    ('not_old',      "{OWNER}'s {R} is no longer {OLD}, it is {O}."),
    ('not_old',      "{OWNER} does not have {OLD} as a {R}, {OWNER} has {O}."),
    ('not_old',      "correction: {OWNER}'s {R} is not {OLD}, it is {O}."),
    ('not_old',      "update: {OWNER}'s {R} is not {OLD}, it is {O}."),
    ('not_old',      "i was wrong, {OWNER}'s {R} is not {OLD}, it is {O}."),
    ('now_instead',  "{OWNER}'s {R} is {O} now, i corrected that."),
    ('now_instead',  "{OWNER}'s {R} is {O} instead."),
    ('now_instead',  "make {OWNER}'s {R} {O} instead."),
    ('now_instead',  "change {OWNER}'s {R} to {O}."),
    ('now_instead',  "please change {OWNER}'s {R} to {O}."),
    ('now_instead',  "set {OWNER}'s {R} to {O}."),
    ('actually_of',  "actually, {OWNER} was given {O} as a {R}."),
    ('actually_of',  "actually, {O} is {OWNER}'s {R}."),
    ('actually_of',  "no, {O} is {OWNER}'s {R}."),
    ('actually_of',  "sorry, the {R} of {OWNER_OF} is {O}."),
]

# ------------------------------------------------------------------ questions with no path
# Section 4.4 case 3: an ASK whose relation path is EMPTY -- a question about the world that
# nothing in the notebook could ever answer.  Every one of these carries a world-knowledge
# marker the parser also holds, because the only surface difference between "what is the
# capital of france?" and "what is your favourite colour?" is the marker.  No capitalised
# word appears here, so nothing is ever read as a name.

ASK_NONE = [
    ('capital',   "what is the capital of france?"),
    ('capital',   "what is the capital of japan?"),
    ('capital',   "what is the capital of peru?"),
    ('capital',   "what is the capital of kenya?"),
    ('capital',   "do you know the capital of spain?"),
    ('capital',   "can you tell me the capital of italy?"),
    ('invented',  "who invented the telephone?"),
    ('invented',  "who invented the printing press?"),
    ('invented',  "who invented the light bulb?"),
    ('invented',  "who discovered america?"),
    ('invented',  "who wrote that famous play?"),
    ('invented',  "who painted that famous picture?"),
    ('howfar',    "how far is the moon?"),
    ('howfar',    "how far is it to the sea?"),
    ('howfar',    "how tall is the tallest mountain?"),
    ('howfar',    "how deep is the ocean?"),
    ('howfar',    "how big is the sun?"),
    ('howfar',    "how old is the earth?"),
    ('howmany',   "how many people live in the world?"),
    ('howmany',   "how many bones are in a body?"),
    ('howmany',   "how many countries are there?"),
    ('howmany',   "how many stars are in the sky?"),
    ('whenwas',   "when was the war?"),
    ('whenwas',   "when did the first plane fly?"),
    ('whenwas',   "when was that king born?"),
    ('whenwas',   "what year did that happen?"),
    ('whyis',     "why is the sky blue?"),
    ('whyis',     "why is the sea salty?"),
    ('whyis',     "why do birds fly south?"),
    ('whyis',     "why does the moon change shape?"),
    ('whatis',    "what is the largest animal?"),
    ('whatis',    "what is the fastest animal?"),
    ('whatis',    "what is the longest river?"),
    ('whatis',    "what is the smallest country?"),
    ('whatis',    "what is the boiling point of water?"),
    ('whatis',    "what is the speed of light?"),
    ('spell',     "how do you spell that long word?"),
    ('spell',     "what does that long word mean?"),
    ('maths',     "what is seven times eight?"),
    ('maths',     "what is the square root of nine?"),
    ('news',      "what is in the news today?"),
    ('news',      "what is the weather tomorrow?"),
    ('news',      "who won the game last night?"),
    ('news',      "what time does the shop close?"),
    ('recipe',    "how do you bake bread?"),
    ('recipe',    "how do you fix a bike?"),
    ('recipe',    "how does an engine work?"),
    ('recipe',    "how does a plane stay up?"),
    ('history',   "what happened in the last century?"),
    ('history',   "who was the first person on the moon?"),
]

CHAT_NONE = [
    ('greeting',  "hi!"),
    ('greeting',  "hello!"),
    ('greeting',  "hey there."),
    ('greeting',  "good morning."),
    ('greeting',  "good evening."),
    ('greeting',  "i am back."),
    ('howareyou', "how are you?"),
    ('howareyou', "how are you today?"),
    ('howareyou', "how is it going?"),
    ('howareyou', "are you ok?"),
    ('howareyou', "how was your day?"),
    ('howareyou', "what are you doing?"),
    ('mystate',   "i am fine."),
    ('mystate',   "i am tired today."),
    ('mystate',   "i am happy today."),
    ('mystate',   "i am a bit bored."),
    ('mystate',   "i am hungry."),
    ('mystate',   "i had a long day."),
    ('didtoday',  "i went to the park today."),
    ('didtoday',  "i walked to school this morning."),
    ('didtoday',  "i read a book last night."),
    ('didtoday',  "i played outside after lunch."),
    ('didtoday',  "we had pizza for dinner."),
    ('didtoday',  "i watched the rain for a while."),
    ('didtoday',  "i cleaned my room today."),
    ('didtoday',  "i helped in the garden."),
    ('ilike',     "i like dogs."),
    ('ilike',     "i like cats."),
    ('ilike',     "i like the rain."),
    ('ilike',     "i like long walks."),
    ('ilike',     "i do not like the cold."),
    ('ilike',     "i love the summer."),
    ('youlike',   "do you like dogs?"),
    ('youlike',   "do you like the rain?"),
    ('youlike',   "what do you like?"),
    ('youlike',   "what is your favourite colour?"),
    ('youlike',   "do you sleep at night?"),
    ('youlike',   "can you see me?"),
    ('reaction',  "that sounds fun."),
    ('reaction',  "that is nice."),
    ('reaction',  "that is funny."),
    ('reaction',  "that is sad."),
    ('reaction',  "ok, thanks."),
    ('reaction',  "thank you."),
    ('closing',   "i have to go now."),
    ('closing',   "talk to you later."),
    ('closing',   "good night."),
    ('closing',   "see you tomorrow."),
    ('weather',   "it is raining here."),
    ('weather',   "it is very sunny today."),
]

# UNCLEAR: exactly the three cases of section 4.2 -- pronoun subjects, two facts in one
# sentence, gibberish.  `{P}` is a pronoun, `{G}` a gibberish token; `{OWNER}` / `{O}` /
# `{V}` / `{R}` fill as usual for the two-facts case.  The gold label is always
# act = UNCLEAR with no subject, no path and no object.
UNCLEAR_NONE = [
    ('pronoun',   "what is {P} {R}?"),
    ('pronoun',   "who is {P} {R}?"),
    ('pronoun',   "{P} {R} is a {V}."),
    ('pronoun',   "{P} {R} is {O}."),
    ('pronoun',   "tell me {P} {R}."),
    ('pronoun',   "do you know {P} {R}?"),
    ('pronoun',   "what about {P} {R}?"),
    ('pronoun',   "{P} {R}?"),
    ('pronoun',   "actually {P} {R} is a {V}."),
    ('pronoun',   "i forget {P} {R}."),
    ('pronoun',   "can you tell me {P} {R}?"),
    ('pronoun',   "remind me of {P} {R}."),
    ('pronoun',   "the {R} of {P} friend is a {V}."),
    ('pronoun',   "what did {P} friend get as a {R}?"),
    ('pronoun',   "{P} {R} turned out to be a {V}."),
    ('ellipsis',  "actually it is a {V} now."),
    ('ellipsis',  "actually it is {O} now."),
    ('ellipsis',  "no, it is a {V}."),
    ('ellipsis',  "it is a {V}, not what i said."),
    ('ellipsis',  "change it to a {V}."),
    ('ellipsis',  "make it {O} instead."),
    ('ellipsis',  "that one is a {V}."),
    ('ellipsis',  "the other one is {O}."),
    ('twofacts',  "{OWNER}'s {R} is a {V} and {O2}'s {R2} is a {V2}."),
    ('twofacts',  "{OWNER}'s {R} is a {V}, {O2}'s {R2} is a {V2}."),
    ('twofacts',  "{OWNER}'s {R} is a {V} and {O2} has a {V2} as a {R2}."),
    ('twofacts',  "{OWNER} got a {V} as a {R} and {O2} got a {V2} as a {R2}."),
    ('twofacts',  "both {OWNER}'s {R} and {O2}'s {R2} are a {V}."),
    ('twofacts',  "{OWNER}'s {R} is a {V}; also {O2}'s {R2} is a {V2}."),
    ('twofacts',  "write down {OWNER}'s {R} as a {V} and {O2}'s {R2} as a {V2}."),
    ('twofacts',  "what are {OWNER}'s {R} and {O2}'s {R2}?"),
    ('noowner',   "the {R} is a {V}."),
    ('noowner',   "what is the {R}?"),
    ('noowner',   "the {R} is {O}."),
    ('noowner',   "tell me the {R}."),
    ('noowner',   "a {V} is the {R}."),
    ('noowner',   "who is the {R}?"),
    ('gibberish', "{G}"),
    ('gibberish', "{G} {G}."),
    ('gibberish', "what is {G}?"),
    ('gibberish', "{G} is a {V}."),
    ('gibberish', "{OWNER}'s {G} is a {V}."),
    ('gibberish', "the {G} of {OWNER} is a {V}."),
    ('gibberish', "{G} {G} {G}?"),
    ('gibberish', "tell me about {G}."),
    ('gibberish', "{G}, please."),
    ('gibberish', "i think {G}."),
    ('gibberish', "{G} {R} {V}."),
    ('gibberish', "do you know {G}?"),
    ('gibberish', "{G}!"),
]

FAMILIES = {
    'tell.attr': TELL_ATTR,
    'tell.link': TELL_LINK,
    'ask.attr': ASK_ATTR,
    'ask.link': ASK_LINK,
    'correct.attr': CORRECT_ATTR,
    'correct.link': CORRECT_LINK,
    'ask.none': ASK_NONE,
    'chat.none': CHAT_NONE,
    'unclear.none': UNCLEAR_NONE,
}

FACT_FAMILIES = ('tell.attr', 'tell.link', 'ask.attr', 'ask.link',
                 'correct.attr', 'correct.link')

# --------------------------------------------------------------------- openers and closers
# Section 4.2: 12 openers x 8 closers; L2 holds out 2 openers and 2 closers.
OPENERS = ['ok, ', 'so, ', 'by the way, ', 'hey, ', 'right, ', 'well, ',
           'anyway, ', 'oh, ', 'listen, ', 'um, ', 'alright, ', 'hmm, ']
CLOSERS = [', ok?', ', please remember that.', ', got it?', ', if you can.',
           ', thanks.', ', please.', ', alright?', ', write that down.']

# --------------------------------------------------------------------------- surface noise
# Every op is either length preserving or changes only the final character, so a character
# span computed before the op is still correct after it (except spans that would touch the
# final full stop, and no slot ever does).
NOISE_OPS = ('none', 'drop_period', 'bang', 'ellipsis', 'capitalise_start', 'upper_i',
             'capitalise_start+upper_i')
NOISE_WEIGHTS = (.46, .12, .07, .05, .14, .08, .08)

PRONOUNS = ('his', 'her', 'their', 'its')
GIBBERISH = ('brklt', 'zzqx', 'pflmn', 'kthrz', 'wmbkl', 'xtnpr', 'gbrtz', 'vlkth',
             'mprkl', 'tzqvn', 'shrkt', 'dwnzl', 'frtkm', 'plnxg', 'kvrtb', 'jmwqz')


# ----------------------------------------------------------------------------- frame table

class Frame:
    """One core frame.  `id` is `<family>.<position>` and is the sealed identity."""

    __slots__ = ('id', 'family', 'construction', 'template', 'index')

    def __init__(self, family, index, construction, template):
        self.family, self.index = family, index
        self.construction, self.template = construction, template
        self.id = f'{family}.{index:03d}'

    @property
    def act(self):
        return self.family.split('.')[0]

    @property
    def relation_kind(self):
        return self.family.split('.')[1]

    def __repr__(self):
        return f'Frame({self.id!r}, {self.template!r})'


def build_frames():
    out = {}
    for family, rows in FAMILIES.items():
        frames = [Frame(family, i, tag, template) for i, (tag, template) in enumerate(rows)]
        seen = {}
        for frame in frames:
            if frame.template in seen:
                raise ValueError(f'duplicate template in {family}: {frame.template!r}')
            seen[frame.template] = frame.id
        out[family] = frames
    return out


FRAMES = build_frames()
ALL_FRAMES = {frame.id: frame for frames in FRAMES.values() for frame in frames}


# -------------------------------------------------------------------- the sealed L1/L2 split

def _rank_key(namespace, item_id):
    return hashlib.sha256(f'{namespace}:{item_id}'.encode()).hexdigest()


def split_ids(item_ids, namespace, share=HELD_OUT_SHARE):
    """Deterministic rank split: the `share` lowest hashes are held out (L2).

    A rank split, not a threshold, so the held-out count is exact and does not drift when a
    frame is added.  Pure function of the ids and the namespace: no seed, no ordering, no
    file system, nothing about any model.
    """
    ranked = sorted(item_ids, key=lambda i: _rank_key(namespace, i))
    n_out = max(1, round(len(ranked)*share)) if ranked else 0
    held = set(ranked[:n_out])
    return sorted(i for i in item_ids if i in held), sorted(i for i in item_ids if i not in held)


def skeleton(template):
    """A template stripped of placeholders, punctuation and case: just its word sequence.

    "{OWNER}'s {R}: a {V}." and "{OWNER}'s {R} - a {V}." have the SAME skeleton.  They are
    different frames, but a model that has learned one has learned nearly all of the other,
    so holding one out and training on the other would make L2 look harder than it is.
    """
    bare = re.sub(r'\{[A-Z_0-9]+\}', ' ', template).lower()
    return ' '.join(re.findall(r"[a-z']+", bare))


def frame_split():
    """{family: {'L1': [ids], 'L2': [ids]}} plus the opener/closer split.

    The unit of the split is a frame, as the design says, EXCEPT that frames sharing a
    skeleton are kept together.  Without that, "{OWNER}'s {R}: a {V}." could be held out
    while "{OWNER}'s {R} - a {V}." was trained on, and the held-out set would contain a
    wording the model has already seen in all but its punctuation.
    """
    out = {}
    for family, frames in FRAMES.items():
        groups = {}
        for frame in frames:
            groups.setdefault(skeleton(frame.template), []).append(frame.id)
        held_groups, _ = split_ids(sorted(groups), f'{SPLIT_NAMESPACE}:{family}')
        held = sorted(i for key in held_groups for i in groups[key])
        kept = sorted(f.id for f in frames if f.id not in set(held))
        out[family] = dict(L2=held, L1=kept)
    opener_ids = [f'op.{i:02d}' for i in range(len(OPENERS))]
    closer_ids = [f'cl.{i:02d}' for i in range(len(CLOSERS))]
    held_o, kept_o = split_ids(opener_ids, f'{SPLIT_NAMESPACE}:openers', 2/len(OPENERS))
    held_c, kept_c = split_ids(closer_ids, f'{SPLIT_NAMESPACE}:closers', 2/len(CLOSERS))
    out['openers'] = dict(L2=held_o, L1=kept_o)
    out['closers'] = dict(L2=held_c, L1=kept_c)
    return out


SPLIT = frame_split()


def frames_for(family, level):
    """The core frames a given wording level may use.  L3 uses no generated frame at all."""
    if level == 'L3':
        return []
    return [ALL_FRAMES[i] for i in SPLIT[family][level]]


def openers_for(level):
    return [(i, OPENERS[int(i.split('.')[1])]) for i in SPLIT['openers'][level]]


def closers_for(level):
    return [(i, CLOSERS[int(i.split('.')[1])]) for i in SPLIT['closers'][level]]


def construction_report():
    """Per family: how many L2 frames use a construction that no L1 frame uses.

    This is the honest measure of how new the held-out wordings are.  A by-frame split
    (which is what section 4.2 specifies) can hand L2 a frame that differs from a training
    frame only in its lead-in; this number says how often it does better than that.
    """
    report = {}
    for family, frames in FRAMES.items():
        by_id = {f.id: f for f in frames}
        l1 = {by_id[i].construction for i in SPLIT[family]['L1']}
        l2_ids = SPLIT[family]['L2']
        novel = [i for i in l2_ids if by_id[i].construction not in l1]
        report[family] = dict(
            n_frames=len(frames), n_l1=len(SPLIT[family]['L1']), n_l2=len(l2_ids),
            n_constructions=len({f.construction for f in frames}),
            l2_construction_novel=len(novel), novel_ids=novel,
            novel_constructions=sorted({by_id[i].construction for i in novel}))
    return report


def frame_table_sha256():
    """One hash over every frame string, in sealed order.  Changes if any frame changes."""
    digest = hashlib.sha256()
    digest.update(FORMAT.encode())
    for family in sorted(FAMILIES):
        for frame in FRAMES[family]:
            digest.update(f'\n{frame.id}\t{frame.construction}\t{frame.template}'.encode())
    for i, text in enumerate(OPENERS):
        digest.update(f'\nop.{i:02d}\t{text}'.encode())
    for i, text in enumerate(CLOSERS):
        digest.update(f'\ncl.{i:02d}\t{text}'.encode())
    return digest.hexdigest()
