# 173b — word-names count as names (child of loop173)

Base: loop173 (scripts/fable_loop173_agent.py + fable_fix173_username.py).
Change: only the name-shape test for user-name statements.

(a) After "My name is" / "Call me" / "You can call me", 1-3 letter tokens
count as a name even if in /usr/share/dict/words, except the sealed closed
list (36 phrases: not, not important, a secret, secret, unknown, none,
nothing, later, back, anytime, whatever, anything, maybe, tomorrow, soon,
crazy, stupid, lazy, a nurse, nurse, tired, happy, sick, a teacher,
teacher, from oslo, important, nobody, no one, anyone, someone, sorry,
please, hello, hi, a friend, the boss, my friend) and except values with a
determiner ({a, an, the}) or a digit. "My name is" capitalises lowercase
silently (as 173); "Call me" requires Title-case, so "Call me later" and
"call me back" stay on the loop173 path.

(b) After "I'm" / "I am", 173's conservative rule stays, but the given
list is 173's GIVEN_NAMES plus /usr/share/dict/propernames (1,308 lines).
Lowercase after I'm is never a name.

Structure: scripts/fable_fix173b_username.py (Name173bMixin, standalone,
bypasses loop173's stage only for Call-me-lowercase) stacked outermost in
scripts/fable_loop173b_agent.py as Loop173bEars(Name173bMixin,
Loop173Ears); Loop173bAgentLoop mirrors loop173's tick keyed on the 173b
parser. No 173/166 file edited.

Evidence: all 16 T1c word-names are dict words (173 rejects); propernames
holds grace/dawn/rich/grant/will/mark (so "I'm Grace." names — the brief's
"lacks Grace" is corrected) but not maya/rose/rue/sol/pip/hope/faith/iris/
sky/reed (accepted known miss after I'm).

Marks: T1 52/52 identical vs loop173; T1b 44/45 identical (listed S13
"l-ena" lowercase now clarifies, 0 writes); T1c 42/42; T2 0 wrong writes,
0 non-USER entities; G1/G2/G3 0 moves; G4 < 25 min each.
