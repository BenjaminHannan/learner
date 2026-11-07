"""Training-only reverse stages; held-out outcomes never enter this state."""
from . import tasks


class ReverseCurriculum:
    def __init__(self, start_k=1, window=20):
        if type(start_k) is not int or start_k < 1:
            raise ValueError('start_k must be a positive int')
        if type(window) is not int or window < 1:
            raise ValueError('window must be a positive int')
        self.window = window
        self.stages = {kind: min(start_k, tasks.maximum_progress_units(kind))
                       for kind in tasks.MULTI_STEP_TYPES}
        self.pending = {kind: [] for kind in self.stages}
        self.history = []

    def for_kind(self, kind):
        return self.stages.get(kind)

    def record(self, kind, start_k, success):
        if kind not in self.stages or start_k != self.stages[kind]:
            return
        if start_k >= tasks.maximum_progress_units(kind):
            return
        outcomes = self.pending[kind]
        outcomes.append(bool(success))
        if len(outcomes) < self.window:
            return
        successes = sum(outcomes)
        promoted = successes * 10 > self.window * 7
        self.history.append({'kind': kind, 'start_k': start_k,
                             'successes': successes, 'episodes': self.window,
                             'promoted': promoted})
        self.pending[kind] = []
        if promoted:
            self.stages[kind] += 1

    def state_dict(self):
        return {'window': self.window, 'stages': dict(self.stages),
                'pending': {kind: list(outcomes) for kind, outcomes in self.pending.items()},
                'history': list(self.history)}

    def load_state_dict(self, state):
        if state['window'] != self.window:
            raise ValueError('curriculum window differs from checkpoint')
        self.stages = dict(state['stages'])
        self.pending = {kind: list(outcomes) for kind, outcomes in state['pending'].items()}
        self.history = list(state['history'])
