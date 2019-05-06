import datetime
import marshal
import struct
import types
from io import BytesIO

from bytepatches import utils
from bytepatches.ops import pretty_printer
from bytepatches.parser import Parser


class PycParser:
    def __init__(self, fn):
        if isinstance(fn, str):
            with open(fn, "rb") as f:
                self.buf = BytesIO(f.read())
        else:
            self.buf = BytesIO(fn.read())

        self.timestamp = None
        self.version = None
        self.content = None
        self.size = 0
        self.filename = [None, fn][isinstance(fn, str)]

        self.read = self.buf.read
        self.seek = self.buf.seek
        self.tell = self.buf.tell

    def __repr__(self):
        return (f"{self.filename or 'file.pyc'}(file_size={self.size}, "
                f"last_edited={self.timestamp}, contents={self.content})")

    def unpack(self, fmt):
        size = struct.calcsize(fmt)
        data = self.read(size)
        res = struct.unpack(fmt, data)
        return res[0] if len(res) == 1 else res

    def parse(self):
        self.parse_file()
        self.parse_body()

    def parse_file(self):
        self.version = self.unpack("H")
        assert self.read(2) == b"\r\n"  # CRLF
        self.read(4)  # NULL
        timestamp, self.size = self.unpack("ii")
        self.timestamp = datetime.datetime.fromtimestamp(timestamp)
        self.seek(16)
        self.content = marshal.loads(self.read())

    def parse_body(self):
        # TODO
        self.content = Parser(self.content).parse_bytecode(True)
        pretty_printer.pprint(self.content)


if __name__ == "__main__":
    def try_thing(data):
        parser = PycParser(BytesIO(b'B\r\r\n\x00\x00\x00\x00\xae\x96\xa8\\9\x16\x00\x00' + data))
        parser.parse()
        print(parser)

    def thing():
        return print(10)

    parser = PycParser("__pycache__/utils.cpython-37.pyc")
    parser.parse()
    print(parser)

