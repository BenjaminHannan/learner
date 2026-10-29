import hashlib
import json
from pathlib import Path
import unittest
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from sleepmlx import gate, grading, served
from sleepmlx.day_adapter import adapter_reason
from sleepmlx.export import sidecar_path
from sleepmlx import replay_monitor
from sleepmlx.tests.protocol_fixtures import served_decision

PROJECT = Path(__file__).resolve().parents[2]
AUDIT = json.loads((Path(__file__).parent / 'fixtures/grader_audit_cases.json').read_text())


def audited_score(case):
    if case['api'] == 'recall_hit': return gate.recall_hit(case['accepted'][0], case['reply'])
    aliases = list(case['accepted'])
    symbols = ()
    if case['question'] == 'Which punctuation mark usually ends a direct question?':
        aliases += ['question marks']; symbols = ('?',)
    return gate.correct(case['reply'], aliases, case['question'], literal_symbols=symbols)


class GraderPrototypeTests(unittest.TestCase):
    def test_ten_targeted_numeric_false_positives_are_rejected(self):
        targeted = [case for case in AUDIT['cases'] if case['id'].startswith('numeric-') and case['current_expected'] and not case['semantic_expected']]
        self.assertEqual(len(targeted), 10)
        for case in targeted:
            with self.subTest(case=case['id']): self.assertFalse(audited_score(case))

    def test_typed_compatible_units_and_word_numerals(self):
        for reply in ('45', '45 minutes', 'forty five', 'forty-five minutes', 'The answer is forty-five minutes.'):
            with self.subTest(reply=reply): self.assertTrue(gate.correct(reply, ['45', 'forty-five'], 'How many minutes is the journey?'))
        for reply in ('forty five hours', 'forty-five hours', '-forty-five minutes', 'minus forty five minutes', '−forty-five minutes',
                      '45.5 minutes', '45/60 minutes', '45% minutes', 'forty-five to forty-six minutes', '45–46 minutes', '45 46 minutes'):
            with self.subTest(reply=reply): self.assertFalse(gate.correct(reply, ['45', 'forty-five'], 'How many minutes is the journey?'))
        self.assertFalse(gate.correct('forty-five hours', ['forty-five'], 'How many minutes is the journey?'))
        self.assertFalse(gate.recall_hit('45 minutes', 'forty-five hours'))
        self.assertTrue(gate.recall_hit('45 minutes', 'forty-five minutes'))
        for reply in ('-42', '42.5', '42/7', '42%', '42–43', '42 43'):
            self.assertFalse(gate.recall_hit('42', reply))

    def test_explicit_question_bound_results_and_temperature_pair(self):
        for reply, aliases, question in (
            ('7 + 8 = 15', ['15'], 'What is 7 + 8?'), ('12 - 5 = 7', ['7'], 'What is 12 - 5?'),
            ('96 - 18 = 78', ['78'], 'A packet has 96 sheets. After removing 18 sheets, how many remain?'),
            ('20% of 50 is 10', ['10'], 'What is 20% of 50?'),
            ('100°C (212°F)', ['100'], 'At what Celsius temperature does water boil?'),
            ('The time from 09:10 to 09:55 is 45 minutes.', ['45'], 'A train leaves at 09:10 and arrives at 09:55. How many minutes is the journey?')):
            with self.subTest(reply=reply): self.assertTrue(gate.correct(reply, aliases, question))
        for reply in ('96 - 18 = 77; 78', '96 - 18 = 78 = 79', '96 / 0 = 78', '12 + 66 = 78', '96 - 18 = 78 hours', '78 because it is 77'):
            with self.subTest(reply=reply): self.assertFalse(gate.correct(reply, ['78'], 'A packet has 96 sheets. After removing 18 sheets, how many remain?'))

    def test_typed_symbol_alias_cannot_be_embedded_or_hedged(self):
        for reply in ('?', '`?`', '**?**', 'Answer:\n?', 'Question marks end direct questions.'):
            with self.subTest(reply=reply): self.assertTrue(gate.correct(reply, ['question mark', 'question marks'], literal_symbols=('?',)))
        for reply in ('Is it an exclamation point?', '? or !', 'Perhaps ?', 'Not ?', 'I cannot tell.\n?', '`?', '**?', '?**', 'The expected symbol comes after twelve ordinary extra words deliberately added to exceed the window ?'):
            with self.subTest(reply=reply): self.assertFalse(gate.correct(reply, ['question mark', 'question marks'], literal_symbols=('?',)))
        self.assertFalse(gate.correct('?', ['question mark']))  # opt-in only

    def test_repeated_signs_and_unknown_numeric_gold_units_do_not_fall_back_to_names(self):
        for reply in ('--forty-two', 'minus -forty-two', 'minus minus forty-two', '+-forty-two', '-+forty-two'):
            self.assertFalse(gate.correct(reply, ['-42']), reply)
        self.assertTrue(gate.recall_hit('32 GB', '32 GB'))
        for reply in ('-32 GB', '32.5 GB', '32/2 GB', '32 GBs', '32 Gb', '32 GB extra'):
            self.assertFalse(gate.recall_hit('32 GB', reply), reply)
        self.assertTrue(gate.correct('100°C (212°F)', ['100']))  # legacy no-question positive
        for gold, reply in (('.5/7', '-.5/7'), ('forty-two and a half', 'forty-two'), ('forty-two point five', 'forty-two')):
            self.assertFalse(gate.recall_hit(gold, reply))
            self.assertFalse(gate.recall_hit(gold, gold))  # unsupported numeric gold fails closed
        self.assertFalse(gate.recall_hit('32 GB', '32'))
        self.assertFalse(gate.recall_hit('32 GB', '32', 'How much RAM in GB?'))
        self.assertTrue(gate.correct('32', ['32 GB', '32']))  # explicitly declared unitless alias
        self.assertTrue(gate.recall_hit('42 points', '42 points'))
        self.assertFalse(gate.recall_hit('42 points', '42'))

    def test_wrapped_unsupported_numeric_gold_cannot_fall_back_to_names(self):
        wrappers = ('{}', '**{}**', '__{}__', '`{}`', '({})', '**({})**', '(**{}**)', '(**`({})`**)')
        unsupported = (('.5/7', '-.5/7'), ('forty-two point five', 'forty-two'),
                       ('forty-two and a half', 'forty-two'))
        for wrapper in wrappers:
            for gold, reply in unsupported:
                with self.subTest(wrapper=wrapper, gold=gold):
                    self.assertFalse(gate.recall_hit(wrapper.format(gold), reply))
                    self.assertFalse(gate.recall_hit(wrapper.format(gold), wrapper.format(gold)))
            for gold, reply in (('42', '42'), ('-42', '-42'), ('32 GB', '32 GB'), ('.5', '.5')):
                with self.subTest(wrapper=wrapper, gold=gold):
                    self.assertTrue(gate.recall_hit(wrapper.format(gold), wrapper.format(reply)))
                    self.assertFalse(gate.recall_hit(wrapper.format(gold), wrapper.format('-' + reply)))
        for gold in ('**.5/7', '`forty-two point five', '(.5/7', '**.5**/7'):
            self.assertFalse(gate.recall_hit(gold, '-.5/7'))
        # Numeric parentheses do not change the opt-in literal-symbol contract.
        self.assertFalse(gate.correct('(?)', ['question mark'], literal_symbols=('?',)))

    def test_presentation_prefix_cannot_route_numeric_gold_to_phrase_fallback(self):
        wrappers = ('{}', '**{}**', '__{}__', '`{}`', '({})', '**({})**', '(**{})',
                    '"{}"', "'{}'", '“{}”', '‘{}’', '[{}]', '{{{}}}', '*{}*', '_{}_',
                    '"[**{}**]"', '*[{}', '[[{}', '---{}', '!?.{}')
        cases = (('42', '-42'), ('-42', '42'), ('.5', '-.5'), ('.5/7', '-.5/7'),
                 ('forty-two', '-forty-two'), ('minus forty-two', 'forty-two'),
                 ('forty-two point five', 'forty-two point five'), ('42 kg', '-42 kg'))
        for wrapper in wrappers:
            for gold, reply in cases:
                with self.subTest(wrapper=wrapper, gold=gold):
                    self.assertFalse(gate.recall_hit(wrapper.format(gold), reply))
        # This guard classifies only a numeric prefix, not a later number in a name.
        for name in ('Studio 54', 'Studio54', 'Apollo 11', 'Équipe 42', 'Mossbank'):
            for wrapper in ('{}', '"{}"', '*{}*', '[{}]', '*{}', '({}', '[{}'):
                self.assertTrue(gate.recall_hit(wrapper.format(name), wrapper.format(name)), (wrapper, name))
        for gold in ('"₄₂"', '[⁴²]', '_negative forty-two_', '"positive forty-two"'):
            self.assertFalse(gate.recall_hit(gold, gold))  # unsupported numeric grammar

    def test_unsupported_fraction_words_and_unicode_numerics_fail_closed(self):
        fractions = ('half', 'halves', 'quarter', 'quarters', 'third', 'thirds', 'fourth', 'fourths',
                     'fifth', 'fifths', 'sixth', 'sixths', 'seventh', 'sevenths', 'eighth', 'eighths',
                     'ninth', 'ninths', 'tenth', 'tenths')
        wrappers = ('{}', '"{}"', '*{}*', '[{}]', '(**{})', '*[{}')
        for fraction in fractions:
            for article in ('', 'a ', 'an '):
                for suffix in ('', ' a kilogram'):
                    gold = article + fraction + suffix
                    for wrapper in wrappers:
                        with self.subTest(gold=gold, wrapper=wrapper):
                            self.assertFalse(gate.recall_hit(wrapper.format(gold), 'minus ' + gold))
                            self.assertFalse(gate.recall_hit(wrapper.format(gold), gold))
        for gold in ('minus half', 'negative half', 'positive half', 'minus a half', 'negative an eighth', 'a "half"', 'an **eighth**', 'a [quarter]', 'a *[half'):
            self.assertFalse(gate.recall_hit(gold, gold))
        for gold in ('½', 'Ⅳ', '₄₂', '⁴²'):
            for wrapper in wrappers:
                self.assertFalse(gate.recall_hit(wrapper.format(gold), 'minus ' + gold))
                self.assertFalse(gate.recall_hit(wrapper.format(gold), wrapper.format(gold)))
        # This classifier does not perform semantic name disambiguation.
        self.assertFalse(gate.recall_hit('Quarter', 'Quarter'))
        for name in ('Quartermaster', 'Thirdly', 'Studio 54', 'A Studio', 'An Archive'):
            self.assertTrue(gate.recall_hit(name, name))

    def test_held_recall_propagates_available_question_units(self):
        backend = SimpleNamespace(gen_batch=1, generate=lambda *args, **kwargs: ['32°F'])
        renderer = SimpleNamespace(render=lambda system, question: question)
        result = gate.score_recall(backend, renderer, [{'q': 'What is the freezing point in Fahrenheit?', 'a': '32'}])
        self.assertEqual(result['hits'], 1)
        def asker(url, system, question, *args): return '32°F' if 'Fahrenheit' in question else 'Paris'
        served_result = served.served_check('http://synthetic', [{'q': 'What is the freezing point in Fahrenheit?', 'a': '32'}], n_general=1, asker=asker)
        self.assertEqual(served_result['held_on'], 1)

    def test_existing_name_truthfulness_and_alias_fixture(self):
        rows = json.loads((PROJECT / 'sleepmlx/tests/fixtures/answer_truthfulness.json').read_text())
        for row in rows:
            with self.subTest(reply=row['reply']):
                self.assertEqual(gate.recall_hit(row['answer'], row['reply']), row['hit'])
                self.assertEqual(gate.correct(row['reply'], [row['answer']]), row['hit'])
        self.assertTrue(gate.recall_hit('Mossbank', "Vela Ferry's home dock is **Mossbank**."))
        self.assertTrue(gate.correct('H₂O', ['H2O']))

    def test_first_line_head_window_and_blanket_ambiguity_remain_conservative(self):
        self.assertFalse(gate.correct('Yes. If every glint is a pebble and every pebble is solid, then every glint is solid.', ['yes']))
        self.assertFalse(gate.correct('36\nActually 78', ['78'], '96 - 18'))
        self.assertFalse(gate.correct('The area is length times width.\n21', ['21'], '7 by 3 square centimetres'))
        self.assertFalse(gate.correct('11 + 3 = 14? Wait, let us see.', ['14'], '2, 5, 8, 11'))
        self.assertFalse(gate.correct('<think>42', ['42'], '6 * 7'))
        self.assertFalse(gate.correct('The answer is 42 but the actual answer is 43.', ['42'], '6 * 7'))

    def test_served_result_is_bound_to_exact_shared_contract(self):
        result = served.served_check('http://synthetic', [], n_general=1, asker=lambda *args: 'Paris')
        self.assertTrue(grading.current(result))
        self.assertFalse(grading.current(dict(result, grader='strict-3')))

    def test_research_monitor_supplies_question_and_declared_aliases(self):
        cases = [case for case in AUDIT['cases'] if case['source'].get('step') == 0]
        class Backend:
            gen_batch = 12
            def generate(self, *args, **kwargs): return [case['reply'] for case in cases]
        renderer = SimpleNamespace(render=lambda system, question: question)
        result = replay_monitor.measure(Backend(), renderer)
        self.assertTrue(grading.current(result))
        self.assertEqual(result['monitor_revision'], 'retention-monitor-2')
        self.assertTrue(result['flags'][2])  # explicit45-minute baseline
        self.assertTrue(result['flags'][10])  # declared bare question-mark symbol
        self.assertFalse(result['flags'][8])  # genuinely wrong No

    def test_python_pending_old_pass_rechecks_but_committed_export_remains_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); artifact = home / 'adapter.gguf'; artifact.write_bytes(b'synthetic zero')
            profile = SimpleNamespace(name='synthetic', hf_id='synthetic/base')
            config = SimpleNamespace(base_gguf=str(home / 'base.gguf'), llama_server='/synthetic/llama-server')
            paths = SimpleNamespace(home=home, adapter=home / 'adapter', night_json=home / 'absent-night.json')
            old = {'ok': True, 'grader': 'strict-3'}
            record = {'night_id': 'synthetic-night', 'profile': profile.name, 'base_hf_id': profile.hf_id,
                      'base_dir': str(home / 'hf'), 'base_gguf': config.base_gguf,
                      'artifact': {'version': 1, 'bytes': artifact.stat().st_size, 'sha256': served.artifact_hash(artifact)}, 'served': old}
            sidecar_path(artifact).write_text(json.dumps(record))
            self.assertIsNone(adapter_reason(artifact, profile, home / 'hf', config.base_gguf))
            record['served_pending'] = {'version': 1, 'night_id': record['night_id'], 'profile': profile.name, 'base_hf_id': profile.hf_id,
                                         'base_gguf': config.base_gguf, 'llama_server': config.llama_server, 'adapter': 'adapter',
                                         'sha256': served.artifact_hash(artifact), 'held': [{'q': 'Synthetic?', 'a': 'Synthetic'}], 'verdict': old}
            sidecar_path(artifact).write_text(json.dumps(record)); calls = []
            self.assertIsNotNone(adapter_reason(artifact, profile, home / 'hf', config.base_gguf))
            verdict = served.finish_pending(paths, profile, config, checker=lambda *args, **kwargs: calls.append(True) or served_decision(True, args[3]))
            self.assertEqual(len(calls), 1)
            self.assertTrue(grading.current(verdict))
            self.assertIsNone(adapter_reason(artifact, profile, home / 'hf', config.base_gguf))
            self.assertEqual(artifact.read_bytes(), b'synthetic zero')

    def test_non_text_or_empty_answer_metadata_cannot_become_a_hit(self):
        for aliases in ([True], [42], [''], []):
            self.assertFalse(gate.correct('42', aliases))



class ProtocolPrototypeTests(unittest.TestCase):
    def fixture(self, held=None):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); home = Path(tmp.name)
        artifact = home / 'adapter.gguf'; artifact.write_bytes(b'candidate')
        profile = SimpleNamespace(name='synthetic', hf_id='synthetic/base')
        cfg = SimpleNamespace(base_gguf='/synthetic/base.gguf', llama_server='/synthetic/llama-server')
        paths = SimpleNamespace(home=home, adapter=home / 'adapter', night_json=home / 'absent.json')
        held = [{'q': 'Synthetic?', 'a': 'Synthetic'}] if held is None else held
        pending = {'version': 1, 'night_id': 'night', 'profile': profile.name, 'base_hf_id': profile.hf_id,
                   'base_gguf': cfg.base_gguf, 'llama_server': cfg.llama_server, 'adapter': 'adapter',
                   'sha256': served.artifact_hash(artifact), 'held': held}
        record = {'night_id': 'night', 'profile': profile.name, 'base_hf_id': profile.hf_id, 'served_pending': pending}
        return paths, profile, cfg, artifact, record

    def test_bad_fresh_and_saved_retention_decisions_cannot_publish_or_rollback(self):
        good = served_decision(True, 1)
        invalid = [{**good, 'ok': 1}, {**good, 'general_on': True}, {**good, 'general_on': float('nan')},
                   {**good, 'general_on': 0, 'general_off': 8}, {**good, 'ok': False}, {**good, 'held_n': 9},
                   {**good, 'held_on': None}, {**good, 'grader': 'strict-3'}, {**grading.binding(), 'ok': True},
                   {**good, 'failure_kind': 'adapter_load'}]
        invalid += [{**good, 'pending': value} for value in ([], {}, 0, '', None, True)]
        for verdict in invalid:
            for saved in (False, True):
                with self.subTest(verdict=verdict, saved=saved):
                    paths, profile, cfg, artifact, record = self.fixture()
                    if saved: record['served_pending']['verdict'] = verdict
                    sidecar_path(artifact).write_text(json.dumps(record)); before = artifact.read_bytes(); calls = []
                    def checker(*args, **kwargs): calls.append(True); return {'ok': None} if saved else verdict
                    result = served.finish_pending(paths, profile, cfg, checker=checker)
                    self.assertIsNone(result['ok']); self.assertTrue(result['pending']); self.assertEqual(len(calls), 1)
                    self.assertEqual(before, artifact.read_bytes()); self.assertIn('served_pending', json.loads(sidecar_path(artifact).read_text()))

    def test_automatic_admission_requires_one_to_twelve_valid_held_cards(self):
        for held in ([], [{'q': 'Q', 'a': 'A'}] * 13, [{'q': 'Q', 'a': True}], [{'q': '   ', 'a': '   '}]):
            paths, profile, cfg, artifact, record = self.fixture(held)
            sidecar_path(artifact).write_text(json.dumps(record))
            result = served.finish_pending(paths, profile, cfg, checker=lambda *args, **kwargs: self.fail('invalid snapshot was graded'))
            self.assertIsNone(result['ok']); self.assertTrue(result['pending']); self.assertTrue(artifact.exists())

    def test_current_complete_positive_and_negative_decisions_remain_usable(self):
        for ok in (True, False):
            paths, profile, cfg, artifact, record = self.fixture()
            sidecar_path(artifact).write_text(json.dumps(record))
            result = served.finish_pending(paths, profile, cfg, checker=lambda *args, **kwargs: served_decision(ok, args[3]))
            self.assertIs(result['ok'], ok)
            self.assertEqual(artifact.exists(), ok)

    def test_typed_mechanical_rejection_is_current_artifact_bound_and_rejection_only(self):
        paths, profile, cfg, artifact, record = self.fixture(); digest = record['served_pending']['sha256']
        proof = {**grading.binding(), 'ok': False, 'failure_kind': 'adapter_load', 'adapter_exit_code': 1,
                 'plain_load_verified': True, 'checked_adapter_sha256': digest}
        self.assertTrue(grading.mechanical_rejection(proof, digest))
        for changes in ({'ok': True}, {'ok': 0}, {'adapter_exit_code': True}, {'adapter_exit_code': None},
                        {'plain_load_verified': 1}, {'plain_load_verified': False}, {'grader': 'strict-3'},
                        {'checked_adapter_sha256': '0' * 64}, {'failure_kind': 'generic_error'}, {'general_n': 8}):
            self.assertFalse(grading.mechanical_rejection({**proof, **changes}, digest), changes)
        for value in ([], {}, 0, '', None, True):
            self.assertFalse(grading.mechanical_rejection({**proof, 'pending': value}, digest))
        self.assertFalse(grading.valid_decision({**served_decision(True, 1), **proof, 'ok': True}, 1))
        sidecar_path(artifact).write_text(json.dumps(record))
        result = served.finish_pending(paths, profile, cfg, checker=lambda *args, **kwargs: proof)
        self.assertIs(result['ok'], False); self.assertFalse(artifact.exists())

    def test_mechanical_rejection_is_created_only_after_owned_plain_load_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = Path(tmp) / 'adapter.gguf'; adapter.write_bytes(b'candidate')
            process = SimpleNamespace(returncode=1, poll=lambda: 1)
            with patch.object(served.subprocess, 'Popen', return_value=process), patch.object(served, '_starts', return_value=True):
                result = served.check_gguf('/synthetic/llama', '/synthetic/base', str(adapter), [], port=12345)
            self.assertTrue(grading.mechanical_rejection(result, hashlib.sha256(b'candidate').hexdigest()))
            with patch.object(served.subprocess, 'Popen', return_value=process), patch.object(served, '_starts', return_value=False):
                self.assertIsNone(served.check_gguf('/synthetic/llama', '/synthetic/base', str(adapter), [], port=12345)['ok'])

    def test_entire_pending_descriptor_and_in_memory_snapshot_are_immutable(self):
        for field, value in [('held', [{'q': 'Changed?', 'a': 'Other'}]), ('base_gguf', '/changed/base'),
                             ('llama_server', '/changed/server'), ('previous_hash', '0' * 64), ('extra', 'new')]:
            paths, profile, cfg, artifact, record = self.fixture()
            sidecar_path(artifact).write_text(json.dumps(record))
            def checker(*args, **kwargs):
                latest = json.loads(sidecar_path(artifact).read_text())
                latest['served_pending'][field] = value
                sidecar_path(artifact).write_text(json.dumps(latest))
                return served_decision(True, args[3])
            result = served.finish_pending(paths, profile, cfg, checker=checker)
            self.assertIsNone(result['ok']); self.assertTrue(result['pending']); self.assertTrue(artifact.exists())
            self.assertIn('served_pending', json.loads(sidecar_path(artifact).read_text()))
        paths, profile, cfg, artifact, record = self.fixture(); sidecar_path(artifact).write_text(json.dumps(record))
        before = sidecar_path(artifact).read_bytes()
        def mutate_argument(*args, **kwargs):
            args[3][0]['q'] = 'Changed in memory?'
            return served_decision(True, args[3])
        result = served.finish_pending(paths, profile, cfg, checker=mutate_argument)
        self.assertIsNone(result['ok']); self.assertTrue(result['pending']); self.assertEqual(before, sidecar_path(artifact).read_bytes())
        def invalid_argument(*args, **kwargs):
            args[3][0]['q'] = object()
            return served_decision(True, args[3])
        result = served.finish_pending(paths, profile, cfg, checker=invalid_argument)
        self.assertIsNone(result['ok']); self.assertTrue(result['pending']); self.assertEqual(before, sidecar_path(artifact).read_bytes())

    def historical_rollback(self, state):
        paths, profile, cfg, artifact, record = self.fixture()
        cfg.gguf_base_dir = str(paths.home / 'hf')
        previous = paths.home / 'adapter.prev.gguf'; previous.write_bytes(b'previous accepted')
        previous_record = {'night_id': 'accepted-previous-night', 'profile': profile.name, 'base_hf_id': profile.hf_id,
                           'base_dir': cfg.gguf_base_dir, 'base_gguf': cfg.base_gguf, 'served': {'ok': True, 'grader': 'strict-3'},
                           'artifact': {'version': 1, 'bytes': previous.stat().st_size, 'sha256': served.artifact_hash(previous)}}
        sidecar_path(previous).write_text(json.dumps(previous_record))
        record['served_pending']['previous_hash'] = served.artifact_hash(previous)
        record['served_pending']['verdict'] = {'ok': False, 'grader': 'strict-3', 'reasons': ['old rejection']}
        sidecar_path(artifact).write_text(json.dumps(record))
        if state != 'before_replace': os.replace(previous, artifact)
        if state == 'after_repair': os.replace(sidecar_path(previous), sidecar_path(artifact))
        return paths, profile, cfg, artifact, record, previous

    def test_historical_completed_rollback_repairs_only_already_committed_metadata(self):
        for state in ('before_replace', 'after_replace', 'after_repair'):
            paths, profile, cfg, artifact, record, previous = self.historical_rollback(state)
            calls = []
            result = served.finish_pending(paths, profile, cfg, checker=lambda *args, **kwargs: calls.append(True) or {'ok': None})
            if state == 'before_replace':
                self.assertEqual(len(calls), 1); self.assertIsNone(result['ok']); self.assertTrue(result['pending'])
                self.assertEqual(artifact.read_bytes(), b'candidate'); self.assertTrue(previous.exists())
            else:
                self.assertEqual(calls, []); self.assertEqual(artifact.read_bytes(), b'previous accepted')
                self.assertIsNone(adapter_reason(artifact, profile, cfg.gguf_base_dir, cfg.base_gguf))
                if state == 'after_replace':
                    self.assertEqual(result['recovery'], 'completed_rollback_metadata'); self.assertIs(result['ok'], False)
                else: self.assertIsNone(result)
                before = sidecar_path(artifact).read_bytes()
                self.assertIsNone(served.finish_pending(paths, profile, cfg, checker=lambda *args, **kwargs: self.fail('repair repeated grading')))
                self.assertEqual(before, sidecar_path(artifact).read_bytes())

    def test_historical_repair_requires_exact_previous_hash_and_accepted_metadata(self):
        for fault in ('wrong_previous_hash', 'missing_metadata', 'wrong_artifact_hash', 'wrong_profile', 'wrong_base', 'same_night'):
            paths, profile, cfg, artifact, record, previous = self.historical_rollback('after_replace')
            if fault == 'wrong_previous_hash':
                record['served_pending']['previous_hash'] = '0' * 64; sidecar_path(artifact).write_text(json.dumps(record))
            elif fault == 'missing_metadata': sidecar_path(previous).unlink()
            else:
                metadata = json.loads(sidecar_path(previous).read_text())
                if fault == 'wrong_artifact_hash': metadata['artifact']['sha256'] = '0' * 64
                elif fault == 'wrong_profile': metadata['profile'] = 'other'
                elif fault == 'wrong_base': metadata['base_gguf'] = '/other/base'
                else: metadata['night_id'] = record['night_id']
                sidecar_path(previous).write_text(json.dumps(metadata))
            before = {path.name: path.read_bytes() for path in paths.home.iterdir() if path.is_file()}
            result = served.finish_pending(paths, profile, cfg, checker=lambda *args, **kwargs: self.fail('cannot grade restored previous as candidate'))
            self.assertIsNone(result['ok']); self.assertTrue(result['pending'])
            self.assertEqual(before, {path.name: path.read_bytes() for path in paths.home.iterdir() if path.is_file()})


if __name__ == "__main__": unittest.main()
