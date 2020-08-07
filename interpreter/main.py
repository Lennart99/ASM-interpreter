from functools import reduce

import interpreter

fileName = "decompress.asm"
useGUI = False
stackSize = 1024
startLabel = "_start"


if useGUI:
    import visualizer

    visualizer.app.MainLoop()
else:
    file = open(fileName, "r")
    lines = file.readlines()

    file_contents: str = reduce(lambda X, Y: X + Y, lines)

    state = interpreter.parse(fileName, file_contents, stackSize, startLabel)
    interpreter.runProgram(state, fileName, file_contents, lambda _: False)
