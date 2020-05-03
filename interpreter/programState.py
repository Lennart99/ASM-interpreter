from copy import deepcopy
from functools import wraps
from typing import List, Dict

import programContext
import nodes


# copy_args ((A, B, ...) -> C) -> ((A, B, ...) -> C)
# A decorator to copy all arguments of a function before calling the function
def copy_args(f):
    @wraps(f)
    def inner(*args, **kwargs):
        # return f(*deepcopy(args), **deepcopy(kwargs))
        return f(*args, **kwargs)
    return inner


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
    def __init__(self, regs: List[int], status: StatusRegister, memory: List[nodes.Node], labels: Dict[str, nodes.Label]):
        self.registers: List[int] = regs
        self.status: StatusRegister = status
        self.memory: List[nodes.Node] = memory
        self.labels: Dict[str, nodes.Label] = labels

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
        print("Invalid register", name)
        return -1


# setReg:: ProgramState -> str -> int -> ProgramState
@copy_args
def setReg(state: ProgramState, name: str, value: int) -> ProgramState:
    regID = regToID(name)
    if regID == -1:
        # TODO err
        return state
    state.registers[regID] = value
    return state


# setReg:: ProgramState -> str -> int
def getReg(state: ProgramState, name: str) -> int:
    regID: int = regToID(name)
    if regID == -1:
        # TODO err
        return -1
    return state.registers[regID]


# loadRegister:: ProgramState -> int -> int -> String -> ProgramState
# bitSize: the number of bits to load, either 32, 16 or 8 bit
# don't need to copy the ProgramState as setReg does that already
def loadRegister(state: ProgramState, address: int, bitsize: int, register: str) -> ProgramState:
    offset = address & 3
    if bitsize == 32 and offset != 0:
        # TODO err
        return state
    elif bitsize == 16 and (address&1) != 0:
        # TODO err
        return state

    internal_address = address >> 2
    # check address is in range
    if internal_address < 0 or internal_address >= len(state.memory):
        # TODO err
        return state

    word = state.memory[internal_address]
    if not isinstance(word, nodes.DataNode):
        # TODO error
        return state
    if bitsize == 32:
        return setReg(state, register, word.value)
    elif bitsize == 16:
        return setReg(state, register, (word.value >> (1-offset)*16) & 0xFFFF)
    elif bitsize == 8:
        return setReg(state, register, (word.value >> (3-offset)*8) & 0xFF)
    else:
        # Invalid bitsize, should never happen
        print("BITSIZE", bitsize)
        return state


# getInstructionFromMem:: ProgramState -> int -> InstructionNode
def getInstructionFromMem(state: ProgramState, address: int) -> nodes.InstructionNode:
    if (address & 3) != 0:
        # TODO err
        pass

    internal_address = address >> 2
    # check address is in range
    if internal_address < 0 or internal_address >= len(state.memory):
        # TODO err
        pass

    word = state.memory[internal_address]
    if isinstance(word, nodes.InstructionNode):
        return word
    else:
        # TODO error
        pass


# storeRegister:: ProgramState -> int -> String -> int -> ProgramState
# bitSize: the number of bits to store, either 32, 16 or 8 bit
@copy_args
def storeRegister(state: ProgramState, address: int, register: str, bitsize: int) -> ProgramState:
    offset = address & 3
    if bitsize == 32 and offset != 0:
        # TODO err
        return state
    elif bitsize == 16 and (address & 1) != 0:
        # TODO err
        return state

    value = getReg(state, register)
    internal_address = address >> 2

    word = state.memory[internal_address]
    if word.section == nodes.Node.Section.TEXT:
        # TODO ERR - can't change .text
        return state
    if not isinstance(word, nodes.DataNode):
        if bitsize == 32:
            # TODO WARN
            pass
        else:
            # TODO ERR - unsupported
            return state
    if bitsize == 32:
        state.memory[internal_address] = nodes.DataNode(value, register)
        return state
    elif bitsize == 16:
        state.memory[internal_address] = nodes.DataNode(
            ((value & 0xFFFF) << ((2 - offset) * 8)) |
            (word.value & (0xFFFF << offset * 8)), register)
        return state
    elif bitsize == 8:
        state.memory[internal_address] = nodes.DataNode((
            ((value & 0xFF) << ((3 - offset) * 8)) |
            (word.value & (0xFFFFFF00FFFFFF >> offset * 8))
        ) & 0xFFFFFFFF, register)
        return state
    else:
        # Invalid bitsize, should never happen
        print("BITSIZE", bitsize)
        return state


# getLabelAddress:: ProgramState -> str -> int
def getLabelAddress(state: ProgramState, label: str) -> int:
    if label not in state.labels.keys():
        # TODO error
        return -1
    return state.labels[label].address


# setALUState:: ProgramState -> StatusRegister -> ProgramState
# set the status register
@copy_args
def setALUState(state: ProgramState, value: StatusRegister) -> ProgramState:
    state.status = value
    return state


# printAndReturn:: ProgramState -> ProgramState
# Implementation of the 'print_char' subroutine
# Note: prints a char to the default output
def subroutine_print_char(state: ProgramState) -> ProgramState:
    # print char
    r0 = getReg(state, "R0")
    print(chr(r0), end='')
    # mov PC, LR
    lr = getReg(state, "LR")
    return setReg(state, "PC", lr)


# convertLabelsToDict:: [label] -> int -> int -> int -> {str, label}
# converts a list of labels to a dict of labels
def convertLabelsToDict(labelList: List[nodes.Label], stackSize: int, textSize: int, bssSize: int) -> Dict[str, nodes.Label]:
    if len(labelList) == 0:
        return {}
    label, *tail = labelList

    if label.section == nodes.Node.Section.TEXT:
        label = nodes.Label(label.name, label.section, stackSize + (4*label.address))
    elif label.section == nodes.Node.Section.BSS:
        label = nodes.Label(label.name, label.section, stackSize + (4*textSize) + (4*label.address))
    elif label.section == nodes.Node.Section.DATA:
        label = nodes.Label(label.name, label.section, stackSize + (4*textSize) + (4*bssSize) + (4*label.address))

    res = convertLabelsToDict(tail, stackSize, textSize, bssSize)
    res[label.name] = label
    return res


# generateProgramState:: ProgramContext -> int -> str -> ProgramState
# Generate a ProgramState based on a ProgramContext
def generateProgramState(context: programContext.ProgramContext, stackSize: int, startLabel: str) -> ProgramState:
    text = context.text + [nodes.InstructionNode(nodes.Node.Section.TEXT, -1, subroutine_print_char),
                           nodes.InstructionNode(nodes.Node.Section.TEXT, -1, lambda s: setReg(setReg(s, "LR", getReg(s, "PC")), "PC", getLabelAddress(s, startLabel) - 4)),
                           # TODO force-stop with exception
                           nodes.InstructionNode(nodes.Node.Section.TEXT, -1, lambda s: setReg(s, "PC", 0))
                           ]

    mem: List[nodes.Node] = [nodes.DataNode(0, "SETUP") for _ in range(stackSize >> 2)] + text + context.bss + context.data
    regs = [0 for _ in range(16)]
    regs[regToID("SP")] = stackSize
    status = StatusRegister(False, False, False, False)
    labelList = context.labels + [nodes.Label("print_char", nodes.Node.Section.TEXT, len(context.text)), nodes.Label("__STACKSIZE", nodes.Node.Section.TEXT, 0)]

    labels = convertLabelsToDict(labelList, stackSize, len(text), len(context.bss))

    regs[regToID("PC")] = labels["print_char"].address+4
    return ProgramState(regs, status, mem, labels)
