# NOTE gr-2 diagnosis for the Thread manager (2026-09-26 19:20 UTC; counts from run outputs and panel truth fields only, no panel text read)

- The 7 wrong readings in new formats were all smaller than the true square. Pairs (true size -> read size, format): 4->3
  (format 10, broken), 4->3 (15), 6->3 (3), 6->3 (3), 6->3 (3, broken), 6->5 (15, broken), 7->6 (15). 5 of the 7 are
  3 x 3, the smallest size allowed. They come from 3 formats: 03 (3 of 3 wrong), 15 (3) and 10 (1).
- The 3 false squares in lookalikes were read at sizes 3, 3 and 4.
- On the 100 squares in 358b3's layouts, all 100 readings had the right size.
- Suggested: the search, not a size prior from practice, makes these errors. A 3 x 3 square needs only 9 cell tokens,
  so when the head tags a new format's tokens unevenly, a small sub-square can beat "no cells". Nothing learned counts
  rows. The search counts them, and it is free to choose any size.
- "None" is not a threshold. It wins when the tagging with no cells is more probable than the best square. Nothing was
  set on DEV.
- gr-2 trained nothing. It reused gr-1's head, whose practice data was the 1B's own wrapper words, code-built squares,
  code labels and the code-inserted blank mark, with no Claude-written text.
