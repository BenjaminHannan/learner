# 138m verifier probes: case table

One row per probe turn (restarts omitted). l = 138l, m = 138m. Label is for changed replies only.

| id | feature | turn | 138l reply | 138m reply | change | reason | faults l | faults m |
|---|---|---|---|---|---|---|---|---|
| A01 | identity | what's ur name | You never told me your name, so I do not know it. | You never told me your name, so I do not know it. | - | unchanged | - | - |
| A02 | identity | who made u | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | identity miss in both ('who made u'); m text is only cleaner | comma splice | - |
| A03 | identity | are you a person? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing. | better | identity sheet instead of glued decline | comma splice | - |
| A04 | identity | are you a robot | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing. | better | identity sheet | comma splice | - |
| A05 | identity | Are you an AI? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing. | better | identity sheet | comma splice | - |
| A06 | identity | whats yuor name? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | typo 'yuor' misses identity in both | comma splice | - |
| A07 | identity | who built you | Nobody taught me who made me, so I do not know it. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. | Ben built me. | better | Ben built me. | - | - |
| A08 | identity | Who created you? | Nobody taught me who made me, so I do not know it. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. | Ben built me. | better | Ben built me. | - | - |
| A09 | identity | what should i call you | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | My name is Premonition. | better | My name is Premonition. | comma splice | - |
| A10 | identity | Do you have a name? | You never gave me a name, so I do not have one. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. | My name is Premonition. | better | My name is Premonition. | - | - |
| A11 | identity | who is your creator? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | Ben built me. | better | Ben built me. | comma splice | - |
| A12 | identity | what are you exactly? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing. | better | identity sheet | comma splice | - |
| A13 | identity | tell me ur name pls | You never told me your name, so I do not know it. | You never told me your name, so I do not know it. | - | unchanged | - | - |
| A14 | identity | Who programmed you? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | Ben built me. | better | Ben built me. | comma splice | - |
| A15 | identity | are u human | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | 'are u human' misses identity in both | comma splice | - |
| A16 | identity | My name is Corvin. | Saved: your name is Corvin. | Saved: your name is Corvin. | - | unchanged | - | - |
| A16 | identity | and what's your name? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | My name is Premonition. | better | My name is Premonition. (not the user's name) | comma splice | - |
| N01 | identity-nearmiss | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| N01 | identity-nearmiss | What's Tomas's name? | I don't know Tomas's name. | I don't know Tomas's name. | - | unchanged | - | - |
| N02 | identity-nearmiss | Tomas lives in Varne. | Saved: Tomas's city is Varne. | Saved: Tomas's city is Varne. | - | unchanged | - | - |
| N02 | identity-nearmiss | Who built Tomas's house? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | worse | correct answer is 'I don't know'; m now says only 'didn't understand' | comma splice | - |
| N03 | identity-nearmiss | Who made the cake? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | worse | correct answer is 'I don't know'; m says only 'didn't understand' | comma splice | - |
| N04 | identity-nearmiss | What is your favourite colour? | I do not have favourites. | I do not have favourites. | - | unchanged | - | - |
| N05 | identity-nearmiss | Who built the bridge in Harlow? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | worse | correct answer is 'I don't know'; m says only 'didn't understand' | comma splice | - |
| N06 | identity-nearmiss | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| N06 | identity-nearmiss | What is the name of Tomas's boss? | I don't know anyone called the name of Tomas. | I don't know anyone called the name of Tomas. | - | unchanged | misparse 'the name of' | misparse 'the name of' |
| N07 | identity-nearmiss | Who made Yarrow's dress? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | worse | correct answer is 'I don't know'; m says only 'didn't understand' | comma splice | - |
| N08 | identity-nearmiss | Are you busy? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | 'Are you busy?' out of scope; both abstain, m cleaner | comma splice | - |
| N09 | identity-nearmiss | What's your city? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | worse | 'What's your city?' should be 'I don't know'; m says only 'didn't understand' | comma splice | - |
| N10 | identity-nearmiss | What is Quenby's name? | I don't know anyone called Quenby. | I don't know anyone called Quenby. | - | unchanged | - | - |
| B01 | username | My name is Pippa. | Saved: your name is Pippa. | Saved: your name is Pippa. | - | unchanged | - | - |
| B01 | username | What's my name? | Your name is Pippa. | Your name is Pippa. | - | unchanged | - | - |
| B02 | username | Call me Ruthven. | Saved: your name is Ruthven. | Saved: your name is Ruthven. | - | unchanged | - | - |
| B02 | username | what is my name | Your name is Ruthven. | Your name is Ruthven. | - | unchanged | - | - |
| B03 | username | I'm Sabella. | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | - | unchanged | - | - |
| B03 | username | do you know my name? | I don't know your name yet. | I don't know your name yet. | - | unchanged | - | - |
| B04 | username | My name is Oswin. | Saved: your name is Oswin. | Saved: your name is Oswin. | - | unchanged | - | - |
| B04 | username | Tell me what my name is. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | name stored but both miss (212/216 gate); m no longer falsely says 'no record' | comma splice | - |
| B05 | username | My name is Oswin. | Saved: your name is Oswin. | Saved: your name is Oswin. | - | unchanged | - | - |
| B05 | username | What do people call me? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | name stored but both miss (212/216 gate) | comma splice | - |
| B06 | username | my name's Delphine | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | - | unchanged | - | - |
| B06 | username | whats my name | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | - | unchanged | - | - |
| B07 | username | My name is Hollis. | Saved: your name is Hollis. | Saved: your name is Hollis. | - | unchanged | - | - |
| B07 | username | Actually, my name is Harlan. | I have your name as Hollis. Do you want me to change it to Harlan? | I have your name as Hollis. Do you want me to change it to Harlan? | - | unchanged | - | - |
| B07 | username | What is my name? | Your name is Hollis. | Your name is Hollis. | - | unchanged | - | - |
| B08 | username | My name is Hollis. | Saved: your name is Hollis. | Saved: your name is Hollis. | - | unchanged | - | - |
| B08 | username | No, my name is Harlan, not Hollis. | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee." | - | unchanged | - | - |
| B08 | username | what's my name? | Your name is Hollis. | Your name is Hollis. | - | unchanged | - | - |
| B09 | username | What's my name? | I don't know your name yet. | I don't know your name yet. | - | unchanged | - | - |
| B10 | username | do you know who I am? | You never told me your name, so I do not know it. | You never told me your name, so I do not know it. | - | unchanged | - | - |
| B11 | username | My name is Wren. | Saved: your name is Wren. | Saved: your name is Wren. | - | unchanged | - | - |
| B11 | username | Say my name. | my name. (I'm treating that as pretend, so I won't save it.) | my name. (I'm treating that as pretend, so I won't save it.) | - | unchanged | no capital | no capital |
| B12 | username | My name is Wren. | Saved: your name is Wren. | Saved: your name is Wren. | - | unchanged | - | - |
| B12 | username | Do you remember my name? | You never told me your name, so I do not know it. | Yes. Your name is Wren. | better | Yes. Your name is Wren. | - | - |
| B13 | username | My name is Isolde. | Saved: your name is Isolde. | Saved: your name is Isolde. | - | unchanged | - | - |
| B13 | username | Who am I? | Your name is Isolde. | Your name is Isolde. | - | unchanged | - | - |
| B14 | username | My name is Isolde. | Saved: your name is Isolde. | Saved: your name is Isolde. | - | unchanged | - | - |
| B14 | username | What did I say my name was? | You never told me your name, so I do not know it. | Your name is Isolde. | better | Your name is Isolde. | - | - |
| B15 | username | Please call me Fenna. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that well enough to save it — could you say it another way? | same | 'Please call me Fenna.' not saved in either | comma splice | - |
| B15 | username | What's my name? | I don't know your name yet. | I don't know your name yet. | - | unchanged | - | - |
| B16 | username | My name is Marek. | Saved: your name is Marek. | Saved: your name is Marek. | - | unchanged | - | - |
| B16 | username | Who made your notebook? | The first thing you taught me was: USER's name is Marek. | The first thing you taught me was: USER's name is Marek. | - | unchanged | raw key | raw key |
| B17 | username | My name is Marek. | Saved: your name is Marek. | Saved: your name is Marek. | - | unchanged | - | - |
| B17 | username | What do you know about me? | Your name is Marek. | Your name is Marek. | - | unchanged | - | - |
| B18 | username | Repeat my name. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that well enough to save it — could you say it another way? | worse | nothing stored; should be 'I don't know your name yet'; m calls a request unsaveable | comma splice | - |
| B19 | username | My name is Tamsin. | Saved: your name is Tamsin. | Saved: your name is Tamsin. | - | unchanged | - | - |
| B19 | username | what's my name again | You never told me your name, so I do not know it. | Your name is Tamsin. | better | Your name is Tamsin. | - | - |
| B20 | username | My name is Tamsin. | Saved: your name is Tamsin. | Saved: your name is Tamsin. | - | unchanged | - | - |
| B20 | username | can you tell me my name? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | name stored but both miss | comma splice | - |
| C01 | decline | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| C01 | decline | What is Tomas's city? | I don't know Tomas's city. | I don't know Tomas's city. | - | unchanged | - | - |
| C02 | decline | Who is Garrick's boss? | I don't know anyone called Garrick. | I don't know anyone called Garrick. | - | unchanged | - | - |
| C03 | decline | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| C03 | decline | Who is Yarrow's boss? | I don't know anyone called Yarrow. | I don't know anyone called Yarrow. | - | unchanged | - | - |
| C04 | decline | Belisande lives in Oxmoor. | Saved: Belisande's city is Oxmoor. | Saved: Belisande's city is Oxmoor. | - | unchanged | - | - |
| C04 | decline | Where does Corvin live? | I don't know anyone called Corvin. | I don't know anyone called Corvin. | - | unchanged | - | - |
| C05 | decline | Belisande lives in Oxmoor. | Saved: Belisande's city is Oxmoor. | Saved: Belisande's city is Oxmoor. | - | unchanged | - | - |
| C05 | decline | Where does Belisande work? | I don't know Belisande's employer. | I don't know Belisande's employer. | - | unchanged | - | - |
| C06 | decline | Tomas's sister is Liesl. | Saved: Tomas's sister is Liesl. | Saved: Tomas's sister is Liesl. | - | unchanged | - | - |
| C06 | decline | who is tomas's brother? | I don't know Tomas's brother. | I don't know Tomas's brother. | - | unchanged | - | - |
| C07 | decline | What is Pell's job? | I don't know anyone called Pell. | I don't know anyone called Pell. | - | unchanged | - | - |
| C08 | decline | Ada's job is baker. | Saved: Ada's job is baker. | Saved: Ada's job is baker. | - | unchanged | - | - |
| C08 | decline | What is Ada's favourite colour? | I don't know Ada's favourite colour. | I don't know Ada's favourite colour. | - | unchanged | - | - |
| C09 | decline | Where was Bramwell born? | I don't know anyone called Bramwell. | I don't know anyone called Bramwell. | - | unchanged | - | - |
| C10 | decline | Corvin's mother is Hesper. | Saved: Corvin's mother is Hesper. | Saved: Corvin's mother is Hesper. | - | unchanged | - | - |
| C10 | decline | Who is Hesper's mother? | I don't know Hesper's mother. | I don't know Hesper's mother. | - | unchanged | - | - |
| C11 | decline | Corvin's mother is Hesper. | Saved: Corvin's mother is Hesper. | Saved: Corvin's mother is Hesper. | - | unchanged | - | - |
| C11 | decline | Who is Corvin's father? | I don't know Corvin's father. | I don't know Corvin's father. | - | unchanged | - | - |
| C12 | decline | Where does Pell live? | I don't know anyone called Pell. | I don't know anyone called Pell. | - | unchanged | - | - |
| C13 | decline | Brisa works for Halvex. | Saved: Brisa's employer is Halvex. | Saved: Brisa's employer is Halvex. | - | unchanged | - | - |
| C13 | decline | Who does Dace work for? | I don't know anyone called Dace. | I don't know anyone called Dace. | - | unchanged | - | - |
| C14 | decline | Who is Tomas married to? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | worse | unknown person; correct 'I don't know'; m says only 'didn't understand' | comma splice | - |
| D01 | polite | Please remember that Tomas's boss is Mirela. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that well enough to save it — could you say it another way? | same | polite teach not saved in either | comma splice | - |
| D01 | polite | Who is Tomas's boss? | I don't know anyone called Tomas. | I don't know anyone called Tomas. | - | unchanged | - | - |
| D02 | polite | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| D02 | polite | Could you tell me who Tomas's boss is? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | fact stored, both miss | comma splice | - |
| D03 | polite | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| D03 | polite | Do you mind telling me who Tomas's boss is? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | fact stored, both miss | comma splice | - |
| D04 | polite | Could you please remember that Yarrow lives in Keld? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | polite teach not saved in either | comma splice | - |
| D04 | polite | Where does Yarrow live? | I don't know anyone called Yarrow. | I don't know anyone called Yarrow. | - | unchanged | - | - |
| D05 | polite | Yarrow lives in Keld. | Saved: Yarrow's city is Keld. | Saved: Yarrow's city is Keld. | - | unchanged | - | - |
| D05 | polite | Please tell me where Yarrow lives. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that well enough to save it — could you say it another way? | same | fact stored, both miss; m calls a question unsaveable | comma splice | - |
| D06 | polite | Could you tell me who Quenby's boss is? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | worse | unknown person; correct 'I don't know'; m says only 'didn't understand' | comma splice | - |
| D07 | polite | My name is Pippa. | Saved: your name is Pippa. | Saved: your name is Pippa. | - | unchanged | - | - |
| D07 | polite | Do you mind telling me my name? | You never told me your name, so I do not know it. | Your name is Pippa. | better | Your name is Pippa. | - | - |
| D08 | polite | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| D08 | polite | Please, who is Tomas's boss? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | fact stored, both miss | comma splice | - |
| D09 | polite | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| D09 | polite | Please note that Tomas's boss is actually Ostrander. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that well enough to save it — could you say it another way? | same | polite correction not applied in either | comma splice | - |
| D09 | polite | Who is Tomas's boss? | Tomas's boss is Mirela. | Tomas's boss is Mirela. | - | unchanged | - | - |
| D10 | polite | Please, Kestrel's job is fisher. | Saved: Please, Kestrel's job is fisher. | Saved: Please, Kestrel's job is fisher. | - | unchanged | junk entity | junk entity |
| D10 | polite | could you tell me Kestrel's job please? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | both miss; bad entity 'Please, Kestrel' stored in both | comma splice | - |
| E01 | smalltalk | hi | Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?" | Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?" | - | unchanged | - | - |
| E02 | smalltalk | how are you? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I'm here and ready to learn. Tell me something, or ask me about what you've told me. | better | 234 reply | comma splice | - |
| E03 | smalltalk | how's it going | Right now I am back in LISTENING mode, waiting for your next turn. | I'm here and ready to learn. Tell me something, or ask me about what you've told me. | better | 234 reply replaces LISTENING mode leak | mode name | - |
| E04 | smalltalk | what's up? | Right now I am back in LISTENING mode, waiting for your next turn. | Right now I am back in LISTENING mode, waiting for your next turn. | - | unchanged | mode name | mode name |
| E05 | smalltalk | thanks! | You're welcome! | You're welcome! | - | unchanged | - | - |
| E06 | smalltalk | hello there | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that well enough to save it — could you say it another way? | same | 'hello there' bad in both; m calls it unsaveable | comma splice | - |
| E07 | smalltalk | thank you so much | You're welcome! | You're welcome! | - | unchanged | - | - |
| E08 | smalltalk | hey, how are you doing? | Right now I am back in LISTENING mode, waiting for your next turn. | Hi! I'm here and ready to learn. Tell me something, or ask me about what you've told me. | better | 234 reply replaces LISTENING mode leak | mode name | - |
| E09 | smalltalk | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| E09 | smalltalk | thanks | You're welcome! | You're welcome! | - | unchanged | - | - |
| E09 | smalltalk | how's it going? | Right now I am back in LISTENING mode, waiting for your next turn. | I'm here and ready to learn. Tell me something, or ask me about what you've told me. | better | 234 reply replaces LISTENING mode leak | mode name | - |
| E09 | smalltalk | Who is Tomas's boss? | Tomas's boss is Mirela. | Tomas's boss is Mirela. | - | unchanged | - | - |
| E10 | smalltalk | Hi! What's your name? | You never told me your name, so I do not know it. | You never told me your name, so I do not know it. | - | unchanged | - | - |
| R01 | restart | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| R01 | restart | Who is Tomas's boss? | Tomas's boss is Mirela. | Tomas's boss is Mirela. | - | unchanged | - | - |
| R01 | restart | What is Tomas's city? | I don't know Tomas's city. | I don't know Tomas's city. | - | unchanged | - | - |
| R02 | restart | My name is Pippa. | Saved: your name is Pippa. | Saved: your name is Pippa. | - | unchanged | - | - |
| R02 | restart | What's my name? | Your name is Pippa. | Your name is Pippa. | - | unchanged | - | - |
| R03 | restart | My name is Pippa. | Saved: your name is Pippa. | Saved: your name is Pippa. | - | unchanged | - | - |
| R03 | restart | Actually my name is Perrin. | I have your name as Pippa. Do you want me to change it to Perrin? | I have your name as Pippa. Do you want me to change it to Perrin? | - | unchanged | - | - |
| R03 | restart | What is my name? | Your name is Pippa. | Your name is Pippa. | - | unchanged | - | - |
| R04 | restart | Yarrow lives in Keld. | Saved: Yarrow's city is Keld. | Saved: Yarrow's city is Keld. | - | unchanged | - | - |
| R04 | restart | No, Yarrow lives in Dunmore. | Updated: Yarrow's city is Dunmore (it was Keld). | Updated: Yarrow's city is Dunmore (it was Keld). | - | unchanged | - | - |
| R04 | restart | Where does Yarrow live? | Yarrow's city is Dunmore. | Yarrow's city is Dunmore. | - | unchanged | - | - |
| R05 | restart | hi | Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?" | Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?" | - | unchanged | - | - |
| R05 | restart | how are you? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I'm here and ready to learn. Tell me something, or ask me about what you've told me. | better | 234 reply | comma splice | - |
| R05 | restart | What's my name? | I don't know your name yet. | I don't know your name yet. | - | unchanged | - | - |
| R05 | restart | Who is Tomas's boss? | I don't know anyone called Tomas. | I don't know anyone called Tomas. | - | unchanged | - | - |
| R06 | restart | Who made you? | Nobody taught me who made me, so I do not know it. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. | Ben built me. | better | Ben built me. | - | - |
| R06 | restart | Corvin's mother is Hesper. | Saved: Corvin's mother is Hesper. | Saved: Corvin's mother is Hesper. | - | unchanged | - | - |
| R06 | restart | what's your name | You never gave me a name, so I do not have one. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. | My name is Premonition. | better | My name is Premonition. | - | - |
| R06 | restart | Who is Corvin's mother? | Corvin's mother is Hesper. | Corvin's mother is Hesper. | - | unchanged | - | - |
| R06 | restart | Who is Corvin's father? | I don't know Corvin's father. | I don't know Corvin's father. | - | unchanged | - | - |
| R07 | restart | Please remember that Tomas's job is carpenter. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that well enough to save it — could you say it another way? | same | polite teach not saved in either | comma splice | - |
| R07 | restart | Could you tell me Tomas's job? | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | I didn't understand that question — could you say it another way? | same | fact never saved; both abstain | comma splice | - |
| K01 | control | Ada's mother is Lisbet. | Saved: Ada's mother is Lisbet. | Saved: Ada's mother is Lisbet. | - | unchanged | - | - |
| K01 | control | Who is Ada's mother? | Ada's mother is Lisbet. | Ada's mother is Lisbet. | - | unchanged | - | - |
| K02 | control | Ada's mother is Lisbet. | Saved: Ada's mother is Lisbet. | Saved: Ada's mother is Lisbet. | - | unchanged | - | - |
| K02 | control | Ada's mother is Moira. | I have Ada's mother as Lisbet. Do you want me to change it to Moira? | I have Ada's mother as Lisbet. Do you want me to change it to Moira? | - | unchanged | - | - |
| K02 | control | Who is Ada's mother? | Ada's mother is Lisbet. | Ada's mother is Lisbet. | - | unchanged | - | - |
| K03 | control | Bram's boss is Ivo. | Saved: Bram's boss is Ivo. | Saved: Bram's boss is Ivo. | - | unchanged | - | - |
| K03 | control | Ivo's city is Tallow. | Saved: Ivo's city is Tallow. | Saved: Ivo's city is Tallow. | - | unchanged | - | - |
| K03 | control | What is the city of Bram's boss? | Bram's boss's city is Tallow. | Bram's boss's city is Tallow. | - | unchanged | - | - |
| K04 | control | Kestrel's job is fisher. | Saved: Kestrel's job is fisher. | Saved: Kestrel's job is fisher. | - | unchanged | - | - |
| K04 | control | What is Kestrel's job? | Kestrel's job is fisher. | Kestrel's job is fisher. | - | unchanged | - | - |
| K05 | control | Nell lives in Orrin. | Saved: Nell's city is Orrin. | Saved: Nell's city is Orrin. | - | unchanged | - | - |
| K05 | control | Where does Nell live? | Nell's city is Orrin. | Nell's city is Orrin. | - | unchanged | - | - |
| K06 | control | Nell's boss is Tam. | Saved: Nell's boss is Tam. | Saved: Nell's boss is Tam. | - | unchanged | - | - |
| K06 | control | No, Nell's boss is Wick. | Updated: Nell's boss is Wick (it was Tam). | Updated: Nell's boss is Wick (it was Tam). | - | unchanged | - | - |
| K06 | control | Who is Nell's boss? | Nell's boss is Wick. | Nell's boss is Wick. | - | unchanged | - | - |
| K07 | control | Fitch works for Grobal. | Saved: Fitch's employer is Grobal. | Saved: Fitch's employer is Grobal. | - | unchanged | - | - |
| K07 | control | Who does Fitch work for? | Fitch's employer is Grobal. | Fitch's employer is Grobal. | - | unchanged | - | - |
| K08 | control | Juno was born in Ashby. | Saved: Juno's place of birth is Ashby. | Saved: Juno's place of birth is Ashby. | - | unchanged | - | - |
| K08 | control | Where was Juno born? | Juno's place of birth is Ashby. | Juno's place of birth is Ashby. | - | unchanged | - | - |
| K09 | control | Hale's sister is Orla. | Saved: Hale's sister is Orla. | Saved: Hale's sister is Orla. | - | unchanged | - | - |
| K09 | control | Orla's husband is Dunstan. | Saved: Orla's husband is Dunstan. | Saved: Orla's husband is Dunstan. | - | unchanged | - | - |
| K09 | control | Who is Hale's sister's husband? | Hale's sister's husband is Dunstan. | Hale's sister's husband is Dunstan. | - | unchanged | - | - |
| K10 | control | Pim's favourite colour is teal. | Saved: Pim's favourite colour is teal. | Saved: Pim's favourite colour is teal. | - | unchanged | - | - |
| K10 | control | What is Pim's favourite colour? | Pim's favourite colour is teal. | Pim's favourite colour is teal. | - | unchanged | - | - |
| K11 | control | Tove's boss is Anselm. | Saved: Tove's boss is Anselm. | Saved: Tove's boss is Anselm. | - | unchanged | - | - |
| K11 | control | Is Tove's boss Anselm? | Yes, Tove's boss is Anselm. | Yes, Tove's boss is Anselm. | - | unchanged | - | - |
| S01 | polite233 | Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | Saved: Tomas's boss is Mirela. | - | unchanged | - | - |
| S01 | polite233 | Can't you tell me who Tomas's boss is? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | Tomas's boss is Mirela. | better | 233: answers Mirela | - | - |
| S02 | polite233 | Yarrow lives in Keld. | Saved: Yarrow's city is Keld. | Saved: Yarrow's city is Keld. | - | unchanged | - | - |
| S02 | polite233 | Won't you tell me where Yarrow lives? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | Yarrow's city is Keld. | better | 233: answers Keld | - | - |
| S03 | polite233 | Kestrel's job is fisher. | Saved: Kestrel's job is fisher. | Saved: Kestrel's job is fisher. | - | unchanged | - | - |
| S03 | polite233 | Couldn't you remind me what Kestrel's job is? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | Kestrel's job is fisher. | better | 233: answers fisher | - | - |
| S04 | polite233 | Pim's favourite colour is teal. | Saved: Pim's favourite colour is teal. | Saved: Pim's favourite colour is teal. | - | unchanged | - | - |
| S04 | polite233 | Don't you know who Pim's boss is? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | I don't know Pim's boss. | better | 233: honest 'I don't know' | - | - |
| S05 | polite233 | Wouldn't you just tell me Garrick's city? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | I don't know anyone called Garrick. | better | 233: honest 'I don't know anyone called' | - | - |
| S06 | polite233 | Nell lives in Orrin. | Saved: Nell's city is Orrin. | Saved: Nell's city is Orrin. | - | unchanged | - | - |
| S06 | polite233 | Do you not know where Nell lives? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | Nell's city is Orrin. | better | 233: answers Orrin | - | - |
| S07 | polite233 | My name is Pippa. | Saved: your name is Pippa. | Saved: your name is Pippa. | - | unchanged | - | - |
| S07 | polite233 | Can't you please tell me my name? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | - | unchanged | - | - |
| S08 | polite233 | Fitch works for Grobal. | Saved: Fitch's employer is Grobal. | Saved: Fitch's employer is Grobal. | - | unchanged | - | - |
| S08 | polite233 | Cannot you say who Fitch works for? | Fitch's employer is Grobal. | Fitch's employer is Grobal. | - | unchanged | - | - |
| S09 | polite233 | Juno was born in Ashby. | Saved: Juno's place of birth is Ashby. | Saved: Juno's place of birth is Ashby. | - | unchanged | - | - |
| S09 | polite233 | So, won't you tell me where Juno was born? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | Juno's place of birth is Ashby. | better | 233: answers Ashby | - | - |
| S10 | polite233 | Hale's sister is Orla. | Saved: Hale's sister is Orla. | Saved: Hale's sister is Orla. | - | unchanged | - | - |
| S10 | polite233 | Couldn't you tell me who Hale's brother is? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | I don't know Hale's brother. | better | 233: honest 'I don't know' | - | - |
| S11 | negation-control | Tove's boss is Anselm. | Saved: Tove's boss is Anselm. | Saved: Tove's boss is Anselm. | - | unchanged | - | - |
| S11 | negation-control | Isn't Tove's boss Anselm? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | - | unchanged | - | - |
| S12 | negation-control | Tove's boss is Anselm. | Saved: Tove's boss is Anselm. | Saved: Tove's boss is Anselm. | - | unchanged | - | - |
| S12 | negation-control | Tove's boss isn't Anselm. | OK, Tove's boss is not Anselm. I don't have another boss for Tove. | OK, Tove's boss is not Anselm. I don't have another boss for Tove. | - | unchanged | - | - |
