from functools import wraps
from typing import List, Tuple
from tkinter import END
import builtins

import visualizer
import programState
import nodes


# Decorators
def writeLogger(f):
    @wraps(f)
    def inner(state: programState.ProgramState, name: str, value: int):
        if state.visualizer:
            visualizer.reg_items[programState.regToID(name)].setValue(value)
        return f(state, name, value)
    return inner


def readLogger(f):
    @wraps(f)
    def inner(state: programState.ProgramState, name: str):
        if state.visualizer:
            visualizer.reg_items[programState.regToID(name)].processRead()
        return f(state, name)
    return inner


def statusLogger(f):
    @wraps(f)
    def inner(state: programState.ProgramState, value: programState.StatusRegister):
        if state.visualizer:
            setStatusRegs(value.N, value.Z, value.C, value.V)
        return f(state, value)
    return inner


# Decorator to update the visualizer and wait until the next instruction can be executed
def runLogger(node: nodes.InstructionNode, lines: List[str]):
    @wraps(node.function)
    def inner(state: programState.ProgramState):
        if state.visualizer:
            resetRegs()
            state, err = node.function(state)
            if isinstance(node, nodes.SystemCall):
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


def resetRegs():
    def reset(reg: visualizer.RegisterEntry):
        reg.reset()
        return reg
    visualizer.reg_items = list(map(reset, visualizer.reg_items))


def initRegs(registers: List[int]):
    def init(e: Tuple[int, visualizer.RegisterEntry]):
        idx, reg = e
        reg.setValue(registers[idx])
        reg.reset()
        return reg
    visualizer.reg_items = list(map(init, enumerate(visualizer.reg_items)))
    # Replace the print function
    builtins.print = visualizer.printLine


def setLine(line: int, text: str):
    visualizer.currentLine.configure(text=f"Line {line}:")
    visualizer.instr.configure(state="normal")
    visualizer.instr.delete(0.0, END)
    visualizer.instr.insert(END, text)
    visualizer.instr.configure(state="disabled")


def setLineInternalFunction(text: str):
    visualizer.currentLine.configure(text=f"Internal function:")
    visualizer.instr.configure(state="normal")
    visualizer.instr.delete(0.0, END)
    visualizer.instr.insert(END, text)
    visualizer.instr.configure(state="disabled")


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
