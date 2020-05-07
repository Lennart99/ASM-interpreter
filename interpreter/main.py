import interpreter
import visualizer

import sys
import threading
sys.setrecursionlimit(0x100000)  # note: hex
threading.stack_size(256000000)  # set stack to 256mb

fileName = "program.asm"

t = threading.Thread(target=lambda: interpreter.parseAndRun(fileName, 0x400, "_start", True))
t.setDaemon(True)
t.start()

visualizer.window.mainloop()

t.join()

# 30.000 iterations need 7 GB
# setup: push, bl, push, mov
# loop:  mov, bl, func, add, b
