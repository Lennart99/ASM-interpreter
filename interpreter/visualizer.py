import tkinter
from tkinter import END, WORD

from functools import reduce
from typing import List, Callable
import threading
import time
import builtins

import programState
import nodes


# De visualizer kan niet volledig functioneel geschreven worden.
# Daarom hebben we afgesproken dat dit niet volledig functioneel hoeft

# Flags
clockTicked: bool = False
clockSpeed: int = 5
closed = False
memoryCommand: Callable[[programState.ProgramState], programState.ProgramState] = None

# init window
window = tkinter.Tk()
window.title("ARM Cortex M0 assembly simulator")
window.geometry("850x450")
window.resizable(0, 0)


# Event handler to handle the closing of the visualizer window
def on_close():
    global closed
    closed = True
    window.destroy()
    exit()


window.protocol("WM_DELETE_WINDOW", on_close)


# Validates that a string is a number, returns the number or -1 when it is not a number
# validateNumber:: String -> int
def validateNumber(text: str) -> int:
    if len(text) == 0:
        print("\033[31m"
              "Integer should not be empty"
              "\033[0m")
        return -1
    try:
        return int(text, 0)
    except ValueError:
        print(f"\033[31m"
              f"This is not a valid integer: {text}"
              f"\033[0m")
        return -1


# Button actions
# Handles the button to write data to memory
def write():
    global memoryCommand
    if clockSetting.get() == "manual":
        addr = validateNumber(addressEntry.get())
        contents = validateNumber(memContents.get())
        if addr == -1:
            return
        if addr & 3 != 0:
            print("\033[31m"
                  "Error while handling button click: To store data in memory, the address needs to be a multiple of 4"
                  "\033[0m")
            return
        internal_address = addr >> 2

        def execute(state: programState.ProgramState) -> programState.ProgramState:
            print("write", addr)
            # check address is in range
            if internal_address < 0 or internal_address >= len(state.memory):
                print(f"\033[31m"
                      f"Error while handling button click: Memory address out of range: {addr}, must be in range [0...{len(state.memory)*4}]"
                      f"\033[0m")
            else:
                state.memory[internal_address] = nodes.DataNode(contents, "GUI")
            return state
        memoryCommand = execute
    else:
        print("\033[31m"
              "It is not possible to load the contents of an instruction"
              "\033[0m")


# Handles the button to read data from memory
def read():
    global memoryCommand
    if clockSetting.get() == "manual":
        addr = validateNumber(addressEntry.get())
        if addr == -1:
            return
        if addr & 3 != 0:
            print("\033[31m"
                  "Error while handling button click: To read data from memory, the address needs to be a multiple of 4"
                  "\033[0m")
            return
        internal_address = addr >> 2

        def execute(state: programState.ProgramState) -> programState.ProgramState:
            print("read", addr)
            # check address is in range
            if internal_address < 0 or internal_address >= len(state.memory):
                print(f"\033[31m"
                      f"Error while handling button click: Memory address out of range: {addr}, must be in range [0...{len(state.memory) * 4}]"
                      f"\033[0m")
                return state
            word = state.memory[internal_address]
            if isinstance(word, nodes.DataNode):
                memContents.delete(0, END)
                memContents.insert(0, word.value)
            else:
                print("\033[31m"
                      "err"
                      "\033[0m")
            return state
        memoryCommand = execute
    else:
        print("\033[31m"
              "It is only possible to interact with memory in manual mode"
              "\033[0m")


# Handles the button to step to next instruction
def nextStep():
    global clockTicked
    clockTicked = True


# Called when the clock mode is changed
def onClockModeChange():
    global memoryCommand
    if clockSetting.get() == "manual":
        nextButton.configure(state="normal")
        readButton.configure(state="normal")
        writeButton.configure(state="normal")
    else:
        memoryCommand = None
        nextButton.configure(state="disabled")
        readButton.configure(state="disabled")
        writeButton.configure(state="disabled")


# Validate the text is a number and not negative, returns True if the text was a valid number
# this function updates the clocksSpeed automatically
# checkClockSpeed:: String -> bool
def checkClockSpeed(text: str) -> bool:
    global clockSpeed
    if len(text) == 0:
        print("\033[31m"
              "Integer should not be empty"
              "\033[0m")
        return False
    if not text.isdigit():
        print(f"\033[31m"
              f"This is not a valid integer: {text}"
              f"\033[0m")
        return False
    if int(text, 0) == 0:
        print("\033[31m"
              "Integer should not be zero"
              "\033[0m")
        return False
    clockSpeed = int(text, 0)
    return True


# generate the tkinter command
clockCommand = window.register(checkClockSpeed)

# registers
tkinter.Label(window, text="Registers:", fg="#000000", font="none 12").place(x=0, y=0)

tkinter.Label(window, text="Read", fg="#00FF00", font="none 12").place(x=100, y=0)
tkinter.Label(window, text="/", fg="#000000", font="none 12").place(x=150, y=0)
tkinter.Label(window, text="Write", fg="#FF0000", font="none 12").place(x=160, y=0)
tkinter.Label(window, text="/", fg="#000000", font="none 12").place(x=210, y=0)
tkinter.Label(window, text="Both", fg="#0000FF", font="none 12").place(x=220, y=0)

regs = [["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"], ["R8", "R9", "R10", "R11", "R12", "SP", "LR", "PC"]]


class RegisterEntry:
    def __init__(self, name: str, column: int, line: int):
        self.name = name
        tkinter.Label(window, text=name, fg="#000000", font="none 12").place(x=75 * column, y=30 + (60 * line))
        self.entry = tkinter.Text(window, height=1, width=10, bg="#DDDDDD", fg="#000000", font="none 10", state='disabled')
        self.entry.place(x=75 * column, y=60 + (60 * line))
        self.read = False
        self.write = False

    def setValue(self, val: int):
        self.entry.configure(state="normal")
        self.entry.delete(0.0, END)
        self.entry.insert(END, val)
        if self.read:
            self.entry.configure(fg="#0000FF")
        else:
            self.entry.configure(fg="#FF0000")
        self.write = True
        self.entry.configure(state="disabled")

    def processRead(self):
        self.read = True
        if self.write:
            self.entry.configure(fg="#0000FF")
        else:
            self.entry.configure(fg="#00FF00")

    def reset(self):
        self.entry.configure(fg="#000000")
        self.read = False
        self.write = False

    def __str__(self):
        return f"RegisterEntry({self.name})"

    def __repr__(self):
        return self.__str__()


# List with all register entries in the visualizer
reg_items: List[RegisterEntry] = reduce(
    lambda a, b: a+b,
    list(map(
        lambda l: list(map(
            lambda r: RegisterEntry(r[1], r[0], l[0]),
            enumerate(l[1])
        )),
        enumerate(regs)
    ))
)

# Status register
tkinter.Label(window, text="Status register:", fg="#000000", font="none 14").place(x=75 * 8, y=0)

tkinter.Label(window, text="On", fg="#00FF00", font="none 14").place(x=75 * 10, y=0)
tkinter.Label(window, text="/", fg="#000000", font="none 14").place(x=(75 * 10)+30, y=0)
tkinter.Label(window, text="Off", fg="#FF0000", font="none 14").place(x=(75 * 10)+40, y=0)

N = tkinter.Label(window, text="N", fg="#FF0000", font="none 14")
N.place(x=(75 * 9), y=30)
Z = tkinter.Label(window, text="Z", fg="#FF0000", font="none 14")
Z.place(x=(75 * 9)+40, y=30)
C = tkinter.Label(window, text="C", fg="#FF0000", font="none 14")
C.place(x=(75 * 9)+80, y=30)
V = tkinter.Label(window, text="V", fg="#FF0000", font="none 14")
V.place(x=(75 * 9)+120, y=30)

# Clock
tkinter.Label(window, text="Clock:", fg="#000000", font="none 14").place(x=75 * 8, y=60)
nextButton = tkinter.Button(window, text="NEXT", width=5, command=nextStep)
nextButton.place(x=75 * 8, y=90)

# Clock mode switch
clockSettingFrame = tkinter.Frame(window)
clockSetting = tkinter.StringVar(value="manual")
tkinter.Radiobutton(clockSettingFrame, text="manual", variable=clockSetting, indicatoron=False, value="manual", width=8, command=onClockModeChange).pack(side="left")
tkinter.Radiobutton(clockSettingFrame, text="auto", variable=clockSetting, indicatoron=False, value="auto", width=8, command=onClockModeChange).pack(side="left")
clockSettingFrame.place(x=75 * 9, y=90)

# Clock speed setting
tkinter.Label(window, text="Speed: ", fg="#000000", font="none 14").place(x=75 * 8, y=120)
speedEntry = tkinter.Entry(window, width=3, bg="#DDDDDD", font="none 10", validate='focusout', validatecommand=(clockCommand, '%P'))
speedEntry.place(x=75 * 9, y=125)
tkinter.Label(window, text="Instr/sec", fg="#000000", font="none 14").place(x=700, y=120)

# Instructions
tkinter.Label(window, text="Instructions:", fg="#000000", font="none 14").place(x=75 * 8, y=155)

currentLine = tkinter.Label(window, text="Line xxx:", fg="#000000", font="none 10")
currentLine.place(x=75 * 8, y=180)

instr = tkinter.Text(window, width=30, height=1, wrap=WORD, bg="#DDDDDD", state='disabled')
instr.place(x=75 * 8, y=200)

# Memory
tkinter.Label(window, text="Memory:", fg="#000000", font="none 14").place(x=75 * 8, y=240)

tkinter.Label(window, text="Address: ", fg="#000000", font="none 14").place(x=75 * 8, y=270)
addressEntry = tkinter.Entry(window, width=10, bg="#DDDDDD")
addressEntry.place(x=690, y=275)

writeButton = tkinter.Button(window, text="Write", width=5, command=write)
writeButton.place(x=75 * 8, y=300)
readButton = tkinter.Button(window, text="Read", width=5, command=read)
readButton.place(x=75 * 9, y=300)

memContents = tkinter.Entry(window, width=10, bg="#DDDDDD")
memContents.place(x=75 * 8, y=330)

# Console
consoleText = ''
console = tkinter.Text(window, width=70, height=16, wrap=WORD, bg="#2B2B2B", fg="#DDDDDD", state='disabled')
console.place(x=0, y=155)
# save the old print function to print to the console
__old_print = builtins.print


# Overrides the print function to forward all output to the visualizer
# printLine:: [any] -> String -> String -> Stream -> void
def printLine(*args, sep=' ', end='\n', file=None):
    def stripColor(text: str) -> str:
        if "\033[" in text:
            idx = text.index("\033[")
            if "m" in text[idx+2:idx+5]:
                mIdx = text.index("m", idx+2, idx+5)
                return stripColor(text[:idx] + text[mIdx + 1:])
            else:
                return stripColor(text[:idx] + text[idx + 2:])
        else:
            return text

    if end is None:
        end = '\n'

    global consoleText
    __old_print(*args, sep=sep, end=end, file=file)

    if len(args) == 0:
        consoleText += str(end)
    else:
        consoleText += stripColor(reduce(lambda text, add: str(text) + str(sep) + str(add), list(args)) + str(end))

    console.configure(state="normal")
    console.delete(0.0, END)
    console.insert(END, consoleText)
    console.configure(state="disabled")


# function to tick the clock periodically when the clock mode is set to auto
def updateClock():
    global clockTicked
    while True:
        if clockSetting.get() == "auto":
            # It isn't really possible to sleep for less then 2 ms
            if clockSpeed < 500:
                time.sleep(1.0/clockSpeed)
            clockTicked = True


# Configure the speed entry
speedEntry.delete(0, END)
speedEntry.insert(0, 5)

# Test code
if __name__ == "__main__":
    reg_items[0].setValue(1_000_000_000)
    reg_items[0].reset()

    N.configure(fg="#00FF00")

    currentLine.configure(text="Line 1:")

    instr.configure(state="normal")
    instr.delete(0.0, END)
    instr.insert(END, "mov r1, #'A'     // 65")
    instr.configure(state="disabled")

    for i in range(32):
        print("line", i, 'test', sep=';', end='\\')

    window.mainloop()
