from dataclasses import dataclass, field
from enum import Enum
from types import LambdaType, FunctionType
from typing import Callable, Optional, List, Union

from asm import Deserializer, LOAD_CONST, CALL_FUNCTION, POP_TOP, Serializer, RETURN_VALUE, LOAD_FAST

__METADATA_NAME = "__mixin_metadata"


class UnsupportedInjectableError(RuntimeError):
    def __init__(self, obj):
        super().__init__(
            f"Unable to inject into object of type {obj.__class__.__name__}")


class AtValue(Enum):
    HEAD = "HEAD"
    RETURN = "RETURN"
    INVOKE = "INVOKE"
    LOAD = "LOAD"


@dataclass
class At:
    value: AtValue
    target: Optional[str] = None
    index: Union[int, List[int], slice, None] = None


class MixinType:
    pass


@dataclass
class Inject(MixinType):
    callback: Callable
    at: At
    cancellable: bool
    priority: int


@dataclass
class Redirect(MixinType):
    callback: Callable
    at: At
    priority: int


@dataclass
class ModifyConst(MixinType):
    callback: Callable
    at: At
    priority: int


@dataclass
class ModifyVar(MixinType):
    callback: Callable
    at: At
    priority: int


@dataclass
class Overwrite(MixinType):
    callback: Callable
    priority: int


@dataclass
class Metadata:
    real_func: Callable
    injections: List[MixinType] = field(default_factory=list)
    applied: bool = False


def do_injection(func: Callable) -> Callable:
    from mixin.impl import check_mixins, apply_mixins

    meta = getattr(func, __METADATA_NAME)
    if not meta.applied:
        if not check_mixins(meta.real_func, meta.injections):
            raise RuntimeError(f"Incompatible mixins for {meta.real_func}!")
        apply_mixins(meta.real_func, meta.injections)
        meta.applied = True
    return func


def get_or_create_meta(func: Callable) -> Metadata:
    if not hasattr(func, __METADATA_NAME):
        meta = Metadata(func)
        setattr(func, __METADATA_NAME, meta)
    else:
        meta = getattr(func, __METADATA_NAME)
    return meta


def is_implemented_in_c(obj):
    if isinstance(obj, (FunctionType, LambdaType)):
        return False
    if isinstance(obj, type):
        if '__dict__' in dir(obj):
            return False
        return not hasattr(obj, '__slots__')
    return True


def get_wrapper(func: Callable) -> Callable:
    if is_implemented_in_c(func):
        raise UnsupportedInjectableError(func)

    if hasattr(func, __METADATA_NAME):
        return func

    meta = get_or_create_meta(func)

    def inject():
        if not meta.applied:
            do_injection(func)

    deserializer = Deserializer(func.__code__)
    ops = deserializer.deserialize()
    ops = [
              # Change bytecode
              LOAD_CONST(inject),
              CALL_FUNCTION(),
              POP_TOP(),
              # Call self
              LOAD_CONST(func),
              *[LOAD_FAST(func.__code__.co_varnames[i]) for i in range(func.__code__.co_argcount)],
              CALL_FUNCTION(func.__code__.co_argcount),
              RETURN_VALUE(),
          ] + ops
    serializer = Serializer(ops, func.__code__)
    func.__code__ = serializer.serialize()

    return func


def add_injection(func: Callable, data: MixinType):
    meta = get_or_create_meta(func)

    if meta.applied:
        raise RuntimeError("Attempted to add mixin after loading function")

    meta.injections.append(data)
