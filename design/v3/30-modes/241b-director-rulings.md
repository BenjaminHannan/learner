# 241b: director's rulings, 2026-09-23 03:25 UTC (written before any grade, judgment or re-measure exists)

Verified: SEAL 19/19 and SEAL2 4/4 OK from the repo root (main + builder-outbox files). No pre-existing 241b
file was changed; the builder added two copies (claude_mouth241b_devrender_r.py, claude_mouth241b_rer241_r.py).
My recount of the fresh sweep: 1205 rows, 13 acts at 80, AMBIGUOUS 30, 0 "(E…)" codes, 0 "someone"; 120 pairs.

1. **M1 graders.** Two independent Muse graders (A and B), each in 3 parts, blind to each other, to the key and to
   PASSMARKS. M1 passes only if the sealed scorer passes on BOTH grade files (stricter than one grader).
2. **M4 judge.** One fresh Muse judge, blind to pairs-key. Scored with the sealed scorer.
3. **M5 wall.** The registered protocol says "check load first". The builder ran the walls at load 160–220 (its
   deviation D-A), while 241's walls and its own dev walls ran at load ~100 or lower; at that load the run spread
   (40.7–47.1 s) is larger than the gap being measured. Ruling: the walls are re-measured ONCE under the same D6
   protocol (3 alternated runs each, median) with load1 below 40 before each run (wait up to 90 minutes). That
   re-measure replaces the loaded one, whatever it shows. If load never gets below 40 in 90 minutes, the loaded
   +8.1% stands as the registered result and M5 wall is a MISS.
4. **S1.** The 22 decision differences on 241b's own 800 rows are not an S1 failure only if every one is on an
   item whose verdict is unchanged. I will recount them from runs/s1-241b.out myself before ruling.
