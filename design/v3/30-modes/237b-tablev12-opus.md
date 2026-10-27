# Exp 237b -- relation table v1.2 (systematic enumeration) on loop237

**One change.** loop237b = loop237 reading
`artifacts/claude-table237b-20260922/relation_table_v1_2.json` instead of v1.1.
Code: `scripts/claude_loop237b_agent.py`. It only forces the table path. The
237 reader, the 221 answer rules, the 138i stack and all writes are unchanged.
The 228 guard is installed (SrcGuardMixin228 first in Loop237bDaemon's bases,
install_srcguard228() at import). v1.2 is built by
`scripts/claude_table237b_build.py` from v1.1 plus additions. Every addition
is listed in the table's `v1_2_additions` block, tagged with its category.

## Where the rows came from
The rows were enumerated **before any testing**, from general English
knowledge, organised by category. They were **not** taken from any panel. The
237 blind panel was never opened. I did read 237's RESULTS.md, which names
the pairs it missed (pupil/student, surname/last name, automobile/car,
phone/telephone). Any category-by-category pass also produces those pairs, so
the enumeration was not built around them. Each relation got:
- its canonical name;
- TRUE synonyms only;
- its ask wordings;
- any labelled inverse entries.

Categories and what they added (full list in the table):
1. **Family and household.**
   - Kin-word synonyms: mama/mam, gran/nan/nana, granddad/grandad, auntie/aunty.
   - Step-, half-, in-law, great-grand, god- and foster relatives, grandparent, twin, guardian.
   - Household roles: tenant, lodger, housekeeper, au pair.
2. **Partners.**
   - fiancée as its own row (fiancé and fiancée are not merged, like wife/husband).
   - ex-wife, ex-husband, ex-girlfriend, ex-boyfriend, ex-partner and ex.
   - "life partner" = partner. "Who's X married to?"
3. **Friends and social.** bestie/BFF/best mate = best friend. pal/buddy = friend. pen pal, childhood friend, acquaintance, enemy, idol, role model, hero.
4. **Work and business.**
   - Wordings: "Who does X report to?" and "Who manages X?" (= boss).
   - People: employee, client, customer, business partner, direct report, intern, trainee, assistant, secretary, deputy, agents, receptionist.
   - workplace / place of work = work location.
   - job title, salary, office, department, industry.
   - "What does X do / work as?" (occupation).
5. **School and learning.**
   - pupil = student.
   - headmaster, headmistress, form tutor, homeroom teacher, advisor, thesis supervisor, professor, lecturer, teaching assistant, study partner, lab partner.
   - university and college, with "Where does X go to university?" and similar.
   - More school wordings, degree, grade, favourite subject, thesis.
6. **Health and services.**
   - 66 rows, mostly service roles, for example dentist, vet, optician, physio (= physical therapist), hairdresser (= hairstylist), estate agent (= realtor = real estate agent), counsellor (= counselor), solicitor, priest, rabbi, imam.
   - Instrument and subject teachers: piano, guitar, violin, singing, drum, dance, art, maths, English, science and yoga teacher, plus music teacher, driving instructor and swimming instructor.
   - landlady, patient.
7. **Home and places.**
   - "Where does X live now / these days / nowadays / currently / at the moment / at present?"
   - "Where did X grow up?" (= hometown's own wording).
   - Rows: country of residence, neighbourhood, postcode (= zip code = postal code), state, county, region, province, location, house, flat (= apartment), holiday home, favourite place, favourite restaurant, local pub, gym, church, hospital, place of burial.
8. **Contact details.**
   - telephone number and contact number = phone number.
   - e-mail = email.
   - home address and street address = address.
   - Separate rows: mobile number (= cell number), landline, work phone, work email, website, username, fax, mailing address, work address.
9. **Identity.**
   - surname = last name = family name. first name = given name = forename.
   - middle, maiden, full, stage and pen name.
   - birthdate / DOB = date of birth. nationality wordings.
   - birth year as its own row. star sign = zodiac sign. blood type = blood group.
   - height, weight, shoe size, eye colour, hair colour, gender, pronouns, ethnicity, accent, second language, home country, country of birth.
10. **Possessions, vehicles and pets.**
    - automobile / motor car = car, plus "What car does X drive?" and "What does X drive?".
    - vehicle, motorbike (= motorcycle), bicycle, bike, van, truck (= lorry), boat, number plate (= licence plate), phone (the device), laptop, computer, watch, guitar, piano.
    - 18 pet kinds.
    - 34 "favourite X" rows. Each row has both spellings, and film = movie.
11. **Organisations.**
    - HQ / head office = headquarters, and "Where is X headquartered?".
    - CEO wordings. "Who started / set up / established X?" (= founder). "Who does X belong to?" and "Who is X owned by?" (= owner).
    - Rows: co-founder, president, VP, MD, CFO, CTO, COO, treasurer, GM, head chef, parent company, subsidiary, motto, slogan, mascot, logo, number of employees, registered name, ticker, product, competitor, investor, sponsor, opening hours.
12. **Creative works.**
    - Roles: publisher, illustrator, translator, editor, narrator, singer, lyricist, songwriter, sculptor, photographer, screenwriter (= scriptwriter), film producer, record producer, record label.
    - Parts of the work: lead actor, main character (= protagonist), villain (= antagonist), setting, sequel, prequel, theme tune.
    - Music and media: band, album, debut album, debut novel, catchphrase, channel.
13. **Sports and hobbies.**
    - Team wordings ("Who does X play for?"), position wording.
    - pastime = hobby.
    - Rows: stadium (= home ground), league, shirt number (= jersey number), rival club, training partner, dance/tennis/doubles partner, trainer, instructor, belt, handicap, personal best, collection, book club, choir, orchestra, favourite hobby.
14. **Dates and events.**
    - The "first open" fix (below). More founding and graduation wordings. "When did X pass away?"
    - New date rows: wedding date ("When did X get married?"), release date, publication date, construction date, closing date, retirement date, launch date, start date, moving date, engagement date, due date, name day, exam date, premiere date, debut date.
    - birthday <-> date of birth (below).

## Rules kept
- **Aliases are true synonyms only.** The answer always uses the STORED word
  ("Tobin Rusk's automobile is a Hesper Coupe."), so it stays true.
- **Near-synonyms that are different relations get their own rows and stay unlinked:**
  - boss / employer; hometown / birthplace / country of birth; girlfriend / wife; fiancé / husband
  - landlord / owner; tutor / teacher; counsellor / therapist; stepmother / mother
  - piano teacher / music teacher; mobile number / landline / phone number; vehicle / car
  - solicitor / lawyer; birth year / birthday
- **No new narrower or broader links**, with one exception: **birthday <-> date of
  birth**, linked both ways (birthday.narrower += date_of_birth;
  date_of_birth.broader = [birthday]). The reply names the stored word, so a
  birthday is never presented as a full date of birth. For example, "When was X
  born?" with a birthday stored gives "X's birthday is May 3." "What year was X
  born?" is a separate row (birth_year) and is NOT linked, so a birthday never
  answers a year question.
- **Inverse entries are answer-time only and labelled "(worked out backwards)".**
  - Three new inverse storage keys: landlord <- tenant, teacher <- student, doctor <- patient.
  - Each of tenant, student and patient is also a row of its own. So a question
    about X's tenant can never be answered with X's landlord: key2rel finds
    the row before the inverse map.
- **Verb-direction leaks are left for exp 251.** "Who does X employ?" still gives X's employer, because the base stack produces it.

## Template capture fix (inside the table)
237 answered "When did Copperleaf Garage first open?" with "I don't know anyone
called Copperleaf Garage first." That happened because the table template
"When did {X} open?" captured "first". In v1.2 the three opening templates are
REPLACED by versions with the table's optional-word syntax: "When did {X}
[first] open?", "When was {X} [first] opened?" and "What year did {X} [first]
open?". The slot is lazy, so the shortest name that still matches wins, and X
becomes "Copperleaf Garage". It is one template, so there is still exactly one
reading. This needed no code.

## Speed (table-data only)
Applying all 221 generic wordings to about 1,000 surfaces gave 39,722 patterns
and about 4.8 ms per reading. The stack reads twice on a turn the base misses,
so that risked M5 (+5 ms). The new rows therefore use **typed generic
families** (the families are new `generic_patterns` entries in the table):
- p_/my_/of_person: "WH is X's R", "Who's X's R", "the name of X's R", "the R of/for X", "my R" forms;
- p_/my_/of_thing: "What is/What's X's R", "the R of/for X";
- p_/my_/of_date: "When is/When's/When was X's R", "When was the R of X".

The v1.1 rows keep the v1.1 families, plus the "the R for X" forms added to
of_form. The result is 16,662 patterns and about 1.5 ms per reading. The
pilot added about +2.6 ms per question on dev. The optional extras I had
drafted ("Who was X's R", "... again?", "What is X's R called?") were dropped
to stay fast.

## Known limits (seen in pilots; outside the table, so not fixed)
- **"What is the name of X's hamster?"** The base 138i stack claims this turn
  itself and asks about an entity called "the name of X". The table stage
  never sees it as a miss. This needs reader or base code.
- **"My last name is Harrow."** The base reads this as a statement about the
  assistant's own name and stores nothing. This is the write side, which is
  unchanged.
- **Verb-form statements** ("X lives in Y.", "X got married in 2012.", "Y
  opened in 1998.") store nothing. This is the write side.
- **Replies spell the stored key** ("your surname is Harrow." in lower case, from the me166 mouth). This is cosmetic and unchanged.
- **Cost.** A table-read question costs about 2 x 1.5 ms, because hear runs twice on a base-miss turn.
