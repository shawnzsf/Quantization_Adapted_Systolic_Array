# MIT License

# Copyright (c) 2020 Debtanu Mukherjee

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pyrtl
import os

# Print function
def print_debug(sim):
    a_row = [sim.inspect(f'a{i}') for i in range(ARRAY_SIZE)]
    print(f'a: {a_row}\n')

    for name in ['a_dbg','b', 'c_dbg', 'c_out_dbg']:
        for i in range(ARRAY_SIZE):
            row = [sim.inspect(f'{name}{i}{j}') for j in range(ARRAY_SIZE)]
            print(f"{name} {i}: {row}")

        print()

    c_out_row = [sim.inspect(f'c_out{i}') for i in range(ARRAY_SIZE)]
    print(f'c: {c_out_row}\n')

# Define the Processing Element (PE)
def pe():
    # Inputs
    a = pyrtl.Register(bitwidth=2)
    b = pyrtl.Register(bitwidth=2)
    c = pyrtl.Register(bitwidth=16)

    # Registers
    a_reg = pyrtl.Register(bitwidth=2)
    b_reg = pyrtl.Register(bitwidth=2)
    c_reg = pyrtl.Register(bitwidth=16)

    # Output
    c_out = pyrtl.WireVector(bitwidth=16)

    # Logic
    a_reg.next <<= a
    b_reg.next <<= b
    c_reg.next <<= c

    # Ternary multiplication
    mul = pyrtl.WireVector(bitwidth=2)
    with pyrtl.conditional_assignment:
        with a_reg == 0b00:
            mul |= 0
        with a_reg == 0b01:
            mul |= b_reg
        with a_reg == 0b10:
            mul |= ~b_reg + 0b01

    c_out <<= c_reg + mul

    return a, b, c, c_out, a_reg, b_reg, c_reg


# Create input and output wires to the systolic array
ARRAY_SIZE = 3

a_inputs  = [pyrtl.Input(bitwidth=8, name=f'a{i}') for i in range(ARRAY_SIZE)]
b_inputs  = [[pyrtl.Input(bitwidth=8, name=f'b{i}{j}') for j in range(ARRAY_SIZE)] for i in range(ARRAY_SIZE)]
c_outputs = [pyrtl.Output(bitwidth=16, name=f'c_out{i}') for i in range(ARRAY_SIZE)]

a_dbg = [[pyrtl.Output(bitwidth=8, name=f'a_dbg{i}{j}') for j in range(ARRAY_SIZE)] for i in range(ARRAY_SIZE)]
c_dbg = [[pyrtl.Output(bitwidth=16, name=f'c_dbg{i}{j}') for j in range(ARRAY_SIZE)] for i in range(ARRAY_SIZE)]
c_out_dbg = [[pyrtl.Output(bitwidth=16, name=f'c_out_dbg{i}{j}') for j in range(ARRAY_SIZE)] for i in range(ARRAY_SIZE)]


reset = pyrtl.Input(1, 'reset')

# Define PE array, access elements in the array to supply inputs and get outputs
pe_array = [[pe() for _ in range(ARRAY_SIZE)] for _ in range(ARRAY_SIZE)]


# Create and connect the PEs
for i in range(ARRAY_SIZE):
    for j in range(ARRAY_SIZE):

        if j == 0:
            # Connect the 'a' inputs of the pes in the first column to the systolic array inputs 
            pe_array[i][0][0].next <<= a_inputs[i]
        else:
            # Connect 'a' inputs for remaining columns
            pe_array[i][j][0].next <<= pe_array[i][j-1][0] # pe[][][0] is a
        
        # B inputs remain the same
        pe_array[i][j][1].next <<= b_inputs[i][j]

        # Connect 'c_in' wires
        if i == 0:
            pe_array[i][j][2].next <<= 0
        else:
            pe_array[i][j][2].next <<= pe_array[i-1][j][3]

        # Connect output wires
        c_outputs[j] <<= pe_array[-1][j][3]

        # Debugging
        a_dbg[i][j] <<= pe_array[i][j][4]
        c_dbg[i][j] <<= pe_array[i][j][2]
        c_out_dbg[i][j] <<= pe_array[i][j][3]

# Design Simulation
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

# Input matrices
A = [[0b01, 0b10, 0b01], 
     [0b01, 0b01, 0b10], 
     [0b01, 0b01, 0b01]]

B = [[0b01, 0b01, 0b00], 
     [0b00, 0b01, 0b01],
     [0b01, 0b00, 0b01]]

A_padded = [[0b01, 0b00, 0b00], 
            [0b01, 0b10, 0b00], 
            [0b01, 0b01, 0b01],
            [0b00, 0b01, 0b10],
            [0b00, 0b00, 0b01]]


for name in ['A', 'B']:
    for i in range(ARRAY_SIZE):
        print(f'{name}: {i} {[A[i][j] for j in range(ARRAY_SIZE)]}')
    print()

# Simulation
a_values = {}
b_values = {}

# Set b inputs
for i in range(ARRAY_SIZE):
    for j in range(ARRAY_SIZE):
            b_values[f'b{i}{j}'] = B[i][j]

reset_value = 0
result = [[]]
for cycle in range(9):

    # Set input values
    idx = cycle % 5
    for j in range(ARRAY_SIZE):
        a_values[f'a{j}'] = A_padded[idx][j]

    print(f"Before cycle {cycle}:")

    print_debug(sim)
    
    sim.step({**a_values, **b_values, 'reset': reset_value})

    # reset_value = 1

    print(f"After cycle {cycle}:")

    print_debug(sim)

    result.append([sim.inspect(f'c_out{i}') for i in range(ARRAY_SIZE)])

# Print the final output values
print("Final output matrix:")
for row in result:
    print(row)

# Print the expected output values
C = [[sum(A[i][k] * B[k][j] for k in range(ARRAY_SIZE)) for j in range(ARRAY_SIZE)] for i in range(ARRAY_SIZE)]
print("Expected output matrix:")
for row in C:
    print(row)

with open('D:\Computer Science\Hardware Acceleration\Test_codes\systolic_array.dot', 'w') as f:
    pyrtl.output_to_graphviz(f)

area_estimator = pyrtl.area_estimation()
print("Area estimation:")
print(area_estimator)