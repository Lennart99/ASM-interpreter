from typing import Union, Any, Match, Callable, List, Dict, Iterator, Tuple

import tokens
import instructions
import nodes


class ProgramContext:
    def __init__(self, text: List[nodes.Node], bss: List[nodes.Node], data: List[nodes.Node],
                 labels: Dict[str, nodes.Label]):
        self.text: List[nodes.Node] = text
        self.bss:  List[nodes.Node] = bss
        self.data: List[nodes.Node] = data
        self.labels: Dict[str, nodes.Label] = labels

    def __str__(self) -> str:
        return ".text: {} \n.bss: {} \n.data: {} \nLabels: {}". \
            format(self.text, self.bss, self.data, self.labels)

    def __repr__(self) -> str:
        return self.__str__()


def addNodeToProgramContext(context: ProgramContext, node: nodes.Node, section: nodes.Node.Section) -> ProgramContext:
    if section == nodes.Node.Section.TEXT:
        return ProgramContext(context.text + [node], context.bss.copy(), context.data.copy(), context.labels.copy())
    elif section == nodes.Node.Section.BSS:
        return ProgramContext(context.text.copy(), context.bss + [node], context.data.copy(), context.labels.copy())
    elif section == nodes.Node.Section.DATA:
        return ProgramContext(context.text.copy(), context.bss.copy(), context.data + [node], context.labels.copy())


# NOTE make sure to not have any ErrorTokens in the iterator
def parse(tokenList: List[tokens.Token], context: ProgramContext = ProgramContext([], [], [], {}),
          section: nodes.Node.Section = nodes.Node.Section.TEXT) -> ProgramContext:
    if len(tokenList) == 0:
        return context
    head, *tokenList = tokenList

    if isinstance(head, tokens.Instruction):
        # It is a label
        if len(tokenList) == 0:
            err = instructions.generateUnexpectedTokenError(head.line, "End of File", "additional tokens")
            return addNodeToProgramContext(context, err, section)
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
            labels = context.labels.copy()
            labels.update({label.name: label})
            # Generate new context and call parse() with remaining tokens
            return parse(tokenList,
                         ProgramContext(context.text.copy(), context.bss.copy(), context.data.copy(), labels),
                         section)
        else:
            # It is an actual instruction
            opCode: str = head.contents.upper()
            func: Callable[[List[tokens.Token], nodes.Node.Section], Tuple[nodes.Node, List[tokens.Token]]] = \
                instructions.tokenFunctions[opCode]
            if func is not None:
                node, tokenList = func(tokenList, section)
                return parse(tokenList, addNodeToProgramContext(context, node, section), section)
            else:
                # TODO error - not implemented
                pass
    elif isinstance(head, tokens.Label) or isinstance(head, tokens.Register):
        if len(tokenList) == 0:
            err = instructions.generateUnexpectedTokenError(head.line, "End of File", "':'")
            return addNodeToProgramContext(context, err, section)
        sep, *tokenList = tokenList
        if isinstance(sep, tokens.Separator) and sep.contents == ":":
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
            labels = context.labels.copy()
            labels.update({label.name: label})
            # Generate new context and call parse() with remaining tokens
            return parse(tokenList,
                         ProgramContext(context.text.copy(), context.bss.copy(), context.data.copy(), labels),
                         section)
        else:
            err = instructions.generateUnexpectedTokenError(head.line, "End of File", "':'")
            return addNodeToProgramContext(context, err, section)
    elif isinstance(head, tokens.Section):
        if head.contents == ".text":
            return parse(tokenList, context, nodes.Node.Section.TEXT)
        elif head.contents == ".bss":
            return parse(tokenList, context, nodes.Node.Section.BSS)
        elif head.contents == ".data":
            return parse(tokenList, context, nodes.Node.Section.DATA)
        else:
            # never happens because of the regular expressions
            pass
    return parse(tokenList, context, section)
    # elif isinstance(head, tokens.Comment) or isinstance(head, tokens.ErrorToken):
    #     # skip
    #     return parse(tokenList)
    # else:
    #     # error
    #     pass
