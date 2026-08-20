from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from .metrics import increment
from .structured_logging import event


@dataclass(frozen=True)
class Timing:
    name: str
    milliseconds: float
    successful: bool

    def payload(self):
        return {
            "name": self.name,
            "milliseconds": round(self.milliseconds, 3),
            "successful": self.successful,
        }


@contextmanager
def measure(name, **fields):
    started = perf_counter()
    try:
        yield
    except Exception:
        timing = Timing(name, (perf_counter() - started) * 1000, False)
        increment(f"{name}.failure")
        event("calendar.timing", **timing.payload(), **fields)
        raise
    else:
        timing = Timing(name, (perf_counter() - started) * 1000, True)
        increment(f"{name}.success")
        event("calendar.timing", **timing.payload(), **fields)


def timed(name):
    def decorator(function):
        def wrapped(*args, **kwargs):
            with measure(name):
                return function(*args, **kwargs)

        return wrapped

    return decorator


def slow(timing, threshold_ms):
    return timing.milliseconds >= threshold_ms


def aggregate(timings):
    values = tuple(timings)
    return {
        "count": len(values),
        "total_ms": sum(item.milliseconds for item in values),
        "failures": sum(not item.successful for item in values),
    }
