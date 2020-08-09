from typing import Union, Callable, List, Tuple
from functools import reduce

import instructions
import nodes
import tokens
from programContext import ProgramContext


# addNodeToProgramContext:: ProgramContext -> Node _> Node.Section -> ProgramContext
# Adds a node to the ProgramContext in the right section based on the arguments
def addNodeToProgramContext(context: ProgramContext, node: nodes.Node, section: nodes.Node.Section) -> ProgramContext:
    if section == nodes.Node.Section.TEXT:
        context.text += [node]
    elif section == nodes.Node.Section.BSS:
        context.bss += [node]
    elif section == nodes.Node.Section.DATA:
        context.data += [node]
    return context


# getStringTokens:: [Token] -> (Either [StringLiteral] ErrorNode, [Token])
# gets the StringLiteral tokens for the decodeStringLiteral function
def getStringTokens(tokenList: List[tokens.Token]) -> Tuple[Union[List[tokens.StringLiteral], nodes.ErrorNode], List[tokens.Token]]:
    if len(tokenList) == 0:
        return [], []
    string, *tokenList = tokenList
    if isinstance(string, tokens.StringLiteral):
        if len(tokenList) > 0:
            sep, *tokenList = tokenList
            if isinstance(sep, tokens.NewLine):
                return [string], tokenList
            elif isinstance(sep, tokens.Separator) and sep.contents == ',':
                res, tokenList = getStringTokens(tokenList)
                if isinstance(res, nodes.ErrorNode):
                    return res, tokenList
                return [string] + res, tokenList
            else:
                return instructions.generateUnexpectedTokenError(sep.line, sep.contents, "','"), instructions.advanceToNewline(tokenList)
        else:
            return [string], tokenList
    else:
        if isinstance(string, tokens.NewLine):
            return instructions.generateUnexpectedTokenError(string.line, "newline", "a string literal"), instructions.advanceToNewline(tokenList)
        return instructions.generateUnexpectedTokenError(string.line, string.contents, "a string literal"), instructions.advanceToNewline(tokenList)


# bytesToInt:: [int] -> [int]
# Convert a list of bytes into a list of ints with four bytes per int
def bytesToInt(values: List[int]) -> List[int]:
    if len(values) > 3:
        first, second, third, fourth, *values = values
    elif len(values) == 3:
        first, second, third, *values = values
        fourth = 0
    elif len(values) == 2:
        first, second, *values = values
        third, fourth = [0, 0]
    elif len(values) == 1:
        first, *values = values
        second, third, fourth = [0, 0, 0]
    else:  # len(bytes) == 0
        return []

    res = ((first & 0xFF) << 24) | ((second & 0xFF) << 16) | ((third & 0xFF) << 8) | (fourth & 0xFF)
    if len(values) > 0:
        return [res] + bytesToInt(values)
    else:
        return [res]


# decodeStringLiteral:: Token -> [Token] -> Node.Section -> (Node, [Token])
def decodeStringLiteral(directive: tokens.Token, tokenList: List[tokens.Token], section: nodes.Node.Section) -> Tuple[List[nodes.Node], List[tokens.Token]]:
    text = directive.contents.lower()
    addTermination = text in [".asciz", ".string"]

    if len(tokenList) == 0:
        return [instructions.generateToFewTokensError(directive.line, text + " directive")], tokenList

    strings, tokenList = getStringTokens(tokenList)
    if isinstance(strings, nodes.ErrorNode):
        return [strings], tokenList

    # replaces escaped characters line /r, /n and /0
    def replaceEscapedChars(string: str) -> str:
        # All checks are done already, just do the converting here
        string = string.replace('\\b', '\b').replace('\\f', '\f').replace('\\n', '\n').replace('\\r', '\r'). \
            replace('\\t', '\t').replace('\\"', '\"').replace('\\\\', '\\').replace('\\0', '\0')
        return string

    if addTermination:
        # Add 0 after each string
        lists = list(map(lambda s: list(map(lambda c: ord(c), replaceEscapedChars(s.contents[1:-1] + "\\0"))), strings))
    else:
        lists = list(map(lambda s: list(map(lambda c: ord(c), replaceEscapedChars(s.contents[1:-1]))), strings))

    lst = reduce(lambda a, b: a + b, lists)
    lst = bytesToInt(lst)
    dataNodes = list(map(lambda x: nodes.DataNode(x, "CODE", section, directive.line), lst))

    return dataNodes, tokenList


# decodeGlobal:: [Token] -> ([String], [Token])
def decodeGlobal(tokenList: List[tokens.Token]) -> Tuple[Union[List[str], nodes.ErrorNode], List[tokens.Token]]:
    if len(tokenList) == 0:
        return [], []
    label, *tokenList = tokenList
    if isinstance(label, tokens.Instruction) or isinstance(label, tokens.Register) or isinstance(label, tokens.Label):
        if len(tokenList) > 0:
            sep, *tokenList = tokenList
            if isinstance(sep, tokens.NewLine):
                return [label.contents], tokenList
            elif isinstance(sep, tokens.Separator) and sep.contents == ',':
                res, tokenList = decodeGlobal(tokenList)
                if isinstance(res, nodes.ErrorNode):
                    return res, tokenList
                return [label.contents] + res, tokenList
            else:
                return instructions.generateUnexpectedTokenError(sep.line, sep.contents, "','"), instructions.advanceToNewline(tokenList)
        else:
            return [label.contents], tokenList
    else:
        if isinstance(label, tokens.NewLine):
            return instructions.generateUnexpectedTokenError(label.line, "newline", "a label"), instructions.advanceToNewline(tokenList)
        return instructions.generateUnexpectedTokenError(label.line, label.contents, "a label"), instructions.advanceToNewline(tokenList)


# parse:: [Token] -> ProgramContext -> Node.Section -> ProgramContext
def parse(tokenList: List[tokens.Token]) -> ProgramContext:
    context = ProgramContext([], [], [], [], [])
    section: nodes.Node.Section = nodes.Node.Section.TEXT

    while len(tokenList) > 0:
        head, *tokenList = tokenList

        if isinstance(head, tokens.Instruction):
            # It is a label
            if len(tokenList) == 0:
                err = instructions.generateToFewTokensError(head.line, head.contents)
                context = addNodeToProgramContext(context, err, section)
            sep: tokens.Token = tokenList[0]
            if isinstance(sep, tokens.Separator) and sep.contents == ":":
                tokenList = tokenList[1:]
                # Get the address where the label should point to
                if section == nodes.Node.Section.TEXT:
                    nextAddress = len(context.text)
                elif section == nodes.Node.Section.BSS:
                    nextAddress = len(context.text)
                elif section == nodes.Node.Section.DATA:
                    nextAddress = len(context.text)
                else:
                    # never happens
                    nextAddress = -1
                # Generate a new label dict
                label = nodes.Label(head.contents, section, nextAddress)
                context.labels += [label]
                # Generate new context and call parse() with remaining tokens
                # continue
                # return parse(tokenList, context, section)
            else:
                # check that section is not BSS
                if section == nodes.Node.Section.BSS:
                    err = nodes.ErrorNode(f"\033[31m"  # red color
                                          f"File \"$fileName$\", line {head.line}\n"
                                          f"\tSyntax error: Instructions should not be placed in BSS"
                                          f"\033[0m\n")
                    tokenList = instructions.advanceToNewline(tokenList)
                    context = addNodeToProgramContext(context, err, section)
                    continue
                    # return parse(instructions.advanceToNewline(tokenList), addNodeToProgramContext(context, err, section), section)
                # It is an actual instruction
                opCode: str = head.contents.upper().strip()
                if opCode in instructions.tokenFunctions.keys():
                    func: Callable[[List[tokens.Token], nodes.Node.Section], Tuple[nodes.Node, List[tokens.Token]]] = instructions.tokenFunctions[opCode]
                    if func is not None:
                        node, tokenList = func(tokenList, section)
                        context = addNodeToProgramContext(context, node, section)
                        continue
                        # return parse(tokenList, addNodeToProgramContext(context, node, section), section)
                # Instruction not implemented
                err = nodes.ErrorNode(f"\033[31m"  # red color
                                      f"File \"$fileName$\", line {head.line}\n"
                                      f"\tSyntax error: Unsupported instruction: '{head.contents}'"
                                      f"\033[0m\n")
                tokenList = instructions.advanceToNewline(tokenList)
                context = addNodeToProgramContext(context, err, section)
                # return parse(instructions.advanceToNewline(tokenList), addNodeToProgramContext(context, err, section), section)
        elif isinstance(head, tokens.Label) or isinstance(head, tokens.Register):
            if len(tokenList) == 0:
                err = instructions.generateUnexpectedTokenError(head.line, "End of File", "':'")
                context = addNodeToProgramContext(context, err, section)
                continue
            sep, *tokenList = tokenList
            if isinstance(sep, tokens.Separator) and sep.contents == ":":
                # Get the address where the label should point to
                if section == nodes.Node.Section.TEXT:
                    nextAddress = len(context.text)
                elif section == nodes.Node.Section.BSS:
                    nextAddress = len(context.bss)
                elif section == nodes.Node.Section.DATA:
                    nextAddress = len(context.data)
                else:
                    # never happens
                    nextAddress = -1

                # Generate a new label dict
                label = nodes.Label(head.contents, section, nextAddress)
                context.labels += [label]
                # Generate new context and call parse() with remaining tokens
                # return parse(tokenList, context, section)
            else:
                err = instructions.generateUnexpectedTokenError(head.line, sep.contents, "':'")
                addNodeToProgramContext(context, err, section)
                # return parse(tokenList, addNodeToProgramContext(context, err, section), section)
        elif isinstance(head, tokens.Section):
            if head.contents == ".text":
                section = nodes.Node.Section.TEXT
                # return parse(tokenList, context, nodes.Node.Section.TEXT)
            elif head.contents == ".bss":
                section = nodes.Node.Section.BSS
                # return parse(tokenList, context, nodes.Node.Section.BSS)
            elif head.contents == ".data":
                section = nodes.Node.Section.DATA
                # return parse(tokenList, context, nodes.Node.Section.DATA)
            else:
                # never happens because of the regular expressions
                pass
        elif isinstance(head, tokens.AsciiAsciz):
            dataNodes, tokenList = decodeStringLiteral(head, tokenList, section)
            if section == nodes.Node.Section.TEXT:
                context.text += dataNodes
                # context = ProgramContext(context.text + dataNodes, context.bss.copy(), context.data.copy(), context.labels.copy(), context.globalLabels.copy())
            elif section == nodes.Node.Section.BSS:
                context.bss += dataNodes
                # context = ProgramContext(context.text.copy(), context.bss + dataNodes, context.data.copy(), context.labels.copy(), context.globalLabels.copy())
            elif section == nodes.Node.Section.DATA:
                context.data += dataNodes
                # context = ProgramContext(context.text.copy(), context.bss.copy(), context.data + dataNodes, context.labels.copy(), context.globalLabels.copy())
            # return parse(tokenList, context, section)
        elif isinstance(head, tokens.Global):
            globalLabels, tokenList = decodeGlobal(tokenList)
            if isinstance(globalLabels, nodes.ErrorNode):
                tokenList = instructions.advanceToNewline(tokenList)
                context = addNodeToProgramContext(context, globalLabels, section)
                # return parse(instructions.advanceToNewline(tokenList), addNodeToProgramContext(context, globalLabels, section), section)
                continue
            context.globalLabels += globalLabels
            # return parse(tokenList, context, section)
        elif isinstance(head, tokens.ErrorToken) or isinstance(head, tokens.NewLine):
            # skip
            pass
            # return parse(tokenList, context, section)
        elif isinstance(head, tokens.Align) or isinstance(head, tokens.Cpu):
            # skip
            pass
            # return parse(instructions.advanceToNewline(tokenList), context, section)
        elif isinstance(head, tokens.Skip):
            number = head.contents[6:]
            n_skip = int(number) >> 2
            if n_skip > 0:
                dataNodes = [nodes.DataNode(0, "CODE", section, head.line) for _ in range(n_skip)]
                if section == nodes.Node.Section.TEXT:
                    context.text += dataNodes
                elif section == nodes.Node.Section.BSS:
                    context.bss += dataNodes
                elif section == nodes.Node.Section.DATA:
                    context.data += dataNodes

            tokenList = instructions.advanceToNewline(tokenList)
            # return parse(instructions.advanceToNewline(tokenList), context, section)
        else:
            # error
            err = instructions.generateUnexpectedTokenError(head.line, head.contents, "End of line")
            context = addNodeToProgramContext(context, err, section)
            # return parse(tokenList, addNodeToProgramContext(context, err, section), section)
    return context


# printAndReturn:: Token -> String -> ErrorType
# Prints the error and returns the error type
def printAndReturn(node: nodes.Node, fileName: str) -> int:
    if isinstance(node, nodes.ErrorNode):
        print(node.message.replace("$fileName$", fileName))
        return 1
    return 0


# printErrors:: [Token] -> String -> boolean
# Print all errors and returns True when the program should exit
def printErrors(context: ProgramContext, fileName: str) -> bool:

    errCount = sum(list(map(lambda a: printAndReturn(a, fileName), context.text)))
    errCount += sum(list(map(lambda a: printAndReturn(a, fileName), context.bss)))
    errCount += sum(list(map(lambda a: printAndReturn(a, fileName), context.data)))

    return errCount > 0
