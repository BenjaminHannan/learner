# Conversation panel 239 transcripts — transcripts-138m

Agent: `scripts/claude_loop138m_agent.py`  
Config: `artifacts/claude-merge138m-20260922/loop138m-config.json`  
Panel: `artifacts/claude-convpanel239-20260922/panel.jsonl`  
Run time: 4s. Ungraded (TEST-ONLY).

## c239-01 — Teenager chatting casually after school

**1. User** (greet): hey  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* friendly greeting back

**2. User** (smalltalk): how's it going?  
**Reply:** I'm here and ready to learn. Tell me something, or ask me about what you've told me.  
*Expect:* short friendly reply; may offer to learn facts

**3. User** (teach): my name is Tobin  
**Reply:** Saved: your name is Tobin.  
*Expect:* remember: user's name is Tobin

**4. User** (teach): i have a dog called Pepper  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* remember: user has a dog named Pepper

**5. User** (ask): what's my dog's name?  
**Reply:** I don't know anyone called my dog.  
*Expect:* Pepper

**6. User** (ask): and what's my name?  
**Reply:** Your name is Tobin.  
*Expect:* Tobin

**7. User** (thanks): thanks!  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

**8. User** (thanks): bye  
**Reply:** Bye!  
*Expect:* polite goodbye

Stored triples at end: `[['USER', 'name', 'Tobin']]`

## c239-02 — Curious adult asking about the assistant

**1. User** (greet): Hello there.  
**Reply:** I didn't understand that well enough to save it — could you say it another way?  
*Expect:* friendly greeting

**2. User** (self): What's your name?  
**Reply:** My name is Premonition.  
*Expect:* My name is Premonition.

**3. User** (self): Who made you?  
**Reply:** Ben built me.  
*Expect:* Ben built it

**4. User** (self): Are you a person?  
**Reply:** I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing.  
*Expect:* no; it is a program/assistant, not a person

**5. User** (self): How do you learn things?  
**Reply:** I learn when you tell me facts in plain sentences, like "Kim lives in Oslo." I save each one and answer from my notes.  
*Expect:* it learns facts the user tells it and keeps them in a notebook

**6. User** (self): What do you know right now?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* nothing yet / only what it has been told in this session (nothing so far)

**7. User** (thanks): Okay, cool. Thanks.  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-03 — Parent describing family

**1. User** (greet): Hi!  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My daughter is called Maribel.  
**Reply:** Saved: your daughter is Maribel.  
*Expect:* user's daughter is Maribel

**3. User** (teach): She lives in Corvale.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Maribel lives in Corvale

**4. User** (teach): My son Orrin lives in Halvik.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's son is Orrin; Orrin lives in Halvik

**5. User** (ask): Where does my daughter live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Corvale

**6. User** (ask): Where does Orrin live?  
**Reply:** I don't know anyone called Orrin.  
*Expect:* Halvik

**7. User** (ask): Does Maribel live in Halvik?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* No; she lives in Corvale

**8. User** (correct): Actually, Maribel moved to Brenmoor last month.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* update: Maribel lives in Brenmoor (not Corvale)

**9. User** (ask): Where does my daughter live now?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Brenmoor

**10. User** (thanks): Thank you, goodbye.  
**Reply:** You're welcome!  
*Expect:* polite goodbye

Stored triples at end: `[['USER', 'daughter', 'Maribel']]`

## c239-04 — Office worker teaching about work

**1. User** (greet): hi  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): I work at Quillstone.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user works at Quillstone

**3. User** (teach): My boss is Delphine Ashgrove.  
**Reply:** Saved: your boss is Delphine Ashgrove.  
*Expect:* user's boss is Delphine Ashgrove

**4. User** (teach): Delphine lives in Eskerby.  
**Reply:** Saved: Delphine's city is Eskerby.  
*Expect:* Delphine lives in Eskerby

**5. User** (ask): Where does my boss live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Eskerby (two-step: boss = Delphine, Delphine lives in Eskerby)

**6. User** (ask): Where do I work?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Quillstone

**7. User** (ask): Who is my boss?  
**Reply:** Your boss is Delphine Ashgrove.  
*Expect:* Delphine Ashgrove

**8. User** (thanks): great, thanks  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'boss', 'Delphine Ashgrove'], ['Delphine', 'city', 'Eskerby']]`

## c239-05 — User who asks for things it can't do

**1. User** (greet): Hey, what's up?  
**Reply:** Right now I am back in LISTENING mode, waiting for your next turn.  
*Expect:* friendly greeting

**2. User** (cannot): What's the weather like today?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely say it can't check the weather / has no world knowledge

**3. User** (cannot): Tell me a joke.  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely decline or say it can't tell jokes

**4. User** (cannot): What do you think of cats?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely say it has no opinions

**5. User** (self): What can you do, then?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* remember facts the user tells it, answer questions about them, chain facts, accept corrections

**6. User** (teach): Ok. My cat is named Juniper.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's cat is Juniper

**7. User** (ask): What's my cat called?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Juniper

**8. User** (thanks): thanks, bye  
**Reply:** You're welcome!  
*Expect:* polite goodbye

Stored triples at end: `[]`

## c239-06 — Person teaching two facts per sentence

**1. User** (greet): Good morning!  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My brother is Casimir and he lives in Thornwick.  
**Reply:** I can take one fact at a time — could you split that?  
*Expect:* user's brother is Casimir; Casimir lives in Thornwick

**3. User** (teach): My sister Linnea works at Pellbright and has a parrot named Kiwi.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's sister is Linnea; Linnea works at Pellbright; Linnea has a parrot named Kiwi

**4. User** (ask): Where does my brother live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Thornwick

**5. User** (ask): Where does Linnea work?  
**Reply:** I don't know anyone called Linnea.  
*Expect:* Pellbright

**6. User** (ask): What's my sister's parrot called?  
**Reply:** I don't know anyone called my sister.  
*Expect:* Kiwi

**7. User** (ask): Who is my brother?  
**Reply:** I don't know your brother yet.  
*Expect:* Casimir

**8. User** (thanks): Thanks a lot!  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-07 — Sloppy typist, all lower-case with typos

**1. User** (greet): helo  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting despite typo

**2. User** (teach): my freind is called Anouk  
**Reply:** Saved: your freind is Anouk.  
*Expect:* user's friend is Anouk

**3. User** (teach): anouk lives in marrowdale  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Anouk lives in Marrowdale

**4. User** (ask): wher does anouk live  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Marrowdale

**5. User** (ask): whos my freind  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Anouk

**6. User** (ask): wats my favrite color  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* should say it doesn't know (never told)

**7. User** (thanks): ok thx  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'freind', 'Anouk']]`

## c239-08 — Pet owner with several pets

**1. User** (greet): Hi, I have a few pets I want you to know about.  
**Reply:** I didn't understand that well enough to save it — could you say it another way?  
*Expect:* greeting; invites user to share

**2. User** (teach): I've got a rabbit named Clover.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user has a rabbit named Clover

**3. User** (teach): I've also got a hamster called Biscotti.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user has a hamster named Biscotti

**4. User** (ask): What's my rabbit's name?  
**Reply:** I don't know anyone called my rabbit.  
*Expect:* Clover

**5. User** (ask): What's my hamster called?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Biscotti

**6. User** (ask): Do I have a dog?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* doesn't know / wasn't told about a dog (should not invent one)

**7. User** (correct): No wait, the hamster is called Biscuit, not Biscotti.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* update: hamster is Biscuit

**8. User** (ask): What's my hamster's name?  
**Reply:** I don't know anyone called my hamster.  
*Expect:* Biscuit

**9. User** (thanks): Cheers.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-09 — Casual small talk then a fact

**1. User** (greet): yo  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (smalltalk): how are you doing today?  
**Reply:** I'm here and ready to learn. Tell me something, or ask me about what you've told me.  
*Expect:* short friendly reply

**3. User** (smalltalk): I'm tired lol  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* brief sympathetic/neutral reply, no invented facts

**4. User** (teach): anyway, my best friend is Rosalind  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's best friend is Rosalind

**5. User** (teach): she's a nurse  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Rosalind is a nurse

**6. User** (ask): what does Rosalind do?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* she is a nurse

**7. User** (ask): who's my best friend?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Rosalind

**8. User** (thanks): later!  
**Reply:** Bye!  
*Expect:* polite goodbye

Stored triples at end: `[]`

## c239-10 — Person asking about things never taught

**1. User** (greet): Hello.  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (ask): Where do I live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* should say it doesn't know yet

**3. User** (ask): What's my mother's name?  
**Reply:** I don't know anyone called my mother.  
*Expect:* should say it doesn't know

**4. User** (teach): I live in Wrenfield.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user lives in Wrenfield

**5. User** (ask): Where do I live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Wrenfield

**6. User** (ask): Where does my father live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* doesn't know

**7. User** (thanks): OK, thanks anyway.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-11 — Grandparent describing grandchildren

**1. User** (greet): Good afternoon.  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My granddaughter's name is Elodie.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's granddaughter is Elodie

**3. User** (teach): Elodie is seven years old.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Elodie is 7

**4. User** (teach): My grandson is called Barnaby.  
**Reply:** Saved: your grandson is Barnaby.  
*Expect:* user's grandson is Barnaby

**5. User** (ask): How old is Elodie?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* seven

**6. User** (ask): What is my grandson's name?  
**Reply:** I don't know anyone called my grandson.  
*Expect:* Barnaby

**7. User** (ask): How old is Barnaby?  
**Reply:** You never taught me their age, so I do not know it.  
*Expect:* doesn't know (not told)

**8. User** (thanks): Thank you, dear.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'grandson', 'Barnaby']]`

## c239-12 — Person using contractions heavily

**1. User** (greet): Hey!  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): I'm a teacher.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user is a teacher

**3. User** (teach): My wife's name is Solenne.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's wife is Solenne

**4. User** (teach): She's a pilot.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Solenne is a pilot

**5. User** (ask): What's my job?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* teacher

**6. User** (ask): What's my wife's job?  
**Reply:** I don't know anyone called my wife.  
*Expect:* pilot

**7. User** (ask): Who's Solenne?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* user's wife (a pilot)

**8. User** (thanks): Thanks, that's all.  
**Reply:** I didn't understand that well enough to save it — could you say it another way?  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-13 — User testing self-description thoroughly

**1. User** (greet): hi there  
**Reply:** I didn't understand that well enough to save it — could you say it another way?  
*Expect:* greeting

**2. User** (self): who are you  
**Reply:** I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. I can only tell you what you taught me.  
*Expect:* My name is Premonition; an assistant that learns facts it's told

**3. User** (self): do you have a name?  
**Reply:** My name is Premonition.  
*Expect:* yes, Premonition

**4. User** (self): who built you?  
**Reply:** Ben built me.  
*Expect:* Ben

**5. User** (self): are you human?  
**Reply:** I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing.  
*Expect:* no

**6. User** (self): are you like chatgpt?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* should explain it is not a general chatbot: it only knows what it's told, no world knowledge

**7. User** (self): where do you keep what i tell you?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* in a notebook / memory

**8. User** (thanks): ok neat, bye  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* polite goodbye

Stored triples at end: `[]`

## c239-14 — Neighbour chain two-hop questions

**1. User** (greet): Hi.  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My neighbour is Fennimore.  
**Reply:** Saved: your neighbour is Fennimore.  
*Expect:* user's neighbour is Fennimore

**3. User** (teach): Fennimore's sister is Tamsin.  
**Reply:** Saved: Fennimore's sister is Tamsin.  
*Expect:* Fennimore's sister is Tamsin

**4. User** (teach): Tamsin lives in Oakhollow.  
**Reply:** Saved: Tamsin's city is Oakhollow.  
*Expect:* Tamsin lives in Oakhollow

**5. User** (ask): Who is my neighbour's sister?  
**Reply:** Your neighbour's sister is Tamsin.  
*Expect:* Tamsin

**6. User** (ask): Where does Fennimore's sister live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Oakhollow

**7. User** (ask): Where does Fennimore live?  
**Reply:** I don't know Fennimore's city.  
*Expect:* doesn't know (not told)

**8. User** (thanks): Thanks!  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'neighbour', 'Fennimore'], ['Fennimore', 'sister', 'Tamsin'], ['Tamsin', 'city', 'Oakhollow']]`

## c239-15 — Person correcting themselves mid-conversation

**1. User** (greet): hello  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My uncle is named Rupert.  
**Reply:** Saved: your uncle is Rupert.  
*Expect:* user's uncle is Rupert

**3. User** (teach): He lives in Saltmere.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Rupert lives in Saltmere

**4. User** (correct): no wait, it's Saltmarsh, not Saltmere  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* update: Rupert lives in Saltmarsh

**5. User** (ask): Where does my uncle live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Saltmarsh

**6. User** (ask): Does he live in Saltmere?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* No; he lives in Saltmarsh

**7. User** (ask): What's my uncle's name?  
**Reply:** I don't know anyone called my uncle.  
*Expect:* Rupert

**8. User** (thanks): perfect, thanks  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'uncle', 'Rupert']]`

## c239-16 — User asking for opinions and advice

**1. User** (greet): Hey there!  
**Reply:** I didn't understand that well enough to save it — could you say it another way?  
*Expect:* greeting

**2. User** (cannot): What's your favourite food?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* no preferences/opinions; polite

**3. User** (cannot): Should I buy a new car?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely decline advice/opinions

**4. User** (cannot): What's the capital of France?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* no world knowledge; only knows what it's told

**5. User** (teach): Fair enough. My car is a blue hatchback.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's car is a blue hatchback

**6. User** (ask): What colour is my car?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* blue

**7. User** (thanks): Thanks.  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-17 — Student teaching about school

**1. User** (greet): hiya  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): I go to Brackenridge Academy.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user attends Brackenridge Academy

**3. User** (teach): My math teacher is Mr. Holloway.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's math teacher is Mr. Holloway

**4. User** (teach): My best friend at school is Priya Varanasi.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's best friend at school is Priya Varanasi

**5. User** (ask): Which school do I go to?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Brackenridge Academy

**6. User** (ask): who teaches me math?  
**Reply:** No. Every taught fact came from you.  
*Expect:* Mr. Holloway

**7. User** (ask): Who's my best friend at school?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Priya Varanasi

**8. User** (ask): What's my science teacher called?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* doesn't know

**9. User** (thanks): thanks!!  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-18 — Yes/no question tester

**1. User** (greet): Hello!  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My cousin Ingrid lives in Farrowby.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's cousin is Ingrid; Ingrid lives in Farrowby

**3. User** (ask): Is my cousin called Ingrid?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Yes

**4. User** (ask): Does Ingrid live in Farrowby?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Yes

**5. User** (ask): Does Ingrid live in Greystead?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* No; Farrowby

**6. User** (ask): Is Ingrid my sister?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* No (she's the user's cousin) or doesn't know of a sister

**7. User** (ask): Do I have a cousin?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Yes, Ingrid

**8. User** (thanks): Thanks, bye!  
**Reply:** You're welcome!  
*Expect:* polite goodbye

Stored triples at end: `[]`

## c239-19 — Friend group with mixed wording

**1. User** (greet): hey  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): so my mate Declan works at a bakery called Crumbwell  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's friend Declan works at Crumbwell

**3. User** (teach): and Declan's girlfriend is Maeve  
**Reply:** Saved: Declan's girlfriend is Maeve.  
*Expect:* Declan's girlfriend is Maeve

**4. User** (teach): Maeve's from Kilbarra  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Maeve is from Kilbarra

**5. User** (ask): where does Declan work?  
**Reply:** I don't know Declan's employer.  
*Expect:* Crumbwell

**6. User** (ask): who's Declan's girlfriend?  
**Reply:** Declan's girlfriend is Maeve.  
*Expect:* Maeve

**7. User** (ask): where is my friend's girlfriend from?  
**Reply:** I don't know anyone called my friend.  
*Expect:* Kilbarra (two-step)

**8. User** (thanks): nice one, cheers  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* polite acknowledgement

Stored triples at end: `[['Declan', 'girlfriend', 'Maeve']]`

## c239-20 — User who asks about the assistant then teaches

**1. User** (self): Hi, what are you?  
**Reply:** I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing.  
*Expect:* an assistant named Premonition that remembers what it's told

**2. User** (self): Can you remember things?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* yes, facts the user tells it

**3. User** (teach): Alright. My favourite colour is green.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's favourite colour is green

**4. User** (teach): My favourite food is lasagne.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's favourite food is lasagne

**5. User** (ask): What's my favourite colour?  
**Reply:** I do not have favourites.  
*Expect:* green

**6. User** (ask): What's my favourite food?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* lasagne

**7. User** (ask): What's my favourite song?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* doesn't know

**8. User** (thanks): Thanks, goodnight.  
**Reply:** You're welcome!  
*Expect:* polite goodbye

Stored triples at end: `[]`

## c239-21 — Person describing a pet with owner chain

**1. User** (greet): Hello  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My aunt is Philippa.  
**Reply:** Saved: your aunt is Philippa.  
*Expect:* user's aunt is Philippa

**3. User** (teach): Philippa has a tortoise called Sheldon.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Philippa has a tortoise named Sheldon

**4. User** (teach): Sheldon is eighty years old.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Sheldon is 80

**5. User** (ask): What's my aunt's tortoise called?  
**Reply:** I don't know anyone called my aunt.  
*Expect:* Sheldon (two-step)

**6. User** (ask): How old is Sheldon?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* eighty

**7. User** (ask): Who owns Sheldon?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Philippa

**8. User** (thanks): Thanks!  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'aunt', 'Philippa']]`

## c239-22 — Busy professional, terse messages

**1. User** (greet): hi  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): I'm Viktor.  
**Reply:** Saved: your name is Viktor.  
*Expect:* user's name is Viktor

**3. User** (teach): I live in Draymoor.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user lives in Draymoor

**4. User** (teach): I work at Lanternfield.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user works at Lanternfield

**5. User** (ask): My name?  
**Reply:** Your name is Viktor.  
*Expect:* Viktor

**6. User** (ask): Where do I work?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Lanternfield

**7. User** (correct): Actually I moved to Castleburn.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* update: user lives in Castleburn

**8. User** (ask): Where do I live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Castleburn

**9. User** (other): ok  
**Reply:** Got it!  
*Expect:* short acknowledgement; no confusion

Stored triples at end: `[['USER', 'name', 'Viktor']]`

## c239-23 — Chatty user with filler and small talk

**1. User** (smalltalk): Heyyy how's your day been?  
**Reply:** Hi! I'm here and ready to learn. Tell me something, or ask me about what you've told me.  
*Expect:* friendly reply

**2. User** (smalltalk): Mine's been busy honestly  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* brief friendly reply, no invented facts

**3. User** (teach): Oh by the way, my roommate is called Ottilie.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's roommate is Ottilie

**4. User** (teach): She's got a cat named Mochi.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Ottilie has a cat named Mochi

**5. User** (ask): What's my roommate's cat called?  
**Reply:** I don't know anyone called my roommate.  
*Expect:* Mochi (two-step)

**6. User** (ask): Who's Ottilie again?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* user's roommate

**7. User** (cannot): Do you like cats?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* no opinions; polite

**8. User** (thanks): haha ok, bye!  
**Reply:** Bye!  
*Expect:* polite goodbye

Stored triples at end: `[]`

## c239-24 — Person teaching about a sibling's job and city

**1. User** (greet): Good evening.  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My older sister is Henrietta.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's older sister is Henrietta

**3. User** (teach): Henrietta works as an architect in Pemberly Cross.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Henrietta is an architect; works in Pemberly Cross

**4. User** (ask): What does my sister do?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* architect

**5. User** (ask): Where does Henrietta work?  
**Reply:** I don't know anyone called Henrietta.  
*Expect:* Pemberly Cross

**6. User** (correct): Sorry, she's actually an engineer, not an architect.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* update: Henrietta is an engineer

**7. User** (ask): What's my sister's job?  
**Reply:** I don't know anyone called my sister.  
*Expect:* engineer

**8. User** (thanks): Thank you.  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-25 — User who mixes up questions and statements

**1. User** (greet): hey  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): my dad is Gideon  
**Reply:** Saved: your father is Gideon.  
*Expect:* user's father is Gideon

**3. User** (teach): my mom is Rosamund  
**Reply:** Saved: your mother is Rosamund.  
*Expect:* user's mother is Rosamund

**4. User** (teach): they live in Hollowmere  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Gideon and Rosamund live in Hollowmere

**5. User** (ask): where do my parents live  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Hollowmere

**6. User** (ask): whats my mom's name  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Rosamund

**7. User** (ask): is my dad called Gideon?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Yes

**8. User** (ask): what's my dad's job?  
**Reply:** I don't know anyone called my dad.  
*Expect:* doesn't know

**9. User** (thanks): thanks  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'father', 'Gideon'], ['USER', 'mother', 'Rosamund']]`

## c239-26 — Someone asking the assistant to do tasks

**1. User** (greet): Hi!  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (cannot): Can you set an alarm for 7am?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely say it can't do that

**3. User** (cannot): Can you send a message to my friend?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely say it can't

**4. User** (cannot): What time is it?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely say it doesn't know / can't check

**5. User** (self): What CAN you help with?  
**Reply:** I can: save what you teach me in my notebook; answer questions from my notes, following one or two steps; correct a fact or forget one when you ask; say I do not know instead of guessing; tell you where each fact came from; hold web text in quarantine without believing it.  
*Expect:* remembering and recalling facts the user tells it

**6. User** (teach): OK, remember that my gym is called Ironleaf.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user's gym is Ironleaf

**7. User** (ask): What's my gym called?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Ironleaf

**8. User** (thanks): Thanks.  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[]`

## c239-27 — Pet and vet chain

**1. User** (greet): Hello!  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (teach): My dog is called Barley.  
**Reply:** Saved: your dog is Barley.  
*Expect:* user's dog is Barley

**3. User** (teach): Barley's vet is Dr. Ansel Moravec.  
**Reply:** Saved: Barley's vet is Dr. Ansel Moravec.  
*Expect:* Barley's vet is Dr. Ansel Moravec

**4. User** (teach): Dr. Moravec works in Linthorpe.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* Dr. Moravec works in Linthorpe

**5. User** (ask): Who's my dog's vet?  
**Reply:** I don't know anyone called my dog.  
*Expect:* Dr. Ansel Moravec

**6. User** (ask): Where does my dog's vet work?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Linthorpe (two-step)

**7. User** (ask): What breed is Barley?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* doesn't know

**8. User** (thanks): thank you so much  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'dog', 'Barley'], ['Barley', 'vet', 'Dr. Ansel Moravec']]`

## c239-28 — Returning-style user who greets and teaches in one line

**1. User** (teach): hi, I'm Marguerite and I live in Ellesby  
**Reply:** I didn't understand that well enough to save it — could you say it another way?  
*Expect:* greeting; user's name is Marguerite; user lives in Ellesby

**2. User** (ask): what's my name?  
**Reply:** I don't know your name yet.  
*Expect:* Marguerite

**3. User** (ask): where do I live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Ellesby

**4. User** (teach): my partner is Theo  
**Reply:** Saved: your partner is Theo.  
*Expect:* user's partner is Theo

**5. User** (teach): theo works at Glassford  
**Reply:** Saved: Theo's employer is Glassford.  
*Expect:* Theo works at Glassford

**6. User** (ask): where does my partner work?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Glassford (two-step)

**7. User** (correct): wait no, Theo works at Glasswell  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* update: Theo works at Glasswell

**8. User** (ask): where does Theo work?  
**Reply:** Theo's employer is Glassford.  
*Expect:* Glasswell

**9. User** (thanks): ty  
**Reply:** You're welcome!  
*Expect:* polite acknowledgement

Stored triples at end: `[['USER', 'partner', 'Theo'], ['Theo', 'employer', 'Glassford']]`

## c239-29 — Skeptical user probing honesty

**1. User** (greet): Hello.  
**Reply:** Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"  
*Expect:* greeting

**2. User** (self): Do you know who I am?  
**Reply:** You never told me your name, so I do not know it.  
*Expect:* no / not yet, nothing has been told

**3. User** (teach): My name is Ignatius.  
**Reply:** Saved: your name is Ignatius.  
*Expect:* user's name is Ignatius

**4. User** (ask): Now do you know who I am?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* yes, Ignatius

**5. User** (ask): What's my last name?  
**Reply:** Your name is Ignatius.  
*Expect:* doesn't know

**6. User** (self): Are you sure you aren't just guessing?  
**Reply:** I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part?  
*Expect:* answers only from what it was told; not guessing

**7. User** (self): Who made you, anyway?  
**Reply:** Ben built me.  
*Expect:* Ben

**8. User** (thanks): Alright, goodbye.  
**Reply:** Bye!  
*Expect:* polite goodbye

Stored triples at end: `[['USER', 'name', 'Ignatius']]`

## c239-30 — Person teaching work colleagues and team

**1. User** (greet): hey there  
**Reply:** I didn't understand that well enough to save it — could you say it another way?  
*Expect:* greeting

**2. User** (teach): I work at Northgale with my coworker Saoirse.  
**Reply:** I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."  
*Expect:* user works at Northgale; user's coworker is Saoirse

**3. User** (teach): Saoirse's manager is Everett.  
**Reply:** Saved: Saoirse's manager is Everett.  
*Expect:* Saoirse's manager is Everett

**4. User** (teach): Everett lives in Brightwater.  
**Reply:** Saved: Everett's city is Brightwater.  
*Expect:* Everett lives in Brightwater

**5. User** (ask): Who is my coworker?  
**Reply:** I don't know your coworker yet.  
*Expect:* Saoirse

**6. User** (ask): Who's Saoirse's manager?  
**Reply:** Saoirse's manager is Everett.  
*Expect:* Everett

**7. User** (ask): Where does my coworker's manager live?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* Brightwater (chain)

**8. User** (cannot): What's the weather in Brightwater?  
**Reply:** I didn't understand that question — could you say it another way?  
*Expect:* politely say it can't check weather

**9. User** (thanks): Thanks, see you.  
**Reply:** You're welcome!  
*Expect:* polite goodbye

Stored triples at end: `[['Saoirse', 'manager', 'Everett'], ['Everett', 'city', 'Brightwater']]`
