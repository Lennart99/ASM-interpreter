from typing import Callable, Dict, List, Tuple, Union

import tokens
import programState
import nodes
import instructionsALU
import instructionsMemory

from instructionsUtils import generateToFewTokensError, generateUnexpectedTokenError, generateImmediateOutOfRangeError, advanceToNewline


# decodeMOV:: [Token] -> Node.Section -> (Node, [Token])
# decode the MOV instruction
def decodeMOV(tokenList: List[tokens.Token], section: nodes.Node.Section, invert: bool) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, f"{'MOVN' if invert else 'MOV'} instruction"), []
    dest, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(dest.line, f"{'MOVN' if invert else 'MOV'} instruction"), []
    if not isinstance(dest, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(dest.line, dest.contents, "a register"), advanceToNewline(tokenList)
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        src, *tokenList = tokenList
        if isinstance(src, tokens.Register):
            def movReg(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                value, err = state.getReg(src.contents)
                if invert:
                    value = value ^ 0xFFFF_FFFF
                state.setReg(dest.contents, value)
                return state, err
            return nodes.InstructionNode(section, dest.line, movReg), tokenList
        elif isinstance(src, tokens.ImmediateValue):
            # check 8 bits
            if src.value > 0xFF:
                return generateImmediateOutOfRangeError(src.line, src.value, 0xFF), tokenList

            def movImmed(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                if invert:
                    value = src.value ^ 0xFFFF_FFFF
                else:
                    value = src.value
                state.setReg(dest.contents, value)
                return state, None
            return nodes.InstructionNode(section, dest.line, movImmed), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(src.line, src.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(separator.line, separator.contents, "','"), advanceToNewline(tokenList)


# decodeExtend:: [Token] -> Node.Section -> bool -> bool -> (Node, [Token])
# decode the SXTH, SXTB, UXTH and UXTB instructions
def decodeExtend(tokenList: List[tokens.Token], section: nodes.Node.Section, signed: bool, halfWord: bool) -> Tuple[nodes.Node, List[tokens.Token]]:
    if halfWord:
        if signed:
            instrName = "SXTH"
        else:
            instrName = "UXTH"
    else:
        if signed:
            instrName = "SXTB"
        else:
            instrName = "UXTB"
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, f"{instrName} instruction"), []
    dest, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(dest.line, f"{instrName} instruction"), []
    if not isinstance(dest, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(dest.line, dest.contents, "a register"), advanceToNewline(tokenList)
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        src, *tokenList = tokenList
        if isinstance(src, tokens.Register):
            def movReg(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                value, err = state.getReg(src.contents)
                if halfWord:
                    if signed:
                        if (value & 0b1000_0000_0000_0000) == 0b1000_0000_0000_0000:
                            value |= 0xFFFF_0000  # Set upper half-word when sign bit is set
                        else:
                            value &= 0xFFFF
                    else:
                        value &= 0xFFFF
                else:
                    if signed:
                        if (value & 0b1000_0000) == 0b1000_0000:
                            value |= 0xFFFF_FF00  # Set upper three bytes when sign bit is set
                        else:
                            value &= 0xFF
                    else:
                        value &= 0xFF

                state.setReg(dest.contents, value)
                return state, err
            return nodes.InstructionNode(section, dest.line, movReg), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(src.line, src.contents, "a register"), advanceToNewline(tokenList)
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
            pc, _ = state.getReg("PC")
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


# decodeBL:: Iterator[tokens.Token] -> Node.Section -> bool -> Node
# decode the BL instruction
def decodeBLX(tokenList: List[tokens.Token], section: nodes.Node.Section, link: bool) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "BL instruction"), []
    label, *tokenList = tokenList
    if isinstance(label, tokens.Register):
        def branchTo(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
            if link:
                # Save return address in LR
                state.setReg("LR", state.getReg("PC")[0])

            address, err = state.getReg(label.contents)
            # Subtract 4 because we will add 4 to the address later in the run loop and we need to start at address and not address+4
            state.setReg("PC", address - 4)
            state.hasReturned = False
            return state, err

        return nodes.InstructionNode(section, label.line, branchTo), tokenList
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(label.line, label.contents, "a label"), advanceToNewline(tokenList)


# saves one function per instruction to be used to decode that instruction into a Node
tokenFunctions: Dict[str, Callable[[List[tokens.Token], nodes.Node.Section], Tuple[nodes.Node, List[tokens.Token]]]] = {
    # decodeMOV has a third argument to tell if the value must be inverted (MOVN)
    "MOV": lambda a, b: decodeMOV(a, b, False),
    "MOVN": lambda a, b: decodeMOV(a, b, True),
    # decodeLDR and decodeSTR expect a int as it's third argument to tell the difference between LDR, LDRH and LDRB
    # decodeLDR expects a bool as it's forth argument to tell if the value must be sign extended
    "LDR": lambda a, b: instructionsMemory.decodeLDR(a, b, 32, False),
    "LDRH": lambda a, b: instructionsMemory.decodeLDR(a, b, 16, False),
    "LDRB": lambda a, b: instructionsMemory.decodeLDR(a, b, 8, False),
    "STR": lambda a, b: instructionsMemory.decodeSTR(a, b, 32),
    "STRH": lambda a, b: instructionsMemory.decodeSTR(a, b, 16),
    "STRB": lambda a, b: instructionsMemory.decodeSTR(a, b, 8),
    "LDRSH": lambda a, b: instructionsMemory.decodeLDR(a, b, 16, True),
    "LDRSB": lambda a, b: instructionsMemory.decodeLDR(a, b, 8, True),

    "PUSH": instructionsMemory.decodePUSH,
    "POP": instructionsMemory.decodePOP,
    "LDM": None,
    "LDMIA": None,
    "STMIA": None,

    "ADD": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeADD, "ADD"),
    "ADC": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeADC, "ADC"),
    "SUB": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeSUB, "SUB"),
    "SBC": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeSBC, "SBC"),
    "MUL": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeMUL, "MUL"),

    "AND": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeAND, "AND"),
    "EOR": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeEOR, "ERR"),
    "ORR": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeORR, "ORR"),
    "BIC": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeBIC, "BIC"),

    "LSL": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeLSL, "LSL"),
    "LSR": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeLSR, "LSR"),
    "ASR": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeASR, "ASR"),
    "ROR": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeROR, "ROR"),

    # The third args tells decodeExtend if it is a signed extend
    "SXTH": lambda a, b: decodeExtend(a, b, True, True),
    "SXTB": lambda a, b: decodeExtend(a, b, True, False),
    "UXTH": lambda a, b: decodeExtend(a, b, False, True),
    "UXTB": lambda a, b: decodeExtend(a, b, False, False),

    "TST": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeTST, "TST"),
    "CMP": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeCMP, "CMP"),
    "CMN": lambda a, b: instructionsALU.decodeALUInstruction(a, b, instructionsALU.decodeCMN, "CMN"),

    "REV": None,
    "REV16": None,
    "REVSH": None,

    # decodeBranch expects a function as it's third argument
    # to decide if a branch needs to be executed based on the StatusRegister
    "B": lambda a, b: decodeBranch(a, b, lambda status: True),
    "BL": decodeBL,
    "BX": lambda a, b: decodeBLX(a, b, False),
    "BLX": lambda a, b: decodeBLX(a, b, False),

    # decodeBranch expects a function as it's third argument
    # to decide if a branch needs to be executed based on the StatusRegister
    "BCC": lambda a, b: decodeBranch(a, b, lambda status: not status.C),
    "BLO": lambda a, b: decodeBranch(a, b, lambda status: not status.C),
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
