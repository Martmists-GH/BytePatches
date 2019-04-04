from contextlib import suppress

from bytepatches.op_replacer import replace as rep, change_ops as change, OpNotFound
from bytepatches.ops import POP_TOP, RETURN_VALUE, LOAD_CONST, JUMP_FORWARD, sync_ops, LOAD_FAST, \
    LOAD_NAME, STORE_NAME, STORE_FAST, POP_BLOCK
from bytepatches.utils import get_ops, patch_function, make_bytecode


def _change(*args):
    with suppress(OpNotFound):
        change(*args)


def replace(before: str, after: str):
    def decorator(func):
        rep(func, before, after, True)
        return func
    return decorator


def omit_return(func):
    fn_ops = get_ops(func)
    _change(fn_ops,
            [POP_TOP(0), LOAD_CONST(0), RETURN_VALUE(0)],
            [RETURN_VALUE(0)])

    _change(fn_ops,
            [POP_TOP(0), JUMP_FORWARD("$1")],
            [JUMP_FORWARD("$1")])

    sync_ops(fn_ops)

    patch_function(func, make_bytecode(fn_ops))
    return func


def optimize(func):
    ops = get_ops(func)
    # TODO: Patch names/varnames to reduce possible overhead
    # The challenge here is to identify unused names/varnames (varnames are used for LOAD_FAST and STORE_FAST)
    # And patch all other name/varname accessors to use the correct value.
    # names = list(func.__code__.co_names)
    # varnames = list(func.__code__.co_varnames)
    stop = False
    while not stop:
        stop = True
        var_name = ""
        stored_op = None
        stored_prop = None
        for op in reversed(ops):
            if isinstance(op.arg, (LOAD_FAST, LOAD_NAME)):
                var_name = op.arg.arg
                stored_op = op
                stored_prop = "arg"

            elif isinstance(op.val, (LOAD_FAST, LOAD_NAME)):
                var_name = op.val.arg
                stored_op = op
                stored_prop = "val"

            elif isinstance(op, POP_BLOCK):
                var_name = ""
                stored_op = None
                stored_prop = ""

            elif isinstance(op, (STORE_FAST, STORE_NAME)) and op.arg == var_name:
                """
                if var_name in names:
                    names.remove(var_name)
                elif var_name in varnames:
                    varnames.remove(var_name)
                """
                del ops[int(getattr(stored_op, stored_prop).bytecode_pos / 2)]
                del ops[int(op.bytecode_pos / 2)]
                setattr(stored_op, stored_prop, op.val)
                stop = False
                break
        sync_ops(ops)

    patch_function(func, make_bytecode(ops))  # , names=tuple(names), varnames=tuple(varnames))
    return func
