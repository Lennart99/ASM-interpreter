import lexer
from high_order import foldR1, foldL

file = open("program.asm", "r")

file_contents: str = foldR1(lambda X, Y: X+Y, file.readlines())
print(file_contents)

matches = list(lexer.token_regex.finditer(file_contents))

tokens = foldL(lexer.match_to_token, [], matches)

for t in tokens:
    print(t)
