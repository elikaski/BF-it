#!/usr/bin/env python3

import argparse
import os
from Compiler import Compiler
from Compiler import Minify
import Interpreter


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath", metavar="input_file", nargs=1, help="Path to the input code file")
    parser.add_argument("-o", metavar="output_file", nargs=1, help="Path to output Brainfuck file")
    parser.add_argument("-r", action="store_true", help="Run the Brainfuck file after compilation")
    parser.add_argument("-m", "--minify", dest="minify", action="store_true", help="Minifies the compiled code")

    args = parser.parse_args()

    input_file = args.filepath[0]
    if args.o:
        output_file = args.o[0]
    else:
        output_file_basename = os.path.splitext(os.path.basename(input_file))[0] + ".bf"
        output_file = os.path.join(os.path.dirname(input_file), output_file_basename)

    run_file = args.r
    minify_file = args.minify

    return input_file, output_file, run_file, minify_file


def compile_file(input_file, output_file, run, minify_file):
    print("Compiling file '%s'..." % input_file)

    with open(input_file, "rb") as f:
        code = f.read().decode("utf8")

    brainfuck_code = Compiler.compile(code)
    brainfuck_code += "\n"

    if minify_file:
        brainfuck_code = Minify.minify(brainfuck_code)

    with open(output_file, "wt") as f:
        f.write(brainfuck_code)

    print("Compiled successfully to '%s'" % output_file)

    if run:
        print("Running compiled code...")
        Interpreter.brainfuck(brainfuck_code)


if __name__ == '__main__':
    input_file, output_file, run_file, minify_file = process_args()
    #input_file = "examples/games/tic_tac_toe.code"
    compile_file(input_file, output_file, run_file, minify_file)
