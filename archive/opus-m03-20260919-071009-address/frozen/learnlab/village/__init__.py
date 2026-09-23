"""Village v0 (design/05-village-v0.md): world, oracle, renderer and text stream.

world.py (true state and event semantics) -> scheduler.py (visits, lives, twins;
records as plain dicts) -> render.py / stream.py (text). oracle.py is the observer
that answers from what the stream told; names.py and vocab.py supply the words.
"""
