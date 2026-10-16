"""The labeller for game-world test GW-L (addendum A22): the right move for a view, as a pure function of the view text.

label(view) -> (word, reason). It reads only the 9x7 map, the stats and the items of one text view (game/crafter_text.py);
it never touches a world, a seed or the sealed range. Walkable cells are '.', ':' and '_' (grass, sand, path); water, trees,
stone, the table, creatures, plants and arrows block. A move into a blocked cell only turns the player, so "target next to
the player but not faced" is the move toward it, and "next to the player and faced" is `do`.

Priority list (first rule that applies wins; reason in brackets):
 1. asleep -> sleep [sleep]
 2. a zombie in a cell next to the player -> `do` if faced [act], else the move toward it [nav]
 3. drink <= 5 and water in view -> go to it [nav] and `do` [act]
 4. food <= 5 and a cow in view -> go to it [nav] and `do` [act]
 5. crafting [craft]:
      wood >= 2, no table in view, the faced cell is grass/sand/path -> table
      table within one cell of the player (crafter's `nearby`, 3x3), wood >= 1, no wood pickaxe -> wpick
      table within one cell, wood >= 1, no wood sword -> wsword
 6. sapling in hand and the faced cell is grass -> plant [act]
 7. wood < 4 -> nearest tree [nav], `do` when faced [act]
 8. wood pickaxe in hand -> nearest stone [nav], `do` when faced [act]
 9. wander [wander]: keep going the way the player faces if that cell is walkable, else turn to the next walkable side in
    the order up, right, down, left starting after the facing, else noop.
A rule about a target that cannot be reached (no path over walkable cells in view) is skipped.
"Nearest" = the first cell reached by a breadth-first search from the player (neighbours in the order up, right, down, left)
that is next to a target; the label is the first step of that path.
"""
from collections import deque, namedtuple

from game.crafter_text import GRID, ITEM_WORDS, OFFSET

WALKABLE = '.:_'
# (dx, dy) in the order used for ties and for the wander turn: up, right, down, left.
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))
DIR_WORD = {(0, -1): 'up', (1, 0): 'right', (0, 1): 'down', (-1, 0): 'left'}
FACING = {'^': (0, -1), '>': (1, 0), 'v': (0, 1), '<': (-1, 0)}
ITEM_NAME = {short: name for name, short in ITEM_WORDS}

View = namedtuple('View', 'grid facing h f d e asleep dark items')


def parse_view(view):
    """Text view -> View(grid: 7 strings of 9 chars, facing: (dx, dy), h, f, d, e: ints, asleep, dark: bools,
    items: {crafter item name: count})."""
    assert view.startswith('game: '), view
    rows, status, items = view[len('game: '):].split(' | ')
    grid = rows.split('/')
    assert len(grid) == GRID[1] and all(len(r) == GRID[0] for r in grid), view
    facing = FACING[grid[OFFSET[1]][OFFSET[0]]]
    words = status.split(' ')
    stats = {w[0]: int(w[1:]) for w in words if len(w) == 2 and w[0] in 'hfde'}
    inv = {}
    if items != 'none':
        for tok in items.split(' '):
            short = tok.rstrip('0123456789')
            inv[ITEM_NAME[short]] = int(tok[len(short):])
    return View(grid, facing, stats['h'], stats['f'], stats['d'], stats['e'], 'zz' in words, 'dark' in words, inv)


def _cell(v, dx, dy):
    """Map character at offset (dx, dy) from the player, '#' outside the view."""
    x, y = OFFSET[0] + dx, OFFSET[1] + dy
    return v.grid[y][x] if 0 <= x < GRID[0] and 0 <= y < GRID[1] else '#'


def _has(v, chars):
    return any(c in chars for row in v.grid for c in row)


def _near(v, dx, dy, chars):
    """True when a cell next to offset (dx, dy), orthogonally, holds one of chars."""
    return any(_cell(v, dx + a, dy + b) in chars for a, b in DIRS)


def _approach(v, chars):
    """(word, reason) to get to / use the nearest cell holding one of chars, else None.
    Orthogonally next to the player: `do` when faced, else the turn toward it. Otherwise the first step of the shortest
    path over walkable cells to a cell next to a target."""
    for d in DIRS:
        if _cell(v, *d) in chars:
            return ('do', 'act') if d == v.facing else (DIR_WORD[d], 'nav')
    seen = {(0, 0)}
    queue = deque((d, d) for d in DIRS if _cell(v, *d) in WALKABLE)
    seen.update(d for d, _ in queue)
    while queue:
        (x, y), first = queue.popleft()
        if _near(v, x, y, chars):
            return DIR_WORD[first], 'nav'
        for a, b in DIRS:
            nxt = (x + a, y + b)
            if nxt not in seen and _cell(v, *nxt) in WALKABLE:
                seen.add(nxt)
                queue.append((nxt, first))
    return None


def label(view):
    """-> (word, reason) for one text view; see the module docstring for the priority list."""
    v = parse_view(view)
    inv = v.items.get
    if v.asleep:
        return 'sleep', 'sleep'
    for d in DIRS:
        if _cell(v, *d) == 'Z':
            return _approach(v, 'Z')
    if v.d <= 5 and _has(v, '~'):
        r = _approach(v, '~')
        if r:
            return r
    if v.f <= 5 and _has(v, 'C'):
        r = _approach(v, 'C')
        if r:
            return r
    faced = _cell(v, *v.facing)
    wood = inv('wood', 0)
    table_in_view = _has(v, 't')
    in_reach = any(_cell(v, a, b) == 't' for a in (-1, 0, 1) for b in (-1, 0, 1))
    missing = [w for w, tool in (('wpick', 'wood_pickaxe'), ('wsword', 'wood_sword')) if not inv(tool, 0)]
    if wood >= 2 and not table_in_view and faced in WALKABLE:
        return 'table', 'craft'
    if in_reach and wood >= 1 and missing:
        return missing[0], 'craft'
    if inv('sapling', 0) and faced == '.':
        return 'plant', 'act'
    if wood < 4:
        r = _approach(v, 'T')
        if r:
            return r
    if inv('wood_pickaxe', 0):
        r = _approach(v, 'o')
        if r:
            return r
    i = DIRS.index(v.facing)
    for k in range(4):
        d = DIRS[(i + k) % 4]
        if _cell(v, *d) in WALKABLE:
            return DIR_WORD[d], 'wander'
    return 'noop', 'wander'


def oracle_policy():
    """A policy for play.play: prompts -> the labeller's word for each."""
    def pol(prompts):
        return [label(p)[0] for p in prompts]
    return pol
