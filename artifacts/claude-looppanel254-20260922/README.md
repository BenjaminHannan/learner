# Loop wording panel 254 (TEST-ONLY)

TEST-ONLY. Do not tune on these items. Category-level summary only.

Files: panel.jsonl (160), base138l.jsonl (160, same ids/order), make_panel.py (items + self-checks),
run_base.py (runs base 138l, one fresh work dir per dialog, writes base138l.jsonl), SEAL.sha256.txt.

Families: teach_varied 30, ask_varied 30, both_varied 20, casual 20 (10 T, 10 A), backwards 15,
chain 15, no_save 20, control 10 (5 T, 5 A).

Base 138l base_right: teach_varied 3/30, ask_varied 1/30, both_varied 2/20, casual 1/20,
backwards 8/15, chain 0/15, no_save 20/20, control 10/10. base_wrong_value: 0 in every family.

Quotas (on the scored turn): lowercase 31, typo 17, no-"?" 25, pron 13, first person 50, two-fact 14.
Relations (28): birthplace, boss, brother, cat, city, cousin, daughter, dentist, dog, father,
favorite_color, favorite_food, friend, hobby, hometown, job, language, mother, neighbour, parrot,
school, sister, son, spouse, teacher, tortoise, uncle, workplace.

Acceptance: every plain setup teach in ask_varied, backwards, chain, no_save and control (and casual A)
was saved by the base exactly as gold_store says; no item was replaced. Everyday families were not
filtered by base success.

Scorer notes: casual/control notes start with "T:" or "A:" (teach- vs ask-scored). Tags live in
note as "[tags: ...]" (lower, typo, noq, pron, back, two, user). "user" tag = the turn has a
first-person word. Four backwards items have gold_answer null (honest answer is "don't know").
One backwards item has a two-part gold_answer. Teach items whose turn also states a relation to
the user (cousin, neighbour, dentist, sister, uncle, friend, brother) list that fact in gold_store,
so a system that stores only the other fact fails store_ok.
