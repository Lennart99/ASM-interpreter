from typing import List, Tuple
import re

from high_order import foldL
from invalidInputException import InvalidInputException

# ^[^\d\W] matches a character that is a letter or a underscore at the start of the string
# \w*\Z matches a letter, a number or a underscore at the rest of the string
regex = re.compile(r"^[^\d\W]\w*\Z", re.IGNORECASE)


def validateLabel(text: str, idx: int):
    if text.startswith(" "):
        text = text[1:]
    if text.endswith(" "):
        text = text[0: -1]

    if regex.fullmatch(text) is None:
        raise InvalidInputException(f"\033[31m"  # red color
                                    f"File \"$fileName$\", line {idx + 1}\n"
                                    f"\tSyntax error, invalid label: '{text}'\n"
                                    f"\tA label should only contain alphanumerical characters and underscores "
                                    f"and should not start with a number"
                                    f"\033[0m")  # standard color
    return text


# getGlobalLabelsFromString:: [String] -> [int, String] -> [String]
def getGlobalLabelsFromString(foldLabels: List[str], programLine: Tuple[int, str]) -> List[str]:
    idx, code = programLine

    if code.startswith(".global"):
        code: str = code.replace(".global", "")
        if len(code.split(",")) >= 1:
            return [validateLabel(label, idx) for label in code.split(",")] + foldLabels

    return foldLabels


# getGlobalLabels:: [String] -> [String]
def getGlobalLabels(program: List[str]) -> List[str]:
    programEnum: List[Tuple[int, str]] = list(enumerate(program))
    return foldL(getGlobalLabelsFromString, [], programEnum)


class Label:
    def __init__(self, name: str, line: int):
        # name of the label
        self.name: str = name
        # The index to the line where the interpreter needs to start
        self.line: int = line

    def __str__(self):
        return f"Label{{{self.name}, {self.line}}}"

    def __repr__(self):
        return self.__str__()


# getLabelFromstring:: [Label] -> [int, String] -> [label]
def getLabelsFromstring(foldLabels: List[Label], programLine: Tuple[int, str]) -> List[Label]:
    idx, code = programLine

    splitCode: List[str] = code.split(":")

    if len(splitCode) > 1:
        if len(splitCode[-1]) > 0:
            # data on same line as label
            return [Label(validateLabel(label, idx), idx) for label in splitCode[:-1]] + foldLabels
        else:
            return [Label(validateLabel(label, idx), idx + 1) for label in splitCode[:-1]] + foldLabels
    else:
        return foldLabels


# getLabels:: [String] -> [label]
def getLabels(program: List[str]) -> List[Label]:
    programEnum: List[Tuple[int, str]] = list(enumerate(program))
    return foldL(getLabelsFromstring, [], programEnum)
