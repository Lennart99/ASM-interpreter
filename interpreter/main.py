from typing import List

import asmParser
import lexer
import nodes
import programState
import tokens
from high_order import foldR1

import sys
import threading
sys.setrecursionlimit(0x100000)  # note: hex
threading.stack_size(256000000)  # set stack to 256mb

fileName = "decompress.asm"

file = open(fileName, "r")

file_contents: str = foldR1(lambda X, Y: X+Y, file.readlines())

loadedTokens = lexer.lexFile(file_contents)
loadedTokens: List[tokens.Token] = lexer.fixMismatches(loadedTokens, file_contents)

if lexer.printErrors(loadedTokens, fileName):
    exit(-1)

context = asmParser.parse(loadedTokens)
errCount = asmParser.printErrors(context, fileName)
if errCount > 0:
    exit(-1)


def run(state: programState.ProgramState) -> programState.ProgramState:
    node: nodes.InstructionNode = programState.getInstructionFromMem(state, programState.getReg(state, "PC"))
    if isinstance(node, nodes.InstructionNode):
        state, err = node.function(state)
        # del node
        if err is not None:
            if isinstance(err, programState.RunError):
                if err.errorType == programState.RunError.ErrorType.Error:
                    print(err)
                    return state
                elif err.errorType == programState.RunError.ErrorType.Warning:
                    print(err)
                    pass
            if isinstance(err, programState.StopProgram):
                return state
        state = programState.setReg(state, "PC", programState.getReg(state, "PC") + 4)
    return run(state)


pstate = programState.generateProgramState(context, 0x400, "_start", fileName)

t = threading.Thread(target=lambda: run(pstate))
t.start()
t.join()

# 30.000 iterations need 7 GB
# setup: push, bl, push, mov
# loop:  mov, bl, func, add, b
