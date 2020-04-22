import lexer
from high_order import foldR1

file = open("program.asm", "r")

file_contents: str = foldR1(lambda X, Y: X+Y, file.readlines())
print(file_contents)

loadedTokens = lexer.getTokens(file_contents)

for t in loadedTokens:
    print(t)
