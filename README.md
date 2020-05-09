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

### The visualizer

