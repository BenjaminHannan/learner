"""Synthetic complete checker responses matching the current admission protocol."""
from sleepmlx import grading


def served_decision(ok, held, reasons=None):
    count = len(held) if isinstance(held, list) else held
    return {**grading.binding(), 'ok': ok, 'reasons': reasons if reasons is not None else ([] if ok else ['worse']),
            'general_n': 8, 'general_on': 8 if ok else 0, 'general_off': 8,
            'held_n': count, 'held_on': count if ok else 0, 'held_off': count}
