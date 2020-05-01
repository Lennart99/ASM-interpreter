from typing import List

import asmParser
import lexer
import nodes
import programState
import tokens
from high_order import foldR1

import sys
import threading
from time import time
sys.setrecursionlimit(0x100000)
threading.stack_size(256000000)  # set stack to 256mb

file = open("decompress.asm", "r")

file_contents: str = foldR1(lambda X, Y: X+Y, file.readlines())

loadedTokens = lexer.lexFile(file_contents)
loadedTokens: List[tokens.Token] = lexer.fixMismatches(loadedTokens, file_contents)

if lexer.printErrors(loadedTokens, "decompress.asm"):
    exit(-1)

context = asmParser.parse(loadedTokens)
errCount = asmParser.printErrors(context, "decompress.asm")
if errCount > 0:
    exit(-1)


def run(state: programState.ProgramState) -> programState.ProgramState:
    # print(state.memory)
    node: nodes.InstructionNode = programState.getInstructionFromMem(state, programState.getReg(state, "PC"))
    if isinstance(node, nodes.InstructionNode):
        state = node.function(state)
        # del node
        state = programState.setReg(state, "PC", programState.getReg(state, "PC") + 4)
    if programState.getReg(state, "PC") < 0x400:
        return state
    else:
        return run(state)

def run_prog():
    pstate = programState.generateProgramState(context, 0x400, "_start")
    run(pstate)


start_time = time()
sys.setrecursionlimit(0x100000)  # note: hex
threading.stack_size(256000000)  # set stack to 256mb
t = threading.Thread(target=run_prog)
t.start()
t.join()

# 30.000 iterations need 7 GB
# setup: push, bl, push, mov
# loop:  mov, bl, func, add, b
