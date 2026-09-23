# concept-toy20 interface fixture (ct20-v1)

Synthetic format fixture produced by `scripts/fable_concepttoy20_sim.py fixture`.

* Outer split `fixture` -- **not** a registered pool world, and never a `final` world.
* Families present: c, o -- the mode family M is absent, so this file contains no mode-family example.
* This file carries no learner output, no score and no curve.

## Public record layout, float32 `<f4`, width 44

| offsets | field | width | encoding |
| --- | --- | ---: | --- |
| 0:24 | `public_properties` | 24 | four rows of six, by local public ID |
| 24:29 | `action_id` | 5 | one-hot public ID, all zero at RESET |
| 29:33 | `source_id` | 4 | one-hot i, all zero at RESET |
| 33:38 | `destination_id` | 5 | one-hot j=0..3 or NONE=4 |
| 38:39 | `dose` | 1 | -1/+1 on pulse, zero otherwise |
| 39:40 | `sensor` | 1 | returned y, zero if missing or a QUERY token |
| 40:41 | `sensor_present` | 1 | observation mask, zero on QUERY/RESET |
| 41:44 | `record_type` | 3 | one-hot RESET, QUERY, OBSERVED |

## One support episode -- 17 records, QUERY always before OBSERVED

Properties (four objects x six channels), rounded for reading:

```
object 0: -0.6585 +0.4872 +0.0990 -0.9769 +0.7789 +0.0126
object 1: -0.5777 +0.4900 +0.7342 -0.9508 -0.3765 -0.6737
object 2: -0.9385 -0.6416 +0.7701 -0.6630 +0.6954 -0.2717
object 3: +0.1146 -0.3156 +0.5661 +0.3835 -0.6505 +0.7689
```

| # | record_type | action_id | source_id | destination_id | dose | sensor | sensor_present |
| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| 0 | RESET |  |  | NONE | +0 | +0.000000 | 0 |
| 1 | QUERY | 3 | 1 | NONE | +0 | +0.000000 | 0 |
| 2 | OBSERVED | 3 | 1 | NONE | +0 | -0.126193 | 1 |
| 3 | QUERY | 1 | 2 | NONE | +0 | +0.000000 | 0 |
| 4 | OBSERVED | 1 | 2 | NONE | +0 | -0.155930 | 1 |
| 5 | QUERY | 4 | 3 | NONE | +1 | +0.000000 | 0 |
| 6 | OBSERVED | 4 | 3 | NONE | +1 | +0.494145 | 1 |
| 7 | QUERY | 4 | 2 | NONE | -1 | +0.000000 | 0 |
| 8 | OBSERVED | 4 | 2 | NONE | -1 | -0.681568 | 1 |
| 9 | QUERY | 1 | 1 | NONE | +0 | +0.000000 | 0 |
| 10 | OBSERVED | 1 | 1 | NONE | +0 | -0.153858 | 1 |
| 11 | QUERY | 0 | 2 | NONE | +0 | +0.000000 | 0 |
| 12 | OBSERVED | 0 | 2 | NONE | +0 | +0.359561 | 1 |
| 13 | QUERY | 4 | 3 | NONE | -1 | +0.000000 | 0 |
| 14 | OBSERVED | 4 | 3 | NONE | -1 | +0.000000 | 0 |
| 15 | QUERY | 1 | 2 | NONE | +0 | +0.000000 | 0 |
| 16 | OBSERVED | 1 | 2 | NONE | +0 | +0.402478 | 1 |

Every OBSERVED record with `sensor_present = 0` carries `sensor = 0` exactly.  Every QUERY record carries `sensor = 0` and `sensor_present = 0`, so the target of transition t is absent from the prefix that predicts it.

## One query unit -- record ID `a47c4e4016f899c8-q0000`

`n_records = 16`; the prediction is read at the final QUERY, index 15.  Forecast steps append a QUERY and then a BLANK OBSERVED token, so no intermediate measurement is ever teacher forced.

| # | record_type | action_id | source_id | destination_id | dose | sensor | sensor_present |
| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| 0 | RESET |  |  | NONE | +0 | +0.000000 | 0 |
| 1 | QUERY | 1 | 0 | NONE | +0 | +0.000000 | 0 |
| 2 | OBSERVED | 1 | 0 | NONE | +0 | -0.052994 | 1 |
| 3 | QUERY | 1 | 0 | NONE | +0 | +0.000000 | 0 |
| 4 | OBSERVED | 1 | 0 | NONE | +0 | +0.047362 | 1 |
| 5 | QUERY | 0 | 0 | NONE | +0 | +0.000000 | 0 |
| 6 | OBSERVED | 0 | 0 | NONE | +0 | +0.000000 | 0 |
| 7 | QUERY | 0 | 1 | NONE | +0 | +0.000000 | 0 |
| 8 | OBSERVED | 0 | 1 | NONE | +0 | -0.028788 | 1 |
| 9 | QUERY | 4 | 2 | NONE | +1 | +0.000000 | 0 |
| 10 | OBSERVED | 4 | 2 | NONE | +1 | +0.000000 | 0 |
| 11 | QUERY | 2 | 2 | 1 | +0 | +0.000000 | 0 |
| 12 | OBSERVED | 2 | 2 | 1 | +0 | +0.000000 | 0 |
| 13 | QUERY | 0 | 1 | NONE | +0 | +0.000000 | 0 |
| 14 | OBSERVED | 0 | 1 | NONE | +0 | +0.000000 | 0 |
| 15 | QUERY | 1 | 1 | NONE | +0 | +0.000000 | 0 |

Panel identity, horizon and the target itself are evaluator-only fields; the public file carries an opaque record ID and nothing else.

## Task-B batch shape (label isolation)

A task-B fitting batch carries the SAME 44-wide records as task A, plus two extra arrays:

```
records      float32 (17, 44)   # identical to the task-A tokenization
b_detector   float32 (8, 9)       # public (a,b) query, one row per transition
b_label      float64 (8,)          # TARGET-ONLY field, never concatenated into records
```

`b_label` values never appear anywhere inside `records`; the B readout is a label, never an encoder input.

## Public tensor hashes (dtype, shape, raw little-endian bytes)

| array | sha256 |
| --- | --- |
| `public/797dc8ab408ea8e7/query_detector.npy` | `8f9df403957272002d358d0ee3f53f97b40ff1d6e2c8ff4bcadb9248b650d039` |
| `public/797dc8ab408ea8e7/query_index.npy` | `70a63faea9658297903b33afec2da5cced18e46594ca78d6fb316c90e92015fb` |
| `public/797dc8ab408ea8e7/query_n_records.npy` | `4ed1ba16a8bb819dea02323dfc74b947668421b1044dfdcf0976438563363437` |
| `public/797dc8ab408ea8e7/query_padding_mask.npy` | `2185646e08ff2dba4a4e5faef8abad57637f8cb0eab12ef2995f2925b9a6e4b3` |
| `public/797dc8ab408ea8e7/query_records.npy` | `509975665aea05bb321ea08ea234797fbba863de173530957b683c0128e6d8fa` |
| `public/797dc8ab408ea8e7/support_budget_rung.npy` | `a96fabe0c73e48461698cfb7882c0611d92f6254b324f0a4e3ab0b8d62bc80a1` |
| `public/797dc8ab408ea8e7/support_episode_role.npy` | `cf7b74acf92ced85a85a4af24417939f59381a19baad093badb0ea7dfdbd050e` |
| `public/797dc8ab408ea8e7/support_observed_present.npy` | `7544b13bb474518ac1c91b09add646a3062290364c4e2f05c2edd646663a4c84` |
| `public/797dc8ab408ea8e7/support_observed_target.npy` | `4d9a026759bf42615dfc15320c10421e59e1bc31de2666b42777c341ecba4462` |
| `public/797dc8ab408ea8e7/support_padding_mask.npy` | `a7b5b5eac1880bebf262150dba146b6c768791ba613b393bcdb3af0b743946d7` |
| `public/797dc8ab408ea8e7/support_records.npy` | `bdcc68fa5703ca207f820ab63468f783d317df36040eb2e71e665568b1ade47c` |
| `public/a47c4e4016f899c8/query_detector.npy` | `b8242383360c9f7472354b362fc8fe9e4769178090b575a6eb69772008d447e8` |
| `public/a47c4e4016f899c8/query_index.npy` | `70a63faea9658297903b33afec2da5cced18e46594ca78d6fb316c90e92015fb` |
| `public/a47c4e4016f899c8/query_n_records.npy` | `4ed1ba16a8bb819dea02323dfc74b947668421b1044dfdcf0976438563363437` |
| `public/a47c4e4016f899c8/query_padding_mask.npy` | `2185646e08ff2dba4a4e5faef8abad57637f8cb0eab12ef2995f2925b9a6e4b3` |
| `public/a47c4e4016f899c8/query_records.npy` | `cc5b239694c093ea555b06d342d8d76b86d31de44cac57ba31a2555a8b6777e3` |
| `public/a47c4e4016f899c8/support_budget_rung.npy` | `a96fabe0c73e48461698cfb7882c0611d92f6254b324f0a4e3ab0b8d62bc80a1` |
| `public/a47c4e4016f899c8/support_episode_role.npy` | `cf7b74acf92ced85a85a4af24417939f59381a19baad093badb0ea7dfdbd050e` |
| `public/a47c4e4016f899c8/support_observed_present.npy` | `fbef5cf04cfa1809415ca0449de352b361982d21e7c6135e15a8c0a525b094dc` |
| `public/a47c4e4016f899c8/support_observed_target.npy` | `e699dca5eda91f3a4e3e3f37f0c9c0cf2d9b5b93d906132e1abb82eb2cab32db` |
| `public/a47c4e4016f899c8/support_padding_mask.npy` | `a7b5b5eac1880bebf262150dba146b6c768791ba613b393bcdb3af0b743946d7` |
| `public/a47c4e4016f899c8/support_records.npy` | `0794e64028f064a4c5f25970f8913d84159a8a3bd55c5ba92c9846a91a5eb467` |
