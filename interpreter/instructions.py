from typing import Callable, Dict, List, Tuple, Union

import tokens
import programState
import nodes
import instructionsALU
import instructionsMemory

from instructionsUtils import generateToFewTokensError, generateUnexpectedTokenError, generateImmediateOutOfRangeError, advanceToNewline


# decodeMOV:: [Token] -> Node.Section -> (Node, [Token])
# decode the MOV instruction
def decodeMOV(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "MOV instruction"), []
    dest, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(dest.line, "MOV instruction"), []
    if not isinstance(dest, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(dest.line, dest.contents, "a register"), advanceToNewline(tokenList)
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        src, *tokenList = tokenList
        if isinstance(src, tokens.Register):
            def movReg(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                value = state.getReg(src.contents)
                state.setReg(dest.contents, value)
                return state, None
            return nodes.InstructionNode(section, dest.line, movReg), tokenList
        elif isinstance(src, tokens.ImmediateValue):
            # check 8 bits
            if src.value > 0xFF:
                return generateImmediateOutOfRangeError(src.line, src.value, 0xFF), tokenList

            def movImmed(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                state.setReg(dest.contents, src.value)
                return state, None
            return nodes.InstructionNode(section, dest.line, movImmed), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(src.line, src.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(separator.line, separator.contents, "','"), advanceToNewline(tokenList)


# decodeB:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the branch instruction
def decodeBranch(tokenList: List[tokens.Token], section: nodes.Node.Section,
                 condition: Callable[[programState.StatusRegister], bool]) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "Branch instruction"), []
    label, *tokenList = tokenList
    if isinstance(label, tokens.Label):
        def branchTo(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
            if condition(state.status):
                address: Union[int, programState.RunError] = state.getLabelAddress(label.contents)
                if isinstance(address, programState.RunError):
                    return state, address
                else:
                    # Subtract 4 because we will add 4 to the address later in the run loop and we need to start at address and not address+4
                    state.setReg("PC", address-4)
            return state, None

        return nodes.InstructionNode(section, label.line, branchTo), tokenList
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(label.line, label.contents, "a label"), advanceToNewline(tokenList)


# decodeBL:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the BL instruction
def decodeBL(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "BL instruction"), []
    label, *tokenList = tokenList
    if isinstance(label, tokens.Label):
        def branchTo(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
            # Save return address in LR
            pc = state.getReg("PC")
            state.setReg("LR", pc)

            address: Union[int, programState.RunError] = state.getLabelAddress(label.contents)
            if isinstance(address, programState.RunError):
                return state, address
            else:
                # Subtract 4 because we will add 4 to the address later in the run loop and we need to start at address and not address+4
                state.setReg("PC", address - 4)
                state.hasReturned = False
                return state, None

        return nodes.InstructionNode(section, label.line, branchTo), tokenList
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(label.line, label.contents, "a label"), advanceToNewline(tokenList)


# saves one function per instruction to be used to decode that instruction into a Node
tokenFunctions: Dict[str, Callable[[List[tokens.Token], nodes.Node.Section], Tuple[nodes.Node, List[tokens.Token]]]] = {
    "MOV": decodeMOV,
    # decodeLDR expects a int as it's third argument to tell the difference between LDR, LDRH and LDRB
    "LDR": lambda a, b: instructionsMemory.decodeLDR(a, b, 32),
    "LDRH": lambda a, b: instructionsMemory.decodeLDR(a, b, 16),
    "LDRB": lambda a, b: instructionsMemory.decodeLDR(a, b, 8),
    "STR": lambda a, b: instructionsMemory.decodeSTR(a, b, 32),
    "STRH": lambda a, b: instructionsMemory.decodeSTR(a, b, 16),
    "STRB": lambda a, b: instructionsMemory.decodeSTR(a, b, 8),
    "LDRSH": None,
    "LDRSB": None,

    "PUSH": instructionsMemory.decodePUSH,
    "POP": instructionsMemory.decodePOP,
    "LDM": None,
    "LDMIA": None,
    "STMIA": None,

    "ADD": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeADD, "ADD"),
    "ADC": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeADC, "ADC"),
    "SUB": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeSUB, "SUB"),
    "SBC": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeSBC, "SBC"),
    "MUL": None,

    "AND": None,
    "EOR": None,
    "ORR": None,
    "BIC": None,
    "MOVN": None,

    "LSL": None,
    "LSR": None,
    "ASR": None,
    "ROR": None,

    "SXTH": None,
    "SXTB": None,
    "UXTH": None,
    "UXTB": None,

    "TST": None,
    "CMP": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeCMP, "CMP"),
    "CMN": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeCMN, "CMN"),

    "REV": None,
    "REV16": None,
    "REVSH": None,

    # decodeBranch expects a function as it's third argument
    # to decide if a branch needs to be executed based on the StatusRegister
    "B": lambda a, b: decodeBranch(a, b, lambda status: True),
    "BL": decodeBL,
    "BX": None,
    "BLX": None,

    # decodeBranch expects a function as it's third argument
    # to decide if a branch needs to be executed based on the StatusRegister
    "BCC": lambda a, b: decodeBranch(a, b, lambda status: not status.C),
    "BCLO": lambda a, b: decodeBranch(a, b, lambda status: not status.C),
    "BCS": lambda a, b: decodeBranch(a, b, lambda status: status.C),
    "BHS": lambda a, b: decodeBranch(a, b, lambda status: status.C),
    "BEQ": lambda a, b: decodeBranch(a, b, lambda status: status.Z),
    "BGE": lambda a, b: decodeBranch(a, b, lambda status: status.N == status.V),
    "BGT": lambda a, b: decodeBranch(a, b, lambda status: (not status.Z) and (status.N == status.V)),
    "BHI": lambda a, b: decodeBranch(a, b, lambda status: (not status.Z) and status.C),
    "BLE": lambda a, b: decodeBranch(a, b, lambda status: status.Z or (status.N != status.V)),
    "BLS": lambda a, b: decodeBranch(a, b, lambda status: (not status.C) or status.Z),
    "BLT": lambda a, b: decodeBranch(a, b, lambda status: (status.N != status.V)),
    "BMI": lambda a, b: decodeBranch(a, b, lambda status: status.N),
    "BNE": lambda a, b: decodeBranch(a, b, lambda status: (not status.Z)),
    "BPL": lambda a, b: decodeBranch(a, b, lambda status: not status.N),
    "BVC": lambda a, b: decodeBranch(a, b, lambda status: not status.V),
    "BVS": lambda a, b: decodeBranch(a, b, lambda status: status.V)
}
