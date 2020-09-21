from typing import List, Optional, Tuple
from functools import reduce

import nodes
import programContext
import programState
import asmParser
import lexer
import tokens


# generateStacktraceElement:: ProgramState -> int -> String -> [String] -> String
# Generates a stacktrace element from an instruction address
def generateStacktraceElement(state: programState.ProgramState, address: int, fileName: str, lines: List[str]) -> str:
    instr: nodes.InstructionNode = state.getInstructionFromMem(address)
    if isinstance(instr, nodes.SystemCall):
        return f"\tInternal function: {instr.name}"
    return f"\tFile \"{fileName}\", line {instr.line}:\n\t\t{lines[instr.line-1].strip()}"


# generateStacktrace:: ProgramState -> RunError -> String -> [String] -> String
# Generates the stacktrace of an error
def generateStacktrace(state: programState.ProgramState, error: programState.RunError, fileName: str, lines: List[str]) -> str:
    # Get return addresses from the stack
    sp: int = state.getReg("SP")[0]
    stackSize = state.getLabelAddress("__STACKSIZE")
    stack: List[nodes.Node] = state.memory[sp >> 2:stackSize >> 2]
    callbacks = list(map(lambda n: generateStacktraceElement(state, n.value, fileName, lines), filter(lambda x: isinstance(x, nodes.DataNode) and x.source == "LR", stack)))

    # Generate the error
    res = f"\033[31m"  # Red color
    res += "Traceback (most recent call first):\n"
    res += generateStacktraceElement(state, state.getReg("PC")[0], fileName, lines) + '\n'
    if not state.hasReturned:
        res += generateStacktraceElement(state, state.getReg("LR")[0], fileName, lines) + '\n'
    if len(callbacks) > 0:
        res += reduce(lambda a, b: a + "\n" + b, callbacks) + '\n'
    res += error.message + '\n'
    return res + f"\033[0m"  # Normal color


# executeInstruction:: InstructionNode -> ProgramState -> String -> [String] -> ProgramState, bool
def executeInstruction(node: nodes.InstructionNode, state: programState.ProgramState, fileName: str, lines: List[str]) -> Tuple[programState.ProgramState, bool]:
    if isinstance(node, nodes.InstructionNode):
        # Execute the instruction
        state, err = node.function(state)

        # Exception handling
        if err is not None:
            if isinstance(err, programState.RunError):
                if err.errorType == programState.RunError.ErrorType.Error:
                    print(generateStacktrace(state, err, fileName, lines))
                    return state, False
                elif err.errorType == programState.RunError.ErrorType.Warning:
                    print(generateStacktrace(state, err, fileName, lines))
                elif isinstance(err, programState.StopProgram):
                    return state, False
        # Set a flag in the ProgramState when a subroutine returned. This way the stacktrace generator knows to not print a stacktrace element for the link register
        pc, _ = state.getReg("PC")
        if pc == state.getReg("LR")[0]:
            state.hasReturned = True
        # increment the program counter
        state.setReg("PC", pc + 4)
        return state, True
    else:
        if isinstance(node, programState.RunError):
            print(generateStacktrace(state, node, fileName, lines))
        return state, False


# runProgram:: ProgramState -> String -> [String] -> ProgramState
def runProgram(state: programState.ProgramState, fileName: str, lines: List[str]) -> programState.ProgramState:
    while True:
        state, res = executeInstruction(state.getInstructionFromMem(state.getReg("PC")[0]), state, fileName, lines)
        if not res:
            break

    return state


# parse:: String -> String -> int -> String -> ProgramState
# calls the parser and the lexer
def parse(fileName: str, file_contents: str, stackSize: int, startLabel: str) -> Optional[programState.ProgramState]:
    loadedTokens = lexer.lexFile(file_contents)
    loadedTokens: List[tokens.Token] = lexer.fixMismatches(loadedTokens, file_contents)

    if lexer.printErrors(loadedTokens, fileName):
        return None

    context = asmParser.parse(loadedTokens)
    errCount = asmParser.printErrors(context, fileName)
    if errCount > 0:
        return None

    return programContext.generateProgramState(context, stackSize, startLabel, fileName)
