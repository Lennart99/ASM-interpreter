from typing import List

import asmParser
import lexer
import nodes
import programState
import tokens
from high_order import foldR1

file = open("program.asm", "r")

file_contents: str = foldR1(lambda X, Y: X+Y, file.readlines())

loadedTokens = lexer.lexFile(file_contents)
loadedTokens: List[tokens.Token] = lexer.fixMismatches(loadedTokens, file_contents)

if lexer.printErrors(loadedTokens, "program.asm"):
    exit(-1)

context = asmParser.parse(loadedTokens)
errCount = asmParser.printErrors(context, "program.asm")
if errCount > 0:
    exit(-1)

state = programState.generateProgramState(context, 0x400, "_start")
print(state)
print(state.memory)
while True:
    node: nodes.InstructionNode = programState.getInstructionFromMem(state, programState.getReg(state, "PC"))
    if isinstance(node, nodes.InstructionNode):
        state = node.function(state)
        state = programState.setReg(state, "PC", programState.getReg(state, "PC") + 4)
    if programState.getReg(state, "PC") < 0x400:
        break


