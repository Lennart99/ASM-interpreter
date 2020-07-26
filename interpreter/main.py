import interpreter
import visualizer

import sys
import threading
sys.setrecursionlimit(0x100000)  # note: hex
threading.stack_size(256000000)  # set stack to 256mb

fileName = "decompress.asm"
useGUI = True
stackSize = 1024
startLabel = "_start"

t = threading.Thread(target=lambda: interpreter.parseAndRun(fileName, stackSize, startLabel, useGUI))
t.setDaemon(True)
t.start()

if useGUI:
    clockThread = threading.Thread(target=visualizer.updateClock)
    clockThread.setDaemon(True)
    clockThread.start()

    visualizer.window.mainloop()

t.join()

# 30.000 iterations need 7 GB
# setup: push, bl, push, mov
# loop:  mov, bl, func, add, b
