from typing import Tuple, List, Union, Any, Match
import re

from high_order import foldR1, foldL

instructions = ["MOV", "LDR", "LDRH", "LDRB", "STR", "STRRH", "STRB", "LDRSH", "LDRSB",
                "PUSH", "POP", "LDM", "LDMIA", "STMIA",
                "ADD", "ADC", "SUB", "SBC", "MUL",
                "AND", "EOR", "ORR", "BIC", "MOVN",
                "LSL", "LSR", "ASR", "ROR",
                "SXTH", "SXTB", "UXTH", "UXTB",
                "TST", "CMP", "CMN",
                "REV", "REV16", "REVSH",
                "B", "BX", "BL", "BLX",
                "BCC", "BCS", "BEQ", "BGE", "BGT", "BHI", "BLE", "BLS", "BLT", "BMI", "BNE", "BPL", "BVC", "BVS"]

r_instruction = r"(?P<INSTRUCTION>" + \
                foldL(lambda text, instr: text + "|(" + instr+")", "(" + instructions[0] + ")", instructions[1:]) + \
                ")|"

# ^[^\d\W] matches a character that is a letter or a underscore at the start of the string
# \w*\Z matches a letter, a number or a underscore at the rest of the string
r_label = r"[^\d\W]\w*"

token_regex = re.compile(r_instruction +
                         r"(?P<REGISTER>(SP)|(LR)|(PC)|(r1[0-2])|(r[0-9]))|"
                         r"(?P<LD_LABEL>=(" + r_label + "))|"
                         r"(?P<LABEL>" + r_label + ")|"
                         r"(?P<IMMED_VALUE>(#0x[0-9a-f]*)|(#0b[01]*)|(#'[^\n]{1}')|(#[0-9]*))|"
                         r"(?P<LD_IMMED_VALUE>(=0x[0-9a-f]*)|(=0b[01]*)|(=[0-9]*))|"
                         r"(?P<ALIGN>\.align[ \t]*[1248])|"
                         r"(?P<ASCII>(\.ascii)|(\.asciz))|"
                         r"(?P<SECTION>(\.text)|(\.bss)|(\.data))|"
                         r"(?P<CPU>\.cpu[^\n]*)|"
                         r"(?P<GLOBAL>\.global)|"
                         r"(?P<SEPERATOR>,)|"
                         r"(?P<COLON>:)|"
                         r"(?P<BLOCKOPEN>\[)|"
                         r"(?P<BLOCKCLOSE>])|"
                         r"(?P<CURLYOPEN>{)|"
                         r"(?P<CURLYCLOSE>})|"
                         r"(?P<SINGELINECOMMENT>(;[^\n]*)|(//[^\n]*))|"
                         r"(?P<MULTILINECOMMENT>/\*.*?\*/)|"
                         r"(?P<STRINGLITERAL>\".*?\")|"
                         r"(?P<IGNORE>[ \t])|"
                         r"(?P<NEWLINE>\n)|"
                         r"(?P<MISMATCH>.)", re.DOTALL+re.ASCII+re.IGNORECASE)


# match_to_token:: Match -> [(String, String, int, int)] -> [(String, String, int, int)]
def match_to_token(lijst: List[Tuple[str, str, int, int]], match: Match[Union[str, Any]]) -> List[Tuple[str, str, int, int]]:
    kind = match.lastgroup
    value = match.group()
    # if kind == 'MISMATCH':
    #     print(f'{value!r} unexpected on char {match.start()}')
    #     return lijst
    if kind == 'IGNORE':
        return lijst
    else:
        token = (kind, value, match.start(), match.end())
        return [token] + lijst
