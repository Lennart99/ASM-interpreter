from typing import List, Tuple
import re

from high_order import foldL
from invalidInputException import InvalidInputException

# ^[^\d\W] matches a character that is a letter or a underscore at the start of the string
# \w*\Z matches a letter, a number or a underscore at the rest of the string
regex = re.compile(r"^[^\d\W]\w*\Z", re.IGNORECASE)


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


# validateLabel:: String -> int -> String
# validate a label, idx is used to generate a meaningful error message if the label is invalid
def validateLabel(text: str, idx: int) -> str:
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


# validateGlobalLabel:: String -> [String] -> int -> String
# validate a label, idx is used to generate a meaningful error message if the label is invalid
# labelNames is used to make sure the label exists in the loaded file
def validateGlobalLabel(text: str, labelNames: List[str], idx: int) -> str:
    text: str = validateLabel(text, idx)
    if text not in labelNames:
        raise InvalidInputException(f"\033[31m"  # red color
                                    f"File \"$fileName$\", line {idx + 1}\n"
                                    f"\tSyntax error, label not found: '{text}'\n"
                                    f"\tlabel is declared global but does not exist in this file"
                                    f"\033[0m")  # standard color
    return text


# getGlobalLabelsFromString:: [String] -> [int, String] -> [String] -> [String]
def getGlobalLabelsFromString(foldLabels: List[str], programLine: Tuple[int, str], labelNames: List[str]) -> List[str]:
    idx, code = programLine

    if code.startswith(".global"):
        code: str = code.replace(".global", "")
        if len(code.split(",")) >= 1:
            return [validateGlobalLabel(label, labelNames, idx) for label in code.split(",")] + foldLabels

    return foldLabels


# getGlobalLabels:: [String] -> [Label] -> [String]
def getGlobalLabels(program: List[str], labels: List[Label]) -> List[str]:
    programEnum: List[Tuple[int, str]] = list(enumerate(program))
    labelNames: List[str] = list(map(lambda l: l.name, labels))
    return foldL(lambda a, b: getGlobalLabelsFromString(a, b, labelNames), [], programEnum)
