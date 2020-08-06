from typing import List, Union, Tuple, Dict

import nodes
import programState

from programState import regToID


class ProgramContext:
    def __init__(self, text: List[nodes.Node], bss: List[nodes.Node], data: List[nodes.Node], labels: List[nodes.Label], globalLabels: List[str]):
        self.text: List[nodes.Node] = text
        self.bss:  List[nodes.Node] = bss
        self.data: List[nodes.Node] = data
        self.labels: List[nodes.Label] = labels
        self.globalLabels: List[str] = globalLabels

    def __str__(self) -> str:
        return ".text: {} \n.bss: {} \n.data: {} \nLabels: {} \nGlobal labels: {}". \
            format(self.text, self.bss, self.data, self.labels, self.globalLabels)

    def __repr__(self) -> str:
        return self.__str__()


# subroutine_print_char:: ProgramState -> ProgramState, Either RunError or None
# Implementation of the 'print_char' subroutine
# Note: prints a char to the default output
def subroutine_print_char(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
    # print char
    r0 = state.getReg("R0")
    print(chr(r0), end='')
    # mov PC, LR
    lr = state.getReg("LR")
    state.setReg("PC", lr)
    return state, None


# subroutine_print_int:: ProgramState -> ProgramState, Either RunError or None
# Implementation of the 'print_int' subroutine
# Note: prints an integer to the default output and adds a newline
def subroutine_print_int(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
    # print char
    r0 = state.getReg("R0")
    print(int(r0), end='\n')
    # mov PC, LR
    lr = state.getReg("LR")
    state.setReg("PC", lr)
    return state, None


# branchToLabel:: ProgramState -> (ProgramState, Either RunError or None)
def branchToLabel(state: programState.ProgramState, label: str) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
    # Save return address in LR
    state.setReg("LR", state.getReg("PC"))

    address: Union[int, programState.RunError] = state.getLabelAddress(label)
    if isinstance(address, programState.RunError):
        return state, programState.RunError(f"Unknown startup label: {label}", programState.RunError.ErrorType.Error)
    else:
        # Subtract 4 because we will add 4 to the address later in the run loop and we need to start at address and not address+4
        state.setReg("PC", address - 4)
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
def generateProgramState(context: ProgramContext, stackSize: int, startLabel: str, fileName: str, useGUI: bool) -> programState.ProgramState:
    text: List[nodes.Node] = context.text + [nodes.SystemCall(subroutine_print_char, "print_char"),
                                             nodes.SystemCall(subroutine_print_int, "print_int"),
                                             # Subroutine to start the program and stop it afterwards
                                             nodes.SystemCall(lambda s: branchToLabel(s, startLabel), "__STARTUP"),
                                             nodes.SystemCall(lambda s: (s, programState.StopProgram()), "__STARTUP")
                                             ]

    mem: List[nodes.Node] = [nodes.DataNode(0, "SETUP") for _ in range(stackSize >> 2)] + text + context.bss + context.data
    regs = [0 for _ in range(16)]
    regs[regToID("SP")] = stackSize
    status = programState.StatusRegister(False, False, False, False)
    labelList = context.labels + [nodes.Label("print_char", nodes.Node.Section.TEXT, len(context.text)),
                                  nodes.Label("print_int", nodes.Node.Section.TEXT, len(context.text)+1),
                                  nodes.Label("__STACKSIZE", nodes.Node.Section.TEXT, 0)
                                  ]

    labels = convertLabelsToDict(labelList, stackSize, len(text), len(context.bss))

    regs[regToID("PC")] = labels["print_int"].address+4
    return programState.ProgramState(regs, status, mem, labels, fileName, useGUI)
