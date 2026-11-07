"""Shared action encoding for the HANDS gym.

The policy emits the same action dictionary shape used by the real HANDS
pipeline: ``{"kind": "click", "x": 0.5, "y": 0.4, ...}`` with normalised
coordinates and a numeric ``keyCode`` in ``0..255``. The gym policy's heads
use a 24x14 click grid and a safe subset of key codes; this module converts
both to that shared format.
"""

KINDS = ('click', 'drag', 'key', 'scroll')

GRID_WIDTH = 24
GRID_HEIGHT = 14
CELL_COUNT = GRID_WIDTH * GRID_HEIGHT

GYM_KEY_CODES = tuple(
    [ord(ch) for ch in 'abcdefghijklmnopqrstuvwxyz0123456789'] + [32, 128, 129, 130, 131]
)

KEYCODE_TO_KEY = {
    32: 'Space',
    128: 'Enter',
    129: 'Backspace',
    130: 'Tab',
    131: 'Escape',
}


def key_name(code):
    """Playwright key name for a HANDS key code, or None if unsafe/unknown."""
    code = int(code)
    if code in KEYCODE_TO_KEY:
        return KEYCODE_TO_KEY[code]
    if 33 <= code <= 126:
        return chr(code)
    return None


def cell_center(cell):
    """Normalised (x, y) centre of a grid cell."""
    cell = int(cell)
    if not 0 <= cell < CELL_COUNT:
        raise ValueError('cell out of range: %r' % (cell,))
    col = cell % GRID_WIDTH
    row = cell // GRID_WIDTH
    return ((col + 0.5) / GRID_WIDTH, (row + 0.5) / GRID_HEIGHT)


def decode_action(kind_index, start_cell, end_cell, key_index=0, scroll=(0.0, 0.0)):
    """Turn head indices into the shared HANDS action dictionary."""
    kind = KINDS[int(kind_index)]
    x, y = cell_center(start_cell)
    ex, ey = cell_center(end_cell)
    action = {
        'kind': kind,
        'x': x,
        'y': y,
        'endX': ex,
        'endY': ey,
        'keyCode': int(GYM_KEY_CODES[int(key_index)]),
        'dx': float(scroll[0]),
        'dy': float(scroll[1]),
    }
    return action
