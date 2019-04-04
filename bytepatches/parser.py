import struct
from io import BytesIO
from typing import List

from bytepatches.ops import Context, Opcode, NOP, sync_ops


class Parser:
    def __init__(self, func_or_data):
        if isinstance(func_or_data, bytes):
            self.buffer = BytesIO(func_or_data)
            self.ctx = Context()

        elif isinstance(func_or_data, str):
            code = compile(func_or_data, "<input>", "exec", optimize=0)
            self.buffer = BytesIO(code.co_code)
            self.ctx = Context(
                code.co_names,
                code.co_consts,
                code.co_varnames
            )

        else:
            try:
                code = func_or_data.__code__
            except AttributeError:
                code = func_or_data
            self.buffer = BytesIO(code.co_code)
            self.ctx = Context(
                code.co_names,
                code.co_consts,
                code.co_varnames
            )

        self.ops: List[Opcode] = []
        self._ops: List[Opcode] = []

    def unpack(self, fmt: str):
        size = struct.calcsize(fmt)
        data = struct.unpack(fmt, self.read(size))
        return data if len(data) != 1 else data[0]

    def read(self, num=None):
        return self.buffer.read(num)

    def tell(self):
        return self.buffer.tell()

    def seek(self, num):
        self.buffer.seek(num)

    def add_op(self, cls, arg=None):
        op = cls(*arg)
        self.ops.append(op)
        self._ops.append(op)

    def pop(self, index: int = None):
        return self.ops.pop(index) if index is not None else self.ops.pop()

    def last(self):
        if self.ops:
            return self.ops[-1]
        return NOP()

    def parse_bytecode(self, tree=True):
        from bytepatches import ops as op_data
        is_op = lambda op: type(op) == type and issubclass(op, Opcode) and op != Opcode
        ops_cls = [getattr(op_data, y)
                   for y in dir(op_data)
                   if is_op(getattr(op_data, y))]
        ops = {
            struct.unpack("B", x.op_byte)[0]: x
            for x in ops_cls
        }

        while True:
            pos = self.tell()
            if self.read(1):
                self.seek(pos)
                opcode, arg = self.unpack("BB")
                op = ops.get(opcode)
                if opcode == 1:
                    # POP_TOP
                    self.add_op(op, [arg])

                elif opcode == 19:
                    # BINARY_POWER
                    self.add_op(op, [arg, self.pop(-2), self.pop()])

                elif opcode == 20:
                    # BINARY_MULTIPLY
                    self.add_op(op, [arg, self.pop(), self.pop()])

                elif opcode == 22:
                    # BINARY_MODULO
                    self.add_op(op, [arg, self.pop(-2), self.pop()])

                elif opcode == 23:
                    # BINARY_ADD
                    self.add_op(op, [arg, self.pop(), self.pop()])

                elif opcode == 24:
                    # BINARY_SUBTRACT
                    self.add_op(op, [arg, self.pop(-2), self.pop()])

                elif opcode == 26:
                    self.add_op(op, [arg, self.pop(-2), self.pop()])

                elif opcode == 27:
                    # BINARY_TRUE_DIVIDE
                    self.add_op(op, [arg, self.pop(-2), self.pop()])

                elif opcode == 68:
                    # GET_ITER
                    self.add_op(op, [arg, self.pop()])

                elif opcode == 83:
                    # RETURN_VALUE
                    self.add_op(op, [arg, self.pop()])

                elif opcode == 87:
                    # POP_BLOCK
                    self.add_op(op, [arg])

                elif opcode == 90:
                    # STORE_NAME
                    self.add_op(op, [arg, self.ctx.load_name(arg), self.pop()])

                elif opcode == 93:
                    # FOR_ITER
                    self.add_op(op, [arg])

                elif opcode == 100:
                    # LOAD_CONST
                    self.add_op(op, [arg, self.ctx.load_const(arg)])

                elif opcode == 101:
                    # LOAD_NAME
                    self.add_op(op, [arg, self.ctx.load_name(arg)])

                elif opcode == 107:
                    # COMPARE_OP
                    self.add_op(op, [arg])

                elif opcode == 108:
                    # IMPORT_NAME
                    self.add_op(op, [arg, self.ctx.load_name(arg)])

                elif opcode == 110:
                    # JUMP_FORWARD
                    self.add_op(op, [arg])

                elif opcode == 113:
                    # JUMP_ABSOLUTE
                    self.add_op(op, [arg])

                elif opcode == 114:
                    # POP_JUMP_IF_FALSE
                    self.add_op(op, [arg, self.pop()])

                elif opcode == 116:
                    # LOAD_GLOBAL
                    self.add_op(op, [arg, self.ctx.load_name(arg)])

                elif opcode == 120:
                    # SETUP_LOOP
                    self.add_op(op, [arg])

                elif opcode == 124:
                    # LOAD_FAST
                    self.add_op(op, [arg, self.ctx.load_fast(arg)])

                elif opcode == 125:
                    # STORE_FAST
                    self.add_op(op, [arg, self.ctx.load_fast(arg), self.pop()])

                elif opcode == 131:
                    # CALL_FUNCTION
                    self.add_op(op, [arg, self.pop(-2), self.pop()])

                elif opcode == 132:
                    # MAKE_FUNCTION
                    self.pop()  # Remove load_const
                    code = [self.pop().arg]
                    if self.last().op_name == "BUILD_CONST_KEY_MAP":
                        code.insert(0, self.pop())
                    self.add_op(op, [arg, *code])

                elif opcode == 156:
                    # BUILD_CONST_KEY_MAP
                    types = [self.pop(-2) for _ in range(arg)]
                    self.add_op(op, [arg, self.pop(), types])

                elif opcode == 160:
                    # LOAD_METHOD
                    self.add_op(op, [arg, self.pop(), self.ctx.load_name(arg)])

                elif opcode == 161:
                    # CALL_METHOD
                    self.add_op(op, [arg, self.pop(-2), self.pop()])

                else:
                    self.seek(self.tell()-2)
                    import dis
                    dis.dis(self.read())
                    raise Exception(f"Unhandled opcode {opcode} with argument {arg}")

                self.last().set_bytecode_pos(int(pos/2))

            else:
                break

        sync_ops(self._ops)
        _p = [self._ops, self.ops][tree]
        return _p if len(_p) != 1 else _p[0]
