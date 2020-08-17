from typing import List

import nodes
import tokens


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
