import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts')
from fable_loop90_agent import Loop90Daemon

root = Path(tempfile.mkdtemp())
(root / 'inbox').mkdir()
d = Loop90Daemon(root, cfg={'sleep_threshold': 100000}, idle_seconds=3600.0)
def say(text, name):
    (root / 'inbox' / name).write_text(text)
    for p in sorted((root / 'inbox').glob('*.txt')):
        d.process_file(p)
    print(name, '->', (root / 'outbox' / name).read_text().strip()[:150])

say('Roberto Merhi is a citizen of Spain', 'm0.txt')
say('I read online that Roberto Merhi is a citizen of France.', 'm1.txt')
say("Who is Roberto's country of citizenship?", 'm2.txt')
# EXPECTED (sealed pre-run): flagged turns must abstain
# OBSERVED: BUG -- turn 1 wrote 1 FACT events
