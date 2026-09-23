# Exp 237 -- relation table v1.1 (synonyms, everyday relations, dates) on loop221

**One change.** loop237 = loop221 reading
`artifacts/claude-table237-20260922/relation_table_v1_1.json` instead of v1.
v1.1 = v1 + additions, built by `scripts/claude_table237_build.py` (the
`v1_1_additions` block in the file lists all 68). v1 is untouched.
Code: `scripts/claude_loop237_agent.py` (subclass of the 221 mixin; 228 guard
installed, `SrcGuardMixin228` first in the daemon bases).

Two small reader changes the new rows need (question side only):
1. An ask template with no `{X}` that says *I / me / my* reads the user's own
   slot ("Where do I work?", "How old am I?"). 221 only accepted "my".
2. A row may list `broader` rows. wife -> spouse and husband -> spouse. When
   the asked word and its own group are empty, the broader row's own keys are
   read too. wife and husband are never linked to each other.

## Answer rules (unchanged from 221 except the wider groups)
- The exact stored word is tried first; if it has a value, nothing else is read.
- Otherwise the group is searched. One value (or the same value under several
  words) -> that fact, said with its STORED word ("Mira Vell's boss is Ada Cole.").
- Different values under different words -> each one with its own word, never
  merged; for a single-valued relation the reply adds "These disagree, so I will
  not pick one. Which is right?"
- Inverse answers keep "(worked out backwards)" and are never stored.
- Only ask / clarify actions are produced, so questions never write. Teaches
  and statements take exactly the 221 path.

## Why each group counts as one relation (217 rule: true synonyms only)
- **boss = manager = supervisor = line manager.** All name the one person
  you report to at work. (Employer is a company, so it stays separate.)
- **doctor = physician = GP = family doctor.** In "X's doctor" the word means
  X's own medical doctor; physician is the formal word, GP / family doctor
  the everyday British/US words for that same person. Dentist, vet, therapist
  and nurse are NOT linked (different jobs).
- **spouse <-> wife, spouse <-> husband (one step each way).** Not full
  synonyms, so they are not aliases. A wife fact answers a spouse question
  (already in v1), and a spouse fact now answers a wife/husband question.
  The reply names the stored word ("Kip's spouse is Jo."), so it never claims
  more than was taught. wife and husband never answer each other.
- **native language = mother tongue = first language = native tongue.** All
  mean the language learned first from birth. It is *narrower* than language
  (one-way): a native-language fact answers "What language does X speak?",
  a plain language fact does NOT answer "mother tongue".
- **city = residence = place of residence = city lived in (+ the key "home").**
  All ask where X lives; v1 already had town and lives_in here. Different
  stored values (a street address under home, a city under city) are listed
  separately, never merged. hometown and birthplace stay separate (217 rule).
- **languages** (plural surface of language), **line of work** (= occupation),
  **next-door neighbour** (= neighbour), **veterinarian** (= vet),
  **attorney** (= lawyer), **flatmate / housemate / room mate** (= roommate),
  **headteacher** (= principal), **stepmom / stepmum** (= stepmother),
  **stepdad** (= stepfather), **fiancé** (spelling of fiance), spelling
  variants of favourite X.
- Dropped as not true synonyms: hairdresser/barber, counsellor/therapist,
  solicitor/lawyer, priest/minister/pastor, landlady, university/college for
  educated_at, wedding date for anniversary, date of birth for birthday.

## New rows
Everyday people: landlord, dentist, vet, tutor, mayor, lawyer, accountant,
therapist, nurse, babysitter, nanny, barber, roommate, classmate, teammate,
girlfriend, boyfriend, fiance, principal, captain, pastor, pharmacist,
mechanic, plumber, stepmother, stepfather, niece, nephew, godmother,
godfather. Things: favourite food/book/song/animal, car, address, phone
number, email, street, bank, team, club, instrument, major. Extra templates:
"Who owns X?", "Who coaches/trains X?", "What language(s) does X speak?",
"Where do I work?", "Who do I work for?", "Where do I live?", "Which books did
Y write?", plus Who's / What's / When's contractions and "the name of X's R".

## Dates
date_founded (founding date/year, year founded, keys founded/founded_in):
"When was X founded / established / set up?", "What year was X founded?".
opening_date: "When did X open?", "When was X opened?". graduation_date:
"When did X graduate?". wedding_anniversary (narrower of anniversary).
birthday: "When's / When was X's birthday?", "When's my birthday?".
All carry the v1 date value guard for inverse questions. Statements like
"Brightmill was founded in 1990." are NOT read (writes untouched).

## Known limits
- Replies spell the stored key ("Pia Lund's gp is ...", "your employer is ..."
  from the existing me166 mouth); cosmetic, unchanged mouths.
- No yes/no, no forward reading of inverse storage keys (as 221).
