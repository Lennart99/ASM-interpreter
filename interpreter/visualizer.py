import wx
import wx.stc as stc

from typing import Union, List, Optional

import builtins
import os
import threading
import time
import random

import programState
import interpreter

MARK_BREAKPOINT = 1
breakpoints = []

MARK_CURRENT_LINE = 2

# Font face data depending on OS
if wx.Platform == '__WXMSW__':
    defaultFont = 'Arial'
    # other = 'Comic Sans MS'
    textSize = 10
    lineNumberSize = 8
elif wx.Platform == '__WXMAC__':
    defaultFont = 'Arial'
    # other = 'Comic Sans MS'
    textSize = 12
    lineNumberSize = 10
else:
    defaultFont = 'Helvetica'
    # other = 'new century schoolbook'
    textSize = 12
    lineNumberSize = 10


class RegisterEntry:
    def __init__(self, parent: wx.Panel, name: str, y: int):
        # The height of the label is 16 and the height of the text box is 22, this means the labels must be offset by 3 pixels to be centered
        self.regLabel = wx.StaticText(parent, -1, name, pos=(10, y + 3))
        self.regLabel.SetBackgroundColour("#FFFFFF")
        self.regBox = wx.TextCtrl(parent, -1, "", pos=(35, y), size=(80, 22))
        self.regBox.SetEditable(False)

    def setValue(self, value: Union[int, bool]):
        self.regBox.SetEditable(True)
        self.regBox.SetValue(str(value))
        self.regBox.SetEditable(False)


class Icons:
    def __init__(self):
        self.new = wx.Bitmap(os.path.join("icons", "new.png"))
        self.open = wx.Bitmap(os.path.join("icons", "open.png"))
        self.save = wx.Bitmap(os.path.join("icons", "save.png"))
        self.saveAs = wx.Bitmap(os.path.join("icons", "save_as.png"))

        self.debug = wx.Bitmap(os.path.join("icons", "debug.png"))
        self.quit = wx.Bitmap(os.path.join("icons", "quit.png"))
        self.resume = wx.Bitmap(os.path.join("icons", "resume.png"))
        self.resumeToBreakpoint = wx.Bitmap(os.path.join("icons", "resume_to_breakpoint.png"))
        self.run = wx.Bitmap(os.path.join("icons", "run.png"))
        self.singleStep = wx.Bitmap(os.path.join("icons", "single_step.png"))
        self.stop = wx.Bitmap(os.path.join("icons", "stop.png"))


class TextPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("#FFFFFF")

        self.textBox = stc.StyledTextCtrl(self, style=wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_READONLY)
        # self.textBox.SetEditable(False)

        # Bind Ctrl + '=', Ctrl + '+' and Ctrl + '-' to zooming in and out or making the text bigger/smaller
        self.textBox.CmdKeyAssign(ord('='), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)  # Ctrl + = to zoom in
        self.textBox.CmdKeyAssign(ord('+'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)  # Ctrl + + to zoom in
        self.textBox.CmdKeyAssign(ord('-'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)  # Ctrl + - to zoom out

        # TODO Set up the ASM keywords for syntax highlighting
        # self.control.SetLexer(stc.STC_LEX_ASM)
        # self.control.SetKeyWords(0, " ".join(keyword.kwlist))

        # Set margins
        self.textBox.SetMargins(5, 0)  # 5px margin on left inside of text control

        self.textBox.SetMarginType(1, stc.STC_MARGIN_SYMBOL)
        self.textBox.SetMarginMask(1, 2)  # Could not find how masks work in WX, but this works with MARK_BREAKPOINT = 1
        self.textBox.SetMarginSensitive(1, True)
        self.textBox.SetMarginWidth(1, 25)

        self.textBox.SetMarginType(2, stc.STC_MARGIN_NUMBER)  # line numbers column
        self.textBox.SetMarginWidth(2, 25)  # width of line numbers column
        self.textBox.SetMarginSensitive(2, True)

        # Set foldSymbols style based off the instance variable self.foldSymbols
        # Like a flattened tree control using circular headers and curved joins
        self.textBox.MarkerDefine(MARK_BREAKPOINT, stc.STC_MARK_CIRCLE, "red", "red")
        self.textBox.MarkerDefine(MARK_CURRENT_LINE, stc.STC_MARK_CIRCLE, "#888888", "#888888")

        # Event handler for margin click
        self.textBox.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)

        # setting the style
        self.textBox.StyleSetSpec(stc.STC_STYLE_DEFAULT, f"face:{defaultFont},size:{textSize}")
        self.textBox.StyleSetSpec(stc.STC_STYLE_LINENUMBER, f"back:#C0C0C0,face:{defaultFont},size:{lineNumberSize}")
        self.textBox.StyleClearAll()  # reset all to be like default

        sizer = wx.GridSizer(rows=1, cols=1, vgap=0, hgap=0)
        sizer.Add(self.textBox, 0, wx.EXPAND)
        self.SetSizer(sizer)

        # TODO get and update current line
        # currentLine = 100
        # self.textBox.MarkerAdd(currentLine, MARK_CURRENT_LINE)
        # self.textBox.GotoLine(currentLine)

    # Handles when the margin is clicked (folding)
    def OnMarginClick(self, e):
        # enable and disable breakpoint as needed
        lineClicked = self.textBox.LineFromPosition(e.GetPosition())  # line 1 = 0
        if self.textBox.MarkerGet(lineClicked):
            if lineClicked in breakpoints:
                breakpoints.remove(lineClicked)
            self.textBox.MarkerDelete(lineClicked, MARK_BREAKPOINT)
        else:
            if lineClicked not in breakpoints:
                breakpoints.append(lineClicked)
            self.textBox.MarkerAdd(lineClicked, MARK_BREAKPOINT)
        print(breakpoints)


class ConsolePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("#FFFFFF")

        self.textBox = stc.StyledTextCtrl(self, style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
        self.textBox.SetEditable(False)

        # setting the style
        self.textBox.StyleSetSpec(stc.STC_STYLE_DEFAULT, f"fore:#FFFFFF,back:#000000,face:{defaultFont},size:{textSize}")
        self.textBox.SetSelBackground(True, "#333333")
        self.textBox.StyleClearAll()  # reset all to be like default
        self.textBox.SetCaretForeground("#FFFFFF")

        sizer = wx.GridSizer(rows=1, cols=1, vgap=0, hgap=0)
        sizer.Add(self.textBox, 0, wx.EXPAND)
        self.SetSizer(sizer)

    def append(self, line: str):
        self.textBox.SetEditable(True)
        self.textBox.SetValue(self.textBox.GetValue() + line)
        self.textBox.ScrollToEnd()
        self.textBox.SetEditable(False)

    def clear(self):
        self.textBox.SetEditable(True)
        self.textBox.SetValue("")
        self.textBox.SetEditable(False)


class RightPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("#FFFFFF")

        horSplitter = wx.SplitterWindow(self)
        self.textPanel = TextPanel(horSplitter)
        self.console = ConsolePanel(horSplitter)
        horSplitter.SplitHorizontally(self.textPanel, self.console)
        horSplitter.SetMinimumPaneSize(500)

        sizer = wx.GridSizer(rows=1, cols=1, vgap=0, hgap=0)
        sizer.Add(horSplitter, 0, wx.EXPAND)
        self.SetSizer(sizer)


class SidePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("#FFFFFF")

        # TODO add regs
        regLabel = wx.StaticText(self, -1, "Registers:", pos=(10, 10))
        regs = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "SP", "LR", "PC"]
        self.regEntries = [RegisterEntry(self, reg, 30+30*idx) for idx, reg in enumerate(regs)]

        statusRegLabel = wx.StaticText(self, -1, "Status Registers:", pos=(10, 530))
        self.statusRegEntries = [RegisterEntry(self, reg, 550+30*idx) for idx, reg in enumerate(["N", "Z", "C", "V"])]

        for reg in self.statusRegEntries:
            reg.setValue(random.randint(0, 1) == 1)

        for reg in self.regEntries:
            reg.setValue(random.randint(0, 9999999999))

    # Initialize the registers in the visualizer with there actual values
    def setRegs(self, registers: List[int]):
        for register, value in zip(self.regEntries, registers):
            register.setValue(value)

    # Set the colors of the statusRegister section of the visualizer to the actual contents of the statusRegister
    # setStatusRegs:: bool -> bool -> bool -> bool -> void
    def setStatusRegs(self, status: programState.StatusRegister):
        # ["N", "Z", "C", "V"]
        self.statusRegEntries[0].setValue(status.N)
        self.statusRegEntries[1].setValue(status.Z)
        self.statusRegEntries[2].setValue(status.C)
        self.statusRegEntries[3].setValue(status.V)

    def update(self, state: programState.ProgramState):
        self.setRegs(state.registers)
        self.setStatusRegs(state.status)


# Application Framework
class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        # Initialize the application Frame and create the Styled Text Control
        wx.Frame.__init__(self, parent, title=title, size=(1200, 800))

        vertSplitter = wx.SplitterWindow(self)
        self.sidePanel = SidePanel(vertSplitter)
        right = RightPanel(vertSplitter)
        vertSplitter.SplitVertically(self.sidePanel, right)
        vertSplitter.SetMinimumPaneSize(150)

        self.textPanel = right.textPanel
        self.console = right.console

        self.dirName = ''
        self.fileName = ''

        # Toolbar
        self.icons = Icons()
        toolbar: wx.ToolBar = self.CreateToolBar()
        toolbar.SetBackgroundColour('DARKGRAY')

        # tool bindings
        newTool = toolbar.AddTool(wx.ID_ANY, "New",  self.icons.new, "Create empty application")
        self.Bind(wx.EVT_TOOL, self.OnNew, newTool)
        openTool = toolbar.AddTool(wx.ID_ANY, "Open", self.icons.open, "Open file")
        self.Bind(wx.EVT_TOOL, self.OnOpen, openTool)
        saveTool = toolbar.AddTool(wx.ID_ANY, "Save",  self.icons.save, "Save file")
        self.Bind(wx.EVT_TOOL, self.OnSave, saveTool)
        saveAsTool = toolbar.AddTool(wx.ID_ANY, "Save As", self.icons.saveAs, "Save file as")
        self.Bind(wx.EVT_TOOL, self.OnSaveAs, saveAsTool)

        toolbar.AddSeparator()

        self.runTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Run", self.icons.run, "Run the program")
        self.Bind(wx.EVT_TOOL, self.OnRun, self.runTool)
        self.debugTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Debug",  self.icons.debug, "Debug the program")
        self.Bind(wx.EVT_TOOL, lambda _: print("debug"), self.debugTool)
        self.stopTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Stop",  self.icons.stop, "Stop the program")
        self.Bind(wx.EVT_TOOL, self.OnStop, self.stopTool)
        self.singleStepTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Single-step",  self.icons.singleStep, "Single-step the program")
        self.Bind(wx.EVT_TOOL, lambda _: print("single-step"), self.singleStepTool)
        self.resumeBreakpointTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Resume-to-breakpoint", self.icons.resumeToBreakpoint, "Resume to the next breakpoint")
        self.Bind(wx.EVT_TOOL, lambda _: print("resume to next breakpoint"), self.resumeBreakpointTool)
        self.resumeTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Resume",  self.icons.resume, "Run the rest of the program")
        self.Bind(wx.EVT_TOOL, lambda _: print("Run rest of program"), self.resumeTool)

        self.stopTool.Enable(False)
        self.singleStepTool.Enable(False)
        self.resumeBreakpointTool.Enable(False)
        self.resumeTool.Enable(False)

        toolbar.AddSeparator()

        quitTool = toolbar.AddTool(wx.ID_ANY, "Quit", self.icons.quit, "Quit")
        self.Bind(wx.EVT_TOOL, lambda _: self.Close(), quitTool)
        toolbar.Realize()

        self.runThread: Optional[threading.Thread] = None
        self.stopFlag = False

        # go ahead and display the application
        self.Show()

    # New document menu action
    def OnNew(self, e):
        # Empty the instance variable for current filename, and the main text box's content
        self.fileName = ""
        self.textPanel.textBox.SetValue("")
        self.console.clear()

    # Open existing document menu action
    def OnOpen(self, e):
        # First try opening the existing file; if it fails, the file doesn't exist most likely
        try:
            dlg = wx.FileDialog(self, "Choose a file to open", self.dirName, "", "*.*", wx.FD_OPEN)
            if dlg.ShowModal() == wx.ID_OK:
                self.fileName = dlg.GetFilename()
                self.dirName = dlg.GetDirectory()
                f = open(os.path.join(self.dirName, self.fileName), 'r')
                self.textPanel.textBox.SetValue(f.read())
                self.console.clear()
                f.close()
            dlg.Destroy()
        except:
            dlg = wx.MessageDialog(self, " Couldn't open file", "Error 009", wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

    # Save the document menu action
    def OnSave(self, e):
        # First try just saving the existing file, but if that file doesn't
        # exist it will fail, and the except will launch the Save As.
        try:
            f = open(os.path.join(self.dirName, self.fileName), 'w')
            f.write(self.textPanel.textBox.GetValue())
            f.close()
        except:
            try:
                # If regular save fails, try the Save As method.
                dlg = wx.FileDialog(self, "Save file", self.dirName, "Untitled", "*.*", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
                if dlg.ShowModal() == wx.ID_OK:
                    self.fileName = dlg.GetFilename()
                    self.dirName = dlg.GetDirectory()
                    f = open(os.path.join(self.dirName, self.fileName), 'w')
                    f.write(self.textPanel.textBox.GetValue())
                    f.close()
                dlg.Destroy()
            except:
                dlg = wx.MessageDialog(self, " Couldn't save file", "Error 009", wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()

    # Save a new document menu action
    def OnSaveAs(self, e):
        try:
            dlg = wx.FileDialog(self, "Save file as", self.dirName, self.fileName, "*.*", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                self.fileName = dlg.GetFilename()
                self.dirName = dlg.GetDirectory()
                f = open(os.path.join(self.dirName, self.fileName), 'w')
                f.write(self.textPanel.textBox.GetValue())
                f.close()
            dlg.Destroy()
        except:
            dlg = wx.MessageDialog(self, " Couldn't save file", "Error 009", wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

    def OnRun(self, e):
        def run():
            file_contents: str = self.textPanel.textBox.GetValue()
            state = interpreter.parse(self.fileName, file_contents, 1024, "_start")  # TODO get stackSize and start label from main
            self.sidePanel.update(state)

            res = interpreter.runProgram(state, self.fileName, file_contents, lambda _: self.stopFlag)
            self.sidePanel.update(res)

            self.runThread = None
            self.stopFlag = False

            self.runTool.Enable(True)
            self.debugTool.Enable(True)
            self.stopTool.Enable(False)
            self.GetToolBar().Realize()

        self.console.clear()

        self.runTool.Enable(False)
        self.debugTool.Enable(False)
        self.stopTool.Enable(True)
        self.GetToolBar().Realize()

        self.runThread = threading.Thread(target=run)
        self.runThread.setDaemon(True)
        self.runThread.start()

    def OnStop(self, e):
        if self.runThread is not None:
            self.stopFlag = True


app = wx.App(False)
frame = MainWindow(None, "ASM debugger (beta)")

addText = ''
# save the old print function to print to the console
__old_print = builtins.print


# Overrides the print function to forward all output to the visualizer
# printLine:: [any] -> String -> String -> Stream -> void
def printLine(*args, sep=' ', end='\n', file=None):
    global addText

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

    __old_print(*args, sep=sep, end=end, file=file)

    if end is None:
        end = '\n'

    if len(args) > 0:
        addText += str(args[0])
        for arg in args[1:]:
            addText += str(sep) + str(arg)
    addText += str(end)

    # Flush when \n is sent
    if '\n' in addText:
        frame.console.append(stripColor(addText))

        addText = ''


# overwrite print function
builtins.print = printLine

if __name__ == "__main__":
    app.MainLoop()
