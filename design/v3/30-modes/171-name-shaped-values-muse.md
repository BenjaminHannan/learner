# 171 — Name-shaped values (design)

## The problem (one paragraph for Ben)

You teach the assistant "Kim's mom is sick" and it saves "sick" as her
name. Later "Who is Kim's dog?" answers "brown". The director caught 8/8
such turns saving junk on loop138b AND loop138d ("Kim's boss is mean",
"Kim's sister is tall", "Kim's mother is a nurse", "Kim's friend is
here", "Kim's boss is away today"). These are the most natural phone-chat
sentences, so saving descriptions as names is a wrong-write class: every
later answer built on that fact is a lie told confidently.

## The one change

For relations whose value must be a NAME, a teach whose value is not
name-shaped now writes nothing and gets one fixed reply, e.g. "That
sounds like a description, not a name, so I didn't save it. What is Kim's
mother's name?" (for the user entity it would say "your mother's name",
but the 138d base has no user entity so that branch never fires). A
follow-up question then finds nothing saved. Real names (Rita, Mira, and
lowercase non-dictionary names like ana) save exactly as before, and every
other relation (job, pet, city, colour, food, car, …) behaves exactly as
before — the guard only claims teach/correct turns on the 21 name keys
with refused values, so everything else is the loop138d code literally.

## What counts as "not a name"

The value's first word (lowercased) is a common English word, or an
article/determiner, or a place/time adverb:

- WORDS: the sealed `wordlist171.txt` = lowercase entries of
  `/usr/share/dict/words` minus the sealed `givennames171.txt` (common
  given names + person-name tokens from our sealed suites: Ann, Bob, Cora,
  Sella, Mark, Patel, Fay, Jo, Wren, Pia, Kip, Ted, Beth, Bobby, Patty,
  Penny, Dick, Peter, Tony, Marge, Buffy, Lech, Atom, Tom, Sam, Ana, Mira
  …; sha256 of both files is in SEAL.sha256.txt). A lowercase word NOT in
  WORDS (ana, priya, zofia) keeps today's behaviour exactly.
- DETERMINERS (sealed in code): a, an, the, my, his, her, its, our, their,
  your, this, that, these, those, very, so, really, quite, too, rather,
  somewhat, fairly, pretty, much, more, most, not, still, always, never,
  just, no, some, any, such, own, same, other, another, each, every, few,
  several, both.
- PLACE_TIME_ADVERBS (sealed in code): here, there, away, home, today,
  yesterday, tomorrow, inside, outside, upstairs, downstairs, abroad,
  nearby, elsewhere, everywhere, nowhere, somewhere, anywhere, indoors,
  outdoors.

Capitalised words are looked up lowercase too, so "Sick" clarifies while
"Rita" saves. Titles stay refused ("Lady", "Queen" are dictionary words,
not names — bench chains through "Lady Macbeth" abstain, predicted).

## The 21 name keys (why each)

mother/father — a parent is a person, named. mom/dad — the parser's own
keys for Mom/Dad (distinct from mother/father). mum/daddy — the parser's
keys for Mum/Daddy. sister/brother/sibling — a sibling is a person, named.
boss/friend/colleague/teacher — a person you know, named. spouse/wife/
husband — a partner is a person, named. child/son/daughter — a child is a
person, named. dog/cat — a pet is a named animal. Multi-word compounds
(best_friend), offices (president), and everything else (pet, job, city,
colour, food) are different parser keys and keep today's behaviour.

## Hooks (mixin, nothing edited)

`NameVal171Mixin` (scripts/fable_fix171_nameval.py) wraps loop138d
read-only: ears `hear()` runs the inner 138d chain first, then rewrites a
refused name-value teach/correct to the sealed clarify; loop `_act()`
re-checks just before the write (covers structured/delegate paths). Same
two-level shape as the exp-139b value guard.

## Known edges

- Base negation ("not well", "never home") and clause ("split that")
  clarifies fire before the guard; those turns keep the base reply.
- "Actually, X is Beth." saves Beth (correction values pass the same
  screen); "Mira's mother is actually Ana." is refused ("actually" is a
  common word) — a predicted p4 move.
- Surname-only values on the exclusion list (Patel) save; anything else
  dictionary-first refuses, even if meant as a name (Rose/Grace are
  excluded as given names and save).

## What it means / doesn't

Means: the 8 director junk-writes are gone, real names and all other
relations byte-identical. Doesn't mean titles read as names, or that
inverted-frame junk (138d's sealed M4 FAILs) is fixed — those are
inherited unchanged.
