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


# generateUnexpectedTokenError:: int -> str -> str -> ErrorNode
# generate an error because of an unexpected token
def generateImmediateOutOfRangeError(line: int, value: int, maxValue: int) -> nodes.ErrorNode:
    return nodes.ErrorNode(f"\033[31m"  # red color
                           f"File \"$fileName$\", line {line}\n"
                           f"\tSyntax error: Immediate value out of range: value must be below {maxValue} but is {value}"
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
            def movReg(state: programState.ProgramState) -> programState.ProgramState:
                value = programState.getReg(state, src.contents)
                return programState.setReg(state, dest.contents, value)
            return nodes.InstructionNode(section, dest.line, movReg), tokenList
        elif isinstance(src, tokens.ImmediateValue):
            # check 8 bits
            if src.value > 0xFF:
                return generateImmediateOutOfRangeError(src.line, src.value, 0xFF), tokenList

            def movImmed(state: programState.ProgramState) -> programState.ProgramState:
                return programState.setReg(state, dest.contents, src.value)
            return nodes.InstructionNode(section, dest.line, movImmed), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(src.line, src.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    else:
        # Wrong token, generate an error
        return generateUnexpectedTokenError(separator.line, separator.contents, "','"), advanceToNewline(tokenList)


# decodeLDR:: [Token] -> Node.Section -> ijt -> (Node, [Token])
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
                val: int = programState.getLabelAddress(state, label.label)
                return programState.setReg(state, dest.contents, val)
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
                    return programState.loadRegister(state, adr, bitSize, dest.contents)
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
                        return programState.loadRegister(state, adr1 + adr2, bitSize, dest.contents)
                    return nodes.InstructionNode(section, dest.line, ldrDualReg), tokenList
                elif isinstance(src2, tokens.ImmediateValue):
                    src2: tokens.ImmediateValue = src2
                    value: int = src2.value
                    # check bit length - 5 bits or 8 for full word relative to SP or PC
                    src1Text = src1.contents.upper()
                    if src1Text == "SP" or src1Text == "PC":
                        if bitSize == 32:
                            if value > 0xFF:
                                return generateImmediateOutOfRangeError(src2.line, value, 0xFF), tokenList
                            else:
                                value = 4 + (value*4)
                        else:
                            return nodes.ErrorNode(f"\033[31m"  # red color
                                                   f"File \"$fileName$\", line {src2.line}\n"
                                                   f"\tSyntax error: Cannot only load a full word relative to PC or LR"
                                                   f"\033[0m\n"), tokenList
                    else:
                        if value > 0b0001_1111:
                            return generateImmediateOutOfRangeError(src2.line, value, 0b0111_1111), tokenList
                        else:
                            # multiple by 4
                            if bitSize == 32:
                                value *= 4
                            elif bitSize == 16:
                                value *= 2

                    def ldrRegImmed(state: programState.ProgramState) -> programState.ProgramState:
                        adr = programState.getReg(state, src1.contents)
                        return programState.loadRegister(state, adr + value, bitSize, dest.contents)
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


# decodeLDR:: [Token] -> Node.Section -> ijt -> (Node, [Token])
# bitSize: the number ob bits to load, either 32, 16 or 8 bit
# decode the LDR, LDRH and LDRB instructions
def decodeSTR(tokenList: List[tokens.Token], section: nodes.Node.Section, bitSize: int) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, "STR instruction"), []
    src, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(src.line, "STR instruction"), []
    if not isinstance(src, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(src.line, src.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        separator, *tokenList = tokenList
        if isinstance(separator, tokens.Separator) and separator.contents == "[":
            if len(tokenList) < 2:
                return generateToFewTokensError(src.line, "STR instruction"), []
            dest1, *tokenList = tokenList
            if not isinstance(dest1, tokens.Register):
                # Wrong token, generate an error
                return generateUnexpectedTokenError(dest1.line, dest1.contents, "a register"), advanceToNewline(tokenList)
            separator, *tokenList = tokenList
            if isinstance(separator, tokens.Separator) and separator.contents == "]":
                def strOneReg(state: programState.ProgramState) -> programState.ProgramState:
                    adr = programState.getReg(state, dest1.contents)
                    return programState.storeRegister(state, adr, src.contents, bitSize)
                return nodes.InstructionNode(section, src.line, strOneReg), tokenList
            elif isinstance(separator, tokens.Separator) and separator.contents == ",":
                if len(tokenList) < 2:
                    return generateToFewTokensError(src.line, "STR instruction"), []
                dest2, separator, *tokenList = tokenList
                if isinstance(separator, tokens.Separator) and separator.contents != "]":
                    return generateUnexpectedTokenError(separator.line, separator.contents, "']'"), advanceToNewline(tokenList)
                if isinstance(dest2, tokens.Register):
                    def strDualReg(state: programState.ProgramState) -> programState.ProgramState:
                        adr1 = programState.getReg(state, dest1.contents)
                        adr2 = programState.getReg(state, dest2.contents)
                        return programState.storeRegister(state, adr1 + adr2, src.contents, bitSize)
                    return nodes.InstructionNode(section, src.line, strDualReg), tokenList
                elif isinstance(dest2, tokens.ImmediateValue):
                    dest2: tokens.ImmediateValue = dest2
                    value: int = dest2.value
                    # check bit length - 5 bits or 8 for full word relative to SP or PC
                    dest1Text = dest1.contents.upper()
                    if dest1Text == "SP" or dest1Text == "PC":
                        if bitSize == 32:
                            if value > 0xFF:
                                return generateImmediateOutOfRangeError(dest2.line, value, 0xFF), tokenList
                            else:
                                value = 4 + (value*4)
                        else:
                            return nodes.ErrorNode(f"\033[31m"  # red color
                                                   f"File \"$fileName$\", line {dest2.line}\n"
                                                   f"\tSyntax error: Cannot only store a full word relative to PC or LR"
                                                   f"\033[0m\n"), tokenList
                    else:
                        if value > 0b0001_1111:
                            return generateImmediateOutOfRangeError(dest2.line, value, 0b0111_1111), tokenList
                        else:
                            # multiple by 4
                            if bitSize == 32:
                                value *= 4
                            elif bitSize == 16:
                                value *= 2

                    def strRegImmed(state: programState.ProgramState) -> programState.ProgramState:
                        adr = programState.getReg(state, dest1.contents)
                        return programState.storeRegister(state, adr + value, src.contents, bitSize)
                    return nodes.InstructionNode(section, src.line, strRegImmed), tokenList
                else:
                    # Wrong token, generate an error
                    return generateUnexpectedTokenError(dest2.line, dest2.contents, "a register or an immediate value"), advanceToNewline(tokenList)
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
def getRegisterList(tokenList: List[tokens.Token], instruction: str, isOpened: bool = False) -> Tuple[Union[List[tokens.Register], nodes.ErrorNode], List[tokens.Token]]:
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


# decodePUSH:: [Token] -> Node.Section -> (Node, [Token])
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
        # check address is in 0...stacksize
        if address > (programState.getLabelAddress(state, "__STACKSIZE")-4) or address < 0:
            # TODO err
            print("stack overflow")
            return state
        state = programState.storeRegister(state, address, head.contents, 32)
        state = programState.setReg(state, "SP", address)
        return push(state, tail)

    return nodes.InstructionNode(section, regs[0].line, lambda x: push(x, regs)), tokenList


# decodePOP:: [Token] -> Node.Section -> (Node, [Token])
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
        # check address is in 0...stacksize
        if address > (programState.getLabelAddress(state, "__STACKSIZE")-4) or address < 0:
            # TODO err
            print("stack underflow")
            return state
        state = programState.loadRegister(state, address, 32, head.contents)
        state = programState.setReg(state, "SP", address + 4)
        return pop(state, tail)

    return nodes.InstructionNode(section, regs[0].line, lambda x: pop(x, list(reversed(regs)))), tokenList


# decodeALUInstruction:: [Token] -> Section ->
# (Node.Section -> int -> String -> Either int String -> Either int String None -> Node)
# -> String -> (Node, [Token])
# Decodes any ALU instruction that uses the syntax INSTR {rd,} rn, <rm|#immed8>
# When the instruction is run, the func parameter is used to perform the right action for the instruction and
#   run checks specific to that instruction
def decodeALUInstruction(tokenList: List[tokens.Token], section: nodes.Node.Section,
                         func: Callable[[nodes.Node.Section, int, str, Union[int, str], Union[int, str, None]], nodes.Node],
                         instruction: str) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return generateToFewTokensError(-1, instruction + " instruction"), []
    arg1, *tokenList = tokenList
    if len(tokenList) < 2:
        return generateToFewTokensError(arg1.line, instruction + " instruction"), []
    seperator1, arg2, *tokenList = tokenList
    if len(tokenList) < 4:
        seperator2 = seperator1
        # arg3 does not exist
        arg3 = None
    else:
        seperator2, arg3, *tokenList = tokenList
    if not (isinstance(seperator1, tokens.Separator) and seperator1.contents == ","):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(seperator1.line, seperator1.contents, "','"), advanceToNewline(tokenList)
    if not (isinstance(seperator2, tokens.Separator) and seperator2.contents == ","):
        if isinstance(seperator2, tokens.NewLine):
            tokenList = [seperator2, arg3] + tokenList
            # arg3 does not exist
            arg3 = None
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(seperator2.line, seperator2.contents, "',' or End of line"), advanceToNewline(tokenList)

    if not isinstance(arg1, tokens.Register):
        # Wrong token, generate an error
        return generateUnexpectedTokenError(arg1.line, arg1.contents, "a register"), advanceToNewline(tokenList)
    if arg3 is None:
        if isinstance(arg2, tokens.Register):
            return func(section, arg1.line, arg1.contents, arg2.contents, None), tokenList
        elif isinstance(arg2, tokens.ImmediateValue):
            return func(section, arg1.line, arg1.contents, arg2.value, None), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(arg2.line, arg2.contents, "a register or an immediate value"), advanceToNewline(tokenList)
    else:
        if not isinstance(arg2, tokens.Register):
            # Wrong token, generate an error
            return generateUnexpectedTokenError(arg2.line, arg2.contents, "a register"), advanceToNewline(tokenList)
        if isinstance(arg3, tokens.Register):
            return func(section, arg1.line, arg1.contents, arg2.contents, arg3.contents), tokenList
        elif isinstance(arg3, tokens.ImmediateValue):
            return func(section, arg1.line, arg1.contents, arg2.contents, arg3.value), tokenList
        else:
            # Wrong token, generate an error
            return generateUnexpectedTokenError(arg3.line, arg3.contents, "a register or an immediate value"), advanceToNewline(tokenList)


# decodeSUB:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the SUB instruction
# This function is called by decodeALUInstruction while decoding the SUB instruction
def decodeSUB(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is None:
        # move arg2 to arg3 and copy arg1 to arg2
        arg3 = arg2
        arg2 = arg1

    if isinstance(arg3, int):
        arg3 = arg3 & 0XFFFFFFFF
        if arg1.upper() == arg2.upper():
            if arg1.upper() == "SP":
                # check 7 bits
                if arg3 > 0b0111_1111:
                    return generateImmediateOutOfRangeError(line, arg3, 0b0111_1111)
                else:
                    # multiple by 4
                    arg3 *= 4
            else:
                # check 8 bits
                if arg3 > 0xFF:
                    return generateImmediateOutOfRangeError(line, arg3, 0xFF)
        else:
            # check 3 bits
            if arg3 > 0b0111:
                return generateImmediateOutOfRangeError(line, arg3, 0b0111)

    def run(state: programState.ProgramState) -> programState.ProgramState:
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
        n = bool((out >> 31) & 1)
        z = out32 == 0

        state = programState.setReg(state, arg1, out32)
        state = programState.setALUState(state, programState.StatusRegister(n, z, c, v))

        return state
    return nodes.InstructionNode(section, line, run)


# decodeADD:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the ADD instruction
# This function is called by decodeALUInstruction while decoding the ADD instruction
def decodeADD(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is None:
        # move arg2 to arg3 and copy arg1 to arg2
        arg3 = arg2
        arg2 = arg1

    if isinstance(arg3, int):
        arg3 = arg3 & 0XFFFFFFFF
        if arg1.upper() == arg2.upper():
            if arg1.upper() == "SP":
                # check 7 bits
                if arg3 > 0b0111_1111:
                    return generateImmediateOutOfRangeError(line, arg3, 0b0111_1111)
                else:
                    # multiple by 4
                    arg3 *= 4
            else:
                # check 8 bits
                if arg3 > 0xFF:
                    return generateImmediateOutOfRangeError(line, arg3, 0xFF)
        else:
            if arg2.upper() == "SP":  # arg1 can't be SP when arg2 is because arg1.upper() == arg2.upper() returned False
                # check 8 bits
                if arg3 > 0xFF:
                    return generateImmediateOutOfRangeError(line, arg3, 0xFF)
                else:
                    # multiple by 4
                    arg3 *= 4
            # check 3 bits
            if arg3 > 0b0111:
                return generateImmediateOutOfRangeError(line, arg3, 0b0111)

    def run(state: programState.ProgramState) -> programState.ProgramState:
        a = programState.getReg(state, arg2)
        if isinstance(arg3, str):
            b = programState.getReg(state, arg3)
        else:
            b = arg3 & 0XFFFFFFFF

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
        n = bool((out >> 31) & 1)
        z = out32 == 0

        state = programState.setReg(state, arg1, out32)
        state = programState.setALUState(state, programState.StatusRegister(n, z, c, v))

        return state
    return nodes.InstructionNode(section, line, run)


# decodeCMP:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the CMP instruction
# This function is called by decodeALUInstruction while decoding the CMP instruction
def decodeCMP(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is not None:
        return generateUnexpectedTokenError(line, (", " + arg3) if isinstance(arg3, str) else (', #'+str(arg3)), "End of line")

    if isinstance(arg2, int):
        arg2 = arg2 & 0XFFFFFFFF
        # check 8 bits
        if arg2 > 0xFF:
            return generateImmediateOutOfRangeError(line, arg2, 0xFF)

    def run(state: programState.ProgramState) -> programState.ProgramState:
        a = programState.getReg(state, arg1)
        if isinstance(arg2, str):
            b = programState.getReg(state, arg2)
        else:
            b = arg2 & 0XFFFFFFFF

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
        n = bool((out >> 31) & 1)
        z = out32 == 0

        # state = programState.setReg(state, arg1, out32)
        state = programState.setALUState(state, programState.StatusRegister(n, z, c, v))

        return state

    return nodes.InstructionNode(section, line, run)


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
                # Subtract 4 because we will add 4 to the address later in the run loop and we need to start at address and not address+4
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

            # Subtract 4 because we will add 4 to the address later in the run loop and we need to start at address and not address+4
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
    "STR": lambda a, b: decodeSTR(a, b, 32),
    "STRH": lambda a, b: decodeSTR(a, b, 16),
    "STRB": lambda a, b: decodeSTR(a, b, 8),
    "LDRSH": None,
    "LDRSB": None,

    "PUSH": decodePUSH,
    "POP": decodePOP,
    "LDM": None,
    "LDMIA": None,
    "STMIA": None,

    "ADD": lambda a, b: decodeALUInstruction(a, b, decodeADD, "ADD"),
    "ADC": None,
    "SUB": lambda a, b: decodeALUInstruction(a, b, decodeSUB, "SUB"),
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
    "CMP": lambda a, b: decodeALUInstruction(a, b, decodeCMP, "CMP"),
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
