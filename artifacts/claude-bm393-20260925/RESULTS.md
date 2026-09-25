# bm-393 RESULTS: does search find the chat line that holds the answer? (after using LoCoMo for development)

Run 2026-09-25 ~19:55 UTC in the cloud container, CPU, 1 min 49 s, $0 (PLAN.md and the script were sealed first,
main 17d7de294). Counts only. Check: for 497 questions (3 chats) the BM25 top 10 here equals the turns bm-390's Rb
arm was shown, 497 of 497.

## Recall at 10 (an evidence turn is in the retriever's top 10 of that chat)
| Category (questions with usable evidence) | BM25 any | BM25 all | MiniLM any | MiniLM all |
|---|---|---|---|---|
| 1 multi-hop (281) | 33.5% | 5.0% | 59.1% | 12.1% |
| 2 temporal (320) | 57.2% | 51.2% | 57.2% | 51.9% |
| 3 open-domain (89) | 29.2% | 13.5% | 42.7% | 21.3% |
| 4 single-hop (841) | 58.1% | 55.4% | 56.5% | 54.2% |
| **1-4 (1,531)** | **51.7%** | 42.8% | **56.3%** | 44.1% |

At 20: BM25 any 61.5%, MiniLM any 67.3%. Either retriever at 10: 72.7%; at 20: 80.9%.
9 of 1,540 questions have no usable evidence id (9 ids name no turn). Category 5 is not meaningful here: bm-390's
category-5 query text contains the answer options, which BM25 matches (95.3%); MiniLM got the bare question (33.4%).

## Finding decides most of Rb's score
Rb's bm-390 F1 on categories 1-4: **38.33** on the 792 questions where BM25's top 10 held an evidence turn, **10.89**
on the 739 where it did not (all evidence found: 41.76 on 656, else 12.58 on 875).

## Predictions
- E1 (BM25 any@10 between 50% and 80%): right, 51.7%.
- E2 (MiniLM within 10 points of BM25): right, +4.6 points.
- E3 (multi-hop all@10 under 40% for both): right, 5.0% and 12.1%.
- E4 (Rb's F1 at least 15 points higher when found): right, +27.4 points.

## What it means (for whoever builds episodic memory)
- Finding is a big lever: about half the questions don't get their evidence into a top 10, and those score about 11.
  Using both retrievers, or a top 20, finds 73-81%.
- The learned MiniLM beats BM25 on multi-hop (59.1% vs 33.5%) and open questions; they tie on single-hop and dates.
- Multi-hop almost never gets all its evidence in one search (5-12%), so it needs a second search guided by the first
  result, which is reasoner work.
- Answering is a lever too: even with the evidence in view, the plain 1B's F1 is about 38.

Deviation: the script's docstring says MiniLM's query is "the question as asked in bm-390"; the code uses the bare
question (no category-2 date hint, no category-5 options). BM25 uses bm-390's exact query text, as registered.
