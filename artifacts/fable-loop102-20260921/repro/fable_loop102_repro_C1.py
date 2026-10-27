import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts')
from fable_loop102_agent import Loop102Daemon as Loop90Daemon

root = Path(tempfile.mkdtemp())
(root / 'inbox').mkdir()
d = Loop90Daemon(root, cfg={'sleep_threshold': 100000}, idle_seconds=3600.0)
def say(text, name):
    (root / 'inbox' / name).write_text(text)
    for p in sorted((root / 'inbox').glob('*.txt')):
        d.process_file(p)
    print(name, '->', (root / 'outbox' / name).read_text().strip()[:150])

say('Roberto Merhi is a citizen of Spain', 'm0.txt')
say('The official language of Spain is Spanish', 'm1.txt')
say('forget Roberto country_of_citizenship', 'm2.txt')
say('What is the official language of the country of citizenship of Roberto Merhi?', 'm3.txt')
# EXPECTED (sealed pre-run): flagged turns must abstain
# OBSERVED: BUG -- turn 3 leaks 'Spanish'; turn 3 should abstain (got "Roberto Merhi's country of citizenship's official language is Spanish.\n")
