import wx
import wx.stc as stc

from typing import Any, Union, List, Optional, Callable

import os
import threading
import sys

import programState
import interpreter
import nodes

# Breakpoint marker ID
MARK_BREAKPOINT = 1
# List of current breakpoints
breakpoints = []

# Address marker ID
MARK_ADDRESS = 2
# Current line marker ID
MARK_CURRENT_LINE = 3

# TODO get stackSize and start label from main
stackSize = 32
startLabel = "_start"

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


# This event is used to update the current line marking from within the run thread, as the marking can only be updated from the main thread
EVT_UPDATE_GUI_ID = wx.NewId()


# This event is used to update the current line marking from within the run thread, as the marking can only be updated from the main thread
class UpdateGUIEvent(wx.PyEvent):
    def __init__(self, func: Callable[[], Any]):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_UPDATE_GUI_ID)
        self.func = func


# represents a Register in the user interface
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


# Loads all icons for the toolbar
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


# The panel that shows the text of the application and makes it possible to set breakpoints
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

        self.textBox.SetMarginType(MARK_BREAKPOINT, stc.STC_MARGIN_SYMBOL)
        self.textBox.SetMarginMask(MARK_BREAKPOINT, 2)  # Could not find how masks work in WX, but this works with MARK_BREAKPOINT = 1
        self.textBox.SetMarginSensitive(MARK_BREAKPOINT, True)
        self.textBox.SetMarginWidth(MARK_BREAKPOINT, 25)

        self.textBox.SetMarginType(MARK_ADDRESS, stc.STC_MARGIN_TEXT)  # line numbers column
        self.textBox.SetMarginWidth(MARK_ADDRESS, 35)  # width of line numbers column
        self.textBox.SetMarginSensitive(MARK_ADDRESS, True)

        self.textBox.SetMarginType(MARK_CURRENT_LINE, stc.STC_MARGIN_NUMBER)  # line numbers column
        self.textBox.SetMarginWidth(MARK_CURRENT_LINE, 25)  # width of line numbers column
        self.textBox.SetMarginSensitive(MARK_CURRENT_LINE, True)

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

    # Handles when the margin is clicked (folding)
    def OnMarginClick(self, e):
        # enable and disable breakpoint as needed
        lineClicked = self.textBox.LineFromPosition(e.GetPosition())  # line 1 = 0
        if self.textBox.MarkerGet(lineClicked):
            if (lineClicked+1) in breakpoints:
                breakpoints.remove(lineClicked+1)
            self.textBox.MarkerDelete(lineClicked, MARK_BREAKPOINT)
        else:
            if (lineClicked+1) not in breakpoints:
                breakpoints.append(lineClicked+1)
            self.textBox.MarkerAdd(lineClicked, MARK_BREAKPOINT)

    def setAddresses(self, state: programState.ProgramState):
        for entry in enumerate(state.memory):
            idx, node = entry
            if node.line != -1:
                self.textBox.MarginSetText(node.line-1, str(idx * 4))

    # Mark the next line to be executed
    def markLine(self, line: int):
        self.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
        self.textBox.MarkerAdd(line-1, MARK_CURRENT_LINE)
        self.textBox.GotoLine(line-1)


class RedirectText:
    def __init__(self, textCtrl, stdout):
        self.out = textCtrl
        self.stdout = stdout

    def stripColor(self, text: str) -> str:
        if "\033[" in text:
            idx = text.index("\033[")
            if "m" in text[idx+2:idx+5]:
                # TODO set color in textbox
                mIdx = text.index("m", idx+2, idx+5)
                return self.stripColor(text[:idx] + text[mIdx + 1:])
            else:
                return self.stripColor(text[:idx] + text[idx + 2:])
        else:
            return text

    def write(self, string):
        wx.PostEvent(frame, UpdateGUIEvent(lambda: self.out.WriteText(self.stripColor(string))))
        self.stdout.write(string)


# This panel shows the console output of the application
class ConsolePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("#FFFFFF")

        self.textBox = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_READONLY)
        self.textBox.SetBackgroundColour("#000000")
        self.textBox.SetForegroundColour("#FFFFFF")
        self.textBox.SetFont(wx.Font(textSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False))

        sizer = wx.GridSizer(rows=1, cols=1, vgap=0, hgap=0)
        sizer.Add(self.textBox, 0, wx.EXPAND)
        self.SetSizer(sizer)

        logger = RedirectText(self.textBox, sys.stdout)
        sys.stdout = logger


# This panel contains the TextPanel and the ConsolePanel and combines these panels into one panel
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


# This panel contains the Values of the registers
class SidePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour("#FFFFFF")

        wx.StaticText(self, -1, "Registers:", pos=(10, 10))
        regs = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "SP", "LR", "PC"]
        self.regEntries = [RegisterEntry(self, reg, 30+30*idx) for idx, reg in enumerate(regs)]

        wx.StaticText(self, -1, "Status Registers:", pos=(10, 530))
        self.statusRegEntries = [RegisterEntry(self, reg, 550+30*idx) for idx, reg in enumerate(["N", "Z", "C", "V"])]

        self.reset()

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

    def reset(self):
        for reg in self.statusRegEntries:
            reg.setValue(False)

        for reg in self.regEntries:
            reg.setValue(0)


# Main application Frame
class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        # Initialize the application Frame and create the Styled Text Control
        wx.Frame.__init__(self, parent, title=title, size=(1200, 800))

        # show the sidepanel on the left and the combined TextPanel and ConsolePanel on the right
        vertSplitter = wx.SplitterWindow(self)
        self.sidePanel = SidePanel(vertSplitter)
        right = RightPanel(vertSplitter)
        vertSplitter.SplitVertically(self.sidePanel, right)
        vertSplitter.SetMinimumPaneSize(150)

        self.textPanel = right.textPanel
        self.console = right.console

        # set default fileName and default directory
        self.dirName = os.path.dirname(__file__)
        self.fileName = ''

        # Toolbar
        self.icons = Icons()
        toolbar: wx.ToolBar = self.CreateToolBar()
        toolbar.SetBackgroundColour('DARKGRAY')

        self.newTool = toolbar.AddTool(wx.ID_ANY, "New",  self.icons.new, "Create empty application")
        self.Bind(wx.EVT_TOOL, self.OnNew, self.newTool)
        self.openTool = toolbar.AddTool(wx.ID_ANY, "Open", self.icons.open, "Open file")
        self.Bind(wx.EVT_TOOL, self.OnOpen, self.openTool)
        self.saveTool = toolbar.AddTool(wx.ID_ANY, "Save",  self.icons.save, "Save file")
        self.Bind(wx.EVT_TOOL, self.OnSave, self.saveTool)
        self.saveAsTool = toolbar.AddTool(wx.ID_ANY, "Save As", self.icons.saveAs, "Save file as")
        self.Bind(wx.EVT_TOOL, self.OnSaveAs, self.saveAsTool)

        toolbar.AddSeparator()

        self.runTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Run", self.icons.run, "Run the program")
        self.Bind(wx.EVT_TOOL, self.OnRun, self.runTool)
        self.debugTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Debug",  self.icons.debug, "Debug the program")
        self.Bind(wx.EVT_TOOL, self.OnDebug, self.debugTool)
        self.stopTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Stop",  self.icons.stop, "Stop the program")
        self.Bind(wx.EVT_TOOL, self.OnStop, self.stopTool)
        self.singleStepTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Single-step",  self.icons.singleStep, "Single-step the program")
        self.Bind(wx.EVT_TOOL, self.OnStep, self.singleStepTool)
        self.resumeBreakpointTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Resume-to-breakpoint", self.icons.resumeToBreakpoint, "Resume to the next breakpoint")
        self.Bind(wx.EVT_TOOL, self.OnResumeBreakpoint, self.resumeBreakpointTool)
        self.resumeTool: wx.ToolBarToolBase = toolbar.AddTool(wx.ID_ANY, "Resume",  self.icons.resume, "Run the rest of the program")
        self.Bind(wx.EVT_TOOL, self.OnResume, self.resumeTool)

        toolbar.AddSeparator()

        quitTool = toolbar.AddTool(wx.ID_ANY, "Quit", self.icons.quit, "Quit")
        self.Bind(wx.EVT_TOOL, lambda _: self.Close(), quitTool)
        # disable some debugging tools
        self.resetTools()

        # Set up event handler for UpdateLineEvent
        self.Connect(-1, -1, EVT_UPDATE_GUI_ID, self.onGUIUpdate)

        # run variables
        self.runThread: Optional[threading.Thread] = None
        self.stopFlag = False
        self.debugState: Optional[programState.ProgramState] = None

        # go ahead and display the application
        self.Show()

    # reset the Enabled flag on all tools to their default value
    def resetTools(self):
        self.GetToolBar().EnableTool(self.newTool.GetId(), True)
        self.GetToolBar().EnableTool(self.openTool.GetId(), True)
        self.GetToolBar().EnableTool(self.saveTool.GetId(), True)
        self.GetToolBar().EnableTool(self.saveAsTool.GetId(), True)

        self.GetToolBar().EnableTool(self.runTool.GetId(), True)
        self.GetToolBar().EnableTool(self.debugTool.GetId(), True)
        self.GetToolBar().EnableTool(self.stopTool.GetId(), False)

        self.GetToolBar().EnableTool(self.singleStepTool.GetId(), False)
        self.GetToolBar().EnableTool(self.resumeBreakpointTool.GetId(), False)
        self.GetToolBar().EnableTool(self.resumeTool.GetId(), False)

        self.GetToolBar().Realize()

    # enable or disable the debug tools (single-step and resume)
    def enableDebugTools(self, enable):
        self.GetToolBar().EnableTool(self.singleStepTool.GetId(), enable)
        self.GetToolBar().EnableTool(self.resumeBreakpointTool.GetId(), enable)
        self.GetToolBar().EnableTool(self.resumeTool.GetId(), enable)

        self.GetToolBar().Realize()

    # enable or disable the run and debug tool
    def enableRunTools(self, enable):
        self.GetToolBar().EnableTool(self.runTool.GetId(), enable)
        self.GetToolBar().EnableTool(self.debugTool.GetId(), enable)

        self.GetToolBar().Realize()

    # enable or disable the file tools (new, open, save, save-as)
    def enableFileTools(self, enable):
        self.GetToolBar().EnableTool(self.newTool.GetId(), enable)
        self.GetToolBar().EnableTool(self.openTool.GetId(), enable)
        self.GetToolBar().EnableTool(self.saveTool.GetId(), enable)
        self.GetToolBar().EnableTool(self.saveAsTool.GetId(), enable)

        self.GetToolBar().Realize()

    # New document menu action
    def OnNew(self, _):
        # Empty the instance variable for current filename, and the main text box's content
        self.fileName = ""
        self.textPanel.textBox.SetValue("")

        breakpoints.clear()
        self.textPanel.textBox.MarkerDeleteAll(MARK_BREAKPOINT)
        self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)

    # Open existing document menu action
    def OnOpen(self, _):
        # First try opening the existing file; if it fails, the file doesn't exist most likely
        dlg = wx.FileDialog(self, "Choose a file to open", self.dirName, "", "*.*", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.fileName = dlg.GetFilename()
            self.dirName = dlg.GetDirectory()
            path = os.path.join(self.dirName, self.fileName)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    self.textPanel.textBox.SetValue(f.read())

                breakpoints.clear()
                self.textPanel.textBox.MarkerDeleteAll(MARK_BREAKPOINT)
                self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
            else:
                dlg = wx.MessageDialog(self, " Couldn't open file", "Error 009", wx.ICON_ERROR)
                dlg.ShowModal()
        dlg.Destroy()

    # Save the document menu action
    def OnSave(self, _):
        # First try just saving the existing file, but if that file doesn't
        # exist it will fail, and the except will launch the Save As.
        if self.fileName == "":
            # If regular save fails, try the Save As method.
            dlg = wx.FileDialog(self, "Save file", self.dirName, "Untitled", "*.*", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                self.fileName = dlg.GetFilename()
                self.dirName = dlg.GetDirectory()
                path = os.path.join(self.dirName, self.fileName)
                with open(path, 'w') as f:
                    f.write(self.textPanel.textBox.GetValue())
            dlg.Destroy()
        else:
            f = open(os.path.join(self.dirName, self.fileName), 'w')
            f.write(self.textPanel.textBox.GetValue())
            f.close()

    # Save a new document menu action
    def OnSaveAs(self, _):
        dlg = wx.FileDialog(self, "Save file as", self.dirName, self.fileName, "*.*", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.fileName = dlg.GetFilename()
            self.dirName = dlg.GetDirectory()
            path = os.path.join(self.dirName, self.fileName)
            with open(path, 'w') as f:
                f.write(self.textPanel.textBox.GetValue())
        dlg.Destroy()

    # Run tool action
    def OnRun(self, _):
        def run():
            self.textPanel.textBox.SetEditable(False)

            file_contents: str = self.textPanel.textBox.GetValue()
            state = interpreter.parse(self.fileName, file_contents, stackSize, startLabel)
            wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.textPanel.setAddresses(state)]))

            lines = file_contents.split('\n')

            while True:
                if self.stopFlag:
                    break
                state, success = interpreter.executeInstruction(state.getInstructionFromMem(state.getReg("PC")), state, self.fileName, lines)
                if not success:
                    break

            # program has exited
            wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.resetTools()]))

            self.runThread = None
            self.stopFlag = False

            self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
            self.textPanel.textBox.SetEditable(True)

        if self.runThread is None:

            self.stopTool.Enable(True)
            self.enableRunTools(False)
            self.enableFileTools(False)

            self.stopFlag = False

            self.runThread = threading.Thread(target=run)
            self.runThread.setDaemon(True)
            self.runThread.start()

    # Debug tool action
    def OnDebug(self, _):
        def run():
            self.textPanel.textBox.SetEditable(False)

            file_contents: str = self.textPanel.textBox.GetValue()
            state = interpreter.parse(self.fileName, file_contents, stackSize, startLabel)
            wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.textPanel.setAddresses(state)]))

            lines = file_contents.split('\n')

            while not self.stopFlag:
                node: nodes.InstructionNode = state.getInstructionFromMem(state.getReg("PC"))
                if node.line in breakpoints:
                    # breakpoint found - save state and enable the single-step and resume tools
                    self.debugState = state
                    self.runThread = None

                    wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.textPanel.markLine(node.line), self.enableDebugTools(True)]))

                    return
                state, success = interpreter.executeInstruction(node, state, self.fileName, lines)
                if not success:
                    break

            # program has exited
            wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.resetTools()]))

            self.runThread = None
            self.stopFlag = False

            self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
            self.textPanel.textBox.SetEditable(True)

        if self.runThread is None:

            self.stopTool.Enable(True)
            self.enableRunTools(False)
            self.enableFileTools(False)

            self.stopFlag = False

            self.runThread = threading.Thread(target=run)
            self.runThread.setDaemon(True)
            self.runThread.start()

    # Stop tool action
    def OnStop(self, _):
        if self.runThread is not None:
            self.stopFlag = True
        if self.debugState is not None:
            self.debugState = None

            self.resetTools()

            self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
            self.textPanel.textBox.SetEditable(True)

    # Single-step tool action
    def OnStep(self, _):
        lines = self.textPanel.textBox.GetValue().split('\n')

        node: nodes.InstructionNode = self.debugState.getInstructionFromMem(self.debugState.getReg("PC"))
        state, success = interpreter.executeInstruction(node, self.debugState, self.fileName, lines)

        self.sidePanel.update(state)

        if not success:
            # program has exited
            self.debugState = None
            self.runThread = None
            self.stopFlag = False

            self.resetTools()

            self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
            self.textPanel.textBox.SetEditable(True)
        else:
            self.debugState = state
            nextNode: nodes.InstructionNode = self.debugState.getInstructionFromMem(self.debugState.getReg("PC"))
            if not isinstance(nextNode, nodes.SystemCall):
                self.textPanel.markLine(nextNode.line)

    # ResumeToBreakpoint tool action
    def OnResumeBreakpoint(self, _):
        def run():
            firstRun = True  # make sure to not block on the same breakpoint right away

            state = self.debugState
            wx.PostEvent(self, UpdateGUIEvent(lambda: self.sidePanel.update(state)))

            lines = self.textPanel.textBox.GetValue().split('\n')

            while not self.stopFlag:
                node: nodes.InstructionNode = state.getInstructionFromMem(state.getReg("PC"))
                if node.line in breakpoints and not firstRun:
                    # breakpoint found - save state and enable the single-step and resume tools
                    self.debugState = state
                    self.runThread = None

                    wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.textPanel.markLine(node.line), self.enableDebugTools(True)]))

                    return
                state, success = interpreter.executeInstruction(node, state, self.fileName, lines)
                firstRun = False
                if not success:
                    break

            # program has exited
            wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.resetTools()]))

            self.runThread = None
            self.debugState = None
            self.stopFlag = False

            self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
            self.textPanel.textBox.SetEditable(True)

        if self.runThread is None:
            self.enableDebugTools(False)

            self.stopFlag = False

            self.runThread = threading.Thread(target=run)
            self.runThread.setDaemon(True)
            self.runThread.start()

    # Resume tool action
    def OnResume(self, _):
        def run():
            state = self.debugState
            wx.PostEvent(self, UpdateGUIEvent(lambda: self.sidePanel.update(state)))

            lines = self.textPanel.textBox.GetValue().split('\n')

            while not self.stopFlag:
                node: nodes.InstructionNode = state.getInstructionFromMem(state.getReg("PC"))
                state, success = interpreter.executeInstruction(node, state, self.fileName, lines)
                if not success:
                    break

            # program has exited
            wx.PostEvent(self, UpdateGUIEvent(lambda: [self.sidePanel.update(state), self.resetTools()]))

            self.runThread = None
            self.debugState = None
            self.stopFlag = False

            self.textPanel.textBox.MarkerDeleteAll(MARK_CURRENT_LINE)
            self.textPanel.textBox.SetEditable(True)

        if self.runThread is None:
            self.enableDebugTools(False)

            self.stopFlag = False

            self.runThread = threading.Thread(target=run)
            self.runThread.setDaemon(True)
            self.runThread.start()

    # Event handler for UpdateLineEvent
    # This event is used to update the current line marking from within the run thread, as the marking can only be updated from the main thread
    def onGUIUpdate(self, e: UpdateGUIEvent):
        e.func()


app = wx.App(False)
frame = MainWindow(None, "ASM debugger (beta)")

if __name__ == "__main__":
    app.MainLoop()
