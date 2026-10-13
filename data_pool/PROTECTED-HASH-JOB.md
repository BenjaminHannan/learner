# Job: hash the protected panels (hashes only). For Ben, or the Mac session with Ben's typed OK.

Why: the data pool must not contain text that also sits in a protected test panel. The check compares 13-word windows. To run it, the
panels' text is turned into 64-bit hashes ON YOUR MACHINE; only the hash file leaves. Nobody (including Claude) reads the panels.
The command below never prints a string from a file and never writes one: it prints counts and an 8-character fingerprint of each
file name. It hashes every string field, so nobody has to open a file to find the right field (answers get hashed too; that only makes
the check stricter).

Needs python3 and numpy only. Do NOT open, cat, head or paste any panel file. Do NOT run any scorer on them.

## 1. Get the tool (no panel data in it)
```
git clone --branch claude/data-pool-8b https://github.com/BenjaminHannan/learner.git ~/data-pool-8b   # or: git -C <existing clone> fetch origin claude/data-pool-8b && git -C <clone> checkout claude/data-pool-8b
cd ~/data-pool-8b
python3 -m unittest data_pool.tests.test_overlap13      # expect: Ran 5 tests ... OK
```

## 2. Find the protected files by NAME only (do not open them)
Run in the beautiful-model checkout on the Mac, and (via `ssh benspc`) in the PC checkout and anything under C:\Users\benja:
```
find ~/ -type f \( -iname '*gold-private*' -o -iname '*reserved*' -o -iname '*blind*' \) \( -name '*.json' -o -name '*.jsonl' \) -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/site-packages/*' 2>/dev/null
```
(Windows: `dir /s /b C:\\Users\\benja\\*gold-private*.json* C:\\Users\\benja\\*reserved*.json* C:\\Users\\benja\\*blind*.json*`.)
Also include any folder named `panels`, `reserved` or `blind` in those checkouts (the tool takes folders and reads every .json / .jsonl inside).

Known protected files that live in git (get them as local files without reading them):
```
mkdir -p ~/protected-in
git -C ~/data-pool-8b show origin/main:artifacts/claude-notepanel378-20260925/blind_dialogs.jsonl   > ~/protected-in/blind_dialogs.jsonl
git -C ~/data-pool-8b show origin/main:artifacts/claude-notepanel378-20260925/blind_questions.jsonl > ~/protected-in/blind_questions.jsonl
git -C ~/data-pool-8b show origin/main:artifacts/claude-readpanel371-20260925/blind_input.jsonl     > ~/protected-in/blind_input.jsonl
git -C ~/data-pool-8b show origin/claude/amazing-rubin-97wdjx:artifacts/claude-readpanel371-20260925/changed_blind.jsonl > ~/protected-in/changed_blind.jsonl
git -C ~/data-pool-8b show origin/claude/critical-thinking-data-128-outputs:data-for-design/critical-thinking-128/questions_and_scoring/GOLD-PRIVATE-v1.json > ~/protected-in/GOLD-PRIVATE-v1.json
```
(the `show ... > file` redirects the bytes straight into a file; nothing is printed. The reserved user panels are not in git, so the
`find` above is the only way to locate them. If `find` turns up nothing for "reserved", say so; do not guess.)

## 3. Hash (counts only)
```
cd ~/data-pool-8b
python3 data_pool/overlap13.py index --owner-hash-only --out ~/protected_hashes.npz  ~/protected-in  <each folder or file the find listed>
```
Output looks like `{"files": N, "hashes": M, "per_file": [{"file_sha8": "ab12cd34", "texts": 16, "ignored_short": 16}, ...]}`.
A file with `"error"` instead of `texts` failed to parse (not JSON/JSONL); tell the thread which sha8, nothing else.
Very short panels (arithmetic questions under 8 words) give `ignored_short` = `texts` and contribute 0 hashes. That is expected; it means the 13-gram rule cannot see them.

## 4. Send back only the .npz
```
cp ~/protected_hashes.npz data_pool/panels/protected_hashes.npz
git add data_pool/panels/protected_hashes.npz && git commit -m "Protected panel hashes (hashes only, no text)" && git push origin claude/data-pool-8b
rm -rf ~/protected-in
```
Report in the thread: the printed JSON (it has no text), and the list of file NAMES found by `find` (names, not contents).

## 5. What the data-pool thread then does (CPU)
`overlap13.py merge --out all.npz data_pool/panels/panel_hashes_all.npz data_pool/panels/protected_hashes.npz`, re-scan the web slices, drop every
hit document, and report the number dropped. Pass: 0 windows left in any kept document. Proved wrong: more than 0.1% of a slice dropped (then re-cut from the next shard).
