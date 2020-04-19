from typing import List

import fileLoader
import labelParser


loadedProgram: List[str] = fileLoader.loadFile("program.asm")

print(loadedProgram)

print(labelParser.getGlobalLabels(loadedProgram))

labels = labelParser.getLabels(loadedProgram)
print(labels)
