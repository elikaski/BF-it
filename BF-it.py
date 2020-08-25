#!/usr/bin/env python3

import argparse
import os
import Compiler
import Interpreter


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath", metavar="input_file", nargs=1, help="Path to the input code file")
    parser.add_argument("-o", metavar="output_file", nargs=1, help="Path to output Brainfuck file")
    parser.add_argument("-r", action="store_true", help="Run the Brainfuck file after compilation")

    args = parser.parse_args()

    input_file = args.filepath[0]
    if args.o:
        output_file = args.o[0]
    else:
        output_file_basename = os.path.splitext(os.path.basename(input_file))[0] + ".bf"
        output_file = os.path.join(os.path.dirname(input_file), output_file_basename)

    run_file = args.r

    return input_file, output_file, run_file


def compile_file(input_file, output_file, run):
    print("Compiling file '%s'..." % input_file)

    with open(input_file, "rt", encoding="unicode_escape") as f:
        code = f.read()

    with open(input_file, "rt") as f:
        original_code = f.read()

    brainfuck_code = Compiler.compile(code, original_code)
    brainfuck_code += "\n"

    with open(output_file, "wt") as f:
        f.write(brainfuck_code)

    print("Compiled successfully to '%s'" % output_file)

    if run:
        print("Running compiled code...")
        Interpreter.brainfuck(brainfuck_code)


if __name__ == '__main__':
    input_file, output_file, run_file = process_args()
    compile_file(input_file, output_file, run_file)


