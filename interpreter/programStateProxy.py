from typing import List, Dict, Tuple, Union

from programState import ProgramState, StatusRegister, regToID, RunError, StopProgram, InstructionNode, SystemCall
import visualizeProxy
import nodes
import programContext


# setReg:: ProgramState -> str -> int -> ProgramState
@visualizeProxy.writeLogger
def setReg(state: ProgramState, name: str, value: int) -> ProgramState:
    regID: int = regToID(name)
    state.registers[regID] = value
    return state


# setReg:: ProgramState -> str -> int
@visualizeProxy.readLogger
def getReg(state: ProgramState, name: str) -> int:
    regID: int = regToID(name)
    return state.registers[regID]


# setALUState:: ProgramState -> StatusRegister -> ProgramState
# set the status register
@visualizeProxy.statusLogger
def setALUState(state: ProgramState, value: StatusRegister) -> Union[ProgramState, RunError]:
    state.status = value
    return state


# loadRegister:: ProgramState -> int -> int -> String -> ProgramState
# bitSize: the number of bits to load, either 32, 16 or 8 bit
# don't need to copy the ProgramState as setReg does that already
def loadRegister(state: ProgramState, address: int, bitsize: int, register: str) -> Union[ProgramState, RunError]:
    offset = address & 3
    if bitsize == 32 and offset != 0:
        return RunError("To load a word from memory, the address needs to be a multiple of 4", RunError.ErrorType.Error)
    elif bitsize == 16 and (address & 1) != 0:
        return RunError("To load a half-word from memory, the address needs to be a multiple of 2", RunError.ErrorType.Error)

    internal_address = address >> 2
    # check address is in range
    if internal_address < 0 or internal_address >= len(state.memory):
        return RunError(f"memory address out of range: {address}, must be in range [0...{len(state.memory)*4}]", RunError.ErrorType.Error)

    word = state.memory[internal_address]
    if not isinstance(word, nodes.DataNode):
        return RunError("It is not possible to load the contents of an instruction", RunError.ErrorType.Error)
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
def getInstructionFromMem(state: ProgramState, address: int) -> Union[InstructionNode, RunError]:
    if (address & 3) != 0:
        return RunError("To load an instruction from memory, the address needs to be a multiple of 4", RunError.ErrorType.Error)

    internal_address = address >> 2
    # check address is in range
    if internal_address < 0 or internal_address >= len(state.memory):
        return RunError(f"memory address out of range: {address}, must be in range [0...{len(state.memory) * 4}]", RunError.ErrorType.Error)

    word = state.memory[internal_address]
    if isinstance(word, InstructionNode):
        return word
    else:
        return RunError("Loaded data is no instruction", RunError.ErrorType.Error)


# storeRegister:: ProgramState -> int -> String -> int -> ProgramState
# bitSize: the number of bits to store, either 32, 16 or 8 bit
def storeRegister(state: ProgramState, address: int, register: str, bitsize: int) -> Union[ProgramState, RunError]:
    offset = address & 3
    if bitsize == 32 and offset != 0:
        return RunError("To store a word in memory, the address needs to be a multiple of 4", RunError.ErrorType.Error)
    elif bitsize == 16 and (address & 1) != 0:
        return RunError("To store a half-word in memory, the address needs to be a multiple of 2", RunError.ErrorType.Error)

    value = getReg(state, register)
    internal_address = address >> 2
    # check address is in range
    if internal_address < 0 or internal_address >= len(state.memory):
        return RunError(f"memory address out of range: {address}, must be in range [0...{len(state.memory) * 4}]", RunError.ErrorType.Error)

    word = state.memory[internal_address]
    if word.section == nodes.Node.Section.TEXT:
        return RunError("It is not possible to change the contents of a text section", RunError.ErrorType.Error)
    if not isinstance(word, nodes.DataNode):
        if bitsize == 32:
            return RunError("You are replacing the contents of an instruction", RunError.ErrorType.Warning)
        else:
            return RunError("It is not possible to change part of the contents of an instruction", RunError.ErrorType.Error)
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
        return RunError("Invalid bitsize", RunError.ErrorType.Error)


# getLabelAddress:: ProgramState -> str -> int
def getLabelAddress(state: ProgramState, label: str) -> Union[int, RunError]:
    if label not in state.labels.keys():
        return RunError(f"Unknown label: {label}", RunError.ErrorType.Error)
    return state.labels[label].address


# printAndReturn:: ProgramState -> (ProgramState, Either RunError or None)
# Implementation of the 'print_char' subroutine
# Note: prints a char to the default output
def subroutine_print_char(state: ProgramState) -> Tuple[ProgramState, Union[RunError, None]]:
    # print char
    r0 = getReg(state, "R0")
    print(chr(r0), end='')
    # mov PC, LR
    lr = getReg(state, "LR")
    return setReg(state, "PC", lr), None


# branchToLabel:: ProgramState -> (ProgramState, Either RunError or None)
def branchToLabel(state: ProgramState, label: str) -> Tuple[ProgramState, Union[RunError, None]]:
    # Save return address in LR
    state = setReg(state, "LR", getReg(state, "PC"))

    address: Union[int, RunError] = getLabelAddress(state, label)
    if isinstance(address, RunError):
        return state, RunError(f"Unknown startup label: {label}", RunError.ErrorType.Error)
    else:
        # Subtract 4 because we will add 4 to the address later in the run loop and we need to start at address and not address+4
        state = setReg(state, "PC", address - 4)
        state.hasReturned = False
        return state, None


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


# generateProgramState:: ProgramContext -> int -> String -> String -> ProgramState
# Generate a ProgramState based on a ProgramContext
def generateProgramState(context: programContext.ProgramContext, stackSize: int, startLabel: str, fileName: str, useGUI: bool) -> ProgramState:
    text = context.text + [SystemCall(subroutine_print_char, "print_char"),
                           # Subroutine to start the program and stop it afterwards
                           SystemCall(lambda s: branchToLabel(s, startLabel), "__STARTUP"),
                           SystemCall(lambda s: (s, StopProgram()), "__STARTUP")
                           ]

    mem: List[nodes.Node] = [nodes.DataNode(0, "SETUP") for _ in range(stackSize >> 2)] + text + context.bss + context.data
    regs = [0 for _ in range(16)]
    regs[regToID("SP")] = stackSize
    status = StatusRegister(False, False, False, False)
    labelList = context.labels + [nodes.Label("print_char", nodes.Node.Section.TEXT, len(context.text)), nodes.Label("__STACKSIZE", nodes.Node.Section.TEXT, 0)]

    labels = convertLabelsToDict(labelList, stackSize, len(text), len(context.bss))

    regs[regToID("PC")] = labels["print_char"].address+4
    return ProgramState(regs, status, mem, labels, fileName, useGUI)
