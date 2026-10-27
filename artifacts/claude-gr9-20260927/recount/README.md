# Blind recount of practice run r1 (2026-09-27)
Done by a separate agent that did not see the owner's count code, count logs, RESULT files or run-r1/logs/.
Truth from dev/{squares,seen,heldout,lookalikes}.jsonl; reads from run-r1/{L9_squares,L9_seen,L9_heldout,L9_lookalikes,L7_heldout,L7_lookalikes}.jsonl.
Counted: id match per file; greedy "grid" exact/none/wrong; lookalike false squares by format (train/H/S); heldout exact on marks . * = :; L9 "pick" exact; marks M1-M4, TOO-EASY, PROVED-WRONG, outcome; L9 non-exact ids with sizes.
Code is recount.py (standard library only); `python3 recount.py > output.txt` reproduces output.txt.
