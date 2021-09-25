from typing import Callable


def unwrap(func: Callable) -> Callable:
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    return func
