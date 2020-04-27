from typing import Callable
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


class InstructionNode(Node):
    # TODO Callable typing
    def __init__(self, section: Node.Section, line: int, func: Callable):
        super().__init__(section, line)
        self.function = func


class Label:
    def __init__(self, name: str, section: Node.Section, address: int):
        self.name = name
        self.section: Node.Section = section
        self.address: int = address

    def __str__(self) -> str:
        return "{}({}, {}, {})".\
            format(type(self).__name__, self.name, self.section, self.address)

    def __repr__(self) -> str:
        return self.__str__()


class ErrorNode(Node):
    def __init__(self, message: str):
        super().__init__(Node.Section.TEXT, 0)
        self.message: str = message

    def __str__(self) -> str:
        return self.message
