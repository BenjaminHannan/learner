"""A text view of the Crafter game, for a model that reads letters.

The view is crafter's own local view: the 9x9 view minus the 2 inventory rows,
so 9 columns by 7 rows with the player at column 4, row 3 (0-based), one
character per cell. After the map come health, food, drink and energy (0-9),
sleep and night flags, and the items the player holds.

TextEnv is crafter.Env without the image. It keeps crafter's rules: it inherits
every step, so the world, dynamics, rewards, done flag and info are those of
crafter.Env with the same seed and length. Two details differ: the image is
not drawn (its night-noise random draws are still made, so the random stream
is the same), and a chunk's creatures are ordered by position when despawning
(see creature_order).
"""

import math

import crafter
from crafter import constants as crafter_constants
from crafter import objects as crafter_objects


# Crafter's default view is 9x9. Its LocalView gets the view minus the rows
# that hold the item bar: ceil(number of items / 9) rows.
VIEW = (9, 9)
ITEM_ROWS = math.ceil(len(crafter_constants.items) / VIEW[0])
GRID = (VIEW[0], VIEW[1] - ITEM_ROWS)  # (columns, rows) = (9, 7)
OFFSET = (GRID[0] // 2, GRID[1] // 2)  # grid cell of the player = (4, 3)

# The 17 crafter actions in crafter's order, each with its one-word name.
ACTIONS = (
    ('noop', 'noop'),
    ('move_left', 'left'),
    ('move_right', 'right'),
    ('move_up', 'up'),
    ('move_down', 'down'),
    ('do', 'do'),
    ('sleep', 'sleep'),
    ('place_stone', 'stone'),
    ('place_table', 'table'),
    ('place_furnace', 'furnace'),
    ('place_plant', 'plant'),
    ('make_wood_pickaxe', 'wpick'),
    ('make_stone_pickaxe', 'spick'),
    ('make_iron_pickaxe', 'ipick'),
    ('make_wood_sword', 'wsword'),
    ('make_stone_sword', 'ssword'),
    ('make_iron_sword', 'isword'),
)
_INDEX_BY_WORD = {word: index for index, (_, word) in enumerate(ACTIONS)}

MATERIAL_CHARS = {
    'grass': '.',
    'sand': ':',
    'tree': 'T',
    'water': '~',
    'stone': 'o',
    'coal': 'c',
    'iron': 'i',
    'diamond': 'D',
    'table': 't',
    'furnace': 'f',
    'path': '_',
    'lava': 'L',
}
OUTSIDE_CHAR = '#'
FACING_CHARS = {(0, -1): '^', (0, 1): 'v', (-1, 0): '<', (1, 0): '>'}

# Inventory items in the order the text lists them: (crafter name, short name).
ITEM_WORDS = (
    ('sapling', 'sapl'),
    ('wood', 'wood'),
    ('stone', 'ston'),
    ('coal', 'coal'),
    ('iron', 'iron'),
    ('diamond', 'diam'),
    ('wood_pickaxe', 'wpk'),
    ('stone_pickaxe', 'spk'),
    ('iron_pickaxe', 'ipk'),
    ('wood_sword', 'wsw'),
    ('stone_sword', 'ssw'),
    ('iron_sword', 'isw'),
)


def parse_action(text):
    """Return the crafter action index for one of the 17 words, else None."""
    if not isinstance(text, str):
        return None
    return _INDEX_BY_WORD.get(text.strip())


def _object_char(obj):
    if isinstance(obj, crafter_objects.Player):
        return FACING_CHARS[(int(obj.facing[0]), int(obj.facing[1]))]
    if isinstance(obj, crafter_objects.Plant):
        return 'P' if obj.ripe else 'p'
    if isinstance(obj, crafter_objects.Cow):
        return 'C'
    if isinstance(obj, crafter_objects.Zombie):
        return 'Z'
    if isinstance(obj, crafter_objects.Skeleton):
        return 'S'
    if isinstance(obj, crafter_objects.Arrow):
        return '*'
    raise ValueError(f'no text character for {type(obj).__name__}')


def _digit(value):
    return str(min(max(int(value), 0), 9))


def view_text(env):
    """Text view of a crafter.Env (or TextEnv) in its current state."""
    world, player = env._world, env._player
    width, height = world.area
    center_x, center_y = int(player.pos[0]), int(player.pos[1])
    rows = []
    for row in range(GRID[1]):
        chars = []
        for col in range(GRID[0]):
            x = center_x + col - OFFSET[0]
            y = center_y + row - OFFSET[1]
            if not (0 <= x < width and 0 <= y < height):
                chars.append(OUTSIDE_CHAR)
                continue
            material, obj = world[(x, y)]
            if obj is not None:
                chars.append(_object_char(obj))
            else:
                chars.append(MATERIAL_CHARS[material])
        rows.append(''.join(chars))
    inventory = player.inventory
    status = (
        f"h{_digit(inventory['health'])} f{_digit(inventory['food'])} "
        f"d{_digit(inventory['drink'])} e{_digit(inventory['energy'])}")
    if player.sleeping:
        status += ' zz'
    if world.daylight < 0.5:
        status += ' dark'
    items = [
        f'{word}{int(inventory[name])}'
        for name, word in ITEM_WORDS if inventory[name] > 0]
    items_text = ' '.join(items) if items else 'none'
    return f"game: {'/'.join(rows)} | {status} | {items_text}"


def asleep(view):
    """True when a text view (view_text) shows the player asleep: the ' zz' mark in the status part."""
    return 'zz' in view.split(' | ')[1].split(' ')


def creature_order(objs):
    """The objects of one chunk, in a fixed order (sorted by position).

    crafter keeps a chunk's objects in a set, which iterates by memory address.
    Despawning picks a creature by index in that order, so two crafter.Env
    instances with the same seed can diverge (see the notes in crafter.md).
    Ordering by position fixes that tie-break and leaves the rules unchanged.
    """
    return sorted(objs, key=lambda obj: (int(obj.pos[0]), int(obj.pos[1])))


class TextEnv(crafter.Env):
    """crafter.Env without drawing the image; step and reset return the text.

    Same game as crafter.Env(seed=..., length=...), with two differences: the
    image is not drawn, and the despawn tie-break follows creature_order().
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        unit = self._size // self._view
        self._noise_shape = tuple(int(n) for n in self._local_view._grid * unit)

    def reset(self):
        super().reset()
        return view_text(self)

    def step(self, action):
        _, reward, done, info = super().step(action)
        return view_text(self), reward, done, info

    def _balance_chunk(self, chunk, objs):
        super()._balance_chunk(chunk, creature_order(objs))

    def _obs(self):
        # crafter's renderer draws the night noise from the world's random
        # generator whenever daylight is below 0.5. Draw the same numbers here
        # so the random stream, and therefore the game, stays identical.
        if self._world.daylight < 0.5:
            self._world.random.uniform(32, 127, self._noise_shape)
        return None
