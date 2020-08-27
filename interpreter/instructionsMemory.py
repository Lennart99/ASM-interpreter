from typing import List, Tuple, Union

import tokens
import programState
import nodes
import instructionsUtils


# decodeLDR:: [Token] -> Node.Section -> int -> bool -> (Node, [Token])
# bitSize: the number ob bits to load, either 32, 16 or 8 bit
# decode the LDR, LDRH and LDRB instructions
def decodeLDR(tokenList: List[tokens.Token], section: nodes.Node.Section, bitSize: int, sign_extend: bool) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return instructionsUtils.generateToFewTokensError(-1, "LDR instruction"), []
    dest, *tokenList = tokenList
    if len(tokenList) < 2:
        return instructionsUtils.generateToFewTokensError(dest.line, "LDR instruction"), []
    if not isinstance(dest, tokens.Register):
        # Wrong token, generate an error
        return instructionsUtils.generateUnexpectedTokenError(dest.line, dest.contents, "a register or an immediate value"), instructionsUtils.advanceToNewline(tokenList)
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        separator, *tokenList = tokenList
        if isinstance(separator, tokens.LoadImmediateValue) and not sign_extend:  # sign extend is not supported for this syntax
            value: int = separator.value & 0xFFFFFFFF

            def ldrImmed(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                state.setReg(dest.contents, value)
                return state, None
            return nodes.InstructionNode(section, dest.line, ldrImmed), tokenList
        elif isinstance(separator, tokens.LoadLabel) and not sign_extend:  # sign extend is not supported for this syntax
            label: tokens.LoadLabel = separator

            def ldrLabel(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                val: Union[int, programState.RunError] = state.getLabelAddress(label.label)
                if isinstance(val, programState.RunError):
                    return state, val
                else:
                    state.setReg(dest.contents, val)
                    return state, None
            return nodes.InstructionNode(section, dest.line, ldrLabel), tokenList
        elif isinstance(separator, tokens.Separator) and separator.contents == "[":
            if len(tokenList) < 2:
                return instructionsUtils.generateToFewTokensError(dest.line, "LDR instruction"), []
            src1, *tokenList = tokenList
            if not isinstance(src1, tokens.Register):
                # Wrong token, generate an error
                return instructionsUtils.generateUnexpectedTokenError(src1.line, src1.contents, "a register"), instructionsUtils.advanceToNewline(tokenList)
            separator, *tokenList = tokenList
            if isinstance(separator, tokens.Separator) and separator.contents == "]":
                def ldrOneReg(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                    adr = state.getReg(src1.contents)
                    err: Union[None, programState.RunError] = state.loadRegister(adr, bitSize, sign_extend, dest.contents)
                    return state, err
                return nodes.InstructionNode(section, dest.line, ldrOneReg), tokenList
            elif isinstance(separator, tokens.Separator) and separator.contents == ",":
                if len(tokenList) < 2:
                    return instructionsUtils.generateToFewTokensError(dest.line, "LDR instruction"), []
                src2, separator, *tokenList = tokenList
                if isinstance(separator, tokens.Separator) and separator.contents != "]":
                    return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "']'"), instructionsUtils.advanceToNewline(tokenList)
                if isinstance(src2, tokens.Register):
                    def ldrDualReg(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                        adr1 = state.getReg(src1.contents)
                        adr2 = state.getReg(src2.contents)
                        err: Union[None, programState.RunError] = state.loadRegister(adr1 + adr2, bitSize, sign_extend, dest.contents)
                        return state, err
                    return nodes.InstructionNode(section, dest.line, ldrDualReg), tokenList
                elif isinstance(src2, tokens.ImmediateValue):
                    src2: tokens.ImmediateValue = src2
                    value: int = src2.value
                    # check bit length - 5 bits or 8 for full word relative to SP or PC
                    src1Text = src1.contents.upper()
                    if src1Text == "SP" or src1Text == "PC":
                        if bitSize == 32:
                            if value > 0xFF:
                                return instructionsUtils.generateImmediateOutOfRangeError(src2.line, value, 0xFF), tokenList
                            else:
                                value = 4 + (value*4)
                        else:
                            return nodes.ErrorNode(f"\033[31m"  # red color
                                                   f"File \"$fileName$\", line {src2.line}\n"
                                                   f"\tSyntax error: Cannot only load a full word relative to PC or LR"
                                                   f"\033[0m\n"), tokenList
                    else:
                        if value > 0b0001_1111:
                            return instructionsUtils.generateImmediateOutOfRangeError(src2.line, value, 0b0111_1111), tokenList
                        else:
                            # multiple by 4
                            if bitSize == 32:
                                value *= 4
                            elif bitSize == 16:
                                value *= 2

                    def ldrRegImmed(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                        adr = state.getReg(src1.contents)
                        err: Union[None, programState.RunError] = state.loadRegister(adr + value, bitSize, sign_extend, dest.contents)
                        return state, err
                    return nodes.InstructionNode(section, dest.line, ldrRegImmed), tokenList
                else:
                    # Wrong token, generate an error
                    return instructionsUtils.generateUnexpectedTokenError(src2.line, src2.contents, "a register or an immediate value"), instructionsUtils.advanceToNewline(tokenList)
            else:
                # Wrong token, generate an error
                return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "']' or ','"), instructionsUtils.advanceToNewline(tokenList)
        else:
            # Wrong token, generate an error
            return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "'['"), instructionsUtils.advanceToNewline(tokenList)
    else:
        # Wrong token, generate an error
        return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "','"), instructionsUtils.advanceToNewline(tokenList)


# decodeLDR:: [Token] -> Node.Section -> ijt -> (Node, [Token])
# bitSize: the number ob bits to load, either 32, 16 or 8 bit
# decode the LDR, LDRH and LDRB instructions
def decodeSTR(tokenList: List[tokens.Token], section: nodes.Node.Section, bitSize: int) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return instructionsUtils.generateToFewTokensError(-1, "STR instruction"), []
    src, *tokenList = tokenList
    if len(tokenList) < 2:
        return instructionsUtils.generateToFewTokensError(src.line, "STR instruction"), []
    if not isinstance(src, tokens.Register):
        # Wrong token, generate an error
        return instructionsUtils.generateUnexpectedTokenError(src.line, src.contents, "a register or an immediate value"), instructionsUtils.advanceToNewline(tokenList)
    separator, *tokenList = tokenList
    if isinstance(separator, tokens.Separator) and separator.contents == ",":
        separator, *tokenList = tokenList
        if isinstance(separator, tokens.Separator) and separator.contents == "[":
            if len(tokenList) < 2:
                return instructionsUtils.generateToFewTokensError(src.line, "STR instruction"), []
            dest1, *tokenList = tokenList
            if not isinstance(dest1, tokens.Register):
                # Wrong token, generate an error
                return instructionsUtils.generateUnexpectedTokenError(dest1.line, dest1.contents, "a register"), instructionsUtils.advanceToNewline(tokenList)
            separator, *tokenList = tokenList
            if isinstance(separator, tokens.Separator) and separator.contents == "]":
                def strOneReg(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                    adr = state.getReg(dest1.contents)
                    newState: Union[None, programState.RunError] = state.storeRegister(adr, src.contents, bitSize)
                    return state, newState
                return nodes.InstructionNode(section, src.line, strOneReg), tokenList
            elif isinstance(separator, tokens.Separator) and separator.contents == ",":
                if len(tokenList) < 2:
                    return instructionsUtils.generateToFewTokensError(src.line, "STR instruction"), []
                dest2, separator, *tokenList = tokenList
                if isinstance(separator, tokens.Separator) and separator.contents != "]":
                    return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "']'"), instructionsUtils.advanceToNewline(tokenList)
                if isinstance(dest2, tokens.Register):
                    def strDualReg(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                        adr1 = state.getReg(dest1.contents)
                        adr2 = state.getReg(dest2.contents)
                        newState: Union[None, programState.RunError] = state.storeRegister(adr1 + adr2, src.contents, bitSize)
                        return state, newState
                    return nodes.InstructionNode(section, src.line, strDualReg), tokenList
                elif isinstance(dest2, tokens.ImmediateValue):
                    dest2: tokens.ImmediateValue = dest2
                    value: int = dest2.value
                    # check bit length - 5 bits or 8 for full word relative to SP or PC
                    dest1Text = dest1.contents.upper()
                    if dest1Text == "SP" or dest1Text == "PC":
                        if bitSize == 32:
                            if value > 0xFF:
                                return instructionsUtils.generateImmediateOutOfRangeError(dest2.line, value, 0xFF), tokenList
                            else:
                                value = 4 + (value*4)
                        else:
                            return nodes.ErrorNode(f"\033[31m"  # red color
                                                   f"File \"$fileName$\", line {dest2.line}\n"
                                                   f"\tSyntax error: Cannot only store a full word relative to PC or LR"
                                                   f"\033[0m\n"), tokenList
                    else:
                        if value > 0b0001_1111:
                            return instructionsUtils.generateImmediateOutOfRangeError(dest2.line, value, 0b0111_1111), tokenList
                        else:
                            # multiple by 4
                            if bitSize == 32:
                                value *= 4
                            elif bitSize == 16:
                                value *= 2

                    def strRegImmed(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
                        adr = state.getReg(dest1.contents)
                        newState: Union[None, programState.RunError] = state.storeRegister(adr + value, src.contents, bitSize)
                        return state, newState
                    return nodes.InstructionNode(section, src.line, strRegImmed), tokenList
                else:
                    # Wrong token, generate an error
                    return instructionsUtils.generateUnexpectedTokenError(dest2.line, dest2.contents, "a register or an immediate value"), instructionsUtils.advanceToNewline(tokenList)
            else:
                # Wrong token, generate an error
                return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "']' or ','"), instructionsUtils.advanceToNewline(tokenList)
        else:
            # Wrong token, generate an error
            return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "'['"), instructionsUtils.advanceToNewline(tokenList)
    else:
        # Wrong token, generate an error
        return instructionsUtils.generateUnexpectedTokenError(separator.line, separator.contents, "','"), instructionsUtils.advanceToNewline(tokenList)


# getRegisterList:: [Token] -> String -> boolean -> (Either [Token] ErrorNode, [Token]]
# The instruction string is used to create the error messages
def getRegisterList(tokenList: List[tokens.Token], instruction: str) -> Tuple[Union[List[str], nodes.ErrorNode], List[tokens.Token]]:
    if len(tokenList) == 0:
        return instructionsUtils.generateToFewTokensError(-1, instruction + " instruction"), []

    regs = []

    nextToken, *tokenList = tokenList
    if isinstance(nextToken, tokens.Separator) and nextToken.contents == "{":
        if len(tokenList) == 0:
            return instructionsUtils.generateToFewTokensError(nextToken.line, instruction + " instruction"), instructionsUtils.advanceToNewline(tokenList)
        nextToken, *tokenList = tokenList
        if isinstance(nextToken, tokens.Register):
            regs.append(nextToken.contents)
        else:
            return instructionsUtils.generateUnexpectedTokenError(nextToken.line, nextToken.contents, "a register"), instructionsUtils.advanceToNewline(tokenList)
    else:
        return instructionsUtils.generateUnexpectedTokenError(nextToken.line, nextToken.contents, "'{'"), instructionsUtils.advanceToNewline(tokenList)
    # add remaining registers
    while True:
        nextToken, *tokenList = tokenList
        if isinstance(nextToken, tokens.Separator) and nextToken.contents == ",":
            if len(tokenList) == 0:
                return instructionsUtils.generateToFewTokensError(nextToken.line, instruction + " instruction"), []
            nextToken, *tokenList = tokenList
            if isinstance(nextToken, tokens.Register):
                regs.append(nextToken.contents)
            else:
                return instructionsUtils.generateUnexpectedTokenError(nextToken.line, nextToken.contents, "a register"), instructionsUtils.advanceToNewline(tokenList)
        elif isinstance(nextToken, tokens.Separator) and nextToken.contents == "}":
            break
        else:
            return instructionsUtils.generateUnexpectedTokenError(nextToken.line, nextToken.contents, "',' or '}'"), instructionsUtils.advanceToNewline(tokenList)

    return sorted(list(set(regs))), tokenList


# decodePUSH:: [Token] -> Node.Section -> (Node, [Token])
# decode the PUSH instruction
def decodePUSH(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    line = tokenList[0].line

    regs, tokenList = getRegisterList(tokenList, "PUSH")

    if isinstance(regs, nodes.ErrorNode):
        return regs, tokenList

    def push(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        if len(regs) == 0:
            return state, None
        # head, *tail = registers

        address = state.getReg("SP")
        # check address is in 0...stacksize
        if address > (state.getLabelAddress("__STACKSIZE")) or address < 0:
            return state, programState.RunError("Stack overflow", programState.RunError.ErrorType.Error)

        for reg in regs:
            address -= 4
            err = state.storeRegister(address, reg, 32)
            if err is not None:
                return state, err
        state.setReg("SP", address)
        return state, None

    return nodes.InstructionNode(section, line, push), tokenList


# decodePOP:: [Token] -> Node.Section -> (Node, [Token])
# decode the POP instruction
def decodePOP(tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[nodes.Node, List[tokens.Token]]:
    line = tokenList[0].line

    regs, tokenList = getRegisterList(tokenList, "POP")

    if isinstance(regs, nodes.ErrorNode):
        return regs, tokenList
    regs = list(reversed(regs))

    def pop(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        if len(regs) == 0:
            return state, None
        # head, *tail = registers

        address = state.getReg("SP")
        # check address is in 0...stacksize
        if address > (state.getLabelAddress("__STACKSIZE")) or address < 0:
            return state, programState.RunError("All stack entries have been pop'ed already", programState.RunError.ErrorType.Error)
        for reg in regs:
            err = state.loadRegister(address, 32, False, reg)
            address += 4
            if err is not None:
                return state, err
        state.setReg("SP", address)
        return state, None

    return nodes.InstructionNode(section, line, pop), tokenList
