from typing import List, Tuple, Dict

from high_order import zipWith, foldL
from invalidInputException import InvalidInputException


# formatLine:: String -> String
def formatLine(line: str) -> str:
    if len(line) == 0:
        return line

    # Remove newlines
    line: str = line.replace("\n", "")

    # Remove single-line comments
    if "//" in line:
        line: str = line[0: line.index("//")]
    if ";" in line:
        line: str = line[0: line.index(";")]

    # Replace tabs with spaces
    line: str = line.replace("\t", " ")

    # Remove multiple spaces in a row
    def func(x): return func(x.replace("  ", " ")) if "  " in x else x
    line: str = func(line)

    # Remove spaces at start and end
    if line.startswith(" "):
        line: str = line[1: -1]
    if line.endswith(" "):
        line: str = line[0: -1]

    return line


# removeMultiLineComments:: bool -> [String] -> [String]
def removeMultiLineComments(program: List[str], hasCommentOnPreviousLine: bool = False) -> List[str]:
    if len(program) == 0:
        if hasCommentOnPreviousLine:
            raise InvalidInputException(f"\033[31m"  # red color
                                        f"File \"$fileName$\"\n"
                                        f"\tSyntax error: Multi-line comment opened, but not closed (*/ is missing)"
                                        f"\033[0m")  # standard color
        return []

    head, *tail = program

    if hasCommentOnPreviousLine:
        # The previous line ended with a multi line comment
        if "*/" in head:
            # */ detected, remove everything until */ (inclusive)
            return removeMultiLineComments([head[head.index("*/")+2:]] + tail, False)
        else:
            # No */ detected, remove whole line, but keep a empty string to keep track of the line numbers
            return [""] + removeMultiLineComments(tail, True)
    else:
        if "/*" in head:
            # /* detected, multi line comment started
            if "*/" in head:
                # */ detected, remove everything from /* until */ (inclusive)
                return removeMultiLineComments([head[0: head.index("/*")] + head[head.index("*/") + 2:]] + tail, False)
            else:
                # No */ detected, remove everything from /* (inclusive)
                return [head[0: head.index("/*")]] + removeMultiLineComments(tail, True)
        else:
            # No comment, do nothing
            return [head] + removeMultiLineComments(tail, False)


# removeStringLiterals:: bool -> [String] -> ([String], [String]))
def removeStringLiterals(program: List[str], hasQuoteOnPreviousLine: bool = False) -> Tuple[List[str], List[str]]:
    # TODO permit multiple strings on same line
    if len(program) == 0:
        return [], []

    head, *tail = program

    if hasQuoteOnPreviousLine:
        # The previous line ended with a string literal
        if '"' in head:
            # Detected second quote replace everything before " (inclusive)
            prog, strings = removeStringLiterals(tail, False)

            literal: str = head[:head.index('"')+1]
            head: str = "$str$" + head[head.index('"')+1:]
            return [head] + prog, [literal] + strings
        else:
            # No second quote detected, replace the whole line
            if len(tail) == 0:
                print(f"\033[31m"  # red color
                      f"Syntax warning: Unterminated string at end of file, '\"' inserted"
                      f"\033[0m")  # standard color
                return ["$str$"], [head + '"']
            else:
                prog, strings = removeStringLiterals(tail, True)

                return ["$str$"] + prog, [head] + strings
    else:
        if '"' in head:
            # Quote detected, string literal started
            if head.count('"') > 1:
                # Detected second quote replace everything between quotes (inclusive)
                prog, strings = removeStringLiterals(tail, False)

                start = head.index('"')
                end = head.index('"', start+1)

                literal: str = head[start:end + 1]
                head: str = head[:start] + "$str$" + head[end + 1:]
                return [head] + prog, [literal] + strings
            else:
                # No second quote detected, replace everything after " (inclusive)
                literal: str = head[head.index('"'):]
                head: str = head[:head.index('"')] + "$str$"

                if len(tail) == 0:
                    print(f"\033[31m"  # red color
                          f"Syntax warning: Unterminated string at end of file, '\"' inserted"
                          f"\033[0m")  # standard color
                    return [head], [literal + '"']
                else:
                    prog, strings = removeStringLiterals(tail, True)

                    return [head] + prog, [literal] + strings
        else:
            # No string literal, do nothing
            prog, strings = removeStringLiterals(tail, False)
            return [head] + prog, [""] + strings


# removeStringLiterals:: [String] -> [String] -> [String]
def replaceStringLiterals(program: List[str], literals: List[str]) -> List[str]:
    return zipWith(lambda prog, lit: prog.replace("$str$", lit), program, literals)


class LoadedFile:
    def __init__(self, name: str, contents: List[str], globalLabels: Dict[str, int], labels: Dict[str, int]):
        # The name of the label
        self.fileName: str = name
        # The contents of the file
        self.contents: List[str] = contents
        # The global labels
        self.globalLabels: Dict[str, int] = globalLabels
        # The labels with the indices where the first instruction can be found
        self.labels: Dict[str, int] = labels

    def __str__(self):
        return (f"LoadedFile {{\n" 
                f"\tfileName: {self.fileName},\n" 
                f"\tcontents: {self.contents},\n" 
                f"\tglobalLabels: {self.globalLabels},\n" 
                f"\tlabels: {self.labels}\n}}")

    def __repr__(self):
        return self.__str__()


# loadFile:: String -> [String]
# Uses File I/O
def loadFile(fileName: str) -> LoadedFile:
    file = open(fileName, "r")

    file_contents: List[str] = file.readlines()

    try:
        # Remove string literals to prevent to change the string literals
        file_contents, strings = removeStringLiterals(file_contents)
        # Remove comments and whitespaces
        file_contents: List[str] = removeMultiLineComments(file_contents)
        file_contents: List[str] = list(map(formatLine, file_contents))
        # Put the string literals back
        file_contents: List[str] = replaceStringLiterals(file_contents, strings)

        # Create a LoadedFile object
        loadedFile = LoadedFile(fileName, file_contents, None, None)
        return loadedFile
    except InvalidInputException as e:
        print(e.msg.replace("$fileName$", "program.asm"))
        exit(-1)
