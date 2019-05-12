#!/usr/bin/env python3

from Token import Token
from Lexical_analyzer import analyze
from collections import namedtuple
import sys
import Interpreter

ADD_DIVISION_BY_ZERO_CHECK = True


class BFSyntaxError(Exception):
    pass


class BFSemanticError(Exception):
    pass


def create_function(name, type, parameters, code):
    # returns function named tuple

    function = namedtuple("function", ["name", "type", "parameters", "code"])
    function.name = name
    function.type = type
    function.parameters = parameters
    function.code = code

    return function


def create_variable(name, type, size):
    # return variable named tuple
    variable = namedtuple("variable", ["name", "type", "size", "cell_index"])

    variable.name = name
    variable. type = type
    variable.size = size
    variable.cell_index = None  # will be updated when we insert this variable into an ids map

    return variable


def get_readint_code():
    # res, tmp, input, loop
    # tmp is used for multiplication
    """
    res = 0
    loop = 1

    while loop
        loop = 0
        input = input()
        if input != newline # todo add a eof check as well. run it in several interpreters to look for common ways for "end of number" input
            loop = 1
            res *= 10 + char_to_digit(input)
    """

    code = "[-]"  # clear res = 0
    code += ">[-]"  # tmp = 0
    code += ">>[-]+"  # loop = 1

    code += "["  # while loop == 1
    code += "[-]"  # loop = 0
    code += "<"  # point to input
    code += ","  # input character
    code += "----------"  # sub 10 (check for newline)

    code += "["  # if input is not newline
    code += ">"  # point to loop
    code += "+"  # loop = 1

    # multiply res by 10 and add the input digit
    code += "<<<"  # point to res
    code += "[>+<-]"  # move res to tmp
    code += ">"  # point to tmp
    code += "[<++++++++++>-]"  # res = tmp * 10, tmp = 0
    code += ">"  # point to input
    code += "-" * (0x30 - 10)  # convert character to digit by substracting 0x30 from it (we already substracted 10 before)
    code += "[<<+>>-]"  # res += input
    code += "]"  # end if

    code += ">"  # point to loop
    code += "]"  # end while

    code += "<<<"  # point to res

    return code


def get_printint_code():
    # return_cell value_to_print_cell

    code = ">"  # point to value_to_print cell
    code += ">[-]" * 10 + "<" * 10  # zero some cells

    # ==============================================================================================
    # code to print num (taken from https://esolangs.org/wiki/brainfuck_algorithms#Print_value_of_cell_x_as_number_.288-bit.29)
    code += ">>++++++++++<<[->+>-[>+>>]>[+[-<+>]>+>>]<<<<<<]>>[-]>>>++++++++++<[->-[>+>>]>[+[-"
    code += "<+>]>+>>]<<<<<]>[-]>>[>++++++[-<++++++++>]<.<<+>+>[-]]<[<[->-<]++++++[->++++++++"
    code += "<]>.[-]]<<++++++[-<++++++++>]<.[-]<<[-<+>]<"
    # todo either document this or write one of my own
    # ==============================================================================================

    code += "<"  # point to value_to_return cell
    return code


def get_readchar_code():
    # read input into "return value cell". no need to move the pointer
    code = ","
    return code

def get_printchar_code():
    # point to parameter, output it, and then point back to "return value cell"
    code = ">.<"
    return code

def get_offset_to_variable(compiler, ID, current_pointer):
    offset = current_pointer - compiler.get_id_index(ID)
    return offset


def get_set_cell_value_code(new_value, previous_value, zero_next_cell_if_necessary=True):
    # this function returns a code that sets the current cell's value to new_value,
    # given that its previous value is previous_value

    # it may return the "naive" way, of "+"/"-" usage, <offset> times
    # and it may return an optimization using loops, by using the next cell as a loop counter
    # if zero_next_cell_if_necessary is set to False, it assumes that the next cell is already 0

    # after the code of this function is executed, the pointer will point to the original cell
    # this function returns the shorter code between "naive" and "looped"

    offset = new_value - previous_value
    char = "+" if offset > 0 else "-"
    offset = abs(offset)

    # "naive" code is simply +/-, <offset> times
    naive = char * offset

    # "looped" code is "[<a> times perform <b> adds/subs] and then <c> more adds/subs"
    def get_abc(offset):
        # returns a,b,c such that a*b+c=offset and a+b+c is minimal

        min_a, min_b, min_c = offset, 1, 0
        min_sum = min_a + min_b + min_c

        for i in range(1, offset//2+1):
            a, b, c = i, offset//i, offset % i
            curr_sum = a + b + c

            if curr_sum < min_sum:
                min_a, min_b, min_c = a, b, c
                min_sum = curr_sum

        return min_a, min_b, min_c

    a, b, c = get_abc(offset)
    looped = ">"  # point to next cell (loop counter)
    if zero_next_cell_if_necessary:
        looped += "[-]"  # zero it if necessary
    looped += "+" * a  # set loop counter
    looped += "[-<" + char * b + ">]"  # sub 1 from counter, perform b actions
    looped += "<"  # point to "character" cell
    looped += char * c  # c more actions

    if len(naive) < len(looped):
        return naive
    else:
        return looped


def get_token_code(compiler, token, current_pointer):
    # generate code that evaluates the token at the current pointer, and sets the pointer to point to the next available cell
    if token.type == Token.NUM:
        value = int(token.data, 16) if token.data.startswith("0x") else int(token.data)
        code = "[-]"  # zero current cell
        code += get_set_cell_value_code(value, 0)  # set current cell to the num value
        code += ">"  # point to the next cell

        return code

    elif token.type == Token.CHAR:
        code = "[-]"  # zero current cell
        code += get_set_cell_value_code(ord(token.data), 0)  # set current cell to the char value
        code += ">"  # point to next cell
        return code

    elif token.type == Token.ID:
        code = get_copy_from_variable_code(compiler, token.data, current_pointer)
        return code

    elif token.type == Token.TRUE:
        code = "[-]"  # zero current cell
        code += "+"  # current cell = 1
        code += ">"  # point to next cell

        return code

    elif token.type == Token.FALSE:
        code = "[-]"  # zero current cell
        code += ">"  # point to next cell

        return code

    raise NotImplementedError


def get_move_to_offset_code(offset):
    #  returns code that moves value from current pointer to cell at offset <offset> to the left
    #  after this, the pointer points to the original cell, which is now the next available cell

    code = "<" * offset  # point to destination
    code += "[-]"  # zero destination
    code += ">" * offset  # point to source cell
    code += "[" + "<" * offset + "+" + ">" * offset + "-]"  # increase destination, zero source
    # point to next free location (source, which is now zero)

    return code


def get_copy_to_offset_code(offset):
    #  returns code that copies value from current pointer to cell at offset <offset> to the left
    #  after this, the pointer points to the original cell, which remains unchanged

    code = ">"  # point to temp
    code += "[-]"  # zero temp
    code += "<" * (offset + 1)  # point to destination
    code += "[-]"  # zero destination
    code += ">" * offset  # point to source cell
    code += "[>+" + "<" * (offset + 1) + "+" + ">" * offset + "-]"  # increase temp and destination, zero source
    code += ">"  # point to temp
    code += "[<+>-]"  # move temp to original cell
    code += "<"  # point to original cell

    return code


def get_copy_to_variable_code(compiler, ID, current_pointer):
    # returns code that copies value from current pointer to cell of the variable ID
    # after this, the pointer points to the original cell, which remains unchanged

    offset = get_offset_to_variable(compiler, ID, current_pointer)
    return get_copy_to_offset_code(offset)


def get_move_to_return_value_cell_code(current_stack_pointer):
    #  returns code that moves value from current pointer to return_value cell
    #  after this, the pointer points to the original cell, which is now the next available cell

    # return_value_cell is always at index 0
    # therefore we need to move it <current_stack_pointer> cells left
    return get_move_to_offset_code(current_stack_pointer)


def get_copy_from_variable_code(compiler, ID, current_pointer):
    #  returns code that copies value from cell of variable ID to current pointer, and then sets the pointer to the next cell

    offset = get_offset_to_variable(compiler, ID, current_pointer)
    code = "[-]"  # res = 0
    code += ">[-]"  # temp (next cell) = 0
    code += "<" * (offset + 1)  # point to destination cell
    code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
    code += ">" * (offset + 1)  # point to temp
    code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
    # at this point we point to the next available cell, which is temp, which is now zero

    return code


def get_divmod_code():
    # given that the current pointer points to a, and the cell after a contains b,
    # (i.e the cells look like: --> a, b, ?, ?, ?, ?, ...)
    # returns a code that calculates divmod, and the cells look like this:
    # --> 0, b-a%b, a%b, a/b, 0, 0
    # and the pointer points to the first 0 (which is in the same cell as a used to be)

    def get_if_equal_to_0_code(inside_if_code, offset_to_temp_cell):
        """
        given a <inside_if_code>, wraps it with an "if (current_cell == 0) {<inside_if_code>}"

        in the process, it zeros the current cell
        additionally, it uses a temp cell
        the argument <offset_to_temp_cell> is the offset from the current cell to the temp cell
        *** note that the temp cell must be AFTER the cells that the <inside_if_code> touches ***

        <inside_if_code> should assume it starts running when pointing to the current cell
        and it should end its run pointing to the same cell
        """

        # temp cell is initialized to 1, and holds a flag of whether or not we should run <inside_if_code> or not
        # if cell to evaluate is not zero, we set this flag to 0

        code = ">" * offset_to_temp_cell  # point to temp
        code += "[-]+"  # temp = 1
        code += "<" * offset_to_temp_cell  # point to cell to compare to 0

        code += "["  # if it is not zero
        code += ">" * offset_to_temp_cell  # point to temp
        code += "-"  # temp = 0
        code += "<" * offset_to_temp_cell  # point to cell
        code += "[-]"  # zero the cell
        code += "]"  # end if

        code += ">" * offset_to_temp_cell  # point to temp cell
        code += "["  # if it is non zero
        code += "<" * offset_to_temp_cell  # point to cell
        code += inside_if_code  # execute desired code
        # at this point we point to the original cell
        code += ">" * offset_to_temp_cell  # point to temp cell
        code += "-"  # temp = 0
        code += "]"  # end if
        code += "<" * offset_to_temp_cell  # point back to original cell

        return code

    code = ""

    if ADD_DIVISION_BY_ZERO_CHECK:
        # create a prefix code: if (b == 0) {print("Error - Division by zero\n");}

        # copy b to temp cell (via another temp cell) and compare that cell to 0. if its 0, execute error print and go to infinite loop

        code += ">>"  # point to empty cell
        code += "[-]>[-]"  # zero 2 temp cells
        code += "<<"  # point to b
        code += "[>+>+<<-]"  # move b to both cells
        code += ">"  # point to first cell
        code += "[<+>-]"  # move first cell back to b
        code += ">"  # point to second cell

        code_inside_if = "[-]>[-]<>++++++[-<+++++++++++>]<+++.>+++++[-<+++++++++>]<..---.+++.>+++++++++[-<--------->]" \
                         "<-.+++++++++++++.-------------.>++++++[-<++++++>]<.>++++++[-<++++++>]<+.+++++++++++++.-----" \
                         "--------.++++++++++.----------.++++++.-.>++++++[-<------------->]<.>++++++[-<+++++++++++>]<" \
                         ".>+++[-<+++++++>]<++.>++++++++[-<----------->]<-.>+++++++++[-<++++++++++>]<.>+++[-<------->" \
                         "]<.+++++++++++++.---.>++++++++++[-<---------->]<-."  # print("Error - Division by zero\n");
        code_inside_if += "[]"  # infinite loop

        code += get_if_equal_to_0_code(code_inside_if, offset_to_temp_cell=1)
        code += "<<<"  # point to a

        # ======================= end of prefix =======================


    # a, b, w, x, y, z

    code += ">>[-]>[-]>[-]>[-]<<<<<"  # zero w,x,y,z, and point to a
    code += "["  # while a != 0

    code += "-"  # decrease a by 1
    code += ">-"  # decrease b by 1
    code += ">+"  # increase w by 1
    code += "<"  # point to b
    code += "[->>>+>+<<<<]>>>>[-<<<<+>>>>]"  # copy b to y (via z)
    code += "<"  # point to y

    code_inside_if = ""
    code_inside_if += "<+"  # increase x by 1
    code_inside_if += "<"  # point to w
    code_inside_if += "[-<+>]"  # copy w to b (b is already 0) (after this we point to w)
    code_inside_if += ">>"  # point to y

    # get_if_equal_to_0 also zeros y
    # i set offset_to_temp_cell = 1 because it can use z, since it is unused inside the if
    code += get_if_equal_to_0_code(inside_if_code=code_inside_if, offset_to_temp_cell=1)

    code += "<<<<"  # point to a
    code += "]"  # end while

    """
    a, b, w, x, y, z
    
    
    w, x, y, z = 0, 0, 0, 0

    while a != 0
        a -= 1
        b -= 1
        w += 1

        if b == 0:  (this means that w = original b) (implementation: copy b to y (via z) and compare y to 0, (then zero y))
            x += 1
            b = w
            w = 0




    at the end:
    w = a%b
    x = a/b
    b = b-a%b

    """

    return code


def get_unary_prefix_op_code(token, offset_to_variable=None):
    # returns code that:
    # performs op on operand that is at the current pointer
    # the result is placed in the cell of the operand
    # and the pointer points to the cell right after it (which becomes the next available cell)

    if token.type == Token.NOT:
        # a temp
        code = ">"  # point to temp
        code += "[-]+"  # temp = 1
        code += "<"  # point to a
        code += "["  # if a is non-zero
        code += ">-"  # temp = 0
        code += "<[-]"  # zero a
        code += "]"  # end if

        code += ">"  # point to temp
        code += "["  # if temp is non-zero
        code += "<+"  # a = 1
        code += ">-"  # temp = 0
        code += "]"  # end if

        return code

    elif token.type == Token.INCREMENT:
        #  returns code that copies value from variable's cell at given offset, and adds 1 to both the copied and the original cell
        assert offset_to_variable is not None
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * offset  # point to res
        code += "+"  # increase res by 1
        code += ">"  # point to temp
        code += "+"  # increase temp by 1
        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    elif token.type == Token.DECREMENT:
        #  returns code that copies value from variable's cell at given offset, and subtracts 1 from both the copied and the original cell
        assert offset_to_variable is not None
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * offset  # point to res
        code += "-"  # decrease res by 1
        code += ">"  # point to temp
        code += "-"  # decrease temp by 1
        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    elif token.type == Token.UNARY_MULTIPLICATIVE:
        #  returns code that copies value from variable's cell at given offset, modifies both the copied and the original cell depending on the op
        assert offset_to_variable is not None
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * offset  # point to res

        if token.data in ["**", "//"]:
            code += ">"  # point to temp (x**, x// keep x the same)
        elif token.data == "%%":
            code += "[-]>[-]"  # put 0 in res and temp, and point to temp
        else:
            raise BFSyntaxError("Unexpected unary prefix %s" % str(token))

        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    raise NotImplementedError


def get_unary_postfix_op_code(token, offset_to_variable):
    # returns code that:
    # performs op on operand that is at the current pointer
    # the result is placed in the cell of the operand
    # and the pointer points to the cell right after it (which becomes the next available cell)

    if token.type == Token.INCREMENT:
        #  returns code that copies value from variable's cell at given offset, and adds 1 to the original cell
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * (offset + 1)  # point to temp
        code += "+"  # increase temp by 1
        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    elif token.type == Token.DECREMENT:
        #  returns code that copies value from variable's cell at given offset, and subtracts 1 from the original cell
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * (offset + 1)  # point to temp
        code += "-"  # decrease temp by 1
        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    elif token.type == Token.UNARY_MULTIPLICATIVE:
        # returns code that copies value from variable's cell at given offset, and modifies the original cell depending on the operation
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * (offset + 1)  # point to temp

        if token.data in ["**", "//"]:
            pass  # x**,x// keeps x the same
        elif token.data == "%%":
            code += "[-]"  # x%% modifies x to 0
        else:
            raise BFSyntaxError("Unexpected unary postfix %s" % str(token))

        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    raise NotImplementedError


def get_op_between_literals_code(op_token):
    # returns code that:
    # performs op on 2 operands
    # the first operand is at current pointer, and the second operand is at current pointer + 1
    # the code can destroy second operand, and everything after it

    # the result is placed in the cell of the first operand
    # and the pointer points to the cell right after it (which becomes the next available cell)

    op = op_token.data
    if op == "+" or op == "-":
        res = ">[<" + op + ">-]"  # increase/decrease first operand and decrease second operand
        # the pointer points to the next available cell, which is the second operand, which is 0

        return res

    elif op == "*":
        # a, b, temp1, temp2
        res = ">>[-]>[-]"  # put 0 into temp1, temp2
        res += "<<<"  # point to first operand
        res += "[>>>+<<<-]"  # move first operand to temp2
        res += ">>>"  # point to temp2

        # do in a loop: as long as temp2 != 0
        res += "["

        res += "<<"  # point to second operand
        res += "[<+>>+<-]"  # add it to first operand and temp1
        res += ">"  # point to temp1
        res += "[<+>-]"  # move it to second operand

        # end loop
        res += ">"  # point back to temp2
        res += "-"  # decrease temp2
        res += "]"

        res += "<<"  # point back to next available cell (second operand)
        return res

    elif op == "/":
        code = get_divmod_code()
        code += ">>>"  # point to a/b
        code += "[<<<+>>>-]"  # copy a/b to current cell
        code += "<<"  # point to next available cell

        return code

    elif op == "%":
        code = get_divmod_code()
        code += ">>"  # point to a%b
        code += "[<<+>>-]"  # copy a%b to current cell
        code += "<"  # point to next available cell

        return code

    # relops
    elif op == "==":
        # a, b
        res = "[->-<]"  # a = 0, b = b - a
        res += "+"  # a = 1. will hold the result. if a!=b, this is unchanged
        res += ">"  # point to b
        res += "["  # if b == 0, enter the following code
        res += "<->[-]"  # a = 0, b=0
        res += "]"  # end of "loop"

        return res

    elif op == "!=":
        # a, b
        res = "[->-<]"  # a = 0, b = b - a
        # a will hold the result. if a!=b, this is unchanged
        res += ">"  # point to b
        res += "["  # if b == 0, enter the following code
        res += "<+>[-]"  # a = 1, b=0
        res += "]"  # end of "loop"

        return res

    elif op == ">":
        # a, b, c, d

        code = ">>[-]"  # c = 0  (will hold res)
        code += ">[-]"  # d = 0
        code += "<<<"  # point to a

        code += "["  # while a != 0

        code += ">>[-]"  # c = 0
        code += "<"  # point to b
        code += "[>+>+<<-]>[<+>-]"  # copy b to d (via c)
        code += "+"  # c = 1 (will hold res)
        code += ">"  # point to d
        code += "["  # if d != 0
        code += "[-]"  # d = 0
        code += "<-"  # c = 0
        code += "<-"  # b -= 1
        code += ">>"  # point to d
        code += "]"  # end if

        code += "<<<"  # point to a
        code += "-"  # a -= 1

        code += "]"  # end while

        # move c to a
        code += ">>"  # point to c
        code += "[<<+>>-]"  # move c to a
        code += "<"  # point to b (next available cell)

        """
        x > y?


        res = 0
        while x != 0:
            res = 1
            if y != 0:
                res = 0
                y -= 1

            x -= 1
        """

        return code

    elif op == "<":
        # similar to >

        # a, b, c, d

        code = ">>[-]"  # c = 0  (will hold res)
        code += ">[-]"  # d = 0
        code += "<<"  # point to b

        code += "["  # while b != 0

        code += ">[-]"  # c = 0
        code += "<<"  # point to a
        code += "[>>+>+<<<-]>>[<<+>>-]"  # copy a to d (via c)
        code += "+"  # c = 1 (will hold res)
        code += ">"  # point to d
        code += "["  # if d != 0
        code += "[-]"  # d = 0
        code += "<-"  # c = 0
        code += "<<-"  # a -= 1
        code += ">>>"  # point to d
        code += "]"  # end if

        code += "<<"  # point to b
        code += "-"  # b -= 1

        code += "]"  # end while

        # move c to a
        code += "<"  # point to a
        code += "[-]"  # a = 0
        code += ">>"  # point to c
        code += "[<<+>>-]"  # move c to a
        code += "<"  # point to b (next available cell)

        """
        x < y?

        res = 0
        while y != 0:
            res = 1
            if x != 0:
                res = 0
                x -= 1

            y -= 1
        """

        return code

    elif op == "<=":
        # a, b, c, d

        code = ">>[-]+"  # c = 1  (will hold res)
        code += ">[-]"  # d = 0
        code += "<<<"  # point to a

        code += "["  # while a != 0

        code += ">>[-]"  # c = 0
        code += "<"  # point to b
        code += "[>+>+<<-]>[<+>-]"  # copy b to d (via c)
        code += ">"  # point to d
        code += "["  # if d != 0
        code += "[-]"  # d = 0
        code += "<+"  # c = 1
        code += "<-"  # b -= 1
        code += ">>"  # point to d
        code += "]"  # end if

        code += "<<<"  # point to a
        code += "-"  # a -= 1

        code += "]"  # end while

        # move c to a
        code += ">>"  # point to c
        code += "[<<+>>-]"  # move c to a
        code += "<"  # point to b (next available cell)

        """
        x <= y?


        res = 1
        while x != 0:
            res = 0

            if y != 0:
                res = 1
                y -= 1

            x -= 1
        """

        return code

    elif op == ">=":
        # similar to <=

        # a, b, c, d

        code = ">>[-]+"  # c = 1  (will hold res)
        code += ">[-]"  # d = 0
        code += "<<"  # point to b

        code += "["  # while b != 0

        code += ">[-]"  # c = 0
        code += "<<"  # point to a
        code += "[>>+>+<<<-]>>[<<+>>-]"  # copy a to d (via c)
        code += ">"  # point to d
        code += "["  # if d != 0
        code += "[-]"  # d = 0
        code += "<+"  # c = 1
        code += "<<-"  # a -= 1
        code += ">>>"  # point to d
        code += "]"  # end if

        code += "<<"  # point to b
        code += "-"  # b -= 1

        code += "]"  # end while

        # move c to a
        code += "<"  # point to a
        code += "[-]"  # a = 0
        code += ">>"  # point to c
        code += "[<<+>>-]"  # move c to a
        code += "<"  # point to b (next available cell)

        """
        x >= y?


        res = 1
        while y != 0:
            res = 0

            if x != 0:
                res = 1
                x -= 1

            y -= 1
        """

        return code

    elif op_token.type == Token.AND:
        # a, b, temp
        code = ">>[-]"  # zero temp
        code += "<<"  # point to a
        code += "["  # if a is non-zero

        code += ">"  # point to b
        code += "["  # if b is non-zero
        code += ">+"  # temp = 1
        code += "<[-]"  # zero b
        code += "]"  # end if

        code += "<"  # point to a
        code += "[-]"  # zero a
        code += "]"  # end if

        code += ">>"  # point to temp
        code += "["  # if non zero
        code += "<<+"  # a = 1
        code += ">>-"  # temp = 0
        code += "]"  # end if

        code += "<"  # point to b (next available cell)

        return code

    elif op_token.type == Token.OR:
        # a, b, temp
        code = ">>[-]"  # zero temp
        code += "<<"  # point to a
        code += "["  # if a is non-zero

        code += ">"  # point to b
        code += "[-]"  # zero b
        code += ">"  # point to temp
        code += "+"  # temp = 1
        code += "<<"  # point to a
        code += "[-]"  # zero a
        code += "]"  # end if

        code += ">"  # point to b
        code += "["  # if b is non-zero
        code += ">"  # point to temp
        code += "+"  # temp = 1
        code += "<"  # point to b
        code += "[-]"  # zero b
        code += "]"  # end if

        code += ">"  # point to temp
        code += "["  # if temp == 1
        code += "<<+"  # a = 1
        code += ">>"  # point to temp
        code += "-"  # zero temp
        code += "]"  # end if

        code += "<"  # point to b (next available cell)

        return code

    raise NotImplementedError


def get_print_string_code(string):
    code = "[-]"  # zero current cell
    code += ">[-]"  # zero next cell (will be used for loop counts)
    code += "<"  # point to original cell ("character" cell)

    prev_value = 0
    for i in range(len(string)):
        current_value = ord(string[i])

        code += get_set_cell_value_code(current_value, prev_value, zero_next_cell_if_necessary=False)
        code += "."

        prev_value = current_value

    return code


def assign_token_to_op_token(assign_token):
    assert assign_token.data in ["+=", "-=", "*=", "/=", "%="]

    assignment_map = {
        "+=": Token(Token.BINOP, data="+"),
        "-=": Token(Token.BINOP, data="-"),
        "*=": Token(Token.BINOP, data="*"),
        "/=": Token(Token.BINOP, data="/"),
        "%=": Token(Token.BINOP, data="%"),
    }

    op_token = assignment_map[assign_token.data]
    op_node = NodeToken(token=op_token)
    return op_node


def get_move_right_index_cells_code(compiler, current_pointer, node_index):
    # used for arrays
    # returns a code that evaluates the index, then moves the pointer right, <index> amount of cells
    # at the end of execution, the layout is:
    # 0  index next_available_cell (point to next available cell)

    # index, steps_taken_counter
    code = node_index.get_code(compiler, current_pointer)  # index
    code += "[-]"  # counter = 0
    code += "<"  # point to index

    code += "["  # while index != 0
    code += ">>"  # point to new_counter (one after current counter)
    code += "[-]"  # zero new_counter
    code += "<"  # move to old counter
    code += "+"  # add 1 to counter
    code += "[>+<-]"  # move old counter to new counter
    code += "<"  # point to old index
    code += "-"  # sub 1 from old index
    code += "[>+<-]"  # move old index to new index
    code += ">"  # point to new index
    code += "]"  # end while

    # old_index=0 new_index res (pointing to old index)
    code += ">>"  # point to res

    return code


def get_move_left_index_cell_code():
    # used for arrays
    # complement of "get_move_right_index_cells_code"
    # assumes the layout is:
    # value, index (pointing to index)
    # moves <index> cells left, and moving <value> along with it
    # in the end, point to one cell after <value> (which becomes the next available cell)

    # layout: res, index (pointing to index)
    code = "["  # while new_index != 0
    code += "<"  # point to res
    code += "[<+>-]"  # move res to the left
    code += ">"  # point to new_index
    code += "-"  # sub 1 from index
    code += "[<+>-]"  # move new_index to left
    code += "<"  # point to new index
    code += "]"  # end while

    # now res is at the desired cell, and we point to the next available cell

    return code


class Node:
    def __init__(self):
        pass

    def get_code(self, *args, **kwargs):
        pass


class NodeToken(Node):
    def __init__(self, left=None, token=None, right=None):
        Node.__init__(self)
        self.left = left
        self.right = right
        self.token = token

    def get_code(self, compiler, current_pointer, *args, **kwargs):
        # returns the code that evaluates the parse tree

        if self.token.type in [Token.NUM, Token.CHAR, Token.ID, Token.TRUE, Token.FALSE]:
            # its a literal (leaf)
            assert self.left is None and self.right is None
            return get_token_code(compiler, self.token, current_pointer)

        elif self.token.type in [Token.BINOP, Token.RELOP, Token.AND, Token.OR]:
            code = self.left.get_code(compiler, current_pointer)
            code += self.right.get_code(compiler, current_pointer + 1)
            code += "<<"  # point to the first operand

            code += get_op_between_literals_code(self.token)
            return code

        elif self.token.type == Token.ASSIGN:
            assert self.left.token.type == Token.ID

            if self.token.data == '=':
                # id = expression
                code = self.right.get_code(compiler, current_pointer)

                # create code to copy from evaluated expression to ID's cell
                code += "<"  # point to evaluated expression cell
                code += get_copy_to_variable_code(compiler, self.left.token.data, current_pointer)
                code += ">"  # point to next available cell

                return code

            else:
                assert self.token.data in ["+=", "-=", "*=", "/=", "%="]
                # id += expression
                # create a node for id + expression

                op_node = assign_token_to_op_token(self.token)
                op_node.left = self.left
                op_node.right = self.right

                # create a node for id = id + expression
                assignment_node = NodeToken(left=self.left, token=Token(type=Token.ASSIGN, data="="), right=op_node)

                return assignment_node.get_code(compiler, current_pointer)


class NodeUnaryPrefix(Node):
    def __init__(self, operation, literal, *kargs, **kwargs):
        Node.__init__(self)
        self.token_operation = operation
        self.node_literal = literal

    def get_code(self, compiler, current_pointer, *args, **kwargs):
        # unary prefix (!x or ++x)
        assert self.token_operation.type in [Token.NOT, Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]

        if self.token_operation.type == Token.NOT:
            code = self.node_literal.get_code(compiler, current_pointer)
            code += "<"  # point to operand
            code += get_unary_prefix_op_code(self.token_operation)

            return code
        else:
            # its INCREMENT or DECREMENT

            if isinstance(self.node_literal, NodeArrayGetElement):
                token_id, index_node = self.node_literal.token_id, self.node_literal.node_expression
                code = get_move_right_index_cells_code(compiler, current_pointer, index_node)

                offset_to_array = get_offset_to_variable(compiler, token_id.data, current_pointer + 2)
                # it is +2 because in "get_move_right_index_cells_code", we moved 2 extra cells to the right, for retrieving the value

                code += get_unary_prefix_op_code(self.token_operation, offset_to_array)

                code += "<"  # point to res
                code += "[<<+>>-]"  # move res to old "index cell"
                code += "<"  # point to new index cell

                code += get_move_left_index_cell_code()
                return code

            # the token to apply on must be an ID
            if isinstance(self.node_literal, NodeToken) is False:
                raise BFSemanticError("prefix operator %s can be applied to a variable only" % str(self.token_operation))

            if self.node_literal.token.type != Token.ID:
                raise BFSemanticError("prefix operator %s cannot be applied to %s, but to a variable only" % (str(self.token_operation), str(self.node_literal.token)))

            offset_to_ID = get_offset_to_variable(compiler, self.node_literal.token.data, current_pointer)
            return get_unary_prefix_op_code(self.token_operation, offset_to_ID)


class NodeUnaryPostfix(Node):
    def __init__(self, operation, literal, *kargs, **kwargs):
        Node.__init__(self)
        self.token_operation = operation
        self.node_literal = literal

    def get_code(self, compiler, current_pointer, *args, **kwargs):

        # its an unary postfix operation (x++)
        assert self.token_operation.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]

        if isinstance(self.node_literal, NodeArrayGetElement):
            token_id, index_node = self.node_literal.token_id, self.node_literal.node_expression
            code = get_move_right_index_cells_code(compiler, current_pointer, index_node)

            offset_to_array = get_offset_to_variable(compiler, token_id.data, current_pointer + 2)
            # it is +2 because in "get_move_right_index_cells_code", we moved 2 extra cells to the right, for retrieving the value

            code += get_unary_postfix_op_code(self.token_operation, offset_to_array)

            code += "<"  # point to res
            code += "[<<+>>-]"  # move res to old "index cell"
            code += "<"  # point to new index cell

            code += get_move_left_index_cell_code()
            return code

        # the token to apply on must be an ID
        if isinstance(self.node_literal, NodeToken) is False:
            raise BFSemanticError("postfix operator %s can be applied to a variable only" % str(self.token_operation))

        if self.node_literal.token.type != Token.ID:
            raise BFSemanticError("postfix operator %s cannot be applied to %s, but to a variable only" % (str(self.token_operation), str(self.node_literal.token)))

        offset_to_ID = get_offset_to_variable(compiler, self.node_literal.token.data, current_pointer)
        return get_unary_postfix_op_code(self.token_operation, offset_to_ID)


class NodeFunctionCall(Node):
    def __init__(self, code):
        Node.__init__(self)
        self.code = code

    def get_code(self, *args, **kwargs):
        return self.code


class NodeArrayElement(Node):
    def __init__(self, *kargs, **kwargs):
        Node.__init__(self)

    """
    the idea:
    1. evaluate index. it is known only in run time, so we need to perform a little trick
    2. move <index> steps to the right, while counting how many steps we moved so far
        hold an index, and a steps_counter, and move them to the right while decreasing index and increasing steps_counter
        e.g: 4,0 --> 3,1 --> 2,2 --> 1,3 --> 0,4
        (move right until index is 0. counter will hold the old index)
        this way we know we moved <index> steps, and know how many steps to go back when we are done
    3. move <offset from stack pointer to array> steps left, to get/set the relevant array element
        this offset is known at compilation time

    """


class NodeArrayGetElement(NodeArrayElement):
    def __init__(self, token_id, node_expression):
        Node.__init__(self)
        self.token_id = token_id
        self.node_expression = node_expression

    def get_code(self, compiler, current_pointer, *args, **kwargs):
        code = get_move_right_index_cells_code(compiler, current_pointer, self.node_expression)
        code += get_copy_from_variable_code(compiler, self.token_id.data, current_pointer + 2)
        # it is +2 because in "get_move_right_index_cells_code", we moved 2 extra cells to the right, for retrieving the value

        code += "<"  # point to res
        code += "[<<+>>-]"  # move res to old "index cell"
        code += "<"  # point to new index cell

        code += get_move_left_index_cell_code()
        return code


class NodeArraySetElement(NodeArrayElement):
    def __init__(self, token_id, node_expression_index, assign_token, node_expression_value):
        Node.__init__(self)
        self.token_id = token_id
        self.node_expression_index = node_expression_index

        if assign_token.data == "=":
            # id[exp] = expression

            self.assign_token = assign_token
            self.node_expression_value = node_expression_value

        else:
            # id[exp] += expression
            assert assign_token.data in ["+=", "-=", "*=", "/=", "%="]

            self.assign_token = Token(Token.ASSIGN, data="=")

            # create a node for id[exp] + expression
            op_node = assign_token_to_op_token(assign_token)
            op_node.left = NodeArrayGetElement(token_id, node_expression_index)
            op_node.right = node_expression_value

            self.node_expression_value = op_node

    def get_code(self, compiler, current_pointer, *args, **kwargs):
        # index, steps_taken_counter, value

        code = self.node_expression_index.get_code(compiler, current_pointer)
        code += "[-]"  # counter = 0
        code += ">"  # point to value cell
        code += self.node_expression_value.get_code(compiler, current_pointer + 2)
        code += "<<<"  # point to index

        code += "["  # while index != 0
        code += ">>>"  # point to new_value (one after current value)
        code += "[-]"  # zero new_value
        code += "<"  # move to old value
        code += "[>+<-]"  # move old value to new counter
        code += "<"  # point to old counter
        code += "+"  # increase old counter
        code += "[>+<-]"  # move old counter to new counter
        code += "<"  # point to old index
        code += "-"  # decrease old index
        code += "[>+<-]"  # move old index to new index
        code += ">"  # point to new index
        code += "]"  # end while

        code += ">>"  # point to value
        code += get_copy_to_variable_code(compiler, self.token_id.data, current_pointer + 2)
        # it is +2 because we moved 2 extra cells to the right, for pointing to value

        # layout: 0, idx, value (pointing to value)
        # create layout: value, idx
        code += "[<<+>>-]"  # move value to old "index" cell (which is now 0)

        # value, index (pointing to one after index)
        code += "<"  # point to index
        code += "["  # while index != 0
        code += "<"  # point to value
        code += "[<+>-]"  # move value to the left
        code += ">"  # point to index
        code += "-"  # sub 1 from index
        code += "[<+>-]"  # move index to left
        code += "<"  # point to index
        code += "]"  # end while

        # now value is at the desired cell, and we point to the next available cell

        return code


class Compiler:
    def __init__(self, code):
        self.tokens = analyze(code)
        self.current_token_index = 0
        self.ids_map_list = list()
        self.functions = dict()
        self.insert_library_functions()
        """
        ids_map_list is a list of named tuples. each tuple represents a scope, and holds 2 items:
            1. an index of the next available cell. (if we want to insert a new ID to the ids_map_list, it will be in that index)
            2. a dictionary that maps an ID (string) to an index - the cell where we hold that variable
        
        we use this list as a stack:
            when entering a scope, we insert a (available_cell, dictionary) to the BEGINNING of the list
            when exiting a scope, we pop the last inserted tuple (the one at the BEGINNING of the list)
            
        when declaring a variable in the current scope, we add it to the dictionary at the beginning of the list,
        and increase the 'next_available_cell' by 1
        when retrieving a variable, we go through the list and return the first occurrence that matches the ID
        
        functions is a dict of string function_name --> function named tuple
        """

    def get_id_index(self, ID):
        # given an id, goes through the ids map list and returns the index of the first ID it finds
        for i in range(len(self.ids_map_list)):
            ids_map = self.ids_map_list[i].IDs_dict
            if ID in ids_map:
                return ids_map[ID].cell_index
        raise BFSemanticError("ID '%s' does not exist" % ID)

    def insert_library_functions(self): # todo put print here too (and remove it from the TOKEN class)
        readint = create_function("readint", Token.INT, list(), get_readint_code())
        self.insert_function(readint)

        printint = create_function("printint", Token.VOID, [Token.INT], get_printint_code())
        self.insert_function(printint)

        reachar = create_function("readchar", Token.INT, list(), get_readchar_code())
        self.insert_function(reachar)

        printchar = create_function("printchar", Token.VOID, [Token.INT], get_printchar_code())
        self.insert_function(printchar)

    def advance_token(self, amount=1):
        self.current_token_index += amount

    def current_token(self):
        if self.current_token_index == len(self.tokens):
            return None
        else:
            return self.tokens[self.current_token_index]

    def token_at_index(self, index):
        assert index < len(self.tokens)
        return self.tokens[index]

    def next_token(self, next_amount=1):
        return self.token_at_index(self.current_token_index + next_amount)

    def find_matching(self, starting_index=None):
        """
        :return: the index of the token that matches the current token
        :param starting_index (optional) - the index of the token we want to match

        for example, if current token is {
        it returns the index of the matching }
        """
        if starting_index is None:
            starting_index = self.current_token_index

        tokens = self.tokens
        token_to_match = tokens[starting_index]
        if token_to_match.type == Token.LBRACE:
            inc = Token.LBRACE
            dec = Token.RBRACE
        elif token_to_match.type == Token.LBRACK:
            inc = Token.LBRACK
            dec = Token.RBRACK
        else:
            raise NotImplementedError(token_to_match.type)

        i = starting_index
        cnt = 0
        while i < len(tokens):
            if tokens[i].type == inc:
                cnt += 1
            elif tokens[i].type == dec:
                cnt -= 1

            if cnt == 0:
                return i

            i += 1

        raise Exception("did not find matching %s for %s at index %s" % (dec, inc, str(starting_index)))

    def add_ids_map(self):
        # first cell (index 0) is the return_value cell. every function assumes that such a cell exists.
        # therefore the first available_cell's index is 1
        next_available_cell = 1 if len(self.ids_map_list) == 0 else self.ids_map_list[0].next_available_cell

        ids_map = namedtuple("ids_map", ["next_available_cell", "IDs_dict"])
        ids_map.next_available_cell = next_available_cell
        ids_map.IDs_dict = dict()

        self.ids_map_list.insert(0, ids_map)

    def remove_ids_map(self):
        self.ids_map_list.pop(0)

    def insert_to_ids_map(self, variable):
        ids_map = self.ids_map_list[0]

        self.check_id_doesnt_exist(variable.name)

        variable.cell_index = ids_map.next_available_cell
        ids_map.next_available_cell += variable.size
        ids_map.IDs_dict[variable.name] = variable

    def size_of_variables_current_scope(self):
        variables_dict = self.ids_map_list[0].IDs_dict

        size = 0
        for variable in variables_dict.values():
            size += variable.size

        return size

    def increase_stack_pointer(self, amount=1):
        # sometimes it is needed to increase the stack pointer
        # for example, when compiling "if ... else ...", we need 2 temporary cells before the inner scope code of both the if and the else
        # another example - when evaluating expression list in function call, each expression is evaluated while pointing to a different cell
        # therefore, it is needed to "update" the stack pointer to represent the new pointer
        self.ids_map_list[0].next_available_cell += amount

    def decrease_stack_pointer(self, amount=1):
        self.ids_map_list[0].next_available_cell -= amount

    def current_stack_pointer(self):
        return self.ids_map_list[0].next_available_cell

    def create_variable_from_definition(self, index=None, advance_tokens=False):
        """
        processes the variable definition at index, and returns the variable named tuple
        if index is None, then assumes we start at the current_token_index
        if advance_tokens is True, then modifies current_token_index accordingly using self.advance_token()
        """

        if index is None:
            index = self.current_token_index

        assert self.tokens[index].type == Token.INT

        self.check_next_tokens_are([Token.ID], starting_index=index)
        ID = self.tokens[index + 1].data
        type = Token.INT

        if advance_tokens:
            self.advance_token(amount=2)  # skip INT ID

        if self.tokens[index + 2].type == Token.LBRACK:
            self.check_next_tokens_are([Token.LBRACK, Token.NUM, Token.RBRACK], starting_index=index + 1)
            size = int(self.tokens[index + 3].data, 16) if self.tokens[index + 3].data.startswith("0x") else int(self.tokens[index + 3].data)

            if advance_tokens:
                self.advance_token(amount=3)  # skip LBRACK NUM RBRACK
        else:
            size = 1

        variable = create_variable(ID, type, size)
        return variable

    def insert_scope_variables_into_ids_map(self):
        # go through all the variable definitions in this scope (not including sub-scopes), and add them to the ids map
        # move the pointer to the next available cell (the one after the last variable declared in this scope)

        assert self.current_token().type == Token.LBRACE
        self.advance_token()

        i = self.current_token_index
        while i < len(self.tokens):
            token = self.tokens[i]

            if token.type == Token.INT:
                if self.tokens[i-2].type != Token.FOR:  # if it is not a definition inside a FOR statement (for (int i = 0...))
                    variable = self.create_variable_from_definition(index=i)
                    self.insert_to_ids_map(variable)

            elif token.type == Token.LBRACE:
                i = self.find_matching(starting_index=i)

            elif token.type == Token.RBRACE:
                break  # we have reached the end of the scope

            i += 1

        return ">" * self.size_of_variables_current_scope()  # advance pointer to the next available cell

    def enter_scope(self):
        # create an ids map to the current scope, and then inserts the scope variables into it
        self.add_ids_map()
        return self.insert_scope_variables_into_ids_map()

    def exit_scope(self):
        # remove the ids map of the current scope
        # return pointer to the previous scope's next available cell
        code = "<" * self.size_of_variables_current_scope()
        self.remove_ids_map()
        return code

    def enter_function_scope(self, parameters):
        # make room for return_value cell
        # create an ids map to the current function scope
        # insert parameters into the ids map
        # insert scope variables into the ids map

        self.add_ids_map()
        for parameter in parameters:
            self.insert_to_ids_map(parameter)

        code = '>'  # skip return_value_cell
        code += self.insert_scope_variables_into_ids_map()
        # this inserts scope variables AND moves pointer right, with the amount of BOTH parameters and scope variables

        return code

    def check_next_tokens_are(self, tokens_list, starting_index=None):
        if starting_index is None:
            starting_index = self.current_token_index

        # used for "assertion" and print a nice message to the user
        if starting_index + len(tokens_list) >= len(self.tokens):
            raise BFSyntaxError("Expected %s after %s" % (str(tokens_list), str(self.tokens[starting_index])))
        for i in range(0, len(tokens_list)):
            if self.tokens[starting_index + 1 + i].type != tokens_list[i]:
                raise BFSyntaxError("Expected %s after %s" % (str(tokens_list[i]), [str(t) for t in self.tokens[starting_index: starting_index+1+i]]))

    def check_current_tokens_are(self, tokens_list):
        self.check_next_tokens_are(tokens_list, starting_index=self.current_token_index - 1)

    def check_id_doesnt_exist(self, ID):
        # make sure that the id does not exist in the current scope
        # used when defining a variable
        if ID in self.ids_map_list[0].IDs_dict:
            raise BFSemanticError("ID %s is already defined" % ID)

    def check_function_exists(self, function_name, parameters_amount):
        if function_name not in self.functions:
            raise BFSemanticError("Function '%s' is undefined" % function_name)

        function = self.functions[function_name]
        if len(function.parameters) != parameters_amount:
            raise BFSemanticError("Function '%s' has %s parameters (called it with %s)" % (function.name, len(function.parameters), parameters_amount))

    # =================
    # compilation rules
    # =================

    # expression
    def function_call(self):
        # function_call: ID LPAREN expression_list RPAREN
        # returns function's CODE

        assert self.current_token().type == Token.ID
        function_name = self.current_token().data
        self.advance_token()  # skip ID

        self.increase_stack_pointer()  # evaluate expression list at one cell ahead, (after return_value_cell)
        parameters_code, parameters_amount = self.compile_expression_list()
        self.decrease_stack_pointer()

        self.check_function_exists(function_name, parameters_amount)
        function_to_call = self.functions[function_name]

        code = '[-]>'  # return_value_cell=0
        code += parameters_code  # after this we point to one after the last parameter
        code += "<" * len(function_to_call.parameters)  # point back to first parameter
        code += "<"  # point to return_value_cell

        code += function_to_call.code  # after this we point to return value
        code += ">"  # point to next available cell (one after return value)
        return code

    def literal(self):
        # literal: NUM | CHAR | ID | ID[expression] | TRUE | FALSE | function_call | ( expression )
        token = self.current_token()

        if token.type == Token.ID and self.next_token().type == Token.LPAREN:
            return NodeFunctionCall(code=self.function_call())

        if token.type == Token.ID and self.next_token().type == Token.LBRACK:
            self.advance_token(amount=2)  # skip ID LBRACK
            exp = self.expression()
            self.check_current_tokens_are([Token.RBRACK])
            self.advance_token()  # skip RBRACK

            return NodeArrayGetElement(token, exp)

        if token.type in [Token.NUM, Token.CHAR, Token.ID, Token.TRUE, Token.FALSE]:
            self.advance_token()
            return NodeToken(token=token)

        if token.type != Token.LPAREN:
            raise BFSyntaxError("Unexpected '%s'. expected literal (NUM | ID | ID[expression] | TRUE | FALSE | function_call | ( expression ))" % str(token))

        # ( expression )
        self.check_current_tokens_are([Token.LPAREN])
        self.advance_token()  # skip LPAREN
        exp = self.expression()
        self.check_current_tokens_are([Token.RPAREN])
        self.advance_token()  # skip RPAREN

        return exp

    def unary_postfix(self):
        # unary_postfix: literal ( ++ | -- | UNARY_MULTIPLICATIVE)?

        literal = self.literal()
        token = self.current_token()

        if token.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:
            self.advance_token()
            new_node = NodeUnaryPostfix(operation=token, literal=literal)
            return new_node
        else:
            return literal

    def unary_prefix(self):
        # unary_prefix:  ( (!)* unary_prefix ) | ( ( ++ | -- | UNARY_MULTIPLICATIVE) literal ) | unary_postfix

        token = self.current_token()

        if token.type == Token.NOT:
            self.advance_token()
            unary_prefix = self.unary_prefix()

            new_node = NodeUnaryPrefix(operation=token, literal=unary_prefix)
            return new_node

        elif token.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:
            self.advance_token()
            literal = self.literal()

            new_node = NodeUnaryPrefix(operation=token, literal=literal)
            return new_node

        else:
            return self.unary_postfix()

    def multiplicative(self):
        # multiplicative: unary_prefix ((MUL|DIV|MOD) unary_prefix)*

        n = self.unary_prefix()

        token = self.current_token()
        while token is not None and token.type == Token.BINOP and token.data in ["*", "/", "%"]:
            self.advance_token()
            next_factor = self.unary_prefix()

            new_node = NodeToken(token=token, left=n, right=next_factor)
            n = new_node

            token = self.current_token()

        return n

    def additive(self):
        # additive: multiplicative ((PLUS|MINUS) multiplicative)*
        n = self.multiplicative()

        token = self.current_token()
        while token is not None and token.type == Token.BINOP and token.data in ["+", "-"]:
            self.advance_token()
            next_term = self.multiplicative()

            new_node = NodeToken(token=token, left=n, right=next_term)
            n = new_node

            token = self.current_token()

        return n

    def relational(self):
        # relational: additive (==|!=|<|>|<=|>= additive)?
        a = self.additive()

        token = self.current_token()
        if token.type != Token.RELOP:  # just an arithmetic expression
            return a

        self.advance_token()
        b = self.additive()

        new_node = NodeToken(token=token, left=a, right=b)
        return new_node

    def logical_and(self):
        # logical_and: relational (&& relational)*

        n = self.relational()

        token = self.current_token()
        while token is not None and token.type == Token.AND:
            self.advance_token()
            next_relational = self.relational()

            new_node = NodeToken(token=token, left=n, right=next_relational)
            n = new_node

            token = self.current_token()

        return n

    def logical_or(self):
        # logical_or: logical_and (|| logical_and)*

        n = self.logical_and()

        token = self.current_token()
        while token is not None and token.type == Token.OR:
            self.advance_token()
            next_and = self.logical_and()

            new_node = NodeToken(token=token, left=n, right=next_and)
            n = new_node

            token = self.current_token()

        return n

    def assignment(self):
        # assignment: ID ASSIGN expression | ID LBRACK expression RBRACK ASSIGN expression | logical_or

        if self.current_token().type == Token.ID and self.next_token().type == Token.ASSIGN:
            # ID ASSIGN expression

            id_token = self.current_token()
            assign_token = self.next_token()
            self.advance_token(amount=2)  # skip ID ASSIGN

            expression_node = self.expression()

            new_node = NodeToken(left=NodeToken(token=id_token), token=assign_token, right=expression_node)
            return new_node

        elif self.current_token().type == Token.ID and self.next_token().type == Token.LBRACK and \
                self.tokens[self.find_matching(self.current_token_index+1)+1].type == Token.ASSIGN:
            # ID LBRACK expression1 RBRACK ASSIGN expression2
            id_token = self.current_token()
            self.advance_token(amount=2)  # skip ID [
            exp1 = self.expression()
            self.check_current_tokens_are([Token.RBRACK, Token.ASSIGN])
            assign_token = self.next_token()
            self.advance_token(amount=2)  # skip ] ASSIGN
            exp2 = self.expression()

            return NodeArraySetElement(id_token, exp1, assign_token, exp2)
        else:
            # logical or
            return self.logical_or()

    def expression(self):
        # expression: assignment
        return self.assignment()

    def compile_expression(self):
        # parses mathematical expressions (+-*/ ())
        # increments/decrements (++, --)
        # relative operations (==, !=, <, >, <=, >=)
        # logical operations (!, &&, ||)
        # assignment (=, +=, -=, *=, /=, %=)
        # this is implemented using a Node class that represents a parse tree

        """
        (used reference: https://introcs.cs.princeton.edu/java/11precedence/)
        order of operations (lowest precedence to highest precedence)
            assignment (=, +=, -=, *=, /=, %=)
            logical_or (||)
            logical_and (&&)
            relational (==|!=|<|>|<=|>=)
            additive (+-)
            multiplicative (*/%)
            unary_prefix (!, ++, --)
            unary_postfix (++, --)

        expression: assignment
        assignment: ID (=|+=|-=|*=|/=|%=) expression | logical_or
        logical_or: logical_and (|| logical_and)*
        logical_and: relational (&& relational)*
        relational: additive (==|!=|<|>|<=|>= additive)?
        additive: multiplicative ((PLUS|MINUS) multiplicative)*
        multiplicative: unary_prefix ((MUL|DIV|MOD) unary_prefix)*
        unary_prefix:  ( (!)* unary_prefix ) | ( ( ++ | -- ) literal ) | unary_postfix
        unary_postfix: literal ( ++ | -- )?
        literal: NUM | CHAR | ID | ID[expression] | TRUE | FALSE | function_call | ( expression )
        """

        parse_tree = self.expression()
        expression_code = parse_tree.get_code(self, self.current_stack_pointer())
        return expression_code

    # functions-related
    def get_function_parameters_declaration(self):
        # parameters declaration: LPAREN (int ID (LBRACK NUM RBRACK)? (COMMA int ID)*)? RPAREN
        # return list of parameters (named tuples (type, ID)) at the same order as declared

        assert self.current_token().type == Token.LPAREN
        self.advance_token()

        res = list()

        token = self.current_token()
        while token.type != Token.RPAREN:
            if token.type != Token.INT:
                raise BFSemanticError("Only int type is supported as a function parameter, and not '%s'" % token.type)

            parameter = self.create_variable_from_definition(advance_tokens=True)
            res.append(parameter)

            if self.current_token().type == Token.COMMA:
                self.advance_token()
            else:
                self.check_current_tokens_are([Token.RPAREN])

            token = self.current_token()

        self.advance_token()  # skip RPAREN
        return res

    def compile_expression_list(self):
        # expression_list: ( expression (COMMA expression)* )?

        # returns a tuple:
        # code that evaluates the parameters passed to function
        # amount of expressions evaluated by that code

        # the code evaluates them from left to right, and puts them on the "stack" in that order
        # then the pointer points to the next available cell
        assert self.current_token().type == Token.LPAREN
        self.advance_token()

        code = ''
        amount_of_expressions = 0

        token = self.current_token()
        while token.type != Token.RPAREN:
            code += self.compile_expression()
            self.increase_stack_pointer()
            amount_of_expressions += 1

            if self.current_token().type == Token.COMMA:
                self.advance_token()
            else:
                self.check_current_tokens_are([Token.RPAREN])
            token = self.current_token()

        self.advance_token()  # skip RPAREN
        self.decrease_stack_pointer(amount=amount_of_expressions)
        return code, amount_of_expressions

    def compile_return(self):
        # this assumes that the return is the last statement in the function

        self.advance_token()  # skip return
        if self.current_token().type == Token.SEMICOLON:
            # return;
            self.advance_token()  # skip ;
            return ''  # nothing to do

        # return exp;
        expression_code = self.compile_expression()
        self.check_current_tokens_are([Token.SEMICOLON])

        self.advance_token()  # skip ;

        code = expression_code  # after this, we point to next available cell
        code += "<"  # point to value to return
        code += get_move_to_return_value_cell_code(self.current_stack_pointer())

        return code

    # statements
    def compile_expression_as_statement(self):
        # this expression can be used as a statement.
        # e.g: x+=5;  or  x++ or ++x;

        assert self.current_token().type in [Token.ID, Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]

        code = self.compile_expression()
        self.check_current_tokens_are([Token.SEMICOLON])
        self.advance_token()  # skip ;

        code += "<"  # discard the expression's value

        return code

    def compile_print_string(self):
        self.check_next_tokens_are([Token.LPAREN, Token.STRING, Token.RPAREN, Token.SEMICOLON])
        self.advance_token(amount=2)  # skip print (
        string_to_print = self.current_token().data
        self.advance_token(amount=3)  # skip string ) ;

        code = get_print_string_code(string_to_print)
        return code

    def compile_function_call_statement(self):
        # compile statement: function_call SEMICOLON
        function_call_code = self.function_call()

        self.check_current_tokens_are([Token.SEMICOLON])
        self.advance_token()  # skip ;

        code = function_call_code  # at this point, we point to one after the return value
        code += "<"  # discard return value
        return code

    def compile_if(self):
        self.check_next_tokens_are([Token.LPAREN])
        self.advance_token(amount=2)  # skip to after LPAREN

        expression_code = self.compile_expression()
        self.check_current_tokens_are([Token.RPAREN, Token.LBRACE])
        self.advance_token()  # point to LBRACE

        token_after_RBRACE = self.token_at_index(self.find_matching() + 1)
        if token_after_RBRACE.type != Token.ELSE:
            # if without else

            inside_if_code = self.compile_scope()

            code = expression_code  # evaluate expression
            code += "<"  # point to the expression
            code += "["  # if it is 0, jump to after the <if> scope
            code += inside_if_code  # <if> scope code. after this code, pointer points to the next available cell, which is the expression's cell
            code += "[-]"  # zero the expression
            code += "]"  # after <if> scope

            return code

        # if ... else ...
        # need to use 2 temp cells
        # expression, execute_else

        self.increase_stack_pointer(amount=2)
        inside_if_code = self.compile_scope()

        self.check_current_tokens_are([Token.ELSE, Token.LBRACE])
        self.advance_token()  # skip the 'else'
        inside_else_code = self.compile_scope()
        self.decrease_stack_pointer(amount=2)

        code = expression_code  # evaluate expression. after this we point to "execute_else" cell
        code += "[-]+"  # execute_else = 1
        code += "<"  # point to the expression
        code += "["  # if it is non-zero
        code += ">-"  # execute_else = 0
        code += ">"  # point to next available cell
        code += inside_if_code  # after this we point to the same cell (one after execute_else)
        code += "<<"  # point to expression
        code += "[-]"  # expression = 0
        code += "]"  # end if

        code += ">"  # point to execute_else
        code += "["  # if it is non-zero
        code += ">"  # point to next available cell
        code += inside_else_code  # after this we point to the same cell (one after execute_else)
        code += "<"  # point to execute_else
        code += "-"  # execute_else = 0
        code += "]"  # end if

        code += "<"  # point to next available cell (what used to be expression_code)

        return code

    def compile_while(self):
        self.check_next_tokens_are([Token.LPAREN])
        self.advance_token(amount=2)  # skip to after LPAREN

        expression_code = self.compile_expression()

        self.check_current_tokens_are([Token.RPAREN, Token.LBRACE])
        self.advance_token()  # i points to LBRACE

        inner_scope_code = self.compile_scope()

        code = expression_code  # evaluate expression
        code += "<"  # point to the expression
        code += "["  # if it is 0, jump to after the <while> scope
        code += inner_scope_code  # <while> scope code. after this code, pointer points to the next available cell. i.e one after the expression
        code += expression_code  # re-evaluate the expression
        code += "<"  # point to the expression
        code += "]"  # after <if> scope

        return code

    def compile_for(self):
        # for (statement expression; expression) { inner_scope_code }
        # (the statement/second expression/inner_scope_code can be empty)

        """
            <for> is a special case of scope
            the initial code (int i = 0;) is executed INSIDE the scope, but BEFORE the LBRACE
            so we manually compile the scope instead of using self.compile_scope():

            we first create an ids map, and in the case that there is a variable definition inside the <for> definition:
            we manually insert the ID into the ids map, and move the pointer to the right once, to make room for it
            (this needs to be done before the <for> definition's statement)
            next, inside the for's scope {}:
            after calling insert_scope_variables_into_ids_map, we move the pointer to the left once, since it counts the ID we entered manually as well
            after calling exit_scope, we move the pointer to the right, since it counts the the ID we entered manually, and we dont want it to be discarded after every iteration
            finally, at the end of the <for> loop, we move the pointer once to the left, to discard the variable we defined manually
        """

        self.check_current_tokens_are([Token.FOR, Token.LPAREN])
        self.advance_token(amount=2)  # skip for (

        manually_inserted_variable_in_for_definition = False
        code = ''

        # =============== enter FOR scope ===============
        self.add_ids_map()
        # ===============================================

        if self.current_token().type == Token.INT:
            # we are defining a variable inside the for statement definition (for (int i = 0....))
            variable = self.create_variable_from_definition(advance_tokens=False)
            self.insert_to_ids_map(variable)
            manually_inserted_variable_in_for_definition = True
            code += ">" * variable.size

        initial_statement = self.compile_statement()

        condition_expression = self.compile_expression()
        self.check_current_tokens_are([Token.SEMICOLON])
        self.advance_token()  # skip ;

        if self.current_token().type == Token.RPAREN:
            modification_expression = ""  # no modification expression
        else:
            modification_expression = self.compile_expression()
            modification_expression += "<"  # discard expression value
        self.check_current_tokens_are([Token.RPAREN])
        self.advance_token()  # skip )

        # compiling <for> scope inside { }:
        self.check_current_tokens_are([Token.LBRACE])
        inner_scope_code = self.insert_scope_variables_into_ids_map()
        if manually_inserted_variable_in_for_definition:
            inner_scope_code += "<"
        inner_scope_code += self.compile_scope_statements()
        # =============== exit FOR scope ===============
        inner_scope_code += self.exit_scope()
        if manually_inserted_variable_in_for_definition:
            inner_scope_code += ">"
        # ===============================================

        code += initial_statement
        code += condition_expression  # evaluate expression
        code += "<"  # point to the expression
        code += "["  # if it is 0, jump to after the <for> scope
        code += inner_scope_code  # <for> scope code
        code += modification_expression
        code += condition_expression  # re-evaluate the expression
        code += "<"  # point to the expression
        code += "]"  # after <for> scope

        if manually_inserted_variable_in_for_definition:
            code += "<"

        return code

    def compile_statement(self):
        # returns code that performs the current statement
        # at the end, the pointer points to the same location it pointed before the statement was executed

        token = self.current_token()

        if token.type == Token.INT:  # INT ID ([NUM])? (= EXPRESSION)? ;
            self.check_next_tokens_are([Token.ID])
            self.advance_token()  # skip "INT" (now points to ID)
            assert self.current_token().type == Token.ID

            if self.next_token().type == Token.SEMICOLON:  # INT ID SEMICOLON
                self.advance_token(2)  # skip ID SEMICOLON
                return ''  # no code is generated here. code was generated for defining this variable when we entered the scope

            elif self.next_token().type == Token.LBRACK and self.next_token(next_amount=4).type == Token.SEMICOLON:  # INT ID LBRACK NUM RBRACK SEMICOLON
                self.advance_token(5)  # skip ID LBRACK NUM RBRACK SEMICOLON
                return ''  # no code is generated here. code was generated for defining this variable when we entered the scope

            else:
                return self.compile_expression_as_statement()

        elif token.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:  # ++ID;
            return self.compile_expression_as_statement()

        elif token.type == Token.ID:
            if self.next_token().type in [Token.ASSIGN, Token.LBRACK, Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:
                # ID ASSIGN expression; or ID[expression] ASSIGN expression; or ID++;
                return self.compile_expression_as_statement()
            elif self.next_token().type == Token.LPAREN:  # ID(...);  (function call)
                return self.compile_function_call_statement()
            raise BFSyntaxError("Unexpected '%s' after '%s'. Expected '=|+=|-=|*=|/=|%%=' (assignment), '++|--' (modification) or '(' (function call)" % (str(self.next_token()), str(token)))

        elif token.type == Token.PRINT:  # print(string);
            return self.compile_print_string()  # todo remove it here and insert it into library functions.
            # todo probably means writing string on the stack. implement after implementing arrays/structs

        elif token.type == Token.IF:  # if (expression) {inner_scope} (else {inner_scope})?
            return self.compile_if()

        elif token.type == Token.LBRACE:
            return self.compile_scope()

        elif token.type == Token.WHILE:  # while (expression) {inner_scope}
            return self.compile_while()

        elif token.type == Token.RETURN:
            return self.compile_return()

        elif token.type == Token.FOR:
            return self.compile_for()

        elif token.type == Token.SEMICOLON:
            #  empty statement
            self.advance_token()  # skip ;
            return ""

        raise NotImplementedError(token.type)

    def compile_scope_statements(self):
        tokens = self.tokens

        code = ''
        while self.current_token() is not None:

            if self.current_token().type == Token.RBRACE:
                # we reached the end of our scope
                self.advance_token()  # skip RBRACE
                return code
            else:
                code += self.compile_statement()

        # should never get here
        raise BFSyntaxError("expected } after the last token in scope " + tokens[-1].type)

    def compile_scope(self):
        assert self.current_token().type == Token.LBRACE

        code = self.enter_scope()
        code += self.compile_scope_statements()
        code += self.exit_scope()

        return code

    # functions
    def insert_function(self, function):
        self.functions[function.name] = function

    def compile_function_scope(self, parameters):
        #  returns code for the current function
        #  parameters is a list of parameters, in the order of their declaration
        #  will be inserted to the new scope prior to the scope's compilation

        """
            example layout:

                int foo(int a, int b) {
                    int x;
                    int y;
                    return 5;
                }

                int main() {
                    int n;
                    foo(1, 2);
                }

                main_return_value n foo_return_value a=1 b=2 x y

                calling convention:
                caller responsibility: make room for return_value (and zero its cell), place parameters, point to return_value cell
                callee responsibility: put return value in return_value cell and point to it (thus "cleaning" parameters)
                    can assume that there is a zerod cell at index 0 (return_value_cell) (therefore ids_map starts at index 1)
                    can assume that the next cells match your parameters
                    assumes that initially, the pointer points to the first cell (return_value_cell).
                    therefore begin with '>' * (1 + parameters + scope variables)
        """

        assert self.current_token().type == Token.LBRACE

        code = self.enter_function_scope(parameters)
        code += self.compile_scope_statements()
        code += self.exit_scope()
        code += "<"  # point to return_value_cell

        return code

    def compile_function(self):
        # function: (INT | VOID) ID LPAREN expression_list RPAREN LBRACE statements RBRACE
        # returns function named tuple

        if self.current_token().type not in [Token.VOID, Token.INT]:
            raise BFSemanticError("Function return type can be either void or int, and not '%s'" % str(self.current_token()))

        self.check_next_tokens_are([Token.ID, Token.LPAREN])

        function_return_type = self.current_token()
        self.advance_token()  # skip return type
        function_name = self.current_token().data
        self.advance_token()  # skip ID
        parameters = self.get_function_parameters_declaration()
        function_code = self.compile_function_scope(parameters)

        function = create_function(function_name, function_return_type, parameters, function_code)
        return function

    def compile_functions(self):
        # functions: (function)*

        token = self.current_token()
        while token is not None and token.type in [Token.VOID, Token.INT]:
            function = self.compile_function()
            self.insert_function(function)
            token = self.current_token()

    def compile(self):
        self.compile_functions()

        if self.current_token() is not None:  # we have not reached the last token
            untouched_tokens = [str(t) for t in self.tokens[self.current_token_index:]]
            raise BFSyntaxError("Did not reach the end of the code (starting at index %s):\n%s" % (str(self.current_token_index+1), untouched_tokens))

        self.check_function_exists("main", 0)

        return self.functions["main"].code


def compile(code):
    """
    :param code:  C-like code
    :return code:  Brainfuck code
    """
    compiler = Compiler(code)
    brainfuck_code = compiler.compile()
    return brainfuck_code


if __name__ == '__main__':
    print("This file cannot be directly run")
    print("Please import it and use the 'compile' function")
    print("Which receives a C-like code (string) and returns Brainfuck code (string)")
