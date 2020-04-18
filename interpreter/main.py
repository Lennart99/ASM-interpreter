from typing import List, Tuple

import fileLoader
import labelParser


loadedProgram: List[str] = fileLoader.loadFile("program.asm")

print(loadedProgram)

print(labelParser.getGlobalLabels(loadedProgram))

enum: List[Tuple[int, str]] = list(enumerate(loadedProgram))
labels = labelParser.getLabels(enum)

print(labels)
