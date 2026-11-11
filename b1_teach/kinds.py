"""B1 TEACH: the 60 fixed question kinds (+ spare kinds), with 2 hand-written examples each.

Fixed before generation (design/thinker-first-split-2026-10-05.md section 6). Kinds 1-6 are the round-4 practised
kinds (so both arms practised what FRESH-EN-R3 tests); kinds 7-60 are the 54 listed in the spec, in spec order.
Each example = (passage, paraphrase, short_question, short_answer, yes_no_question, yes_no_answer).
SPARES replace a kind that loses more than half its rows to the overlap guard.
"""

# (name, one-line description of what the passage says and what the questions ask, [ex1, ex2])
KINDS = [
    # ---- 6 practised round-4 kinds ----
    ("giver_recipient_roles", "someone gives, hands, sends or throws a thing to someone else (who gave, who got, what was given)", [
        ("At the fair, Orrin handed a pear to Sela.", "At the fair, a pear was handed to Sela by Orrin.", "Who handed the pear to Sela?", "Orrin", "Did Sela hand the pear to Orrin?", "No"),
        ("Mina sent a postcard to her uncle.", "A postcard was sent to her uncle by Mina.", "What did Mina send to her uncle?", "a postcard", "Did Mina send a postcard?", "Yes")]),
    ("comparative_direction", "two things are compared (taller, older, heavier, longer, softer...) and both are in the same place", [
        ("The oak rail is longer than the pine rail; both rails lie in the shed.", "The pine rail is shorter than the oak rail; both rails lie in the shed.", "Which rail is shorter?", "the pine rail", "Is the oak rail longer than the pine rail?", "Yes"),
        ("The felt hat is softer than the straw hat, and both hang by the door.", "The straw hat is harder than the felt hat, and both hang by the door.", "Which hat is softer?", "the felt hat", "Is the straw hat softer than the felt hat?", "No")]),
    ("explicit_negation_with_positive_alternative", "someone did NOT choose or do one thing and instead chose or did another thing", [
        ("For lunch, Kiri did not eat the soup; Kiri ate the salad.", "For lunch, Kiri ate the salad and did not eat the soup.", "What did Kiri not eat for lunch?", "the soup", "Did Kiri eat the salad for lunch?", "Yes"),
        ("Joss did not wear the green scarf on Friday; Joss wore the grey one.", "On Friday, Joss wore the grey scarf and did not wear the green one.", "Which scarf did Joss wear on Friday?", "the grey one", "Did Joss wear the green scarf on Friday?", "No")]),
    ("event_ordering", "one event happens before or after another event, said with before/after", [
        ("Wren mopped the hall before she watered the ferns.", "Wren watered the ferns after mopping the hall.", "What did Wren do first?", "mopped the hall", "Did Wren water the ferns before mopping the hall?", "No"),
        ("Pell locked the shop after he counted the money.", "Pell counted the money before locking the shop.", "What did Pell lock?", "the shop", "Did Pell count the money before locking the shop?", "Yes")]),
    ("unambiguous_descriptive_reference", "two similar objects are told apart by a detail (the cracked one, the left one), and someone uses one of them", [
        ("Two pots stood on a step: the dented one was left of the shiny one. Dara took the right-hand pot inside.", "Two pots stood on a step: the shiny one was right of the dented one. Dara took the pot on the right inside.", "Which pot did Dara take inside?", "the shiny pot", "Did Dara take the dented pot?", "No"),
        ("Two spades leaned on a fence, the rusty one near the gate and the clean one far from it. Hobb borrowed the rusty spade.", "Two spades leaned on a fence, the clean one far from the gate and the rusty one near it. Hobb borrowed the one that was rusty.", "Which spade did Hobb borrow?", "the rusty spade", "Did Hobb borrow the clean spade?", "No")]),
    ("two_simple_relations_combined", "two things about where objects are put are joined (A is on B, and B is on C)", [
        ("A blue scarf lay on a cane chair, and the chair stood by a brick wall.", "The cane chair stood by a brick wall, with a blue scarf lying on the chair.", "What lay on the cane chair?", "a blue scarf", "Did the chair stand by a brick wall?", "Yes"),
        ("A tin whistle hung on a nail, and the nail was in a wooden beam.", "The nail was in a wooden beam, and a tin whistle hung on it.", "Where was the nail?", "in a wooden beam", "Did the whistle hang on a rope?", "No")]),
    # ---- 54 listed kinds (spec order) ----
    ("owner_possession", "a thing belongs to a named person (whose kite, whose bag)", [
        ("The yellow kite on the roof is Nell's.", "Nell is the owner of the yellow kite on the roof.", "Whose kite is on the roof?", "Nell's", "Is the kite Nell's?", "Yes"),
        ("The big drum in the hall belongs to Ravi.", "Ravi owns the big drum in the hall.", "Who owns the big drum?", "Ravi", "Does the drum belong to Nell?", "No")]),
    ("agent_action", "a named person does one clear action to an object", [
        ("Odell patched the old tent.", "The old tent was patched by Odell.", "What did Odell do to the tent?", "patched it", "Did Odell patch the tent?", "Yes"),
        ("Lena stirred the thick stew.", "The thick stew was stirred by Lena.", "What did Lena stir?", "the thick stew", "Did Lena chop the stew?", "No")]),
    ("companion_with", "a person goes somewhere or does something together with another person", [
        ("Bram walked to the lake with his cousin Aya.", "With his cousin Aya, Bram walked to the lake.", "Who did Bram walk with?", "his cousin Aya", "Did Bram walk to the lake alone?", "No"),
        ("Suri sat at the back of the bus beside Kolo.", "Beside Kolo, Suri sat at the back of the bus.", "Who sat beside Suri?", "Kolo", "Did Suri sit beside Kolo?", "Yes")]),
    ("feeling_state", "a person feels some way (glad, nervous, tired, proud) because of something", [
        ("Idris felt proud after he finished the long puzzle.", "After finishing the long puzzle, Idris felt proud.", "How did Idris feel?", "proud", "Did Idris feel sad?", "No"),
        ("Tilly was nervous before her first dance class.", "Before her first dance class, Tilly felt nervous.", "How did Tilly feel before the class?", "nervous", "Was Tilly nervous?", "Yes")]),
    ("naming", "a pet or thing has a name", [
        ("The grey rabbit next door is called Biscuit.", "Next door, there is a grey rabbit named Biscuit.", "What is the rabbit called?", "Biscuit", "Is the rabbit called Biscuit?", "Yes"),
        ("Mara named her little boat Sparrow.", "Mara's little boat is named Sparrow.", "What did Mara name her boat?", "Sparrow", "Is the boat named Mara?", "No")]),
    ("family_relation", "a person is the sister, brother, aunt, grandfather or other relative of another person", [
        ("Corin's sister, Hazel, plays the flute.", "Hazel, who plays the flute, is Corin's sister.", "Who is Corin's sister?", "Hazel", "Does Hazel play the flute?", "Yes"),
        ("Pavel lives with his grandmother, Oksa.", "Oksa is Pavel's grandmother, and he lives with her.", "Who does Pavel live with?", "his grandmother", "Is Oksa Pavel's aunt?", "No")]),
    ("occupation", "a person has a job (baker, nurse, driver, farmer)", [
        ("Ingrid is the nurse at the village clinic.", "At the village clinic, Ingrid works as the nurse.", "What is Ingrid's job?", "nurse", "Is Ingrid a baker?", "No"),
        ("Tomas drives the school bus every morning.", "Every morning, Tomas is the driver of the school bus.", "What does Tomas drive?", "the school bus", "Is Tomas a bus driver?", "Yes")]),
    ("part_whole", "a part of an object is broken, missing or new (the wheel of the cart, the lid of the pot)", [
        ("The handle of the old pitcher snapped off.", "The old pitcher lost its handle when it snapped off.", "What part of the pitcher snapped off?", "the handle", "Did the pitcher's handle snap off?", "Yes"),
        ("Edda's bicycle has a bent front wheel.", "The front wheel of Edda's bicycle is bent.", "Which part of the bicycle is bent?", "the front wheel", "Is the back wheel bent?", "No")]),
    ("goal_want", "a person wants or hopes to get or do something", [
        ("Fenwick wanted a ride on the wooden horse.", "A ride on the wooden horse was what Fenwick wanted.", "What did Fenwick want?", "a ride on the wooden horse", "Did Fenwick want a ride?", "Yes"),
        ("Yara hopes to learn the violin.", "Learning the violin is what Yara hopes for.", "What does Yara hope to learn?", "the violin", "Does Yara hope to learn the piano?", "No")]),
    ("object_eaten", "a person eats or drinks one particular food", [
        ("Cosmo ate a ripe plum on the porch.", "On the porch, a ripe plum was eaten by Cosmo.", "What did Cosmo eat?", "a ripe plum", "Did Cosmo eat a plum?", "Yes"),
        ("Dilys drank hot milk before bed.", "Before bed, Dilys had a cup of hot milk.", "What did Dilys drink?", "hot milk", "Did Dilys drink juice?", "No")]),
    ("object_made", "a person bakes, builds, sews or draws one thing", [
        ("Rhea baked a round loaf for the picnic.", "For the picnic, Rhea made a round loaf by baking it.", "What did Rhea bake?", "a round loaf", "Did Rhea bake a cake?", "No"),
        ("Gus built a tiny bridge from sticks.", "A tiny bridge was built from sticks by Gus.", "What did Gus build?", "a tiny bridge", "Did Gus build the bridge from sticks?", "Yes")]),
    ("object_read", "a person reads a book, letter, sign or note", [
        ("Marit read a funny poem to the class.", "To the class, Marit read a funny poem.", "What did Marit read?", "a funny poem", "Did Marit read to the class?", "Yes"),
        ("Basil read the long letter twice.", "The long letter was read twice by Basil.", "What did Basil read twice?", "the long letter", "Did Basil read a map?", "No")]),
    ("container_contents", "a container holds something (a jar of buttons, a box of chalk)", [
        ("The tin on the shelf was full of buttons.", "Buttons filled the tin on the shelf.", "What was in the tin?", "buttons", "Was the tin empty?", "No"),
        ("Inside the wicker basket were three fresh eggs.", "The wicker basket held three fresh eggs.", "What was in the basket?", "three fresh eggs", "Did the basket hold eggs?", "Yes")]),
    ("category_member", "something is said to be a kind of thing (a robin is a bird, a pine is a tree)", [
        ("A robin is a small bird with a red chest.", "With a red chest, the robin is a small bird.", "What kind of animal is a robin?", "a bird", "Is a robin a fish?", "No"),
        ("A pine is a tall tree with needles.", "The pine, a tall tree, has needles.", "What is a pine?", "a tall tree", "Is a pine a tree?", "Yes")]),
    ("ability", "someone can or cannot do something (swim, ride a bike, whistle)", [
        ("Lotta can whistle two songs, but she cannot yet swim.", "Lotta cannot yet swim, though she can whistle two songs.", "What can Lotta do?", "whistle two songs", "Can Lotta swim?", "No"),
        ("Ansel can ride a bike without help.", "Without any help, Ansel can ride a bike.", "What can Ansel do without help?", "ride a bike", "Can Ansel ride a bike?", "Yes")]),
    ("rule_must", "a rule says what someone must do (wear a helmet, line up, wash hands)", [
        ("Every rider must wear a helmet in the yard.", "In the yard, a helmet must be worn by every rider.", "What must every rider wear?", "a helmet", "Must riders wear a helmet?", "Yes"),
        ("At the pool, children must walk and not run.", "Children at the pool must not run; they must walk.", "What must children do at the pool?", "walk", "May children run at the pool?", "No")]),
    ("like_best", "a person likes one thing best of all", [
        ("Of all the fruit, Hana likes mangoes best.", "Hana likes mangoes best of all the fruit.", "What fruit does Hana like best?", "mangoes", "Does Hana like mangoes best?", "Yes"),
        ("Of all the games, Per likes chess the most.", "Chess is the game Per likes the most.", "Which game does Per like the most?", "chess", "Does Per like checkers the most?", "No")]),
    ("dislike", "a person does not like one thing", [
        ("Quill does not like loud music at night.", "Loud music at night is something Quill does not like.", "What does Quill not like?", "loud music at night", "Does Quill like loud music?", "No"),
        ("Nadia dislikes the smell of fish.", "The smell of fish is disliked by Nadia.", "What does Nadia dislike?", "the smell of fish", "Does Nadia dislike the smell of fish?", "Yes")]),
    ("plan_next", "a person says or decides what they will do next", [
        ("Next, Elio will sand the table.", "Elio will sand the table next.", "What will Elio do next?", "sand the table", "Will Elio sand the table next?", "Yes"),
        ("After dinner, Greta plans to feed the goats.", "Greta plans to feed the goats after dinner.", "What does Greta plan to do after dinner?", "feed the goats", "Does Greta plan to milk the cow?", "No")]),
    ("habit", "a person does something every day, week or season", [
        ("Osric feeds the ducks every morning.", "Every morning, the ducks are fed by Osric.", "What does Osric do every morning?", "feeds the ducks", "Does Osric feed the ducks every morning?", "Yes"),
        ("Every Sunday, Vesna visits her aunt.", "Vesna visits her aunt every Sunday.", "Who does Vesna visit every Sunday?", "her aunt", "Does Vesna visit her aunt every Monday?", "No")]),
    ("if_then", "an if-then rule or cause (if the bell rings, then the gate opens)", [
        ("If the bell rings twice, the gate opens.", "The gate opens when the bell rings twice.", "What happens if the bell rings twice?", "the gate opens", "Does the gate open if the bell rings twice?", "Yes"),
        ("If the kettle whistles, Ruben turns off the stove.", "Ruben turns off the stove when the kettle whistles.", "What does Ruben do if the kettle whistles?", "turns off the stove", "Does Ruben leave the stove on?", "No")]),
    ("team_member", "a person is on a team or in a club, with a team colour or name", [
        ("Zeke plays on the Otter team.", "The Otter team is the team Zeke plays on.", "Which team is Zeke on?", "the Otter team", "Is Zeke on the Otter team?", "Yes"),
        ("Beth belongs to the reading club at school.", "At school, Beth is a member of the reading club.", "Which club does Beth belong to?", "the reading club", "Does Beth belong to the chess club?", "No")]),
    ("helper", "one person helps another person with a task", [
        ("Cedric helped Alma carry the heavy crate.", "Alma was helped by Cedric to carry the heavy crate.", "Who helped Alma?", "Cedric", "Did Alma help Cedric?", "No"),
        ("Dorrit helped the boy find his glasses.", "The boy was helped by Dorrit to find his glasses.", "Who helped the boy?", "Dorrit", "Did Dorrit help the boy find his glasses?", "Yes")]),
    ("patient_target", "an animal or person does something TO another (the dog chased the goose)", [
        ("The collie chased the goose around the barn.", "The goose was chased around the barn by the collie.", "Who did the collie chase?", "the goose", "Did the goose chase the collie?", "No"),
        ("A tiny wasp stung Pavo on the arm.", "Pavo was stung on the arm by a tiny wasp.", "Who did the wasp sting?", "Pavo", "Did the wasp sting Pavo?", "Yes")]),
    ("winner", "a game or race has a winner", [
        ("Joaquin won the sack race at the fair.", "At the fair, the sack race was won by Joaquin.", "Who won the sack race?", "Joaquin", "Did Joaquin win the race?", "Yes"),
        ("The Heron team won the final match.", "The final match was won by the Heron team.", "Which team won the final match?", "the Heron team", "Did the Heron team lose?", "No")]),
    ("loser", "a game or race has a loser", [
        ("Tamsin lost the chess game to her brother.", "Tamsin's brother beat her at chess.", "Who lost the chess game?", "Tamsin", "Did Tamsin lose to her brother?", "Yes"),
        ("The Falcon team lost the last match.", "The last match was lost by the Falcon team.", "Which team lost the last match?", "the Falcon team", "Did the Falcon team win?", "No")]),
    ("learned", "a person learns or finds out a fact or a skill", [
        ("Odile learned how to tie a sailor's knot.", "A sailor's knot is what Odile learned to tie.", "What did Odile learn?", "how to tie a sailor's knot", "Did Odile learn to tie a knot?", "Yes"),
        ("At camp, Rufus learned to light a fire safely.", "Rufus learned at camp how to light a fire safely.", "What did Rufus learn at camp?", "to light a fire safely", "Did Rufus learn to swim at camp?", "No")]),
    ("topic_about", "a book, song, film or talk is about something", [
        ("The book on the desk is about a lighthouse keeper.", "On the desk lies a book about a lighthouse keeper.", "What is the book about?", "a lighthouse keeper", "Is the book about a lighthouse keeper?", "Yes"),
        ("Pia's song is about her old dog.", "The song Pia wrote is about her old dog.", "What is Pia's song about?", "her old dog", "Is the song about a horse?", "No")]),
    ("creator", "a person painted, wrote or made a picture, song or story", [
        ("The mural by the school gate was painted by Soren.", "Soren painted the mural by the school gate.", "Who painted the mural?", "Soren", "Did Soren paint the mural?", "Yes"),
        ("Yvette wrote the short play about the market.", "The short play about the market was written by Yvette.", "Who wrote the play?", "Yvette", "Did Soren write the play?", "No")]),
    ("language_spoken", "a person speaks a language", [
        ("Matteo speaks Italian at home and English at school.", "At home Matteo speaks Italian, and at school he speaks English.", "What language does Matteo speak at home?", "Italian", "Does Matteo speak English at home?", "No"),
        ("Linh's grandmother speaks Vietnamese.", "Vietnamese is the language that Linh's grandmother speaks.", "What language does Linh's grandmother speak?", "Vietnamese", "Does Linh's grandmother speak Vietnamese?", "Yes")]),
    ("hobby", "a person has a hobby (stamps, knitting, birdwatching)", [
        ("Wilf's hobby is collecting old stamps.", "Collecting old stamps is Wilf's hobby.", "What is Wilf's hobby?", "collecting old stamps", "Is Wilf's hobby knitting?", "No"),
        ("Cleo spends her weekends birdwatching.", "On weekends, Cleo goes birdwatching.", "What does Cleo do on weekends?", "birdwatching", "Does Cleo go birdwatching?", "Yes")]),
    ("title_role", "a person holds a role or title (captain, mayor, leader of the group)", [
        ("Rosalind is the captain of the rowing crew.", "The rowing crew's captain is Rosalind.", "Who is the captain of the crew?", "Rosalind", "Is Rosalind the captain?", "Yes"),
        ("Thorne became mayor of the small town.", "The small town's new mayor is Thorne.", "Who became mayor?", "Thorne", "Did Thorne become the captain?", "No")]),
    ("best_friend", "a person has a best friend", [
        ("Ulrich's best friend is a girl called Maeve.", "Maeve, a girl, is Ulrich's best friend.", "Who is Ulrich's best friend?", "Maeve", "Is Maeve Ulrich's best friend?", "Yes"),
        ("Alba and Dmitri have been best friends since they were four.", "Since they were four, Alba and Dmitri have been best friends.", "Who is Alba's best friend?", "Dmitri", "Is Alba's best friend Maeve?", "No")]),
    ("lost_item", "a person loses an item", [
        ("Hollis lost his wool gloves on the way home.", "On the way home, Hollis lost his wool gloves.", "What did Hollis lose?", "his wool gloves", "Did Hollis lose his hat?", "No"),
        ("Perdita lost the key to the shed.", "The key to the shed was lost by Perdita.", "What did Perdita lose?", "the key to the shed", "Did Perdita lose a key?", "Yes")]),
    ("found_item", "a person finds an item", [
        ("Jorgen found a silver coin under the bench.", "Under the bench, a silver coin was found by Jorgen.", "What did Jorgen find?", "a silver coin", "Did Jorgen find a coin?", "Yes"),
        ("Sabine found a small shell on the sand.", "On the sand, Sabine came across a small shell.", "What did Sabine find on the sand?", "a small shell", "Did Sabine find a stone?", "No")]),
    ("choice_pick", "a person picks one of two options (tea or milk, the red one or the blue one)", [
        ("Asher could choose tea or milk, and he picked milk.", "Asher picked milk when he could choose tea or milk.", "Which did Asher pick, tea or milk?", "milk", "Did Asher pick tea?", "No"),
        ("Eira chose the short path instead of the long road.", "Instead of the long road, Eira chose the short path.", "What did Eira choose?", "the short path", "Did Eira choose the long road?", "No")]),
    ("fact_yes_no", "a person did or did not do a simple thing (lock, close, pay, call)", [
        ("Nico locked the back door before bed.", "Before bed, the back door was locked by Nico.", "What did Nico lock before bed?", "the back door", "Did Nico lock the back door?", "Yes"),
        ("Saskia did not close the gate.", "The gate was not closed by Saskia.", "What did Saskia not close?", "the gate", "Did Saskia close the gate?", "No")]),
    ("forgot", "a person forgets something (a lunch, a hat, a name)", [
        ("Leopold forgot his lunch on the kitchen table.", "On the kitchen table, Leopold left his forgotten lunch.", "What did Leopold forget?", "his lunch", "Did Leopold forget his lunch?", "Yes"),
        ("Marguerite forgot the name of the new boy.", "The new boy's name was forgotten by Marguerite.", "What did Marguerite forget?", "the name of the new boy", "Did Marguerite forget her coat?", "No")]),
    ("permission", "a person lets another person in, or allows something", [
        ("The porter let the guests in through the side door.", "Through the side door, the porter let in the guests.", "Who let the guests in?", "the porter", "Did the porter let the guests in?", "Yes"),
        ("Mama allowed Teodor to stay up late.", "Teodor was allowed by Mama to stay up late.", "Who allowed Teodor to stay up late?", "Mama", "Did Papa allow Teodor to stay up?", "No")]),
    ("game_played", "people play a named game", [
        ("After school, Katya and Emil played marbles.", "Marbles was the game Katya and Emil played after school.", "What game did they play?", "marbles", "Did they play marbles?", "Yes"),
        ("The twins played checkers on the porch.", "On the porch, the twins played a game of checkers.", "What game did the twins play?", "checkers", "Did the twins play cards?", "No")]),
    ("clothing", "a person wears or puts on some clothes", [
        ("Dagny wore a thick wool coat to the market.", "To the market, Dagny wore a thick wool coat.", "What did Dagny wear?", "a thick wool coat", "Did Dagny wear a coat?", "Yes"),
        ("Bertil put on his striped socks.", "His striped socks were put on by Bertil.", "What did Bertil put on?", "his striped socks", "Did Bertil put on boots?", "No")]),
    ("replacement", "one thing replaced another thing", [
        ("A new lamp replaced the cracked one in the hall.", "In the hall, the cracked lamp was replaced by a new one.", "What was replaced?", "the cracked lamp", "Was the new lamp replaced?", "No"),
        ("The town put a stone bridge in place of the wooden one.", "A stone bridge replaced the town's wooden bridge.", "What replaced the wooden bridge?", "a stone bridge", "Did a stone bridge replace the wooden one?", "Yes")]),
    ("visitor", "a person visits or comes to see another person", [
        ("Aunt Philippa visited Roan on his birthday.", "On his birthday, Roan was visited by Aunt Philippa.", "Who visited Roan?", "Aunt Philippa", "Did Roan visit Aunt Philippa?", "No"),
        ("A tall stranger came to see the baker.", "The baker was visited by a tall stranger.", "Who came to see the baker?", "a tall stranger", "Did the baker have a visitor?", "Yes")]),
    ("joiner", "a person joins a club, a team or a group", [
        ("Imogen joined the choir in the spring.", "In the spring, Imogen became a member of the choir.", "Who joined the choir?", "Imogen", "Did Imogen join the choir?", "Yes"),
        ("Lucan joined the hiking club last month.", "Last month, the hiking club gained a new member, Lucan.", "Which club did Lucan join?", "the hiking club", "Did Lucan join the choir?", "No")]),
    ("search_for", "a person looks for something", [
        ("Odette was looking for her red umbrella.", "Her red umbrella was what Odette was looking for.", "What was Odette looking for?", "her red umbrella", "Was Odette looking for her umbrella?", "Yes"),
        ("Everett searched the attic for his old skates.", "In the attic, Everett searched for his old skates.", "What was Everett searching for?", "his old skates", "Did Everett search the cellar?", "No")]),
    ("fear", "a person is afraid of something", [
        ("Sunniva is afraid of spiders.", "Spiders are what Sunniva is afraid of.", "What is Sunniva afraid of?", "spiders", "Is Sunniva afraid of spiders?", "Yes"),
        ("Cyril is scared of the dark hallway.", "The dark hallway scares Cyril.", "What is Cyril scared of?", "the dark hallway", "Is Cyril scared of dogs?", "No")]),
    ("wish", "a person wishes for something", [
        ("Elspeth wished for a pony on her birthday.", "On her birthday, Elspeth wished for a pony.", "What did Elspeth wish for?", "a pony", "Did Elspeth wish for a pony?", "Yes"),
        ("Dov wishes for a quiet summer.", "A quiet summer is what Dov wishes for.", "What does Dov wish for?", "a quiet summer", "Does Dov wish for a loud summer?", "No")]),
    ("pronoun_reference", "two people appear and a pronoun (she, he, they) points to exactly one of them, clear from the sentence", [
        ("Marta called Ines because she was late.", "Because she was late, Marta called Ines.", "Who was late?", "Marta", "Was Ines late?", "No"),
        ("Hugo thanked Oskar because he had fixed the gate.", "Because he had fixed the gate, Hugo thanked Oskar.", "Who fixed the gate?", "Oskar", "Did Hugo fix the gate?", "No")]),
    ("teacher_of", "a person teaches, trains or coaches another person", [
        ("Madame Roux taught Felix to play the cello.", "Felix was taught to play the cello by Madame Roux.", "Who taught Felix?", "Madame Roux", "Did Felix teach Madame Roux?", "No"),
        ("Coach Brandt trains the young swimmers.", "The young swimmers are trained by Coach Brandt.", "Who trains the swimmers?", "Coach Brandt", "Does Coach Brandt train swimmers?", "Yes")]),
    ("neighbor", "a person lives next door to another person", [
        ("Winnie's neighbor is a retired sailor named Ahab.", "Ahab, a retired sailor, lives next door to Winnie.", "Who is Winnie's neighbor?", "Ahab", "Is Ahab Winnie's neighbor?", "Yes"),
        ("The Okafors live next door to the miller.", "The miller's neighbors are the Okafors.", "Who lives next door to the miller?", "the Okafors", "Do the Okafors live next door to the baker?", "No")]),
    ("named_after", "a pet, child or place was named after someone", [
        ("The puppy was named after Uncle Casper.", "Uncle Casper is who the puppy was named after.", "Who was the puppy named after?", "Uncle Casper", "Was the puppy named after Uncle Casper?", "Yes"),
        ("Greta's baby brother is named after their grandfather.", "Their grandfather is who Greta's baby brother is named after.", "Who is the baby named after?", "their grandfather", "Is the baby named after an uncle?", "No")]),
    ("caretaker", "a person feeds, waters or looks after an animal or plant", [
        ("Ilsa feeds the cat every evening.", "Every evening, the cat is fed by Ilsa.", "Who feeds the cat?", "Ilsa", "Does Ilsa feed the cat?", "Yes"),
        ("Grandpa Tobin waters the tomato plants.", "The tomato plants are watered by Grandpa Tobin.", "Who waters the tomato plants?", "Grandpa Tobin", "Does Ilsa water the plants?", "No")]),
    ("opponent", "one person or team plays against another", [
        ("Rafferty played against Noor in the final round.", "In the final round, Noor was Rafferty's opponent.", "Who did Rafferty play against?", "Noor", "Did Rafferty play against Noor?", "Yes"),
        ("The Badgers played the Swifts on Saturday.", "On Saturday, the Swifts were the Badgers' opponent.", "Who did the Badgers play?", "the Swifts", "Did the Badgers play the Owls?", "No")]),
    ("role_in_play", "in a school play or story, a person plays a part", [
        ("In the school play, Kestrel played the king.", "The king in the school play was played by Kestrel.", "Who played the king?", "Kestrel", "Did Kestrel play the king?", "Yes"),
        ("Phoebe played the dragon in the spring show.", "In the spring show, the dragon was played by Phoebe.", "What part did Phoebe play?", "the dragon", "Did Phoebe play the queen?", "No")]),
]

# 8 spares, used only if a kind above loses more than half its rows to the overlap guard (fixed now, before generation)
SPARES = [
    ("gift_for", "a person buys or makes a gift for someone", [
        ("Ottilie knitted a scarf for her father.", "A scarf was knitted by Ottilie for her father.", "Who was the scarf for?", "her father", "Did Ottilie knit a scarf?", "Yes"),
        ("Benno bought a kite for his niece.", "For his niece, Benno bought a kite.", "What did Benno buy?", "a kite", "Did Benno buy the kite for his nephew?", "No")]),
    ("borrowed_item", "a person borrows something from another person", [
        ("Kasimir borrowed a ladder from Mrs. Alder.", "Mrs. Alder lent a ladder to Kasimir.", "What did Kasimir borrow?", "a ladder", "Did Kasimir borrow the ladder from Mrs. Alder?", "Yes"),
        ("Fiora borrowed two pencils from Gil.", "Gil lent two pencils to Fiora.", "Who lent the pencils?", "Gil", "Did Fiora lend pencils to Gil?", "No")]),
    ("pet_kind", "a person has a pet of a certain kind", [
        ("Lysander keeps a tortoise in the garden.", "In the garden, Lysander keeps a tortoise.", "What pet does Lysander keep?", "a tortoise", "Does Lysander keep a parrot?", "No"),
        ("Hedda has two goldfish in a bowl.", "A bowl holds Hedda's two goldfish.", "What pets does Hedda have?", "two goldfish", "Does Hedda have goldfish?", "Yes")]),
    ("ordinal_position", "people stand in a line and one is first, second or last", [
        ("Ambrose stood first in line, and Rilla stood last.", "Rilla stood last in line, behind Ambrose, who stood first.", "Who stood first in line?", "Ambrose", "Did Rilla stand first?", "No"),
        ("Ceci came second in the spelling contest.", "In the spelling contest, Ceci finished in second place.", "What place did Ceci come?", "second", "Did Ceci come second?", "Yes")]),
    ("carried_item", "a person carries or brings an item", [
        ("Valdis carried the lamp up the stairs.", "The lamp was carried up the stairs by Valdis.", "What did Valdis carry?", "the lamp", "Did Valdis carry the lamp?", "Yes"),
        ("Thea brought a basket of pears to the party.", "To the party, Thea brought a basket of pears.", "What did Thea bring?", "a basket of pears", "Did Thea bring a cake?", "No")]),
    ("instrument_played", "a person plays a musical instrument", [
        ("Merrick plays the trumpet in the town band.", "In the town band, Merrick plays the trumpet.", "What does Merrick play?", "the trumpet", "Does Merrick play the drum?", "No"),
        ("Isolde plays the harp.", "The harp is played by Isolde.", "What instrument does Isolde play?", "the harp", "Does Isolde play the harp?", "Yes")]),
    ("gave_name_to", "a person gives a name to something they made", [
        ("Zofia called her new robot Pixel.", "Her new robot was called Pixel by Zofia.", "What did Zofia call her robot?", "Pixel", "Did Zofia call the robot Pixel?", "Yes"),
        ("The sailors called their ship the Gull.", "The ship was called the Gull by the sailors.", "What did the sailors call their ship?", "the Gull", "Did the sailors call the ship the Swan?", "No")]),
    ("sat_next_to", "a person sits or stands next to another person or thing", [
        ("Waldo sat next to the window.", "Next to the window sat Waldo.", "Who sat next to the window?", "Waldo", "Did Waldo sit next to the window?", "Yes"),
        ("Odalys stood beside the old oak.", "Beside the old oak stood Odalys.", "What did Odalys stand beside?", "the old oak", "Did Odalys stand beside a pine?", "No")]),
]

assert len(KINDS) == 60 and len({k[0] for k in KINDS}) == 60, len(KINDS)
