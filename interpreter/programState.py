from copy import deepcopy
from typing import List, Dict

import programContext
import nodes


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
# bitSize: the number of bits to load, either 32, 16 or 8 bit
def getFromMem(state: ProgramState, address: int, bitsize: int) -> nodes.Node:
    # TODO check address is in range
    offset = address & 3
    if bitsize == 32 and offset != 0:
        # TODO err
        pass
    elif bitsize == 16 and (address&1) != 0:
        # TODO err
        pass

    internal_address = address >> 2

    word = state.memory[internal_address]
    if bitsize == 32:
        return word
    elif bitsize == 16:
        return nodes.DataNode((word.value >> (1-offset)*16) & 0xFFFF)
    elif bitsize == 8:
        return nodes.DataNode((word.value >> (3-offset)*8) & 0xFF)
    else:
        print("BITSIZE")
        # TODO error - invalid bitsize
        return nodes.DataNode(-1)


def storeInMem(state: ProgramState, address: int, value: int, bitsize: int) -> ProgramState:
    # TODO check address is in range
    newState = deepcopy(state)

    offset = address & 3
    if bitsize == 32 and offset != 0:
        # TODO err
        pass
    elif bitsize == 16 and (address & 1) != 0:
        # TODO err
        pass

    internal_address = address >> 2

    if bitsize == 32:
        newState.memory[internal_address] = nodes.DataNode(value)
        return newState
    elif bitsize == 16:
        word = state.memory[internal_address].value
        newState.memory[internal_address] = nodes.DataNode(
            ((value << ((1 - offset) * 16)) & 0xFFFF) |
            (word & (0xFFFF << offset * 16))
        )
        return newState
    elif bitsize == 8:
        word = state.memory[internal_address].value
        newState.memory[internal_address] = nodes.DataNode((
            ((value << ((3 - offset) * 8)) & 0xFF) |
            (word & (0xFFFFFF00FFFFFF >> offset * 8))
        ) & 0xFFFFFFFF)
        return newState
    else:
        print("BITSIZE")
        # TODO error - invalid bitsize
        return state


# getLabelAddress:: ProgramState -> str -> int
def getLabelAddress(state: ProgramState, label: str) -> int:
    # TODO check label exists
    return state.labels[label].address


def setALUState(state: ProgramState, value: StatusRegister) -> ProgramState:
    newState = deepcopy(state)
    newState.status = value
    return newState


def printAndReturn(state: ProgramState) -> ProgramState:
    r0 = getReg(state, "R0")
    print(chr(r0), end='')
    lr = getReg(state, "LR")
    return setReg(state, "PC", lr)


def generateProgramState(context: programContext.ProgramContext, stackSize: int, startLabel: str) -> ProgramState:
    text = context.text + [nodes.InstructionNode(nodes.Node.Section.TEXT, -1, printAndReturn)]
    printlabel = nodes.Label("print_char", nodes.Node.Section.TEXT, len(text)-1)

    mem: List[nodes.Node] = [nodes.DataNode(0) for _ in range(stackSize>>2)] + text + context.bss + context.data
    regs = [0 for _ in range(16)]
    regs[regToID("SP")] = stackSize
    status = StatusRegister(False, False, False, False)
    labels = context.labels.copy()
    labels["print_char"] = printlabel

    # TODO no FP
    for k in labels.keys():
        label = labels[k]
        if label.section == nodes.Node.Section.TEXT:
            label.address = stackSize + 4*label.address
        elif label.section == nodes.Node.Section.BSS:
            label.address = stackSize + 4*len(text) + 4*label.address
        elif label.section == nodes.Node.Section.DATA:
            label.address = stackSize + (4*len(text)) + (4*len(context.bss)) + (4*label.address)
        labels[k] = label

    regs[regToID("PC")] = labels[startLabel].address
    return ProgramState(regs, status, mem, labels)
