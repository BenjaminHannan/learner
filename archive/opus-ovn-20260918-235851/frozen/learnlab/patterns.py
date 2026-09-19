"""Village v0 vocabulary and sentence-pattern banks (design/05-village-v0.md).

The simulator renders every event, rule, teacher act and question by filling a
sentence pattern. Two local writer models propose patterns; a pattern is kept
only if it passes `check_pattern` (exact placeholders, no fact words outside
them) and the other writer agrees it means exactly the bank's gloss. Patterns
are "mechanically verified transformations" in the reliability order, so they
must never add a fact of their own.

Placeholder rendering (used by prompts, the cross-check and the simulator):
  {person} {person_b} {leader} {giver} {receiver}  a made-up name: "Kelo"
  {object}          "the red cup"      {place} {place2}  "the mill"
  {container}       "the chest"        {time}            "night" (a bare word)
  {material}        "glass"            {category}        "dishes"
  {colour}          "green"            {count}           "two"
  {object_kind}     "cups" (plural)    {item}            "a lamp"
  {action}          a past-tense clause without final punctuation: "Rami dropped the cup"
  {fact} {correction} {rule} {event}  one full sentence with final punctuation
  {question}        one full question ending in "?"

Stdlib only (the Bonsai venv has no torch).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import random
import re
from typing import Any, Iterable, Mapping, Optional, Sequence

from learnlab.splits import FamilyManifest, SplitManifest, assign_ranked, hash_canary

# ---------------------------------------------------------------- vocabulary

PLACES = (
    "barn", "mill", "well", "market", "bakery", "bridge", "pond", "orchard", "field", "garden",
    "forest", "river", "hill", "farm", "shop", "school", "tower", "gate", "square", "stable",
    "dock", "beach", "cave", "meadow", "lake", "fountain", "library", "inn", "shed", "workshop",
    "harbour", "castle", "cottage", "hut", "quarry", "smithy", "dairy", "lighthouse", "playground", "hall",
)
# noun -> (plural, category)
OBJECT_INFO: Mapping[str, tuple[str, str]] = {
    "cup": ("cups", "dishes"), "plate": ("plates", "dishes"), "bowl": ("bowls", "dishes"),
    "spoon": ("spoons", "dishes"), "fork": ("forks", "dishes"), "jug": ("jugs", "dishes"),
    "mug": ("mugs", "dishes"), "pot": ("pots", "dishes"), "pan": ("pans", "dishes"),
    "kettle": ("kettles", "dishes"), "teapot": ("teapots", "dishes"), "ladle": ("ladles", "dishes"),
    "key": ("keys", "tools"), "rope": ("ropes", "tools"), "hammer": ("hammers", "tools"),
    "brush": ("brushes", "tools"), "shovel": ("shovels", "tools"), "rake": ("rakes", "tools"),
    "broom": ("brooms", "tools"), "lamp": ("lamps", "tools"), "bucket": ("buckets", "tools"),
    "ladder": ("ladders", "tools"), "needle": ("needles", "tools"), "axe": ("axes", "tools"),
    "hat": ("hats", "clothes"), "scarf": ("scarves", "clothes"), "coat": ("coats", "clothes"),
    "boot": ("boots", "clothes"), "glove": ("gloves", "clothes"), "sock": ("socks", "clothes"),
    "shirt": ("shirts", "clothes"), "cloak": ("cloaks", "clothes"), "apron": ("aprons", "clothes"),
    "belt": ("belts", "clothes"), "mitten": ("mittens", "clothes"), "shawl": ("shawls", "clothes"),
    "ball": ("balls", "toys"), "doll": ("dolls", "toys"), "kite": ("kites", "toys"),
    "drum": ("drums", "toys"), "whistle": ("whistles", "toys"), "puppet": ("puppets", "toys"),
    "rattle": ("rattles", "toys"), "flute": ("flutes", "toys"), "hoop": ("hoops", "toys"),
    "bell": ("bells", "toys"), "balloon": ("balloons", "toys"), "sled": ("sleds", "toys"),
    "apple": ("apples", "food"), "pear": ("pears", "food"), "loaf": ("loaves", "food"),
    "cake": ("cakes", "food"), "egg": ("eggs", "food"), "cheese": ("cheeses", "food"),
    "carrot": ("carrots", "food"), "plum": ("plums", "food"), "pie": ("pies", "food"),
    "onion": ("onions", "food"), "potato": ("potatoes", "food"), "melon": ("melons", "food"),
}
OBJECTS = tuple(OBJECT_INFO)
OBJECT_PLURALS = tuple(plural for plural, _ in OBJECT_INFO.values())
PLURAL: Mapping[str, str] = {noun: plural for noun, (plural, _) in OBJECT_INFO.items()}
CATEGORY: Mapping[str, str] = {noun: category for noun, (_, category) in OBJECT_INFO.items()}
CATEGORIES = ("dishes", "tools", "clothes", "toys", "food")
MATERIALS = ("glass", "wood", "iron", "cloth", "clay", "stone")
COLOURS = ("red", "blue", "green", "yellow", "white", "black", "brown", "grey")
CONTAINERS = ("box", "basket", "chest", "sack")
TIMES = ("morning", "noon", "evening", "night")
DIRECTIONS = ("north", "south", "east", "west")
NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
    "nineteen", "twenty",
)
STYLES = ("plain", "cheerful", "terse", "storyteller", "formal", "questioning", "childlike", "grandparent", "bossy", "poetic")
STYLE_HINTS: Mapping[str, str] = {
    "plain": "plain and simple",
    "cheerful": "cheerful and warm",
    "terse": "very short and to the point",
    "storyteller": "like someone telling a story",
    "formal": "polite and formal",
    "questioning": "curious, using a gentle question to lead in",
    "childlike": "like a young child talking",
    "grandparent": "like a kind, patient grandparent",
    "bossy": "bossy, giving firm orders",
    "poetic": "a little poetic, with a gentle rhythm",
}
FLAVOURS: Mapping[str, str] = {
    "plain": "short and plain",
    "manner": "add one harmless manner word such as slowly, quickly, quietly or carefully",
    "connector": "start with a connector such as Then, After that, Soon or Next",
    "verb": "use a different verb than the most obvious one",
    "passive": "use the passive voice where it sounds natural",
    "longer": "a slightly longer sentence that still adds no facts",
}


def _plural(word: str) -> str:
    if word.endswith(("s", "x", "ch", "sh")):
        return word + "es"
    if word.endswith("y") and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


# ------------------------------------------------------- forbidden word lists

# label -> words; every vocab word is banned outside placeholders in every bank.
VOCAB_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("place word", PLACES + tuple(_plural(p) for p in PLACES)),
    ("object word", OBJECTS + OBJECT_PLURALS),
    ("category word", CATEGORIES),
    ("material word", MATERIALS),
    ("colour word", COLOURS),
    ("container word", CONTAINERS + tuple(_plural(c) for c in CONTAINERS)),
    ("direction word", DIRECTIONS),
    ("number word", NUMBER_WORDS),
)
# The lists below are blocklists, so they cannot be complete: an open-class word ("bread",
# "slept", a lowercase name) still gets through, and only the cross-check can catch it.

# Words that name a time of day: the {time} slot supplies it, so they are banned outside ev.new_day.
TIME_OF_DAY_WORDS = TIMES + tuple(t + "s" for t in TIMES) + (
    "dawn", "dusk", "midnight", "midday", "afternoon", "afternoons", "sunrise", "sunset", "tonight",
    "sun", "moon", "dark", "darkness", "daylight", "daytime", "nighttime",
    "breakfast", "lunch", "supper", "dinner", "teatime", "bedtime",
)
# Banned outside ev.new_day; the daily rules (R3, R4, R7) may say "day".
GENERIC_TIME_WORDS = (
    "day", "days", "daily", "today", "yesterday", "tomorrow", "early", "late", "later", "earlier", "moment",
)
CLOCK_WORDS = ("time", "times")  # fine next to a {time} slot, a fact elsewhere ("for the first time")
# Spans and dates the world never uses: banned everywhere, ev.new_day included ("A new week began").
CALENDAR_WORDS = (
    "week", "weeks", "hour", "hours", "minute", "minutes", "month", "months", "year", "years", "clock",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "weekend", "weekday",
    "spring", "summer", "autumn", "winter", "season", "seasons", "birthday", "holiday", "festival",
)
GENDERED_PRONOUNS = ("he", "she", "him", "her", "his", "hers", "himself", "herself")
PEOPLE_WORDS = (
    "friend", "friends", "brother", "sister", "mother", "father", "mum", "dad", "family", "neighbour",
    "neighbor", "child", "children", "man", "men", "woman", "women", "boy", "boys", "girl", "girls",
    "kid", "kids", "baby", "lady", "stranger", "someone", "somebody", "everyone", "everybody",
    "anyone", "anybody", "nobody", "people", "villager", "villagers",
    "others", "pal", "pals", "buddy", "crowd", "guest", "guests", "visitor", "visitors", "teacher",
    "farmer", "baker", "miller", "smith", "shepherd", "king", "queen", "guard", "guards", "mayor",
    "grandma", "grandpa", "granny", "grandmother", "grandfather", "aunt", "uncle", "cousin", "son",
    "daughter", "wife", "husband", "parent", "parents", "mom", "mama", "papa", "sir",
    # company words: "went alone" is false when a follower (R2) came along
    "alone", "together", "themself", "themselves",
)
# Universal quantifiers: rule banks may use them ("Anything made of {material} ...").
QUANTITY_WORDS = (
    "all", "every", "both", "each", "once", "anything", "everything", "something", "whatever",
    "everywhere", "anywhere", "any", "only", "other", "another", "else", "thing", "things", "stuff",
    "item", "items", "object", "objects", "whoever", "whichever",
)
# Partial or comparative amounts: banned everywhere ("Some things made of {material} break").
PARTIAL_WORDS = (
    "several", "many", "few", "some", "most", "none", "twice", "pair", "dozen", "half", "somewhere",
    "more", "less", "least", "fewer", "extra", "rest", "lot", "lots", "plenty", "enough",
)
EXTRA_NUMBER_WORDS = (
    "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "hundreds", "thousand",
    "thousands", "million", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
    "tenth", "thrice", "single", "double", "triple", "couple", "pairs", "dozens", "halves", "quarter",
)
NEGATION_WORDS = ("not", "never", "no", "nothing", "cannot", "nowhere", "neither", "nor", "nope")
SPEAKER_WORDS = (
    "i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
)
HOME_WORDS = ("home",)
# Words that point at an earlier or repeated event ("went back", "the same cup").
HISTORY_WORDS = (
    "back", "again", "also", "too", "still", "same", "different", "first", "last", "already", "before",
    "ago", "ever", "forever", "anymore", "previous", "previously", "usual", "used", "return", "returns",
    "returned", "returning",
)
FREQUENCY_WORDS = (
    "always", "usually", "often", "sometimes", "rarely", "seldom", "mostly", "normally", "generally", "occasionally",
)
HEDGE_WORDS = (
    "maybe", "perhaps", "probably", "possibly", "might", "almost", "nearly", "hardly", "barely", "likely",
    "unlikely", "seem", "seems", "seemed", "apparently", "somehow", "unless", "except", "besides",
)
# Teacher statements: a doubt or a denial around {fact} changes what the learner is told.
DOUBT_WORDS = (
    "false", "untrue", "lie", "lies", "lying", "joke", "joking", "kidding", "fake", "wrong", "incorrect",
    "mistake", "think", "thinks", "thought", "guess", "believe", "believes", "suppose", "heard",
    "rumour", "rumor", "forget", "forgot", "ignore",
)
# t.wrong must say the answer was wrong; rule.R6 must say only that person can.
WRONG_MARKER = re.compile(r"\b(wrong|incorrect|mistake|not|no|nope|oops)\b|n't\b")
EXCLUSIVE_MARKER = re.compile(r"\b(only|alone|nobody|none|no one|no other|no body)\b")
_EVERY_OTHER = re.compile(r"\bevery other\b", re.IGNORECASE)
OWNERSHIP_WORDS = ("own", "owns", "owned", "owner", "owners", "belong", "belongs", "belonged", "whose", "theirs")
# States and properties of things or people that the world does not track.
PROPERTY_WORDS = (
    "big", "bigger", "small", "smaller", "little", "tiny", "large", "huge", "heavy", "light", "hot", "cold",
    "warm", "cool", "wet", "dry", "old", "new", "young", "locked", "unlocked", "stuck", "full", "empty",
    "dirty", "clean", "shiny", "sharp", "long", "short", "tall", "round", "pretty", "beautiful", "ugly",
    "favourite", "favorite", "happy", "sad", "tired", "hungry", "thirsty", "angry", "scared", "afraid",
    "sleepy", "sick", "ill", "excited", "lonely", "friendly", "busy", "poor", "brave", "clever", "strong",
    "weak", "rich", "lazy", "bright", "quiet", "noisy",
)
# Events other than the bank's own ("put it down and it broke", "the stolen cup").
EVENT_WORDS = (
    "lost", "lose", "loses", "losing", "missing", "hid", "hide", "hides", "hidden", "hiding", "stole",
    "steal", "steals", "stolen", "sold", "sell", "sells", "bought", "buy", "buys", "pay", "paid", "borrow",
    "borrowed", "lend", "lent", "broke", "break", "breaks", "broken", "cracked", "smashed", "shattered",
    "fell", "fall", "falls", "spilled", "spilt", "burned", "burnt", "melted",
)
BREAK_WORDS = ("broke", "break", "breaks", "broken", "cracked", "smashed", "shattered")
TRADE_WORDS = ("sold", "sell", "sells", "bought", "buy", "buys", "pay", "paid")
# Narration, rules and questions: an attempt, a wish or a start is not the event itself.
ATTEMPT_WORDS = (
    "try", "tries", "tried", "trying", "attempt", "attempts", "attempted", "fail", "fails", "failed",
    "failing", "unable", "want", "wants", "wanted", "wish", "wished", "hope", "hoped", "plan", "plans",
    "planned", "decide", "decided", "refuse", "refused", "begin", "began", "begun", "begins", "start",
    "starts", "started", "stop", "stops", "stopped", "toward", "towards", "instead", "pretend", "pretended",
)
START_WORDS = ("begin", "began", "begun", "begins", "start", "starts", "started")
# Narration, rules and questions: reported speech or belief turns an event into a claim.
REPORT_WORDS = (
    "say", "says", "said", "tell", "tells", "told", "think", "thinks", "thought", "believe", "believes",
    "believed", "claim", "claims", "claimed", "dream", "dreams", "dreamed", "dreamt", "imagine", "imagined",
    "hear", "heard", "wonder", "wondered", "know", "knows", "knew", "remember", "remembered", "forget",
    "forgot", "forgotten", "guess", "guessed",
)
# Narration and rules: a modal turns an event into a possibility or a duty.
MODAL_WORDS = ("can", "could", "would", "will", "shall", "should", "must", "may")
_OTHER_NOUNS = (
    "dish", "tool", "toy", "road", "path", "street", "lane", "house", "room", "door", "table", "shelf",
    "floor", "tree", "wall", "window", "town", "city", "yard", "bench", "bed", "cart", "horse", "dog", "cat",
    "bird", "village", "mountain", "valley", "kitchen", "church", "palace", "store", "attic", "cellar",
    "stair", "bag", "coin", "book", "flower", "gift", "boat", "ship", "wagon", "car", "pet", "goat", "cow",
    "pig", "hen", "chicken", "duck", "storm",
)
# Common nouns and adjectives outside the vocab that would still add an untracked fact.
OTHER_FACT_WORDS = _OTHER_NOUNS + tuple(_plural(word) for word in _OTHER_NOUNS) + (
    "clothing", "woods", "sheep", "fish", "mouse", "mice", "gold", "golden", "silver", "pink", "orange",
    "purple", "violet", "gray", "metal", "wooden", "paper", "leather", "steel", "wool", "tin", "copper",
    "brass", "plastic", "rubber", "straw", "wicker", "fur", "silk", "cotton", "linen", "rain", "snow",
    "wind", "fog", "sunny", "cloudy", "windy", "rained", "raining", "snowed", "snowing", "sky", "grass", "water", "milk", "bread", "soup", "money",
    "sea", "ocean", "upstairs", "downstairs", "outside", "outdoors", "indoors", "nearby", "far", "abroad",
)
# Fail banks must say the attempt FAILED; "tried" alone does not ("tried to open it, and it opened").
FAILURE_OUTCOME = re.compile(
    r"\b(not|never|no|cannot|fail|fails|failed|unable|in vain|stuck|refused|gave up|without success|"
    r"(stayed|remained) (shut|closed|put|still))\b|n't\b"
)
NOT_ATTEMPTED = re.compile(r"\b(not|never)\s+(even\s+)?(try|tried|attempt|attempted)\b|n't\s+(even\s+)?(try|attempt)\b")
# Narration, rule and question sentences must start with a placeholder, an -ly adverb or one of
# these, so a made-up name or an extra state ("Mira and {person} ...", "Tired, {person} ...") cannot
# hide in the one position where capitals are allowed. Teacher lines are free here (cross-check).
STARTER_WORDS = frozenset((
    "the", "a", "an", "it", "its", "this", "that", "these", "those", "there", "here", "they", "their",
    "then", "next", "soon", "now", "so", "and", "but", "after", "before", "afterwards", "afterward", "meanwhile",
    "just", "right", "at", "in", "into", "inside", "on", "onto", "from", "to", "with", "by", "near",
    "over", "under", "up", "down", "out", "off", "away", "along", "across", "through", "past", "around",
    "behind", "beside", "between", "for", "of", "as", "while", "when", "whenever", "wherever", "if",
    "what", "which", "who", "where", "why", "how", "is", "are", "was", "were", "do", "does", "did",
    "has", "have", "had", "can", "could", "would", "will", "should", "tell", "no", "yes", "nobody", "none",
    # rule openers (their quantifier checks still apply)
    "whatever", "anything", "everything", "things", "all", "every", "each", "any", "only", "once", "lost",
    "left", "made", "put", "placed", "set", "given", "taken", "carried",
))

# ---------------------------------------------------------------- placeholders

PERSON_SLOTS = ("person", "person_b", "leader", "giver", "receiver")
SENTENCE_SLOTS = ("fact", "correction", "rule", "event", "question")
PLACEHOLDERS = PERSON_SLOTS + (
    "object", "place", "place2", "container", "time", "material", "category", "colour", "count",
    "object_kind", "item", "action", "direction",
) + SENTENCE_SLOTS
# Typical rendered length in words, for the word-count bounds.
PLACEHOLDER_WIDTH: Mapping[str, int] = {
    **{name: 1 for name in PLACEHOLDERS}, "object": 3, "place": 2, "place2": 2, "container": 2,
    "item": 2, "action": 4, **{name: 6 for name in SENTENCE_SLOTS},
}
PLACEHOLDER_HELP: Mapping[str, str] = {
    **{name: 'a made-up name like "Kelo"' for name in PERSON_SLOTS},
    "object": 'an object with "the", like "the red cup"',
    "place": 'a place with "the", like "the mill"', "place2": 'another place with "the", like "the barn"',
    "container": 'a container with "the", like "the chest"',
    "time": "one bare time word: morning, noon, evening or night (write so it reads well with each; not after at, in, on or the)",
    "material": 'a bare material word like "glass"', "category": 'a bare plural kind of thing like "dishes"',
    "colour": 'a bare colour word like "green"', "count": 'a number word like "two"',
    "object_kind": 'a bare plural noun like "cups"', "item": 'one object with "a", like "a lamp"',
    "action": 'a past-tense clause with no final punctuation, like "Rami dropped the cup"',
    "direction": "one bare direction word: north, south, east or west",
    "fact": "one full sentence with its own final punctuation", "correction": "one full sentence with its own final punctuation",
    "rule": "one full sentence with its own final punctuation", "event": "one full sentence with its own final punctuation",
    "question": 'one full question ending in "?"',
}
KINDS = ("narration", "rule", "teacher", "question")
WORD_BOUNDS: Mapping[str, tuple[int, int]] = {"narration": (3, 20), "question": (3, 20), "rule": (3, 24), "teacher": (1, 30)}
TARGETS: Mapping[str, int] = {"narration": 32, "rule": 20, "teacher": 10, "question": 20}  # teacher: per style
PER_REQUEST = 12
OVERSAMPLE = 1.8  # base round; topup rounds fill shortfalls at the observed yield
NEAR_DUPLICATE = 0.85

# ---------------------------------------------------------------------- banks


@dataclass(frozen=True)
class Bank:
    """One pattern bank. `placeholders` must each appear exactly once in every pattern."""

    kind: str
    placeholders: tuple[str, ...]
    gloss: str
    target: int
    flags: frozenset[str] = frozenset()  # negation, failure, time, any_time, quantifiers
    seeds: tuple[str, ...] = ()
    note: str = ""
    allow: frozenset[str] = field(default=frozenset())  # single words exempted from the bans


_SLOT = re.compile(r"\{([A-Za-z0-9_]*)\}")


def _bank(kind: str, gloss: str, seeds: Sequence[str], note: str = "", flags: Iterable[str] = (), allow: Iterable[str] = ()) -> Bank:
    return Bank(kind, tuple(_SLOT.findall(gloss)), gloss, TARGETS[kind], frozenset(flags), tuple(seeds), note, frozenset(allow))


_N, _R, _T, _Q = "narration", "rule", "teacher", "question"
_FAIL = ("negation", "failure")
_TIME_STARTERS = frozenset(TIME_OF_DAY_WORDS + GENERIC_TIME_WORDS + CLOCK_WORDS)
_DAILY = ("day", "days", "daily")
BANKS: Mapping[str, Bank] = {
    "ev.go": _bank(_N, "{person} went to {place}.", ["{person} walked to {place}.", "Then {person} went over to {place}."]),
    "ev.pick_up": _bank(_N, "{person} picked up {object}.", ["{person} lifted {object} up.", "Soon {person} picked {object} up."]),
    "ev.put_down": _bank(_N, "{person} put down {object} at {place}.", ["{person} left {object} at {place}.", "At {place}, {person} set {object} down."]),
    "ev.give": _bank(_N, "{giver} gave {object} to {receiver}.", ["{giver} handed {object} to {receiver}.", "{receiver} got {object} from {giver}."]),
    "ev.put_in": _bank(_N, "{person} put {object} in {container}.", ["{person} placed {object} inside {container}.", "Then {person} dropped {object} into {container}."]),
    "ev.take_out": _bank(_N, "{person} took {object} out of {container}.", ["{person} pulled {object} out of {container}.", "From {container}, {person} lifted out {object}."]),
    "ev.open": _bank(_N, "{person} opened {container}.", ["{person} opened up {container}.", "Slowly, {person} opened {container}."]),
    "ev.close": _bank(_N, "{person} closed {container}.", ["{person} shut {container}.", "Then {person} closed {container} tight."]),
    "ev.carry": _bank(_N, "{person} carried {container} to {place}.", ["{person} took {container} over to {place}.", "{person} brought {container} along to {place}."],
                      "the container and whatever is inside it move together", allow=("everything", "all", "things")),
    "ev.swap": _bank(_N, "{person} and {person_b} swapped what they were holding.", ["{person} and {person_b} traded what they held.", "{person} swapped things with {person_b}."],
                     "the two people exchange what they hold", allow=("each", "both", "other", "things", "together", "themselves")),
    "ev.time": _bank(_N, "It became {time}.", ["Soon it was {time}.", "Then {time} came."], "a time of day arrives", ("time",), START_WORDS + ("fell", "fall", "falls")),
    "ev.new_day": _bank(_N, "A new day began.", ["A new day started.", "Then the next day began."], "a new day begins", ("any_time",), START_WORDS + ("new", "again", "fell", "fall", "falls")),
    "ev.fail_open": _bank(_N, "{person} tried to open {container}, but it did not open.", ["{person} tried to open {container}, but it stayed shut.", "{person} could not open {container}."],
                          "the attempt FAILED; say so clearly", _FAIL),
    "ev.fail_pick_up": _bank(_N, "{person} tried to pick up {object}, but could not.", ["{person} tried to lift {object}, but it would not move.", "{person} was unable to pick up {object}."],
                             "the attempt FAILED; say so clearly", _FAIL),
    "ev.fail_put_in": _bank(_N, "{person} tried to put {object} in {container}, but could not.", ["{person} tried to put {object} into {container}, but it would not go in.", "{person} could not get {object} into {container}."],
                            "the attempt FAILED; say so clearly", _FAIL),
    "ev.breaks": _bank(_N, "{object} broke.", ["{object} broke into pieces.", "Then {object} cracked and broke."], allow=BREAK_WORDS),
    "ev.follows": _bank(_N, "{person} followed {leader} to {place}.", ["{person} went after {leader} to {place}.", "{leader} went to {place}, and {person} followed."]),
    "ev.moved_by_place": _bank(_N, "{object} was left at {place} and ended up at {place2}.", ["{object} left at {place} was moved to {place2}.", "{object}, left at {place}, ended up at {place2}."],
                               "the object had been left at the first place and is now at the second"),
    "ev.returned": _bank(_N, "{object} went back to its owner, {person}.", ["{object} found its way back to {person}, its owner.", "{object} returned to {person}, who owns it."],
                         allow=("back", "return", "returns", "returned") + OWNERSHIP_WORDS),
    "ev.recoloured": _bank(_N, "{object} turned {colour}.", ["{object} became {colour}.", "Slowly, {object} changed to {colour}."]),
    "ev.traded": _bank(_N, "{person} traded {count} {object_kind} for {item}.", ["{person} gave {count} {object_kind} and got {item}.", "{person} swapped {count} {object_kind} for {item}."], allow=TRADE_WORDS + ("return",)),
    "ev.intro_person": _bank(_N, "{person} is at {place}.", ["{person} is standing at {place}.", "At {place}, there is {person}."], "a scene description of how things are now"),
    "ev.intro_object": _bank(_N, "{object} is at {place}.", ["{object} lies at {place}.", "At {place}, there is {object}."], "a scene description of how things are now"),
    "ev.intro_in": _bank(_N, "{object} is in {container}.", ["{object} is inside {container}.", "Inside {container} is {object}."], "a scene description of how things are now"),
    "ev.intro_holds": _bank(_N, "{person} is holding {object}.", ["{person} has {object}.", "{person} holds {object}."], "a scene description of how things are now"),
    "ev.owner": _bank(_N, "{object} belongs to {person}.", ["{person} owns {object}.", "{object} is owned by {person}."], "a scene description of how things are now", allow=OWNERSHIP_WORDS),
    "ev.material": _bank(_N, "{object} is made of {material}.", ["{object} is made from {material}.", "{material} is what {object} is made of."], "a scene description of how things are now"),
    "ev.kind_group": _bank(_N, "{object_kind} are {category}.", ["{object_kind} are a kind of {category}.", "{object_kind} count as {category}."], "a general fact about kinds of things"),
    "ev.is_open": _bank(_N, "{container} is open.", ["{container} is standing open.", "{container} is open now."], "a scene description of how things are now"),
    "ev.is_closed": _bank(_N, "{container} is closed.", ["{container} is shut.", "{container} is closed now."], "a scene description of how things are now"),
    "ev.layout_dir": _bank(_N, "{place} is {direction} of {place2}.", ["{place} lies {direction} of {place2}.", "{place} sits {direction} of {place2}."], "a map fact: where one place is from another"),
    "ev.layout_next": _bank(_N, "{place} is next to {place2}.", ["{place} is beside {place2}.", "Right next to {place2} is {place}."], "a map fact: two places are neighbours"),
    "rule.R1_material": _bank(_R, "Things made of {material} break when they are put down.", ["Anything made of {material} breaks when it is put down.", "When things of {material} are set down, they break."], flags=("quantifiers",), allow=BREAK_WORDS),
    "rule.R1_category": _bank(_R, "{category} break when they are put down.", ["All {category} break when put down.", "If {category} are put down, they break."], flags=("quantifiers",), allow=BREAK_WORDS),
    "rule.R2": _bank(_R, "{person} always follows {leader}.", ["Wherever {leader} goes, {person} goes too.", "{person} goes wherever {leader} goes."], flags=("quantifiers",)),
    "rule.R3": _bank(_R, "Things left at {place} are moved to {place2} every {time}.", ["Anything left at {place} is taken to {place2} each {time}.", "Each {time}, whatever is left at {place} goes to {place2}."], flags=("quantifiers",), allow=_DAILY),
    "rule.R4": _bank(_R, "Lost things go back to their owners every {time}.", ["Each {time}, lost things return to their owners.", "Every {time}, anything lost finds its owner."], flags=("quantifiers",),
                     allow=_DAILY + OWNERSHIP_WORDS + ("lost", "lose", "missing", "back", "return", "returns", "returned")),
    "rule.R5": _bank(_R, "Things put in {container} turn {colour}.", ["Whatever goes in {container} turns {colour}.", "Anything placed in {container} becomes {colour}."], flags=("quantifiers",)),
    "rule.R6": _bank(_R, "Only {person} can open {container}.", ["{container} opens only for {person}.", "{container} can be opened by {person} and no other."], flags=("quantifiers", "negation"), allow=("may", "one", "nobody", "alone", "none")),
    "rule.R7": _bank(_R, "Every day, {person} goes to {place} when it is {time}.", ["{person} goes to {place} every {time}.", "Each day, when {time} comes, {person} goes to {place}."], flags=("quantifiers",), allow=_DAILY),
    "rule.R8": _bank(_R, "At {place}, {count} {object_kind} can be traded for {item}.", ["{count} {object_kind} buy {item} at {place}.", "At {place}, {count} {object_kind} can be swapped for {item}."], flags=("quantifiers",), allow=TRADE_WORDS),
    "t.state": _bank(_T, "Here is something true. {fact}", ["Listen. {fact}", "I will tell you something. {fact}"]),
    "t.remember": _bank(_T, "Remember this: {fact}", ["Please remember this. {fact}", "Keep this in your head: {fact}"], "ask the learner to remember it", allow=("later",)),
    "t.ask": _bank(_T, "Answer this question. {question}", ["Here is a question for you. {question}", "Can you tell me? {question}"]),
    "t.right": _bank(_T, "Your answer was right.", ["Yes, that is right.", "Good, you got it right."]),
    "t.wrong": _bank(_T, "Your answer was wrong. {correction}", ["No, that is not right. {correction}", "That is wrong. {correction}"],
                     "say the answer was wrong, then give the correction", ("negation",), ("wrong", "incorrect", "mistake")),
    "t.demo_intro": _bank(_T, "I will show you how this rule works. {rule}", ["Watch and learn this rule. {rule}", "Let me show you a rule. {rule}"]),
    "t.demo_step": _bank(_T, "Watch what happens next. {event}", ["Look. {event}", "Now see this. {event}"]),
    "t.demo_outro": _bank(_T, "That showed the rule. {rule}", ["So now you know the rule. {rule}", "You saw it work. {rule}"]),
    "t.change": _bank(_T, "Something has changed. {fact}", ["Things are different now. {fact}", "This is new. {fact}"], "say that something has changed, then state the new fact",
                      allow=("different", "anymore")),
    "t.quiz_later": _bank(_T, "Let me ask about something from earlier. {question}", ["Think back to before. {question}", "Let me ask you again. {question}"],
                          "ask again about something from earlier", allow=("again", "back", "before", "earlier", "later", "ago")),
    "q.where_object": _bank(_Q, "Where is {object}?", ["Where is {object} now?", "Can you tell me where {object} is?"]),
    "q.where_person": _bank(_Q, "Where is {person}?", ["Where is {person} now?", "Where has {person} gone?"]),
    "q.who_has": _bank(_Q, "Who has {object}?", ["Who is holding {object}?", "Who has {object} now?"]),
    "q.in_container": _bank(_Q, "What is in {container}?", ["What is inside {container}?", "What can be found in {container}?"]),
    "q.where_before": _bank(_Q, "Where was {object} before?", ["Where did {object} use to be?", "Before, where was {object}?"],
                              allow=("before", "earlier", "first", "previously", "ago")),
    "q.where_at_time": _bank(_Q, "Where was {object} when it was {time}?", ["When it was {time}, where was {object}?", "Where was {object} when {time} came?"]),
    "q.count_at": _bank(_Q, "How many {object_kind} are at {place}?", ["How many {object_kind} can be found at {place}?", "At {place}, how many {object_kind} are there?"], allow=("many",)),
    "q.count_held": _bank(_Q, "How many {object_kind} does {person} have?", ["How many {object_kind} is {person} holding?", "{person} has how many {object_kind}?"], allow=("many",)),
    "q.compare_count": _bank(_Q, "Which has more {object_kind}, {place} or {place2}?", ["Where are there more {object_kind}, at {place} or at {place2}?", "Which place has more {object_kind}, {place} or {place2}?"], allow=("many", "more", "fewer", "less")),
    "q.direction": _bank(_Q, "Which way is {place2} from {place}?", ["In which direction is {place2} from {place}?", "From {place}, which way do you go to reach {place2}?"], allow=("toward", "towards")),
    "q.next_to": _bank(_Q, "What is next to {place}?", ["What place is beside {place}?", "What is right next to {place}?"]),
    "q.what_if": _bank(_Q, "What would happen if {action}?", ["What happens if {action}?", "If {action}, what would happen?"]),
    "q.why_at": _bank(_Q, "Why is {object} at {place}?", ["How did {object} end up at {place}?", "Why is {object} now at {place}?"]),
    "q.plan_get": _bank(_Q, "How could {person} get {object}?", ["What could {person} do to get {object}?", "How can {person} get hold of {object}?"], allow=("plan", "try")),
    "q.rule_material": _bank(_Q, "What is the rule about things made of {material}?", ["What happens to things made of {material} here?", "What is the rule for {material} things?"]),
    "q.rule_category": _bank(_Q, "What is the rule about {category}?", ["What happens to {category} here?", "What rule is there for {category}?"]),
    "q.rule_person": _bank(_Q, "What is the rule about {person}?", ["What rule is there about {person}?", "What is special about {person}?"]),
    "q.rule_place": _bank(_Q, "What is the rule about {place}?", ["What rule is there for {place}?", "What is special about {place}?"]),
    "q.rule_container": _bank(_Q, "What is the rule about {container}?", ["What rule is there for {container}?", "What is special about {container}?"]),
    "q.yn_at": _bank(_Q, "Is {object} at {place}?", ["Is {object} at {place} now?", "Can {object} be found at {place}?"]),
    "q.yn_has": _bank(_Q, "Does {person} have {object}?", ["Is {person} holding {object}?", "Does {person} have {object} now?"]),
    "q.yn_in": _bank(_Q, "Is {object} in {container}?", ["Is {object} inside {container}?", "Is {object} in {container} now?"]),
}


def bank_target(bank_id: str) -> int:
    """Accepted patterns wanted for the whole bank (teacher banks: per style times styles)."""
    bank = BANKS[bank_id]
    return bank.target * len(STYLES) if bank.kind == "teacher" else bank.target


# ------------------------------------------------------------ mechanical check


@lru_cache(maxsize=None)
def forbidden_words(bank_id: str) -> Mapping[str, str]:
    """word -> why it is forbidden outside placeholders in this bank."""
    bank = BANKS[bank_id]
    kind, flags = bank.kind, bank.flags
    groups: list[tuple[str, Iterable[str]]] = [
        *VOCAB_GROUPS, ("number word", EXTRA_NUMBER_WORDS), ("fact word", OTHER_FACT_WORDS),
        ("calendar word", CALENDAR_WORDS), ("gendered pronoun", GENDERED_PRONOUNS), ("people word", PEOPLE_WORDS),
        ("home word", HOME_WORDS), ("history word", HISTORY_WORDS), ("frequency word", FREQUENCY_WORDS),
        ("hedge word", HEDGE_WORDS), ("ownership word", OWNERSHIP_WORDS), ("property word", PROPERTY_WORDS),
        ("event word", EVENT_WORDS),
    ]
    if "any_time" not in flags:
        groups += [("time word", TIME_OF_DAY_WORDS), ("time word", GENERIC_TIME_WORDS)]
        if "time" not in bank.placeholders:
            groups.append(("time word", CLOCK_WORDS))
    groups.append(("quantity word", PARTIAL_WORDS))
    if "quantifiers" not in flags:
        groups.append(("quantity word", QUANTITY_WORDS))
    if "negation" not in flags:
        groups.append(("negation", NEGATION_WORDS))
    if kind in ("narration", "rule"):
        groups += [("speaker word", SPEAKER_WORDS), ("modal word", MODAL_WORDS)]
    if kind == "teacher" and "question" not in bank.placeholders:
        groups.append(("doubt word", DOUBT_WORDS))
    if kind != "teacher":
        groups.append(("report word", REPORT_WORDS))
        if "failure" not in flags:
            groups.append(("attempt word", ATTEMPT_WORDS))
    banned: dict[str, str] = {}
    for label, words in groups:
        for word in words:
            banned.setdefault(word, label)
    for word in bank.allow | KIND_ALLOW[kind] | (FAIL_ALLOW if "failure" in flags else frozenset()):
        banned.pop(word, None)
    return banned


KIND_ALLOW: Mapping[str, frozenset[str]] = {
    "narration": frozenset(),
    "rule": frozenset(("always", "too", "can", "will", "you")),  # generic "you": "If you put down glass things ..."
    "teacher": frozenset(("something", "thing", "things", "one", "little", "new", "happy", "well")),  # "well done"; "the well" is caught below
    "question": frozenset(("thing", "things", "tell", "say", "know", "remember")),
}
FAIL_ALLOW = frozenset(("can", "could", "will", "would", "stuck"))


_TOKEN = re.compile(r"\{[a-z0-9_]+\}(?:'s)?|[A-Za-z]+(?:'[A-Za-z]+)*|\S")
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*")
_ALLOWED_PUNCT = set(".,!?':;- ")
_LEAD_IN = re.compile(r":\s*(?=\{(?:fact|correction|rule|event|question)\})")  # "Remember this: {fact}"
_DASH = re.compile(r"(^|\s)-|-(\s|$)|--")
_GLUED = re.compile(r"\}[A-Za-z]|[A-Za-z]\{")  # "{person}s", "un{place}"
_THE_WELL = re.compile(r"\b(the|a|this|that|at|to|by|near|from|in|into)\s+well\b", re.IGNORECASE)
_BAD_TIME_LEAD = re.compile(r"\b(at|in|on|the|a|an)\s+\{time\}", re.IGNORECASE)
_BAD_DETERMINER = re.compile(
    r"\b(the|a|an|this|these|those|its|their|my|your|our|his|her|some|any|every|each)\s+"
    r"\{(person|person_b|leader|giver|receiver|object|place|place2|container|item)\}",
    re.IGNORECASE,
)


def _char_problem(char: str) -> Optional[str]:
    if char.isalpha() and char.isascii() or char in _ALLOWED_PUNCT:
        return None
    if not char.isascii():
        return "non-ASCII character"
    if char in "\n\r\t":
        return "newline or tab"
    if char.isdigit():
        return "digit"
    if char in "\"`":
        return "quote mark"
    if char in "()[]<>":
        return "bracket"
    if char in "{}":
        return "malformed placeholder brace"
    if char in "*_#~|":
        return "markdown character"
    return f"character {char!r} not allowed"


def check_pattern(bank_id: str, text: str) -> list[str]:
    """Rejection reasons for `text` as a pattern of `bank_id`; empty means it passes."""
    bank = BANKS[bank_id]
    if not text or not text.strip():
        return ["empty"]
    reasons: list[str] = []

    def reject(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    for char in _SLOT.sub(" ", text):
        problem = _char_problem(char)
        if problem:
            reject(problem)

    found = _SLOT.findall(text)
    for name in found:
        if name not in PLACEHOLDERS:
            reject(f"unknown placeholder {{{name}}}")
        elif name not in bank.placeholders:
            reject(f"placeholder {{{name}}} not allowed in this bank")
    for name in bank.placeholders:
        if found.count(name) != 1:
            reject(f"placeholder {{{name}}} appears {found.count(name)} times, needs exactly 1")

    stripped = text.rstrip()
    if bank.kind == "question":
        if not stripped.endswith("?"):
            reject('question does not end with "?"')
    elif stripped.endswith("?"):
        reject('only questions may end with "?"')
    elif bank.kind in ("narration", "rule") and not stripped.endswith((".", "!")):
        reject('statement does not end with "." or "!"')
    elif bank.kind == "teacher" and not (stripped.endswith((".", "!")) or any(stripped.endswith("{" + s + "}") for s in SENTENCE_SLOTS)):
        reject('teacher line does not end with ".", "!" or a sentence placeholder')
    if bank.kind in ("narration", "rule") and "?" in stripped:
        reject('statement contains "?"')

    for name in SENTENCE_SLOTS:
        slot = "{" + name + "}"
        if slot not in text:
            continue
        index = text.index(slot)
        before, after = text[:index].rstrip(), text[index + len(slot):]
        if before and before[-1] not in ".!?:":
            reject(f"{slot} must start its own sentence")
        if after.strip() and not (after.startswith(" ") and (after.lstrip()[0].isupper() or after.lstrip()[0] == "{")):
            reject(f"{slot} must be followed by the end or a new sentence")
    if _BAD_TIME_LEAD.search(text):
        reject("{time} after at/in/on/the/a/an does not read well with every time word")
    if _BAD_DETERMINER.search(text):
        reject("determiner before a placeholder that brings its own")

    banned = forbidden_words(bank_id)
    tokens = _TOKEN.findall(text)
    speaker = bank.kind == "teacher"
    at_start, width = True, 0
    for token in tokens:
        if token.startswith("{") and "}" in token:
            name = token[1:token.index("}")]
            width += PLACEHOLDER_WIDTH.get(name, 1)
            at_start = name in SENTENCE_SLOTS
            continue
        if token in ".!?:;":
            at_start = True
            continue
        if token == "'":
            reject("stray apostrophe or quote")
            continue
        if not token[0].isalpha():
            continue
        width += 1
        tail_ok = token[1:] == token[1:].lower()
        head_ok = token[0].islower() or at_start or (speaker and token.split("'")[0] == "I")
        if not (tail_ok and head_ok):
            reject(f"capitalised word {token!r} mid-sentence (names are not allowed)")
        lower = token.lower()
        starter_ok = lower in STARTER_WORDS or lower in bank.allow or (lower.endswith("ly") and len(lower) > 3) \
            or (lower in _TIME_STARTERS and lower not in banned)
        if at_start and not speaker and not starter_ok:
            reject(f"sentence starts with {token!r}, not a placeholder or a known starter word (names are not allowed)")
        at_start = False
    low, high = WORD_BOUNDS[bank.kind]
    if not low <= width <= high:
        reject(f"{width} words, needs {low}-{high}")
    own = _SLOT.sub(" ", _LEAD_IN.sub(" ", text))
    sentences = len(re.findall(r"[.!?;:]+", own))
    if sentences > (2 if bank.kind == "teacher" else 1):
        reject(f"{sentences} sentences, too many for a {bank.kind} pattern")

    for word in _WORD.findall(_SLOT.sub(" ", text)):
        lower = word.lower()
        base = lower.split("'")[0]
        label = banned.get(lower) or banned.get(base)
        if label:
            reject(f"{label} {lower!r}")
        if lower.endswith("n't") and "negation" not in bank.flags:
            reject(f"negation {lower!r}")
    if "failure" in bank.flags and not FAILURE_OUTCOME.search(text.lower()):
        reject("fail pattern has no failure marker saying the attempt failed (could not, failed, unable, stayed shut; tried alone is not enough)")
    if NOT_ATTEMPTED.search(text.lower()):
        reject("says there was no attempt at all")
    if _DASH.search(text):
        reject("dash used as punctuation")
    if _GLUED.search(text):
        reject("placeholder glued to a word")
    if _THE_WELL.search(text):
        reject("place word 'well'")
    if _EVERY_OTHER.search(text):
        reject("'every other' changes how often")
    if bank_id == "t.wrong" and not WRONG_MARKER.search(text.lower()):
        reject("t.wrong pattern does not say the answer was wrong")
    if bank_id == "rule.R6" and not EXCLUSIVE_MARKER.search(text.lower()):
        reject("rule.R6 pattern does not say that only this person can")
    if bank_id in _HEDGE_BANKS and _HEDGE.search(_SLOT.sub(" ", text)):
        reject("teacher frame doubts or denies what it introduces")
    manner = _MANNER.findall(_SLOT.sub(" ", text))
    if bank_id in _NO_AGENT_BANKS:  # how fast it happened still fits an event nobody performs
        manner = [word for word in manner if word.lower() not in _RATE]
    if manner and (bank_id in SCENE_BANKS or bank_id in _NO_AGENT_BANKS or bank.kind == "question"):
        reject("manner word on a sentence about how things are")
    return reasons


# The frame checker accepted "This rule is not always true. {rule}".
_HEDGE = re.compile(r"\b(not|n't|no longer|maybe|perhaps|might|probably|guess|never|sometimes|unsure|doubt\w*|used to)\b"
                    r"|n't\b", re.IGNORECASE)
_HEDGE_BANKS = frozenset({"t.state", "t.remember", "t.demo_intro", "t.demo_step", "t.demo_outro", "t.change"})

# Events nobody performs: "Gently, {object} broke." / "Slowly, night fell."
_RATE = frozenset({"slowly", "quickly", "suddenly", "finally", "gradually"})
_NO_AGENT_BANKS = frozenset({"ev.time", "ev.new_day", "ev.breaks", "ev.returned", "ev.moved_by_place", "ev.recoloured"})

# Qwen-accepted scene patterns such as "Carefully, {object} is at {place}." put a manner adverb on a state.
_MANNER = re.compile(r"\b(?!only\b|early\b|daily\b|nearby\b)[a-z]+ly\b", re.IGNORECASE)


# ------------------------------------------------------------ ids and dedup


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def pattern_id(bank_id: str, text: str) -> str:
    return hashlib.sha256(f"{bank_id}\n{normalize(text)}".encode()).hexdigest()[:12]


def _content_words(text: str) -> frozenset[str]:
    return frozenset(word.lower() for word in _WORD.findall(_SLOT.sub(" ", text)))


def jaccard(a: str, b: str) -> float:
    """Token Jaccard on the non-placeholder words (1.0 when both have none)."""
    left, right = _content_words(a), _content_words(b)
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def dedup(texts: Sequence[str], threshold: float = NEAR_DUPLICATE) -> list[Optional[int]]:
    """For each text, None if kept, else the index of the earlier kept text it duplicates."""
    kept: list[int] = []
    seen: dict[str, int] = {}
    result: list[Optional[int]] = []
    for index, text in enumerate(texts):
        key = normalize(text)
        match = seen.get(key)
        if match is None:
            match = next((k for k in kept if jaccard(text, texts[k]) >= threshold), None)
        if match is None:
            kept.append(index)
            seen[key] = index
        result.append(match)
    return result


# ------------------------------------------------------------------- prompts


def _forbidden_summary(bank_id: str) -> str:
    """The world's vocab in full; other groups by up to 10 examples (the prompt stays short)."""
    by_label: dict[str, list[str]] = {}
    plurals = set(OBJECT_PLURALS) | {_plural(w) for w in PLACES + CONTAINERS} | {t + "s" for t in TIMES}
    full = {label for label, _ in VOCAB_GROUPS} - {"number word"}
    cut: set[str] = set()
    for word, label in forbidden_words(bank_id).items():
        shown = by_label.setdefault(label, [])
        if word in plurals or (label not in full and any(word[:4] == w[:4] for w in shown)):
            continue
        if label not in full and len(shown) >= 10:
            cut.add(label)
            continue
        shown.append(word)
    return "\n".join(f"  {label}s: {', '.join(words + (['...'] if label in cut else []))}" for label, words in by_label.items())


SCENE_BANKS = frozenset(bank_id for bank_id in BANKS if bank_id.startswith(("ev.intro_", "ev.owner", "ev.material", "ev.kind_group", "ev.is_", "ev.layout_")))


def tense_rule(bank_id: str) -> str:
    """The tense a bank is written in: narrated events past, descriptions and rules present."""
    kind = BANKS[bank_id].kind
    if kind == "narration":
        return ("Write in the present tense: it describes how things are now." if bank_id in SCENE_BANKS
                else "Write in the simple past tense: it tells what just happened.")
    if kind == "rule":
        return "Write in the present tense: the rule is always true in this village."
    return ""


def build_prompt(bank_id: str, variant: str, n: int) -> str:
    """Ask a writer for `n` new patterns of `bank_id`; `variant` is a style (teacher) or a flavour."""
    bank = BANKS[bank_id]
    slots = " ".join("{" + name + "}" for name in bank.placeholders)
    lines = [
        "You write sentence patterns for a simple story world for young children.",
        f"Write {n} new, different patterns that all mean: {bank.gloss}",
    ]
    if bank.note:
        lines.append(f"Meaning note: {bank.note}.")
    if bank.kind == "teacher":
        lines.append(f"These are things a teacher says to a learner. Teacher style: {variant} ({STYLE_HINTS[variant]}). "
                     "You may use I, you and we, and one or two sentences.")
    else:
        lines.append(f"Flavour for this batch: {FLAVOURS[variant]}.")
    lines.append("Rules:")
    tense = tense_rule(bank_id)
    if tense:
        lines.append(f"- {tense}")
    if slots:
        lines.append(f"- Use each of these placeholders exactly once, written exactly like this: {slots}. No other curly braces.")
        for name in bank.placeholders:
            lines.append(f"  {{{name}}} will become {PLACEHOLDER_HELP[name]}.")
    else:
        lines.append("- Use no placeholders and no curly braces.")
    lines += [
        "- Use simple words a young child knows. Vary the sentence structure; do not just swap one word.",
        "- Add NO new facts: no names, other people, places, objects, colours, materials, numbers, times or amounts. "
        "Only the placeholders may carry those.",
        "- Only capitalise the first word of a sentence" + (" (and I)." if bank.kind == "teacher" else "."),
        "- Plain ASCII only: no digits, quotation marks, brackets, lists, markdown or emoji.",
        {"narration": '- Each pattern is a statement ending with "." or "!".',
         "rule": '- Each pattern states the rule and ends with "." or "!".',
         "teacher": '- Do not end with "?".',
         "question": '- Each pattern is one question ending with "?".'}[bank.kind],
    ]
    if bank.kind != "teacher":
        lines.append("- Start each sentence with a placeholder or a common word such as The, Then, Soon, At, In, When, "
                     "Where or What, or a manner word ending in -ly; never with a name.")
    if "failure" in bank.flags:
        lines.append("- Say clearly that the attempt failed (could not, failed, unable, but it stayed shut); "
                     "tried alone is not enough. Give no reason for the failure.")
    if bank_id == "t.wrong":
        lines.append("- Say plainly that the answer was wrong (wrong, not right, a mistake).")
    if bank_id == "rule.R6":
        lines.append("- Say that only this person can open it (only, no one else, nobody but).")
    lines.append("- Do not use these words, or others like them, outside the placeholders:\n" + _forbidden_summary(bank_id))
    lines.append("Examples:")
    lines += [f"{seed}" for seed in bank.seeds[:2]]
    lines.append(f"Now write exactly {n} new patterns, one per line, with no numbering and nothing else.")
    return "\n".join(lines)


_QUOTES = "\"'`“”‘’"
_LEAD = re.compile(r"^(?:\d+\s*[.):-]|[-*+•]|\(?[a-z]\))\s+")
_CHATTER = re.compile(
    r"^(here (are|is)\b.*\b(patterns?|sentences?|lines?|versions?|examples?)\b|sure\b|certainly\b|"
    r"of course\b|i hope\b|let me know\b|note\b)",
    re.IGNORECASE,
)
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def parse_generation(text: str) -> list[str]:
    """Candidate patterns from a writer's raw output: numbering, bullets and quotes stripped, chatter dropped."""
    out = []
    for raw in _THINK.sub("", text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith(("```", "#", "<")):
            continue
        line = _LEAD.sub("", line).strip().strip("*_").strip()
        while len(line) >= 2 and line[0] in _QUOTES and line[-1] in _QUOTES:
            line = line[1:-1].strip()
        if not line or line.endswith(":") or ("{" not in line and _CHATTER.match(line)):
            continue
        out.append(line)
    return out


# --------------------------------------------------------------- cross-check

SAMPLE_NAMES = ("Kelo", "Rami", "Tosa", "Vemi", "Nuba", "Lira", "Zobi", "Mafo")


def render(pattern: str, values: Mapping[str, str]) -> str:
    """Fill placeholders and capitalise sentence starts."""
    text = _SLOT.sub(lambda m: values[m.group(1)], pattern)
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def sample_values(bank_id: str, rng: random.Random) -> dict[str, str]:
    """Random renderings for the bank's placeholders (plus the sentence-slot fillers)."""
    names = rng.sample(SAMPLE_NAMES, 7)
    places = rng.sample(PLACES, 3)
    noun, noun2 = rng.sample(OBJECTS, 2)
    colour, colour2 = rng.sample(COLOURS, 2)
    container = rng.choice(CONTAINERS)
    extra_name, extra_place, extra_container = names[5], places[2], rng.choice(CONTAINERS)
    item = rng.choice(OBJECTS)
    values = {
        **dict(zip(PERSON_SLOTS, names)),
        "object": f"the {colour} {noun}", "place": f"the {places[0]}", "place2": f"the {places[1]}",
        "container": f"the {container}", "time": rng.choice(TIMES), "material": rng.choice(MATERIALS),
        "category": rng.choice(CATEGORIES), "colour": colour2, "direction": rng.choice(DIRECTIONS), "count": rng.choice(NUMBER_WORDS[2:6]),
        "object_kind": PLURAL[rng.choice(OBJECTS)], "item": ("an " if item[0] in "aeiou" else "a ") + item,
        "action": rng.choice([f"{extra_name} dropped the {noun2}", f"{extra_name} put the {noun2} in the {extra_container}",
                              f"{extra_name} walked to the {extra_place}"]),
        "fact": rng.choice([f"The {colour2} {noun2} is at the {extra_place}.", f"{extra_name} has the {noun2}.",
                            f"The {noun2} is in the {extra_container}."]),
        "correction": rng.choice([f"The {noun2} is at the {extra_place}.", f"{names[6]} has the {noun2}."]),
        "rule": rng.choice([f"Things made of {rng.choice(MATERIALS)} break when they are put down.",
                            f"{extra_name} always follows {names[6]}.", f"Only {extra_name} can open the {extra_container}."]),
        "event": rng.choice([f"{extra_name} picked up the {noun2}.", f"{extra_name} put the {noun2} in the {extra_container}.",
                             f"{extra_name} walked to the {extra_place}."]),
        "question": rng.choice([f"Where is the {colour2} {noun2}?", f"Who has the {noun2}?", f"What is in the {extra_container}?"]),
    }
    return {name: values[name] for name in BANKS[bank_id].placeholders}


def crosscheck_values(bank_id: str, key: str, count: int = 2) -> list[dict[str, str]]:
    """`count` reproducible instantiations for checking pattern `key`, distinct where the bank allows."""
    chosen: list[dict[str, str]] = []
    for k in range(count):
        for attempt in range(20):
            values = sample_values(bank_id, random.Random(f"{key}:{k}:{attempt}"))
            if values not in chosen:
                break
        chosen.append(values)
    return chosen


def crosscheck_prompt(bank_id: str, pattern: str, values: Mapping[str, str]) -> str:
    """Ask a checker whether the instantiated pattern says exactly the instantiated gloss."""
    bank = BANKS[bank_id]
    no_extra = "no other people, names, places, objects, colours, times, amounts, reasons or events"
    # Wording measured on Bonsai with red-team cases: a "narrower or wider question" test rejected
    # nearly every good paraphrase, and naming the harmless variation lifted good acceptance.
    if bank.kind == "question":
        tests = ["- The sentence asks exactly the meaning above.", f"- It adds no other fact: {no_extra}."]
    else:
        tests = [
            "- The sentence says exactly what the meaning says" + (" (an attempt that failed)." if "failure" in bank.flags else "."),
            f"- It adds no other fact: {no_extra}.",
            "- It does not deny, doubt or weaken the meaning, and does not say it did not happen"
            + (", only happened sometimes, or has exceptions." if bank.kind == "rule" else "."),
        ]
    return "\n".join([
        "You check sentences for a simple story world for young children.",
        f"Meaning: {render(bank.gloss, values)}",
        f"Sentence: {render(pattern, values)}",
        "Answer yes only if all of these are true:",
        *tests,
        "- It is correct, plain English.",
        f"These are fine and are not new facts: {_HARMLESS[bank.kind]}.",
        "Answer with one word: yes or no.",
    ])



def frame_prompt(bank_id: str, pattern: str, values: Mapping[str, str]) -> str:
    """Check only a teacher line's own words around its fixed sentence slot.

    The whole-line check rejected most good frames ("I want you to answer this. Where is the sled?"): the
    checker compared wording, not job. The fixed sentence is shown separately; the mechanical check has
    already ruled out new fact words in the frame.
    """
    bank = BANKS[bank_id]
    slot = next(name for name in bank.placeholders if name in SENTENCE_SLOTS)
    fixed = values[slot]
    job = _SLOT.sub("", bank.gloss).strip()
    return "\n".join([
        "A teacher in a simple story world for young children says this line:",
        render(pattern, values),
        f"This part of it is fixed and always correct: {fixed}",
        f"The teacher's other words must do this job: {job}",
        "Answer yes only if all of these are true:",
        "- The teacher's other words do that job (other wording and a different tone are fine).",
        "- They add no fact about the story: no people, names, places, objects, colours, times or amounts.",
        "- They do not say the fixed part is false, doubtful or a guess.",
        "- The whole line is correct, plain English.",
        # A bare one-word answer was "no" for 6/6 good frames; one short line per test first fixed it.
        "Go through each test in one short line, then give the answer alone on the last line: yes or no.",
    ])


def parse_last_yes_no(text: str) -> bool:
    """The verdict on the last non-empty line (for prompts that reason first)."""
    lines = [line for line in _THINK.sub("", text or "").strip().splitlines() if line.strip()]
    return bool(lines) and parse_yes_no(lines[-1].replace("*", "").split(":")[-1])


FRAME_BANKS = frozenset(b for b, bank in BANKS.items() if bank.kind == "teacher" and set(bank.placeholders) & set(SENTENCE_SLOTS))

_HARMLESS: Mapping[str, str] = {
    "narration": "other words for the same action (like walked or headed for went), words about how it was done "
                 "(like slowly), and joining words (like then, soon or now)",
    "rule": "other words for the same rule (like anything or whatever for things), and joining words (like when, if or once)",
    "teacher": "friendly words to the learner (like dear, little one or well done) and other words that do the same job",
    "question": "other wording for the same question, and small words like now or right now",
}


def parse_yes_no(text: str) -> bool:
    """True only for a bare yes (case and a final . or ! ignored); anything else counts as no."""
    answer = _THINK.sub("", text or "").strip().lower().rstrip(".!").strip()
    return answer == "yes"


# ------------------------------------------------------------------- splits

MANIFEST_VERSION = "village-patterns-v1"
SPLIT_FRACTIONS = (0.6, 0.2, 0.2)


def assign_splits(accepted: Iterable[Mapping[str, Any]]) -> tuple[SplitManifest, dict[str, dict[str, list[dict[str, Any]]]]]:
    """Split accepted patterns ({id, bank, text, writer, style?}) into train/validation/test.

    Narration, rule and question banks are split per bank by hash rank
    (`assign_ranked`, 0.6/0.2/0.2). Teacher patterns follow their style, and the
    ten styles are split 6/2/2 the same way, so held-out styles come with
    held-out wording. A bank with fewer than three patterns goes wholly to
    train (it is a shortfall anyway).
    """
    salt = MANIFEST_VERSION
    styles = assign_ranked("teacher_style", STYLES, salt=salt, fractions=SPLIT_FRACTIONS)
    by_bank: dict[str, list[Mapping[str, Any]]] = {bank_id: [] for bank_id in BANKS}
    for entry in accepted:
        by_bank[entry["bank"]].append(entry)
    assignment: dict[str, str] = {}
    banks: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for bank_id, entries in by_bank.items():
        if BANKS[bank_id].kind == "teacher":
            ranked = {e["id"]: styles[e["style"]] for e in entries}
        elif len(entries) >= 3:
            ranked = assign_ranked("template", [e["id"] for e in entries], salt=salt, fractions=SPLIT_FRACTIONS)
        else:
            ranked = {e["id"]: "train" for e in entries}
        assignment.update(ranked)
        banks[bank_id] = {"train": [], "validation": [], "test": []}
        for entry in sorted(entries, key=lambda e: e["id"]):
            row = {"id": entry["id"], "text": entry["text"], "writer": entry["writer"]}
            if entry.get("style"):
                row["style"] = entry["style"]
            banks[bank_id][ranked[entry["id"]]].append(row)
    manifest = SplitManifest(
        salt=salt,
        fractions=SPLIT_FRACTIONS,
        families=(
            FamilyManifest("teacher_style", MANIFEST_VERSION, tuple(styles.items())),
            FamilyManifest("template", MANIFEST_VERSION, tuple(assignment.items())),
        ),
        canary=hash_canary(salt, SPLIT_FRACTIONS),
    )
    return manifest, banks
