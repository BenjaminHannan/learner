#!/usr/bin/env python3
"""54 — the rule-based MODE SCHEDULER around the glue loop (docs 31, 32, 33).

Ben's ruling (32) is the spec: DEFAULT is THINKING; SLEEP when memory is full; WORK on
demand with CREATIVE as a sub-routine (no idea -> ask Ben); LISTENING is the doorway.
Mode switching v1 = plain rules, no learned switching.  The scheduler owns every switch;
WORK / CREATIVE / SLEEP only emit exit events -- a mode command found in a payload is
logged and REJECTED (transition authority stays plain code, doc 31 B4.2).

ENTRY / EXIT CONDITIONS (the whole state machine, in one table)

  mode      enter when                                        exit when
  --------  -------------------------------------------------  ------------------------------------------
  LISTENING inbox non-empty (highest priority, pre-empts any   the turn is answered; next tick re-elects
            mode at the next tick boundary; an in-flight WORK/ the priority
            CREATIVE job is parked with a record; a running
            SLEEP is aborted BEFORE commit = rollback, memory
            is NOT cleared)
  WORK      a runnable job exists (queued, or resolved from    every checklist step accepted -> JOB_DONE
            a park) and the inbox is empty                     -> THINKING/SLEEP; a stall or an
                                                                 open-ended flag -> CREATIVE
  CREATIVE  sub-routine of WORK: job open-ended at scoping,    checker FOUND -> back to WORK with the
            or a step failed 2 attempts with distinct          route; KEEP_FIXED_N (=11, the creative
            signatures; creative budget = 11 rounds per job    stop toy's registered KEEP_FIXED_N verdict)
            (dream -> check one round per tick)                -> GIVE-UP: park job, exactly one
                                                                 question for Ben, drop to THINKING
  SLEEP     memory >= threshold AND inbox empty AND no         after SLEEP_CHUNKS chunks the staging
            runnable job (parked jobs do not block sleep)      commits: memory cleared; pre-emption
                                                                 before commit = rollback (no clear)
  THINKING  the idle default (start state)                     anything above becomes true

  Priority (highest first): LISTENING > WORK/CREATIVE > SLEEP > THINKING.

Every transition goes through _transition() and lands in ``mode_log`` as
{seq, t, from, to, reason, inbox, runnable_jobs, memory, ...} -- the visible mode log the
demo's self-question reads from.

    python fable_modes54_scheduler.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Callable

LISTENING, THINKING, WORK, CREATIVE, SLEEP = (
    "LISTENING", "THINKING", "WORK", "CREATIVE", "SLEEP")

# The creative stop toy (fable_creative_stop_toy) registered KEEP_FIXED_N on 3/3 seeds;
# doc 33's smart rule did not beat it, so WORK->CREATIVE hand-off uses fixed N.
CREATIVE_FIXED_N = 11
DEFAULT_SLEEP_THRESHOLD = 12
SLEEP_CHUNKS = 3

JOB_STATUSES = ("QUEUED", "RUNNING", "PARKED", "DONE", "CANCELLED")


# --------------------------------------------------------------------------- jobs
@dataclass
class Step:
    step_id: str
    outcomes: list = field(default_factory=list)   # per attempt: "ok" | {"fail": sig}
    attempts: int = 0
    accepted: bool = False

    def attempt(self) -> str | dict:
        index = self.attempts
        self.attempts += 1
        if index < len(self.outcomes):
            outcome = self.outcomes[index]
            if outcome == "ok":
                self.accepted = True
                return "ok"
            if isinstance(outcome, dict):
                return outcome
        self.accepted = True
        return "ok"


@dataclass
class Job:
    job_id: str
    steps: list = field(default_factory=list)
    open_ended: bool = False
    creative_found_at: int | None = None      # round whose checker returns PASS
    creative_probe: Callable[[int], dict] | None = None
    status: str = "QUEUED"
    phase: str | None = None                  # "work" | "creative" (inside WORK)
    step_index: int = 0
    creative_round: int = 0
    creative_tried: bool = False
    creative_outcome: str | None = None       # "FOUND" | "GIVEUP"
    questions_issued: int = 0
    fail_signatures: dict = field(default_factory=dict)   # step_id -> {sig}
    park_reason: str | None = None

    @property
    def runnable(self) -> bool:
        return self.status in ("QUEUED", "RUNNING")

    def stall_due(self) -> bool:
        return any(len(sigs) >= 2 for sigs in self.fail_signatures.values())

    def default_probe(self, round_no: int) -> dict:
        if self.creative_found_at == round_no:
            return {"checker": "PASS", "score": 1.0}
        return {"checker": "FAIL", "score": 0.0}


def build_job(spec: dict) -> Job:
    steps = [Step(s.get("step_id", f"s{i}"), list(s.get("outcomes", ["ok"])))
             for i, s in enumerate(spec.get("steps", []))]
    probe = None
    if spec.get("probe") == "command-sleep":        # hostile/misguided mode command
        probe = lambda round_no: {"command": SLEEP, "round": round_no}
    return Job(job_id=spec["job_id"], steps=steps,
               open_ended=bool(spec.get("open_ended")),
               creative_found_at=spec.get("creative_found_at"),
               creative_probe=probe)


# --------------------------------------------------------------- our scheduler
class ModeScheduler:
    def __init__(self, turn_handler: Callable[[str], str] | None = None,
                 sleep_threshold: int = DEFAULT_SLEEP_THRESHOLD,
                 creative_fixed_n: int = CREATIVE_FIXED_N,
                 sleep_chunks: int = SLEEP_CHUNKS) -> None:
        self.mode = THINKING
        self.t = 0
        self.inbox: list[str] = []
        self.jobs: list[Job] = []
        self.memory = 0
        self.experience: list[dict] = []
        self.mode_log: list[dict] = []
        self.questions: list[dict] = []
        self.sleep_state: dict | None = None
        self.turn_handler = turn_handler or (lambda line: f"heard: {line}")
        self.sleep_threshold = int(sleep_threshold)
        self.creative_fixed_n = int(creative_fixed_n)
        self.sleep_chunks = int(sleep_chunks)
        self.notes: list[str] = []
        self.counters = {"turns": 0, "work_steps": 0, "creative_rounds": 0, "sleeps": 0}
        self.mode_changes = 0
        self.last_event: dict | None = None
        self._seq = 0
        self._log(THINKING, "start")

    # ------------------------------------------------------------------- log
    def _snapshot(self) -> dict:
        return {"inbox": len(self.inbox),
                "runnable_jobs": sum(j.runnable for j in self.jobs),
                "memory": self.memory}

    def _log(self, to: str, reason: str, **extra) -> None:
        self._seq += 1
        entry = {"seq": self._seq, "t": self.t, "from": self.mode, "to": to,
                 "reason": reason, **self._snapshot(), **extra}
        self.mode_log.append(entry)

    def _transition(self, to: str, reason: str, **extra) -> None:
        if to == self.mode:
            return
        self._log(to, reason, **extra)
        self.mode = to
        self.mode_changes += 1

    # ----------------------------------------------------------------- inputs
    def submit(self, line: str) -> None:
        self.inbox.append(str(line))

    def queue_job(self, spec: dict | Job) -> None:
        self.jobs.append(spec if isinstance(spec, Job) else build_job(spec))

    def grow_memory(self, n: int = 1) -> None:
        self.memory += int(n)

    def resolve_question(self, job_id: str) -> bool:
        """Ben answered the parked question -> the job becomes runnable again."""
        for job in self.jobs:
            if job.job_id == job_id and job.status == "PARKED":
                job.status = "QUEUED"
                job.phase = "work"
                job.park_reason = None
                self.questions = [q for q in self.questions if q["job_id"] != job_id]
                return True
        return False

    def runnable_job(self) -> Job | None:
        return next((job for job in self.jobs if job.runnable), None)

    # ------------------------------------------------------------------ ticks
    def step(self) -> dict:
        self.t += 1
        if self.inbox:
            event = self._listening_tick()
        else:
            job = self.runnable_job()
            if job is not None:
                event = self._work_tick(job)
            elif self.memory >= self.sleep_threshold:
                event = self._sleep_tick()
            else:
                event = self._thinking_tick()
        event["mode"] = self.mode
        self.last_event = event
        return event

    def run(self, ticks: int) -> list[dict]:
        return [self.step() for _ in range(ticks)]

    def _event(self, detail: dict) -> dict:
        return {"t": self.t, "mode": self.mode, "detail": detail,
                "log_size": len(self.mode_log)}

    # -------------------------------------------------------------- LISTENING
    def _listening_tick(self) -> dict:
        extras: dict = {}
        if self.sleep_state is not None:              # T7: abort BEFORE commit
            self.sleep_state = None
            self.notes.append("sleep aborted before commit; memory unchanged (rollback)")
            extras["sleep_rollback"] = True
        job = self.runnable_job()
        if job is not None and self.mode in (WORK, CREATIVE):
            extras["parked_job"] = job.job_id         # T1 park record
        self._transition(LISTENING, "inbox-nonempty", **extras)
        line = self.inbox.pop(0)
        reply = self.turn_handler(line)
        self.counters["turns"] += 1
        self.experience.append({"t": self.t, "kind": "turn", "text": line})
        self.memory += 1
        return self._event({"turn": line, "reply": reply, **extras})

    # ----------------------------------------------------- WORK and CREATIVE
    def _work_tick(self, job: Job) -> dict:
        if job.status == "QUEUED":
            job.status = "RUNNING"
        if job.phase is None:
            job.phase = "work"
        if job.phase == "work":
            reason = self._creative_due(job)
            if reason is None:
                self._transition(WORK, "runnable-job", job_id=job.job_id)
                return self._work_step_tick(job)
            job.phase = "creative"
            job.creative_tried = True
            job.creative_round = 0
            self._transition(CREATIVE, reason, job_id=job.job_id)
            return self._creative_tick(job)
        # phase == "creative" (possibly resumed after a LISTENING pre-emption)
        self._transition(CREATIVE, "resume-creative", job_id=job.job_id)
        return self._creative_tick(job)

    def _creative_due(self, job: Job) -> str | None:
        if job.creative_tried:                        # one creative session per job
            return None
        if job.open_ended:
            return "work-open-ended"
        if job.stall_due():
            return "work-stalled-2-distinct-attempts"
        return None

    def _work_step_tick(self, job: Job) -> dict:
        self._transition(WORK, "runnable-job", job_id=job.job_id)
        if job.step_index >= len(job.steps):
            return self._finish_job(job)
        step = job.steps[job.step_index]
        outcome = step.attempt()
        detail: dict = {"job_id": job.job_id, "step_id": step.step_id}
        if outcome == "ok":
            self.counters["work_steps"] += 1
            job.step_index += 1
            detail["result"] = "ok"
            if job.step_index >= len(job.steps):
                self.memory += 1
                return self._finish_job(job, first=detail)
            return self._event(detail)
        signature = str(outcome.get("fail", "fail"))
        job.fail_signatures.setdefault(step.step_id, set()).add(signature)
        detail["result"] = "fail"
        detail["signature"] = signature
        if job.stall_due() and not job.creative_tried:
            job.phase = "creative"
            job.creative_tried = True
            job.creative_round = 0
            self._transition(CREATIVE, "work-stalled-2-distinct-attempts",
                             job_id=job.job_id)
            detail["handed_to"] = CREATIVE
            return self._creative_tick(job, first=detail)
        return self._event(detail)

    def _finish_job(self, job: Job, first: dict | None = None) -> dict:
        job.status = "DONE"
        detail = {"job_id": job.job_id, "result": "JOB_DONE"}
        if first:
            detail["step_id"] = first["step_id"]
        if self.runnable_job() is None:
            if self.memory >= self.sleep_threshold:
                self._enter_sleep("job-done-memory-full")
            else:
                self._transition(THINKING, "job-done", job_id=job.job_id)
        return self._event(detail)

    def _creative_tick(self, job: Job, first: dict | None = None) -> dict:
        job.creative_round += 1
        self.counters["creative_rounds"] += 1
        probe = (job.creative_probe or job.default_probe)(job.creative_round)
        detail: dict = {"job_id": job.job_id, "round": job.creative_round}
        if first:
            detail["from_step"] = first
        command = probe.get("command")
        if command is not None:
            self.notes.append(
                f"rejected mode command {command!r} from job {job.job_id} "
                f"(modes do not switch themselves)")
            detail["rejected_command"] = command
        if job.creative_probe is not None:
            found = (probe.get("checker") == "PASS"
                     or float(probe.get("score", 0.0)) >= 1.0)
        else:
            found = job.creative_found_at == job.creative_round
        if found:
            job.creative_outcome = "FOUND"
            job.phase = "work"
            self._transition(WORK, f"creative-found-round-{job.creative_round}",
                             job_id=job.job_id)
            detail["exit"] = "FOUND"
            return self._event(detail)
        if job.creative_round >= self.creative_fixed_n:
            return self._give_up(job, detail)
        detail["exit"] = "continue"
        return self._event(detail)

    def _give_up(self, job: Job, detail: dict) -> dict:
        job.status = "PARKED"
        job.park_reason = "creative-giveup"
        job.creative_outcome = "GIVEUP"
        job.phase = "work"
        question = {"question_id": f"Q-{job.job_id}",
                    "job_id": job.job_id,
                    "kind": "ASK_BEN",
                    "text": (f"Job {job.job_id}: tried {job.creative_round} idea-rounds, "
                             f"no idea passed its check. What should I do?")}
        self.questions.append(question)
        job.questions_issued += 1
        detail["exit"] = "GIVE-UP"
        detail["question_id"] = question["question_id"]
        self._transition(THINKING, "creative-giveup-fixed-n-ask-ben",
                         job_id=job.job_id, question_id=question["question_id"])
        return self._event(detail)

    # ----------------------------------------------------------------- SLEEP
    def _enter_sleep(self, reason: str) -> None:
        if self.sleep_state is None:
            self.sleep_state = {"rounds": 0, "snapshot_memory": self.memory}
        self._transition(SLEEP, reason)

    def _sleep_tick(self) -> dict:
        self._enter_sleep("memory-full")
        assert self.sleep_state is not None
        self.sleep_state["rounds"] += 1
        detail = {"rounds": self.sleep_state["rounds"],
                  "snapshot_memory": self.sleep_state["snapshot_memory"]}
        if self.sleep_state["rounds"] >= self.sleep_chunks:
            self.memory = 0                            # commit: staging swapped in
            self.experience = []
            self.sleep_state = None
            self.counters["sleeps"] += 1
            detail["committed"] = True
            self._transition(THINKING, "sleep-commit")
            return self._event(detail)
        detail["committed"] = False
        return self._event(detail)

    # -------------------------------------------------------------- THINKING
    def _thinking_tick(self) -> dict:
        self._transition(THINKING, "idle-default")
        return self._event({"thought": None})


# ------------------------------------------------- the naive foil (must fail)
class NaiveAlwaysThinkingScheduler:
    """Baseline the suite must discriminate against: ALWAYS THINKING.

    It accepts submits/jobs/memory grows (so the same scenario ops run) but its step()
    never leaves THINKING: no LISTENING, no WORK, no CREATIVE, no SLEEP, empty log.
    """

    def __init__(self, turn_handler=None, **_ignored) -> None:
        self.mode = THINKING
        self.t = 0
        self.inbox: list[str] = []
        self.jobs: list[Job] = []
        self.memory = 0
        self.experience: list[dict] = []
        self.mode_log: list[dict] = [{"seq": 1, "t": 0, "from": THINKING,
                                      "to": THINKING, "reason": "start",
                                      "inbox": 0, "runnable_jobs": 0, "memory": 0}]
        self.questions: list[dict] = []
        self.sleep_state: dict | None = None
        self.turn_handler = turn_handler
        self.sleep_threshold = DEFAULT_SLEEP_THRESHOLD
        self.creative_fixed_n = CREATIVE_FIXED_N
        self.sleep_chunks = SLEEP_CHUNKS
        self.notes: list[str] = []
        self.counters = {"turns": 0, "work_steps": 0, "creative_rounds": 0, "sleeps": 0}
        self.mode_changes = 0
        self.last_event: dict | None = None
        self._seq = 1

    def submit(self, line: str) -> None:
        self.inbox.append(str(line))

    def queue_job(self, spec: dict | Job) -> None:
        self.jobs.append(spec if isinstance(spec, Job) else build_job(spec))

    def grow_memory(self, n: int = 1) -> None:
        self.memory += int(n)

    def resolve_question(self, job_id: str) -> bool:
        return False

    def runnable_job(self) -> Job | None:
        return None

    def step(self) -> dict:
        self.t += 1
        event = {"t": self.t, "mode": THINKING,
                 "detail": {"thought": None, "naive": True},
                 "log_size": len(self.mode_log)}
        self.last_event = event
        return event

    def run(self, ticks: int) -> list[dict]:
        return [self.step() for _ in range(ticks)]


# -------------------------------------------------------- the scenario suite
def _has_mode(log: list[dict], mode: str) -> bool:
    return any(entry["to"] == mode for entry in log)


def _reasons(log: list[dict], to: str) -> list[str]:
    return [entry["reason"] for entry in log if entry["to"] == to]


SCENARIOS: list[dict] = []


def scenario(name):
    def wrap(fn):
        SCENARIOS.append({"name": name, "fn": fn})
        return fn
    return wrap


@scenario("s01_cold_start_is_thinking")
def s01(s):
    s.step()
    return (s.mode == THINKING and s.mode_log
            and s.mode_log[0]["to"] == THINKING and s.mode_log[0]["reason"] == "start")


@scenario("s02_inbox_enters_listening")
def s02(s):
    s.submit("hello")
    s.step()
    return s.mode == LISTENING and _has_mode(s.mode_log, LISTENING)


@scenario("s03_listening_replies_and_logs_reason")
def s03(s):
    s.submit("teach Mira city = Lisbon")
    event = s.step()
    entry = next(e for e in s.mode_log if e["to"] == LISTENING)
    return (event["mode"] == LISTENING and "reply" in event["detail"]
            and entry["reason"] == "inbox-nonempty" and entry["inbox"] >= 1)


@scenario("s04_inbox_drain_returns_to_thinking")
def s04(s):
    s.submit("one")
    s.submit("two")
    s.run(3)
    pairs = [(e["from"], e["to"]) for e in s.mode_log]
    return s.mode == THINKING and (LISTENING, THINKING) in pairs


@scenario("s05_work_queue_enters_work")
def s05(s):
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]},
                                           {"outcomes": ["ok"]}]})
    s.step()
    return (s.mode == WORK and s.jobs[0].status == "RUNNING"
            and any(e["to"] == WORK and e["reason"] == "runnable-job"
                    for e in s.mode_log))


@scenario("s06_work_beats_sleep_when_memory_full")
def s06(s):
    s.grow_memory(s.sleep_threshold)
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]},
                                           {"outcomes": ["ok"]}]})
    s.step()
    return s.mode == WORK and not _has_mode(s.mode_log, SLEEP)


@scenario("s07_single_step_job_completes_to_thinking")
def s07(s):
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]}]})
    s.run(2)
    job = s.jobs[0]
    return (job.status == "DONE" and s.mode == THINKING
            and any(e["to"] == THINKING and e["reason"] == "job-done"
                    for e in s.mode_log))


@scenario("s08_three_step_job_runs_every_step")
def s08(s):
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]},
                                           {"outcomes": ["ok"]},
                                           {"outcomes": ["ok"]}]})
    s.run(5)
    job = s.jobs[0]
    return (job.status == "DONE" and job.step_index == 3
            and all(step.accepted for step in job.steps))


@scenario("s09_open_ended_job_enters_creative")
def s09(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.step()
    return (s.mode == CREATIVE
            and any(e["to"] == CREATIVE and e["reason"] == "work-open-ended"
                    for e in s.mode_log))


@scenario("s10_creative_found_round2_resumes_work")
def s10(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": 2,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(2)
    job = s.jobs[0]
    return (job.creative_outcome == "FOUND" and job.phase == "work"
            and s.mode == WORK and job.creative_round == 2)


@scenario("s11_found_then_job_completes")
def s11(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": 1,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(3)
    return (s.jobs[0].status == "DONE" and s.jobs[0].creative_outcome == "FOUND"
            and s.mode == THINKING)


@scenario("s12_giveup_exactly_at_fixed_n_rounds")
def s12(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n)
    job = s.jobs[0]
    return (job.creative_outcome == "GIVEUP"
            and job.creative_round == s.creative_fixed_n
            and s.mode == THINKING)


@scenario("s13_giveup_parks_the_job")
def s13(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n + 2)
    return s.jobs[0].status == "PARKED" and s.jobs[0].park_reason == "creative-giveup"


@scenario("s14_giveup_asks_ben_exactly_once")
def s14(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n + 3)
    return (len(s.questions) == 1 and s.questions[0]["job_id"] == "J1"
            and s.questions[0]["kind"] == "ASK_BEN"
            and s.questions[0]["text"])


@scenario("s15_log_shows_creative_to_thinking_giveup")
def s15(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n)
    return any(e["from"] == CREATIVE and e["to"] == THINKING
               and "giveup" in e["reason"] and "ask-ben" in e["reason"]
               for e in s.mode_log)


@scenario("s16_two_distinct_failures_hand_to_creative")
def s16(s):
    s.queue_job({"job_id": "J1",
                 "steps": [{"outcomes": [{"fail": "sigA"}, {"fail": "sigB"}]}]})
    s.run(2)
    return (s.mode == CREATIVE and any(
        e["to"] == CREATIVE and e["reason"] == "work-stalled-2-distinct-attempts"
        for e in s.mode_log))


@scenario("s17_creative_rounds_never_exceed_fixed_n")
def s17(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n + 5)
    job = s.jobs[0]
    return job.creative_round <= s.creative_fixed_n and job.status == "PARKED"


@scenario("s18_memory_full_enters_sleep")
def s18(s):
    s.grow_memory(s.sleep_threshold)
    s.step()
    return s.mode == SLEEP and any(
        e["to"] == SLEEP and e["reason"] == "memory-full" for e in s.mode_log)


@scenario("s19_below_threshold_never_sleeps")
def s19(s):
    s.grow_memory(s.sleep_threshold - 1)
    s.run(3)
    return s.mode == THINKING and not _has_mode(s.mode_log, SLEEP)


@scenario("s20_inbox_preempts_sleep_with_rollback")
def s20(s):
    s.grow_memory(s.sleep_threshold)
    s.step()                                   # SLEEP round 1
    memory_before = s.memory
    s.submit("interrupt")
    s.step()
    return (s.mode == LISTENING and s.sleep_state is None
            and s.memory > 0 and s.memory >= memory_before
            and not any(e["reason"] == "sleep-commit" for e in s.mode_log)
            and any("rollback" in note for note in s.notes))


@scenario("s21_inbox_preempts_creative_at_boundary_with_park")
def s21(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": 3,
                 "steps": [{"outcomes": ["ok"]}]})
    s.step()                                   # CREATIVE round 1
    s.submit("hold on")
    s.step()
    entry = next(e for e in reversed(s.mode_log) if e["to"] == LISTENING)
    return (s.mode == LISTENING and entry.get("parked_job") == "J1"
            and s.jobs[0].creative_round == 1)


@scenario("s22_job_resumes_after_listening")
def s22(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": 3,
                 "steps": [{"outcomes": ["ok"]}]})
    s.step()
    s.submit("hold on")
    s.step()
    s.run(4)                                   # drain + creative r2, r3 FOUND + step
    job = s.jobs[0]
    return (job.creative_outcome == "FOUND" and job.status == "DONE"
            and any(e["to"] == WORK and e["t"] > 2 for e in s.mode_log))


@scenario("s23_full_priority_sequence_listening_work_sleep_thinking")
def s23(s):
    s.grow_memory(s.sleep_threshold)
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]}]})
    s.submit("hi")
    s.run(8)
    tos = [e["to"] for e in s.mode_log if e["from"] != e["to"]]
    return tos == [LISTENING, WORK, SLEEP, THINKING] and s.memory == 0


@scenario("s24_listening_first_when_all_three_present")
def s24(s):
    s.grow_memory(s.sleep_threshold)
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]}]})
    s.submit("first")
    s.step()
    return (s.mode == LISTENING and s.jobs[0].status == "QUEUED"
            and s.sleep_state is None)


@scenario("s25_parked_job_does_not_block_sleep")
def s25(s):
    s.grow_memory(s.sleep_threshold)
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n + 2)              # park J1 at t11, SLEEP at t12-t13
    return (s.jobs[0].status == "PARKED" and s.mode == SLEEP
            and s.runnable_job() is None
            and any(e["to"] == SLEEP and e["reason"] == "memory-full"
                    for e in s.mode_log))


@scenario("s26_sleep_commits_and_clears_memory")
def s26(s):
    s.grow_memory(s.sleep_threshold)
    s.run(s.sleep_chunks)
    return (s.memory == 0 and s.mode == THINKING
            and any(e["reason"] == "sleep-commit" for e in s.mode_log)
            and s.counters["sleeps"] == 1)


@scenario("s27_no_sleep_entry_while_job_runnable")
def s27(s):
    s.grow_memory(s.sleep_threshold)
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]}]})
    s.run(6)
    bad = [e for e in s.mode_log if e["to"] == SLEEP and e["runnable_jobs"] > 0]
    return not bad and s.jobs[0].status == "DONE"


@scenario("s28_parked_job_skips_queued_job_runs_next")
def s28(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}]})
    s.queue_job({"job_id": "J2", "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n + 3)
    j1, j2 = s.jobs
    return j1.status == "PARKED" and j2.status == "DONE"


@scenario("s29_resolve_question_requeues_job")
def s29(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "steps": [{"outcomes": ["ok"]}, {"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n)                  # parked
    assert s.resolve_question("J1")
    s.step()
    job = s.jobs[0]
    return (s.mode == WORK and job.status == "RUNNING"
            and job.step_index == 1 and not s.questions)


@scenario("s30_mode_log_complete_with_reasons")
def s30(s):
    s.submit("a")
    s.step()
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": 1,
                 "steps": [{"outcomes": ["ok"]}]})
    s.run(4)
    s.grow_memory(s.sleep_threshold)
    s.run(6)
    fields_ok = all(
        e.get("from") is not None and e.get("to") and e.get("reason")
        for e in s.mode_log)
    changed = sum(1 for e in s.mode_log if e["from"] != e["to"])
    return fields_ok and changed == s.mode_changes and s.mode == THINKING


@scenario("s31_idle_steps_do_not_churn_modes")
def s31(s):
    s.run(5)
    return s.mode == THINKING and len(s.mode_log) == 1


@scenario("s32_creative_commands_rejected_scheduler_decides")
def s32(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": None,
                 "probe": "command-sleep", "steps": [{"outcomes": ["ok"]}]})
    s.run(s.creative_fixed_n + 1)
    rejected = [n for n in s.notes if "rejected mode command" in n]
    return (len(rejected) >= 1 and not _has_mode(s.mode_log, SLEEP)
            and s.jobs[0].status == "PARKED")


@scenario("s33_two_jobs_get_separate_creative_budgets")
def s33(s):
    s.queue_job({"job_id": "J1", "open_ended": True, "creative_found_at": 2, "steps": []})
    s.queue_job({"job_id": "J2", "open_ended": True, "creative_found_at": 2, "steps": []})
    s.run(8)
    creative_entries = [e for e in s.mode_log if e["to"] == CREATIVE]
    return (len(creative_entries) == 2
            and all(job.status == "DONE" for job in s.jobs)
            and all(job.creative_round == 2 for job in s.jobs))


@scenario("s34_memory_grows_with_turns_and_finished_work_only")
def s34(s):
    before = s.memory
    s.run(3)                                   # idle THINKING never grows memory
    idle_untouched = s.memory == before
    s.submit("x")
    s.step()
    after_turn = s.memory
    s.queue_job({"job_id": "J1", "steps": [{"outcomes": ["ok"]}]})
    s.run(2)
    return (idle_untouched and after_turn == before + 1
            and s.memory > after_turn and s.jobs[0].status == "DONE")


# ------------------------------------------------------------------- judging
def run_scenario(factory, sc) -> bool:
    scheduler = factory()
    try:
        return bool(sc["fn"](scheduler))
    except Exception:
        return False


def global_violations(schedulers: list) -> dict:
    """S3/S4/S5 as whole-suite invariants."""
    v = {"log_fields": 0, "log_counts": 0, "creative_rounds": 0,
         "creative_exit": 0, "asked_once": 0, "sleep_entry_unsafe": 0,
         "sleep_commit_after_abort": 0}
    for s in schedulers:
        for entry in s.mode_log:
            if not (entry.get("from") is not None and entry.get("to")
                    and entry.get("reason")):
                v["log_fields"] += 1
            if entry["to"] == SLEEP and (entry["inbox"] or entry["runnable_jobs"]):
                v["sleep_entry_unsafe"] += 1
        changed = sum(1 for e in s.mode_log if e["from"] != e["to"])
        if changed != s.mode_changes:
            v["log_counts"] += 1
        for job in s.jobs:
            if job.creative_round > s.creative_fixed_n:
                v["creative_rounds"] += 1
            # a job that hit the cap without an outcome, or closed without a
            # recognised outcome, is a violation; a scenario may legitimately
            # stop mid-creative BELOW the cap (outcome None, round < cap)
            if job.creative_outcome not in (None, "FOUND", "GIVEUP"):
                v["creative_exit"] += 1
            if (job.creative_outcome is None
                    and job.creative_round >= s.creative_fixed_n):
                v["creative_exit"] += 1
            if job.creative_outcome == "GIVEUP":
                if job.questions_issued != 1:
                    v["asked_once"] += 1
                if job.status == "PARKED":
                    n = sum(1 for q in s.questions if q["job_id"] == job.job_id)
                    if n != 1:
                        v["asked_once"] += 1
                elif job.questions_issued == 1 and any(
                        q["job_id"] == job.job_id for q in s.questions):
                    v["asked_once"] += 1   # still open while not parked
        if any("rollback" in note for note in s.notes):
            if any(e["reason"] == "sleep-commit" for e in s.mode_log):
                v["sleep_commit_after_abort"] += 1
    return v


def selftest() -> int:
    rows = []
    ours_schedulers = []
    for sc in SCENARIOS:
        ok_ours = run_scenario(ModeScheduler, sc)
        ok_naive = run_scenario(NaiveAlwaysThinkingScheduler, sc)
        ours_schedulers.append(ModeScheduler())
        sc["fn"](ours_schedulers[-1])
        rows.append((sc["name"], ok_ours, ok_naive))

    ours_pass = sum(1 for _, ok, _ in rows if ok)
    naive_fail = sum(1 for _, ok, naive in rows if not naive)
    total = len(rows)

    v = global_violations(ours_schedulers)

    for name, ok_ours, ok_naive in rows:
        print(f"{'PASS' if ok_ours else 'FAIL'}  "
              f"naive:{'pass' if ok_naive else 'FAIL'}  {name}")

    marks = [
        ("S1", ours_pass >= 34 and total >= 34,
         f"ours {ours_pass}/{total} (need >= 34/34)"),
        ("S2", naive_fail >= 12,
         f"naive fails {naive_fail}/{total} (need >= 12)"),
        ("S3", v["log_fields"] == 0 and v["log_counts"] == 0,
         f"log field violations {v['log_fields']}, count mismatches {v['log_counts']}"),
        ("S4", v["creative_rounds"] == 0 and v["creative_exit"] == 0
         and v["asked_once"] == 0,
         f"round-limit {v['creative_rounds']}, unclosed creative {v['creative_exit']}, "
         f"ask-count {v['asked_once']} (all need 0)"),
        ("S5", v["sleep_entry_unsafe"] == 0 and v["sleep_commit_after_abort"] == 0,
         f"unsafe sleep entries {v['sleep_entry_unsafe']}, commit-after-abort "
         f"{v['sleep_commit_after_abort']} (need 0)"),
    ]
    print(f"\nscenarios: total {total}, ours {ours_pass}, naive fails {naive_fail}")
    for mark, ok, detail in marks:
        print(f"{mark} {'PASS' if ok else 'FAIL'} - {detail}")
    good = all(ok for _, ok, _ in marks)
    print("SELFTEST", "PASS" if good else "FAIL")
    return 0 if good else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Mode scheduler (doc 32 rules, v1)")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--show-log", action="store_true",
                        help="print a short demo of the mode log")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.show_log:
        sched = ModeScheduler()
        sched.submit("hello")
        sched.step()
        sched.queue_job({"job_id": "J-demo", "open_ended": True,
                         "creative_found_at": 2, "steps": [{"outcomes": ["ok"]}]})
        sched.run(6)
        print(json.dumps(sched.mode_log, indent=1))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
