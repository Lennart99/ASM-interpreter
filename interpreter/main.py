from typing import List

import fileLoader
import labelParser
from invalidInputException import InvalidInputException

loadedProgram: List[str] = fileLoader.loadFile("program.asm")

print(loadedProgram)
try:
    print(labelParser.getGlobalLabels(loadedProgram))

    labels = labelParser.getLabels(loadedProgram)
    print(labels)
except InvalidInputException as e:
    print(e.msg.replace("$fileName$", "program.asm"))
    exit(-1)
