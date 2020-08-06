from typing import List, Dict, Callable, Tuple, Union
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
        return "{}({}, {})".format(type(self).__name__, self.registers, self.status)

    def __repr__(self) -> str:
        return self.__str__()

    # setReg:: ProgramState -> str -> int -> None
    def setReg(self, name: str, value: int):
        regID: int = regToID(name)
        self.registers[regID] = value

    # setReg:: ProgramState -> str -> int
    def getReg(self, name: str) -> int:
        regID: int = regToID(name)
        return self.registers[regID]

    # setALUState:: ProgramState -> StatusRegister -> None
    # set the status register
    def setALUState(self, value: StatusRegister):
        self.status = value

    # loadRegister:: ProgramState -> int -> int -> String -> RunError
    # bitSize: the number of bits to load, either 32, 16 or 8 bit
    # don't need to copy the ProgramState as setReg does that already
    def loadRegister(self, address: int, bitSize: int, register: str) -> Union[RunError, None]:
        offset = address & 3
        if bitSize == 32 and offset != 0:
            return RunError("To load a word from memory, the address needs to be a multiple of 4", RunError.ErrorType.Error)
        elif bitSize == 16 and (address & 1) != 0:
            return RunError("To load a half-word from memory, the address needs to be a multiple of 2", RunError.ErrorType.Error)

        internal_address = address >> 2
        # check address is in range
        if internal_address < 0 or internal_address >= len(self.memory):
            return RunError(f"memory address out of range: {address}, must be in range [0...{len(self.memory) * 4}]", RunError.ErrorType.Error)

        word = self.memory[internal_address]
        if not isinstance(word, nodes.DataNode):
            return RunError("It is not possible to load the contents of an instruction", RunError.ErrorType.Error)
        if bitSize == 32:
            self.setReg(register, word.value)
        elif bitSize == 16:
            self.setReg(register, (word.value >> (1 - offset) * 16) & 0xFFFF)
        elif bitSize == 8:
            self.setReg(register, (word.value >> (3 - offset) * 8) & 0xFF)
        else:
            # Invalid bitsize, should never happen
            print("BITSIZE", bitSize)
        return None

    # getInstructionFromMem:: ProgramState -> int -> Either InstructionNode or RunError
    def getInstructionFromMem(self, address: int) -> Union[nodes.InstructionNode, RunError]:
        if (address & 3) != 0:
            return RunError("To load an instruction from memory, the address needs to be a multiple of 4", RunError.ErrorType.Error)

        internal_address = address >> 2
        # check address is in range
        if internal_address < 0 or internal_address >= len(self.memory):
            return RunError(f"memory address out of range: {address}, must be in range [0...{len(self.memory) * 4}]", RunError.ErrorType.Error)

        word = self.memory[internal_address]
        if isinstance(word, nodes.InstructionNode):
            return word
        else:
            return RunError("Loaded data is no instruction", RunError.ErrorType.Error)

    # storeRegister:: ProgramState -> int -> String -> int -> RunError
    # bitSize: the number of bits to store, either 32, 16 or 8 bit
    def storeRegister(self, address: int, register: str, bitSize: int) -> Union[RunError, None]:
        offset = address & 3
        if bitSize == 32 and offset != 0:
            return RunError("To store a word in memory, the address needs to be a multiple of 4", RunError.ErrorType.Error)
        elif bitSize == 16 and (address & 1) != 0:
            return RunError("To store a half-word in memory, the address needs to be a multiple of 2", RunError.ErrorType.Error)

        value = self.getReg(register)
        internal_address = address >> 2
        # check address is in range
        if internal_address < 0 or internal_address >= len(self.memory):
            return RunError(f"memory address out of range: {address}, must be in range [0...{len(self.memory) * 4}]", RunError.ErrorType.Error)

        word = self.memory[internal_address]
        if word.section == nodes.Node.Section.TEXT:
            return RunError("It is not possible to change the contents of a text section", RunError.ErrorType.Error)
        if not isinstance(word, nodes.DataNode):
            if bitSize == 32:
                return RunError("You are replacing the contents of an instruction", RunError.ErrorType.Warning)
            else:
                return RunError("It is not possible to change part of the contents of an instruction", RunError.ErrorType.Error)
        if bitSize == 32:
            self.memory[internal_address] = nodes.DataNode(value, register)
            return None
        elif bitSize == 16:
            self.memory[internal_address] = nodes.DataNode(
                ((value & 0xFFFF) << ((2 - offset) * 8)) |
                (word.value & (0xFFFF << offset * 8)), register)
            return None
        elif bitSize == 8:
            self.memory[internal_address] = nodes.DataNode((
                ((value & 0xFF) << ((3 - offset) * 8)) |
                (word.value & (0xFFFFFF00FFFFFF >> offset * 8))
            ) & 0xFFFFFFFF, register)
            return None
        else:
            # Invalid bitsize, should never happen
            return RunError("Invalid bitsize", RunError.ErrorType.Error)

    # getLabelAddress:: ProgramState -> str -> int
    def getLabelAddress(self, label: str) -> Union[int, RunError]:
        if label not in self.labels.keys():
            return RunError(f"Unknown label: {label}", RunError.ErrorType.Error)
        return self.labels[label].address
