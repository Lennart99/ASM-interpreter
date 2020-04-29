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
def getDataFromMem(state: ProgramState, address: int, bitsize: int) -> int:
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
        return word.value
    elif bitsize == 16:
        # TODO check the node is a DataNode
        return (word.value >> (1-offset)*16) & 0xFFFF
    elif bitsize == 8:
        # TODO check the node is a DataNode
        return (word.value >> (3-offset)*8) & 0xFF
    else:
        # TODO error - invalid bitsize
        return -1


# getFromMem:: ProgramState -> int -> int -> int
# bitSize: the number of bits to load, either 32, 16 or 8 bit
def getInstructionFromMem(state: ProgramState, address: int) -> nodes.InstructionNode:
    # TODO check address is in range
    if (address & 3) != 0:
        # TODO err
        pass

    internal_address = address >> 2

    word = state.memory[internal_address]
    if isinstance(word, nodes.InstructionNode):
        return word
    else:
        # TODO error
        pass


# storeInMem:: ProgramState -> int -> int -> int -> ProgramState
# bitSize: the number of bits to store, either 32, 16 or 8 bit
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
        # TODO check the node is a DataNode and warn the user otherwise
        newState.memory[internal_address] = nodes.DataNode(value)
        return newState
    elif bitsize == 16:
        # TODO check the node is a DataNode
        word = state.memory[internal_address].value
        newState.memory[internal_address] = nodes.DataNode(
            ((value << ((1 - offset) * 16)) & 0xFFFF) |
            (word & (0xFFFF << offset * 16))
        )
        return newState
    elif bitsize == 8:
        # TODO check the node is a DataNode
        word = state.memory[internal_address].value
        newState.memory[internal_address] = nodes.DataNode((
            ((value << ((3 - offset) * 8)) & 0xFF) |
            (word & (0xFFFFFF00FFFFFF >> offset * 8))
        ) & 0xFFFFFFFF)
        return newState
    else:
        # TODO error - invalid bitsize
        return state


# getLabelAddress:: ProgramState -> str -> int
def getLabelAddress(state: ProgramState, label: str) -> int:
    # TODO check label exists
    return state.labels[label].address


# setALUState:: ProgramState -> StatusRegister -> ProgramState
# set the status register
def setALUState(state: ProgramState, value: StatusRegister) -> ProgramState:
    newState = deepcopy(state)
    newState.status = value
    return newState


# printAndReturn:: ProgramState -> ProgramState
# Implementation of the 'print_char' subroutine
# Note: prints a char to the default output
def subroutine_print_char(state: ProgramState) -> ProgramState:
    r0 = getReg(state, "R0")
    print(chr(r0), end='')
    lr = getReg(state, "LR")
    return setReg(state, "PC", lr)


# convertLabelsToDict:: [label] -> int -> int -> int -> {str, label}
# converts a list of labels to a dict of labels
def convertLabelsToDict(labelList: List[nodes.Label], stackSize: int, textSize: int, bssSize: int) -> \
        Dict[str, nodes.Label]:
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
    text = context.text + [nodes.InstructionNode(nodes.Node.Section.TEXT, -1, subroutine_print_char)]

    mem: List[nodes.Node] = [nodes.DataNode(0) for _ in range(stackSize >> 2)] + text + context.bss + context.data
    regs = [0 for _ in range(16)]
    regs[regToID("SP")] = stackSize
    status = StatusRegister(False, False, False, False)
    labelList = context.labels + [nodes.Label("print_char", nodes.Node.Section.TEXT, len(context.text))]

    labels = convertLabelsToDict(labelList, stackSize, len(text), len(context.bss))

    regs[regToID("PC")] = labels[startLabel].address
    return ProgramState(regs, status, mem, labels)
