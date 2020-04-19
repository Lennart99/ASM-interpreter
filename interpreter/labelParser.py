from typing import List, Tuple
from high_order import foldL


# getLabelFromstring:: [String] -> String -> [String]
def getGlobalLabelFromString(foldLabels: List[str], programLine: str) -> List[str]:
    if programLine.startswith(".global"):
        programLine: str = programLine.replace(".global", "").replace(" ", "")
        if len(programLine.split(",")) >= 1:
            result = programLine.split(",")
            return result + foldLabels

    return foldLabels


# getGlobalLabels:: [String] -> [String]
def getGlobalLabels(program: List[str]) -> List[str]:
    return foldL(getGlobalLabelFromString, [], program)


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
        for label in splitCode[:-1]:
            if label.count(" ") > 0:
                # TODO throw error
                fileName = "filename"
                print(f"\033[91m"  # red color
                      f"File \"{fileName}\", line {idx+1}\n"
                      f"\tSyntax error: A label should not contain whitespaces"
                      f"\033[0m")  # standard color
        if len(splitCode[-1]) > 0:
            # data on same line as label
            return [Label(label, idx) for label in splitCode[:-1]] + foldLabels
        else:
            return [Label(label, idx + 1) for label in splitCode[:-1]] + foldLabels
    else:
        return foldLabels


# getLabels:: [String] -> [label]
def getLabels(program: List[str]) -> List[Label]:
    programEnum: List[Tuple[int, str]] = list(enumerate(program))
    return foldL(getLabelsFromstring, [], programEnum)
