from functools import wraps
from typing import List

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
            visualizer.setStatusRegs(value.N, value.Z, value.C, value.V)
        return f(state, value)
    return inner


# Decorator to update the visualizer and wait until the next instruction can be executed
def runLogger(node: nodes.InstructionNode, lines: List[str]):
    @wraps(node.function)
    def inner(state: programState.ProgramState):
        if state.visualizer:
            visualizer.resetRegs()
            state, err = node.function(state)
            if isinstance(node, nodes.SystemCall):
                visualizer.setLineInternalFunction(node.name)
            else:
                visualizer.setLine(node.line, lines[node.line-1].strip())
            visualizer.clockTicked = False
            if isinstance(err, programState.StopProgram):
                return state, err
            while not visualizer.clockTicked:
                pass
            return state, err
        else:
            return node.function(state)
    return inner
