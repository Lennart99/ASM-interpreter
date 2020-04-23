from typing import Dict, Callable, Union
from enum import Enum


class Token:
    def __init__(self, contents: str, idx: int, line: int, column_start: int, column_end: int):
        self.contents = contents
        self.start_index = idx
        self.line = line
        self.column_start = column_start
        self.column_end = column_end
        self.is_mismatch = False
        self.n_newLine = 0

    def __str__(self) -> str:
        return "{}('{}', {}, {}, {}, {})".\
            format(type(self).__name__, self.contents,
                   self.line, self.column_start, self.column_end, self.start_index)

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
    def __init__(self, contents: str, idx: int, line: int, column_start: int, column_end: int):
        super().__init__(contents.replace(" ", "").replace("\t", ""), idx, line, column_start, column_end)
        self.label: str = self.contents[1:]

    def __str__(self) -> str:
        return "{}('{}', {}, {}, {})".\
            format(type(self).__name__, self.label,
                   self.line, self.column_start, self.column_end)


class LoadImmediateValue(Token):
    def __init__(self, value: Union[str, int], contents: str, idx: int, line: int, column_start: int, column_end: int):
        super().__init__(contents, idx, line, column_start, column_end)
        self.value: Union[str, int] = value
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {}, {}, {})".\
            format(type(self).__name__, self.value,
                   self.line, self.column_start, self.column_end)


class ImmediateValue(Token):
    def __init__(self, value: Union[str, int], contents: str, idx: int, line: int, column_start: int, column_end: int):
        super().__init__(contents, idx, line, column_start, column_end)
        self.value: Union[str, int] = value
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {}, {}, {})".\
            format(type(self).__name__, self.value,
                   self.line, self.column_start, self.column_end)


class Align(Token):
    def __init__(self, contents: str, idx: int, line: int, column_start: int, column_end: int):
        # Remove whitespace
        super().__init__(".align " + contents[-1], idx, line, column_start, column_end)


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
    def __init__(self, contents: str, idx: int, line: int, column_start: int, column_end: int):
        super().__init__(contents, idx, line, column_start, column_end)
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {} newlines, {}, {}, {})".\
            format(type(self).__name__, self.contents.replace('\n', '\\n'), self.n_newLine,
                   self.line, self.column_start, self.column_end)


class StringLiteral(Token):
    def __init__(self, contents: str, idx: int, line: int, column_start: int, column_end: int):
        super().__init__(contents, idx, line, column_start, column_end)
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {} newlines, {}, {}, {})".\
            format(type(self).__name__, self.contents.replace('\n', '\\n'), self.n_newLine,
                   self.line, self.column_start, self.column_end)


class NewLine(Token):
    def __init__(self, contents: str, idx: int, line: int, column_start: int, column_end: int):
        super().__init__(contents, idx, line, column_start, column_end)
        self.n_newLine = 1


class Mismatch(Token):
    def __init__(self, contents: str, idx: int, line: int, column_start: int, column_end: int):
        super().__init__(contents, idx, line, column_start, column_end)
        self.is_mismatch = True


# This type can be added to the tokens to indicate a error has occurred
# The error can be printed later on
class Error(Token):
    class ErrorType(Enum):
        NoError = 0
        Warning = 1
        Error = 2

    def __init__(self, message: str, type: ErrorType):
        self.message = message

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
                     f"\tSyntax error: no value after '#' or '='"
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
def createImmediateValue(contents: str, idx: int, line: int, column_start: int, column_end: int) -> Union[Token, None]:
    # because of the regex we know for sure the text starts with #
    if "'" in contents:
        if contents.count("'") < 2:
            return Error(f"\033[31m"  # red color
                         f"File \"$fileName$\", line {line}\n"
                         f"\tSyntax error: immediate character declaration was not closed (\"'\" missing)"
                         f"\033[0m", Error.ErrorType.Error)
        else:
            value = getCharValue(contents[1:], line)
            return ImmediateValue(value, contents, idx, line, column_start, column_end)
    else:
        value: int = getIntValue(contents[1:], line)
        return ImmediateValue(value, contents, idx, line, column_start, column_end)


# createLoadImmediateValue:: str -> int -> int -> int -> int -> int -> Token|None
def createLoadImmediateValue(contents: str, idx: int, line: int, column_start: int, column_end: int) -> \
        Union[Token, None]:
    # because of the regex we know for sure the text starts with =
    if "'" in contents:
        if contents.count("'") < 2:
            return Error(f"\033[31m"  # red color
                         f"File \"$fileName$\", line {line}\n"
                         f"\tSyntax error: immediate character declaration was not closed (\"'\" missing)"
                         f"\033[0m", Error.ErrorType.Error)
        else:
            value = getCharValue(contents[1:], line)
            return ImmediateValue(value, contents, idx, line, column_start, column_end)
    else:
        value: int = getIntValue(contents[1:], line)
        return ImmediateValue(value, contents, idx, line, column_start, column_end)


# TODO fix missing ' in immed value
tokenConstructors: Dict[str, Callable[[str, int, int, int, int], Token]] = {
    "INSTRUCTION": Instruction,
    "REGISTER": Register,
    "LD_LABEL": LoadLabel,
    "LABEL": Label,
    "IMMED_VALUE": createImmediateValue,
    "LD_IMMED_VALUE": createLoadImmediateValue,
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
