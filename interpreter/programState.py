from copy import deepcopy
from typing import List


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
    def __init__(self, regs: List[int], status: StatusRegister):
        self.registers: List[int] = regs
        self.status: StatusRegister = status

    def __str__(self) -> str:
        return "{}({}, {})". \
            format(type(self).__name__, self.registers, self.status)

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
        return -1


# setReg:: ProgramState -> str -> int -> ProgramState
def setReg(state: ProgramState, name: str, value: int) -> ProgramState:
    newState = deepcopy(state)
    regID = regToID(name)
    newState.registers[regID] = value
    return newState


# setReg:: ProgramState -> str -> int
def getReg(state: ProgramState, name: str) -> int:
    regID: int = regToID(name)
    return state.registers[regID]


# getFromMem:: ProgramState -> int -> int -> int
# bitSize: the number ob bits to load, either 32, 16 or 8 bit
def getFromMem(state: ProgramState, adress: int, bitsize: int) -> int:
    # TODO implement memory
    return -1


def storeInMem(state: ProgramState, adress: int, value: int, bitsize: int) -> ProgramState:
    # TODO implement memory
    pass


# getLabelAddress:: ProgramState -> str -> int
def getLabelAddress(state: ProgramState, label: str) -> int:
    # TODO implement memory
    return -1


def setALUState(state: ProgramState, value: StatusRegister) -> ProgramState:
    newState = deepcopy(state)
    newState.status = value
    return newState
