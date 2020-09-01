from functools import reduce

import interpreter

fileName = "decompress.asm"
useGUI = True
stackSize = 1024
startLabel = "_start"


if useGUI:
    import visualizer

    visualizer.startLabel = startLabel
    visualizer.stackSize = stackSize

    visualizer.app.MainLoop()
else:
    file = open(fileName, "r")
    lines = file.readlines()

    file_contents: str = reduce(lambda X, Y: X + Y, lines)

    state = interpreter.parse(fileName, file_contents, stackSize, startLabel)
    if state is None:
        exit(-1)
    interpreter.runProgram(state, fileName, lines)
