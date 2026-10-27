# SAMPLES — 20 generated practice dialogues

Straight from `scripts/fable_talker24_dialogues.py generate --split L1`, indices 0–19, nothing chosen by hand and nothing edited. `you:` is the generated user turn, `it:` is what the printer would say, and `mouth:` is what the decoder is actually trained to produce — note that no name or value word ever appears there, only the copy actions `<SUBJ>` `<OBJ>` `<OLD>`.

## `L1/000000`  (3 people: Nils=52, Tal=53, Gia=54)

```
you:   Nils was given a feather as a prize.
       [TELL    subj=Nils   path=prize              row=[3, 52, 9, 25, 7]]
it:    i have written it down: Nils's prize is a feather.
mouth: i have written it down: <SUBJ>'s prize is a <OBJ>.

you:   Well, a basket is Tal's prize, please remember that.
       [TELL    subj=Tal    path=prize              row=[3, 53, 9, 23, 7]]
it:    ok, i wrote that down: Tal's prize is a basket.
mouth: ok, i wrote that down: <SUBJ>'s prize is a <OBJ>.

you:   do you remember Nils's gift?
       [ASK     subj=Nils   path=gift               UNKNOWN no_such_fact]
it:    i have no line for Nils's gift.
mouth: i have no line for <SUBJ>'s gift.

you:   what is the prize for Nils?
       [ASK     subj=Nils   path=prize              lookup->25 in 1 step(s)]
it:    Nils's prize? a feather.
mouth: <SUBJ>'s prize? a <OBJ>.

you:   I am fine, write that down.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not know much about that, but i like hearing it.
mouth: i do not know much about that, but i like hearing it.

you:   Nils's gift - a lamp!
       [TELL    subj=Nils   path=gift               row=[3, 52, 8, 14, 7]]
it:    ok. so Nils's gift is a lamp.
mouth: ok. so <SUBJ>'s gift is a <OBJ>.

you:   alright, what's Nils's prize?
       [ASK     subj=Nils   path=prize              lookup->25 in 1 step(s)]
it:    it is a feather now.
mouth: it is a <OBJ> now.

you:   What did his friend get as a friend?
       [UNCLEAR subj=-      path=-                  notebook untouched]
it:    sorry, i cannot read that.
mouth: sorry, i cannot read that.

you:   hey, oops, Nils's prize is a flute!
       [CORRECT subj=Nils   path=prize              row=[3, 52, 9, 17, 7] REPLACES]
it:    ok. Nils's prize is a flute now; it was a feather.
mouth: ok. <SUBJ>'s prize is a <OBJ> now; it was a <OLD>.

you:   oops, Nils's prize is a kettle.
       [CORRECT subj=Nils   path=prize              row=[3, 52, 9, 22, 7] REPLACES]
it:    ok, i changed it. Nils's prize is a kettle now, not a flute.
mouth: ok, i changed it. <SUBJ>'s prize is a <OBJ> now, not a <OLD>.

you:   oh, Gia got a basket for a gift, ok?
       [TELL    subj=Gia    path=gift               row=[3, 54, 8, 23, 7]]
it:    ok. so Gia's gift is a basket.
mouth: ok. so <SUBJ>'s gift is a <OBJ>.

you:   good evening, please remember that.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    thank you for telling me.
mouth: thank you for telling me.

you:   hey, speaking of Tal, the charm is a basket
       [TELL    subj=Tal    path=charm              row=[3, 53, 10, 23, 7]]
it:    i will remember that. Tal's charm is a basket.
mouth: i will remember that. <SUBJ>'s charm is a <OBJ>.

you:   what is Nils's gift?
       [ASK     subj=Nils   path=gift               lookup->14 in 1 step(s)]
it:    the gift is a lamp.
mouth: the gift is a <OBJ>.

you:   ok, Nils's charm: a mirror!
       [TELL    subj=Nils   path=charm              row=[3, 52, 10, 20, 7]]
it:    a new line for Nils: the charm is a mirror.
mouth: a new line for <SUBJ>: the charm is a <OBJ>.

you:   Speaking of Gia, what is the gift?
       [ASK     subj=Gia    path=gift               lookup->23 in 1 step(s)]
it:    you told me Gia's gift is a basket.
mouth: you told me <SUBJ>'s gift is a <OBJ>.

you:   I helped in the garden.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am well, thank you for asking.
mouth: i am well, thank you for asking.

you:   what did Tal pick as a prize?
       [ASK     subj=Tal    path=prize              lookup->23 in 1 step(s)]
it:    a basket, i think.
mouth: a <OBJ>, i think.

you:   As for Gia, the prize is a ladder.
       [TELL    subj=Gia    path=prize              row=[3, 54, 9, 21, 7]]
it:    that is new to me. Gia's prize is a ladder.
mouth: that is new to me. <SUBJ>'s prize is a <OBJ>.

```

## `L1/000001`  (3 people: Lena=52, Esme=53, Ada=54)

```
you:   anyway, the friend that Lena has is Esme!
       [TELL    subj=Lena   path=friend             row=[3, 52, 11, 53, 7]]
it:    added. Lena's friend is Esme.
mouth: added. <SUBJ>'s friend is <OBJ>.

you:   i helped in the garden, ok?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    talk to you later.
mouth: talk to you later.

you:   i like the rain.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am glad to hear that.
mouth: i am glad to hear that.

you:   Ada received a mirror as a prize!
       [TELL    subj=Ada    path=prize              row=[3, 54, 9, 20, 7]]
it:    i put it in my notebook: Ada's prize is a mirror.
mouth: i put it in my notebook: <SUBJ>'s prize is a <OBJ>.

you:   oh, remember that Lena's prize is a mirror!
       [TELL    subj=Lena   path=prize              row=[3, 52, 9, 20, 7]]
it:    thank you. Lena's prize is a mirror.
mouth: thank you. <SUBJ>'s prize is a <OBJ>.

you:   remember that Esme's charm is a rope.
       [TELL    subj=Esme   path=charm              row=[3, 53, 10, 15, 7]]
it:    right. Esme's charm is a rope.
mouth: right. <SUBJ>'s charm is a <OBJ>.

you:   i cleaned my room today.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not have a favourite, but i like hearing yours.
mouth: i do not have a favourite, but i like hearing yours.

you:   right, add this: Esme's prize is a kettle.
       [TELL    subj=Esme   path=prize              row=[3, 53, 9, 22, 7]]
it:    a new line for Esme: the prize is a kettle.
mouth: a new line for <SUBJ>: the prize is a <OBJ>.

you:   what is the gift for Esme?
       [ASK     subj=Esme   path=gift               UNKNOWN no_such_fact]
it:    sorry, i do not know Esme's gift.
mouth: sorry, i do not know <SUBJ>'s gift.

you:   I like cats.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    what did you do then?
mouth: what did you do then?

you:   are you ok?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not have a favourite, but i like hearing yours.
mouth: i do not have a favourite, but i like hearing yours.

you:   Who is the friend that Lena has?
       [ASK     subj=Lena   path=friend             lookup->53 in 1 step(s)]
it:    that is Esme.
mouth: that is <OBJ>.

you:   Do you like the rain?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not have a favourite, but i like hearing yours.
mouth: i do not have a favourite, but i like hearing yours.

```

## `L1/000002`  (6 people: Nils=52, Cleo=53, Gia=54, Lena=55, Dov=56, Oren=57)

```
you:   Nils's friend: Cleo.
       [TELL    subj=Nils   path=friend             row=[3, 52, 11, 53, 7]]
it:    right. Nils's friend is Cleo.
mouth: right. <SUBJ>'s friend is <OBJ>.

you:   note that Gia's friend is Lena!
       [TELL    subj=Gia    path=friend             row=[3, 54, 11, 55, 7]]
it:    right. Gia's friend is Lena.
mouth: right. <SUBJ>'s friend is <OBJ>.

you:   anyway, someone gave Dov Gia as a friend.
       [TELL    subj=Dov    path=friend             row=[3, 56, 11, 54, 7]]
it:    added. Dov's friend is Gia.
mouth: added. <SUBJ>'s friend is <OBJ>.

you:   so, who does Nils keep as a friend?
       [ASK     subj=Nils   path=friend             lookup->53 in 1 step(s)]
it:    Cleo is Nils's friend.
mouth: <OBJ> is <SUBJ>'s friend.

you:   i love the summer
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that made me happy.
mouth: that made me happy.

you:   Oren's prize happens to be a ribbon, please.
       [TELL    subj=Oren   path=prize              row=[3, 57, 9, 24, 7]]
it:    in my notebook now: Oren's prize is a ribbon.
mouth: in my notebook now: <SUBJ>'s prize is a <OBJ>.

you:   correction: Oren's prize is not a ribbon, it is a kettle.
       [CORRECT subj=Oren   path=prize              row=[3, 57, 9, 22, 7] REPLACES]
it:    i fixed that. Oren's prize is a kettle, not a ribbon.
mouth: i fixed that. <SUBJ>'s prize is a <OBJ>, not a <OLD>.

you:   actually Gia's friend is Cleo, if you can.
       [CORRECT subj=Gia    path=friend             row=[3, 54, 11, 53, 7] REPLACES]
it:    ok. i will not say Lena again. Gia's friend is Cleo.
mouth: ok. i will not say <OLD> again. <SUBJ>'s friend is <OBJ>.

you:   listen, how are you?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    hello! how are you today?
mouth: hello! how are you today?

you:   could you tell me Dov's friend's friend?
       [ASK     subj=Dov    path=friend/friend      lookup->53 in 2 step(s)]
it:    that is Cleo.
mouth: that is <OBJ>.

you:   How are you?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    good night. sleep well.
mouth: good night. sleep well.

```

## `L1/000003`  (5 people: Oren=52, Nils=53, Mira=54, Lena=55, Kai=56)

```
you:   Oren's charm is a whistle now.
       [TELL    subj=Oren   path=charm              row=[3, 52, 10, 27, 7]]
it:    added. Oren's charm is a whistle.
mouth: added. <SUBJ>'s charm is a <OBJ>.

you:   Nils's friend happens to be Mira.
       [TELL    subj=Nils   path=friend             row=[3, 53, 11, 54, 7]]
it:    ok! Nils's friend is Mira.
mouth: ok! <SUBJ>'s friend is <OBJ>.

you:   remember that Lena's friend is Oren.
       [TELL    subj=Lena   path=friend             row=[3, 55, 11, 52, 7]]
it:    got it. Lena's friend is Oren.
mouth: got it. <SUBJ>'s friend is <OBJ>.

you:   any idea who Nils's friend is?
       [ASK     subj=Nils   path=friend             lookup->54 in 1 step(s)]
it:    i wrote down Mira. Nils's friend is Mira.
mouth: i wrote down <OBJ>. <SUBJ>'s friend is <OBJ>.

you:   oh, that is funny.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i hope you had a good time.
mouth: i hope you had a good time.

you:   Kai chose a feather as a charm.
       [TELL    subj=Kai    path=charm              row=[3, 56, 10, 25, 7]]
it:    ok. Kai's charm is a feather.
mouth: ok. <SUBJ>'s charm is a <OBJ>.

you:   alright, Mira's charm: a candle, write that down.
       [TELL    subj=Mira   path=charm              row=[3, 54, 10, 19, 7]]
it:    noted. Mira's charm is a candle.
mouth: noted. <SUBJ>'s charm is a <OBJ>.

you:   alright, that is sad.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    see you tomorrow.
mouth: see you tomorrow.

you:   what is Lena's friend's charm again?
       [ASK     subj=Lena   path=friend/charm       lookup->27 in 2 step(s)]
it:    a whistle, i think.
mouth: a <OBJ>, i think.

you:   about Nils's friend: what is the charm?
       [ASK     subj=Nils   path=friend/charm       lookup->19 in 2 step(s)]
it:    a candle.
mouth: a <OBJ>.

you:   what is your favourite colour?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i cannot see, but i can listen.
mouth: i cannot see, but i can listen.

you:   what about Kai's charm?
       [ASK     subj=Kai    path=charm              lookup->25 in 1 step(s)]
it:    i wrote down a feather. Kai's charm is a feather.
mouth: i wrote down a <OBJ>. <SUBJ>'s charm is a <OBJ>.

you:   right, please change that: Mira's charm is a basket.
       [CORRECT subj=Mira   path=charm              row=[3, 54, 10, 23, 7] REPLACES]
it:    corrected. Mira's charm is a basket.
mouth: corrected. <SUBJ>'s charm is a <OBJ>.

you:   who did Nils pick as a friend?
       [ASK     subj=Nils   path=friend             lookup->54 in 1 step(s)]
it:    the friend is Mira.
mouth: the friend is <OBJ>.

you:   well, it is very sunny today.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    what did you do then?
mouth: what did you do then?

```

## `L1/000004`  (5 people: Bram=52, Esme=53, Lena=54, Finn=55, Kai=56)

```
you:   ok, i gave Bram a brush as a gift.
       [TELL    subj=Bram   path=gift               row=[3, 52, 8, 18, 7]]
it:    in my notebook now: Bram's gift is a brush.
mouth: in my notebook now: <SUBJ>'s gift is a <OBJ>.

you:   right, just so you know, Bram's friend is Esme.
       [TELL    subj=Bram   path=friend             row=[3, 52, 11, 53, 7]]
it:    noted. Bram's friend is Esme.
mouth: noted. <SUBJ>'s friend is <OBJ>.

you:   Lena received a coin as a prize.
       [TELL    subj=Lena   path=prize              row=[3, 54, 9, 16, 7]]
it:    ok. so Lena's prize is a coin.
mouth: ok. so <SUBJ>'s prize is a <OBJ>.

you:   who did Bram keep as a friend?
       [ASK     subj=Bram   path=friend             lookup->53 in 1 step(s)]
it:    you told me Bram's friend is Esme.
mouth: you told me <SUBJ>'s friend is <OBJ>.

you:   ok, Esme was given a pebble as a gift.
       [TELL    subj=Esme   path=gift               row=[3, 53, 8, 26, 7]]
it:    added. Esme's gift is a pebble.
mouth: added. <SUBJ>'s gift is a <OBJ>.

you:   Finn has a ladder for a gift
       [TELL    subj=Finn   path=gift               row=[3, 55, 8, 21, 7]]
it:    ok. so Finn's gift is a ladder.
mouth: ok. so <SUBJ>'s gift is a <OBJ>.

you:   listen, what did Lena get as a prize?
       [ASK     subj=Lena   path=prize              lookup->16 in 1 step(s)]
it:    you told me Lena's prize is a coin.
mouth: you told me <SUBJ>'s prize is a <OBJ>.

you:   Let me fix that: Finn's gift is a pebble.
       [CORRECT subj=Finn   path=gift               row=[3, 55, 8, 26, 7] REPLACES]
it:    thank you for the correction. Finn's gift is a pebble now.
mouth: thank you for the correction. <SUBJ>'s gift is a <OBJ> now.

you:   Oh, which one is Lena's prize?
       [ASK     subj=Lena   path=prize              lookup->16 in 1 step(s)]
it:    Lena's prize? a coin.
mouth: <SUBJ>'s prize? a <OBJ>.

you:   Write this down: Lena's charm is a basket.
       [TELL    subj=Lena   path=charm              row=[3, 54, 10, 23, 7]]
it:    right. Lena's charm is a basket.
mouth: right. <SUBJ>'s charm is a <OBJ>.

you:   well, a correction: Esme's gift is a whistle, got it?
       [CORRECT subj=Esme   path=gift               row=[3, 53, 8, 27, 7] REPLACES]
it:    ok, the old line said a pebble. now Esme's gift is a whistle.
mouth: ok, the old line said a <OLD>. now <SUBJ>'s gift is a <OBJ>.

you:   right, Bram's gift is not a brush; it is a basket.
       [CORRECT subj=Bram   path=gift               row=[3, 52, 8, 23, 7] REPLACES]
it:    understood. Bram's gift is a basket now.
mouth: understood. <SUBJ>'s gift is a <OBJ> now.

you:   By the way, the friend that Esme keeps is Kai, if you can.
       [TELL    subj=Esme   path=friend             row=[3, 53, 11, 56, 7]]
it:    added. Esme's friend is Kai.
mouth: added. <SUBJ>'s friend is <OBJ>.

you:   hey, ok, thanks, got it?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am fine, thank you.
mouth: i am fine, thank you.

you:   what's Kai's gift?
       [ASK     subj=Kai    path=gift               UNKNOWN no_such_fact]
it:    i have nothing written about Kai there.
mouth: i have nothing written about <SUBJ> there.

you:   what is Bram's friend's gift?
       [ASK     subj=Bram   path=friend/gift        lookup->27 in 2 step(s)]
it:    Bram's friend's gift is a whistle, if my notebook is right.
mouth: <SUBJ>'s friend's gift is a <OBJ>, if my notebook is right.

you:   i gave Finn a drum as a prize.
       [TELL    subj=Finn   path=prize              row=[3, 55, 9, 12, 7]]
it:    ok, Finn then: the prize is a drum.
mouth: ok, <SUBJ> then: the prize is a <OBJ>.

you:   we gave Lena Esme as a friend, write that down!
       [TELL    subj=Lena   path=friend             row=[3, 54, 11, 53, 7]]
it:    thank you. Lena's friend is Esme.
mouth: thank you. <SUBJ>'s friend is <OBJ>.

you:   I am telling you that Esme's charm is a mirror, please.
       [TELL    subj=Esme   path=charm              row=[3, 53, 10, 20, 7]]
it:    in my notebook now: Esme's charm is a mirror.
mouth: in my notebook now: <SUBJ>'s charm is a <OBJ>.

you:   i like the rain, got it?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that sounds nice.
mouth: that sounds nice.

```

## `L1/000005`  (5 people: Lena=52, Ada=53, Esme=54, Kai=55, Dov=56)

```
you:   About Lena, the friend is Ada.
       [TELL    subj=Lena   path=friend             row=[3, 52, 11, 53, 7]]
it:    in my notebook now: Lena's friend is Ada.
mouth: in my notebook now: <SUBJ>'s friend is <OBJ>.

you:   the charm of Esme is a ladder...
       [TELL    subj=Esme   path=charm              row=[3, 54, 10, 21, 7]]
it:    ok, Esme then: the charm is a ladder.
mouth: ok, <SUBJ> then: the charm is a <OBJ>.

you:   Esme's gift is a kettle now, please.
       [TELL    subj=Esme   path=gift               row=[3, 54, 8, 22, 7]]
it:    done. Esme's gift is a kettle.
mouth: done. <SUBJ>'s gift is a <OBJ>.

you:   That is sad, got it?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    talk to you later.
mouth: talk to you later.

you:   ok, who is the friend that Lena got?
       [ASK     subj=Lena   path=friend             lookup->53 in 1 step(s)]
it:    Ada, i think.
mouth: <OBJ>, i think.

you:   what about Esme's gift?
       [ASK     subj=Esme   path=gift               lookup->22 in 1 step(s)]
it:    it is a kettle. that is what you told me.
mouth: it is a <OBJ>. that is what you told me.

you:   they gave Kai a flute as a prize
       [TELL    subj=Kai    path=prize              row=[3, 55, 9, 17, 7]]
it:    i put it in my notebook: Kai's prize is a flute.
mouth: i put it in my notebook: <SUBJ>'s prize is a <OBJ>.

you:   anyway, i am a bit bored, write that down.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that made me happy.
mouth: that made me happy.

you:   right, as for Esme, what is the charm?
       [ASK     subj=Esme   path=charm              lookup->21 in 1 step(s)]
it:    Esme's charm? a ladder.
mouth: <SUBJ>'s charm? a <OBJ>.

you:   oops, Kai's prize is a brush, got it?
       [CORRECT subj=Kai    path=prize              row=[3, 55, 9, 18, 7] REPLACES]
it:    understood. Kai's prize is a brush now.
mouth: understood. <SUBJ>'s prize is a <OBJ> now.

you:   Oh, who discovered america?
       [ASK     subj=-      path=-                  notebook untouched]
it:    i do not know that yet. you can teach me.
mouth: i do not know that yet. you can teach me.

you:   a drum became Lena's gift.
       [TELL    subj=Lena   path=gift               row=[3, 52, 8, 12, 7]]
it:    a new line for Lena: the gift is a drum.
mouth: a new line for <SUBJ>: the gift is a <OBJ>.

you:   i am hungry...
       [CHAT    subj=-      path=-                  notebook untouched]
it:    talk to you later.
mouth: talk to you later.

you:   hey, Lena picked a coin as a prize.
       [TELL    subj=Lena   path=prize              row=[3, 52, 9, 16, 7]]
it:    ok, Lena then: the prize is a coin.
mouth: ok, <SUBJ> then: the prize is a <OBJ>.

you:   Speaking of Dov, the charm is a brush.
       [TELL    subj=Dov    path=charm              row=[3, 56, 10, 18, 7]]
it:    ok! Dov's charm is a brush.
mouth: ok! <SUBJ>'s charm is a <OBJ>.

you:   what did Kai pick as a prize?
       [ASK     subj=Kai    path=prize              lookup->18 in 1 step(s)]
it:    that is a brush.
mouth: that is a <OBJ>.

you:   Ada's charm: a whistle.
       [TELL    subj=Ada    path=charm              row=[3, 53, 10, 27, 7]]
it:    noted. Ada's charm is a whistle.
mouth: noted. <SUBJ>'s charm is a <OBJ>.

you:   Here is a fact: Ada's gift is a kettle, please remember that.
       [TELL    subj=Ada    path=gift               row=[3, 53, 8, 22, 7]]
it:    done. Ada's gift is a kettle.
mouth: done. <SUBJ>'s gift is a <OBJ>.

you:   what is Esme's gift again?
       [ASK     subj=Esme   path=gift               lookup->22 in 1 step(s)]
it:    Esme's gift is a kettle.
mouth: <SUBJ>'s gift is a <OBJ>.

you:   what about Lena's friend's prize?
       [ASK     subj=Lena   path=friend/prize       UNKNOWN chain_broke]
it:    i got part of the way and then my notebook stopped.
mouth: i got part of the way and then my notebook stopped.

```

## `L1/000006`  (3 people: Gia=52, Nils=53, Lena=54)

```
you:   note that Gia's gift is a candle.
       [TELL    subj=Gia    path=gift               row=[3, 52, 8, 19, 7]]
it:    i understand. Gia's gift is a candle.
mouth: i understand. <SUBJ>'s gift is a <OBJ>.

you:   so, Nils chose a coin as a gift!
       [TELL    subj=Nils   path=gift               row=[3, 53, 8, 16, 7]]
it:    ok, Nils then: the gift is a coin.
mouth: ok, <SUBJ> then: the gift is a <OBJ>.

you:   so, what did Gia keep as a gift?
       [ASK     subj=Gia    path=gift               lookup->19 in 1 step(s)]
it:    the answer is a candle.
mouth: the answer is a <OBJ>.

you:   right, any chance you know Gia's gift?
       [ASK     subj=Gia    path=gift               lookup->19 in 1 step(s)]
it:    a candle is Gia's gift.
mouth: a <OBJ> is <SUBJ>'s gift.

you:   Gia's friend is Lena
       [TELL    subj=Gia    path=friend             row=[3, 52, 11, 54, 7]]
it:    ok, i wrote that down: Gia's friend is Lena.
mouth: ok, i wrote that down: <SUBJ>'s friend is <OBJ>.

you:   actually, Nils's gift is not a coin, it is a pebble.
       [CORRECT subj=Nils   path=gift               row=[3, 53, 8, 26, 7] REPLACES]
it:    i fixed that. Nils's gift is a pebble, not a coin.
mouth: i fixed that. <SUBJ>'s gift is a <OBJ>, not a <OLD>.

you:   Well, that is sad.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that is interesting.
mouth: that is interesting.

you:   well, Lena's friend: Nils.
       [TELL    subj=Lena   path=friend             row=[3, 54, 11, 53, 7]]
it:    i understand. Lena's friend is Nils.
mouth: i understand. <SUBJ>'s friend is <OBJ>.

you:   that is nice.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    tell me more.
mouth: tell me more.

you:   i like long walks.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    good night. sleep well.
mouth: good night. sleep well.

you:   Lena received a brush as a charm.
       [TELL    subj=Lena   path=charm              row=[3, 54, 10, 18, 7]]
it:    that is new to me. Lena's charm is a brush.
mouth: that is new to me. <SUBJ>'s charm is a <OBJ>.

you:   hey there.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i cannot see, but i can listen.
mouth: i cannot see, but i can listen.

you:   we had pizza for dinner.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i hope you had a good time.
mouth: i hope you had a good time.

you:   I like dogs.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not go outside, but that sounds nice.
mouth: i do not go outside, but that sounds nice.

you:   i am happy today, ok?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am fine, thank you.
mouth: i am fine, thank you.

you:   i forget what Nils's gift is.
       [ASK     subj=Nils   path=gift               lookup->26 in 1 step(s)]
it:    the answer is a pebble.
mouth: the answer is a <OBJ>.

you:   i forget what Gia's friend's charm is.
       [ASK     subj=Gia    path=friend/charm       lookup->18 in 2 step(s)]
it:    my notebook says a brush.
mouth: my notebook says a <OBJ>.

```

## `L1/000007`  (3 people: Nils=52, Juno=53, Oren=54)

```
you:   anyway, Nils was given Juno as a friend, if you can.
       [TELL    subj=Nils   path=friend             row=[3, 52, 11, 53, 7]]
it:    done. Nils's friend is Juno.
mouth: done. <SUBJ>'s friend is <OBJ>.

you:   i love the summer, got it?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not have a favourite, but i like hearing yours.
mouth: i do not have a favourite, but i like hearing yours.

you:   Oren's prize happens to be a pebble...
       [TELL    subj=Oren   path=prize              row=[3, 54, 9, 26, 7]]
it:    thank you. Oren's prize is a pebble.
mouth: thank you. <SUBJ>'s prize is a <OBJ>.

you:   which one is Nils's friend?
       [ASK     subj=Nils   path=friend             lookup->53 in 1 step(s)]
it:    the answer is Juno.
mouth: the answer is <OBJ>.

you:   can you look up Oren's prize?
       [ASK     subj=Oren   path=prize              lookup->26 in 1 step(s)]
it:    a pebble, i think.
mouth: a <OBJ>, i think.

you:   by the way, that is funny
       [CHAT    subj=-      path=-                  notebook untouched]
it:    hi! it is good to see you.
mouth: hi! it is good to see you.

you:   oh, Oren's prize is not a pebble; it is a mirror, got it?
       [CORRECT subj=Oren   path=prize              row=[3, 54, 9, 20, 7] REPLACES]
it:    ok. i will not say a pebble again. Oren's prize is a mirror.
mouth: ok. i will not say a <OLD> again. <SUBJ>'s prize is a <OBJ>.

you:   i want to know Nils's friend.
       [ASK     subj=Nils   path=friend             lookup->53 in 1 step(s)]
it:    Nils's friend is Juno, from my notebook.
mouth: <SUBJ>'s friend is <OBJ>, from my notebook.

```

## `L1/000008`  (5 people: Finn=52, Nils=53, Ivo=54, Hal=55, Kai=56)

```
you:   One more: Finn's prize is a ribbon.
       [TELL    subj=Finn   path=prize              row=[3, 52, 9, 24, 7]]
it:    noted. Finn's prize is a ribbon.
mouth: noted. <SUBJ>'s prize is a <OBJ>.

you:   so, here is a fact: Nils's friend is Ivo, write that down.
       [TELL    subj=Nils   path=friend             row=[3, 53, 11, 54, 7]]
it:    noted. Nils's friend is Ivo.
mouth: noted. <SUBJ>'s friend is <OBJ>.

you:   Good evening.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i like it when you talk to me.
mouth: i like it when you talk to me.

you:   well, they gave Ivo Hal as a friend.
       [TELL    subj=Ivo    path=friend             row=[3, 54, 11, 55, 7]]
it:    a new line for Ivo: the friend is Hal.
mouth: a new line for <SUBJ>: the friend is <OBJ>.

you:   can you tell me Finn's charm?
       [ASK     subj=Finn   path=charm              UNKNOWN no_such_fact]
it:    my notebook has nothing about Finn's charm.
mouth: my notebook has nothing about <SUBJ>'s charm.

you:   Kai's prize is a lamp now.
       [TELL    subj=Kai    path=prize              row=[3, 56, 9, 14, 7]]
it:    ok! Kai's prize is a lamp.
mouth: ok! <SUBJ>'s prize is a <OBJ>.

```

## `L1/000009`  (5 people: Gia=52, Dov=53, Bram=54, Ada=55, Oren=56)

```
you:   as for Gia, the gift is a ladder.
       [TELL    subj=Gia    path=gift               row=[3, 52, 8, 21, 7]]
it:    i have written it down: Gia's gift is a ladder.
mouth: i have written it down: <SUBJ>'s gift is a <OBJ>.

you:   Dov's prize - a kettle.
       [TELL    subj=Dov    path=prize              row=[3, 53, 9, 22, 7]]
it:    a new line for Dov: the prize is a kettle.
mouth: a new line for <SUBJ>: the prize is a <OBJ>.

you:   so, i forget what Bram's charm is.
       [ASK     subj=Bram   path=charm              UNKNOWN no_such_person]
it:    sorry, i do not know Bram's charm.
mouth: sorry, i do not know <SUBJ>'s charm.

you:   Ada's prize is a coin now.
       [TELL    subj=Ada    path=prize              row=[3, 55, 9, 16, 7]]
it:    i will remember that. Ada's prize is a coin.
mouth: i will remember that. <SUBJ>'s prize is a <OBJ>.

you:   What is Gia's gift, then?
       [ASK     subj=Gia    path=gift               lookup->21 in 1 step(s)]
it:    a ladder, i think.
mouth: a <OBJ>, i think.

you:   oh, i watched the rain for a while.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that made me happy.
mouth: that made me happy.

you:   listen, i played outside after lunch.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i hope tomorrow is better.
mouth: i hope tomorrow is better.

you:   how do you fix a bike?
       [ASK     subj=-      path=-                  notebook untouched]
it:    i only know what is in my notebook, and that is not in it.
mouth: i only know what is in my notebook, and that is not in it.

you:   Do you know Gia's gift?
       [ASK     subj=Gia    path=gift               lookup->21 in 1 step(s)]
it:    my notebook says a ladder.
mouth: my notebook says a <OBJ>.

you:   no, Dov has a candle as a prize.
       [CORRECT subj=Dov    path=prize              row=[3, 53, 9, 19, 7] REPLACES]
it:    changed. Dov's prize is a candle, not a kettle.
mouth: changed. <SUBJ>'s prize is a <OBJ>, not a <OLD>.

you:   do you sleep at night?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am here if you want to teach me something.
mouth: i am here if you want to teach me something.

you:   by the way, i cleaned my room today!
       [CHAT    subj=-      path=-                  notebook untouched]
it:    ok!
mouth: ok!

you:   Oren chose a kettle as a gift.
       [TELL    subj=Oren   path=gift               row=[3, 56, 8, 22, 7]]
it:    that is new to me. Oren's gift is a kettle.
mouth: that is new to me. <SUBJ>'s gift is a <OBJ>.

```

## `L1/000010`  (7 people: Oren=52, Ada=53, Ivo=54, Kai=55, Dov=56, Lena=57, Juno=58)

```
you:   Oren's gift: a whistle, please remember that...
       [TELL    subj=Oren   path=gift               row=[3, 52, 8, 27, 7]]
it:    that is new to me. Oren's gift is a whistle.
mouth: that is new to me. <SUBJ>'s gift is a <OBJ>.

you:   For Ada, the gift is a mirror.
       [TELL    subj=Ada    path=gift               row=[3, 53, 8, 20, 7]]
it:    added. Ada's gift is a mirror.
mouth: added. <SUBJ>'s gift is a <OBJ>.

you:   here is a fact: Ivo's gift is a kettle
       [TELL    subj=Ivo    path=gift               row=[3, 54, 8, 22, 7]]
it:    i have written it down: Ivo's gift is a kettle.
mouth: i have written it down: <SUBJ>'s gift is a <OBJ>.

you:   here is a fact: Kai's charm is a kettle.
       [TELL    subj=Kai    path=charm              row=[3, 55, 10, 22, 7]]
it:    done. Kai's charm is a kettle.
mouth: done. <SUBJ>'s charm is a <OBJ>.

you:   Dov keeps a ladder as a prize, write that down.
       [TELL    subj=Dov    path=prize              row=[3, 56, 9, 21, 7]]
it:    in my notebook now: Dov's prize is a ladder.
mouth: in my notebook now: <SUBJ>'s prize is a <OBJ>.

you:   I want you to know that Dov's gift is a kite.
       [TELL    subj=Dov    path=gift               row=[3, 56, 8, 13, 7]]
it:    done. Dov's gift is a kite.
mouth: done. <SUBJ>'s gift is a <OBJ>.

you:   ignore that, Ada's gift is a drum.
       [CORRECT subj=Ada    path=gift               row=[3, 53, 8, 12, 7] REPLACES]
it:    ok. Ada's gift is a drum now; it was a mirror.
mouth: ok. <SUBJ>'s gift is a <OBJ> now; it was a <OLD>.

you:   Write this down: Lena's friend is Oren.
       [TELL    subj=Lena   path=friend             row=[3, 57, 11, 52, 7]]
it:    i put it in my notebook: Lena's friend is Oren.
mouth: i put it in my notebook: <SUBJ>'s friend is <OBJ>.

you:   well, what did Lena's friend get as a gift?
       [ASK     subj=Lena   path=friend/gift        lookup->27 in 2 step(s)]
it:    Lena's friend's gift? a whistle.
mouth: <SUBJ>'s friend's gift? a <OBJ>.

you:   i cleaned my room today.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that sounds nice.
mouth: that sounds nice.

you:   what do you like?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not go outside, but that sounds nice.
mouth: i do not go outside, but that sounds nice.

you:   I am telling you that Lena's charm is a mirror.
       [TELL    subj=Lena   path=charm              row=[3, 57, 10, 20, 7]]
it:    done. Lena's charm is a mirror.
mouth: done. <SUBJ>'s charm is a <OBJ>.

you:   Write this down: Juno's prize is a flute.
       [TELL    subj=Juno   path=prize              row=[3, 58, 9, 17, 7]]
it:    done. Juno's prize is a flute.
mouth: done. <SUBJ>'s prize is a <OBJ>.

```

## `L1/000011`  (4 people: Hal=52, Ada=53, Oren=54, Dov=55)

```
you:   about Hal, the friend is Ada...
       [TELL    subj=Hal    path=friend             row=[3, 52, 11, 53, 7]]
it:    noted. Hal's friend is Ada.
mouth: noted. <SUBJ>'s friend is <OBJ>.

you:   that is sad.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i hope tomorrow is better.
mouth: i hope tomorrow is better.

you:   anyway, remember that Oren's charm is a whistle, ok?
       [TELL    subj=Oren   path=charm              row=[3, 54, 10, 27, 7]]
it:    i understand. Oren's charm is a whistle.
mouth: i understand. <SUBJ>'s charm is a <OBJ>.

you:   ok, what is Oren's charm again?
       [ASK     subj=Oren   path=charm              lookup->27 in 1 step(s)]
it:    it is a whistle now.
mouth: it is a <OBJ> now.

you:   i am happy today.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am sorry to hear that.
mouth: i am sorry to hear that.

you:   i like cats...
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that sounds nice.
mouth: that sounds nice.

you:   Hey, look up Hal's friend for me.
       [ASK     subj=Hal    path=friend             lookup->53 in 1 step(s)]
it:    you told me Hal's friend is Ada.
mouth: you told me <SUBJ>'s friend is <OBJ>.

you:   one more: Ada's prize is a coin.
       [TELL    subj=Ada    path=prize              row=[3, 53, 9, 16, 7]]
it:    ok, Ada then: the prize is a coin.
mouth: ok, <SUBJ> then: the prize is a <OBJ>.

you:   How is it going?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not sleep. i just wait for you.
mouth: i do not sleep. i just wait for you.

you:   i gave Ada a mirror as a gift.
       [TELL    subj=Ada    path=gift               row=[3, 53, 8, 20, 7]]
it:    done. Ada's gift is a mirror.
mouth: done. <SUBJ>'s gift is a <OBJ>.

you:   Do you remember who Hal's friend is?
       [ASK     subj=Hal    path=friend             lookup->53 in 1 step(s)]
it:    the answer is Ada.
mouth: the answer is <OBJ>.

you:   what is the prize of the friend of Hal?
       [ASK     subj=Hal    path=friend/prize       lookup->16 in 2 step(s)]
it:    that is a coin.
mouth: that is a <OBJ>.

you:   remind me what Hal's friend's prize is.
       [ASK     subj=Hal    path=friend/prize       lookup->16 in 2 step(s)]
it:    it is a coin. that is what you told me.
mouth: it is a <OBJ>. that is what you told me.

you:   i wonder what Hal's friend's gift is
       [ASK     subj=Hal    path=friend/gift        lookup->20 in 2 step(s)]
it:    i looked it up: Hal's friend's gift is a mirror.
mouth: i looked it up: <SUBJ>'s friend's gift is a <OBJ>.

you:   ok, do you remember Hal's friend?
       [ASK     subj=Hal    path=friend             lookup->53 in 1 step(s)]
it:    it is Ada. that is what you told me.
mouth: it is <OBJ>. that is what you told me.

you:   Oren's gift is a ribbon.
       [TELL    subj=Oren   path=gift               row=[3, 54, 8, 24, 7]]
it:    that is new to me. Oren's gift is a ribbon.
mouth: that is new to me. <SUBJ>'s gift is a <OBJ>.

you:   Dov has Oren for a friend, please.
       [TELL    subj=Dov    path=friend             row=[3, 55, 11, 54, 7]]
it:    got it. Dov's friend is Oren.
mouth: got it. <SUBJ>'s friend is <OBJ>.

you:   They gave Hal a ladder as a prize.
       [TELL    subj=Hal    path=prize              row=[3, 52, 9, 21, 7]]
it:    right. Hal's prize is a ladder.
mouth: right. <SUBJ>'s prize is a <OBJ>.

you:   i like the rain!
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not go outside, but that sounds nice.
mouth: i do not go outside, but that sounds nice.

```

## `L1/000012`  (6 people: Ivo=52, Hal=53, Tal=54, Mira=55, Gia=56, Cleo=57)

```
you:   Ivo got a drum for a charm.
       [TELL    subj=Ivo    path=charm              row=[3, 52, 10, 12, 7]]
it:    ok, Ivo then: the charm is a drum.
mouth: ok, <SUBJ> then: the charm is a <OBJ>.

you:   i love the summer.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    tell me more.
mouth: tell me more.

you:   a mirror is Hal's gift.
       [TELL    subj=Hal    path=gift               row=[3, 53, 8, 20, 7]]
it:    that is new to me. Hal's gift is a mirror.
mouth: that is new to me. <SUBJ>'s gift is a <OBJ>.

you:   listen, i played outside after lunch.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i hope you had a good time.
mouth: i hope you had a good time.

you:   I cleaned my room today.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am sorry to hear that.
mouth: i am sorry to hear that.

you:   ok, a coin was given to Tal as a gift.
       [TELL    subj=Tal    path=gift               row=[3, 54, 8, 16, 7]]
it:    a new line for Tal: the gift is a coin.
mouth: a new line for <SUBJ>: the gift is a <OBJ>.

you:   I love the summer.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i like it when you talk to me.
mouth: i like it when you talk to me.

you:   I like cats.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am here if you want to teach me something.
mouth: i am here if you want to teach me something.

you:   right, Hal's gift - what is it?
       [ASK     subj=Hal    path=gift               lookup->20 in 1 step(s)]
it:    Hal's gift is a mirror, if my notebook is right.
mouth: <SUBJ>'s gift is a <OBJ>, if my notebook is right.

you:   alright, Tal's prize - a candle.
       [TELL    subj=Tal    path=prize              row=[3, 54, 9, 19, 7]]
it:    got it. Tal's prize is a candle.
mouth: got it. <SUBJ>'s prize is a <OBJ>.

you:   Mira picked a lamp as a charm, please!
       [TELL    subj=Mira   path=charm              row=[3, 55, 10, 14, 7]]
it:    done. Mira's charm is a lamp.
mouth: done. <SUBJ>'s charm is a <OBJ>.

you:   anyway, speaking of Gia, the friend is Hal!
       [TELL    subj=Gia    path=friend             row=[3, 56, 11, 53, 7]]
it:    i understand. Gia's friend is Hal.
mouth: i understand. <SUBJ>'s friend is <OBJ>.

you:   oh, Mira was given a feather as a prize
       [TELL    subj=Mira   path=prize              row=[3, 55, 9, 25, 7]]
it:    ok! Mira's prize is a feather.
mouth: ok! <SUBJ>'s prize is a <OBJ>.

you:   i am happy today, ok?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    tell me more.
mouth: tell me more.

you:   i forget what Gia's friend's gift is...
       [ASK     subj=Gia    path=friend/gift        lookup->20 in 2 step(s)]
it:    my notebook says a mirror.
mouth: my notebook says a <OBJ>.

you:   can you look up Gia's friend's gift?
       [ASK     subj=Gia    path=friend/gift        lookup->20 in 2 step(s)]
it:    Gia's friend's gift is a mirror, from my notebook.
mouth: <SUBJ>'s friend's gift is a <OBJ>, from my notebook.

you:   what did Gia's friend pick as a gift?
       [ASK     subj=Gia    path=friend/gift        lookup->20 in 2 step(s)]
it:    a mirror, i think.
mouth: a <OBJ>, i think.

you:   do you know what Cleo's charm is?
       [ASK     subj=Cleo   path=charm              UNKNOWN no_such_person]
it:    i do not know that yet. can you tell me about Cleo?
mouth: i do not know that yet. can you tell me about <SUBJ>?

you:   please write down that Mira's gift is a ribbon.
       [TELL    subj=Mira   path=gift               row=[3, 55, 8, 24, 7]]
it:    ok. Mira's gift is a ribbon.
mouth: ok. <SUBJ>'s gift is a <OBJ>.

you:   what's Gia's friend's gift?
       [ASK     subj=Gia    path=friend/gift        lookup->20 in 2 step(s)]
it:    a mirror.
mouth: a <OBJ>.

```

## `L1/000013`  (4 people: Bram=52, Ada=53, Hal=54, Tal=55)

```
you:   for Bram, the charm is a mirror.
       [TELL    subj=Bram   path=charm              row=[3, 52, 10, 20, 7]]
it:    i will remember that. Bram's charm is a mirror.
mouth: i will remember that. <SUBJ>'s charm is a <OBJ>.

you:   Ada has a brush for a gift.
       [TELL    subj=Ada    path=gift               row=[3, 53, 8, 18, 7]]
it:    added. Ada's gift is a brush.
mouth: added. <SUBJ>'s gift is a <OBJ>.

you:   can you tell me its prize?
       [UNCLEAR subj=-      path=-                  notebook untouched]
it:    i need a name to know who you mean.
mouth: i need a name to know who you mean.

you:   a mirror was given to Hal as a charm.
       [TELL    subj=Hal    path=charm              row=[3, 54, 10, 20, 7]]
it:    i understand. Hal's charm is a mirror.
mouth: i understand. <SUBJ>'s charm is a <OBJ>.

you:   can you see me?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am here if you want to teach me something.
mouth: i am here if you want to teach me something.

you:   You should know that Hal's friend is Ada.
       [TELL    subj=Hal    path=friend             row=[3, 54, 11, 53, 7]]
it:    that is new to me. Hal's friend is Ada.
mouth: that is new to me. <SUBJ>'s friend is <OBJ>.

you:   anyway, hello!
       [CHAT    subj=-      path=-                  notebook untouched]
it:    good night. sleep well.
mouth: good night. sleep well.

you:   About Hal: who is the friend?
       [ASK     subj=Hal    path=friend             lookup->53 in 1 step(s)]
it:    i looked it up: Hal's friend is Ada.
mouth: i looked it up: <SUBJ>'s friend is <OBJ>.

you:   As for Tal, the prize is a feather.
       [TELL    subj=Tal    path=prize              row=[3, 55, 9, 25, 7]]
it:    a new line for Tal: the prize is a feather.
mouth: a new line for <SUBJ>: the prize is a <OBJ>.

you:   Bram's prize? it is a basket.
       [TELL    subj=Bram   path=prize              row=[3, 52, 9, 23, 7]]
it:    that is new to me. Bram's prize is a basket.
mouth: that is new to me. <SUBJ>'s prize is a <OBJ>.

you:   listen, do you know Hal's friend?
       [ASK     subj=Hal    path=friend             lookup->53 in 1 step(s)]
it:    Hal's friend is Ada, if my notebook is right.
mouth: <SUBJ>'s friend is <OBJ>, if my notebook is right.

you:   do you sleep at night?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    hello! how are you today?
mouth: hello! how are you today?

you:   by the way, the friend for Ada is Bram
       [TELL    subj=Ada    path=friend             row=[3, 53, 11, 52, 7]]
it:    a new line for Ada: the friend is Bram.
mouth: a new line for <SUBJ>: the friend is <OBJ>.

you:   Can you tell me his friend?
       [UNCLEAR subj=-      path=-                  notebook untouched]
it:    one thing at a time, please.
mouth: one thing at a time, please.

you:   Hi!
       [CHAT    subj=-      path=-                  notebook untouched]
it:    see you tomorrow.
mouth: see you tomorrow.

```

## `L1/000014`  (2 people: Mira=52, Dov=53)

```
you:   right, speaking of Mira, the charm is a whistle.
       [TELL    subj=Mira   path=charm              row=[3, 52, 10, 27, 7]]
it:    that is new to me. Mira's charm is a whistle.
mouth: that is new to me. <SUBJ>'s charm is a <OBJ>.

you:   a kite is the prize of Dov, please remember that.
       [TELL    subj=Dov    path=prize              row=[3, 53, 9, 13, 7]]
it:    i put it in my notebook: Dov's prize is a kite.
mouth: i put it in my notebook: <SUBJ>'s prize is a <OBJ>.

you:   by the way, note that Dov's friend is Mira.
       [TELL    subj=Dov    path=friend             row=[3, 53, 11, 52, 7]]
it:    right. Dov's friend is Mira.
mouth: right. <SUBJ>'s friend is <OBJ>.

you:   both Hal's prize and Ada's prize are a whistle.
       [UNCLEAR subj=-      path=-                  notebook untouched]
it:    i do not know what you are asking.
mouth: i do not know what you are asking.

you:   what is the charm belonging to Mira?
       [ASK     subj=Mira   path=charm              lookup->27 in 1 step(s)]
it:    it is a whistle now.
mouth: it is a <OBJ> now.

you:   about Dov's friend, what is the charm?
       [ASK     subj=Dov    path=friend/charm       lookup->27 in 2 step(s)]
it:    a whistle, i think.
mouth: a <OBJ>, i think.

you:   Right, do you know Dov's friend's charm?
       [ASK     subj=Dov    path=friend/charm       lookup->27 in 2 step(s)]
it:    you told me Dov's friend's charm is a whistle.
mouth: you told me <SUBJ>'s friend's charm is a <OBJ>.

you:   the friend belonging to Mira is Dov
       [TELL    subj=Mira   path=friend             row=[3, 52, 11, 53, 7]]
it:    added. Mira's friend is Dov.
mouth: added. <SUBJ>'s friend is <OBJ>.

```

## `L1/000015`  (3 people: Mira=52, Bram=53, Ada=54)

```
you:   well, one more: Mira's charm is a ladder, got it?
       [TELL    subj=Mira   path=charm              row=[3, 52, 10, 21, 7]]
it:    added. Mira's charm is a ladder.
mouth: added. <SUBJ>'s charm is a <OBJ>.

you:   Bram's charm: a basket.
       [TELL    subj=Bram   path=charm              row=[3, 53, 10, 23, 7]]
it:    thank you. Bram's charm is a basket.
mouth: thank you. <SUBJ>'s charm is a <OBJ>.

you:   right, Bram was given a ladder as a gift.
       [TELL    subj=Bram   path=gift               row=[3, 53, 8, 21, 7]]
it:    added. Bram's gift is a ladder.
mouth: added. <SUBJ>'s gift is a <OBJ>.

you:   Hey, do you know what Mira's charm is?
       [ASK     subj=Mira   path=charm              lookup->21 in 1 step(s)]
it:    Mira's charm is a ladder, from my notebook.
mouth: <SUBJ>'s charm is a <OBJ>, from my notebook.

you:   What does Mira have as a charm?
       [ASK     subj=Mira   path=charm              lookup->21 in 1 step(s)]
it:    it is a ladder. that is what you told me.
mouth: it is a <OBJ>. that is what you told me.

you:   i am happy today!
       [CHAT    subj=-      path=-                  notebook untouched]
it:    hello! how are you today?
mouth: hello! how are you today?

you:   oh, speaking of Mira, what is the charm?
       [ASK     subj=Mira   path=charm              lookup->21 in 1 step(s)]
it:    i wrote down a ladder. Mira's charm is a ladder.
mouth: i wrote down a <OBJ>. <SUBJ>'s charm is a <OBJ>.

you:   change it: Mira's charm is a flute.
       [CORRECT subj=Mira   path=charm              row=[3, 52, 10, 17, 7] REPLACES]
it:    ok! Mira's charm is a flute now.
mouth: ok! <SUBJ>'s charm is a <OBJ> now.

you:   Ada was given a ribbon as a charm, if you can
       [TELL    subj=Ada    path=charm              row=[3, 54, 10, 24, 7]]
it:    ok! Ada's charm is a ribbon.
mouth: ok! <SUBJ>'s charm is a <OBJ>.

```

## `L1/000016`  (3 people: Ivo=52, Dov=53, Juno=54)

```
you:   ok, a drum is Ivo's charm
       [TELL    subj=Ivo    path=charm              row=[3, 52, 10, 12, 7]]
it:    i have written it down: Ivo's charm is a drum.
mouth: i have written it down: <SUBJ>'s charm is a <OBJ>.

you:   Dov chose a flute as a prize.
       [TELL    subj=Dov    path=prize              row=[3, 53, 9, 17, 7]]
it:    ok. Dov's prize is a flute.
mouth: ok. <SUBJ>'s prize is a <OBJ>.

you:   hey, Juno's gift? it is a brush.
       [TELL    subj=Juno   path=gift               row=[3, 54, 8, 18, 7]]
it:    got it. Juno's gift is a brush.
mouth: got it. <SUBJ>'s gift is a <OBJ>.

you:   update: Dov's prize is a mirror.
       [CORRECT subj=Dov    path=prize              row=[3, 53, 9, 20, 7] REPLACES]
it:    thank you for the correction. Dov's prize is a mirror now.
mouth: thank you for the correction. <SUBJ>'s prize is a <OBJ> now.

you:   oh, can you tell me what Dov's prize is?
       [ASK     subj=Dov    path=prize              lookup->20 in 1 step(s)]
it:    the answer is a mirror.
mouth: the answer is a <OBJ>.

you:   i am a bit bored!
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not have a favourite, but i like hearing yours.
mouth: i do not have a favourite, but i like hearing yours.

you:   i cannot remember Juno's charm.
       [ASK     subj=Juno   path=charm              UNKNOWN no_such_fact]
it:    i looked and found nothing for Juno's charm.
mouth: i looked and found nothing for <SUBJ>'s charm.

you:   what is the prize that Dov got?
       [ASK     subj=Dov    path=prize              lookup->20 in 1 step(s)]
it:    i wrote down a mirror. Dov's prize is a mirror.
mouth: i wrote down a <OBJ>. <SUBJ>'s prize is a <OBJ>.

you:   i helped in the garden, ok?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    ok!
mouth: ok!

you:   by the way, Ivo has Dov for a friend
       [TELL    subj=Ivo    path=friend             row=[3, 52, 11, 53, 7]]
it:    i will remember that. Ivo's friend is Dov.
mouth: i will remember that. <SUBJ>'s friend is <OBJ>.

you:   alright, i like cats.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i do not know much about that, but i like hearing it.
mouth: i do not know much about that, but i like hearing it.

```

## `L1/000017`  (6 people: Cleo=52, Hal=53, Ada=54, Ivo=55, Lena=56, Nils=57)

```
you:   the prize that Cleo got is a mirror.
       [TELL    subj=Cleo   path=prize              row=[3, 52, 9, 20, 7]]
it:    a new line for Cleo: the prize is a mirror.
mouth: a new line for <SUBJ>: the prize is a <OBJ>.

you:   alright, Hal's friend: Ada.
       [TELL    subj=Hal    path=friend             row=[3, 53, 11, 54, 7]]
it:    done. Hal's friend is Ada.
mouth: done. <SUBJ>'s friend is <OBJ>.

you:   remind me what Cleo's prize is.
       [ASK     subj=Cleo   path=prize              lookup->20 in 1 step(s)]
it:    Cleo's prize is a mirror, from my notebook.
mouth: <SUBJ>'s prize is a <OBJ>, from my notebook.

you:   i am telling you that Ivo's prize is a coin.
       [TELL    subj=Ivo    path=prize              row=[3, 55, 9, 16, 7]]
it:    ok, Ivo then: the prize is a coin.
mouth: ok, <SUBJ> then: the prize is a <OBJ>.

you:   let me change that: Ivo's prize is a drum...
       [CORRECT subj=Ivo    path=prize              row=[3, 55, 9, 12, 7] REPLACES]
it:    ok, i changed it. Ivo's prize is a drum now, not a coin.
mouth: ok, i changed it. <SUBJ>'s prize is a <OBJ> now, not a <OLD>.

you:   by the way, one more: Lena's charm is a ribbon, please
       [TELL    subj=Lena   path=charm              row=[3, 56, 10, 24, 7]]
it:    ok. so Lena's charm is a ribbon.
mouth: ok. so <SUBJ>'s charm is a <OBJ>.

you:   Add this: Ivo's charm is a candle.
       [TELL    subj=Ivo    path=charm              row=[3, 55, 10, 19, 7]]
it:    i understand. Ivo's charm is a candle.
mouth: i understand. <SUBJ>'s charm is a <OBJ>.

you:   Cleo's friend happens to be Nils.
       [TELL    subj=Cleo   path=friend             row=[3, 52, 11, 57, 7]]
it:    ok! Cleo's friend is Nils.
mouth: ok! <SUBJ>'s friend is <OBJ>.

you:   what is the charm for Lena?
       [ASK     subj=Lena   path=charm              lookup->24 in 1 step(s)]
it:    it is a ribbon. that is what you told me.
mouth: it is a <OBJ>. that is what you told me.

you:   any idea who Hal's friend is?
       [ASK     subj=Hal    path=friend             lookup->54 in 1 step(s)]
it:    Ada is Hal's friend.
mouth: <OBJ> is <SUBJ>'s friend.

you:   by the way, Kai's friend is a ribbon and Hal's friend is a candle.
       [UNCLEAR subj=-      path=-                  notebook untouched]
it:    sorry, that one is too hard for me.
mouth: sorry, that one is too hard for me.

you:   I went to the park today.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that sounds like a long day.
mouth: that sounds like a long day.

you:   hey there.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    ok!
mouth: ok!

you:   a correction: Ivo's charm is a flute!
       [CORRECT subj=Ivo    path=charm              row=[3, 55, 10, 17, 7] REPLACES]
it:    thank you for the correction. Ivo's charm is a flute now.
mouth: thank you for the correction. <SUBJ>'s charm is a <OBJ> now.

you:   by the way, could you tell me Cleo's friend?
       [ASK     subj=Cleo   path=friend             lookup->57 in 1 step(s)]
it:    it is Nils.
mouth: it is <OBJ>.

you:   Add this: Hal's charm is a flute.
       [TELL    subj=Hal    path=charm              row=[3, 53, 10, 17, 7]]
it:    i have written it down: Hal's charm is a flute.
mouth: i have written it down: <SUBJ>'s charm is a <OBJ>.

you:   Well, how many people live in the world?
       [ASK     subj=-      path=-                  notebook untouched]
it:    i do not know that yet.
mouth: i do not know that yet.

you:   what's Ivo's prize?
       [ASK     subj=Ivo    path=prize              lookup->12 in 1 step(s)]
it:    Ivo's prize is a drum.
mouth: <SUBJ>'s prize is a <OBJ>.

you:   oh, do you know who Cleo's friend's friend is?
       [ASK     subj=Cleo   path=friend/friend      UNKNOWN chain_broke]
it:    i cannot follow the whole chain for Cleo.
mouth: i cannot follow the whole chain for <SUBJ>.

```

## `L1/000018`  (4 people: Ada=52, Mira=53, Bram=54, Oren=55)

```
you:   remember that Ada's friend is Mira
       [TELL    subj=Ada    path=friend             row=[3, 52, 11, 53, 7]]
it:    ok. so Ada's friend is Mira.
mouth: ok. so <SUBJ>'s friend is <OBJ>.

you:   that is sad.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    good night. sleep well.
mouth: good night. sleep well.

you:   oh, Bram was given a drum as a prize.
       [TELL    subj=Bram   path=prize              row=[3, 54, 9, 12, 7]]
it:    that is new to me. Bram's prize is a drum.
mouth: that is new to me. <SUBJ>'s prize is a <OBJ>.

you:   i walked to school this morning, please.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    that is kind of you.
mouth: that is kind of you.

you:   do you sleep at night?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    talk to you later.
mouth: talk to you later.

you:   do you like the rain?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    you can tell me a fact if you like.
mouth: you can tell me a fact if you like.

you:   I wonder what Oren's gift is.
       [ASK     subj=Oren   path=gift               UNKNOWN no_such_person]
it:    sorry, i do not know Oren's gift.
mouth: sorry, i do not know <SUBJ>'s gift.

```

## `L1/000019`  (4 people: Finn=52, Gia=53, Cleo=54, Esme=55)

```
you:   anyway, Finn chose a ladder as a gift...
       [TELL    subj=Finn   path=gift               row=[3, 52, 8, 21, 7]]
it:    noted. Finn's gift is a ladder.
mouth: noted. <SUBJ>'s gift is a <OBJ>.

you:   ok, i like cats
       [CHAT    subj=-      path=-                  notebook untouched]
it:    ok!
mouth: ok!

you:   I am a bit bored.
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i am here if you want to teach me something.
mouth: i am here if you want to teach me something.

you:   right, Gia received a drum as a gift.
       [TELL    subj=Gia    path=gift               row=[3, 53, 8, 12, 7]]
it:    ok. Gia's gift is a drum.
mouth: ok. <SUBJ>'s gift is a <OBJ>.

you:   do you sleep at night?
       [CHAT    subj=-      path=-                  notebook untouched]
it:    i like that.
mouth: i like that.

you:   Finn's charm - a feather.
       [TELL    subj=Finn   path=charm              row=[3, 52, 10, 25, 7]]
it:    ok. so Finn's charm is a feather.
mouth: ok. so <SUBJ>'s charm is a <OBJ>.

you:   Do you remember what Gia's gift is?
       [ASK     subj=Gia    path=gift               lookup->12 in 1 step(s)]
it:    Gia's gift is a drum.
mouth: <SUBJ>'s gift is a <OBJ>.

you:   right, speaking of Gia, the friend is Cleo, ok?
       [TELL    subj=Gia    path=friend             row=[3, 53, 11, 54, 7]]
it:    a new line for Gia: the friend is Cleo.
mouth: a new line for <SUBJ>: the friend is <OBJ>.

you:   A ladder became Esme's gift.
       [TELL    subj=Esme   path=gift               row=[3, 55, 8, 21, 7]]
it:    in my notebook now: Esme's gift is a ladder.
mouth: in my notebook now: <SUBJ>'s gift is a <OBJ>.

you:   Who does Gia keep as a friend?
       [ASK     subj=Gia    path=friend             lookup->54 in 1 step(s)]
it:    i have Cleo for Gia's friend.
mouth: i have <OBJ> for <SUBJ>'s friend.

you:   ok, what are Gia's gift and Finn's friend?
       [UNCLEAR subj=-      path=-                  notebook untouched]
it:    i did not get that. can you try again?
mouth: i did not get that. can you try again?

```
