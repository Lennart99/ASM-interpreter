from functools import wraps
from typing import List, Tuple, Union, Callable
from tkinter import END
import builtins

import visualizer
import programState


# Decorators

# Updates the visualizer when a register is changed
# writeLogger:: (ProgramState -> String -> int -> ProgramState) -> (ProgramState -> String -> int -> ProgramState)
def writeLogger(f: Callable[[programState.ProgramState, str, int], programState.ProgramState]) -> Callable[[programState.ProgramState, str, int], programState.ProgramState]:
    @wraps(f)
    # inner:: ProgramState -> String -> int -> ProgramState
    def inner(state: programState.ProgramState, name: str, value: int) -> programState.ProgramState:
        if state.visualizer:
            visualizer.reg_items[programState.regToID(name)].setValue(value)
        return f(state, name, value)
    return inner


# Updates the visualizer when a register is read
# readLogger:: (ProgramState -> String -> int) -> (ProgramState -> String -> int)
def readLogger(f: Callable[[programState.ProgramState, str], int]) -> Callable[[programState.ProgramState, str], int]:
    @wraps(f)
    # inner:: ProgramState -> String -> int
    def inner(state: programState.ProgramState, name: str) -> int:
        if state.visualizer:
            visualizer.reg_items[programState.regToID(name)].processRead()
        return f(state, name)
    return inner


# Updates the visualizer when the status register is changed
# statusLogger:: (ProgramState -> StatusRegister -> ProgramState) -> (ProgramState -> StatusRegister -> ProgramState)
def statusLogger(f: Callable[[programState.ProgramState, programState.StatusRegister], programState.ProgramState]) -> Callable[[programState.ProgramState, programState.StatusRegister], programState.ProgramState]:
    @wraps(f)
    # inner:: ProgramState -> StatusRegister -> ProgramState
    def inner(state: programState.ProgramState, value: programState.StatusRegister) -> programState.ProgramState:
        if state.visualizer:
            setStatusRegs(value.N, value.Z, value.C, value.V)
        return f(state, value)
    return inner


# Decorator to update the visualizer and wait until the next instruction can be executed
# runLogger:: InstructionNode -> [String] -> (ProgramState -> (ProgramState, RunError))
def runLogger(node: programState.InstructionNode, lines: List[str]) -> Callable[[programState.ProgramState], Tuple[programState.ProgramState, programState.RunError]]:
    @wraps(node.function)
    # inner:: ProgramState -> (ProgramState, RunError)
    def inner(state: programState.ProgramState) -> Tuple[programState.ProgramState, programState.RunError]:
        if state.visualizer:
            resetRegs()
            state, err = node.function(state)
            if isinstance(node, programState.SystemCall):
                setLineInternalFunction(node.name)
            else:
                setLine(node.line, lines[node.line-1].strip())
            if isinstance(err, programState.StopProgram):
                return state, err
            while not visualizer.clockTicked:
                if visualizer.memoryCommand is not None:
                    state = visualizer.memoryCommand(state)
                    visualizer.memoryCommand = None
            visualizer.clockTicked = False
            return state, err
        else:
            return node.function(state)
    return inner


# Resets the color of the resisters in the visualizer
def resetRegs():
    # reset:: RegisterEntry -> RegisterEntry
    def reset(reg: visualizer.RegisterEntry) -> visualizer.RegisterEntry:
        reg.reset()
        return reg
    visualizer.reg_items = list(map(reset, visualizer.reg_items))


# Initialize the registers in the visualizer with there actual values
def initRegs(registers: List[int]):
    # init:: (int, RegisterEntry) -> RegisterEntry
    def init(e: Tuple[int, visualizer.RegisterEntry]) -> visualizer.RegisterEntry:
        idx, reg = e
        reg.setValue(registers[idx])
        reg.reset()
        return reg
    visualizer.reg_items = list(map(init, enumerate(visualizer.reg_items)))
    # Replace the print function
    builtins.print = visualizer.printLine


# Update the current instruction and its location in the visualizer
# setLine:: String -> int -> void
def setLine(line: int, text: str):
    visualizer.currentLine.configure(text=f"Line {line}:")
    visualizer.instr.configure(state="normal")
    visualizer.instr.delete(0.0, END)
    visualizer.instr.insert(END, text)
    visualizer.instr.configure(state="disabled")


# Update the current instruction and its location in the visualizer to a internal function
# setLineInternalFunction:: String -> void
def setLineInternalFunction(text: str):
    visualizer.currentLine.configure(text=f"Internal function:")
    visualizer.instr.configure(state="normal")
    visualizer.instr.delete(0.0, END)
    visualizer.instr.insert(END, text)
    visualizer.instr.configure(state="disabled")


# Set the colors of the statusRegister section of the visualizer to the actual contents of the statusRegister
# setStatusRegs:: bool -> bool -> bool -> bool -> void
def setStatusRegs(n: bool, z: bool, c: bool, v: bool):
    if n:
        visualizer.N.configure(fg="#00FF00")
    else:
        visualizer.N.configure(fg="#FF0000")

    if z:
        visualizer.Z.configure(fg="#00FF00")
    else:
        visualizer.Z.configure(fg="#FF0000")

    if c:
        visualizer.C.configure(fg="#00FF00")
    else:
        visualizer.C.configure(fg="#FF0000")

    if v:
        visualizer.V.configure(fg="#00FF00")
    else:
        visualizer.V.configure(fg="#FF0000")
