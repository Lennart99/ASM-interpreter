import interpreter

import sys
import threading
sys.setrecursionlimit(0x100000)  # note: hex
threading.stack_size(256000000)  # set stack to 256mb

fileName = "looptest.asm"

t = threading.Thread(target=lambda: interpreter.parseAndRun(fileName, 0x40, "_start"))
t.start()
t.join()

# 30.000 iterations need 7 GB
# setup: push, bl, push, mov
# loop:  mov, bl, func, add, b
