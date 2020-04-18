from typing import List


# formatLine:: String -> String
def formatLine(line: str) -> str:
    if len(line) == 0:
        return line

    # TODO ignore string literals
    line = line.replace("\n", "")

    if line.count("//") > 0:
        line = line[0: line.index("//")]

    if line.count(";") > 0:
        line = line[0: line.index(";")]

    line = line.replace("\t", " ")

    # remove multiple spaces in a row
    while line.count("  ") > 0:
        line = line.replace("  ", " ")

    if line.startswith(" "):
        line = line[1: -1]
    if line.endswith(" "):
        line = line[0: -1]

    return line


# removeMultiLineComments:: bool -> [String] -> [String]
def removeMultiLineComments(program: List[str], hasCommentOnPreviousLine: bool = False) -> List[str]:
    if len(program) == 0:
        if hasCommentOnPreviousLine:
            # TODO throw error
            print(f"\033[91m"  # red color
                  f"Syntax error: multi-line comment opened, but not closed (*/ is missing)"
                  f"\033[0m")  # standard color
        return []

    head, *tail = program

    # TODO ignore string literals
    if hasCommentOnPreviousLine:
        if head.count("*/") > 0:
            return removeMultiLineComments([head[head.index("*/")+2:]] + tail, False)
        else:
            return [""] + removeMultiLineComments(tail, True)
    else:
        if head.count("/*") > 0:
            if head.count("*/") > 0:
                return removeMultiLineComments([head[0: head.index("/*")] + head[head.index("*/") + 2:]] + tail, False)
            else:
                return [head[0: head.index("/*")]] + removeMultiLineComments(tail, True)
        else:
            return [head] + removeMultiLineComments(tail, False)


# loadFile:: String -> [String]
# Uses File I/O
def loadFile(program_name: str) -> List[str]:
    file = open(program_name, "r")

    file_contents: List[str] = file.readlines()

    file_contents: List[str] = list(map(formatLine, file_contents))
    file_contents: List[str] = removeMultiLineComments(file_contents)

    return file_contents
