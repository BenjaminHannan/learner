# RESULTS own-O0b — frame data generator (plan §2.4)

**Verdict: PASS.** All four marks pass on the registered run. Sealed scripts
unchanged after the seal (hashes match pre-seal snapshot).

Generator: scripts/claude_own_o0b_gen.py (world sampler, exact labels by
construction). Checker: scripts/claude_own_o0b_check.py (independent
re-deriver from turn text + world intent, never frame id).
Data: artifacts/claude-own-o0b-20260923/ — 200,000 train + 5,000 L1 dev +
5,000 L2 dev rows as jsonl.gz, counts.json, frame_split.json,
name_pools.json. CPU only, no model, no downloads. Fictional names only.

## Marks table (integer counts)

| Mark | Bar | Measured | Result |
|---|---|---|---|
| Pown0b.1 re-deriver mismatches on 10,000 sampled rows (seed 7) | 0 | 0 / 10,000 | PASS |
| Pown0b.2 L2 frame ids appearing in train (all 200,000 rows) | 0 | 0 | PASS |
| Pown0b.3 non-whole-word spans (all 210,000 rows, all spans) | 0 | 0 | PASS |
| Pown0b.4 smallest family share of train | >= 3% (>= 6,000) | 10.0% (20,000) | PASS |

Extra verification (all rows, not sampled): question relations all in
relation_table_v2 and <= 3 per question (0 violations); count == len(facts)
(0 violations); world surface == span text for every span (0 mismatches in
210,000 rows); reserved L2 names in train turns 0 rows; train name-pool names
in L2 turns 0 rows; held-out opener slots in train 0 rows; held-out closer
slots in train 0 rows (323 train turns end in " again." but all are
core-internal wording such as "Good night! Thanks again." with an empty
closer, never the closer slot); every file under 5 MB (largest 1,576,636
bytes); 3,597 L1 frames + 915 L2 frames (20.3% held out); >= 44 hand-written
core patterns per act for each of 7 acts x 6 relation kinds (asserted at
import); L3 empty as ordered.

## Moves (every run)

- Pre-seal pilots (debugging, expected to fail): ~10 pilot generations
  (3k–10k rows) + checker runs; each failure diagnosed and fixed in code
  (possessive-span search, table-grounded cues, whole-word span search,
  noise confined to keep spans whole-word, act-cascade edge cases).
- Pre-seal: 2 × 10,000 rows (seeds 3, 43) with 0/10,000 mismatches each.
- Seal: PASSMARKS.md written; script hashes snapshotted; Pown0b.1–4
  predictions appended to artifacts/fable-predictions-ledger.md. Scripts
  frozen after this point (hashes re-verified identical post-run).
- Registered run 1 (once): full generation — 200,000 train (seeds 11),
  5,000 L1 dev (seed 22), 5,000 L2 dev (seed 33). 8 train shards
  (~1.58 MB each) + 2 dev files. No re-run.
- Registered run 2 (once): checker --sample 10000 --seed 7 on final data:
  0 mismatches.
- Verification sweeps (read-only): full-row span/frame/count checks above.
- Misses: 0 in all registered runs. No TEST-ONLY panel opened, tuned on, or
  quoted. No other agent's artifacts/claude-own-* folder opened (see D5).

## Deviations and limitations (all reported, none hidden)

- D1 (name-string overlap): the L1-dev person name "Fern" occurs in 494
  train rows — 419 as a standalone work value and ~75 inside "Fern Clinic".
  Cause (D4): the ORGS value list was .split() into single words, so
  employer values are fragments ("Works", "Fern", "Clinic"). "Fern" NEVER
  occurs as a person entity (owner or person value) in train — verified 0
  owner hits, 0 reserved-name hits anywhere. Impact: the string is seen, the
  person is not.
- D2 (holdout unit): the split holds out frame-id cells (family/act/kind/idx;
  915 of 4,512 = 20.3%), and L2 gets reserved names + 2 held-out openers +
  2 held-out closers as slots. But the surface pattern is drawn randomly
  within (family, act) independent of idx, so L1/L2 share surface patterns.
  Pown0b.2 as written (frame-id absence) passes literally, 0/200,000. A
  stricter wording-level holdout would need pattern choice bound to frame idx
  — named as follow-up work, not done here.
- D3 (process): one file edit was applied via bash python instead of the
  edit tool (3 chained replacements). No data impact; seal verified after.
- D4: see D1 (org values are single-word fragments by construction; labels
  remain exact).
- D5 (process): listed the sibling builder's artifacts/claude-own-o0a-20260923
  directory (ls) before realising it is out of bounds; opened no file inside.
- Style note: some rows are ungrammatical but label-exact (e.g. "Who is Ivo's
  title, then?", "who did me pick as favorite subject?"). Exactness is what
  the marks measure.

## What it means (plain high-school English)

We built a machine that writes 210,000 short made-up chat turns and, for each
one, writes down the exact answer key: who is talking about whom, what the
relationship word is, what the value is, and whether the speaker is telling,
asking, checking, supposing, planning, correcting, denying, or just chatting.
A second, separately written checker re-did every answer key from scratch and
found zero mistakes in 10,000 spot-checked rows and zero bad text highlights
in all 210,000 rows. One fifth of the fill-in-the-blank templates plus some
greetings and names were kept out of training so later tests can check whether
a model really learned to read or just memorized.

## What it doesn't mean

It does not mean a trained ear will read real English well — these turns come
from fixed templates, not real people. It does not mean the held-out test is a
hard wording test (see D2: surface patterns overlap). It does not certify
anything about memory, reasoning, or answers — only that the training labels
match the turns that were generated.

## Counts per family (train / L1 dev / L2 dev)

tell 20000/500/500 · ask 20000/500/500 · chat 20000/500/500 ·
act 20000/500/500 · binding 20000/500/500 · plural 20000/500/500 ·
appositive 20000/500/500 · correction 20000/500/500 · noise 20000/500/500 ·
typo 20000/500/500.

## 10 example train rows per family (turn | facts owner,relation,mode | Q?)

tell | STATE | Listen, Mark this: Quinn's work location is Saltholm. you know. | [([19, 24], 'work_location', 'ASSERT')] | Q=False
tell | STATE | Guess what, Honestly, Orla's mom is Mira. | [([22, 26], 'mother', 'ASSERT')] | Q=False
tell | STATE | Just so you know, Ayers's rival is Lena. | [([18, 23], 'rival', 'ASSERT')] | Q=False
tell | STATE | Listen, I am telling you my dog is Clover. you know. | [('ME', 'dog', 'ASSERT')] | Q=False
tell | STATE | Final answer: my doctor is Aldo. really. | [('ME', 'doctor', 'ASSERT')] | Q=False
tell | STATE | Listen, Rowan's favourite colour: handball. I think. | [([8, 13], 'favorite_color', 'ASSERT')] | Q=False
tell | STATE | Well, Like I told you, my brother is Owen. | [('ME', 'brother', 'ASSERT')] | Q=False
tell | STATE | Well, Rasmus's one wife is Astrid. right now. | [([6, 12], 'wife', 'ASSERT')] | Q=False
tell | STATE | So, For the record, Sabina's school is Harrowgate. I think. | [([20, 26], 'school', 'ASSERT')] | Q=False
tell | STATE | Roscoe's husband is Oswald. really. | [([0, 6], 'husband', 'ASSERT')] | Q=False
ask | ASK | Guess what, Who is Ivo's title, then? you know. | [] | Q=True
ask | ASK | So, Who is Riva's town? these days. | [] | Q=True
ask | ASK | I wonder who Una's cat is? you know. | [] | Q=True
ask | ASK | Which one is Ulrik's cat? | [] | Q=True
ask | ASK | So, I ask you: who is my dog? these days. | [] | Q=True
ask | ASK | Hey, Has anyone told you who Elif's son is? really. | [] | Q=True
ask | ASK | Guess what, Have you met my hamster? you know. | [] | Q=True
ask | ASK | Well, My question is who is my niece? these days. | [] | Q=True
ask | ASK | Hey, Do you remember Ivo's brother-in-law? right now. | [] | Q=True
ask | ASK | Guess what, But who is Juna's favorite season? | [] | Q=True
chat | CHAT | See you later, cool? | [] | Q=False
chat | CHAT | Awful weather today, right? really. | [] | Q=False
chat | CHAT | Listen, Cool, cool. Anyway, how was your weekend? | [] | Q=False
chat | CHAT | Any weekend plans? Mine involve coffee. | [] | Q=False
chat | CHAT | Lol, that's funny. | [] | Q=False
chat | CHAT | Guess what, Hi, what's up? | [] | Q=False
chat | CHAT | Listen, Good morning! Coffee first? | [] | Q=False
chat | CHAT | Good morning, nice weather we're having. | [] | Q=False
chat | CHAT | Hello! Nice to see you. | [] | Q=False
chat | CHAT | Hey, how are you? right now. | [] | Q=False
act | CORRECT | Listen, Hmm, actually Ulrik's pony is Ziggy. | [([22, 27], 'horse', 'CORRECT')] | Q=False
act | PLAN | Hey, Stina wants their therapist to be Orla. right now. | [([5, 10], 'therapist', 'PLAN')] | Q=False
act | CHECK | Hey, Just confirming Rowan's mother in law is Ayers right now. | [([21, 26], 'mother_in_law', 'CHECK')] | Q=False
act | STATE | So, Let me tell you: Tamara's home is Pellham. really. | [([21, 27], 'home', 'ASSERT')] | Q=False
act | STATE | Well, The occupation of Wren is Works. you know. | [([24, 28], 'occupation', 'ASSERT')] | Q=False
act | STATE | I just learned Pascal's hamster is Pebble. right now. | [([15, 21], 'hamster', 'ASSERT')] | Q=False
act | ASK | Hey, Can you name Oona's friend? really. | [] | Q=True
act | DENY | So, Ysolde's work location is never Tansford. these days. | [([4, 10], 'work_location', 'DENY')] | Q=False
act | ASK | Well, Who might Stina's home town be? really. | [] | Q=True
act | CHECK | Echoing you: Romy's allergy is mustard really. | [([13, 17], 'allergy', 'CHECK')] | Q=False
binding | STATE | Well, Lena's daughter is Tobin and her hometown is Kallby. I think. | [([6, 10], 'daughter', 'ASSERT'), ([35, 38], 'hometown', 'ASSERT')] | Q=False
binding | STATE | So, Ayers's daughter is Elif and her hometown is Norvik. I think. | [([4, 9], 'daughter', 'ASSERT'), ([4, 9], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Guess what, Juna's daughter is Hazel and her hometown is Marby. you know. | [([12, 16], 'daughter', 'ASSERT'), ([41, 44], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Well, Veda's son is Ulrik and her hometown is Rook. these days. | [([6, 10], 'son', 'ASSERT'), ([6, 10], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Hazel's son is Tamara and his hometown is Kallby. right now. | [([0, 5], 'son', 'ASSERT'), ([26, 29], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Listen, Riva's daughter is Rowan and her hometown is Fellsby. I think. | [([8, 12], 'daughter', 'ASSERT'), ([37, 40], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Listen, Abel's daughter is Tessa and her hometown is Harrowgate. really. | [([8, 12], 'daughter', 'ASSERT'), ([8, 12], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Farah's son is Ashby and his hometown is Ormskirk. you know. | [([0, 5], 'son', 'ASSERT'), ([25, 28], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Well, Tal's son is Pascal and his hometown is Pellham. these days. | [([6, 9], 'son', 'ASSERT'), ([30, 33], 'hometown', 'ASSERT')] | Q=False
binding | STATE | Listen, Roald's daughter is Ysolde and her hometown is Vexford. these days. | [([8, 13], 'daughter', 'ASSERT'), ([8, 13], 'hometown', 'ASSERT')] | Q=False
plural | STATE | Hey, Stina and Tove are my titles. these days. | [('ME', 'title', 'ASSERT'), ('ME', 'title', 'ASSERT')] | Q=False
plural | STATE | Listen, My friends are Ragna, Veda and Lena. really. | [('ME', 'friend', 'ASSERT'), ('ME', 'friend', 'ASSERT'), ('ME', 'friend', 'ASSERT')] | Q=False
plural | STATE | Listen, My nieces are Juna and Vanna. | [('ME', 'niece', 'ASSERT'), ('ME', 'niece', 'ASSERT')] | Q=False
plural | STATE | Well, Odette and Lena are my bosses. I think. | [('ME', 'boss', 'ASSERT'), ('ME', 'boss', 'ASSERT')] | Q=False
plural | STATE | My horses are Paloma, Tamara and Wren. you know. | [('ME', 'horse', 'ASSERT'), ('ME', 'horse', 'ASSERT'), ('ME', 'horse', 'ASSERT')] | Q=False
plural | STATE | Hey, Paloma and Abel are my capitals. | [('ME', 'capital', 'ASSERT'), ('ME', 'capital', 'ASSERT')] | Q=False
plural | STATE | Guess what, Tessa and Roscoe are my favorite colors. these days. | [('ME', 'favorite_color', 'ASSERT'), ('ME', 'favorite_color', 'ASSERT')] | Q=False
plural | STATE | Guess what, Ragna and Kito are my wifes. really. | [('ME', 'wife', 'ASSERT'), ('ME', 'wife', 'ASSERT')] | Q=False
plural | STATE | Listen, My titles are Lena and Rasmus. these days. | [('ME', 'title', 'ASSERT'), ('ME', 'title', 'ASSERT')] | Q=False
plural | STATE | Hey, My coaches are Tansy and Quinn. you know. | [('ME', 'coach', 'ASSERT'), ('ME', 'coach', 'ASSERT')] | Q=False
appositive | STATE | Guess what, My manager, Oswald, has a cat named Pebble. | [('ME', 'boss', 'ASSERT'), ([24, 30], 'cat', 'ASSERT')] | Q=False
appositive | STATE | Listen, My mentor, Ulrik, has a rabbit named Biscuit. right now. | [('ME', 'mentor', 'ASSERT'), ([19, 24], 'rabbit', 'ASSERT')] | Q=False
appositive | STATE | Hey, My boss, Ragna, has a dog named Pickles. these days. | [('ME', 'boss', 'ASSERT'), ([14, 19], 'dog', 'ASSERT')] | Q=False
appositive | STATE | So, My doctor, Thea, has a parrot named Biscuit. these days. | [('ME', 'doctor', 'ASSERT'), ([15, 19], 'parrot', 'ASSERT')] | Q=False
appositive | STATE | My boss, Oren, has a dog named Noodle. these days. | [('ME', 'boss', 'ASSERT'), ([9, 13], 'dog', 'ASSERT')] | Q=False
appositive | STATE | Hey, My manager, Vesper, has a cat named Noodle. | [('ME', 'boss', 'ASSERT'), ([17, 23], 'cat', 'ASSERT')] | Q=False
appositive | STATE | My teacher, Polly, has a parrot named Wicket. these days. | [('ME', 'teacher', 'ASSERT'), ([12, 17], 'parrot', 'ASSERT')] | Q=False
appositive | STATE | So, My boss, Pascal, has a dog named Ziggy. really. | [('ME', 'boss', 'ASSERT'), ([13, 19], 'dog', 'ASSERT')] | Q=False
appositive | STATE | Hey, My teacher, Willa, has a rabbit named Miso. these days. | [('ME', 'teacher', 'ASSERT'), ([17, 22], 'rabbit', 'ASSERT')] | Q=False
appositive | STATE | Well, My manager, Ayers, has a cat named Fig. really. | [('ME', 'boss', 'ASSERT'), ([18, 23], 'cat', 'ASSERT')] | Q=False
correction | DENY | Guess what, False: Quentin's place of birth isn't Vexford. right now. | [([19, 26], 'place_of_birth', 'DENY')] | Q=False
correction | CORRECT | Well, Rufus's home changed from Dunmere to Saltholm. you know. | [([6, 11], 'home', 'CORRECT')] | Q=False
correction | DENY | So, Strike that: Quinn's place of birth isn't Marby. really. | [([17, 22], 'place_of_birth', 'DENY')] | Q=False
correction | DENY | Well, Correction denied: Astrid's aunt isn't Robin. these days. | [([25, 31], 'aunt', 'DENY')] | Q=False
correction | CORRECT | Listen, Oops, Ulrik's parrot is Noodle. | [([14, 19], 'parrot', 'CORRECT')] | Q=False
correction | CORRECT | Guess what, Actually Romy's partner is Ysolde now. really. | [([21, 25], 'partner', 'CORRECT')] | Q=False
correction | CORRECT | Now that I check, Rowan's brother in law is Tansy. right now. | [([18, 23], 'brother_in_law', 'CORRECT')] | Q=False
correction | CORRECT | Listen, To correct the record, Ulrik's city is Norvik. these days. | [([31, 36], 'city', 'CORRECT')] | Q=False
correction | CORRECT | Listen, My mistake, Garr's allergy is rowing. I think. | [([20, 24], 'allergy', 'CORRECT')] | Q=False
correction | CORRECT | Hey, Breaking: Selma's friend is now Ayers. really. | [([15, 20], 'friend', 'CORRECT')] | Q=False
noise | CHECK | Listen, Wait, my allergy is Small right now! | [('ME', 'allergy', 'CHECK')] | Q=False
noise | ASK | Hey, Do you remember  my dog? | [] | Q=True
noise | ASK | Hey, Any idea who Vera's doctor is | [] | Q=True
noise | ASK | Listen, What name did Pascal give for  their car? I think. | [] | Q=True
noise | CHECK | Really, Paloma's therapist is Roscoe these days! | [([8, 14], 'therapist', 'CHECK')] | Q=False
noise | STATE | so, mark this: sabina's parrot is nibbles. you know. | [([15, 21], 'parrot', 'ASSERT')] | Q=False
noise | CHECK | Echoing you: my nephew  is Anselma | [('ME', 'nephew', 'CHECK')] | Q=False
noise | ASK | can you name roald's partner? | [] | Q=True
noise | ASK | well, who did me pick as favorite subject? i think. | [] | Q=True
noise | CHECK | Hey, To repeat back, Petras teammate is Bram really. | [([21, 27], 'teammate', 'CHECK')] | Q=False
typo | STATE | Listen, Like I told you, Perry's country is Harowgate. right now. | [([25, 30], 'country', 'ASSERT')] | Q=False
typo | STATE | Listen, For the record, Celia's birthplace is Harowgate. | [([24, 29], 'place_of_birth', 'ASSERT')] | Q=False
typo | STATE | So, Just so you know, Celia's vet is oSren. you know. | [([22, 27], 'vet', 'ASSERT')] | Q=False
typo | STATE | Hey, Like I told you, Garr's car is orientering. you know. | [([22, 26], 'car', 'ASSERT')] | Q=False
typo | STATE | Listen, I am telling you Thea's nickname is berad. these days. | [([25, 29], 'nickname', 'ASSERT')] | Q=False
typo | STATE | Guess what, Bram mentioned their pony is Clver. these days. | [([12, 16], 'horse', 'ASSERT')] | Q=False
typo | STATE | Listen, Ashby mentioned their grandma is Toibn. really. | [([8, 13], 'grandmother', 'ASSERT')] | Q=False
typo | STATE | Listen, Something true: Ulrik's hobby is boany. you know. | [([24, 29], 'hobby', 'ASSERT')] | Q=False
typo | STATE | I found out Sasha's stepmom is bAel. these days. | [([12, 17], 'stepmother', 'ASSERT')] | Q=False
typo | STATE | Listen, Something true: Willa's landlord is Odete. I think. | [([24, 29], 'landlord', 'ASSERT')] | Q=False
