import tkinter
from tkinter import END, WORD

from typing import List, Tuple
import threading, time

from high_order import foldR1
import programState
import programStateProxy


# De visualizer kan niet volledig functioneel geschreven worden.
# Daarom hebben we afgesproken dat dit niet volledig functioneel hoeft

# Flags
clockTicked: bool = False
clockSpeed: int = 5
closed = False

# init window
window = tkinter.Tk()
window.title("ARM Cortex M0 assembly simulator")
window.geometry("850x450")
window.resizable(0, 0)


def on_close():
    global closed
    closed = True
    window.destroy()


window.protocol("WM_DELETE_WINDOW", on_close)


# Button actions
# Write mem
def write():
    p: programState.ProgramState = None
    if clockSetting.get() == "manual":
        # TODO implement
        cont = memContents.get()
        print("'" + cont + "'")
    else:
        print("It is only possible to interact with memory in manual mode")


# Read mem
def read():
    if clockSetting.get() == "manual":
        # TODO implement
        memContents.delete(0, END)
        memContents.insert(0, 100)
    else:
        print("It is only possible to interact with memory in manual mode")


# Step to next instruction
def nextStep():
    global clockTicked
    clockTicked = True


def onClockModeChange():
    if clockSetting.get() == "manual":
        nextButton.configure(state="normal")
        readButton.configure(state="normal")
        writeButton.configure(state="normal")
    else:
        nextButton.configure(state="disabled")
        readButton.configure(state="disabled")
        writeButton.configure(state="disabled")


def checkClockSpeed(text: str) -> bool:
    global clockSpeed
    if len(text) == 0:
        print("Integer should not be empty")
        return False
    if not text.isdigit():
        print("This is not a valid integer:", text)
        return False
    if int(text, 0) == 0:
        print("Integer should not be zero")
        return False
    clockSpeed = int(text, 0)
    return True


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
        tkinter.Label(window, text=name, fg="#000000", font="none 12").place(x=75 * column, y=30 + (60 * line))
        self.entry = tkinter.Text(window, height=1, width=10, bg="#DDDDDD", fg="#000000", font="none 10", state='disabled')
        self.entry.place(x=75 * column, y=60 + (60 * line))
        self.read = False
        self.write = False

    def setValue(self, val: int):
        if closed:
            exit()
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
        if closed:
            exit()
        self.read = True
        if self.write:
            self.entry.configure(fg="#0000FF")
        else:
            self.entry.configure(fg="#00FF00")

    def reset(self):
        if closed:
            exit()
        self.entry.configure(fg="#000000")
        self.read = False
        self.write = False


reg_items: List[RegisterEntry] = foldR1(
    lambda a, b: a+b,
    list(map(
        lambda l: list(map(
            lambda r: RegisterEntry(r[1], r[0], l[0]),
            enumerate(l[1])
        )),
        enumerate(regs)
    ))
)

# Status reg
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

# CLOCK
tkinter.Label(window, text="Clock:", fg="#000000", font="none 14").place(x=75 * 8, y=60)
nextButton = tkinter.Button(window, text="NEXT", width=5, command=nextStep)
nextButton.place(x=75 * 8, y=90)

# switch
clockSettingFrame = tkinter.Frame(window)
clockSetting = tkinter.StringVar(value="manual")
tkinter.Radiobutton(clockSettingFrame, text="manual", variable=clockSetting, indicatoron=False, value="manual", width=8, command=onClockModeChange).pack(side="left")
tkinter.Radiobutton(clockSettingFrame, text="auto", variable=clockSetting, indicatoron=False, value="auto", width=8, command=onClockModeChange).pack(side="left")
clockSettingFrame.place(x=75 * 9, y=90)

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
addr = tkinter.Entry(window, width=10, bg="#DDDDDD")
addr.place(x=690, y=275)

writeButton = tkinter.Button(window, text="Write", width=5, command=write)
writeButton.place(x=75 * 8, y=300)
readButton = tkinter.Button(window, text="Read", width=5, command=read)
readButton.place(x=75 * 9, y=300)

memContents = tkinter.Entry(window, width=10, bg="#DDDDDD")
memContents.place(x=75 * 8, y=330)


def resetRegs():
    if closed:
        exit()
    global reg_items

    def reset(reg: RegisterEntry):
        reg.reset()
        return reg
    # for i in range(len(reg_items)):
    #     reg = reg_items[i]
    #     reg.reset()
    #     reg_items[i] = reg
    reg_items = list(map(reset, reg_items))


def initRegs(registers: List[int]):
    if closed:
        exit()
    global reg_items

    def init(e: Tuple[int, RegisterEntry]):
        idx, reg = e
        reg.setValue(registers[idx])
        reg.reset()
        return reg
    # for i in range(len(reg_items)):
    #     reg = reg_items[i]
    #     reg.reset()
    #     reg_items[i] = reg
    reg_items = list(map(init, enumerate(reg_items)))


def setLine(line: int, text: str):
    currentLine.configure(text=f"Line {line}:")
    instr.configure(state="normal")
    instr.delete(0.0, END)
    instr.insert(END, text)
    instr.configure(state="disabled")


def setLineInternalFunction(text: str):
    currentLine.configure(text=f"Internal function:")
    instr.configure(state="normal")
    instr.delete(0.0, END)
    instr.insert(END, text)
    instr.configure(state="disabled")


def setStatusRegs(n: bool, z: bool, c: bool, v: bool):
    if n:
        N.configure(fg="#00FF00")
    else:
        N.configure(fg="#FF0000")

    if z:
        Z.configure(fg="#00FF00")
    else:
        Z.configure(fg="#FF0000")

    if c:
        C.configure(fg="#00FF00")
    else:
        C.configure(fg="#FF0000")

    if v:
        V.configure(fg="#00FF00")
    else:
        V.configure(fg="#FF0000")


def updateClock():
    global clockTicked
    # window.after(1000//clockSpeed, updateClock)
    while not closed:
        time.sleep(1.0/clockSpeed)
        if closed:
            break
        if clockSetting.get() == "auto":
            clockTicked = True


clockThread = threading.Thread(target=updateClock)
clockThread.start()

# configure
speedEntry.delete(0, END)
speedEntry.insert(0, 5)

if __name__ == "__main__":
    reg_items[0].setValue(1_000_000_000)
    reg_items[0].reset()

    N.configure(fg="#00FF00")

    currentLine.configure(text="Line 1:")

    instr.configure(state="normal")
    instr.delete(0.0, END)
    instr.insert(END, "mov r1, #'A'     // 65")
    instr.configure(state="disabled")

    window.mainloop()
