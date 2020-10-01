#!/usr/bin/env python3

import sys


def create_jumps_dictionary(program):
    lbraces = list()
    res = dict()

    for index, command in enumerate(program):
        if command == '[':
            lbraces.append(index)
        elif command == ']':
            if len(lbraces) == 0:
                raise SyntaxError("Brainfuck: mismatched parentheses")

            lbrace_index = lbraces.pop()
            res[lbrace_index] = index
            res[index] = lbrace_index

    return res


def brainfuck(program):
    program = ''.join(char for char in program if char in "[]-+><.,")
    program = (program.replace("[-]", "0")
    .replace(">>>", "D")
    .replace("<<<", "A")
    .replace("[-<+>]", "m")
    .replace("[<+>-]", "m")
    .replace("[->+<]", "M")
    .replace("[>+<-]", "M")
    .replace("[<<+>>-]", "n")
    .replace("[-<<+>>]", "n")
    .replace("[>+>+<<-]", "b")
    .replace("[->+>+<<]", "b")
    .replace("[>>+>+A-]", "B")
    .replace("[->>+>+A]", "B")
    .replace("[-D+<+<<]", "B")
    .replace("[D+<+<<-]", "B")
    .replace("[<+>>+<-]", "V")
    .replace("[>+<<+>-]", "V")
    .replace("[-<+>>+<]", "V")
    .replace("[D+>+A<-]", "c")
    .replace("[A<+D>-]", "C")
    .replace("++++++", "z")
    .replace("----", "Z")
    )

    jumps = create_jumps_dictionary(program)
    data = dict()
    data_pointer = 0

    instruction_pointer = 0

    while instruction_pointer < len(program):
        command = program[instruction_pointer]

        if command == '>':
            data_pointer += 1
        elif command == '<':
            data_pointer -= 1
        elif command == '0': # [-]
            data[data_pointer] = 0
        elif command == 'D': # >>>
            data_pointer += 3
        elif command == 'A': # <<<
            data_pointer -= 3
        elif command == 'm': # [<+>-]
            data[data_pointer-1] = (data.get(data_pointer-1, 0) + data.get(data_pointer, 0))%256
            data[data_pointer] = 0
        elif command == 'M': # [>+<-]
            data[data_pointer+1] = (data.get(data_pointer+1, 0) + data.get(data_pointer, 0))%256
            data[data_pointer] = 0
        elif command == 'c': # [>>>+>+<<<<-]
            current_cell = data.get(data_pointer, 0)
            data[data_pointer+3] = (data.get(data_pointer+3, 0) + current_cell)%256
            data[data_pointer+4] = (data.get(data_pointer+4, 0) + current_cell)%256
            data[data_pointer] = 0
        elif command == 'C': # [<<<<+>>>>-]
            data[data_pointer-4] = (data.get(data_pointer-4, 0) + data.get(data_pointer, 0))%256
            data[data_pointer] = 0
        elif command == 'z': # ++++++
            data[data_pointer] = (data.get(data_pointer, 0) + 6) % 256
        elif command == 'Z': # ----
            data[data_pointer] = (data.get(data_pointer, 0) - 4) % 256
        elif command == 'b': # [>+>+<<-]
            current_cell = data.get(data_pointer, 0)
            data[data_pointer+1] = (data.get(data_pointer+1, 0) + current_cell)%256
            data[data_pointer+2] = (data.get(data_pointer+2, 0) + current_cell)%256
            data[data_pointer] = 0
        elif command == 'B': # [>>+>+<<<-]
            current_cell = data.get(data_pointer, 0)
            data[data_pointer+2] = (data.get(data_pointer+2, 0) + current_cell)%256
            data[data_pointer+3] = (data.get(data_pointer+3, 0) + current_cell)%256
            data[data_pointer] = 0
        elif command == 'V': # [<+>>+<-]
            current_cell = data.get(data_pointer, 0)
            data[data_pointer-1] = (data.get(data_pointer-1, 0) + current_cell)%256
            data[data_pointer+1] = (data.get(data_pointer+1, 0) + current_cell)%256
            data[data_pointer] = 0
        elif command == 'n': # [<<+>>-]
            data[data_pointer-2] = (data.get(data_pointer-2, 0) + data.get(data_pointer, 0))%256
            data[data_pointer] = 0
        elif command == '+':
            data[data_pointer] = (data.get(data_pointer, 0) + 1)
            if data[data_pointer] == 256:
                data[data_pointer] = 0
        elif command == '-':
            data[data_pointer] = (data.get(data_pointer, 0) - 1)
            if data[data_pointer] == -1:
                data[data_pointer] = 255
        elif command == ',':
            data[data_pointer] = ord(sys.stdin.read(1)) % 256
        elif command == '.':
            print(chr(data.get(data_pointer, 0)), end='', flush=True)
        elif command == '[':
            if data.get(data_pointer, 0) == 0:
                instruction_pointer = jumps[instruction_pointer]
        elif command == ']':
            if data.get(data_pointer, 0) != 0:
                instruction_pointer = jumps[instruction_pointer]
        else:  # everything else is comment
            pass

        instruction_pointer += 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: '%s' <path_to_brainfuck_code_file>" % sys.argv[0])
        exit(0)

    fpath = sys.argv[1]
    with open(fpath, "rt") as f:
        code = f.read()

    brainfuck(code)
