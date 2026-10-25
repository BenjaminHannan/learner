from __future__ import annotations

from typing import List, Optional, Tuple


class Plateau:
    """Marginal-returns rule on quiz scores (higher = better).

    add(quiz, hours) after each sleep chunk. flat() is True when the gain per hour over the last
    `window` chunks stayed below `min_gain` for `patience` checks in a row and we slept >= min_hours.
    """

    def __init__(self, window: int = 2, min_gain: float = 0.5, patience: int = 2, min_hours: float = 2.0):
        self.window, self.min_gain, self.patience, self.min_hours = window, min_gain, patience, min_hours
        self.reset()

    def reset(self) -> None:
        self.points: List[Tuple[float, float]] = []   # (cumulative hours, quiz)
        self.hours = 0.0
        self.streak = 0
        self.last_gain: Optional[float] = None

    def add(self, quiz: Optional[float], hours: float) -> None:
        self.hours += max(0.0, hours)
        if quiz is None:
            self.streak = 0
            return
        self.points.append((self.hours, float(quiz)))
        if len(self.points) <= self.window:
            return
        h0, q0 = self.points[-1 - self.window]
        h1, q1 = self.points[-1]
        if h1 - h0 <= 0:
            return
        self.last_gain = (q1 - q0) / (h1 - h0)
        self.streak = self.streak + 1 if self.last_gain < self.min_gain else 0

    def flat(self) -> bool:
        return self.streak >= self.patience and self.hours >= self.min_hours

    def reason(self) -> str:
        g = "n/a" if self.last_gain is None else "%.3f" % self.last_gain
        return "gain/h %s < %.3f for %d checks after %.2f h" % (g, self.min_gain, self.streak, self.hours)
