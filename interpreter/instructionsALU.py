from typing import Callable, List, Tuple, Union

import tokens
import programState
import nodes
import instructionsUtils


# decodeALUInstruction:: [Token] -> Section ->
# (Node.Section -> int -> String -> Either int String -> Either int String None -> Node)
# -> String -> (Node, [Token])
# Decodes any ALU instruction that uses the syntax INSTR {rd,} rn, <rm|#immed8>
# When the instruction is run, the func parameter is used to perform the right action for the instruction and
#   run checks specific to that instruction
def decodeALUInstruction(tokenList: List[tokens.Token], section: nodes.Node.Section,
                         nodeGen: Callable[[nodes.Node.Section, int, str, Union[int, str], Union[int, str, None]], nodes.Node],
                         instruction: str) -> Tuple[nodes.Node, List[tokens.Token]]:
    if len(tokenList) == 0:
        return instructionsUtils.generateToFewTokensError(-1, instruction + " instruction"), []
    arg1, *tokenList = tokenList
    if len(tokenList) < 2:
        return instructionsUtils.generateToFewTokensError(arg1.line, instruction + " instruction"), []
    seperator1, arg2, *tokenList = tokenList
    if len(tokenList) < 4:
        seperator2 = seperator1
        # arg3 does not exist
        arg3 = None
    else:
        seperator2, arg3, *tokenList = tokenList
    if not (isinstance(seperator1, tokens.Separator) and seperator1.contents == ","):
        # Wrong token, generate an error
        return instructionsUtils.generateUnexpectedTokenError(seperator1.line, seperator1.contents, "','"), instructionsUtils.advanceToNewline(tokenList)
    if not (isinstance(seperator2, tokens.Separator) and seperator2.contents == ","):
        if isinstance(seperator2, tokens.NewLine):
            tokenList = [seperator2, arg3] + tokenList
            # arg3 does not exist
            arg3 = None
        else:
            # Wrong token, generate an error
            return instructionsUtils.generateUnexpectedTokenError(seperator2.line, seperator2.contents, "',' or End of line"), instructionsUtils.advanceToNewline(tokenList)

    if not isinstance(arg1, tokens.Register):
        # Wrong token, generate an error
        return instructionsUtils.generateUnexpectedTokenError(arg1.line, arg1.contents, "a register"), instructionsUtils.advanceToNewline(tokenList)
    if arg3 is None:
        if isinstance(arg2, tokens.Register):
            return nodeGen(section, arg1.line, arg1.contents, arg2.contents, None), tokenList
        elif isinstance(arg2, tokens.ImmediateValue):
            return nodeGen(section, arg1.line, arg1.contents, arg2.value, None), tokenList
        else:
            # Wrong token, generate an error
            return instructionsUtils.generateUnexpectedTokenError(arg2.line, arg2.contents, "a register or an immediate value"), instructionsUtils.advanceToNewline(tokenList)
    else:
        if not isinstance(arg2, tokens.Register):
            # Wrong token, generate an error
            return instructionsUtils.generateUnexpectedTokenError(arg2.line, arg2.contents, "a register"), instructionsUtils.advanceToNewline(tokenList)
        if isinstance(arg3, tokens.Register):
            return nodeGen(section, arg1.line, arg1.contents, arg2.contents, arg3.contents), tokenList
        elif isinstance(arg3, tokens.ImmediateValue):
            return nodeGen(section, arg1.line, arg1.contents, arg2.contents, arg3.value), tokenList
        else:
            # Wrong token, generate an error
            return instructionsUtils.generateUnexpectedTokenError(arg3.line, arg3.contents, "a register or an immediate value"), instructionsUtils.advanceToNewline(tokenList)


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
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111_1111)
                else:
                    # multiple by 4
                    arg3 *= 4
            else:
                # check 8 bits
                if arg3 > 0xFF:
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)
        else:
            # check 3 bits
            if arg3 > 0b0111:
                return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3 & 0XFFFFFFFF

        minusB = ((~b)+1) & 0xFFFFFFFF
        out = a + minusB
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (minusB >> 31) & 1

        v = signA == signB and signB != bit31
        c = bool((out >> 32) & 1)
        n = bool((out >> 31) & 1)
        z = out32 == 0

        state.setReg(arg1, out32)
        state.setALUState(programState.StatusRegister(n, z, c, v))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeSBC:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the SBC instruction
# This function is called by decodeALUInstruction while decoding the SBC instruction
def decodeSBC(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
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
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111_1111)
                else:
                    # multiple by 4
                    arg3 *= 4
            else:
                # check 8 bits
                if arg3 > 0xFF:
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)
        else:
            # check 3 bits
            if arg3 > 0b0111:
                return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3

        # subtract one more if carry is set
        if state.status.C:
            b += 1

        minusB = ((~b)+1) & 0xFFFFFFFF
        out = a + minusB
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (minusB >> 31) & 1

        v = signA == signB and signB != bit31
        c = bool((out >> 32) & 1)
        n = bool((out >> 31) & 1)
        z = out32 == 0

        state.setReg(arg1, out32)
        state.setALUState(programState.StatusRegister(n, z, c, v))

        return state, None
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
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111_1111)
                else:
                    # multiple by 4
                    arg3 *= 4
            else:
                # check 8 bits
                if arg3 > 0xFF:
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)
        else:
            if arg2.upper() == "SP":  # arg1 can't be SP when arg2 is because arg1.upper() == arg2.upper() returned False
                # check 8 bits
                if arg3 > 0xFF:
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)
                else:
                    # multiple by 4
                    arg3 *= 4
            # check 3 bits
            if arg3 > 0b0111:
                return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3 & 0XFFFFFFFF

        out = a + b
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (b >> 31) & 1

        v = signA == signB and signB != bit31
        c = bool((out >> 32) & 1)
        n = bool((out >> 31) & 1)
        z = out32 == 0

        state.setReg(arg1, out32)
        state.setALUState(programState.StatusRegister(n, z, c, v))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeADC:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the ADC instruction
# This function is called by decodeALUInstruction while decoding the ADC instruction
def decodeADC(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
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
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111_1111)
                else:
                    # multiple by 4
                    arg3 *= 4
            else:
                # check 8 bits
                if arg3 > 0xFF:
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)
        else:
            if arg2.upper() == "SP":  # arg1 can't be SP when arg2 is because arg1.upper() == arg2.upper() returned False
                # check 8 bits
                if arg3 > 0xFF:
                    return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)
                else:
                    # multiple by 4
                    arg3 *= 4
            # check 3 bits
            if arg3 > 0b0111:
                return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0b0111)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3 & 0XFFFFFFFF

        # subtract one more if carry is set
        if state.status.C:
            b += 1

        out = a + b
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (b >> 31) & 1

        v = signA == signB and signB != bit31
        c = bool((out >> 32) & 1)
        n = bool((out >> 31) & 1)
        z = out32 == 0

        state.setReg(arg1, out32)
        state.setALUState(programState.StatusRegister(n, z, c, v))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeAND:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the AND instruction
# This function is called by decodeALUInstruction while decoding the AND instruction
def decodeAND(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is None:
        # move arg2 to arg3 and copy arg1 to arg2
        arg3 = arg2
        arg2 = arg1

    if isinstance(arg3, int):
        arg3 = arg3 & 0XFFFFFFFF
        if arg3 > 0xFF:
            return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3 & 0XFFFFFFFF

        out = a & b

        n = bool((out >> 31) & 1)
        z = out == 0

        state.setReg(arg1, out)
        state.setALUState(programState.StatusRegister(n, z, False, False))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeEOR:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the EOR instruction
# This function is called by decodeALUInstruction while decoding the EOR instruction
def decodeEOR(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is None:
        # move arg2 to arg3 and copy arg1 to arg2
        arg3 = arg2
        arg2 = arg1

    if isinstance(arg3, int):
        arg3 = arg3 & 0XFFFFFFFF
        if arg3 > 0xFF:
            return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3 & 0XFFFFFFFF

        out = a ^ b

        n = bool((out >> 31) & 1)
        z = out == 0

        state.setReg(arg1, out)
        state.setALUState(programState.StatusRegister(n, z, False, False))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeORR:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the ORR instruction
# This function is called by decodeALUInstruction while decoding the ORR instruction
def decodeORR(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is None:
        # move arg2 to arg3 and copy arg1 to arg2
        arg3 = arg2
        arg2 = arg1

    if isinstance(arg3, int):
        arg3 = arg3 & 0XFFFFFFFF
        if arg3 > 0xFF:
            return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3 & 0XFFFFFFFF

        out = a | b

        n = bool((out >> 31) & 1)
        z = out == 0

        state.setReg(arg1, out)
        state.setALUState(programState.StatusRegister(n, z, False, False))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeBIC:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the BIC instruction
# This function is called by decodeALUInstruction while decoding the BIC instruction
def decodeBIC(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is None:
        # move arg2 to arg3 and copy arg1 to arg2
        arg3 = arg2
        arg2 = arg1

    if isinstance(arg3, int):
        arg3 = arg3 & 0XFFFFFFFF
        if arg3 > 0xFF:
            return instructionsUtils.generateImmediateOutOfRangeError(line, arg3, 0xFF)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg2)
        if isinstance(arg3, str):
            b = state.getReg(arg3)
        else:
            b = arg3 & 0XFFFFFFFF

        out = a & (b ^ 0xFFFF_FFFF)  # out = a & ! b

        n = bool((out >> 31) & 1)
        z = out == 0

        state.setReg(arg1, out)
        state.setALUState(programState.StatusRegister(n, z, False, False))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeCMP:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the CMP instruction
# This function is called by decodeALUInstruction while decoding the CMP instruction
def decodeCMP(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is not None:
        return instructionsUtils.generateUnexpectedTokenError(line, (", " + arg3) if isinstance(arg3, str) else (', #' + str(arg3)), "End of line")

    if isinstance(arg2, int):
        arg2 = arg2 & 0XFFFFFFFF
        # check 8 bits
        if arg2 > 0xFF:
            return instructionsUtils.generateImmediateOutOfRangeError(line, arg2, 0xFF)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg1)
        if isinstance(arg2, str):
            b = state.getReg(arg2)
        else:
            b = arg2 & 0XFFFFFFFF

        minusB = ((~b) + 1) & 0xFFFFFFFF
        out = a + minusB
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (minusB >> 31) & 1

        v = signA == signB and signB != bit31
        c = bool((out >> 32) & 1)
        n = bool((out >> 31) & 1)
        z = out32 == 0

        # state.setReg(arg1, out32)
        state.setALUState(programState.StatusRegister(n, z, c, v))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeCMN:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the CMN instruction
# This function is called by decodeALUInstruction while decoding the CMN instruction
def decodeCMN(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is not None:
        return instructionsUtils.generateUnexpectedTokenError(line, (", " + arg3) if isinstance(arg3, str) else (', #' + str(arg3)), "End of line")

    if isinstance(arg2, int):
        arg2 = arg2 & 0XFFFFFFFF
        # check 8 bits
        if arg2 > 0xFF:
            return instructionsUtils.generateImmediateOutOfRangeError(line, arg2, 0xFF)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg1)
        if isinstance(arg2, str):
            b = state.getReg(arg2)
        else:
            b = arg2 & 0XFFFFFFFF

        out = a + b
        out32 = out & 0xFFFFFFFF
        bit31 = (out32 >> 31) & 1

        signA = (a >> 31) & 1
        signB = (b >> 31) & 1

        v = signA == signB and signB != bit31
        c = bool((out >> 32) & 1)
        n = bool((out >> 31) & 1)
        z = out32 == 0

        # state.setReg(arg1, out32)
        state.setALUState(programState.StatusRegister(n, z, c, v))

        return state, None
    return nodes.InstructionNode(section, line, run)


# decodeTST:: Node.Section -> int -> String -> Either int String -> Either int String None -> Node
# Decode the TST instruction
# This function is called by decodeALUInstruction while decoding the TST instruction
def decodeTST(section: nodes.Node.Section, line: int, arg1: str, arg2: Union[int, str], arg3: Union[int, str, None]) -> nodes.Node:
    if arg3 is not None:
        return instructionsUtils.generateUnexpectedTokenError(line, (", " + arg3) if isinstance(arg3, str) else (', #' + str(arg3)), "End of line")

    if isinstance(arg2, int):
        arg2 = arg2 & 0XFFFFFFFF
        # check 8 bits
        if arg2 > 0xFF:
            return instructionsUtils.generateImmediateOutOfRangeError(line, arg2, 0xFF)

    def run(state: programState.ProgramState) -> Tuple[programState.ProgramState, Union[programState.RunError, None]]:
        a = state.getReg(arg1)
        if isinstance(arg2, str):
            b = state.getReg(arg2)
        else:
            b = arg2 & 0XFFFFFFFF

        out = a & b

        n = bool((out >> 31) & 1)
        z = out == 0

        # state.setReg(arg1, out)
        state.setALUState(programState.StatusRegister(n, z, False, False))

        return state, None
    return nodes.InstructionNode(section, line, run)