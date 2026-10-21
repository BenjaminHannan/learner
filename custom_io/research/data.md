# data (Sonnet reader, 2026-10-05)

SKILLS CURRICULUM AS A FROM-SCRATCH BENCHMARK (seed 1 build; computed by me from the files unless marked "git")

0. FACTS. 38 families, 8 levels, 0 verify failures, 200,000 unique train prompts, no dev prompt in train. Dev (40 rows per family): in_dist 1360 (34 families), answer 1200 (30), frame 1360 (34), vocab 800 (20), variant 1320 (33), family 160 (4). Dev can be enlarged: a scratch rebuild with `--dev-per-cell 200` gave the identical train hash, the old dev rows as per-family prefix, and 6800/6000/6800/4000/6600/800 rows (scratchpad/sk200k_big; drop duplicate prompts). `accepted` always equals [answer].

1. FAMILIES. Format: family, level, skill; sample->answer; type, V, D. Types: N number, W word from prompt, F fixed label, S new string. V = share of train rows whose answer is a whole token of the prompt; D = distinct train answers. HELD = never in train.
copy_word L1 copy; "Echo: sune"->sune; W, V1.00, D4467
letter_ops L1 char lookup; "last letter of perayu?"->u; letter or N, V.01 (substring .64), D23
list_index L1 lookup; "list: lamp, bread, quilt, island. word right before quilt?"->bread; W or N, V.76, D41
arith_bare L2 arithmetic; "30 times 14?"->420; N, V.02, D682
div_exact L2 arithmetic; "88 tiles into 8 piles, each?"->11; N, V.06, D37
story_addsub L2 1-step story; "owned 39 keys, used up 10, now?"->29; N, V0, D691
compare_numbers L2 compare; "56, 90, 45, 36. smallest?"->36; N copied, V1.00, D809
list_stats L2 count/arith; "23, 77, 57, 3: second largest?"->57; N, V.38, D90
digits_parity L2 digits; "Is 3076 odd or even?"->even; F or N, V.37, D29
seq_next L3 rule induction; "4, 8, 14, 22, next?"->32; N, V0, D153
seq_cycle L3 position; "w c q repeats forever. item 7?"->w; W, V1.00, D23
odd_one_out L3 induction+copy; "not belonging: 91, 82, 50, 52, 36"->91; N copied, V1.00, D99
var_chain L4 binding, multi-step; "t = 25. t = t + 7. t = t - 2. t = t * 3. t?"->90; N, V.03, D647
order_chain L4 transitive logic; "Lena older than Quin. Sam older than Lena. Sam older than Quin?"->yes; W or F, V.67, D39
object_track L4 tracking; "Flo holds kettle, Zoe violin, swap, swap again. Zoe holds?"->violin; W, V1.00, D42
state_update L4 multi-step; "jar 11; 6 out, 3 in, 7 in. now?"->15; N, V.05, D84
table_lookup L4 lookup+arith; "ribbon: 13; ladder: 8; turtle: 47. larger minus smaller of ladder, turtle?"->39; N or W, V.38, D133
prop_eval L5 logic; "R false, S true, Q true. not (R and S) or Q?"->true; F, D2 (V1.00 only because "true or false" is in the prompt)
syllogism L5 logic, invented categories; "All yarps are nasks. Kela is a yarp. Is Kela a nask?"->yes; F, D2 ("unknown" only held out)
rule_apply L5 rule in prompt; "If light purple, wait; ... light is purple. do?"->wait; W or N, V.39, D91
verify_claim L5 check; "Is 36 - 33 = 13 correct?"->no; F, D2
chain_ops L6 multi-step, 2-3 ops of + - * /; "Ida has 10 keys, loses 3, picks up 37. end?"->44; N (to 4800), V.05, D614
chain_story2 L6 2-step; "9 boxes of 11 pears, gives away 18. now?"->81; N, V.04, D234
backward_solve L6 inverse; "sum 63, differ by 17, larger?"->40; N, V.02, D58
distance_units, percent_rate, table_calc L6 arithmetic; "50 km per hour, 9 hours?"->450; N, V<.15, D57/114/40
unit_convert L6 HELD, given-fact use; "1 supa equals 8 yuro. How many yuro in 13 supa?"->104; N, V0
clock_date L6 HELD, knowledge arithmetic; "6:05 on a 12-hour clock, 133 minutes earlier, as h:mm"->3:52; "Today is Friday. In 39 days?"->Tuesday; S
cipher_map L7 table lookup; "Code: h=2, e=5, c=3, g=6. Decode 5 6 5"->ege; S (letters, or digits with spaces), V0, D1009
fewshot_number_rule L7 induction; "12->48; 18->72. Now 10->?"->40; N, V.05, D159
group_induct L7 induction; "A: 6, 12, 48. B: 47, 82, 51. 32?"->B; F (B 66%), D2
string_transform L7 HELD, word induction; "tupe->eptu; dope->deop. Now kose->?"->ekos; S
op_define L7 HELD, definition use; "x @ y means x*y - x. 11 @ 14?"->143; N
passage_qa L8 binding; "Ana owns a pink tiger. Bo a black river. Color of the river?"->black; W or N, V.67, D73
word_filter L8 count; "Words: yogurt, candle... more than 5 letters?"->6; N 0-7, V.05, D7
kin_chain L8 composition; "A parent of B. B parent of D. D's grandparent?"->A; W or F, V.44, D34
story_chain3 L8 3-step + compare; "Gus had 32, got 2, lost 9, bought 9 times as many as left. bought?"->225; N or W, V.52, D378
In_dist: 61% numeric answers, 16% fixed labels. Shortcuts: syllogism is solved 100% on train and in_dist by "prompt starts with No -> no, else yes" (47.5% on dev/variant); object_track handoff and move_place by "last recipient/place named" (100%). After masking numbers, names, nouns and made-up words, 82% of in_dist prompts have an exact train template (vocab 89%, variant 16%, frame and family 0%).

2. STATS. Characters: train prompts use 77 symbols (51 letters, no capital O; 10 digits; space; 15 punctuation % ' ( ) * + , - . / : ; = > ?). All dev files: 82 (capital O only in dev/vocab; # @ & $ only in dev/family, so no trained embedding). Prompt chars p5/p50/p95/max: train 28/78/142/204; in_dist 31/87/145/198; frame 43/101/160/203; family 47/74/110/136. Answers use 63 symbols; chars: train mean 2.6, p95 6, max 8; dev/family p95 8, max 12.
Words (regex tokens): train 18,496 distinct: 14,093 alphabetic (13,084 made-up syllable words, an open vocabulary; about 490 designed words; about 490 letter strings), 4,388 numbers (to 9994), 15 punctuation. Unseen alphabetic types (token OOV) per dev file: in_dist 30 of 631 (0.2%, all made-up); answer 27 of 520 (0.1%); frame 49 of 636 (7.4%); vocab 144 of 593 (10.1%; 87% of made-up tokens); variant 63 of 606 (4.2%); family 183 of 363 (29.2%). Unseen real words: frame 12 (Please, help, Reply, Answer, just...); variant 35 (multiply, halve, child, grandchild, third..sixth...); family 30 (equals, Define, means, clock, Wednesday..Sunday...).

3. SHIFTS
- answer: 15% of (family, answer) pairs never trained, yet 1045 of 1200 answer strings are train answers of other families, so a shared digit/char decoder has emitted them; only a per-family answer-lookup head fails. Degenerate: word_filter (all 40 rows = "2"), letter_ops (z, j), seq_cycle (3 letters), order_chain (3 names), div_exact (4), digits_parity (6), object_track (6), list_index (7), kin_chain (8). Exclude from means.
- frame: 1349 of 1360 rows differ only by a held-out opener ("Work this out.", "Please help with this.") or closer ("Answer with just the result.", "Reply with the answer only."); train has 10 openers and 6 closers. Tests wrapper robustness only; a reader that memorised wrappers can fail.
- vocab: 20% of names (Eli, Omar, Pia, Zed...), nouns, words, category words, places, colors, and 6 of 30 syllables (do gi ro ti tu za); 97% of rows have an unseen word. Char-level reading with a copy mechanism should work; whole-word embeddings or a closed output vocabulary fail.
- variant: 1078 rows use a never-trained variant, 313 the held-out layout "Question: ... Facts: ..." (242 layout only; all of state_update and story_chain3). Expect transfer on layout-only and on recombinations (arith_bare symbol, div groups, distance time, table_calc cost, chain_ops sub_second, copy_word distractor). New computation is zero-shot: seq geom/alternating, count_above, list_stats sum, num_digits, letter_ops length/nth, word_filter contains, syllogism "unknown" (label never seen), group threshold, fewshot affine.
- family, does the prompt suffice? unit_convert yes: all facts given, only multiply/divide, but "equals ... How many ... in" is new wording; "multiply all numbers in the prompt" gets 27/40 (inverse 0). op_define yes for a human, but a symbol never seen in training. string_transform yes in principle: two examples give the rule (unique against 10 rules), but nothing in train outputs a transformed word; "drop first letter" alone gets 14/40. clock_date NO: needs the 7 weekday names in order (train has only Monday and Tuesday, in story contexts) and 60 min per hour; weekday chance 1/7. Expect near these floors without the family.

4. MULTI-STEP. Best for "beat bare 1.2B": chain_ops (2-3 ops, all of + - * /), chain_story2 (2), story_chain3 three_step (3), state_update (2-5 events), var_chain (1-4 reassignments). Also percent rate_total; dev/variant only: table_calc cost, backward_solve think_of_number; held-out: unit_convert two_hop, op_define nested. Git (01-diag-bare, bare frozen 1.2B, 40 in_dist rows each): direct answer only chain_ops 2, chain_story2 1, state_update 1, var_chain 4 (8/160 = 5%); with worked steps first 25, 32, 29, 28 (114/160 = 71%). Worked equations exist in `steps` for 11 arithmetic families (incl. all five chain ones); other families have labels only.

5. WORLD KNOWLEDGE. No factual knowledge anywhere (category words, units, made-up words are invented). Missing from train and prompt: clock_date (weekday order, 60 min per hour). Learnable lexical knowledge present in train: comparative/superlative sets (older/oldest/youngest...), add/subtract/multiply/divide phrasing, parent->older, odd/even, percent, "per hour", qty x price. Held-out variants use unseen words: child/grandchild (kin_chain needs the inverse of "parent of"), ordinals third to sixth (list_index), multiply/halve (rule_apply), found, greater, outnumber, "think of a number".

6. CURRENT SANDWICH (git). Checkpoint main2 (about 50k updates on this curriculum), job 06-genfix-eval, eval only, 40 rows per family (+-15 points), in_dist only. all/ = 1014/1360 = 74.6% (68.5% before the double-prompt fix). shuf/ (another same-family row's core vectors) = 1012/1360 = 74.4%. zero/ = 0/1360 in every family, even copy_word: a format cue, not a reasoning test.
Per family %: 100: div_exact, object_track, syllogism, distance_units. 95-98: copy_word, list_index, story_addsub, table_calc, kin_chain, passage_qa. 88-92: letter_ops, arith_bare, compare_numbers, rule_apply, percent_rate, backward_solve. 75-85: odd_one_out, order_chain, prop_eval, word_filter, digits_parity (78), group_induct. 55-70: list_stats, table_lookup, fewshot_number_rule (60), story_chain3 (58), verify_claim. 38-45: seq_cycle, seq_next, cipher_map. 10-32: var_chain 30, chain_story2 32, chain_ops 18, state_update 10. The four chain families: 36/160 = 22.5% (bare direct 5%, bare with steps 71%).
Shifts (skills-main2, 100-row subsamples, double-prompt generation): in_dist 72, answer 63, frame 65, vocab 78, variant 50, family 13 (those rows exclude unit_convert). Full family split (plateau eval, double prompt): 39/160 = 24.4%: unit_convert 25/40, op_define 9/40, clock_date 4/40, string_transform 1/40. No gen-fix family numbers exist. unit_convert 25/40 is below the 27/40 multiply-everything floor.

7. PROTOCOL
- Rows: all six dev files (6200), not the old rows[::step][:100] subsample. For headline multi-step claims use the 200-per-cell rebuild (5 chain families x 200 = 1000 rows, +-3 points). Report micro and family-macro means; paired McNemar.
- Rule (existing): norm(s) = ' '.join(s.strip().lower().split()); hit = norm(output) in {norm(a) for a in row['accepted']}. Whole string, no prefix or contains match. Cap decode at 24 chars.
- Floors: train-majority answer per family (in_dist mean 16%; syllogism 68, group_induct 65, verify_claim 57, prop_eval 55), the heuristics above, and an equal-size from-scratch transformer on the same 200k.
- Split dev/variant by layout == labeled_q_first versus variant not in train variants. Report syllogism and object_track separately.
- Multi-step panel: five chain families on in_dist + variant + frame, binned by len(steps) or diff. Mark (fixed in advance): beats bare direct by 20+ points per family; report vs bare with steps separately.
- Lesion: pair dev rows of one family with different answers; swap the reasoner output. Mark: accuracy drops 20+ points and at least half of swapped outputs equal the donor row's answer. Run on in_dist, variant, family. Zeroing is only a format check.

Scratch: /tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/ (sk200k_big/, res_*.json). Git: origin/claude/ultracode-learning-blocker-gh011t (artifacts/ultracode-v4, plateau-diag-v1, skills-main2).
