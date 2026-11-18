"""429-safe retry for litellm calls to Anthropic (tau2 user simulator + judge). Opt-in: PYTHONPATH=<this dir>.
Why: litellm num_retries backs off ~1-10 s with a few tries and ignores Retry-After; under a burst of 10-30 sims
all threads retry in sync and give up -> tau2 logs an infra error / too_many_errors (counted as a fail).
This wrapper: honours Retry-After, full-jitter exponential backoff (cap 60 s), a shared cool-down so all threads
back off together, up to SPEED_RETRY_MAX (default 8) extra tries. Only Anthropic models; local vLLM errors pass through.
Never changes a successful response, so results are unchanged. Stats: SPEED_RETRY_LOG (default /tmp/speed_retry.log)."""
import os, random, threading, time

MAXTRY = int(os.environ.get("SPEED_RETRY_MAX", "8")); CAP = float(os.environ.get("SPEED_RETRY_CAP", "60"))
LOG = os.environ.get("SPEED_RETRY_LOG", "/tmp/speed_retry.log")
_lock = threading.Lock(); _pause_until = 0.0


def _retryable(e):
    n = type(e).__name__; s = str(e).lower(); code = getattr(e, "status_code", None)
    return code in (408, 429, 500, 502, 503, 504, 529) or n in ("RateLimitError", "ServiceUnavailableError", "InternalServerError",
        "APIConnectionError", "Timeout", "APITimeoutError") or "overloaded" in s or "rate limit" in s


def _retry_after(e):
    try:
        h = getattr(getattr(e, "response", None), "headers", None) or {}
        v = h.get("retry-after") or h.get("Retry-After")
        return float(v) if v else None
    except Exception:
        return None


def _is_anthropic(kw, args):
    m = str(kw.get("model") or (args[0] if args else ""))
    return "claude" in m or m.startswith("anthropic/")


def with_retry(fn, sleep=time.sleep, rnd=random.random):
    def wrapped(*a, **kw):
        global _pause_until
        if not _is_anthropic(kw, a):
            return fn(*a, **kw)
        for i in range(MAXTRY + 1):
            w = _pause_until - time.time()
            if w > 0:
                sleep(w + rnd())
            try:
                return fn(*a, **kw)
            except Exception as e:
                if i >= MAXTRY or not _retryable(e):
                    raise
                d = _retry_after(e) or rnd() * min(CAP, 2 ** (i + 1))  # full jitter
                with _lock:
                    _pause_until = max(_pause_until, time.time() + d * 0.5)  # shared, half the wait
                try:
                    open(LOG, "a").write("%s try=%d %s wait=%.1f\n" % (time.strftime("%T"), i, type(e).__name__, d))
                except Exception:
                    pass
                sleep(d)
    return wrapped


try:
    import litellm
    if not getattr(litellm.completion, "_speed_retry", False):
        litellm.completion = with_retry(litellm.completion); litellm.completion._speed_retry = True
except Exception:
    pass
