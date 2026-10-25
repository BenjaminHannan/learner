"""Deterministic sim-Ben for the GPU jobs: answers and corrections are triggered by code and use pre-generated Haiku phrasings."""
import zlib

from .config import ANNOY_PREFIX, CORR_PREFIX, FULLSPEC_REPLY, norm
from .requests_gen import label_name


def h(*parts):
    return zlib.crc32("|".join(map(str, parts)).encode())


class UserSim:
    def __init__(self, persona, phr):
        self.P, self.phr = persona, phr

    def target_slot(self, req, question):
        """Which of the request's needed slots is the question about? (rule based; the eval grader is Haiku, this one only drives the sim)"""
        if not req.get("underspecified"):
            return None
        q = norm(question)
        for sid in req["slots"]:
            s = self.P.slot(sid)
            if norm(s["key_token"]) in q or norm(s["ref"]) in q:
                return sid
            for c in s["candidates"]:
                if s["kind"] in ("contact", "meeting", "file") and (norm(c["value"]) in q or (len(label_name(c["label"])) > 3 and norm(label_name(c["label"])) in q)):
                    return sid
        return req["slots"][0]  # generic question: Ben answers the open slot (lenient)

    def answer_ask(self, req, question, known_slots):
        """-> (reply text, slot id or None, annoyed bool). known_slots: slot ids Ben answered/corrected on earlier days."""
        k = h(req["req_id"], question[:20])
        sid = self.target_slot(req, question)
        if sid is None:  # fully specified request: the answer was in the message
            lits = ", ".join(str(v[0] if isinstance(v, list) else v) for v in req["literals"].values()) or req["text"]
            return FULLSPEC_REPLY[k % len(FULLSPEC_REPLY)].format(lits=lits), None, True
        ans = self.phr["slots"][sid]["answers"][k % len(self.phr["slots"][sid]["answers"])]
        if sid in known_slots:
            return ANNOY_PREFIX[k % len(ANNOY_PREFIX)] + ans, sid, True
        return ans, sid, False

    def correction(self, req, sid):
        """Correction text for a wrong committed value of slot sid, or None when Ben does not notice (silent slots)."""
        s = self.P.slot(sid)
        if s["split"] == "silent":
            return None
        k = h(req["req_id"], sid, "c")
        c = self.phr["slots"][sid]["corrections"]
        return CORR_PREFIX[k % len(CORR_PREFIX)] + c[k % len(c)]
