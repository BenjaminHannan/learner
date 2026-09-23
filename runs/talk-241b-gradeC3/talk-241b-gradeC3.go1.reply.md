Grading part 3 — verifying sources and reading every reply by hand.
I've read all 415 replies. Now I'll write the grades file.
VERDICT: DONE — part 3 graded. 415 rows (g0831–g1245), 19 marked false, file written to artifacts/claude-grade241b-C-set2-20260923/part3.jsonl (415 lines, ids in order, all unique — verified).

MARKS TABLE (integer counts)
- Rows graded: 415
- Marked grammatical (true): 396
- Marked ungrammatical (false): 19
- Lines in part3.jsonl: 415
- Ids unique / in order: 415 / yes

EVERY FALSE ID WITH REASON (every move)
1. g0856 — rule 4 agreement: "The daughter of Sailniros's coach's boss are Niothgund" (singular subject, "are")
2. g0882 — rule 1 possessive: "Ollstearks grandfather" (missing apostrophe; should be Ollstearks's)
3. g0896 — rule 3 numbers: "I know 7 people" (digit for count under ten)
4. g0944 — rule 4 agreement: "I doesn't know when Trontrom Sudrio Trirbror was born"
5. g0969 — rule 6 doubled word: "Drumstior Drumstior as Sillshil's godmother" (cf. g0852 with single Drumstior)
6. g0983 — rule 4 agreement: "I doesn't know who the tutor of Mithnias is"
7. g0996 — rules 6+5: "developer of Nurnan Krellduths is Nillgen" (lowercase start, missing "The")
8. g1033 — rules 6+5: "boyfriend of Elltend's mother's friend is Emgerk" (lowercase start, missing "The"; cf. correct g1079)
9. g1038 — rule 4 agreement: "I doesn't know who composed Gesail Kanhiothz"
10. g1082 — rule 1 possessive: "Umstorks plumber" (missing apostrophe)
11. g1093 — rules 6+5: "toy of Mearvond Books is a kite" (lowercase start, missing "The"; cf. correct g1096)
12. g1105 — general word choice + raw label: "Buddhist is the religion or worldview of Tallfam Wonha Paidond" ("Buddhist" is a person, not the religion; "religion or worldview" is a raw database label)
13. g1108 — rule 8 machine text: "(E9295)" internal entity code
14. g1151 — raw database label: "the language of work or name of Siolgraith and Balkain"
15. g1152 — rule 4 agreement: "Sterlal Grangrion Faltherk are the architect of …" (singular name-string with "are")
16. g1163 — rule 8 machine text: "(E8889)" internal entity code
17. g1195 — rule 3 numbers: "I know 7 people" (digit for count under ten)
18. g1212 — rule 4 agreement: "I doesn't know who your dog is yet"
19. g1227 — raw database label: "Shendtind's language of work or name is Drirkhiothish"

MISSES / DEVIATIONS
- Misses: none found beyond the 19 above. Every row in g0831–g1245 was read one by one; no script, regex, or search was used to decide; no rows marked in bulk.
- Deviation 1 (PUSH): the task says PUSH the file, but OPUS-RULES line 9 forbids git commits, PRs, and pushes, so I did not commit or push. The file exists on disk in the worktree at artifacts/claude-grade241b-C-set2-20260923/part3.jsonl (verified: 415 lines, 23,342 bytes). It is also invisible to `git status` (likely git-ignored like part1.jsonl), so a git push would not carry it anyway.
- Deviation 2: none other. SHAs matched (stylesheet 16bdf0cf…, rows f4327edbc…), only the two allowed sources were opened, free disk was ~14–15 GB (above the 3 GB floor), no code was run to grade.

WHAT IT MEANS (plain high-school English): Out of 415 replies, 396 are clean, normal English sentences. 19 have clear mistakes a careful editor would fix — mostly "I doesn't", missing apostrophes, sentences starting with a lowercase letter, the digit "7" where the style sheet wants the word "seven", two computer codes like (E9295), two database labels like "language of work or name", one doubled name, and two singular/plural mix-ups.

WHAT IT DOESN'T MEAN: It doesn't mean the facts in the replies are true or false — I only graded grammar, never facts. It doesn't mean the 19 errors are the only problems in the whole set — I only graded rows 831–1245, not the rest.
