# Verifier probe table, exp 236 vs 221 (25 held-out dialogs, 228 guard installed in harness)

Raw: out236.json, out221.json, run236.log, run221.log. Runner: run236v.py. Dialogs: probes.json.

| dialog | turn | 236 reply | 221 reply (if different) |
|---|---|---|---|
| D00 | Tavi Orlen's city is Quarnby. | Saved: Tavi Orlen's city is Quarnby. |  |
| D00 | Tavi Brusk's city is Mellowford. | Saved: Tavi Brusk's city is Mellowford. |  |
| D00 | Tavi Cadden's city is Ostrel. | Saved: Tavi Cadden's city is Ostrel. |  |
| D00 | What is Tavi's city? | Which Tavi do you mean: Tavi Brusk, Tavi Cadden or Tavi Orlen? | I don't know anyone called Tavi. |
| D00 | Forget Tavi Brusk's city. | Forgotten: Tavi Brusk's city. |  |
| D00 | What is Tavi's city? | Which Tavi do you mean: Tavi Cadden or Tavi Orlen? | I don't know anyone called Tavi. |
| D00 | Where does Tavi live? | Which Tavi do you mean: Tavi Cadden or Tavi Orlen? | I don't know anyone called Tavi. |
| D00 | STORED (236) | [['Tavi Orlen', 'city', 'Quarnby'], ['Tavi Cadden', 'city', 'Ostrel']] | same |
| D01 | Pell Arvo's employer is Kestrine. | Saved: Pell Arvo's employer is Kestrine. |  |
| D01 | Pell Dunwick's employer is Hollowmere. | Saved: Pell Dunwick's employer is Hollowmere. |  |
| D01 | Pell Garsh's employer is Vantrel. | Saved: Pell Garsh's employer is Vantrel. |  |
| D01 | Pell Yorin's employer is Sabbeth. | Saved: Pell Yorin's employer is Sabbeth. |  |
| D01 | Who is Pell's employer? | Which Pell do you mean: Pell Arvo, Pell Dunwick or Pell Garsh? | I don't know anyone called Pell. |
| D01 | Who is Pell Yorin's employer? | Pell Yorin's employer is Sabbeth. |  |
| D01 | STORED (236) | [['Pell Arvo', 'employer', 'Kestrine'], ['Pell Dunwick', 'employer', 'Hollowmere'], ['Pell Garsh', 'employer', 'Vantrel'], ['Pell Yorin', 'employer', 'Sabbeth']] | same |
| D02 | Idris Vane's employer is Corvel. | Saved: Idris Vane's employer is Corvel. |  |
| D02 | Idris Hollan's employer is Brisby. | Saved: Idris Hollan's employer is Brisby. |  |
| D02 | Actually, Idris Vane's employer is Tamsworth. | Saved: Idris Vane's employer is Tamsworth. |  |
| D02 | Who is Idris's employer? | Which Idris do you mean: Idris Hollan or Idris Vane? | I don't know anyone called Idris. |
| D02 | Forget Idris Hollan. | I don't know anyone called Idris. |  |
| D02 | Who is Idris's employer? | Which Idris do you mean: Idris Hollan or Idris Vane? | I don't know anyone called Idris. |
| D02 | STORED (236) | [['Idris Vane', 'employer', 'Tamsworth'], ['Idris Hollan', 'employer', 'Brisby']] | same |
| D03 | Corla Hesk's spouse is Brannoc. | Saved: Corla Hesk's spouse is Brannoc. |  |
| D03 | Brannoc Tull's city is Varnholt. | Saved: Brannoc Tull's city is Varnholt. |  |
| D03 | What is Brannoc's city? | I don't know Brannoc's city. |  |
| D03 | Who is Corla's spouse? | Corla Hesk's spouse is Brannoc. | I don't know anyone called Corla. |
| D03 | Who is Brannoc? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D03 | STORED (236) | [['Corla Hesk', 'spouse', 'Brannoc'], ['Brannoc Tull', 'city', 'Varnholt']] | same |
| D04 | Mirel Stroud's employer is Quillon. | Saved: Mirel Stroud's employer is Quillon. |  |
| D04 | who is mirel's employer? | I don't know anyone called mirel. |  |
| D04 | Who is mirel's employer? | I don't know anyone called mirel. |  |
| D04 | WHO IS MIREL'S EMPLOYER? | I don't know anyone called MIREL. |  |
| D04 | What is MIREL's employer? | I don't know anyone called MIREL. |  |
| D04 | STORED (236) | [['Mirel Stroud', 'employer', 'Quillon']] | same |
| D05 | Mara Quell's boss is Otto Rennick. | Saved: Mara Quell's boss is Otto Rennick. |  |
| D05 | Otto Rennick's city is Fawnmoor. | Saved: Otto Rennick's city is Fawnmoor. |  |
| D05 | Where does Mara's boss live? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D05 | What is the city of Mara's boss? | I don't know anyone called the city of Mara Quell. | I don't know anyone called Mara. |
| D05 | Who is Mara's boss? | Mara Quell's boss is Otto Rennick. | I don't know anyone called Mara. |
| D05 | Whose boss is Otto? | Otto Rennick is the boss of Mara Quell. (worked out backwards) | I don't know anyone whose boss is Otto. |
| D05 | Is Mara's boss Otto? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D05 | STORED (236) | [['Mara Quell', 'boss', 'Otto Rennick'], ['Otto Rennick', 'city', 'Fawnmoor']] | same |
| D06 | Sorrel Ambry's city is Pellam. | Saved: Sorrel Ambry's city is Pellam. |  |
| D06 | Sorrel Ambry's employer is Grismoor. | Saved: Sorrel Ambry's employer is Grismoor. |  |
| D06 | Tell me about Sorrel? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D06 | Tell me about Sorrel. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D06 | Is Sorrel's city Pellam? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D06 | Is Sorrel's city Varnholt? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D06 | Does Sorrel work at Grismoor? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D06 | STORED (236) | [['Sorrel Ambry', 'city', 'Pellam'], ['Sorrel Ambry', 'employer', 'Grismoor']] | same |
| D07 | Wendel Faro's city is Ashcombe. | Saved: Wendel Faro's city is Ashcombe. |  |
| D07 | Wendel Pruitt's city is Lindqvay. | Saved: Wendel Pruitt's city is Lindqvay. |  |
| D07 | __RESTART__ | (restarted) |  |
| D07 | What is Wendel's city? | Which Wendel do you mean: Wendel Faro or Wendel Pruitt? | I don't know anyone called Wendel. |
| D07 | Wendel Faro's employer is Tessit. | Saved: Wendel Faro's employer is Tessit. |  |
| D07 | __RESTART__ | (restarted) |  |
| D07 | Who is Wendel's employer? | Which Wendel do you mean: Wendel Faro or Wendel Pruitt? | I don't know anyone called Wendel. |
| D07 | STORED (236) | [['Wendel Faro', 'city', 'Ashcombe'], ['Wendel Pruitt', 'city', 'Lindqvay'], ['Wendel Faro', 'employer', 'Tessit'], ['Wendel Faro', 'city', 'Ashcombe'], ['Wendel Pruitt', 'city', 'Lindqvay'], ['Wendel Faro', 'employer', 'Tessit']] | same |
| D08 | Anna Pirel's city is Hollinby. | Saved: Anna Pirel's city is Hollinby. |  |
| D08 | What is Ann's city? | I don't know anyone called Ann. |  |
| D08 | Ann Loder's city is Crastow. | Saved: Ann Loder's city is Crastow. |  |
| D08 | What is Ann's city? | Ann Loder's city is Crastow. | I don't know anyone called Ann. |
| D08 | What is Anna's city? | Anna Pirel's city is Hollinby. | I don't know anyone called Anna. |
| D08 | What is Annabel's city? | I don't know anyone called Annabel. |  |
| D08 | STORED (236) | [['Anna Pirel', 'city', 'Hollinby'], ['Ann Loder', 'city', 'Crastow']] | same |
| D09 | Summer Kade's city is Varnholt. | Saved: Summer Kade's city is Varnholt. |  |
| D09 | What is Summer's city? | Summer Kade's city is Varnholt. | I don't know anyone called Summer. |
| D09 | Where do people go in Summer? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D09 | Is it cold in Summer? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D09 | What happens in Summer? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D09 | STORED (236) | [['Summer Kade', 'city', 'Varnholt']] | same |
| D10 | Grant Oswin's employer is Belmark. | Saved: Grant Oswin's employer is Belmark. |  |
| D10 | Grant me one thing: who is Oswin's employer? | Grant Oswin's employer is Belmark. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |
| D10 | Who is Grant's employer? | Grant Oswin's employer is Belmark. | I don't know anyone called Grant. |
| D10 | Can Grant help? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D10 | STORED (236) | [['Grant Oswin', 'employer', 'Belmark']] | same |
| D11 | Mara Quell's city is Tolland. | Saved: Mara Quell's city is Tolland. |  |
| D11 | Mara's employer is Hexwell. | Saved: Mara's employer is Hexwell. |  |
| D11 | Who is Mara Quell's employer? | I don't know Mara Quell's employer. |  |
| D11 | Who is Mara's employer? | Mara's employer is Hexwell. |  |
| D11 | What is Mara's city? | I don't know Mara's city. |  |
| D11 | STORED (236) | [['Mara Quell', 'city', 'Tolland'], ['Mara', 'employer', 'Hexwell']] | same |
| D12 | Mara Quell's city is Tolland. | Saved: Mara Quell's city is Tolland. |  |
| D12 | Mara's city is Dunmore. | Saved: Mara's city is Dunmore. |  |
| D12 | What is Mara Quell's city? | Mara Quell's city is Tolland. |  |
| D12 | What is Mara's city? | Mara's city is Dunmore. |  |
| D12 | STORED (236) | [['Mara Quell', 'city', 'Tolland'], ['Mara', 'city', 'Dunmore']] | same |
| D13 | Mara Quell's city is Tolland. | Saved: Mara Quell's city is Tolland. |  |
| D13 | Mara Soren's city is Pickwell. | Saved: Mara Soren's city is Pickwell. |  |
| D13 | Mara's employer is Hexwell. | Saved: Mara's employer is Hexwell. |  |
| D13 | Who is Mara's employer? | Mara's employer is Hexwell. |  |
| D13 | Who is Mara Quell's employer? | I don't know Mara Quell's employer. |  |
| D13 | Who is Mara Soren's employer? | I don't know Mara Soren's employer. |  |
| D13 | STORED (236) | [['Mara Quell', 'city', 'Tolland'], ['Mara Soren', 'city', 'Pickwell'], ['Mara', 'employer', 'Hexwell']] | same |
| D14 | My name is Kellan. | Saved: your name is Kellan. |  |
| D14 | Kellan Voss's city is Emberly. | Saved: Kellan Voss's city is Emberly. |  |
| D14 | What is Kellan's city? | I don't know your city yet. |  |
| D14 | What is my name? | Your name is Kellan. |  |
| D14 | My city is Rookhaven. | Saved: your city is Rookhaven. |  |
| D14 | What is Kellan's city? | Your city is Rookhaven. |  |
| D14 | STORED (236) | [['USER', 'name', 'Kellan'], ['Kellan Voss', 'city', 'Emberly'], ['USER', 'city', 'Rookhaven']] | same |
| D15 | My name is Dovie Brand. | Saved: your name is Dovie Brand. |  |
| D15 | Dovie Marsh's city is Pellam. | Saved: Dovie Marsh's city is Pellam. |  |
| D15 | What is Dovie's city? | Dovie Marsh's city is Pellam. | I don't know anyone called Dovie. |
| D15 | My city is Crastow. | Saved: your city is Crastow. |  |
| D15 | What is Dovie's city? | Dovie Marsh's city is Pellam. | I don't know anyone called Dovie. |
| D15 | What is my city? | Your city is Crastow. |  |
| D15 | STORED (236) | [['USER', 'name', 'Dovie Brand'], ['Dovie Marsh', 'city', 'Pellam'], ['USER', 'city', 'Crastow']] | same |
| D16 | Corla Hesk's spouse is Brannoc Tull. | Saved: Corla Hesk's spouse is Brannoc Tull. |  |
| D16 | Where does Brannoc live? | I don't know anyone called Brannoc. |  |
| D16 | Who is Brannoc's spouse? | I don't know anyone called Brannoc. |  |
| D16 | Whose spouse is Brannoc? | I don't know anyone whose spouse is Brannoc. |  |
| D16 | STORED (236) | [['Corla Hesk', 'spouse', 'Brannoc Tull']] | same |
| D17 | Tavi Orlen's city is Quarnby. | Saved: Tavi Orlen's city is Quarnby. |  |
| D17 | Tavi Brusk's city is Mellowford. | Saved: Tavi Brusk's city is Mellowford. |  |
| D17 | What is Tavi's city? | Which Tavi do you mean: Tavi Brusk or Tavi Orlen? | I don't know anyone called Tavi. |
| D17 | Tavi Orlen. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D17 | What is Tavi Orlen's city? | Tavi Orlen's city is Quarnby. |  |
| D17 | The first one? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D17 | STORED (236) | [['Tavi Orlen', 'city', 'Quarnby'], ['Tavi Brusk', 'city', 'Mellowford']] | same |
| D18 | Mara Quell's boss is Otto Rennick. | Saved: Mara Quell's boss is Otto Rennick. |  |
| D18 | Otto Rennick's boss is Tavi Brusk. | Saved: Otto Rennick's boss is Tavi Brusk. |  |
| D18 | Tavi Brusk's city is Mellowford. | Saved: Tavi Brusk's city is Mellowford. |  |
| D18 | Where does Mara's boss's boss live? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D18 | Who is the boss of Otto's boss? | I don't know anyone called the boss of Otto Rennick. | I don't know anyone called Otto. |
| D18 | Is Otto's boss Tavi? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D18 | STORED (236) | [['Mara Quell', 'boss', 'Otto Rennick'], ['Otto Rennick', 'boss', 'Tavi Brusk'], ['Tavi Brusk', 'city', 'Mellowford']] | same |
| D19 | Jo-Ann Pell's city is Brindlemoor. | Saved: Jo-Ann Pell's city is Brindlemoor. |  |
| D19 | What is Jo-Ann's city? | Jo-Ann Pell's city is Brindlemoor. | I don't know anyone called Jo-Ann. |
| D19 | Al Rusk's city is Harrowby. | Saved: Al Rusk's city is Harrowby. |  |
| D19 | What is Al's city? | Al Rusk's city is Harrowby. | I don't know anyone called Al. |
| D19 | What is Jo's city? | I don't know anyone called Jo. |  |
| D19 | STORED (236) | [['Jo-Ann Pell', 'city', 'Brindlemoor'], ['Al Rusk', 'city', 'Harrowby']] | same |
| D20 | Mara Quell's city is Tolland. | Saved: Mara Quell's city is Tolland. |  |
| D20 | Otto Rennick's city is Tolland. | Saved: Otto Rennick's city is Tolland. |  |
| D20 | Otto Brisk's city is Fenwick. | Saved: Otto Brisk's city is Fenwick. |  |
| D20 | Is Mara's city the same as Otto's? | Which Otto do you mean: Otto Brisk or Otto Rennick? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |
| D20 | Do Mara and Otto live in the same city? | Which Otto do you mean: Otto Brisk or Otto Rennick? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |
| D20 | Who lives in Tolland? | Mara Quell's city is Tolland. Otto Rennick's city is Tolland. (worked out backwards) |  |
| D20 | STORED (236) | [['Mara Quell', 'city', 'Tolland'], ['Otto Rennick', 'city', 'Tolland'], ['Otto Brisk', 'city', 'Fenwick']] | same |
| D21 | Florence Adair's city is Pellam. | Saved: Florence Adair's city is Pellam. |  |
| D21 | Pellam Stroud's city is Florence. | Saved: Pellam Stroud's city is Florence. |  |
| D21 | What is Florence's city? | I don't know anyone called Florence. |  |
| D21 | What is Pellam's city? | I don't know anyone called Pellam. |  |
| D21 | Where does Florence live? | I don't know anyone called Florence. |  |
| D21 | STORED (236) | [['Florence Adair', 'city', 'Pellam'], ['Pellam Stroud', 'city', 'Florence']] | same |
| D22 | Mara Quell's employer is Hexwell. | Saved: Mara Quell's employer is Hexwell. |  |
| D22 | Mara's employer is Brisby? | Mara Quell's employer is Hexwell. | Was that a question? |
| D22 | Who is Mara Quell's employer? | Mara Quell's employer is Hexwell. |  |
| D22 | Mara's employer is not Hexwell? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? |  |
| D22 | Who is Mara's employer? | Mara Quell's employer is Hexwell. | I don't know anyone called Mara. |
| D22 | STORED (236) | [['Mara Quell', 'employer', 'Hexwell']] | same |
| D23 | Kip Dorran's city is Welsby. | Saved: Kip Dorran's city is Welsby. |  |
| D23 | Where does Kip Live? | I don't know anyone called Kip. |  |
| D23 | Does Kip Like Welsby? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D23 | Where does Kip live, Kip Dorran? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |  |
| D23 | Where does kip live? | I don't know anyone called kip. |  |
| D23 | STORED (236) | [['Kip Dorran', 'city', 'Welsby']] | same |
| D24 | Tavi Orlen's city is Quarnby. | Saved: Tavi Orlen's city is Quarnby. |  |
| D24 | Tavi Brusk's city is Mellowford. | Saved: Tavi Brusk's city is Mellowford. |  |
| D24 | Actually, Tavi Brusk's city is Quarnby. | Saved: Tavi Brusk's city is Quarnby. |  |
| D24 | What is Tavi's city? | Which Tavi do you mean: Tavi Brusk or Tavi Orlen? | I don't know anyone called Tavi. |
| D24 | Is Tavi's city Quarnby? | Which Tavi do you mean: Tavi Brusk or Tavi Orlen? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? |
| D24 | STORED (236) | [['Tavi Orlen', 'city', 'Quarnby'], ['Tavi Brusk', 'city', 'Quarnby']] | same |
