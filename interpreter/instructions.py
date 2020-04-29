from typing import Callable, Dict, List, Tuple, Union

import tokens
import programState
import nodes


# generateUnexpectedTokenError:: int -> str -> str -> ErrorNode
# generate an error because of an unexpected token
def generateUnexpectedTokenError(line: int, contents: str, expected: str) -> nodes.ErrorNode:
    return nodes.ErrorNode(f"\033[31m"  # red color
                           f"File \"$fileName$\", line {line}\n"
                           f"\tSyntax error: Unexpected token: '{contents}', expected {expected}"
                           f"\033[0m\n")


# generateToFewTokensError:: int -> str -> ErrorNode
# generate an error because there are not enough nodes for the instruction
def generateToFewTokensError(line: int, instruction: str) -> nodes.ErrorNode:
    if line == -1:
        return nodes.ErrorNode(f"\033[31m"  # red color
                               f"File \"$fileName$\", at the last line\n"
                               f"\tSyntax error: To few tokens to finish the {instruction}"
                               f"\033[0m\n")
    else:
        return nodes.ErrorNode(f"\033[31m"  # red color
                               f"File \"$fileName$\", line {line}\n"
                               f"\tSyntax error: To few tokens to finish the {instruction}"
                               f"\033[0m\n")


# advanceToNewline:: [Token] -> [Token]
# Advance to the first token after a newline
def advanceToNewline(tokenList: List[tokens.Token]) -> List[tokens.Token]:
    if len(tokenList) == 0:
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
            def movReg(state: programState.ProgramState) -> programState.ProgramState:
                value = programState.getReg(state, src.contents)
                return programState.setReg(state, dest.contents, value)
            return nodes.InstructionNode(section, dest.line, movReg), tokenList
        elif isinstance(src, tokens.ImmediateValue):
            # todo check bit length - 8 bits
            def movImmed(state: programState.ProgramState) -> programState.ProgramState:
                return programState.setReg(state, dest.contents, src.value)
            return nodes.InstructionNode(section, dest.line, movImmed), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(src.line, src.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(separator.line, separator.contents, "','"), advanceToNewline(tokenList)


# decodeLDR:: Iterator[tokens.Token] -> Node.Section -> int -> Node
# bitSize: the number ob bits to load, either 32, 16 or 8 bit
# decode the LDR, LDRH and LDRB instructions
def decodeLDR(tokenList: List[tokens.Token], section: nodes.Node.Section, bitSize: int) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "LDR instruction"), []
    dest, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(dest.line, "LDR instruction"), []
    if not isinstance(dest, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(dest.line, dest.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        separator, *tokenList = tokenList
        if isinstance(separator, tokens.LoadImmediateValue):
            value: int = separator.value & 0xFFFFFFFF

            def ldrImmed(state: programState.ProgramState) -> programState.ProgramState:
                return programState.setReg(state, dest.contents, value)
            return nodes.InstructionNode(section, dest.line, ldrImmed), tokenList
        elif isinstance(separator, tokens.LoadLabel):
            label: tokens.LoadLabel = separator

            def ldrLabel(state: programState.ProgramState) -> programState.ProgramState:
                value: int = programState.getLabelAddress(state, label.label)
                return programState.setReg(state, dest.contents, value)
            return nodes.InstructionNode(section, dest.line, ldrLabel), tokenList
        elif isinstance(separator, tokens.Separator) and separator.contents == "[":
            if len(tokenList) < 2:
                return generateToFewTokensError(dest.line, "LDR instruction"), []
            src1, *tokenList = tokenList
            if not isinstance(src1, tokens.Register):
                # Wrong token, generate an error
                return generateUnexpectedTokenError(src1.line, src1.contents, "a register"), advanceToNewline(tokenList)
            separator, *tokenList = tokenList
            if isinstance(separator, tokens.Separator) and separator.contents == "]":
                def ldrOneReg(state: programState.ProgramState) -> programState.ProgramState:
                    adr = programState.getReg(state, src1.contents)
                    contents = programState.getDataFromMem(state, adr, bitSize)
                    return programState.setReg(state, dest.contents, contents)
                return nodes.InstructionNode(section, dest.line, ldrOneReg), tokenList
            elif isinstance(separator, tokens.Separator) and separator.contents == ",":
                if len(tokenList) < 2:
                    return generateToFewTokensError(dest.line, "LDR instruction"), []
                src2, separator, *tokenList = tokenList
                if isinstance(separator, tokens.Separator) and separator.contents != "]":
                    return generateUnexpectedTokenError(separator.line, separator.contents, "']'"), advanceToNewline(tokenList)
                if isinstance(src2, tokens.Register):
                    def ldrDualReg(state: programState.ProgramState) -> programState.ProgramState:
                        adr1 = programState.getReg(state, src1.contents)
                        adr2 = programState.getReg(state, src2.contents)
                        contents = programState.getDataFromMem(state, adr1 + adr2, bitSize)
                        return programState.setReg(state, dest.contents, contents)
                    return nodes.InstructionNode(section, dest.line, ldrDualReg), tokenList
                elif isinstance(src2, tokens.ImmediateValue):
                    src2: tokens.ImmediateValue = src2
                    # TODO check bit length - 5 bits or 8 for relative to SP or PC

                    def ldrRegImmed(state: programState.ProgramState) -> programState.ProgramState:
                        adr = programState.getReg(state, src1.contents)
                        contents = programState.getDataFromMem(state, adr + src2.value, bitSize)
                        return programState.setReg(state, dest.contents, contents)
                    return nodes.InstructionNode(section, dest.line, ldrRegImmed), tokenList
                else:
                    # Wrong token, generate an error
                    return generateUnexpectedTokenError(src2.line, src2.contents, "a register or an immediate value"), advanceToNewline(tokenList)
            else:
                # Wrong token, generate an error
                return generateUnexpectedTokenError(separator.line, separator.contents, "']' or ','"), advanceToNewline(tokenList)
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(separator.line, separator.contents, "'['"), advanceToNewline(tokenList)
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(separator.line, separator.contents, "','"), advanceToNewline(tokenList)


# getRegisterList:: [Token] -> String -> boolean -> (Either [Token] ErrorNode, [Token]]
# The instruction string is used to create the error messages
def getRegisterList(tokenList: List[tokens.Token], instruction: str, isOpened: bool = False) -> \
        Tuple[Union[List[tokens.Register], nodes.ErrorNode], List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, instruction + " instruction"), []
    separator, *tokenList = tokenList

    if isOpened:
        if isinstance(separator, tokens.Separator) and separator.contents == ",":
            if len(tokenList) == 0:
                return generateToFewTokensError(separator.line, instruction + " instruction"), []
            reg, *tokenList = tokenList
            if isinstance(reg, tokens.Register):
                regs, tokenList = getRegisterList(tokenList, instruction, True)
                return [reg] + regs, tokenList
            else:
                return generateUnexpectedTokenError(reg.line, reg.contents, "a register"), advanceToNewline(tokenList)
        elif isinstance(separator, tokens.Separator) and separator.contents == "}":
            return [], tokenList
        else:
            return generateUnexpectedTokenError(separator.line, separator.contents, "',' or '}'"), advanceToNewline(tokenList)
    else:
        if isinstance(separator, tokens.Separator) and separator.contents == "{":
            if len(tokenList) == 0:
                return generateToFewTokensError(separator.line, instruction + " instruction"), advanceToNewline(tokenList)
            reg, *tokenList = tokenList
            if isinstance(reg, tokens.Register):
                regs, tokenList = getRegisterList(tokenList, instruction, True)
                return [reg] + regs, tokenList
            else:
                return generateUnexpectedTokenError(reg.line, reg.contents, "a register"), advanceToNewline(tokenList)
        else:
            return generateUnexpectedTokenError(separator.line, separator.contents, "'{'"), advanceToNewline(tokenList)


# decodePUSH:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the PUSH instruction
def decodePUSH(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    regs, tokenList = getRegisterList(tokenList, "PUSH")

    if isinstance(regs, nodes.ErrorNode):
        return regs, tokenList

    def push(state: programState.ProgramState, registers: List[tokens.Token]) -> programState.ProgramState:
        if len(registers) == 0:
            return state
        head, *tail = registers

        address = programState.getReg(state, "SP") - 4
        # TODO check address is in 0...stacksize
        val = programState.getReg(state, head.contents)
        state = programState.storeInMem(state, address, val, 32)
        state = programState.setReg(state, "SP", address)
        return push(state, tail)

    return nodes.InstructionNode(section, regs[0].line, lambda x: push(x, regs)), tokenList


# decodePOP:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the POP instruction
def decodePOP(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    regs, tokenList = getRegisterList(tokenList, "POP")

    if isinstance(regs, nodes.ErrorNode):
        return regs, tokenList

    def pop(state: programState.ProgramState, registers: List[tokens.Token]) -> programState.ProgramState:
        if len(registers) == 0:
            return state
        head, *tail = registers

        address = programState.getReg(state, "SP")
        # TODO check address is in 0...(stacksize-4) - stacksize-4 because we add 4 later on
        val = programState.getDataFromMem(state, address, 32)
        state = programState.setReg(state, head.contents, val)
        state = programState.setReg(state, "SP", address + 4)
        return pop(state, tail)

    return nodes.InstructionNode(section, regs[0].line, lambda x: pop(x, list(reversed(regs)))), tokenList


# decodeALUInstruction:: [Token] -> Section -> (ProgramState -> int -> int -> String -> ProgramState) -> String
#       -> (Node, [Token])
# decodes any ALU instruction that uses the syntax INSTR {rd,} rn, <rm|#immed8>
# when the instruction is run, the func parameter is used to perform the right action for the instruction
def decodeALUInstruction(tokenList: List[tokens.Token], section: nodes.Node.Section,
                         func: Callable[[programState.ProgramState, str, Union[int, str, None], str], programState.ProgramState],
                         instruction: str) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, instruction + " instruction"), []
    arg1, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(arg1.line, instruction + " instruction"), []
    seperator1, arg2, *tokenList = tokenList
    if len(tokenList) < 4:
        seperator2 = seperator1
        # move arg2 to arg3 and copy arg1 to arg2
        arg3 = None
    else:
        seperator2, arg3, *tokenList = tokenList
    if not (isinstance(seperator1, tokens.Separator) and seperator1.contents == ","):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(seperator1.line, seperator1.contents, "','"), advanceToNewline(tokenList)
    if not (isinstance(seperator2, tokens.Separator) and seperator2.contents == ","):
        if isinstance(seperator2, tokens.NewLine) or isinstance(seperator2, tokens.Comment):
            tokenList = [seperator2, arg3] + tokenList
            # move arg2 to arg3 and copy arg1 to arg2
            arg3 = None
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(seperator2.line, seperator2.contents, "',' or End of line"), advanceToNewline(tokenList)

    if not isinstance(arg1, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(arg1.line, arg1.contents, "a register"), advanceToNewline(tokenList)
    if arg3 is None:
        if isinstance(arg2, tokens.Register):
            def runWithReg(state: programState.ProgramState) -> programState.ProgramState:
                return func(state, arg1.contents, arg2.contents, None)

            return nodes.InstructionNode(section, arg1.line, runWithReg), tokenList
        elif isinstance(arg2, tokens.ImmediateValue):
            # TODO check bit length - 3 bits or 8 when arg 1 and 2 are the same
            # TODO special case for SP
            def runWithImm(state: programState.ProgramState) -> programState.ProgramState:
                return func(state, arg1.contents, arg2.value, None)

            return nodes.InstructionNode(section, arg1.line, runWithImm), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(arg2.line, arg2.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    else:
        if not isinstance(arg2, tokens.Register):
            # Wrong token, generate an error
            return generateUnexpectedTokenError(arg2.line, arg2.contents, "a register"), advanceToNewline(tokenList)
        if isinstance(arg3, tokens.Register):
            def runWithReg(state: programState.ProgramState) -> programState.ProgramState:
                return func(state, arg1.contents, arg2.contents, arg3.contents)

            return nodes.InstructionNode(section, arg1.line, runWithReg), tokenList
        elif isinstance(arg3, tokens.ImmediateValue):
            # TODO check bit length - 3 bits or 8 when arg 1 and 2 are the same
            # TODO special case for SP
            def runWithImm(state: programState.ProgramState) -> programState.ProgramState:
                return func(state, arg1.contents, arg2.contents, arg3.value)

            return nodes.InstructionNode(section, arg1.line, runWithImm), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(arg3.line, arg3.contents, "a register or an immediate value"), advanceToNewline(tokenList)


# decodeSUB:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the SUB instruction
def decodeSUB(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    def sub(state: programState.ProgramState, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> programState.ProgramState:
        if arg3 is None:
            a = programState.getReg(state, arg1)
            if isinstance(arg2, str):
                b = programState.getReg(state, arg2)
            else:
                b = arg2 & 0XFFFFFFFF
        else:
            a = programState.getReg(state, arg2)
            if isinstance(arg3, str):
                b = programState.getReg(state, arg3)
            else:
                b = arg3 & 0XFFFFFFFF

        minusB = ((~b)+1) & 0xFFFFFFFF
        out = a + minusB
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (minusB >> 31) & 1
        if signA == signB and signB != bit31:
            v = True
        else:
            v = False

        c = bool((out >> 32) & 1)
        n = out < 0
        z = out == 0

        state = programState.setReg(state, arg1, out32)
        state = programState.setALUState(state, programState.StatusRegister(n, z, c, v))

        return state

    return decodeALUInstruction(tokenList, section, sub, "SUB")


# decodeADD:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the ADD instruction
def decodeADD(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    def add(state: programState.ProgramState, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> programState.ProgramState:
        if arg3 is None:
            a = programState.getReg(state, arg1)
            if isinstance(arg2, str):
                b = programState.getReg(state, arg2)
            else:
                b = arg2 & 0xFFFFFFFF
        else:
            a = programState.getReg(state, arg2)
            if isinstance(arg3, str):
                b = programState.getReg(state, arg3)
            else:
                b = arg3 & 0xFFFFFFFF

        out = a + b
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (b >> 31) & 1
        if signA == signB and signB != bit31:
            v = True
        else:
            v = False

        c = bool((out >> 32) & 1)
        n = bool(bit31)
        z = out == 0

        state = programState.setReg(state, arg1, out32)
        state = programState.setALUState(state, programState.StatusRegister(n, z, c, v))

        return state

    return decodeALUInstruction(tokenList, section, add, "ADD")


# decodeCMP:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the CMP instruction
def decodeCMP(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    def cmp(state: programState.ProgramState, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> programState.ProgramState:
        if arg3 is None:
            a = programState.getReg(state, arg1)
            if isinstance(arg2, str):
                b = programState.getReg(state, arg2)
            else:
                b = arg2 & 0xFFFFFFFF
        else:
            print("NOT NONE")
            # TODO error
            return state

        minusB = ((~b) + 1) & 0xFFFFFFFF
        out = a + minusB
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (minusB >> 31) & 1
        if signA == signB and signB != bit31:
            v = True
        else:
            v = False

        c = bool((out >> 32) & 1)
        n = bool(bit31)
        z = out == 0

        # discard the result
        # state = programState.setReg(state, arg1, out32)
        state = programState.setALUState(state, programState.StatusRegister(n, z, c, v))

        return state

    return decodeALUInstruction(tokenList, section, cmp, "CMP")


# decodeB:: Iterator[tokens.Token] -> Node.Section -> Node
# decode the branch instruction
def decodeBranch(tokenList: List[tokens.Token], section: nodes.Node.Section,
                 condition: Callable[[programState.StatusRegister], bool]) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "Branch instruction"), []
    label, *tokenList = tokenList
    if isinstance(label, tokens.Label):
        def branchTo(state: programState.ProgramState) -> programState.ProgramState:
            if condition(state.status):
                address = programState.getLabelAddress(state, label.contents)

                return programState.setReg(state, "PC", address-4)
            else:
                return state

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
        def branchTo(state: programState.ProgramState) -> programState.ProgramState:
            # Save return address in LR
            pc = programState.getReg(state, "PC")
            state = programState.setReg(state, "LR", pc)

            address = programState.getLabelAddress(state, label.contents)
            return programState.setReg(state, "PC", address-4)

        return nodes.InstructionNode(section, label.line, branchTo), tokenList
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(label.line, label.contents, "a label"), advanceToNewline(tokenList)


# saves one function per instruction to be used to decode that instruction into a Node
tokenFunctions: Dict[str, Callable[[List[tokens.Token], nodes.Node.Section], Tuple[nodes.Node, List[tokens.Token]]]] = {
    "MOV": decodeMOV,
    # decodeLDR expects a int as it's third argument to tell the difference between LDR, LDRH and LDRB
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
