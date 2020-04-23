import lexer
from high_order import foldR1
import tokens

file = open("program.asm", "r")

file_contents: str = foldR1(lambda X, Y: X+Y, file.readlines())

loadedTokens = lexer.lexFile(file_contents)
loadedTokens = lexer.fixMismatches(loadedTokens, file_contents)

if lexer.printErrors(loadedTokens, "program.asm"):
    exit(-1)

for t in filter(lambda x: not isinstance(x, tokens.Error), loadedTokens):
    print(t)
