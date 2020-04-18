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
        self.line: str = line

    def __str__(self):
        return f"Label{{{self.name}, {self.line}}}"

    def __repr__(self):
        return self.__str__()


# getLabelFromstring:: [Label] -> [int, String] -> [label]
def getLabelFromstring(foldLabels: List[Label], programLine: Tuple[int, str]) -> List[Label]:
    idx, code = programLine

    if code.count(":") > 0:
        if code.count(":") > 1:
            # TODO throw error
            print(f"\033[91m"  # red color
                  f"Syntax error: A colon (:) is not supported in an assembly statement"
                  f"\033[0m")  # standard color
        label: str = code[0:programLine[1].index(":")]
        if label.count(" ") > 0:
            # TODO throw error
            print(f"\033[91m"  # red color
                  f"Syntax error: A label should not contain whitespaces"
                  f"\033[0m")  # standard color
            return foldLabels
        if len(code[code.index(":") + 1:]) > 0:
            result = Label(label, idx)
        else:
            result = Label(label, idx + 1)

        return [result] + foldLabels
    else:
        return foldLabels


# getLabels:: [[int, String]] -> [label]
def getLabels(program: List[Tuple[int, str]]) -> List[Label]:
    return foldL(getLabelFromstring, [], program)
