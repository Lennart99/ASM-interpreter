from typing import Dict, Callable


class Token:
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        self.contents = contents
        self.line = line
        self.column_start = column_start
        self.column_end = column_end
        self.is_mismatch = False
        self.n_newLine = 0

    def __str__(self) -> str:
        return "{}('{}', {}, {}, {})".\
            format(type(self).__name__, self.contents.replace('\\', '\\\\').replace('\n', '\\n'),
                   self.line, self.column_start, self.column_end)

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
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        super().__init__(contents.replace(" ", "").replace("\t", ""), line, column_start, column_end)


# Note: can contain whitespaces between '=' and the value
class LoadImmediateValue(Token):
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        super().__init__(contents.replace(" ", "").replace("\t", ""), line, column_start, column_end)


# Note: can contain whitespaces between '#' and the value
class ImmediateValue(Token):
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        super().__init__(contents.replace(" ", "").replace("\t", ""), line, column_start, column_end)


class Align(Token):
    pass


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
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        super().__init__(contents, line, column_start, column_end)
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {} newlines, {}, {}, {})".\
            format(type(self).__name__, self.contents.replace('\\', '\\\\').replace('\n', '\\n'), self.n_newLine,
                   self.line, self.column_start, self.column_end)


class StringLiteral(Token):
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        super().__init__(contents, line, column_start, column_end)
        # count newlines
        self.n_newLine = contents.count('\n')

    def __str__(self) -> str:
        return "{}('{}', {} newlines, {}, {}, {})".\
            format(type(self).__name__, self.contents.replace('\\', '\\\\').replace('\n', '\\n'), self.n_newLine,
                   self.line, self.column_start, self.column_end)


class NewLine(Token):
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        super().__init__(contents, line, column_start, column_end)
        self.n_newLine = 1


class Mismatch(Token):
    def __init__(self, contents: str, line: int, column_start: int, column_end: int):
        super().__init__(contents, line, column_start, column_end)
        self.is_mismatch = True


tokenConstructors: Dict[str, Callable[[str, int, int, int], Token]] = {
    "INSTRUCTION": Instruction,
    "REGISTER": Register,
    "LD_LABEL": LoadLabel,
    "LABEL": Label,
    "IMMED_VALUE": ImmediateValue,
    "LD_IMMED_VALUE": LoadImmediateValue,
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
