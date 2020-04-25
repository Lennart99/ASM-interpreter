from typing import Callable, Dict, List, Tuple

import tokens
import programState
import nodes


# generateUnexpectedTokenError:: int -> str -> str -> ErrorNode
# generate an error because of an unexpected token
def generateUnexpectedTokenError(line: int, contents: str, expected: str) -> nodes.ErrorNode:
    return nodes.ErrorNode(f"\033[31m"  # red color
                           f"File \"$fileName$\", line {line}\n"
                           f"\tSyntax error: Unexpected token: '{contents}', expected {expected}"
                           f"\033[0m")


# generateToFewTokensError:: int -> str -> ErrorNode
# generate an error because there are not enough nodes for the instruction
def generateToFewTokensError(line: int, instruction: str) -> nodes.ErrorNode:
    if line == -1:
        return nodes.ErrorNode(f"\033[31m"  # red color
                               f"File \"$fileName$\", at the last line\n"
                               f"\tSyntax error: To few tokens to finish the {instruction} instruction"
                               f"\033[0m")
    else:
        return nodes.ErrorNode(f"\033[31m"  # red color
                               f"File \"$fileName$\", line {line}\n"
                               f"\tSyntax error: To few tokens to finish the {instruction} instruction"
                               f"\033[0m")


def advanceToNewline(tokenList: List[tokens.Token]) -> List[tokens.Token]:
    if len(tokenList) < 0:
        return []
    head, *tail = tokenList

    if isinstance(head, tokens.NewLine):
        return tail
    else:
        return advanceToNewline(tail)


# decodeMOV:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the MOV instruction
def decodeMOV(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "MOV"), []
    dest, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(dest.line, "MOV"), []
    if not isinstance(dest, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(dest.line, dest.contents, "A register"), tokenList[1:]
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        src, *tokenList = tokenList
        if isinstance(src, tokens.Register):
            def mov(state: programState.ProgramState) -> programState.ProgramState:
                value = programState.getReg(state, src.contents)
                return programState.setReg(state, dest.contents, value)
            return nodes.InstructionNode(section, dest.line, mov), tokenList
        elif isinstance(src, tokens.ImmediateValue):
            # todo check bit length
            def mov(state: programState.ProgramState) -> programState.ProgramState:
                return programState.setReg(state, dest.contents, src.value)
            return nodes.InstructionNode(section, dest.line, mov), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(src.line, src.contents, "A register or immediate value"), tokenList
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(separator.line, separator.contents, "','"), tokenList


# decodeLDR:: Iterator[tokens.Token] -> Node.Section -> int -> Node
# bitSize: the number ob bits to load, either 32, 16 or 8 bit
# decode the LDR, LDRH and LDRB instructions
def decodeLDR(tokenList: List[tokens.Token], section: nodes.Node.Section, bitSize: int) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "MOV"), []
    dest, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(dest.line, "MOV"), []
    if not isinstance(dest, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(dest.line, dest.contents, "A register or immediate value"), tokenList
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        separator, *tokenList = tokenList
        if isinstance(separator, tokens.LoadImmediateValue):
            value: tokens.LoadImmediateValue = separator

            def ldrImmed(state: programState.ProgramState) -> programState.ProgramState:
                return programState.setReg(state, dest.contents, value.value)
            return nodes.InstructionNode(section, dest.line, ldrImmed), tokenList
        elif isinstance(separator, tokens.LoadLabel):
            label: tokens.LoadLabel = separator

            def ldrLabel(state: programState.ProgramState) -> programState.ProgramState:
                value: int = programState.getLabelAddress(state, label.label)
                return programState.setReg(state, dest.contents, value)
            return nodes.InstructionNode(section, dest.line, ldrLabel), tokenList
        elif isinstance(separator, tokens.Separator) and separator.contents == "[":
            if len(tokenList) < 2:
                return generateToFewTokensError(dest.line, "MOV"), []
            src1, *tokenList = tokenList
            if not isinstance(src1, tokens.Register):
                # Wrong token, generate an error
                return generateUnexpectedTokenError(src1.line, src1.contents, "A register"), tokenList
            separator, *tokenList = tokenList
            if separator.contents == "]":
                def ldrOneReg(state: programState.ProgramState) -> programState.ProgramState:
                    adr = programState.getReg(state, src1.contents)
                    contents = programState.getFromMem(state, adr, bitSize)
                    return programState.setReg(state, dest.contents, contents)
                return nodes.InstructionNode(section, dest.line, ldrOneReg), tokenList
            elif separator.contents == ",":
                if len(tokenList) < 2:
                    return generateToFewTokensError(dest.line, "MOV"), []
                src2, separator, *tokenList = tokenList
                if separator.contents != "]":
                    return generateUnexpectedTokenError(separator.line, separator.contents, "']'"), tokenList
                if isinstance(src2, tokens.Register):
                    def ldrDualReg(state: programState.ProgramState) -> programState.ProgramState:
                        adr1 = programState.getReg(state, src1.contents)
                        adr2 = programState.getReg(state, src2.contents)
                        contents = programState.getFromMem(state, adr1 + adr2, bitSize)
                        return programState.setReg(state, dest.contents, contents)
                    return nodes.InstructionNode(section, dest.line, ldrDualReg), tokenList
                elif isinstance(src2, tokens.ImmediateValue):
                    src2: tokens.ImmediateValue = src2

                    def ldrRegImmed(state: programState.ProgramState) -> programState.ProgramState:
                        adr = programState.getReg(state, src1.contents)
                        contents = programState.getFromMem(state, adr + src2.value, bitSize)
                        return programState.setReg(state, dest.contents, contents)
                    return nodes.InstructionNode(section, dest.line, ldrRegImmed), tokenList
                else:
                    # Wrong token, generate an error
                    return generateUnexpectedTokenError(src2.line, src2.contents, "A register or immediate value")\
                        , tokenList
            else:
                # Wrong token, generate an error
                return generateUnexpectedTokenError(separator.line, separator.contents, "']' or ','"), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(separator.line, separator.contents, "'['"), tokenList
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(separator.line, separator.contents, "','"), tokenList


# decodePUSH:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the PUSH instruction
def decodePUSH(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodePOP:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the POP instruction
def decodePOP(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodeSUB:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the SUB instruction
def decodeSUB(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodeADD:: Iterator[tokens.Token] -> Node.Section -> Node

# decode the ADD instruction
def decodeADD(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodeCMP:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the CMP instruction
def decodeCMP(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodeBLS:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the BLS instruction
def decodeBLS(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodeBEQ:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the BEQ instruction
def decodeBEQ(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodeB:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the branch instruction
def decodeB(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# decodeBL:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the BL instruction
def decodeBL(itt: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    pass


# TODO MOV, LDRB, LDR, PUSH, POP, SUB, ADD, CMP, BLS, BL, B, BEQ
# saves one function per instruction to be used to decode that instruction into a Node
tokenFunctions: Dict[str, Callable[[List[tokens.Token], nodes.Node.Section], Tuple[nodes.Node, List[tokens.Token]]]] = {
    "MOV": decodeMOV,
    "LDR": lambda a, b: decodeLDR(a, b, 32),
    "LDRH": lambda a, b: decodeLDR(a, b, 16),
    "LDRB": lambda a, b: decodeLDR(a, b, 8),
    "STR": None,
    "STRH": None,
    "STRB": None,
    "LDRSH": None,
    "LDRSB": None,

    "PUSH": decodePUSH,
    "POP": decodePOP,
    "LDM": None,
    "LDMIA": None,
    "STMIA": None,

    "ADD": decodeADD,
    "ADC": None,
    "SUB": decodeSUB,
    "SBC": None,
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
    "CMP": decodeCMP,
    "CMN": None,

    "REV": None,
    "REV16": None,
    "REVSH": None,

    "B": decodeB,
    "BL": decodeBL,
    "BX": None,
    "BLX": None,

    "BCC": None,
    "BCS": None,
    "BEQ": decodeBEQ,
    "BGE": None,
    "BGT": None,
    "BHI": None,
    "BLE": None,
    "BLS": decodeBLS,
    "BLT": None,
    "BMI": None,
    "BNE": None,
    "BPL": None,
    "BVC": None,
    "BVS": None
}
