from typing import Callable

from mixin.annotate import At, add_injection, Inject, get_wrapper, Overwrite, ModifyConst, Redirect, ModifyVar


def inject(method: Callable, at: At, priority: int = 1000, cancellable=False) -> Callable:
    def wrapper(func):
        new_func = get_wrapper(method)
        add_injection(new_func, Inject(callback=func, at=at, priority=priority, cancellable=cancellable))
        return new_func

    return wrapper


def overwrite(method: Callable, priority: int = 1000) -> Callable:
    def wrapper(func):
        new_func = get_wrapper(method)
        add_injection(new_func, Overwrite(callback=func, priority=priority))
        return new_func

    return wrapper


def redirect(method: Callable, at: At, priority: int = 1000):
    def wrapper(func):
        new_func = get_wrapper(method)
        add_injection(new_func, Redirect(callback=func, at=at, priority=priority))
        return new_func

    return wrapper


def modify_const(method: Callable, at: At, priority: int = 1000):
    def wrapper(func):
        new_func = get_wrapper(method)
        add_injection(new_func, ModifyConst(callback=func, at=at, priority=priority))
        return new_func

    return wrapper


def modify_var(method: Callable, at: At, priority: int = 1000):
    def wrapper(func):
        new_func = get_wrapper(method)
        add_injection(new_func, ModifyVar(callback=func, at=at, priority=priority))
        return new_func

    return wrapper
