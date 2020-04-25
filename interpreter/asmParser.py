from typing import Union, Any, Match, Callable, List, Dict, Iterator, Tuple

import tokens
import instructions
import nodes


# NOTE make sure to not have any ErrorTokens in the iterator
def parse(tokenList: List[tokens.Token], snakeNodes: List[nodes.Node] = []) -> List[nodes.Node]:
    if len(tokenList) == 0:
        return snakeNodes
    head, *tokenList = tokenList

    if len(snakeNodes) == 0:
        section: nodes.Node.Section = nodes.Node.Section.TEXT
    else:
        section: nodes.Node.Section = snakeNodes[-1].section

    if isinstance(head, tokens.Instruction):
        opCode: str = head.contents.upper()
        func: Callable[[List[tokens.Token], nodes.Node.Section], Tuple[nodes.Node, List[tokens.Token]]] = \
            instructions.tokenFunctions[opCode]
        if func is not None:
            # TODO return remaining tokens from func
            node, tokenList = func(tokenList, section)
            return parse(tokenList, snakeNodes + [node])
        else:
            # TODO error - not implemented
            pass
    return parse(tokenList, snakeNodes)
    # elif isinstance(head, tokens.Label):
    #     pass
    # elif isinstance(head, tokens.Section):
    #     pass
    # elif isinstance(head, tokens.Comment) or isinstance(head, tokens.ErrorToken):
    #     # skip
    #     return parse(tokenList)
    # else:
    #     # error
    #     pass
