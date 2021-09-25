import secrets
from dis import dis
from inspect import signature
from itertools import product
from types import CodeType, LambdaType, FunctionType
from typing import Any, List, Callable, Union, Optional, Tuple
from mixin.annotate import MixinType, Overwrite, ModifyConst, Inject, AtValue, At, Redirect, ModifyVar
from asm import LOAD_CONST, CALL_FUNCTION, DUP_TOP, POP_TOP, LOAD_ATTR, POP_JUMP_IF_FALSE, \
    RETURN_VALUE, ROT_TWO, Deserializer, Serializer, LOAD_FAST, Label, Opcode, STORE_FAST, NOP, LOAD_GLOBAL, LOAD_DEREF
from mixin.callback import CallbackInfo

OpList = List[Union[Opcode, Label]]
# TODO: Replace pattern matching with 3.5-compatible alternative


def check_mixins(func: Callable, mixins: List[MixinType]):
    injected = 6 + func.__code__.co_argcount
    code_obj = func.__code__.replace(
        co_code=func.__code__.co_code,
        co_consts=func.__code__.co_consts
    )
    deserializer = Deserializer(code_obj)
    ops = deserializer.deserialize()[injected:]

    # Overwrite + anything else = fail
    if len(mixins) > 1 and any(isinstance(it, Overwrite) for it in mixins):
        return False

    # Modifying same constant = fail
    all_targets = [get_targets(ops, LOAD_CONST, it.at.index, it.at.target) for it in mixins if isinstance(it, ModifyConst)]
    known = set()
    for it in all_targets:
        for el in it:
            if el not in known:
                known.add(el)
            else:
                return False

    # Redirecting same call with same prio = fail
    for m1, m2 in product(mixins, mixins):
        if m1 is m2:
            continue
        if m1.target == m2.target and m1.priority == m2.priority:
            # TODO: compare string target with func target
            return False

    return True


def get_targets(ops: OpList, type_: Union[type, Tuple[type, ...]], index: Union[int, slice], target: Any) -> List[Opcode]:
    targets = [
        op for op in ops if isinstance(op, type_) and (
                target is None or
                target == op.arg or (
                    hasattr(target, "__name__") and target.__name__ == op.arg
                )
        )

        # Prevent it from finding injected ops; These are never consts in python itself
        # Maybe figure out a better way to do this?
        and not (isinstance(op, LOAD_CONST) and isinstance(op.arg, (type, FunctionType, LambdaType)))
    ]

    targets = targets[index or slice(0, len(targets))]
    if not isinstance(targets, list):
        targets = [targets]
    return targets


def load_locals(code: CodeType, func: Callable, ignore_last: bool) -> List[Opcode]:
    params = [*signature(func).parameters.keys()]
    return [
        LOAD_FAST(param) if param in code.co_varnames else LOAD_DEREF(param)
        for param in (params[:-1] if ignore_last else params)
    ]


def replace_op(ops: OpList, index: int, target: OpList):
    ops[index:index+1] = target


def apply_inject(code: CodeType, ops: OpList, callback: Callable, at: At, cancellable: bool):
    args = load_locals(code, callback, True)
    name = "__mixin_" + secrets.token_hex(32)

    if at.value is AtValue.RETURN:
        mark1 = [
            STORE_FAST(name)
        ]
        mark2 = [
            LOAD_FAST(name)
        ]
        nargs = 2
    else:
        mark1 = mark2 = []
        nargs = 1

    if cancellable:
        end_label = Label()
        injected = [
            *mark1,
            LOAD_CONST(CallbackInfo),
            LOAD_CONST(True),
            *mark2,
            CALL_FUNCTION(nargs),
            STORE_FAST(name),
            LOAD_CONST(callback),
            *args,
            LOAD_FAST(name),
            CALL_FUNCTION(1 + len(args)),
            POP_TOP(),
            LOAD_FAST(name),
            DUP_TOP(),
            LOAD_ATTR("_cancelled"),
            POP_JUMP_IF_FALSE(end_label),
            LOAD_ATTR("return_value"),
            RETURN_VALUE(),
            end_label,
            POP_TOP(),
        ]
    else:
        injected = [
            *mark1,
            LOAD_CONST(callback),
            *args,
            LOAD_CONST(CallbackInfo),
            LOAD_CONST(False),
            *mark2,
            CALL_FUNCTION(nargs),
            CALL_FUNCTION(1 + len(args)),
            POP_TOP(),
        ]

    match at.value:
        # At head
        case AtValue.HEAD:
            ops[:] = injected + ops
        case _:
            raise NotImplementedError(at.value)


def apply_overwrite(code: CodeType, ops: OpList, callback: Callable):
    args = load_locals(code, callback, False)
    ops[:] = [
        LOAD_CONST(callback),
        *args,
        CALL_FUNCTION(len(args)),
        RETURN_VALUE(),
    ]


def apply_modifyconst(code: CodeType, ops: OpList, callback: Callable, at: At):
    # At load
    targets = get_targets(ops, LOAD_CONST, at.index, at.target)

    args = load_locals(code, callback, False)
    index = 0

    for op in ops[:]:
        if op in targets:
            replace_op(ops, index, [
                LOAD_CONST(callback),
                *args,
                CALL_FUNCTION(len(args))
            ])
            index += 1 + len(args)
        index += 1


def apply_modifyvar(code: CodeType, ops: OpList, callback: Callable, at: At):
    # At load
    targets = get_targets(ops, (LOAD_FAST, LOAD_DEREF), at.index, at.target)

    args = load_locals(code, callback, False)
    index = 0

    for op in ops[:]:
        if op in targets:
            replace_op(ops, index, [
                LOAD_CONST(callback),
                *args,
                CALL_FUNCTION(len(args))
            ])
            index += 1 + len(args)
        index += 1


def apply_redirect(code: CodeType, ops: OpList, callback: Callable, at: At):
    # At invoke
    targets = get_targets(ops, (LOAD_GLOBAL, LOAD_FAST, LOAD_DEREF), at.index, at.target)
    # TODO: LOAD_ATTR with parent/attr name
    index = 0
    for op in ops[:]:
        if op in targets:
            ops[index] = LOAD_CONST(callback)
        index += 1


def apply_mixins(func: Callable, mixins: List[MixinType]):
    # Restore original
    injected = 6 + func.__code__.co_argcount
    code_obj = func.__code__.replace(
        co_code=func.__code__.co_code,
        co_consts=func.__code__.co_consts
    )

    deserializer = Deserializer(code_obj)
    ops = deserializer.deserialize()[injected:]
    code_obj = code_obj.replace(
        co_consts=(None,),
        co_names=tuple(),
        co_varnames=code_obj.co_varnames[:code_obj.co_argcount],
    )

    for m in sorted(mixins, key=lambda t: t.priority):
        match m:
            case Overwrite(callback):
                # Only one overwrite
                apply_overwrite(code_obj, ops, callback)
            case ModifyConst(callback, at):
                apply_modifyconst(code_obj, ops, callback, at)
            case ModifyVar(callback, at):
                apply_modifyvar(code_obj, ops, callback, at)
            case Redirect(callback, at):
                apply_redirect(code_obj, ops, callback, at)
            case Inject(callback, at, cancellable):
                apply_inject(code_obj, ops, callback, at, cancellable)
            case _:
                # Error
                raise NotImplementedError(m)

    serializer = Serializer(ops, code_obj)
    func.__code__ = serializer.serialize()
