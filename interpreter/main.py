import fileLoader
from fileLoader import LoadedFile

loadedProgram: LoadedFile = fileLoader.loadFile("program.asm")

print(loadedProgram)
