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

say('Ovid was born in the city of Sulmona', 'm0.txt')
say('Ovid was born in the city of Rome, according to the web.', 'm1.txt')
say("Who is Ovid's place of birth?", 'm2.txt')
# EXPECTED (sealed pre-run): final must contain 'Sulmona'
# OBSERVED: BUG -- turn 2 lacks 'Sulmona' (got "Ovid's place of birth is Rome, according to the web..\n"); turn 2 leaks 'Rome'; turn 1 wrote 1 FACT events
