from typing import Callable, List
from enum import Enum


class Node:
    class Section(Enum):
        TEXT = 0
        BSS = 1
        DATA = 2

    def __init__(self, section: Section, line: int):
        self.section: Node.Section = section
        self.line: int = line

    def __str__(self) -> str:
        return "{}({}, {})".\
            format(type(self).__name__, self.section, self.line)

    def __repr__(self) -> str:
        return self.__str__()


class DataNode(Node):
    def __init__(self, val: int, section: Node.Section = Node.Section.BSS, line: int = -1):
        super().__init__(section, line)
        self.value = val

    def __str__(self) -> str:
        return "{}({})".\
            format(type(self).__name__, hex(self.value))


class InstructionNode(Node):
    # InstructionNode:: Node.Section -> int -> (ProgramState -> ProgramState) -> InstructionNode
    # can't add type parameters to func because of a circular import
    def __init__(self, section: Node.Section, line: int, func: Callable):
        super().__init__(section, line)
        self.function = func

    def __str__(self) -> str:
        return "{}({}, {}, {})".\
            format(type(self).__name__, self.section, self.line, self.function)


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


class StringNode(Node):
    def __init__(self, section: Node.Section, line: int, contents: List[int]):
        super().__init__(section, line)
        self.contents: List[int] = contents

    def __str__(self) -> str:
        return "{}({}, {}, {})".\
            format(type(self).__name__, self.line, self.section, self.contents)

    def __repr__(self) -> str:
        return self.__str__()


class ErrorNode(Node):
    def __init__(self, message: str):
        super().__init__(Node.Section.TEXT, -1)
        self.message: str = message

    def __str__(self) -> str:
        return self.message
