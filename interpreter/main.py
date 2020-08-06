import interpreter
import visualizer

import threading

fileName = "decompress.asm"
useGUI = True
stackSize = 1024
startLabel = "_start"

t = threading.Thread(target=lambda: interpreter.parseAndRun(fileName, stackSize, startLabel, useGUI))
t.setDaemon(True)
t.start()

if useGUI:
    visualizer.window.mainloop()

t.join()
