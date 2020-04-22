from typing import List, Union, Any, Match, Callable
import re

import tokens
from high_order import foldL

INSTRUCTIONS = ["MOV", "LDR", "LDRH", "LDRB", "STR", "STRRH", "STRB", "LDRSH", "LDRSB",
                "PUSH", "POP", "LDM", "LDMIA", "STMIA",
                "ADD", "ADC", "SUB", "SBC", "MUL",
                "AND", "EOR", "ORR", "BIC", "MOVN",
                "LSL", "LSR", "ASR", "ROR",
                "SXTH", "SXTB", "UXTH", "UXTB",
                "TST", "CMP", "CMN",
                "REV", "REV16", "REVSH",
                "B", "BX", "BL", "BLX",
                "BCC", "BCS", "BEQ", "BGE", "BGT", "BHI", "BLE", "BLS", "BLT", "BMI", "BNE", "BPL", "BVC", "BVS"]

R_INSTRUCTION = r"(?P<INSTRUCTION>" + \
                foldL(lambda text, instr: text + "|(" + instr+")", "(" + INSTRUCTIONS[0] + ")", INSTRUCTIONS[1:]) + \
                ")|"

# ^[^\d\W] matches a character that is a letter or a underscore at the start of the string
# \w*\Z matches a letter, a number or a underscore at the rest of the string
# https://stackoverflow.com/questions/5474008/regular-expression-to-confirm-whether-a-string-is-a-valid-identifier-in-python
R_LABEL = r"[^\d\W]\w*"

TOKEN_REGEX = re.compile(R_INSTRUCTION +
                         r"(?P<REGISTER>(SP)|(LR)|(PC)|(r1[0-2])|(r[0-9]))|"
                         r"(?P<LD_LABEL>=[ \t]*(" + R_LABEL + "))|"
                         r"(?P<LABEL>" + R_LABEL + ")|"
                         r"(?P<IMMED_VALUE>(#[ \t]*0x[0-9a-f]*)|(#[ \t]*0b[01]*)|(#[ \t]*'[^\n]')|(#[ \t]*[0-9]*))|"
                         r"(?P<LD_IMMED_VALUE>(=[ \t]*0x[0-9a-f]*)|(=[ \t]*0b[01]*)|(=[ \t]*'[^\n]')|(=[ \t]*[0-9]*))|"
                         r"(?P<ALIGN>\.align[ \t]*[1248])|"
                         r"(?P<ASCII_ASCIZ>(\.ascii)|(\.asciz))|"
                         r"(?P<SECTION>(\.text)|(\.bss)|(\.data))|"
                         r"(?P<CPU>\.cpu[^\n]*)|"
                         r"(?P<GLOBAL>\.global)|"
                         r"(?P<SEPARATOR>[,:\[\]{}])|"
                         r"(?P<SINGELINECOMMENT>(;[^\n]*)|(//[^\n]*))|"
                         r"(?P<MULTILINECOMMENT>/\*.*?\*/)|"
                         r"(?P<STRINGLITERAL>\".*?\")|"
                         r"(?P<IGNORE>[ \t])|"
                         r"(?P<NEWLINE>\n)|"
                         r"(?P<MISMATCH>.)", re.DOTALL+re.ASCII+re.IGNORECASE)


# lastIndex:: String -> String -> int
# Get the index to the last occurrence of search in string
def lastIndex(string: str, search: str) -> int:
    if len(string) < len(search):
        return -1
    if string[len(string)-len(search):] == search:
        return len(string)-len(search)
    else:
        return lastIndex(string[:-1], search)


# match_to_token:: Match -> [(String, String, int, int)] -> [(String, String, int, int)]
def match_to_token(lijst: List[tokens.Token], match: Match[Union[str, Any]], file_contents: str) -> List[tokens.Token]:
    kind = match.lastgroup
    value = match.group()
    if kind == 'IGNORE':
        return lijst
    else:
        func: Callable[[str, int, int, int], tokens.Token] = tokens.tokenConstructors[kind]
        if func is None:
            return lijst
        processed = file_contents[:match.start()]
        line = processed.count('\n')+1
        if line > 1:
            lastNewLine = lastIndex(processed, '\n')
        else:
            lastNewLine = 0
        token = func(value, line, match.start()-lastNewLine, match.end()-lastNewLine)
        return [token] + lijst


def getTokens(file_contents: str) -> List[tokens.Token]:
    matches = list(TOKEN_REGEX.finditer(file_contents))
    tokenList = foldL(lambda a, b: match_to_token(a, b, file_contents), [], matches)
    return tokenList
