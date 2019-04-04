import dis
import textwrap
from pprint import PrettyPrinter
from struct import pack, unpack
from typing import Any, List, Union

VERBOSE = True


def b(byte: int) -> bytes:
    return pack("B", byte)


def sync_ops(ops: List['Opcode']):
    for pos, op in enumerate(ops):
        if op is not None:
            op.set_bytecode_pos(pos*2)
    for op in ops:
        if hasattr(op, "load"):
            op.load(ops)


NULL_BYTE = b(0)


class OpCodePrinter(PrettyPrinter):
    def _format(self, obj, stream, indent, allowance, *args, **kwargs):
        if hasattr(obj, "__pformat__"):
            max_width = self._width - indent - allowance
            if len(str(obj)) > max_width:
                obj = obj.__pformat__(indent)
                stream.write(obj)
                return
        return super()._format(obj, stream, indent, allowance, *args, **kwargs)


pretty_printer = OpCodePrinter()


class Context:
    def __init__(self, names: tuple = None, consts: tuple = None, varnames: tuple = None):
        self.names = names or tuple()
        self.consts = consts or tuple()
        self.varnames = varnames or tuple()

    def load_name(self, name: int):
        if self.names:
            return self.names[name]
        return name

    def load_const(self, const: int):
        if self.consts:
            c = self.consts[const]
            if c.__class__.__name__ == "code":
                from bytepatches.parser import Parser
                return Parser(c).parse_bytecode()
            return c
        return const

    def load_fast(self, varname: int):
        if self.varnames:
            return self.varnames[varname]
        return varname


class Opcode:
    op_byte: bytes = b(0)

    def __init__(self, arg: Union[int, str] = None, arg_obj: Any = None, val_obj: Any = None):
        self.bytecode_pos = 0
        self._arg = arg
        self.arg = arg_obj
        self.val = val_obj

    def __eq__(self, other):
        if not isinstance(other, Opcode):
            return False

        if self.op_name == other.op_name:
            return (self._arg == Any or
                    other._arg == Any or
                    isinstance(self._arg, str) or
                    isinstance(other._arg, str) or
                    self._arg == other._arg)

        return False

    def set_bytecode_pos(self, pos: int):
        self.bytecode_pos = pos

    @property
    def op_name(self):
        return self.__class__.__name__

    def pack(self):
        return self.op_byte + b(self._arg)

    def __repr__(self) -> str:
        if not VERBOSE:
            if self.op_name == "LOAD_CONST":
                return str(self.arg)

        if self.val is not None:
            arg = f"{self.op_name}[{self._arg}]({self.arg}, {self.val})"
        else:
            arg = f"{self.op_name}[{self._arg}]({self.arg})"
        return str(self.bytecode_pos) + " " + arg

    def __pformat__(self, indent: int) -> str:
        args = (self.arg, self.val) if self.val is not None else (self.arg, )
        formatted = (f"{self.op_name}[{self._arg}](\n" +
                     textwrap.indent(",\n".join(map(pretty_printer.pformat, args)), " " * (4 + indent)) +
                     "\n" + " " * indent + ")")
        return str(self.bytecode_pos) + " " + formatted


class JumpOp(Opcode):
    op_byte = b(0)
    _target = 0

    def reljump(self) -> bool:
        return unpack("B", self.op_byte)[0] in dis.hasjrel

    def pack(self):
        self._arg = self._target
        return super().pack()

    def load(self, ops):
        if not self.val:
            # Initial load, get target op
            if self.reljump():
                target_op_pos = (self.bytecode_pos + self._arg + 2) / 2
            else:
                target_op_pos = self._arg/2
            self.val = ops[int(target_op_pos)]
        else:
            if self.reljump():
                self._target = self.val.bytecode_pos - self.bytecode_pos - 2
            else:
                self._target = self.val.bytecode_pos


class NOP(Opcode):
    op_byte = b(0)


class POP_TOP(Opcode):
    op_byte = b(1)


class BINARY_POWER(Opcode):
    op_byte = b(19)


class BINARY_MULTIPLY(Opcode):
    op_byte = b(20)


class BINARY_MODULO(Opcode):
    op_byte = b(22)


class BINARY_ADD(Opcode):
    op_byte = b(23)


class BINARY_SUBTRACT(Opcode):
    op_byte = b(24)


class BINARY_FLOOR_DIVIDE(Opcode):
    op_byte = b(26)


class BINARY_TRUE_DIVIDE(Opcode):
    op_byte = b(27)

class GET_ITER(Opcode):
    op_byte = b(68)


class RETURN_VALUE(Opcode):
    op_byte = b(83)


class POP_BLOCK(Opcode):
    op_byte = b(87)


class STORE_NAME(Opcode):
    op_byte = b(90)


class FOR_ITER(JumpOp):  # JumpOp because it has a referenced target
    op_byte = b(93)


class LOAD_CONST(Opcode):
    op_byte = b(100)


class LOAD_NAME(Opcode):
    op_byte = b(101)


class COMPARE_OP(Opcode):
    op_byte = b(107)


class IMPORT_NAME(Opcode):
    op_byte = b(108)


class JUMP_FORWARD(JumpOp):
    op_byte = b(110)


class JUMP_ABSOLUTE(JumpOp):
    op_byte = b(113)


class POP_JUMP_IF_FALSE(JumpOp):
    op_byte = b(114)


class LOAD_GLOBAL(Opcode):
    op_byte = b(116)


class SETUP_LOOP(JumpOp):
    op_byte = b(120)


class LOAD_FAST(Opcode):
    op_byte = b(124)


class STORE_FAST(Opcode):
    op_byte = b(125)


class CALL_FUNCTION(Opcode):
    op_byte = b(131)


class MAKE_FUNCTION(Opcode):
    op_byte = b(132)


class BUILD_CONST_KEY_MAP(Opcode):
    op_byte = b(156)


class LOAD_METHOD(Opcode):
    op_byte = b(160)


class CALL_METHOD(Opcode):
    op_byte = b(161)
