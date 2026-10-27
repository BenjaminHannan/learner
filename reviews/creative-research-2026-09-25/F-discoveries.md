# F. How past discoveries were made, and what the model could copy (2026-09-25)

Scope: 22 discoveries plus a myths box (Part 1), research on how discovery works (Part 2), and mechanisms mapped to
parts of the model (Part 3). Every quote below was fetched today (Wikipedia via its API, PubMed or Crossref abstracts,
PDFs, archive.org, nobelprize.org). Labels: **SHOWN** = a source shows it; **SUGGESTED** = a source argues it or it fits
the pattern but was not tested; **UNTESTED** = my proposal; **DISPUTED** = historians or researchers disagree.
Small card experiments and the village model are not discussed here: everything in Part 3 is for the number puzzles
(nums -> target, + - * /, exact checker) and later coding.

Tag codes: AN anomaly-noticing · CON strict constraint/principle · REF reframing/representation change ·
ANA analogy/cross-domain · REC recombining existing pieces · BRU systematic brute-force search ·
SER serendipity + prepared mind · INC incubation/sleep · STEP stepping stone from someone else's work ·
CHK exact test/check · PER long persistence through failure · TOOL an instrument made it possible ·
COM community/collaboration.

## Part 1. Case studies

**1. Kepler: Mars moves on an ellipse (astronomy, c.1600-1609).** Kepler fitted Tycho Brahe's naked-eye data with
circles. His best circle model missed by 8 arcminutes. He refused to ignore the gap, tried an oval, set the ellipse
aside once because of a calculation error, and came back to it.
- Tags: AN CON REF BRU CHK PER STEP
- Time/fails: years; a circle model, an oval, a wrongly rejected ellipse; "at least seventy repetitions" of one calculation. Check: the orbit matched Tycho's positions.
- Source: https://en.wikipedia.org/wiki/Astronomia_nova — "these eight minutes alone will lead us along a path to the reform of the whole of Astronomy"; "take pity on me, who had to go through with at least seventy repetitions of it".

**2. Newton: one gravity for the apple and the Moon (physics, c.1666-1687).** Newton guessed that the force pulling
an apple down also holds the Moon in orbit. He tested the guess with numbers, building on Kepler's laws.
- Tags: STEP ANA CHK
- Time/fails: about 20 years from the idea to the *Principia*; his first Moon check was only rough. Check: the Moon's orbit worked out from Earth's surface gravity, which came within 16% on the values of the time.
- Source: https://en.wikipedia.org/wiki/Newton%27s_law_of_universal_gravitation — "His calculations of the Moon orbit time was within 16% of the known value."
- Myth status: Newton told the falling-apple story himself (Stukeley's account of 1726). The apple hitting his head is **apocryphal**: https://en.wikipedia.org/wiki/Isaac_Newton%27s_apple_tree — "not the apocryphal version that the apple actually hit Newton's head."

**3. Maxwell: the displacement current, and light is electromagnetic (physics, 1861-1865).** Maxwell added a new term
to Ampère's law while working from a mechanical picture of "molecular vortices". The term predicted waves. Their speed
equalled the measured speed of light.
- Tags: ANA STEP CON CHK
- Time/fails: 1861 to 1865; the vortex model was later dropped, but the equation stayed. Check: a predicted wave speed matched two measured numbers.
- Source: https://en.wikipedia.org/wiki/Displacement_current — "Maxwell compared the speed of electricity measured by Wilhelm Eduard Weber and Rudolf Kohlrausch (193,088 miles/second) and the speed of light determined by the Fizeau experiment (195,647 miles/second)."
- (That consistency with charge conservation also drove the term is the usual textbook account. I did not fetch a quote for it: SUGGESTED.)

**4. Le Verrier: Neptune found by calculation (astronomy, 1845-1846) and Vulcan, the planet that never was (1859-1915).**
Uranus drifted from Newton's predictions. Le Verrier kept Newton's law, assumed an unseen planet, and computed where it
should be. Galle found it the same night. Le Verrier then used the same recipe on Mercury's extra perihelion drift and
announced a planet, "Vulcan". Decades of searches failed. General relativity explained Mercury in 1915 (case 5).
- Tags: AN CON CHK STEP COM (Neptune); AN ANA (the Neptune recipe copied, wrongly, for Vulcan)
- Time/fails: Neptune took about a year. Vulcan took about 56 years of false sightings. Check: the telescope, less than 1 degree off. For Vulcan the check was negative.
- Source: https://en.wikipedia.org/wiki/Discovery_of_Neptune — "Neptune was discovered just after midnight, after less than an hour of searching and less than 1 degree from the position Le Verrier had predicted".
- Source: https://en.wikipedia.org/wiki/Vulcan_(hypothetical_planet) — "Many searches were conducted for Vulcan over the following decades but, despite several claimed observations, its existence could not be confirmed."
- Lesson (SUGGESTED): the same anomaly-plus-constraint move gave one hit and one miss. When a fix keeps failing, the rules themselves may be wrong.

**5. Einstein: general relativity (physics, 1907-1915).** It began with the "happiest thought" of 1907: a falling
person feels no weight. Grossmann introduced Einstein to Riemannian geometry. Einstein dropped the right approach in 1913,
worked on a wrong one through 1914-15, and returned to the right one in late 1915. The theory then explained Mercury's
unexplained drift.
- Tags: CON REF STEP COM PER CHK AN
- Time/fails: 8 years, with one approach dropped wrongly and then picked up again. Check: Mercury's 43″ per century, then the 1919 eclipse.
- Source: https://en.wikipedia.org/wiki/History_of_general_relativity — "The first piece of evidence in support of general relativity came from its correct prediction of the anomalous rate of precession of Mercury's orbit."; "However, in 1913 Einstein abandoned that approach"

**6. Mendeleev: the periodic table (chemistry, 1869-1886).** Mendeleev arranged the elements by weight and by
properties. He trusted the pattern enough to leave gaps and to correct accepted atomic weights. He predicted three
unknown elements in detail.
- Tags: REF CON STEP CHK
- Time/fails: Newlands' earlier "octaves" left no gaps and were ignored. Check: gallium in 1875, scandium in 1879, germanium in 1886, all matching the predictions. He even corrected gallium's measured density.
- Source: https://en.wikipedia.org/wiki/History_of_the_periodic_table — "Mendeleev's eka-aluminium was discovered in 1875 and became known as gallium; eka-boron and eka-silicium were discovered in 1879 and 1886".
- Myth status: the "chemical solitaire" cards are hedged even there ("It is sometimes said"). The dream is Mendeleev's own later claim ("I saw in a dream a table..."): **DISPUTED/unverified**.

**7. Darwin and Wallace: natural selection (biology, 1838-1859).** Both men carried an idea from Malthus's writing on
human population (economics) over to animals. Darwin got there in 1838 and then spent 20 years gathering evidence.
Wallace reached it on his own in 1858, reportedly during a fever.
- Tags: ANA STEP PER COM
- Time/fails: Darwin took 21 years to publish. Check: no single exact check. The support is a large body of evidence gathered over time, which puzzles cannot reproduce.
- Source: https://en.wikipedia.org/wiki/Inception_of_Darwin%27s_theory — "in late September he began reading "for amusement" the 6th edition of Malthus's An Essay on the Principle of Population".
- Source: https://en.wikipedia.org/wiki/Alfred_Russel_Wallace — "it was while he was in bed with a fever that he thought about Malthus's idea of positive checks".

**8. Kekulé: the benzene ring (chemistry, 1865).** He proposed a ring of six carbons. Couper and Loschmidt had drawn
possible structures before him. In an 1890 speech, 25 years later, he said a daydream of a snake biting its tail gave
him the idea.
- Tags: REF STEP (INC claimed, **DISPUTED**)
- Check: fit with chemical evidence on aromatic compounds. The usual account cites isomer counts; I did not fetch it.
- Source: https://en.wikipedia.org/wiki/August_Kekul%C3%A9 — "Others have speculated that Kekulé's story in 1890 was a re-parody of the monkey spoof, and was a mere invention rather than a recollection of an event in his life."

**9. Poincaré: Fuchsian functions (maths, 1880).** He spent two weeks trying to prove that such functions could NOT
exist, with daily sessions "trying a great number of combinations". A sleepless night gave the first class of them.
Weeks later, with his mind on other things, he realised as he stepped onto a bus that his transformations were those of
non-Euclidean geometry. He checked the result later at home.
- Tags: PER BRU INC ANA REF CHK
- Time/fails: a fortnight with "no result", then several insights spread over weeks. Check: a written proof ("verified the result at my leisure").
- Source (primary, *Science and Method*, 1908 English transl.; archive.org id b21974123): "For a fortnight I had been attempting to prove that there could not be any function analogous to what I have since called Fuchsian functions... Every day I sat down at my table and spent an hour or two trying a great number of combinations, and I arrived at no result." And: "These sudden inspirations are never produced ... except after some days of voluntary efforts which appeared absolutely fruitless".

**10. Planck: the quantum (physics, 1900).** Wien's law fitted short wavelengths but failed at long ones. Rubens told
Planck the new measurements. Within days Planck guessed a formula that fitted all the data. He then derived it using
energy that comes in chunks, which he called "an act of desperation".
- Tags: AN STEP REC CHK REF
- Time/fails: the formula came "within a few days", and the explanation followed weeks later. Check: agreement with Rubens' measured spectrum.
- Source: https://en.wikipedia.org/wiki/Planck%27s_law — "Planck was informed by his friend Rubens and quickly created a formula within a few days."; "in what Planck called "an act of desperation", he turned to Boltzmann's atomic law of entropy".
- Lesson (SUGGESTED): the formula came before the explanation. That fits "blurt, check, understand later".

**11. Pauli: the neutrino (physics, 1930-1956).** Electrons from beta decay came out with a smear of energies, which
seemed to break conservation of energy. Bohr was ready to give up exact conservation. Pauli kept it and proposed an
invisible particle instead.
- Tags: AN CON CHK TOOL
- Time/fails: 26 years until detection. Check: the Cowan–Reines reactor experiment, 1956.
- Source: https://en.wikipedia.org/wiki/Neutrino — "In contrast to Niels Bohr, who proposed a statistical version of the conservation laws ... Pauli hypothesized an undetected particle".

**12. Dirac: antimatter (physics, 1928-1932).** Dirac's equation combining quantum theory and relativity had
negative-energy solutions that would not go away. He first identified them with the proton, which was wrong. Anderson
then found the positron in a cloud chamber.
- Tags: CON AN COM CHK TOOL
- Time/fails: 4 years and one wrong identification. Check: tracks in a magnetised cloud chamber, 2 Aug 1932.
- Source: https://en.wikipedia.org/wiki/Positron — "Dirac was puzzled by the equally valid negative-energy solution that the mathematical model allowed."; "Anderson discovered the positron on 2 August 1932".

**13. Fleming, then Florey and Chain: penicillin (medicine, 1928-1940).** A mould contaminated one of Fleming's
plates, and he noticed that it killed the bacteria. The work stalled for about 10 years. Chain found the "largely
forgotten" paper, and Florey's team purified the substance and tested it in mice.
- Tags: SER AN STEP COM CHK PER
- Time/fails: 12 years from plate to proof. Check: 25 May 1940, 8 infected mice. All 4 untreated mice were dead by morning. The treated mice lived.
- Source: https://en.wikipedia.org/wiki/History_of_penicillin — "By 3:30 am on Sunday all four of the untreated mice were dead."; "Ernst Boris Chain drew the attention of ... Howard Florey, to Fleming's largely forgotten 1929 paper."

**14. Ehrlich and Hata: Salvarsan (medicine, 1909).** Ehrlich's "magic bullet" principle held that a drug should hit
the germ and spare the patient. His lab screened hundreds of arsenic compounds, and Hata found that compound 606 worked
against syphilis.
- Tags: BRU CON COM CHK
- Check: cures in infected animals, then in patients.
- Source: https://en.wikipedia.org/wiki/Arsphenamine — "discovered by Sahachiro Hata in 1909, during a survey of hundreds of newly synthesized organic arsenical compounds."
- Myth status: "the 606th attempt" is **wrong** on that page: "originally called "606" because it was the sixth in the sixth group of compounds synthesized for testing".

**15. Edison: a practical light bulb (engineering, 1878-1880).** Swan and others already had carbon filaments. Edison's
team won through a better vacuum, high-resistance filaments, and systematic tests of filament materials, ending with
carbonised bamboo.
- Tags: BRU STEP TOOL CHK PER
- Time/fails: the first success burned 13.5 hours, and bamboo later passed 1200 hours. The famous "thousands of failures" count was not verified. Check: hours burned.
- Source: https://en.wikipedia.org/wiki/Incandescent_light_bulb — "The first successful test was on 22 October 1879, and lasted 13.5 hours."; "a carbonized Japanese bamboo filament could last more than 1200 hours."

**16. The Wright brothers: control and lift (engineering, 1899-1903).** Their gliders lifted less than the tables
predicted. They doubted the accepted "Smeaton coefficient", built a wind tunnel, and tested 200 model wings. Wing
twisting came from birds and from Wilbur absently twisting a box.
- Tags: AN TOOL BRU ANA CHK PER STEP
- Time/fails: two disappointing gliders (1900, 1901), and Wilbur said "man would not fly in a thousand years". Check: wind-tunnel numbers, then flight.
- Source: https://en.wikipedia.org/wiki/Wright_brothers — "showed that the poor lift of the 1900 and 1901 gliders was entirely due to an incorrect Smeaton value"; "discovered wing-warping when Wilbur idly twisted a long inner-tube box".

**17. Watson and Crick: the double helix (biology, 1951-1953).** They built physical models against firm constraints:
Chargaff's A=T and G=C, and the X-ray pictures, including Photo 51, which was shown to Watson without Franklin's
permission. Pauling's triple helix failed.
- Tags: CON STEP COM REC CHK
- Time/fails: about 2 years, with their own failed early model (not fetched) and Pauling's wrong one. Check: fit to the X-ray pattern and to base ratios. The pairing also suggested a copying mechanism.
- Source: https://en.wikipedia.org/wiki/Photo_51 — "Maurice Wilkins later shared the image with James Watson without their permission."; https://en.wikipedia.org/wiki/Molecular_Structure_of_Nucleic_Acids:_A_Structure_for_Deoxyribose_Nucleic_Acid — "In early 1953, Pauling published a triple helix model of DNA, which subsequently turned out to be incorrect."

**18. Mullis: PCR (biochemistry, 1983).** Mullis was working on a different problem, reading a single DNA letter. He
thought about how that method could fail, and saw that repeated copying doubles the target each cycle. Every step was
already known.
- Tags: REC REF CHK STEP
- Time/fails: the idea came on one night drive, and making it work took months (Taq polymerase came later, 1986). Check: arithmetic first, then gels.
- Source (primary, Nobel lecture): https://www.nobelprize.org/prizes/chemistry/1993/mullis/lecture/ — "Every time I did it I would double the signal."; "Everyone agreed that you could extend a primer on a DNA template, everyone knew you could melt double stranded DNA."

**19. Wiles: Fermat's Last Theorem (maths, 1986-1995).** Ribet's 1986 result was the stepping stone. Wiles announced
a proof in 1993, and referees found a gap. A year later he saw that each of two approaches he had tried, and set aside,
could repair the other.
- Tags: PER STEP REC CHK COM
- Time/fails: 7 years, plus 1 year on the gap. Check: expert referees, then publication with Taylor in 1995.
- Source: https://en.wikipedia.org/wiki/Wiles%27s_proof_of_Fermat%27s_Last_Theorem — "the Kolyvagin–Flach method wasn't working, but it was all I needed to make my original Iwasawa theory work from three years earlier."; "Each was inadequate by itself, but fixing one approach with tools from the other would resolve the issue".

**20. Perelman: the Poincaré conjecture (maths, 1904-2003).** Hamilton's Ricci-flow program was the stepping stone.
Perelman "modified and completed" it. Three separate groups checked the details in 2006.
- Tags: STEP PER CHK COM
- Time/fails: a century of attempts. Check: independent written checks by three teams.
- Source: https://en.wikipedia.org/wiki/Poincar%C3%A9_conjecture — "By developing a number of new techniques and results in the theory of Ricci flow, Grigori Perelman modified and completed Hamilton's program."

**21. Ishino, Mojica and others: CRISPR (biology, 1987-2012).** Strange repeats were seen in 1987. Mojica searched
genomes by computer and found that the spacers match viruses, and that those viruses cannot infect the carriers. From
that he inferred an immune system. Top journals rejected the paper.
- Tags: AN BRU TOOL STEP CHK PER
- Time/fails: 16-18 years to the immune idea, rejected by several journals, and 25 years to gene editing. Check: sequence matches, then phage-challenge experiments (Barrangou 2005).
- Source: https://pubmed.ncbi.nlm.nih.gov/15791728 (Mojica 2005 abstract) — "these extrachromosomal elements fail to infect the specific spacer-carrier strain, implying a relationship between CRISPR and immunity"; https://en.wikipedia.org/wiki/Francisco_Mojica — "The paper was rejected by a series of high-profile journals, including Nature".

**22. Karikó and Weissman: modified mRNA (medicine, 1990s-2005).** mRNA set off immune alarms. They compared RNAs and
noticed that mammalian RNA, which is rich in modified building blocks, did not set off the alarm. Swapping in modified
bases made mRNA quiet. Karikó had been demoted in 1995.
- Tags: PER AN COM CHK
- Time/fails: over a decade with little funding. Check: measured immune signals (TLR assays, dendritic-cell cytokines).
- Source: https://pubmed.ncbi.nlm.nih.gov/16111635 (Karikó 2005 abstract) — "potently activated by bacterial and mitochondrial RNA, but not by mammalian total RNA, which is abundant in modified nucleosides."

**Myths box (serendipity stories, graded).**
- Velcro (1941-1958): burrs on a dog, looked at under a microscope, then 10 years of trial and error with nylon. Tags ANA SER TOOL PER BRU. Source https://en.wikipedia.org/wiki/George_de_Mestral — "He examined them under a microscope, and noted hundreds of "hooks"". **SHOWN** (well documented).
- Microwave oven (1945): the melted candy bar is "According to legend" (https://en.wikipedia.org/wiki/Percy_Spencer). The popcorn and egg tests are documented. Tags SER AN CHK. **Partly legend**.
- Archimedes' bath: first written "two centuries after it supposedly took place" (https://en.wikipedia.org/wiki/Eureka_(word)). **Myth or unverifiable**.
- Newton's apple on the head, Kekulé's snake dream, Mendeleev's dream and cards, "Salvarsan was attempt 606": see cases 2, 8, 6, 14.

## Part 2. Research on how discovery works (quotes fetched; labels as above)

- **Dunbar 1997, "How scientists think" (in vivo study: taped meetings in 4 molecular-biology labs).**
  PDF: https://sites.cc.gatech.edu/classes/AY2013/cs7601_spring/papers/Dunbar.pdf.
  SHOWN (small sample, 16 meetings): "only 2 of the 99 analogies used by the scientists were of this type [distant]", and
  "distant analogies are rare and generally used for explanations rather than the generation of new hypotheses".
  SHOWN: unexpected results got far more discussion than expected ones ("23 interactions for "expected" findings and 176
  interactions for "unexpected" findings"), and "there was little attempt to explain away the "unexpected" findings".
  Of 70 coded findings, 22 were expected, 18 unexpected and 30 exploratory, so 26% were unexpected in this sample.
  SUGGESTED: "Conceptual change, like evolutionary change, is the result of tinkering."
- **Dunbar & Blanchette, "The in vivo/in vitro approach to cognition: the case of analogy" (TICS).**
  PDF: https://pages.ucsd.edu/~scoulson/203/dunbarTICS.pdf. SHOWN: analogies used to fix experiments were near ones.
  "When scientists switched goals to formulating a hypothesis ... The distance between the source and the target
  increased". "While only 25% of all analogies ... were based on structural rather than superficial features, over 80%
  of these structural analogies were used to formulate hypotheses." Also SHOWN: "when generating analogies, people use
  structural information and when recalling analogs they use superficial features."
- **Dunbar & Fugelsang 2005, "Causal thinking in science".** I found only the citation, not the text. The common claim
  that "half or more of lab findings are unexpected" is **NOT VERIFIED** here. The 1997 sample above gives 26%.
- **Langley 1981, BACON.3** (Cognitive Science; abstract via Crossref, DOI 10.1111/j.1551-6708.1981.tb00869.x). SHOWN
  that simple heuristics ("detect constancies and trends in data") rediscover "Kepler's third law ... Coulomb's law,
  Ohm's law" from supplied data. **DISPUTED** as a model of discovery: Chalmers, French and Hofstadter 1992
  (http://consc.net/papers/highlevel.pdf): "BACON, in short, works only in a world of hand-picked, prestructured data".
  They add that students given BACON's data "could make essentially the same "discoveries" within an hour-long experiment".
  Lesson (SUGGESTED): picking the representation is the hard part, and search inside a representation is the easy part.
- **Kulkarni & Simon 1988, KEKADA** (Cognitive Science, DOI 10.1207/s15516709cog1202_1). SHOWN as a simulation of one
  case, Krebs and the urea cycle: "KEKADA reacts to surprises, formulates explanations, and carries out experiments in the
  same manner as the evidence ... indicates Hans Krebs did." Whether this generalises is SUGGESTED.
- **Knoblich, Ohlsson, Haider & Rhenius 1999, representational change** (JEP:LMC; abstract on the CEU research portal).
  SHOWN for matchstick *arithmetic* puzzles: "impasses are broken by changing the problem representation ... the
  relaxation of constraints on the solution and the decomposition of perceptual chunks ... tested in 4 experiments using
  matchstick arithmetic problems. The results were consistent with the predictions."
- **Wagner et al. 2004, "Sleep inspires insight"** (Nature, PMID 14737168; a number task with a hidden rule). SHOWN:
  "more than twice as many subjects gained insight into the hidden rule after sleep as after wakefulness". Also SHOWN:
  "Sleep did not enhance insight in the absence of initial training."
- **Gentner 1983, structure-mapping** (Cognitive Science, DOI 10.1207/s15516709cog0702_3). A theory: "Relations between
  objects, rather than attributes of objects, are mapped from base to target", chosen by "systematicity". Later
  experimental support exists, but I did not fetch it, so it is SUGGESTED here.
- **Simonton 2010, creativity as blind variation and selective retention** (Phys Life Rev, PMID 20416854). A review of
  combinatorial models, SUGGESTED. His own 2024 update (PMID 39270513) admits "its formal definition of "blindness" was
  inadequate", so the details are **DISPUTED**.
- **Uzzi, Mukherjee, Stringer & Jones 2013** (Science, PMID 24159044; 17.9M papers). SHOWN as a correlation, not a
  cause: the top work is "grounded in exceptionally conventional combinations of prior work yet simultaneously features
  an intrusion of unusual combinations. Papers of this type were twice as likely to be highly cited".
- **Wu, Wang & Evans 2019** (Nature, PMID 30760923; 65M papers, patents and software products). SHOWN as a correlation:
  "smaller teams have tended to disrupt science and technology with new ideas and opportunities, whereas larger teams
  have tended to develop existing ones"; small teams "search more deeply into the past".
- **Fortunato et al. 2018, "Science of science"** (Science review, PMC5949209). SHOWN as correlations: "scholars are
  risk-averse, preferring to study topics related to their current expertise ... Those willing to break this pattern
  engage in riskier careers but become more likely to make major breakthroughs." Also: "the highest-impact work can be,
  with the same probability, anywhere in the sequence of papers" (so more tries means more hits). And: "the actual
  strategy of science is suboptimal for discovering" the network of chemical relations.

## Part 3. Synthesis: mechanisms ranked by how often they appear (22 numbered cases)

Counts are my own tags from Part 1. That makes them SUGGESTED: another reader could tag differently, and famous
discoveries are a biased sample. Incubation and serendipity score low partly because the vivid stories are the
disputed ones (Kekulé, Archimedes, the melted candy bar).

| # | Mechanism | Cases | Plain lesson | Model part | Have it? |
|---|---|---|---|---|---|
| 1 | Exact check | 20/22 | Every story ended in a hard test, not a feeling | The code checker is the only judge of a win | **Yes** (shown in blurt-2/3) |
| 2 | Stepping stone | 17/22 | Almost nobody started from zero | Pieces library (b); asking a human | Partly (near-miss stones, asking) |
| 3 | Persistence | 11/22 | Wins came after long, useless-looking work | Open-problems shelf, retried after each sleep | No |
| 4 | Anomaly | 10/22 | The start was one number that did not fit | Practise surprises first (c) | Partly (the belief gives predictions to be surprised by) |
| 5 | Community | 10/22 | Others checked, fixed and supplied data | Asking a human; a second model as critic | Partly (asking); rest UNTESTED |
| 6 | Strict constraint | 9/22 | Trusting a law forces a prediction (Neptune, the neutrino, Mendeleev's gaps) | Rule-keeping blurts, plus a "missing piece" move | **Yes** (2.4% vs 0.1-0.2% right; roadmap figures, different sets) |
| 7 | Reframing | 7/22 | Change the question, not only the answer | Restated puzzles, with pieces carried back (a) | No |
| 8 | Brute-force search | 6/22 | Works when options are few and checks are cheap | The checker's job on puzzles; test-driven search in code | Yes for code, trivially |
| 9 | Analogy | 6/22 | Mostly near and structural, rarely wild (Dunbar) | Fetch a solved puzzle with the same shape as a hint | No |
| 10 | Instrument | 5/22 | A new tool opened the view | Calculator or code runner (later, for coding) | Cannot test on puzzles |
| 11 | Recombination | 4/22 | New = old pieces in a new order (PCR, Wiles) | Hints mostly familiar plus one unusual piece (Uzzi) | No |
| 12 | Incubation/sleep | 1/22 (+2 disputed) | Sleep helps only after real effort (Wagner) | Sleep on hits | **Yes** (blurt-3 PASS; blurt-3r pending) |
| 13 | Serendipity | 1/22 (+Velcro, microwave) | A hit on the wrong target is still a hit | Save "off-target hits" as pieces | No |

**What cannot be tested on number puzzles (honest list).** Teams and communities, new instruments, persistence over
years, distant analogy across fields (there is only one field), and physical accidents. On 3-4-number puzzles, brute
force by code solves everything instantly. So the puzzles test whether *the model* learns to find answers. They do not
test discovery in the historical sense. Coding is the first place where search is costly, so it is the first real test.

### Proposed model parts, one change at a time (all UNTESTED; pass marks set before running)

**A. Practise surprises first (anomaly, persistence, and Ben's (c)).** Surprise is measured against the model's own
belief. (i) It predicted "can't", yet a blurt hit (this links to ask-24). (ii) It was confident, yet it missed. (iii) A
near miss: off by 1-2, with every rule kept. Surprises go on an open-problems shelf and are practised and retried first
after sleep. The Dunbar and KEKADA evidence (SHOWN/SUGGESTED above) is that surprises get the most reasoning.
Test: three arms with equal sleep-example counts. S = surprise-first. E = edge-of-ability (1-29 of 30 blurts right,
the Absolute Zero idea). R = random misses. Measure lucky blurts per 30 on a fresh set, over two seeds. PASS: S ≥ 1.2×R
and E ≥ 1.2×R in both seeds. Proved wrong: S ≤ R. Report S vs E, but do not claim a winner unless one is ≥ 1.2× the
other.

**B. Reframe and carry back (reframing, strict constraint; Ben's (a)).** The code, not the model, makes the variants at
first, so the change stays single: (1) another target (target ± 1-3, target ÷ 2); (2) a relaxed rule (use 3 of the 4
numbers); (3) work backwards (24 = 4×6, so make 4 and 6 from the numbers; this is Knoblich's "chunk decomposition");
(4) flip the question and try to show "can't" (Poincaré tried to prove non-existence and found existence). A checked
answer to a variant becomes a piece, and the checker tries joining it back. Test: on puzzles still missed after 30 plain
blurts, compare 30 more plain blurts against 30 blurts spread over variants plus carry-back, with the same number of
model calls. PASS: ≥ 1.5× as many puzzles solved in both seeds. Proved wrong: variants ≤ plain. Knoblich showed
representational change in humans on matchstick arithmetic. For a 1B model it is UNTESTED.

**C. Pieces library with retrieval by shape (stepping stones, analogy, recombination, serendipity; Ben's (b)).** Store
every checked sub-expression and every off-target hit as (value, numbers used, expression, skeleton), for example
"(a*(b-c))". Build the store only from practice puzzles, never from test puzzles. On a miss, give 4 hints: 3 near pieces
and 1 unusual piece, following Uzzi. Retrieve by *shape* (same skeleton, same factorisation of the target), not by
*surface* (same numbers). Dunbar found that recall runs on surface features while useful hypotheses came from structure.
Test: three arms with the same blurt count: no hint, surface-retrieved and shape-retrieved. PASS: shape ≥ 1.3× no hint
and shape > surface in both seeds. Proved wrong: shape ≤ no hint.

**Also worth knowing.** (1) Vulcan: the recipe that found Neptune failed for Mercury. A "can't" learner (ask-24) needs
exactly this distinction between "not found yet" and "cannot exist", and the puzzles have an exact impossibility check.
(2) Wiles repaired his proof with two approaches he had set aside, so the library should also keep checked pieces from
failed attempts. (3) Wagner found that sleep helped only after training. Prediction (UNTESTED): sleep gains concentrate
on puzzle types already attempted, and are near zero on unseen types.

## Plain summary for Ben
1. Across 22 big discoveries, the most common ingredients were an exact test (20 of 22), building on someone else's work (17), long persistence (11) and noticing a number that did not fit (10).
2. Flashes of insight while dreaming are the least reliable part of the history: Kekulé's snake, Archimedes' bath and Newton's apple on the head are disputed or myths.
3. Real scientists mostly use *near* comparisons, not wild ones: in one lab study only 2 of 99 analogies were distant.
4. The hard part is often choosing how to look at the problem. BACON "discovered" Kepler's law only after humans handed it the right data.
5. You already have the top ingredients: an exact checker, rule-keeping guesses, sleep on hits, and asking.
6. Next, I would add, one at a time: practise surprises first, restate puzzles and carry the pieces back, and a pieces library searched by shape.
