# write_copy labels: text vs gold slots (Amendment 4 step 1; data only)

Dev file /tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/sk200k_big/dev/in_dist.jsonl (sha256 3e3a5edb05c7eee8), 6800 rows, 2793 with a gold program. Lengths are the gold operand's digits.
text_result = its text equals an earlier call result (what write_copy labelled a copy); gold_result_only = every gold slot holding the value is a result; disagree = text says copy but a prompt number or constant also holds the value; unambiguous = the new rule (exactly one earlier result, no prompt number or constant); the last column must be 0 (the rule agrees with the gold slots).

## The rows write_copy scores (3000 spread over the file)

| digits | operands | text_result | gold_result_only | disagree | unambiguous | unamb. but gold not one result |
|---|---|---|---|---|---|---|
| 1 | 3673 | 388 | 175 | 213 | 174 | 0 |
| 2 | 5976 | 2145 | 1474 | 671 | 1468 | 0 |
| 3 | 1579 | 473 | 240 | 233 | 240 | 0 |
| 4 | 35 | 31 | 31 | 0 | 31 | 0 |
| 5 | 11 | 11 | 11 | 0 | 11 | 0 |

| digits | answers = a call result | unambiguous | also a prompt number or constant | equals several results |
|---|---|---|---|---|
| 1 | 297 | 179 | 118 | 1 |
| 2 | 1618 | 1432 | 178 | 56 |
| 3 | 626 | 503 | 122 | 50 |
| 4 | 16 | 16 | 0 | 0 |

## All program rows

| digits | operands | text_result | gold_result_only | disagree | unambiguous | unamb. but gold not one result |
|---|---|---|---|---|---|---|
| 1 | 3673 | 388 | 175 | 213 | 174 | 0 |
| 2 | 5976 | 2145 | 1474 | 671 | 1468 | 0 |
| 3 | 1579 | 473 | 240 | 233 | 240 | 0 |
| 4 | 35 | 31 | 31 | 0 | 31 | 0 |
| 5 | 11 | 11 | 11 | 0 | 11 | 0 |

| digits | answers = a call result | unambiguous | also a prompt number or constant | equals several results |
|---|---|---|---|---|
| 1 | 297 | 179 | 118 | 1 |
| 2 | 1618 | 1432 | 178 | 56 |
| 3 | 626 | 503 | 122 | 50 |
| 4 | 16 | 16 | 0 | 0 |

