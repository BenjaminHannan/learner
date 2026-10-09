# How the brain does the talking part

Written Oct 4, 2026, about 4:10 PM ET, for Ben's question in the thread "How does the brain do the talking part?"
Science claims are tagged **well established**, **good evidence** or **debated**. Design ideas at the end are
**suggested, not shown**: nothing here was tested on our model.

## Short answer

Speaking runs in stages, from meaning to mouth, and the system that thinks is mostly separate from the system
that finds words.

1. **Meaning (the "message").** You decide what you want to say, with no words yet.
2. **Words (the "lemma").** You pick words that fit the meaning, and their grammar and order.
3. **Sounds (the "word form").** You fetch each word's sounds and split them into syllables.
4. **Mouth (articulation).** Motor cortex sends timed commands to lips, tongue, jaw and voice box.
5. **Self-check.** You listen to your own speech, even inner speech, and fix slips.

This staged picture comes from Levelt's model (Levelt 1989; Levelt, Roelofs & Meyer 1999). It is the standard
textbook account. **Well established** as a description; the details are argued over (see "Uncertain").

## Timing (single words in the lab)

Indefrey & Levelt (2004) combined many brain-imaging and timing studies of picture naming. With an average
naming time of about 600 ms from seeing the picture to starting to speak:

| Stage | Roughly when (ms after picture) |
|---|---|
| Understand the picture, form the concept | 0 to 175 |
| Pick the word (lemma) | 175 to 250 |
| Fetch its sounds | 250 to 330 |
| Build syllables, plan the movements | 330 to 600 |
| Start speaking | about 600 |

Indefrey (2011) re-checked this with newer data and found it mostly held. **Good evidence**, but only for
naming one word. Real conversation is different: gaps between turns are about 200 ms in many languages
(Stivers et al. 2009), far shorter than 600 ms, so people must plan their reply while the other person is still
talking (Levinson & Torreira 2015). Castellucci et al. (2022) found a planning circuit around Broca's region that
is most active just before a person's turn.

## Where it happens

- **Words and grammar: the left "language network"** (parts of the left frontal and temporal lobes). Hu et al.
  (2023) showed the same regions that respond when you understand language also do word-finding and
  phrase-building when you speak, and they work harder when speaking. Silbert et al. (2014) found speaking and
  listening to the same story use heavily overlapping, coupled networks. **Good evidence** that understanding
  and talking share one word system.
- **Sound planning: left prefrontal neurons.** Khanna et al. (2024) recorded single neurons in people during
  natural speech. Neurons in language-dominant prefrontal cortex coded the sounds, syllables and word parts of
  the next word before it was said, in the order they would be said. **Good evidence** (few patients).
- **Broca's area as a relay.** Flinker et al. (2015) recorded the brain surface during word repetition. Activity
  went auditory cortex, then Broca's area, then motor cortex. Broca's area was busy before speaking and went
  quiet while the word was actually said, so it seems to coordinate the plan, not move the mouth. **Good
  evidence, role still debated.**
- **Mouth control: ventral motor cortex.** Bouchard et al. (2013) showed a map for lips, jaw, tongue and larynx
  on the motor strip, with activity patterns that shift every few tens of milliseconds between sounds. **Well
  established.**
- **Language to sound, in time order.** Goldstein et al. (2025) recorded 100 hours of real conversation and
  matched brain activity to a speech-to-text AI model (Whisper). Before each spoken word, higher language areas
  matched the model's word-level layers first, then motor and sensory areas matched its sound-level layers.
  When listening, the order reversed. **Good evidence.**

## How we know it works: speech implants

Most speech implants read the mouth-control step, not the thought. Card et al. (2024) put electrode arrays on
the speech motor cortex of a man with ALS. The system reached 97.5% word accuracy over 8.4 months, at about 32
words per minute in his own conversations. Willett et al. (2023) and Metzger et al. (2023) did similar work.
Tang et al. (2023) decoded the gist of sentences from fMRI of meaning areas, but not reliably the exact words.
So we can read the "mouth" end well and the "meaning" end only roughly.

## Self-checking and feedback

- **Perceptual loop.** Levelt (1983): you check your own inner and spoken words with your comprehension
  system, compare them to what you meant, and repair errors ("left, I mean right"). **Good evidence, details
  debated.**
- **Feedback control of the mouth.** The DIVA model (Tourville & Guenther 2011) and state-feedback models
  (Houde & Nagarajan 2011; Hickok 2012) say the brain predicts what its speech should sound and feel like and
  corrects when the real feedback differs. **Good evidence** at the sound level.

## Thinking is mostly separate from talking

Fedorenko, Piantadosi & Gibson (2024, Nature) review evidence that the language network is not needed for
most thinking. People who lose almost all language after a stroke can still do arithmetic, logic and planning
(for example Varley et al. 2005, "Agrammatic but numerate"), and the language network stays quiet during
math, logic and music. They argue language is mainly a tool for communicating thoughts. **Good evidence, but
debated**: inner speech seems to help some kinds of hard reasoning, and critics say "mostly separate" is not
"no role".

A related finding: Ferreira & Swets (2002) asked people to say the sum of two numbers. Without time pressure,
they worked out the whole sum before starting to talk (harder sums delayed the start, not the speech itself).
Under a deadline they started talking earlier and thought while speaking. So "think first, then speak" is the
default, and speaking while still thinking is a strategy people switch to. **Good evidence** (one task type).

## What is uncertain

- **What a thought looks like.** Nobody knows the format of the "message" level. The decoders above read the
  mouth end or a rough gist.
- **Strict steps or overlap.** Levelt's model runs the stages in order; Dell's (1986) model lets them overlap
  and feed back (sound neighbours influence word choice). Speech-error data favour some overlap. **Debated.**
- **The old map is too simple.** "Broca's area = speaking, Wernicke's area = understanding" is outdated; only
  2% of surveyed experts called that classic model the best theory (Tremblay & Dick 2016).
- **Lab vs life.** Most timing data are single words in the lab; real conversation has far more overlap of
  listening and planning.
- **Language and hard reasoning.** How much language helps difficult reasoning is still argued.

## What this suggests for our talker (suggested, not shown)

These are analogies. The brain is not a blueprint, and none of this was tested on our model.

1. **Ben's design matches the brain's default.** Think to a finished answer, then translate it to words. That
   is the Ferreira & Swets default, and it fits the thinking-vs-language split. The copy-and-gate test's
   no-core arm (`copytalk-nocore`, see `reader-talker-compare/verdict.md`) is the right check that our "thought"
   (the core's final state) actually holds the answer, the way the message level does in people.
2. **The brain's talker is not small.** Its word-picking step is the same large network used for
   understanding. A ~2M talker can work for us only because our answers are short and the hard part (choosing
   the word) has to already be in the core's state; spelling the word out is easy for us (tokens), unlike real
   sound planning. Suggestion: the talker should **share the reader's word table** instead of learning its own.
   The planned copy talker already ties its word head to the frozen LM embeddings; if the LM is dropped later,
   keep one shared embedding table for reading and talking.
3. **Copying is normal.** In dialogue, people reuse the words and phrasing they just heard (Pickering & Garrod
   2004, "interactive alignment"). A pointer that copies words from the question is human-like, not a cheat.
   The gate between "copy a word" and "say a word from my vocabulary" mirrors this.
4. **Later, one change at a time: a self-check loop.** People check their speech through their own
   understanding system (Levelt 1983). A later experiment could run the talker's answer back through the reader
   and core and compare the result with the original final state, either as an extra training signal or to
   reject bad answers. Only worth trying after the copy talker passes.
5. **Longer answers may need step-by-step access to the core.** For multi-word answers, people plan in chunks
   and keep consulting the plan while speaking. A talker that emits several words may need to look at the core's
   state at each step rather than once.

## Sources

- Levelt, W. J. M. (1989). *Speaking: From Intention to Articulation*. MIT Press.
- Levelt, Roelofs & Meyer (1999). A theory of lexical access in speech production. *Behavioral and Brain
  Sciences* 22, 1-38. https://www.mpi.nl/node/40638
- Levelt (1983). Monitoring and self-repair in speech. *Cognition* 14, 41-104. https://forms.mpi.nl/node/46259
- Indefrey & Levelt (2004). The spatial and temporal signatures of word production components. *Cognition* 92,
  101-144.
- Indefrey (2011). The spatial and temporal signatures of word production components: a critical update.
  *Frontiers in Psychology* 2, 255. https://pubmed.ncbi.nlm.nih.gov/22016740/
- Dell (1986). A spreading-activation theory of retrieval in sentence production. *Psychological Review* 93,
  283-321.
- Hu, Small, Kean, ... Fedorenko (2023). Precision fMRI reveals that the language-selective network supports
  both phrase-structure building and lexical access during language production. *Cerebral Cortex* 33,
  4384-4404. https://dspace.mit.edu/handle/1721.1/148770
- Silbert, Honey, Simony, Poeppel & Hasson (2014). Coupled neural systems underlie the production and
  comprehension of naturalistic narrative speech. *PNAS*. https://pmc.ncbi.nlm.nih.gov/articles/PMC4217461
- Khanna et al. (2024). Single-neuronal elements of speech production in humans. *Nature* 626, 603-610.
  https://read.qxmd.com/read/38297120/single-neuronal-elements-of-speech-production-in-humans
- Flinker et al. (2015). Redefining the role of Broca's area in speech. *PNAS*.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4352780/
- Bouchard, Mesgarani, Johnson & Chang (2013). Functional organization of human sensorimotor cortex for speech
  articulation. *Nature* 495, 327-332. https://pubmed.ncbi.nlm.nih.gov/23426266/
- Goldstein et al. (2025). A unified acoustic-to-speech-to-language embedding space captures the neural basis
  of natural language processing in everyday conversations. *Nature Human Behaviour*.
  https://research.google/pubs/a-unified-acoustic-to-speech-to-language-embedding-space-captures-the-neural-basis-of-natural-language-processing-in-everyday-conversations/
- Card et al. (2024). An accurate and rapidly calibrating speech neuroprosthesis. *New England Journal of
  Medicine*. https://pubmed.ncbi.nlm.nih.gov/39141853/
- Willett et al. (2023). A high-performance speech neuroprosthesis. *Nature*.
- Metzger et al. (2023). A high-performance neuroprosthesis for speech decoding and avatar control. *Nature*.
- Tang, LeBel, Jain & Huth (2023). Semantic reconstruction of continuous language from non-invasive brain
  recordings. *Nature Neuroscience*. https://pmc.ncbi.nlm.nih.gov/articles/PMC11304553
- Tourville & Guenther (2011). The DIVA model: a neural theory of speech acquisition and production. *Language
  and Cognitive Processes* 26, 952-981.
- Houde & Nagarajan (2011). Speech production as state feedback control. *Frontiers in Human Neuroscience* 5, 82.
- Hickok (2012). Computational neuroanatomy of speech production. *Nature Reviews Neuroscience* 13, 135-145.
- Fedorenko, Piantadosi & Gibson (2024). Language is primarily a tool for communication rather than thought.
  *Nature* 630. https://news.mit.edu/2024/what-is-language-for-0703
- Varley, Klessinger, Romanowski & Siegal (2005). Agrammatic but numerate. *PNAS* 102, 3519-3524.
- Ferreira & Swets (2002). How incremental is language production? *Journal of Memory and Language* 46, 57-84.
  https://www.gvsu.edu/cms4/asset/92386C7F-BF75-96ED-67D9FAA81701D122/ferreiraswets2002.pdf
- Stivers et al. (2009). Universals and cultural variation in turn-taking in conversation. *PNAS* 106,
  10587-10592. https://forms.mpi.nl/node/50939
- Levinson & Torreira (2015). Timing in turn-taking and its implications for processing models of language.
  *Frontiers in Psychology* 6, 731. https://pmc.ncbi.nlm.nih.gov/articles/PMC4464110
- Castellucci et al. (2022). A speech planning network for interactive language use. *Nature* 602, 117-122.
  https://longlab.med.nyu.edu/wp-content/uploads/2022/03/Castellucci.pdf
- Pickering & Garrod (2004). Toward a mechanistic psychology of dialogue. *Behavioral and Brain Sciences* 27,
  169-225. https://www.psy.gla.ac.uk/~simon/CD8063.Pickering_1-58.pdf
- Tremblay & Dick (2016). Broca and Wernicke are dead, or moving past the classic model of language
  neurobiology. *Brain and Language* 162, 60-71.
  https://myweb.fiu.edu/wp-content/uploads/sites/252/2015/12/tremblaydick_2016proof.pdf

Checked against search results and abstracts on Oct 4, 2026. Page numbers without a link were not re-checked.
