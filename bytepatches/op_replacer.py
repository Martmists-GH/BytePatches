from itertools import zip_longest
from typing import List, Union

from bytepatches.ops import Opcode, sync_ops, LOAD_FAST, STORE_FAST, JumpOp, LOAD_NAME, LOAD_CONST, STORE_NAME
from bytepatches.parser import Parser
from bytepatches.utils import patch_function, make_bytecode


class OpNotFound(Exception):
    pass


def change_ops(ops: List[Opcode], ops_before: List[Opcode], ops_after: List[Opcode]):
    index = 0
    found = False
    _cache = {}
    indices = []
    while True:
        if index == len(ops):
            if not found:
                raise OpNotFound("Ops not found!")
            break

        target = ops[index:index+len(ops_before)]

        if target == ops_before:
            for existing, op in zip(target, ops_before):
                if op is not None and isinstance(op._arg, str):
                    if op._arg not in _cache:
                        _cache[op._arg] = [existing]
                    else:
                        _cache[op._arg].append(existing)
            found = True
            indices.append(index)

        index += 1

    for index in indices:
        for before, after in zip_longest(ops_before, ops_after):
            if after is not None:
                if isinstance(after._arg, str):
                    after = _cache[after._arg].pop(0)

            if before is None:
                # Append after
                ops.insert(index, after)
            elif after is None:
                # Remove before
                # We can't pop because that fucks stuff up, but we can set to None and remove later
                # Go forwards first
                new_target = None
                direction = 1
                pos = index
                target = ops[index]
                ops[index] = None
                while new_target is None:
                    pos += direction
                    try:
                        new_target = ops[pos]
                    except IndexError:
                        direction = -1

                for op in ops:
                    if isinstance(op, JumpOp) and op.val == target:
                        if op.reljump():
                            op._arg = new_target.bytecode_pos - op.bytecode_pos
                        else:
                            op._arg = new_target.bytecode_pos
                        op.val = new_target

            else:
                # Switch ops
                for op in ops:
                    if isinstance(op, JumpOp) and op.val == before:
                        op.val = after
                after.set_bytecode_pos(ops[index].bytecode_pos)
                ops[index] = after
            index += 1

    for index, item in reversed(list(enumerate(ops))):
        if item is None:
            ops.pop(index)
    sync_ops(ops)


def replace(func, before_code: Union[str, List[Opcode]], after_code: Union[str, List[Opcode]], name_to_fast=False):
    fn_code = func.__code__
    consts = list(fn_code.co_consts)
    names = list(fn_code.co_names)
    varnames = list(fn_code.co_varnames)
    groups = []
    if isinstance(before_code, str):
        before = compile(before_code, "<input>", "exec")
        groups.append(before)
    if isinstance(after_code, str):
        after = compile(after_code, "<input>", "exec")
        groups.append(after)

    for group in groups:
        for const in group.co_consts:
            if const not in consts:
                consts.append(const)
        for name in group.co_names:
            if name not in names:
                names.append(name)
        for varname in group.co_varnames:
            if varname not in varnames:
                varnames.append(varname)
    if name_to_fast:
        for name in names:
            if name not in varnames:
                varnames.append(name)

    if isinstance(before_code, str):
        before_ops = Parser(before_code).parse_bytecode(False)
    else:
        before_ops = before_code

    if isinstance(after_code, str):
        after_ops = Parser(after_code).parse_bytecode(False)
    else:
        after_ops = after_code

    # TODO: Find a more reliable way to strip LOAD_CONST(None) RETURN_VALUE from code if not in the input
    if before_ops[-1].op_name == "RETURN_VALUE" and before_ops[-1].arg is not None and before_ops[-1].arg.arg is None:
        before_ops = before_ops[:-2]
        after_ops = after_ops[:-2]
    if before_ops[-1].op_name == "POP_TOP" and before_ops[-1].arg is None:
        before_ops = before_ops[:-1]
        after_ops = after_ops[:-1]

    if isinstance(before_code, str):
        for i, op in enumerate(before_ops):
            if name_to_fast:
                if op.op_name == "LOAD_NAME":
                    op = LOAD_FAST(op._arg, op.arg, op.val)
                elif op.op_name == "STORE_NAME":
                    op = STORE_FAST(op._arg, op.arg, op.val)

            if "CONST" in op.op_name:
                val = before.co_consts[op._arg]
                if op._arg != consts.index(val):
                    op._arg = consts.index(val)
            elif "NAME" in op.op_name:
                val = before.co_names[op._arg]
                if op._arg != names.index(val):
                    op._arg = names.index(val)
            elif "FAST" in op.op_name:
                group = before.co_varnames
                if name_to_fast:
                    group += before.co_names
                val = group[op._arg]
                if op._arg != varnames.index(val):
                    op._arg = varnames.index(val)

            before_ops[i] = op

    if isinstance(after_code, str):
        for i, op in enumerate(after_ops):
            if name_to_fast:
                if op.op_name == "LOAD_NAME":
                    op = LOAD_FAST(op._arg, op.arg, op.val)
                elif op.op_name == "STORE_NAME":
                    op = STORE_FAST(op._arg, op.arg, op.val)

            if "CONST" in op.op_name:
                val = after.co_consts[op._arg]
                if op._arg != consts.index(val):
                    op._arg = consts.index(val)
            elif "NAME" in op.op_name:
                val = after.co_names[op._arg]
                if op._arg != names.index(val):
                    op._arg = names.index(val)
            elif "FAST" in op.op_name:
                group = after.co_varnames
                if name_to_fast:
                    group += after.co_names
                val = group[op._arg]
                if op._arg != varnames.index(val):
                    op._arg = varnames.index(val)

            after_ops[i] = op

    ops = Parser(func).parse_bytecode(False)

    change_ops(ops, before_ops, after_ops)

    names, varnames = optimize_access(ops)
    payload = make_bytecode(ops)
    patch_function(func, payload, consts=tuple(consts), names=tuple(names), varnames=tuple(varnames))
    return func


def optimize_access(ops: List[Opcode]):
    accessed_names = []
    accessed_varnames = []

    for op in ops:
        if isinstance(op, (LOAD_NAME, STORE_NAME)) and op.arg not in accessed_names:
            accessed_names.append(op.arg)
        elif isinstance(op, (LOAD_FAST, STORE_FAST)) and op.arg not in accessed_varnames:
            accessed_varnames.append(op.arg)

    accessed_names = tuple(accessed_names)
    accessed_varnames = tuple(accessed_varnames)

    for op in ops:
        if isinstance(op, (LOAD_NAME, STORE_NAME)):
            op._arg = accessed_names.index(op.arg)
        elif isinstance(op, (LOAD_FAST, STORE_FAST)):
            op._arg = accessed_varnames.index(op.arg)

    return accessed_names, accessed_varnames
