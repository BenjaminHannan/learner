import json
import tempfile
import unittest
from pathlib import Path
from sleepmlx import lessons


def week(target='https://example.org', days=(1, 2, 3)):
    return {'diary': [{'role': 'user', 'day': d, 'turn': i, 'tools': [{'name': 'browser_go', 'args': json.dumps({'url': target})}]} for i, d in enumerate(days)]}


class HabitOfferTests(unittest.TestCase):
    def test_requires_distinct_days_and_drops_secrets(self):
        self.assertEqual(lessons.offer_habits(week(days=(1, 1, 1)), 1), [])
        self.assertEqual(lessons.offer_habits(week('https://example.org/?token=secret123'), 3), [])
        self.assertEqual(lessons.offer_habits(week('https://[broken'), 3), [])
        self.assertEqual(lessons.offer_habits(week(), 3)[0]['days'], 3)

    def test_writes_small_candidate_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            lessons.write_offer_habits(Path(tmp), week(), 3)
            data = json.loads((Path(tmp) / 'habit-candidates.json').read_text())
            self.assertEqual(data['habits'][0]['target'], 'example.org')
            self.assertNotIn('text', data['habits'][0])
