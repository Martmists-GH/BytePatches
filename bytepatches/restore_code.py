from typing import List

from bytepatches.ops import Opcode, pretty_printer
from bytepatches.pyc_parser import PycParser


def restore_code(ops: List[Opcode]):
    # Has to be a tree=True view
    code = ""
    pretty_printer.pprint(ops[:10])
    for op in ops:
        code += encode_op(op)
        print("-" * 20)
        print(code)


def encode_op(op: Opcode) -> str:
    if op.op_name == "LOAD_CONST":
        return ""

    elif op.op_name == "STORE_NAME":
        if op.val.op_name == "IMPORT_NAME":
            if op.arg != op.val.arg.split(".")[0]:
                return f"import {op.val.arg} as {op.arg}\n"
            else:
                return f"import {op.val.arg}\n"
        elif op.val.op_name == "IMPORT_FROM":
            print(op)
            op.val
        else:
            return f"{op.arg} = {op.val}\n"

    raise


if __name__ == "__main__":
    parser = PycParser("__pycache__/utils.cpython-37.pyc")
    parser.parse()
    print(restore_code(parser.content))
