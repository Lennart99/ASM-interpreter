# ARM Cortex M0 interpreter

### Features

- Implements basic instructions like MOV, LDR(H/B), STR(H/B), PUSH, POP, ADD, SUB, CMP
- Supports Branch and Branch-link instructions as well as conditional branch instructions
- Error handling for both the parse and run steps, showing the call stack for runtime errors
- A visualizer to show the registers of the simulated processor and the current instruction and interact with the memory of the simulated processor


### Conditional branch instructions

These conditional branch instructions are supported:

- BCC/BCLO: carry clear / unsigned lower
- BCS/BHS: Carry set / unsigned higher or same
- BEQ: Equal / zero
- BGE: Signed greater than or equal
- BGT: Signed greater than
- BHI: Unsigned higher
- BLE: Signed less than or equal
- BLS: Unsigned lower or same
- BLT: Signed less than
- BMI: Minus / negative
- BNE: Not equal / not zero
- BPL: Plus / zero or positive
- BVC: No overflow
- BVS: Overflow

### error detection

To enable the userr to find problenms in their code easily, clear errors are thrown when problems orccur. When a runtime errror occurs, a stacktrace is printed to make it easy to trace the problem back.

![alt text](pictures/stacktrace.png)

### The visualizer

Using the visualizer, the register processor can be viewed easily to make debugging code easier. It is also possible to single-step the program to see exactly when the program broke. The current instruction and its location in the source code is shown to make it easy to find the instruction in the source code.

![alt text](pictures/visualizer.png)