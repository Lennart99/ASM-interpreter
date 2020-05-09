from enum import Enum


class Node:
    class Section(Enum):
        TEXT = 0
        BSS = 1
        DATA = 2
        # No __str__ implemented because Enum implements it itself

    def __init__(self, section: Section, line: int):
        self.section: Node.Section = section
        self.line: int = line

    def __str__(self) -> str:
        return "{}({}, {})".\
            format(type(self).__name__, self.section, self.line)

    def __repr__(self) -> str:
        return self.__str__()


class DataNode(Node):
    def __init__(self, val: int, source: str, section: Node.Section = Node.Section.BSS, line: int = -1):
        super().__init__(section, line)
        self.value = val
        # tels from which register was this value was stored, useful while generating a stacktrace
        self.source = source

    def __str__(self) -> str:
        return "{}({})".\
            format(type(self).__name__, hex(self.value))


class ErrorNode(Node):
    def __init__(self, message: str):
        super().__init__(Node.Section.TEXT, -1)
        self.message: str = message

    def __str__(self) -> str:
        return self.message


class Label:
    def __init__(self, name: str, section: Node.Section, address: int):
        self.name: str = name
        self.section: Node.Section = section
        self.address: int = address

    def __str__(self) -> str:
        return "{}({}, {}, {})".\
            format(type(self).__name__, self.name, self.section, self.address)

    def __repr__(self) -> str:
        return self.__str__()
