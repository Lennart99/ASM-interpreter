from typing import Dict, Callable, Union
from enum import Enum


class Token:
    def __init__(self, contents: str, idx: int, line: int):
        self.contents = contents
        self.start_index = idx
        self.line = line
        # Makes it possible to detect a mismatch
        self.is_mismatch = False
        # makes it possible to count the newlines easily
        self.n_newLine = 0

    def __str__(self) -> str:
        return "{}('{}')".\
            format(type(self).__name__, self.contents)

    def __repr__(self) -> str:
        return self.__str__()


class Instruction(Token):
    pass


class Register(Token):
    pass


class Label(Token):
    pass


# Note: can contain whitespaces between '=' and the label
class LoadLabel(Token):
    def __init__(self, contents: str, idx: int, line: int):
        super().__init__(contents.replace(" ", "").replace("\t", ""), idx, line)
        self.label: str = self.contents[1:]

    def __str__(self) -> str:
        return "{}('{}')".\
            format(type(self).__name__, self.label)


class LoadImmediateValue(Token):
    def __init__(self, value: Union[str, int], contents: str, idx: int, line: int):
        super().__init__(contents, idx, line)
        self.value: Union[str, int] = value
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}')".\
            format(type(self).__name__, self.value)


class ImmediateValue(Token):
    def __init__(self, value: Union[str, int], contents: str, idx: int, line: int):
        super().__init__(contents, idx, line)
        self.value: Union[str, int] = value
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}')".\
            format(type(self).__name__, self.value)


class Align(Token):
    def __init__(self, contents: str, idx: int, line: int):
        # Remove whitespace
        super().__init__(".align " + contents[-1], idx, line)


class AsciiAsciz(Token):
    pass


class Section(Token):
    pass


class Cpu(Token):
    pass


class Global(Token):
    pass


class Separator(Token):
    pass


class Comment(Token):
    def __init__(self, contents: str, idx: int, line: int):
        super().__init__(contents, idx, line)
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {} newlines)".\
            format(type(self).__name__, self.contents.replace('\n', '\\n'), self.n_newLine)


class StringLiteral(Token):
    def __init__(self, contents: str, idx: int, line: int):
        super().__init__(contents, idx, line)
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {} newlines)".\
            format(type(self).__name__, self.contents.replace('\n', '\\n'), self.n_newLine)


class NewLine(Token):
    def __init__(self, contents: str, idx: int, line: int):
        super().__init__(contents, idx, line)
        self.n_newLine = 1

    def __str__(self) -> str:
        return "{}('{}')".\
            format(type(self).__name__, "\\n")


class Mismatch(Token):
    def __init__(self, contents: str, idx: int, line: int):
        super().__init__(contents, idx, line)
        self.is_mismatch = True


# This type can be added to the tokens to indicate a error has occurred
# The error can be printed later on
class Error(Token):
    class ErrorType(Enum):
        NoError = 0
        Warning = 1
        Error = 2

    def __init__(self, message: str, errorType: ErrorType):
        super().__init__("ERROR", -1, -1)
        self.message = message
        self.errorType = errorType

    def __str__(self) -> str:
        return self.message


# getIntValue:: str -> int -> int|Error
def getIntValue(text: str, line: int) -> Union[int, Error]:
    if len(text) == 0:
        return Error(f"\033[31m"  # red color
                     f"File \"$fileName$\", line {line}\n"
                     f"\tSyntax error: no value after '#' or '='"
                     f"\033[0m", Error.ErrorType.Error)
    if text[0] in " \t":
        return getIntValue(text[1:], line)
    elif text[-1] in " \t":
        return getIntValue(text[:-1], line)
    else:
        # make python guess the notation based on the prefix
        return int(text, 0)


# getCharValue:: str -> int -> str|Error
def getCharValue(text: str, line: int) -> Union[str, Error]:
    if len(text) == 0:
        return Error(f"\033[31m"  # red color
                     f"File \"$fileName$\", line {line}\n"
                     f"\tSyntax error: No value after '#' or '='"
                     f"\033[0m", Error.ErrorType.Error)
    if text[0] in " \t":
        return getCharValue(text[1:], line)
    elif text[-1] in " \t":
        return getCharValue(text[:-1], line)
    else:
        text = text[1:-1]
        if len(text) > 2:
            return Error(f"\033[31m"  # red color
                         f"File \"$fileName$\", line {line}\n"
                         f"\tSyntax error: More then one character in the quotes '{text}'"
                         f"\033[0m", Error.ErrorType.Error)
        elif len(text) == 2 and text[0] != '\\':
            return Error(f"\033[31m"  # red color
                         f"File \"$fileName$\", line {line}\n"
                         f"\tSyntax error: More then one character in the quotes '{text}'"
                         f"\033[0m", Error.ErrorType.Error)
        # get the char
        return text.replace('\\n', '\n').replace('\\t', '\t')


# createImmediateValue:: str -> int -> int -> int -> int -> int -> Token|None
def createImmediateValue(constr: Callable[[Union[str, int], str, int, int], Token],
                         contents: str, idx: int, line: int) -> Token:
    # because of the regex we know for sure the text starts with #
    if "'" in contents:
        if contents.count("'") < 2:
            return Error(f"\033[31m"  # red color
                         f"File \"$fileName$\", line {line}\n"
                         f"\tSyntax error: Immediate character declaration was not closed (\"'\" missing)"
                         f"\033[0m", Error.ErrorType.Error)
        else:
            value = getCharValue(contents[1:], line)
            if isinstance(value, Error):
                return value
            return constr(value, contents, idx, line)
    else:
        value: int = getIntValue(contents[1:], line)
        if isinstance(value, Error):
            return value
        return constr(value, contents, idx, line)


# functions to create the different tokens
tokenConstructors: Dict[str, Callable[[str, int, int], Token]] = {
    "INSTRUCTION": Instruction,
    "REGISTER": Register,
    "LD_LABEL": LoadLabel,
    "LABEL": Label,
    "IMMED_VALUE": lambda a, b, c: createImmediateValue(ImmediateValue, a, b, c),
    "LD_IMMED_VALUE": lambda a, b, c: createImmediateValue(LoadImmediateValue, a, b, c),
    "ALIGN": Align,
    "ASCII_ASCIZ": AsciiAsciz,
    "SECTION": Section,
    "CPU": Cpu,
    "GLOBAL": Global,
    "SEPARATOR": Separator,
    "SINGELINECOMMENT": Comment,
    "MULTILINECOMMENT": Comment,
    "STRINGLITERAL": StringLiteral,
    "IGNORE": None,
    "NEWLINE": NewLine,
    "MISMATCH": Mismatch,
}
