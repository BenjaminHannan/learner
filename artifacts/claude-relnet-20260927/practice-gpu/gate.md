| arm | seed | lr | weights | train min | dev sums4 | dev grids5 | gate sums4 | gate grids5 | mean rounds (s/g) | cap hits (s/g) | best fixed depth -> gate (s/g) | stop failure |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|
| loop | 0 | 0.001 | 1,645,726 | 7.7 | 200 of 200 | 200 of 200 | 200 of 200 | 199 of 200 | 7.38/9.18 | 3/0 | 4->200/24->199 | no |
| loop | 1 | 0.001 | 1,645,726 | 7.7 | 200 of 200 | 200 of 200 | 199 of 200 | 198 of 200 | 6.87/10.85 | 0/0 | 8->200/12->198 | no |
| relnet | 0 | 0.001 | 1,644,198 | 9.1 | 200 of 200 | 198 of 200 | 200 of 200 | 197 of 200 | 7.05/15.32 | 0/1 | 4->200/12->197 | no |
| relnet | 1 | 0.001 | 1,644,198 | 9.2 | 200 of 200 | 199 of 200 | 200 of 200 | 200 of 200 | 6.61/13.78 | 0/3 | 4->200/12->199 | no |

- seed 0: G1 pass; G2 pass
- seed 1: G1 pass; G2 pass
- **gate verdict (lr 0.001): PASS**
