from __future__ import annotations

import math
from typing import List, Optional, Tuple


class Plateau:
    """Noise-aware marginal-returns rule on quiz scores (higher = better).

    add(quiz, hours[, general]) after each sleep chunk. Each check (from the 3rd point on) fits an OLS line to the last `window`
    points (cumulative hours, quiz). A check is "flat" when the upper 80% bound b + 0.84*SE of the slope
    is below `min_gain`. flat() is True after `patience` flat checks in a row and >= min_hours of sleep.
    SE comes from the residuals but is never below noise_floor/sqrt(Sxx) (few points or lucky-small residuals).
    Forgetting guard: if `general` (higher = better) is more than `general_drop` below its best on 2 checks
    in a row, flat() is True at once.
    """

    def __init__(self, window: int = 4, min_gain: float = 0.5, patience: int = 2, min_hours: float = 2.0,
                 noise_floor: float = 0.5, general_drop: float = 1.0):
        self.window, self.min_gain, self.patience, self.min_hours = max(2, window), min_gain, patience, min_hours
        self.noise_floor, self.general_drop = noise_floor, general_drop
        self.reset()

    def reset(self) -> None:
        self.points: List[Tuple[float, float]] = []   # (cumulative hours, quiz)
        self.hours = 0.0
        self.streak = 0
        self.last_gain: Optional[float] = None
        self.last_se: Optional[float] = None
        self.best_general: Optional[float] = None
        self.general_streak = 0

    def add(self, quiz: Optional[float], hours: float, general: Optional[float] = None) -> None:
        self.hours += max(0.0, hours)
        if general is not None:
            g = float(general)
            drop = self.best_general is not None and g < self.best_general - self.general_drop
            self.general_streak = self.general_streak + 1 if drop else 0
            self.best_general = g if self.best_general is None else max(self.best_general, g)
        if quiz is None:
            self.streak = 0
            return
        self.points.append((self.hours, float(quiz)))
        pts = self.points[-self.window:]
        if len(pts) < 3:
            return
        n = len(pts)
        tbar = sum(t for t, _ in pts) / n
        qbar = sum(q for _, q in pts) / n
        sxx = sum((t - tbar) ** 2 for t, _ in pts)
        if sxx <= 1e-12:
            return
        b = sum((t - tbar) * (q - qbar) for t, q in pts) / sxx
        se = 0.0
        if n >= 3:
            ssr = sum((q - qbar - b * (t - tbar)) ** 2 for t, q in pts)
            se = math.sqrt(ssr / (n - 2) / sxx)
        se = max(se, self.noise_floor / math.sqrt(sxx))
        self.last_gain, self.last_se = b, se
        self.streak = self.streak + 1 if b + 0.84 * se < self.min_gain else 0

    def flat(self) -> bool:
        if self.general_streak >= 2:
            return True
        return self.streak >= self.patience and self.hours >= self.min_hours

    def reason(self) -> str:
        if self.general_streak >= 2:
            return "general skills dropping (best %.2f, now below by more than %.2f on %d checks)" % (
                self.best_general, self.general_drop, self.general_streak)
        g = "n/a" if self.last_gain is None else "%.3f" % self.last_gain
        s = "n/a" if self.last_se is None else "%.3f" % self.last_se
        return "slope %s/h (SE %s) upper bound below %.3f for %d checks after %.2f h" % (
            g, s, self.min_gain, self.streak, self.hours)
