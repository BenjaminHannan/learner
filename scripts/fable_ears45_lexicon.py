#!/usr/bin/env python3
"""Rung 1 of design 43 (`design/v3/30-modes/43-talker-ears-mouth-design-fable.md`) --
the hand-written common-word list that stands in for the TinyStories + Simple English
Wikipedia frequency lexicon.

DEVIATION FROM THE DESIGN, stated here and in PASSMARKS.md
----------------------------------------------------------
B.1 builds the lexicon as "the 3,000 most frequent lower-case word forms in TinyStories +
Simple English Wikipedia, after deleting any form that is capitalised in >= 50 % of its
mid-sentence occurrences".  Neither corpus is present on this machine and downloading is
forbidden for this task, so the lexicon is built instead from

  (a) the list below: ordinary English words written out by hand, from my own knowledge of
      which English word forms are common.  It contains NO personal names and NO place
      names.  Words that are BOTH common nouns/verbs and common names (rose, will, may,
      mark, hope, art, bill, grace, sky, daisy, ...) are deliberately kept, because B.1
      keeps them and G.3 measures the collision they cause;
  (b) every non-placeholder word form of the TRAIN frames (`fable_ears45_data.py`);
  (c) every word form of the relation-wording table (`RELATION_MAP` of
      `fable_listening_english.py`) and of the correction-cue table.

RULE FOR TEST-ONLY MATERIAL.  A test-only relation wording or a test-only sentence opener
is in the lexicon if and only if its words are in list (a) -- i.e. only if a real frequency
lexicon would plausibly have contained them.  List (a) was written before the frame table
was split, and is not adjusted per split.  Words I judge too rare for a 3,000-word
frequency list are deliberately absent, so they reach the network as opaque labels exactly
as an unknown word would: `resides`, `dwells`, `hails`, `moniker`, `surname`, `employed`,
`occupation`, `abode`, `domicile`, `sibling`(kept -- common enough), ... the absent set is
printed by `fable_ears45_data.py --lexicon-report`.

Nothing in this file is learned and nothing here is edited by any other file.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------------------
# (a) hand-written common English word list.  No names, no places.
# Grouped only for my own legibility; the grouping carries no meaning downstream.
# ---------------------------------------------------------------------------------------

_RAW = """
a an the this that these those there here it its it's they them their theirs
i me my mine myself we us our ours you your yours yourself he him his she her hers
who whom whose which what when where why how whether if then than so because since while
and or but nor yet for of to in on at by with without from into onto over under above below
between among through during before after about around across against along behind beside
beyond down up off out near next past per plus via within throughout inside outside upon
am is are was were be been being have has had having do does did doing done
will would shall should can could may might must ought need dare used
get gets got gotten getting go goes went gone going come comes came coming
make makes made making take takes took taken taking give gives gave given giving
say says said saying tell tells told telling ask asks asked asking answer answers answered
know knows knew known knowing think thinks thought thinking mean means meant meaning
see sees saw seen seeing look looks looked looking watch watches watched watching
hear hears heard hearing listen listens listened listening speak speaks spoke spoken
talk talks talked talking call calls called calling name names named naming
write writes wrote written writing read reads reading note notes noted noting
remember remembers remembered remembering forget forgets forgot forgotten forgetting
learn learns learned learnt learning teach teaches taught teaching study studies studied
work works worked working live lives lived living stay stays stayed staying
move moves moved moving leave leaves left leaving arrive arrives arrived arriving
start starts started starting begin begins began begun beginning stop stops stopped
end ends ended ending finish finishes finished finishing keep keeps kept keeping
hold holds held holding put puts putting set sets setting place places placed placing
bring brings brought bringing carry carries carried carrying send sends sent sending
show shows showed shown showing find finds found finding lose loses lost losing
want wants wanted wanting like likes liked liking love loves loved loving
hate hates hated hating hope hopes hoped hoping wish wishes wished wishing
try tries tried trying help helps helped helping let lets letting allow allows allowed
use uses used using change changes changed changing fix fixes fixed fixing
turn turns turned turning open opens opened opening close closes closed closing
play plays played playing run runs ran running walk walks walked walking
sit sits sat sitting stand stands stood standing sleep sleeps slept sleeping
eat eats ate eaten eating drink drinks drank drunk drinking cook cooks cooked cooking
buy buys bought buying sell sells sold selling pay pays paid paying cost costs
build builds built building break breaks broke broken breaking cut cuts cutting
grow grows grew grown growing draw draws drew drawn drawing paint paints painted
sing sings sang sung singing dance dances danced dancing swim swims swam swimming
drive drives drove driven driving ride rides rode ridden riding fly flies flew flown
wait waits waited waiting meet meets met meeting visit visits visited visiting
follow follows followed following lead leads led leading join joins joined joining
add adds added adding remove removes removed removing count counts counted counting
check checks checked checking mark marks marked marking list lists listed listing
mind minds minded matter matters mattered care cares cared caring
seem seems seemed happen happens happened happening become becomes became
belong belongs belonged belonging own owns owned owning
man woman men women boy girl child children baby kid kids people person persons
family families mother mothers mom moms mum mums father fathers dad dads
parent parents son sons daughter daughters brother brothers sister sisters
sibling siblings cousin cousins aunt uncle grandmother grandfather grandma grandpa
wife husband partner partners friend friends neighbour neighbours neighbor neighbors
teacher teachers student students boss bosses worker workers doctor doctors nurse
coach coaches landlord landlords mentor mentors roommate roommates classmate
driver drivers writer writers singer singers painter painters builder builders
player players reader readers leader leaders maker makers owner owners
creator creators employer employers guest guests host hosts
home homes house houses flat flats room rooms kitchen garden gardens yard
school schools class classes college university office offices shop shops store stores
market markets library libraries museum park parks street streets road roads
city cities town towns village villages country countries state states place places
world worlds land lands sea seas river rivers lake lakes hill hills mountain mountains
beach island bridge station stations airport hospital church farm farms
job jobs company companies team teams band bands club clubs group groups
book books story stories film films movie movies song songs play plays
game games sport sports colour colours color colors number numbers word words
letter letters line lines page pages list lists note notes name names
food foods meal meals dish dishes bread rice soup cake fruit apple apples
drink drinks water tea coffee milk juice
animal animals pet pets dog dogs cat cats bird birds fish horse horses
car cars bike bikes bus buses train trains plane planes boat boats
phone phones computer computers screen radio camera clock watch key keys
door doors window windows wall walls floor roof table tables chair chairs bed beds
bag bags box boxes cup cups plate plates knife fork spoon
coat hat shoe shoes shirt dress
tree trees flower flowers grass leaf leaves stone stones sand
sun moon star stars sky rain snow wind cloud clouds storm
day days night nights morning afternoon evening week weeks month months year years
hour hours minute minutes second seconds moment moments time times today tomorrow
yesterday now soon later early late always never often sometimes usually again
age ages birthday birth origin hometown home
red blue green yellow black white brown grey gray pink purple orange teal
gold silver dark light bright pale
big small large little long short tall high low wide narrow thick thin
old new young fresh clean dirty warm cool cold hot dry wet
good bad best better worse worst nice fine great fun funny sad happy angry
kind mean quiet loud busy free easy hard simple hardest
right wrong true false real same different other another each every all both
some any no none one two three four five six seven eight nine ten
first second third last next previous only just even still also too very much many
more most less least enough quite rather almost nearly about exactly
please thanks thank sorry hello hi hey bye goodnight goodbye welcome ok okay
yes yep yeah no nope not never nothing something anything everything
someone anyone everyone somebody anybody everybody nobody
well actually really maybe perhaps probably surely certainly clearly
anyway besides however though although unless until whenever wherever
btw fyi lol nickname nicknames known called quick aside rumour rumor plus
update correction fact facts detail details thing things stuff
question questions answer answers idea ideas reason reasons
favourite favorite best worst top main whole half part parts piece pieces
lot lots few little several many kind sort type types
head hand hands foot feet eye eyes face hair heart
side sides top bottom front back middle centre center corner end
way ways road path step steps plan plans
sound sounds music noise voice voices
money price prices cost costs pound dollar euro
weekend holiday holidays trip trips summer winter spring autumn fall
hobby hobbies instrument instruments guitar piano drums violin
chess football tennis running swimming cycling reading cooking painting drawing
science history maths math art english language languages subject subjects
lunch dinner breakfast supper outside inside cleaned
smart clever tired hungry thirsty ready sure unsure
speaking regarding concerning
whatever whoever whichever
oh ah um hmm er well
done alright
""".strip()

# Words a 3,000-form frequency lexicon over TinyStories + Simple English Wikipedia would
# very likely NOT contain, listed so the report can show them: they are deliberately left
# out of (a) and therefore reach the network as opaque labels.
DELIBERATELY_OMITTED = (
    "resides reside residing dwells dwell hails hail moniker surname employed "
    "occupation abode domicile alias appellation designation nickname's"
).split()

COMMON_WORDS = tuple(
    sorted({w for w in _RAW.split() if w and not w.startswith("#")})
)

PUNCT_TOKENS = tuple(".,;:!?()\"—–")

CLITIC_TOKENS = (
    "'s", "’s", "n't", "n’t", "'m", "’m", "'re", "’re",
    "'ve", "’ve", "'ll", "’ll", "'d", "’d",
)


if __name__ == "__main__":
    print(f"hand-written common words: {len(COMMON_WORDS)}")
    print(f"deliberately omitted     : {len(DELIBERATELY_OMITTED)}")
