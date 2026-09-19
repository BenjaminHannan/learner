import dataclasses
import itertools
import re
import unittest

from memorylab import tasks


_ALL_NONCE_NAMES = frozenset(
    name
    for pool in tasks.NONCE_NAME_POOLS.values()
    for name in pool
)


def _nonce_words(text):
    return tuple(
        word for word in re.findall(r"[a-z]+", text)
        if word in _ALL_NONCE_NAMES
    )


def _operand_from_query(text):
    match = re.search(r"\[\s*(.*?)\s*\]", text)
    if match is None:
        raise AssertionError(f"query has no list operand: {text!r}")
    body = match.group(1)
    return tuple(body.split()) if body else ()


def _tag_assignment(teaching):
    match = re.fullmatch(
        r"(?:correction : )?the tag of ([a-z]+) is ([a-h]) \.",
        teaching.text,
    )
    if match is None:
        return None
    return match.groups()


class TokenizerTests(unittest.TestCase):
    def test_generated_text_and_targets_have_fixed_vocab_coverage(self):
        vocab_before = dict(tasks.VOCAB)
        size_before = tasks.TOKENIZER.vocab_size

        for split in ("train", "validation", "test"):
            for tier in (1, 2, 3):
                for index in range(12):
                    episode = tasks.generate_episode(split, 100 + index, tier=tier)
                    texts = [teaching.text for teaching in episode.teachings]
                    texts.extend(query.text for query in episode.queries)
                    texts.extend(query.expected for query in episode.queries)
                    for text in texts:
                        with self.subTest(split=split, tier=tier, text=text):
                            encoded = tasks.TOKENIZER.encode(text)
                            self.assertNotIn(tasks.UNK_ID, encoded)

        fresh_name = "zavoke"
        fresh_text = f"the tag of {fresh_name} is a ."
        expected_pieces = (
            "the", "tag", "of", "<name>",
            "@z", "@a", "@v", "@o", "@k", "@e", "</name>",
            "is", "a", ".",
        )
        self.assertNotIn(fresh_name, tasks.VOCAB)
        self.assertEqual(tasks.TOKENIZER.pieces(fresh_text), expected_pieces)
        encoded = tasks.TOKENIZER.encode(fresh_text)
        self.assertNotIn(tasks.UNK_ID, encoded)
        self.assertEqual(
            tuple(tasks.ID_TO_TOKEN[token_id] for token_id in encoded[1:-1]),
            expected_pieces,
        )
        self.assertEqual(tasks.VOCAB, vocab_before)
        self.assertEqual(tasks.TOKENIZER.vocab_size, size_before)

    def test_answer_tokens_decode_to_canonical_report_text(self):
        for split in ("train", "validation", "test"):
            for tier in (1, 2, 3):
                episode = tasks.generate_episode(split, 37, tier=tier)
                for query in episode.queries:
                    encoded = tasks.encode_answer(query.expected)
                    self.assertEqual(
                        tasks.decode_token_ids(encoded),
                        tasks.normalize_text(query.expected),
                    )

        name = tasks.NONCE_NAME_POOLS["test"][0]
        text = f"the tag of {name} is a ."
        self.assertEqual(
            tasks.decode_token_ids(tasks.TOKENIZER.encode(text)),
            tasks.normalize_text(text),
        )


class GenerationTests(unittest.TestCase):
    def test_split_seeds_are_disjoint_and_episodes_are_deterministic(self):
        boundary_seeds = {
            tasks.split_seed(split, index)
            for split in ("train", "validation", "test")
            for index in (0, tasks.EPISODES_PER_SPLIT - 1)
        }
        self.assertEqual(len(boundary_seeds), 6)
        self.assertLess(tasks.split_seed("train", tasks.EPISODES_PER_SPLIT - 1),
                        tasks.split_seed("validation", 0))
        self.assertLess(tasks.split_seed("validation", tasks.EPISODES_PER_SPLIT - 1),
                        tasks.split_seed("test", 0))

        for split in ("train", "validation", "test"):
            for tier in (None, 1, 2, 3):
                for index in (0, 7, 101):
                    with self.subTest(split=split, tier=tier, index=index):
                        first = tasks.generate_episode(split, index, tier=tier)
                        second = tasks.generate_episode(split, index, tier=tier)
                        self.assertEqual(first, second)
                        self.assertEqual(first.seed, tasks.split_seed(split, index))

        generator = tasks.EpisodeGenerator("validation")
        self.assertEqual(
            generator.episodes(11, 4, tier=2),
            tuple(tasks.generate_episode("validation", index, tier=2)
                  for index in range(11, 15)),
        )

    def test_nonce_name_pools_are_registered_composable_and_edit_separated(self):
        pools = tasks.NONCE_NAME_POOLS
        self.assertEqual(set(pools), {"train", "validation", "test"})
        self.assertEqual(
            sum(len(pool) for pool in pools.values()),
            len(set().union(*(set(pool) for pool in pools.values()))),
        )
        for split, pool in pools.items():
            self.assertTrue(pool)
            self.assertEqual(len(pool), len(set(pool)))
            for name in pool:
                self.assertTrue(name.isalpha() and name.islower())
                self.assertTrue(name.startswith(tasks.NONCE_NAME_PREFIXES[split]))
                self.assertNotIn(name, tasks.VOCAB)
                self.assertNotIn(tasks.UNK_ID, tasks.TOKENIZER.encode(name))

        for left, right in itertools.combinations(("train", "validation", "test"), 2):
            minimum = min(
                tasks.levenshtein_distance(left_name, right_name)
                for left_name in pools[left]
                for right_name in pools[right]
            )
            self.assertGreaterEqual(minimum, 2)

        expected_unique = {1: 8, 2: 4, 3: 1}
        for split in ("train", "validation", "test"):
            for tier in (1, 2, 3):
                episode = tasks.generate_episode(split, 91, tier=tier)
                names = set()
                for teaching in episode.teachings:
                    names.update(_nonce_words(teaching.text))
                for query in episode.queries:
                    names.update(_nonce_words(query.text))
                self.assertEqual(len(names), expected_unique[tier])
                self.assertTrue(names.issubset(set(pools[split])))

    def test_feedback_is_minimal_and_model_batches_cannot_carry_targets(self):
        episode = tasks.generate_episode("train", 9, tier=1)
        correction = next(teaching for teaching in episode.teachings if teaching.correction)
        feedback = tasks.accepted_teaching(correction)
        self.assertEqual(feedback, tasks.TeachingFeedback(accepted=True, correction=True))
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(tasks.TeachingFeedback)),
            ("accepted", "correction"),
        )

        query = episode.queries[0]
        self.assertEqual(tasks.self_evaluate(query, query.expected), tasks.SelfEvaluation(True))
        self.assertEqual(tasks.self_evaluate(query, "definitely wrong"), tasks.SelfEvaluation(False))
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(tasks.SelfEvaluation)),
            ("correct",),
        )

        teaching_batch = tasks.batch_teachings(episode.teachings[:2])
        query_batch = tasks.batch_queries(episode.queries[:2])
        expected_batch_fields = ("token_ids", "lengths", "attention_mask")
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(tasks.TokenBatch)),
            expected_batch_fields,
        )
        self.assertEqual(tuple(vars(teaching_batch)), expected_batch_fields)
        self.assertEqual(tuple(vars(query_batch)), expected_batch_fields)
        for object_ in (feedback, tasks.self_evaluate(query, query.expected),
                        teaching_batch, query_batch):
            self.assertNotIn("target", vars(object_))
            self.assertNotIn("expected", vars(object_))

    def test_fact_support_queries_are_evaluator_only_and_procedures_are_deferred(self):
        for tier in (1, 2):
            episode = tasks.generate_episode("train", 17, tier=tier)
            for teaching in episode.teachings:
                support = tasks.support_query_for_teaching(teaching)
                self.assertIsNotNone(support)
                batch = tasks.batch_queries([support])
                self.assertNotIn("expected", vars(batch))
                self.assertEqual(
                    batch.token_ids[0, : batch.lengths[0]].tolist(),
                    support.tokens(),
                )

        procedure = tasks.generate_episode("train", 17, tier=3).teachings[0]
        self.assertIsNone(tasks.support_query_for_teaching(procedure))

        tier2 = tasks.generate_episode("train", 17, tier=2)
        twin = next(teaching for teaching in tier2.teachings if " twin " in teaching.text)
        probe = tasks.relation_value_key_probe(twin)
        self.assertIsNotNone(probe)
        self.assertEqual(probe.expected, "unknown")
        self.assertNotIn("expected", vars(tasks.batch_queries([probe])))


class TierTests(unittest.TestCase):
    def test_tier1_correction_interference_and_unknown_control(self):
        episode = tasks.generate_episode("train", 42, tier=1)
        assignments = []
        final_tags = {}
        for teaching in episode.teachings:
            parsed = _tag_assignment(teaching)
            self.assertIsNotNone(parsed)
            name, tag = parsed
            assignments.append((name, tag, teaching.correction))
            final_tags[name] = tag

        corrections = [item for item in assignments if item[2]]
        self.assertEqual(len(corrections), 1)
        corrected_name, corrected_tag, _ = corrections[0]
        earlier_tags = [tag for name, tag, correction in assignments
                        if name == corrected_name and not correction]
        self.assertEqual(len(earlier_tags), 1)
        self.assertNotEqual(earlier_tags[0], corrected_tag)

        by_purpose = {}
        for query in episode.queries:
            by_purpose.setdefault(query.purpose, []).append(query)
        self.assertEqual(len(by_purpose["correction_paraphrase"]), 2)
        self.assertEqual(len(by_purpose["interference"]), 6)
        self.assertEqual(len(by_purpose["unknown_control"]), 1)

        for query in by_purpose["correction_paraphrase"]:
            self.assertEqual(_nonce_words(query.text), (corrected_name,))
            self.assertEqual(query.expected, final_tags[corrected_name])
        for query in by_purpose["interference"]:
            (name,) = _nonce_words(query.text)
            self.assertNotEqual(name, corrected_name)
            self.assertEqual(query.expected, final_tags[name])

        unknown_query = by_purpose["unknown_control"][0]
        (unknown_name,) = _nonce_words(unknown_query.text)
        self.assertNotIn(unknown_name, final_tags)
        self.assertEqual(unknown_query.expected, "unknown")

    def test_tier2_uses_a_corrected_intermediate_for_two_hop_queries(self):
        episode = tasks.generate_episode("validation", 17, tier=2)
        twin_teaching = next(teaching for teaching in episode.teachings
                             if teaching.text.startswith("the twin of "))
        match = re.fullmatch(r"the twin of ([a-z]+) is ([a-z]+) \.", twin_teaching.text)
        self.assertIsNotNone(match)
        source, intermediate = match.groups()

        intermediate_assignments = [
            (teaching, _tag_assignment(teaching)[1])
            for teaching in episode.teachings
            if _tag_assignment(teaching) is not None
            and _tag_assignment(teaching)[0] == intermediate
        ]
        self.assertEqual(len(intermediate_assignments), 2)
        self.assertFalse(intermediate_assignments[0][0].correction)
        self.assertTrue(intermediate_assignments[1][0].correction)
        old_tag = intermediate_assignments[0][1]
        corrected_tag = intermediate_assignments[1][1]
        self.assertNotEqual(old_tag, corrected_tag)

        two_hop = next(query for query in episode.queries
                       if query.purpose == "corrected_two_hop")
        paraphrase = next(query for query in episode.queries
                          if query.purpose == "two_hop_paraphrase")
        single_hop = next(query for query in episode.queries
                          if query.purpose == "single_hop_control")
        self.assertEqual(_nonce_words(two_hop.text), (source,))
        self.assertEqual(_nonce_words(paraphrase.text), (source,))
        self.assertNotIn(intermediate, two_hop.text)
        self.assertNotIn(intermediate, paraphrase.text)
        self.assertEqual(_nonce_words(single_hop.text), (intermediate,))
        self.assertEqual(two_hop.expected, corrected_tag)
        self.assertEqual(paraphrase.expected, corrected_tag)
        self.assertEqual(single_hop.expected, corrected_tag)

    def test_tier3_edge_semantics_output_capacity_and_non_growth(self):
        five = ("a", "b", "c", "d", "e")
        expected = {
            "reverse": ("e", "d", "c", "b", "a"),
            "drop_first": ("b", "c", "d", "e"),
            "rotate_left": ("b", "c", "d", "e", "a"),
            "swap_pairs": ("b", "a", "d", "c", "e"),
        }
        singleton_expected = {
            "reverse": ("a",),
            "drop_first": (),
            "rotate_left": ("a",),
            "swap_pairs": ("a",),
        }
        for primitive in tasks.PRIMITIVES:
            with self.subTest(primitive=primitive):
                self.assertEqual(tasks.apply_primitive(primitive, ()), ())
                self.assertEqual(tasks.apply_primitive(primitive, ("a",)),
                                 singleton_expected[primitive])
                self.assertEqual(tasks.apply_primitive(primitive, five), expected[primitive])
                for length in range(tasks.MAX_LIST_LENGTH + 1):
                    operand = tuple(range(length))
                    self.assertLessEqual(len(tasks.apply_primitive(primitive, operand)), length)

        for program in itertools.product(tasks.PRIMITIVES, repeat=3):
            for length in range(tasks.MAX_LIST_LENGTH + 1):
                operand = tuple(range(length))
                self.assertLessEqual(len(tasks.apply_program(program, operand)), length)

        max_answer = tasks.format_list(five)
        encoded = tasks.encode_answer(max_answer)
        self.assertEqual(encoded[-1], tasks.EOS_ID)
        self.assertNotIn(tasks.UNK_ID, encoded)
        self.assertEqual(sum(tasks.ID_TO_TOKEN[token_id] in five for token_id in encoded), 5)

        for split in ("train", "validation", "test"):
            episode = tasks.generate_episode(split, 23, tier=3)
            by_purpose = {query.purpose: query for query in episode.queries}
            self.assertNotIn("empty_semantics", by_purpose)
            self.assertNotIn("singleton_semantics", by_purpose)
            self.assertEqual(len(_operand_from_query(by_purpose["novel_operand"].text)), 5)
            for query in episode.queries:
                operand = _operand_from_query(query.text)
                self.assertIn(operand, tasks.TIER3_OPERAND_POOLS[split])
                self.assertLessEqual(len(operand), tasks.MAX_LIST_LENGTH)
                self.assertNotIn(
                    tasks.UNK_ID,
                    tasks.TOKENIZER.encode(tasks.format_list(operand)),
                )
                result = tasks.apply_program(query.program, operand)
                self.assertEqual(query.expected, tasks.format_list(result))
                self.assertLessEqual(len(result), tasks.MAX_LIST_LENGTH)

    def test_tier3_operand_pools_are_disjoint_and_generated_queries_stay_in_split(self):
        pools = {split: set(pool) for split, pool in tasks.TIER3_OPERAND_POOLS.items()}
        self.assertTrue(pools["train"].isdisjoint(pools["validation"]))
        self.assertTrue(pools["train"].isdisjoint(pools["test"]))
        self.assertTrue(pools["validation"].isdisjoint(pools["test"]))

        observed = {split: set() for split in pools}
        for split, pool in pools.items():
            self.assertTrue(pool)
            for operand in pool:
                self.assertGreater(len(operand), 0)
                self.assertLessEqual(len(operand), tasks.MAX_LIST_LENGTH)
                self.assertTrue(set(operand).issubset(set(tasks.SYMBOLS)))
                self.assertNotIn(
                    tasks.UNK_ID,
                    tasks.TOKENIZER.encode(tasks.format_list(operand)),
                )
            for index in range(48):
                episode = tasks.generate_episode(split, index, tier=3)
                for query in episode.queries:
                    operand = _operand_from_query(query.text)
                    self.assertIn(operand, pool)
                    observed[split].add(operand)

        self.assertTrue(observed["train"].isdisjoint(observed["validation"]))
        self.assertTrue(observed["train"].isdisjoint(observed["test"]))
        self.assertTrue(observed["validation"].isdisjoint(observed["test"]))

    def test_tier3_holds_out_t5_and_keeps_semantic_classes_disjoint(self):
        classes = tasks.SEMANTIC_PROCEDURE_CLASSES
        self.assertTrue(classes["train"])
        self.assertTrue(classes["validation"])
        self.assertTrue(classes["test"])
        self.assertTrue(classes["train"].isdisjoint(classes["validation"]))
        self.assertTrue(classes["train"].isdisjoint(classes["test"]))
        self.assertTrue(classes["validation"].isdisjoint(classes["test"]))

        for split in ("train", "validation", "test"):
            for index in range(24):
                episode = tasks.generate_episode(split, index, tier=3)
                teaching = episode.teachings[0]
                if split == "test":
                    self.assertIn(" is : ", teaching.text)
                    self.assertIn(" ; after that ", teaching.text)
                else:
                    self.assertNotIn(" is : ", teaching.text)

                programs = [teaching.program]
                programs.extend(query.program for query in episode.queries)
                for program in programs:
                    self.assertIn(tasks.semantic_signature(program), classes[split])


class AuditTests(unittest.TestCase):
    def test_audit_rejects_forged_teaching_and_every_query_composition(self):
        valid = [tasks.generate_episode(split, 5, tier=3)
                 for split in ("train", "validation", "test")]
        self.assertTrue(tasks.audit_split_separation(valid)["ok"])

        for source, destination in itertools.permutations(
                ("train", "validation", "test"), 2):
            foreign = next(
                tasks.generate_episode(source, index, tier=3)
                for index in range(100)
                if any(query.purpose == "query_time_composition"
                       for query in tasks.generate_episode(source, index, tier=3).queries)
            )
            forged = tasks.Episode(
                split=destination,
                episode=foreign.episode,
                seed=tasks.split_seed(destination, foreign.episode),
                tier=3,
                teachings=foreign.teachings,
                queries=foreign.queries,
            )
            with self.subTest(source=source, destination=destination):
                with self.assertRaises(ValueError) as caught:
                    tasks.audit_split_separation((forged,))
                message = str(caught.exception)
                self.assertIn("teaching[0]", message)
                self.assertIn(f"reserved for {source}", message)
                for index, query in enumerate(foreign.queries):
                    self.assertIsNotNone(query.program)
                    self.assertIn(f"query[{index}]", message)

    def test_audit_rejects_forged_nonce_name_overlap(self):
        train = tasks.generate_episode("train", 12, tier=3)
        validation = tasks.generate_episode("validation", 12, tier=3)
        train_name = _nonce_words(train.teachings[0].text)[0]
        validation_name = _nonce_words(validation.teachings[0].text)[0]

        forged = dataclasses.replace(
            validation,
            teachings=tuple(
                dataclasses.replace(
                    teaching,
                    text=re.sub(
                        rf"\b{re.escape(validation_name)}\b",
                        train_name,
                        teaching.text,
                    ),
                )
                for teaching in validation.teachings
            ),
            queries=tuple(
                dataclasses.replace(
                    query,
                    text=re.sub(
                        rf"\b{re.escape(validation_name)}\b",
                        train_name,
                        query.text,
                    ),
                )
                for query in validation.queries
            ),
        )
        with self.assertRaises(ValueError) as caught:
            tasks.audit_split_separation((train, forged))
        message = str(caught.exception)
        self.assertIn("nonce name", message)
        self.assertIn("reserved for train", message)
        self.assertIn("observed nonce-name overlap", message)

    def test_audit_rejects_forged_operand_overlap(self):
        train = tasks.generate_episode("train", 13, tier=3)
        validation = tasks.generate_episode("validation", 13, tier=3)
        train_operand = _operand_from_query(train.queries[0].text)
        original = validation.queries[0]
        expected = tasks.format_list(tasks.apply_program(original.program, train_operand))
        forged_query = dataclasses.replace(
            original,
            text=re.sub(
                r"\[\s*.*?\s*\]",
                tasks.format_list(train_operand),
                original.text,
                count=1,
            ),
            expected=expected,
        )
        forged = dataclasses.replace(
            validation,
            queries=(forged_query,) + validation.queries[1:],
        )

        with self.assertRaises(ValueError) as caught:
            tasks.audit_split_separation((train, forged))
        message = str(caught.exception)
        self.assertIn("uses operand", message)
        self.assertIn("reserved for train", message)
        self.assertIn("observed operand overlap", message)


class BatchingTests(unittest.TestCase):
    def test_padding_masks_and_target_eos(self):
        batch = tasks.pad_sequences(((11, 12), (21,)), max_length=4)
        self.assertEqual(batch.token_ids.tolist(), [[11, 12, tasks.PAD_ID, tasks.PAD_ID],
                                                   [21, tasks.PAD_ID, tasks.PAD_ID, tasks.PAD_ID]])
        self.assertEqual(batch.lengths.tolist(), [2, 1])
        self.assertEqual(batch.attention_mask.tolist(),
                         [[True, True, False, False], [True, False, False, False]])

        queries = (
            tasks.Query("what is the tag of zavu ?", "a"),
            tasks.Query("what is the tag of kefi ?", "[ a b c d e ]"),
        )
        model_batch = tasks.batch_queries(queries)
        target_batch = tasks.batch_query_targets(queries)
        for row, length in enumerate(model_batch.lengths.tolist()):
            self.assertEqual(model_batch.token_ids[row, 0].item(), tasks.BOS_ID)
            self.assertEqual(model_batch.token_ids[row, length - 1].item(), tasks.EOS_ID)
        for row, length in enumerate(target_batch.lengths.tolist()):
            tokens = target_batch.token_ids[row, :length].tolist()
            self.assertNotEqual(tokens[0], tasks.BOS_ID)
            self.assertEqual(tokens[-1], tasks.EOS_ID)
            self.assertEqual(tokens.count(tasks.EOS_ID), 1)
            self.assertTrue(bool(target_batch.attention_mask[row, :length].all()))
            self.assertTrue(bool((~target_batch.attention_mask[row, length:]).all()))
            self.assertTrue(bool((target_batch.token_ids[row, length:] == tasks.PAD_ID).all()))


if __name__ == "__main__":
    unittest.main()
