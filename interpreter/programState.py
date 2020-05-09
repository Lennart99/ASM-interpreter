from typing import List, Dict, Callable, Tuple
from enum import Enum

import nodes


class RunError:
    class ErrorType(Enum):
        NoError = 0
        Warning = 1
        Error = 2
        # No __str__ implemented because Enum implements it itself

    def __init__(self, message: str, errType: ErrorType):
        self.message = ("Runtime Error: " if errType == RunError.ErrorType.Error else "Runtime Warning: ") + message
        self.errorType = errType

    def __repr__(self) -> str:
        return self.message

    def __str__(self) -> str:
        return self.message


# This error is used to stop the interpreter when the program has returned
class StopProgram(RunError):
    def __init__(self):
        super().__init__("Program has stopped", RunError.ErrorType.NoError)


class StatusRegister:
    def __init__(self, n: bool = False, z: bool = False, c: bool = False, v: bool = False):
        self.N: bool = n
        self.Z: bool = z
        self.C: bool = c
        self.V: bool = v

    def __str__(self) -> str:
        return "{}({}, {}, {}, {})". \
            format(type(self).__name__, self.N, self.Z, self.C, self.V)

    def __repr__(self) -> str:
        return self.__str__()


class ProgramState:
    def __init__(self, regs: List[int], status: StatusRegister, memory: List[nodes.Node], labels: Dict[str, nodes.Label], file: str, useGUI: bool):
        self.registers: List[int] = regs
        self.status: StatusRegister = status
        self.memory: List[nodes.Node] = memory
        self.labels: Dict[str, nodes.Label] = labels
        self.fileName = file
        self.hasReturned = True
        self.visualizer: bool = useGUI

    def __str__(self) -> str:
        return "{}({}, {})". \
            format(type(self).__name__, self.registers, self.status)

    def __repr__(self) -> str:
        return self.__str__()


class InstructionNode(nodes.Node):
    # InstructionNode:: Node.Section -> int -> (ProgramState -> (ProgramState, RunError)) -> InstructionNode
    def __init__(self, section: nodes.Node.Section, line: int, func: Callable[[ProgramState], Tuple[ProgramState, RunError]]):
        super().__init__(section, line)
        self.function: Callable[[ProgramState], Tuple[ProgramState, RunError]] = func

    def __str__(self) -> str:
        return "{}({}, {}, {})".\
            format(type(self).__name__, self.section, self.line, self.function)


class SystemCall(InstructionNode):
    # InstructionNode:: Node.Section -> int -> (ProgramState -> (ProgramState, RunError)) -> InstructionNode
    def __init__(self, func: Callable[[ProgramState], Tuple[ProgramState, RunError]], name: str):
        super().__init__(nodes.Node.Section.TEXT, -1, func)
        self.name = name

    def __str__(self) -> str:
        return "{}({}, internal function {})".\
            format(type(self).__name__, self.section, self.name)


# regToID:: str -> int
def regToID(name: str) -> int:
    name = name.upper()
    if name[0] == "R":
        return int(name[1:3])
    elif name == "SP":
        return 13
    elif name == "LR":
        return 14
    elif name == "PC":
        return 15
    else:
        # The name of the register can't be unknown because it then would not be recognized as such
        print("Invalid register", name)
        return -1
