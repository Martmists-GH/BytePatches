from types import CodeType
from typing import List

from bytepatches.ops import Opcode
from bytepatches.parser import Parser


def make_bytecode(ops: List[Opcode]):
    return b"".join(
        op.pack() for op in ops
    )


def get_ops(code: str, tree: bool = False):
    return Parser(code).parse_bytecode(tree)


def patch_function(func, payload: bytes, consts=None, names=None, varnames=None):
    fn_code = func.__code__
    func.__code__ = CodeType(
        fn_code.co_argcount,
        fn_code.co_kwonlyargcount,
        fn_code.co_nlocals,
        fn_code.co_stacksize,
        fn_code.co_flags,
        payload,
        consts or fn_code.co_consts,
        names or fn_code.co_names,
        varnames or fn_code.co_varnames,
        fn_code.co_filename,
        fn_code.co_name,
        fn_code.co_firstlineno,
        fn_code.co_lnotab,
        fn_code.co_freevars,
        fn_code.co_cellvars
    )
