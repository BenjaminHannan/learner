"""Check sleep and the model-lock owner again after the FIFO wait."""
import ctypes
import datetime
import os
import math
import sys
from pathlib import Path


def idle_seconds():
    if sys.platform != 'darwin': raise RuntimeError('Mac idle check unavailable')
    cg=ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    cg.CGEventSourceSecondsSinceLastEventType.argtypes=[ctypes.c_uint32,ctypes.c_uint32]
    cg.CGEventSourceSecondsSinceLastEventType.restype=ctypes.c_double
    return cg.CGEventSourceSecondsSinceLastEventType(1,0xffffffff)


def check(now, idle):
    if not 1 <= now.hour < 7 or not math.isfinite(idle) or idle < 1200:
        raise RuntimeError('night request deferred: Mac must be idle for 20 minutes after 01:00')
    if (Path.home()/'learner-ops/aon-notes/hands-20261106/STOP-TRAINING').exists():
        raise RuntimeError('night request stopped')


def main():
    owner=Path('/tmp/aon/realmodel.lock/owner').read_text().split()
    if len(owner)<2 or owner[0]!='NIGHT-LEARN' or int(owner[1])!=os.getppid():
        raise RuntimeError('must run directly under the NIGHT-LEARN model lock')
    check(datetime.datetime.now().astimezone(),idle_seconds())
    if len(sys.argv)<2 or not os.path.isabs(sys.argv[1]): raise RuntimeError('absolute command required')
    os.execv(sys.argv[1],sys.argv[1:])

if __name__=='__main__':main()
