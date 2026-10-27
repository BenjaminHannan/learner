# Exp 152 per-turn table (both targets; verdicts post one documented correction)

## T-Q S1-family10
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hi | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Ana's mother is Lisa. | teach | Lisa | OK | 1 | Saved: Ana's mother is Lisa. |
| 2 | Ana's father is Mark. | teach | Mark | OK | 1 | Saved: Ana's father is Mark. |
| 3 | Who is Ana's mother? | ask | Lisa | OK | 0 | Ana's mother is Lisa. |
| 4 | Lisa's city is Denver. | teach | Denver | OK | 1 | Saved: Lisa's city is Denver. |
| 5 | where does she live? | ask | Denver | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 6 | Who is Ana's mother's city? | ask | Denver | OK | 0 | Ana's mother's city is Denver. |
| 7 | Mark's city is Denver. | teach | Denver | OK | 1 | Saved: Mark's city is Denver. |
| 8 | what about his mom? | ask | Lisa | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 9 | Ana's sister is Zoe. | teach | Zoe | OK | 1 | Saved: Ana's sister is Zoe. |
| 10 | Who is Ana's sister? | ask | Zoe | OK | 0 | Ana's sister is Zoe. |
| 11 | Zoe's city is Austin. | teach | Austin | OK | 1 | Saved: Zoe's city is Austin. |
| 12 | Where is Ana's sister's city? | ask | Austin | OK | 0 | Ana's sister's city is Austin. |
| 13 | Ana's brother is Leo. | teach | Leo | OK | 1 | Saved: Ana's brother is Leo. |
| 14 | Who is Ana's brother? | ask | Leo | OK | 0 | Ana's brother is Leo. |
| 15 | Leo's teacher is Patel. | teach | Patel | OK | 1 | Saved: Leo's teacher is Patel. |
| 16 | Who is Leo's teacher? | ask | Patel | OK | 0 | Leo's teacher is Patel. |
| 17 | Who is Ana's brother's teacher? | ask | Patel | OK | 0 | Ana's brother's teacher is Patel. |
| 18 | Kip's wife is Jo. | teach | Jo | OK | 1 | Saved: Kip's wife is Jo. |
| 19 | Who is Kip married to? | known [K147] | Jo | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 20 | Jo's city is Austin. | teach | Austin | OK | 1 | Saved: Jo's city is Austin. |
| 21 | Who is Kip's wife's city? | ask | Austin | OK | 0 | Kip's wife's city is Austin. |
| 22 | Who is Ana's mother? | reask | Lisa | OK | 0 | Ana's mother is Lisa. |
| 23 | Who is Ana's mother's city? | reask | Denver | OK | 0 | Ana's mother's city is Denver. |
| 24 | thanks! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 25 | Who is Zoe's city? | ask | Austin | OK | 0 | Zoe's city is Austin. |
| 26 | Who is Mark's city? | ask | Denver | OK | 0 | Mark's city is Denver. |
| 27 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 28 | Who is Ana's father's city? | ask | Denver | OK | 0 | Ana's father's city is Denver. |
| 29 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |

## T-Q S2-casual-friends
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | heyyy | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | what can you do | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 2 | Marta's friend is June. | teach | June | OK | 1 | Saved: Marta's friend is June. |
| 3 | june's city is reno | teach | reno | OK | 1 | Saved: June's city is reno. |
| 4 | btw marta's brother is kai | teach | kai | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 5 | Who is Marta's friend? | ask | June | OK | 0 | Marta's friend is June. |
| 6 | oh and june's teacher is patel | teach | patel | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 7 | who is june's teacher? | ask | patel | UNHELPFUL | 0 | I don't know June's teacher. |
| 8 | I think Kip Dune's city is Reno. | known [K150] | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 9 | Who is Marta's friend's city? | ask | reno | OK | 0 | Marta's friend's city is reno. |
| 10 | who are you | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 11 | Marta's sister is Wren. | teach | Wren | OK | 1 | Saved: Marta's sister is Wren. |
| 12 | also wren's city is miami | teach | miami | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 13 | what is wren's city? | ask | miami | UNHELPFUL | 0 | I don't know Wren's city. |
| 14 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 15 | Who is Wren's city? | reask | miami | UNHELPFUL | 0 | I don't know Wren's city. |
| 16 | Marta's father is Dez. | teach | Dez | OK | 1 | Saved: Marta's father is Dez. |
| 17 | dez's city is dallas | teach | dallas | OK | 1 | Saved: Dez's city is dallas. |
| 18 | where is marta's father's city? | ask | dallas | OK | 0 | marta's father's city is dallas. |
| 19 | Who is June's city? | reask | reno | OK | 0 | June's city is reno. |
| 20 | ty, very helpful! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 21 | Marta's mother is Liv. | teach | Liv | OK | 1 | Saved: Marta's mother is Liv. |
| 22 | liv's city is boston | teach | boston | OK | 1 | Saved: Liv's city is boston. |
| 23 | who is marta's mother's city? | ask | boston | OK | 0 | marta's mother's city is boston. |
| 24 | Who is Zane's city? | abstain | None | OK | 0 | I don't know anyone called Zane. |
| 25 | k bye | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 26 | Who is Marta's mother's city? | reask | boston | OK | 0 | Marta's mother's city is boston. |
| 27 | Who is Liv's city? | ask | boston | OK | 0 | Liv's city is boston. |
| 28 | Who is Marta's brother? | reask | kai | UNHELPFUL | 0 | I don't know Marta's brother. |
| 29 | Who is Marta's sister's city? | ask | miami | UNHELPFUL | 0 | I don't know Wren's city. |

## T-Q S3-teachers-correction
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | heyy, what can you do? | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Nadia's teacher is Rao. | teach | Rao | OK | 1 | Saved: Nadia's teacher is Rao. |
| 2 | Who is Nadia's teacher? | ask | Rao | OK | 0 | Nadia's teacher is Rao. |
| 3 | rao's city is seattle | teach | seattle | OK | 1 | Saved: Rao's city is seattle. |
| 4 | where does she live? | ask | seattle | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 5 | Where is Nadia's teacher's city? | ask | seattle | OK | 0 | Nadia's teacher's city is seattle. |
| 6 | no wait, it's denver | correct | denver | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 7 | Actually, Rao's city is Denver. | correct | Denver | OK | 1 | Saved: Rao's city is Denver. |
| 8 | Where is Nadia's teacher's city? | reask | Denver | OK | 0 | Nadia's teacher's city is Denver. |
| 9 | Nadia's brother is Finn. | teach | Finn | OK | 1 | Saved: Nadia's brother is Finn. |
| 10 | what about his mom? | ask | Orla | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 11 | Finn's mother is Orla. | teach | Orla | OK | 1 | Saved: Finn's mother is Orla. |
| 12 | Who is Finn's mother? | ask | Orla | OK | 0 | Finn's mother is Orla. |
| 13 | Who is Nadia's brother's mother? | ask | Orla | OK | 0 | Nadia's brother's mother is Orla. |
| 14 | Who was Nadia's teacher in 2023? | known [K148] | Rao | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 15 | Nadia's school is Lyceum. | teach | Lyceum | OK | 1 | Saved: Nadia's school is Lyceum. |
| 16 | Aldo's title is Dean of the School of Music. | teach | Dean | OK | 1 | Saved: Aldo's title is Dean of the School of Music. |
| 17 | who is the dean of the school of music? | known [K144] | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 18 | What is Aldo's title? | ask | Dean | OK | 0 | Aldo's title is Dean of the School of Music. |
| 19 | where does she live? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 20 | thanks! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 21 | Who is Nadia's teacher? | reask | Rao | OK | 0 | Nadia's teacher is Rao. |
| 22 | Where is Nadia's teacher's city? | reask | Denver | OK | 0 | Nadia's teacher's city is Denver. |
| 23 | Who is Petra's teacher? | abstain | None | OK | 0 | I don't know anyone called Petra. |
| 24 | Who is Nadi's teacher? | abstain | None | OK | 0 | I don't know anyone called Nadi. |
| 25 | Who is Finn's mother? | reask | Orla | OK | 0 | Finn's mother is Orla. |
| 26 | What is Nadia's school? | ask | Lyceum | OK | 0 | Nadia's school is Lyceum. |
| 27 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 28 | Who is Nadia's brother's mother? | reask | Orla | OK | 0 | Nadia's brother's mother is Orla. |
| 29 | Who is Orla's city? | abstain | None | OK | 0 | I don't know Orla's city. |

## T-Q S4-pets-identity
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hi!! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | my dog is biscuit | teach | biscuit | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 2 | Biscuit's color is brown. | teach | brown | OK | 1 | Saved: Biscuit's color is brown. |
| 3 | Biscuit's owner is Ana. | teach | Ana | OK | 1 | Saved: Biscuit's owner is Ana. |
| 4 | What is Biscuit's color? | ask | brown | OK | 0 | Biscuit's color is brown. |
| 5 | Who is Biscuit's owner? | ask | Ana | OK | 0 | Biscuit's owner is Ana. |
| 6 | Ana's pet is Biscuit. | teach | Biscuit | OK | 1 | Saved: Ana's pet is Biscuit. |
| 7 | Who is Ana's pet's color? | ask | brown | WRONG | 0 | Ana's pet is Biscuit, which is not someone I can look up. |
| 8 | who are you | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 9 | what can you do? | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 10 | Milo's color is gray. | teach | gray | OK | 1 | Saved: Milo's color is gray. |
| 11 | Milo's owner is Ana. | teach | Ana | OK | 1 | Saved: Milo's owner is Ana. |
| 12 | What is Milo's color? | ask | gray | OK | 0 | Milo's color is gray. |
| 13 | What is Milo's city? | abstain | None | OK | 0 | I don't know Milo's city. |
| 14 | What is Zane's color? | abstain | None | OK | 0 | I don't know anyone called Zane. |
| 15 | thanks so much! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 16 | Milo's toy is ball | teach | ball | OK | 1 | Saved: Milo's toy is ball. |
| 17 | What is Milo's toy? | ask | ball | OK | 0 | Milo's toy is ball. |
| 18 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 19 | What is Biscuit's color? | reask | brown | OK | 0 | Biscuit's color is brown. |
| 20 | Who is Ana's pet's owner? | ask | Ana | OK | 0 | Ana's pet is Biscuit, which is not someone I can look up. |
| 21 | What is Biscut's color? | abstain | None | OK | 0 | I don't know anyone called Biscut. |
| 22 | Who is Milo's owner? | ask | Ana | OK | 0 | Milo's owner is Ana. |
| 23 | Who is Ana's pet? | reask | Biscuit | OK | 0 | Ana's pet is Biscuit. |
| 24 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 25 | What is Milo's color? | reask | gray | OK | 0 | Milo's color is gray. |
| 26 | Who is Biscuit's owner's pet? | ask | Biscuit | OK | 0 | Biscuit's owner is Ana, which is not someone I can look up. |
| 27 | Who is Ana's pet's color? | reask | brown | WRONG | 0 | Ana's pet is Biscuit, which is not someone I can look up. |
| 28 | bye!! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 29 | What is Milo's toy? | reask | ball | OK | 0 | Milo's toy is ball. |

## T-Q S5-robustness
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hey | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Rosa's friend is Tess. | teach | Tess | OK | 1 | Saved: Rosa's friend is Tess. |
| 2 | Tess's city is Omaha | teach | Omaha | OK | 1 | Saved: Tess's city is Omaha. |
| 3 | What is Tess's city | known [K151] | Omaha | OK | 0 | Tess's city is Omaha. |
| 4 | who is rosa's friend | ask | Tess | OK | 0 | rosa's friend is Tess. |
| 5 | what's tess's city? | ask | Omaha | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 6 | tell me tess's city | ask | Omaha | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 7 | Rosa's mother is Vera. | teach | Vera | OK | 1 | Saved: Rosa's mother is Vera. |
| 8 | vera's city is lima | teach | lima | OK | 1 | Saved: Vera's city is lima. |
| 9 | Who is Rosa's mother's city??? | ask | lima | UNHELPFUL | 0 | I don't know Vera's city??. |
| 10 |   who is vera's city   | ask | lima | OK | 0 | vera's city is lima. |
| 11 | Rosa's brother is Ned. | teach | Ned | OK | 1 | Saved: Rosa's brother is Ned. |
| 12 | ned's teacher is quinn | teach | quinn | OK | 1 | Saved: Ned's teacher is quinn. |
| 13 | who is ned's teacher | ask | quinn | OK | 0 | ned's teacher is quinn. |
| 14 | Who is Rosa's brother's teacher? | ask | quinn | OK | 0 | Rosa's brother's teacher is quinn. |
| 15 | ok | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 16 | Tess's city is Omaha. | teach | Omaha | OK | 0 | I already have that. |
| 17 | What is Tess's city? | reask | Omaha | OK | 0 | Tess's city is Omaha. |
| 18 | Rosa's sister is Pia 🙂 | teach | Pia | OK | 1 | Saved: Rosa's sister is Pia 🙂. |
| 19 | Who is Rosa's sister? | ask | Pia | OK | 0 | Rosa's sister is Pia 🙂. |
| 20 | cool thanks | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 21 | Who is Rosa's friend? | reask | Tess | OK | 0 | Rosa's friend is Tess. |
| 22 | Where is Rosa's friend's city? | ask | Omaha | OK | 0 | Rosa's friend's city is Omaha. |
| 23 | Who is Rosa's mother's city? | reask | lima | OK | 0 | Rosa's mother's city is lima. |
| 24 | Who is Tess's city? | reask | Omaha | OK | 0 | Tess's city is Omaha. |
| 25 | Who is Ned's teacher? | reask | quinn | OK | 0 | Ned's teacher is quinn. |
| 26 | Who is Rosa's brother? | ask | Ned | OK | 0 | Rosa's brother is Ned. |
| 27 | Who is Pia's city? | abstain | None | OK | 0 | I don't know anyone called Pia. |
| 28 | Who is Rosa's sister's city? | abstain | None | OK | 0 | I don't know Pia 🙂's city. |
| 29 | bye | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |

## T-Q S6-pronouns-corrections
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hii | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Eve's mother is Fay. | teach | Fay | OK | 1 | Saved: Eve's mother is Fay. |
| 2 | Fay's city is Reno. | teach | Reno | OK | 1 | Saved: Fay's city is Reno. |
| 3 | where does she live? | ask | Reno | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 4 | Who is Eve's mother's city? | ask | Reno | OK | 0 | Eve's mother's city is Reno. |
| 5 | Eve's father is Gus. | teach | Gus | OK | 1 | Saved: Eve's father is Gus. |
| 6 | what about his mom? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 7 | Gus's mother is Hattie. | teach | Hattie | OK | 1 | Saved: Gus's mother is Hattie. |
| 8 | Who is Gus's mother? | ask | Hattie | OK | 0 | Gus's mother is Hattie. |
| 9 | and his dad? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 10 | Gus's father is Ivan. | teach | Ivan | OK | 1 | Saved: Gus's father is Ivan. |
| 11 | Who is Gus's father? | ask | Ivan | OK | 0 | Gus's father is Ivan. |
| 12 | Who is Eve's father's mother? | ask | Hattie | OK | 0 | Eve's father's mother is Hattie. |
| 13 | Vera's city is Lima. | teach | Lima | OK | 1 | Saved: Vera's city is Lima. |
| 14 | no Vera's city is Quito | known [K146] | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 15 | What is Vera's city? | known [K146] | Lima | OK | 0 | Vera's city is Lima. |
| 16 | Actually, Vera's city is Quito. | correct | Quito | OK | 1 | Saved: Vera's city is Quito. |
| 17 | What is Vera's city? | reask | Quito | OK | 0 | Vera's city is Quito. |
| 18 | Eve's sister is June. | teach | June | OK | 1 | Saved: Eve's sister is June. |
| 19 | June's city is Miami. | teach | Miami | OK | 1 | Saved: June's city is Miami. |
| 20 | where does she live? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 21 | Who is June's city? | ask | Miami | OK | 0 | June's city is Miami. |
| 22 | thanks! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 23 | Who is Eve's mother? | reask | Fay | OK | 0 | Eve's mother is Fay. |
| 24 | Who is Eve's mother's city? | reask | Reno | OK | 0 | Eve's mother's city is Reno. |
| 25 | Who is Eve's father's father? | ask | Ivan | OK | 0 | Eve's father's father is Ivan. |
| 26 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 27 | Who is Gus's mother's city? | abstain | None | OK | 0 | I don't know Hattie's city. |
| 28 | What is Vera's city? | reask | Quito | OK | 0 | Vera's city is Quito. |
| 29 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |

## T-T S1-family10
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hi | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Ana's mother is Lisa. | teach | Lisa | OK | 1 | Saved: Ana's mother is Lisa. |
| 2 | Ana's father is Mark. | teach | Mark | OK | 1 | Saved: Ana's father is Mark. |
| 3 | Who is Ana's mother? | ask | Lisa | OK | 0 | Ana's mother is Lisa. |
| 4 | Lisa's city is Denver. | teach | Denver | OK | 1 | Saved: Lisa's city is Denver. |
| 5 | where does she live? | ask | Denver | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 6 | Who is Ana's mother's city? | ask | Denver | OK | 0 | Ana's mother's city is Denver. |
| 7 | Mark's city is Denver. | teach | Denver | OK | 1 | Saved: Mark's city is Denver. |
| 8 | what about his mom? | ask | Lisa | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 9 | Ana's sister is Zoe. | teach | Zoe | OK | 1 | Saved: Ana's sister is Zoe. |
| 10 | Who is Ana's sister? | ask | Zoe | OK | 0 | Ana's sister is Zoe. |
| 11 | Zoe's city is Austin. | teach | Austin | OK | 1 | Saved: Zoe's city is Austin. |
| 12 | Where is Ana's sister's city? | ask | Austin | OK | 0 | Ana's sister's city is Austin. |
| 13 | Ana's brother is Leo. | teach | Leo | OK | 1 | Saved: Ana's brother is Leo. |
| 14 | Who is Ana's brother? | ask | Leo | OK | 0 | Ana's brother is Leo. |
| 15 | Leo's teacher is Patel. | teach | Patel | OK | 1 | Saved: Leo's teacher is Patel. |
| 16 | Who is Leo's teacher? | ask | Patel | OK | 0 | Leo's teacher is Patel. |
| 17 | Who is Ana's brother's teacher? | ask | Patel | OK | 0 | Ana's brother's teacher is Patel. |
| 18 | Kip's wife is Jo. | teach | Jo | OK | 1 | Saved: Kip's wife is Jo. |
| 19 | Who is Kip married to? | known [K147] | Jo | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 20 | Jo's city is Austin. | teach | Austin | OK | 1 | Saved: Jo's city is Austin. |
| 21 | Who is Kip's wife's city? | ask | Austin | OK | 0 | Kip's wife's city is Austin. |
| 22 | Who is Ana's mother? | reask | Lisa | OK | 0 | Ana's mother is Lisa. |
| 23 | Who is Ana's mother's city? | reask | Denver | OK | 0 | Ana's mother's city is Denver. |
| 24 | thanks! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 25 | Who is Zoe's city? | ask | Austin | OK | 0 | Zoe's city is Austin. |
| 26 | Who is Mark's city? | ask | Denver | OK | 0 | Mark's city is Denver. |
| 27 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 28 | Who is Ana's father's city? | ask | Denver | OK | 0 | Ana's father's city is Denver. |
| 29 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |

## T-T S2-casual-friends
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | heyyy | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | what can you do | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 2 | Marta's friend is June. | teach | June | OK | 1 | Saved: Marta's friend is June. |
| 3 | june's city is reno | teach | reno | OK | 1 | Saved: June's city is reno. |
| 4 | btw marta's brother is kai | teach | kai | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 5 | Who is Marta's friend? | ask | June | OK | 0 | Marta's friend is June. |
| 6 | oh and june's teacher is patel | teach | patel | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 7 | who is june's teacher? | ask | patel | UNHELPFUL | 0 | I don't know June's teacher. |
| 8 | I think Kip Dune's city is Reno. | known [K150] | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 9 | Who is Marta's friend's city? | ask | reno | OK | 0 | Marta's friend's city is reno. |
| 10 | who are you | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 11 | Marta's sister is Wren. | teach | Wren | OK | 1 | Saved: Marta's sister is Wren. |
| 12 | also wren's city is miami | teach | miami | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 13 | what is wren's city? | ask | miami | UNHELPFUL | 0 | I don't know Wren's city. |
| 14 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 15 | Who is Wren's city? | reask | miami | UNHELPFUL | 0 | I don't know Wren's city. |
| 16 | Marta's father is Dez. | teach | Dez | OK | 1 | Saved: Marta's father is Dez. |
| 17 | dez's city is dallas | teach | dallas | OK | 1 | Saved: Dez's city is dallas. |
| 18 | where is marta's father's city? | ask | dallas | OK | 0 | marta's father's city is dallas. |
| 19 | Who is June's city? | reask | reno | OK | 0 | June's city is reno. |
| 20 | ty, very helpful! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 21 | Marta's mother is Liv. | teach | Liv | OK | 1 | Saved: Marta's mother is Liv. |
| 22 | liv's city is boston | teach | boston | OK | 1 | Saved: Liv's city is boston. |
| 23 | who is marta's mother's city? | ask | boston | OK | 0 | marta's mother's city is boston. |
| 24 | Who is Zane's city? | abstain | None | OK | 0 | I don't know anyone called Zane. |
| 25 | k bye | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 26 | Who is Marta's mother's city? | reask | boston | OK | 0 | Marta's mother's city is boston. |
| 27 | Who is Liv's city? | ask | boston | OK | 0 | Liv's city is boston. |
| 28 | Who is Marta's brother? | reask | kai | UNHELPFUL | 0 | I don't know Marta's brother. |
| 29 | Who is Marta's sister's city? | ask | miami | UNHELPFUL | 0 | I don't know Wren's city. |

## T-T S3-teachers-correction
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | heyy, what can you do? | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Nadia's teacher is Rao. | teach | Rao | OK | 1 | Saved: Nadia's teacher is Rao. |
| 2 | Who is Nadia's teacher? | ask | Rao | OK | 0 | Nadia's teacher is Rao. |
| 3 | rao's city is seattle | teach | seattle | OK | 1 | Saved: Rao's city is seattle. |
| 4 | where does she live? | ask | seattle | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 5 | Where is Nadia's teacher's city? | ask | seattle | OK | 0 | Nadia's teacher's city is seattle. |
| 6 | no wait, it's denver | correct | denver | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 7 | Actually, Rao's city is Denver. | correct | Denver | OK | 1 | Saved: Rao's city is Denver. |
| 8 | Where is Nadia's teacher's city? | reask | Denver | OK | 0 | Nadia's teacher's city is Denver. |
| 9 | Nadia's brother is Finn. | teach | Finn | OK | 1 | Saved: Nadia's brother is Finn. |
| 10 | what about his mom? | ask | Orla | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 11 | Finn's mother is Orla. | teach | Orla | OK | 1 | Saved: Finn's mother is Orla. |
| 12 | Who is Finn's mother? | ask | Orla | OK | 0 | Finn's mother is Orla. |
| 13 | Who is Nadia's brother's mother? | ask | Orla | OK | 0 | Nadia's brother's mother is Orla. |
| 14 | Who was Nadia's teacher in 2023? | known [K148] | Rao | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 15 | Nadia's school is Lyceum. | teach | Lyceum | OK | 1 | Saved: Nadia's school is Lyceum. |
| 16 | Aldo's title is Dean of the School of Music. | teach | Dean | OK | 1 | Saved: Aldo's title is Dean of the School of Music. |
| 17 | who is the dean of the school of music? | known [K144] | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 18 | What is Aldo's title? | ask | Dean | OK | 0 | Aldo's title is Dean of the School of Music. |
| 19 | where does she live? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 20 | thanks! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 21 | Who is Nadia's teacher? | reask | Rao | OK | 0 | Nadia's teacher is Rao. |
| 22 | Where is Nadia's teacher's city? | reask | Denver | OK | 0 | Nadia's teacher's city is Denver. |
| 23 | Who is Petra's teacher? | abstain | None | OK | 0 | I don't know anyone called Petra. |
| 24 | Who is Nadi's teacher? | abstain | None | OK | 0 | I don't know anyone called Nadi. |
| 25 | Who is Finn's mother? | reask | Orla | OK | 0 | Finn's mother is Orla. |
| 26 | What is Nadia's school? | ask | Lyceum | OK | 0 | Nadia's school is Lyceum. |
| 27 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 28 | Who is Nadia's brother's mother? | reask | Orla | OK | 0 | Nadia's brother's mother is Orla. |
| 29 | Who is Orla's city? | abstain | None | OK | 0 | I don't know Orla's city. |

## T-T S4-pets-identity
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hi!! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | my dog is biscuit | teach | biscuit | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 2 | Biscuit's color is brown. | teach | brown | OK | 1 | Saved: Biscuit's color is brown. |
| 3 | Biscuit's owner is Ana. | teach | Ana | OK | 1 | Saved: Biscuit's owner is Ana. |
| 4 | What is Biscuit's color? | ask | brown | OK | 0 | Biscuit's color is brown. |
| 5 | Who is Biscuit's owner? | ask | Ana | OK | 0 | Biscuit's owner is Ana. |
| 6 | Ana's pet is Biscuit. | teach | Biscuit | OK | 1 | Saved: Ana's pet is Biscuit. |
| 7 | Who is Ana's pet's color? | ask | brown | WRONG | 0 | Ana's pet is Biscuit, which is not someone I can look up. |
| 8 | who are you | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 9 | what can you do? | self | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 10 | Milo's color is gray. | teach | gray | OK | 1 | Saved: Milo's color is gray. |
| 11 | Milo's owner is Ana. | teach | Ana | OK | 1 | Saved: Milo's owner is Ana. |
| 12 | What is Milo's color? | ask | gray | OK | 0 | Milo's color is gray. |
| 13 | What is Milo's city? | abstain | None | OK | 0 | I don't know Milo's city. |
| 14 | What is Zane's color? | abstain | None | OK | 0 | I don't know anyone called Zane. |
| 15 | thanks so much! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 16 | Milo's toy is ball | teach | ball | OK | 1 | Saved: Milo's toy is ball. |
| 17 | What is Milo's toy? | ask | ball | OK | 0 | Milo's toy is ball. |
| 18 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 19 | What is Biscuit's color? | reask | brown | OK | 0 | Biscuit's color is brown. |
| 20 | Who is Ana's pet's owner? | ask | Ana | OK | 0 | Ana's pet is Biscuit, which is not someone I can look up. |
| 21 | What is Biscut's color? | abstain | None | OK | 0 | I don't know anyone called Biscut. |
| 22 | Who is Milo's owner? | ask | Ana | OK | 0 | Milo's owner is Ana. |
| 23 | Who is Ana's pet? | reask | Biscuit | OK | 0 | Ana's pet is Biscuit. |
| 24 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 25 | What is Milo's color? | reask | gray | OK | 0 | Milo's color is gray. |
| 26 | Who is Biscuit's owner's pet? | ask | Biscuit | OK | 0 | Biscuit's owner is Ana, which is not someone I can look up. |
| 27 | Who is Ana's pet's color? | reask | brown | WRONG | 0 | Ana's pet is Biscuit, which is not someone I can look up. |
| 28 | bye!! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 29 | What is Milo's toy? | reask | ball | OK | 0 | Milo's toy is ball. |

## T-T S5-robustness
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hey | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Rosa's friend is Tess. | teach | Tess | OK | 1 | Saved: Rosa's friend is Tess. |
| 2 | Tess's city is Omaha | teach | Omaha | OK | 1 | Saved: Tess's city is Omaha. |
| 3 | What is Tess's city | known [K151] | Omaha | OK | 0 | Tess's city is Omaha. |
| 4 | who is rosa's friend | ask | Tess | OK | 0 | rosa's friend is Tess. |
| 5 | what's tess's city? | ask | Omaha | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 6 | tell me tess's city | ask | Omaha | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 7 | Rosa's mother is Vera. | teach | Vera | OK | 1 | Saved: Rosa's mother is Vera. |
| 8 | vera's city is lima | teach | lima | OK | 1 | Saved: Vera's city is lima. |
| 9 | Who is Rosa's mother's city??? | ask | lima | UNHELPFUL | 0 | I don't know Vera's city??. |
| 10 |   who is vera's city   | ask | lima | OK | 0 | vera's city is lima. |
| 11 | Rosa's brother is Ned. | teach | Ned | OK | 1 | Saved: Rosa's brother is Ned. |
| 12 | ned's teacher is quinn | teach | quinn | OK | 1 | Saved: Ned's teacher is quinn. |
| 13 | who is ned's teacher | ask | quinn | OK | 0 | ned's teacher is quinn. |
| 14 | Who is Rosa's brother's teacher? | ask | quinn | OK | 0 | Rosa's brother's teacher is quinn. |
| 15 | ok | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 16 | Tess's city is Omaha. | teach | Omaha | OK | 0 | I already have that. |
| 17 | What is Tess's city? | reask | Omaha | OK | 0 | Tess's city is Omaha. |
| 18 | Rosa's sister is Pia 🙂 | teach | Pia | OK | 1 | Saved: Rosa's sister is Pia 🙂. |
| 19 | Who is Rosa's sister? | ask | Pia | OK | 0 | Rosa's sister is Pia 🙂. |
| 20 | cool thanks | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 21 | Who is Rosa's friend? | reask | Tess | OK | 0 | Rosa's friend is Tess. |
| 22 | Where is Rosa's friend's city? | ask | Omaha | OK | 0 | Rosa's friend's city is Omaha. |
| 23 | Who is Rosa's mother's city? | reask | lima | OK | 0 | Rosa's mother's city is lima. |
| 24 | Who is Tess's city? | reask | Omaha | OK | 0 | Tess's city is Omaha. |
| 25 | Who is Ned's teacher? | reask | quinn | OK | 0 | Ned's teacher is quinn. |
| 26 | Who is Rosa's brother? | ask | Ned | OK | 0 | Rosa's brother is Ned. |
| 27 | Who is Pia's city? | abstain | None | OK | 0 | I don't know anyone called Pia. |
| 28 | Who is Rosa's sister's city? | abstain | None | OK | 0 | I don't know Pia 🙂's city. |
| 29 | bye | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |

## T-T S6-pronouns-corrections
| n | text | expect | want | verdict | w | reply |
|---|---|---|---|---|---|---|
| 0 | hii | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 1 | Eve's mother is Fay. | teach | Fay | OK | 1 | Saved: Eve's mother is Fay. |
| 2 | Fay's city is Reno. | teach | Reno | OK | 1 | Saved: Fay's city is Reno. |
| 3 | where does she live? | ask | Reno | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 4 | Who is Eve's mother's city? | ask | Reno | OK | 0 | Eve's mother's city is Reno. |
| 5 | Eve's father is Gus. | teach | Gus | OK | 1 | Saved: Eve's father is Gus. |
| 6 | what about his mom? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 7 | Gus's mother is Hattie. | teach | Hattie | OK | 1 | Saved: Gus's mother is Hattie. |
| 8 | Who is Gus's mother? | ask | Hattie | OK | 0 | Gus's mother is Hattie. |
| 9 | and his dad? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 10 | Gus's father is Ivan. | teach | Ivan | OK | 1 | Saved: Gus's father is Ivan. |
| 11 | Who is Gus's father? | ask | Ivan | OK | 0 | Gus's father is Ivan. |
| 12 | Who is Eve's father's mother? | ask | Hattie | OK | 0 | Eve's father's mother is Hattie. |
| 13 | Vera's city is Lima. | teach | Lima | OK | 1 | Saved: Vera's city is Lima. |
| 14 | no Vera's city is Quito | known [K146] | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 15 | What is Vera's city? | known [K146] | Lima | OK | 0 | Vera's city is Lima. |
| 16 | Actually, Vera's city is Quito. | correct | Quito | OK | 1 | Saved: Vera's city is Quito. |
| 17 | What is Vera's city? | reask | Quito | OK | 0 | Vera's city is Quito. |
| 18 | Eve's sister is June. | teach | June | OK | 1 | Saved: Eve's sister is June. |
| 19 | June's city is Miami. | teach | Miami | OK | 1 | Saved: June's city is Miami. |
| 20 | where does she live? | clarify | None | OK | 0 | I didn't understand that. Could you say it another way? |
| 21 | Who is June's city? | ask | Miami | OK | 0 | June's city is Miami. |
| 22 | thanks! | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 23 | Who is Eve's mother? | reask | Fay | OK | 0 | Eve's mother is Fay. |
| 24 | Who is Eve's mother's city? | reask | Reno | OK | 0 | Eve's mother's city is Reno. |
| 25 | Who is Eve's father's father? | ask | Ivan | OK | 0 | Eve's father's father is Ivan. |
| 26 | lol | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
| 27 | Who is Gus's mother's city? | abstain | None | OK | 0 | I don't know Hattie's city. |
| 28 | What is Vera's city? | reask | Quito | OK | 0 | Vera's city is Quito. |
| 29 | ok cool | smalltalk | None | UNHELPFUL | 0 | I didn't understand that. Could you say it another way? |
