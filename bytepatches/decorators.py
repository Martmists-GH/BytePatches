from contextlib import suppress
from typing import List, Union

from bytepatches.op_replacer import replace as rep, change_ops as change, OpNotFound, optimize_access
from bytepatches.ops import POP_TOP, RETURN_VALUE, LOAD_CONST, JUMP_FORWARD, sync_ops, LOAD_FAST, \
    LOAD_NAME, STORE_NAME, STORE_FAST, POP_BLOCK, JUMP_ABSOLUTE, Opcode
from bytepatches.utils import get_ops, patch_function, make_bytecode


def _change(*args):
    with suppress(OpNotFound):
        change(*args)


def replace(before: Union[str, List[Opcode]], after: Union[str, List[Opcode]]):
    def decorator(func):
        rep(func, before, after, True)
        return func

    return decorator


def omit_return(func):
    fn_ops = get_ops(func)
    # Regular
    _change(fn_ops,
            [POP_TOP(0), LOAD_CONST(0), RETURN_VALUE(0)],
            [RETURN_VALUE(0)])

    # If/elif/else
    _change(fn_ops,
            [POP_TOP(0), JUMP_FORWARD("$1")],
            [JUMP_FORWARD("$1")])

    # For loop
    next_op_pos = len(func.__code__.co_varnames)
    varnames = [*func.__code__.co_varnames, "omitReturnVariableName"]

    _change(fn_ops,
            [POP_BLOCK(0), LOAD_CONST(0), RETURN_VALUE(0)],
            [POP_BLOCK(0), LOAD_FAST(next_op_pos, "omitReturnVariableName"), RETURN_VALUE(0)])

    _change(fn_ops,
            [POP_TOP(0), JUMP_ABSOLUTE("$1")],
            [STORE_FAST(next_op_pos, "omitReturnVariableName"), JUMP_ABSOLUTE("$1")])

    sync_ops(fn_ops)
    patch_function(func, make_bytecode(fn_ops), varnames=tuple(varnames))
    return func


def optimize(func):
    ops = get_ops(func)
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
                del ops[int(getattr(stored_op, stored_prop).bytecode_pos / 2)]
                del ops[int(op.bytecode_pos / 2)]
                setattr(stored_op, stored_prop, op.val)
                stop = False
                break
        sync_ops(ops)

    names, varnames = optimize_access(ops)
    patch_function(func, make_bytecode(ops), names=names, varnames=varnames)
    return func
