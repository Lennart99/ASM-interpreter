from typing import Union, Any, Match, Callable, List, Dict, Iterator

import lexer
from high_order import foldR1
import tokens
import asmParser
import programState
import nodes

# file = open("program.asm", "r")
#
# file_contents: str = foldR1(lambda X, Y: X+Y, file.readlines())
# print(file_contents)

loadedTokens = lexer.lexFile("MOV R0, #0xFFFF\n"
                             "MOV R1, #0xFF")
loadedTokens: List[tokens.Token] = lexer.fixMismatches(loadedTokens, "MOV R0, #1\n"
                                                                     "MOV R1, #3")

if lexer.printErrors(loadedTokens, "program.asm"):
    exit(-1)

nodeList = asmParser.parse(loadedTokens)

state = programState.ProgramState([0 for _ in range(16)])
print(state)
for node in nodeList:
    if isinstance(node, nodes.InstructionNode):
        state = node.function(state)
        print(state)
    if isinstance(node, nodes.ErrorNode):
        print(node)

