from .Exceptions import BFSyntaxError, BFSemanticError
from .Token import Token
from functools import reduce

"""
This file holds functions that generate general Brainfuck code
And general functions that are not dependent on other objects
"""


# =================
#  Brainfuck code
# =================


def get_set_cell_value_code(new_value, previous_value, zero_next_cell_if_necessary=True):
    # this function returns a code that sets the current cell's value to new_value,
    # given that its previous value is previous_value

    # it may return the "naive" way, of "+"/"-" usage, <offset> times
    # and it may return an optimization using loops, by using the next cell as a loop counter
    # if zero_next_cell_if_necessary is set to False, it assumes that the next cell is already 0

    # after the code of this function is executed, the pointer will point to the original cell
    # this function returns the shorter code between "naive" and "looped"

    def get_char(value):
        return "+" if value > 0 else "-"

    offset = new_value - previous_value
    char = get_char(offset)
    is_negative = offset < 0
    offset = abs(offset)

    # "naive" code is simply +/-, <offset> times
    naive = char * offset

    # "looped" code is "[<a> times perform <b> adds/subs] and then <c> more adds/subs"
    def get_abc(offset):
        # returns a,b,c such that a*b+c=offset and a+b+c is minimal

        min_a, min_b, min_c = offset, 1, 0
        min_sum = offset + 1

        left = 1
        right = offset // 2 - 1

        while right >= left:
            a, b = left + 1, right + 1
            c = offset - a * b
            curr_sum = abs(a) + abs(b) + abs(c)

            if curr_sum < min_sum:
                min_a, min_b, min_c = a, b, c
                min_sum = curr_sum

            if a * b > offset:
                right -= 1
            else:
                left += 1

        return min_a, min_b, min_c

    a, b, c = get_abc(offset)
    looped = ">"  # point to next cell (loop counter)
    if zero_next_cell_if_necessary:
        looped += "[-]"  # zero it if necessary
    looped += "+" * a  # set loop counter
    looped += "[<" + char * abs(b) + ">-]"  # sub 1 from counter, perform b actions
    looped += "<"  # point to "character" cell
    looped += get_char(-c if is_negative else c) * abs(c)  # c more actions

    if len(naive) > len(looped):
        return looped
    else:
        return naive


def get_move_to_offset_code(offset):
    # returns code that moves value from current pointer to cell at offset <offset> to the left
    # after this, the pointer points to the original cell, which is now the next available cell

    code = "<" * offset  # point to destination
    code += "[-]"  # zero destination
    code += ">" * offset  # point to source cell
    code += "[" + "<" * offset + "+" + ">" * offset + "-]"  # increase destination, zero source
    # point to next free location (source, which is now zero)

    return code


def get_copy_to_offset_code(offset):
    # returns code that copies value from current pointer to cell at offset <offset> to the left
    # after this, the pointer points to the original cell, which remains unchanged

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


def get_copy_to_variable_code(ids_map_list, ID_token, current_pointer):
    # returns code that copies value from current pointer to cell of the variable ID
    # after this, the pointer points to the original cell, which remains unchanged

    offset = get_offset_to_variable(ids_map_list, ID_token, current_pointer)
    return get_copy_to_offset_code(offset)


def get_move_to_return_value_cell_code(return_value_cell, current_stack_pointer):
    # returns code that moves value from current pointer to return_value cell
    # after this, the pointer points to the original cell, which is now the next available cell

    # we need to move it <current_stack_pointer - return_value_cell> cells left
    return get_move_to_offset_code(current_stack_pointer - return_value_cell)


def unpack_multidimensional_literal_tokens_to_array_dimensions(ID_token, array_dimensions, literal_tokens_list):
    if len(array_dimensions) == 0:
        raise BFSemanticError("Tried to initialize array %s with too many nested sub-arrays" % ID_token)
    if len(literal_tokens_list) > array_dimensions[0]:
        raise BFSemanticError("Tried to initialize array %s dimension %s with too many elements (%s)"
                              % (ID_token, str(array_dimensions), str(len(literal_tokens_list))))

    result = []
    for element in literal_tokens_list:
        if isinstance(element, list):
            # recursively unpack the list with the sub-dimension of the sub-array
            # E.g if we have arr[3][3][3] and then this call will fill [3][3]=9 elements
            result.extend(unpack_multidimensional_literal_tokens_to_array_dimensions(ID_token, array_dimensions[1:], element))
        else:
            result.append(element)
            if len(array_dimensions) > 1:
                dimension_size = dimensions_to_size(array_dimensions[1:])  # current size we need to fill
                result.extend([Token(Token.NUM, 0, 0, "0")] * (dimension_size - 1))  # fill missing elements in this dimension with zeros

    dimension_size = dimensions_to_size(array_dimensions)  # current size we need to fill
    result.extend([Token(Token.NUM, 0, 0, "0")] * (dimension_size-len(result)))  # fill the result with zeros
    return result


def unpack_literal_tokens_to_array_dimensions(ID_token, array_dimensions, literal_tokens_list):
    # gets array dimensions and list of (list of list of...) literal tokens to initialize it with
    # returns one long list of literal tokens that can be used to initialize the array as a one dimensional array
    # if there are missing literals to fill the entire array, then fill the blanks with NUM 0
    # E.g if the code is int arr[3][3][3] = {{1,2,3}, {}, {7, 8}}
    # Then this function receives ([3,3,3] and [[1,2,3],[],[7,8]]) and returns [1,2,3,0,0,0,7,8,0] (all are tokens)

    array_size = dimensions_to_size(array_dimensions)  # current size we need to fill
    if all(not isinstance(element, list) for element in literal_tokens_list):
        # special case - if all elements are literals, then we allow assigning them as-is and not care about dimensions
        # E.g if we have arr[3][3][3] = {1,2,3,4} then return [1,2,3,4,0,0,0,0,0]
        unpacked_literals_list = literal_tokens_list + [Token(Token.NUM, 0, 0, "0")] * (array_size - len(literal_tokens_list))  # fill missing with zeros
    else:
        unpacked_literals_list = unpack_multidimensional_literal_tokens_to_array_dimensions(ID_token, array_dimensions, literal_tokens_list)

    if len(unpacked_literals_list) > array_size:
        raise BFSemanticError("Tried to initialize array %s with incompatible amount of literals."
                              " (array size is %s and literals size is %s)" % (ID_token, str(array_size), str(len(unpacked_literals_list))))
    assert len(unpacked_literals_list) == array_size
    return unpacked_literals_list


def get_copy_from_variable_code(ids_map_list, ID_token, current_pointer):
    # returns code that copies the value from cell of variable ID to current pointer, and then sets the pointer to the next cell

    offset = get_offset_to_variable(ids_map_list, ID_token, current_pointer)
    code = "[-]"  # res = 0
    code += ">[-]"  # temp (next cell) = 0
    code += "<" * (offset + 1)  # point to destination cell
    code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
    code += ">" * (offset + 1)  # point to temp
    code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
    # at this point we point to the next available cell, which is temp, which is now zero

    return code


def get_token_ID_code(ids_map_list, token, current_pointer):
    # generate code that evaluates the ID token at the current pointer, and sets the pointer to point to the next available cell
    return get_copy_from_variable_code(ids_map_list, token, current_pointer)


def get_literal_token_code(token):
    # generate code that evaluates the token at the current pointer, and sets the pointer to point to the next available cell
    if token.type == Token.NUM:
        value = get_NUM_token_value(token)
        code = "[-]"  # zero current cell
        code += get_set_cell_value_code(value, 0)  # set current cell to the num value
        code += ">"  # point to the next cell
        return code

    elif token.type == Token.CHAR:
        code = "[-]"  # zero current cell
        code += get_set_cell_value_code(ord(token.data), 0)  # set current cell to the char value
        code += ">"  # point to next cell
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

    raise NotImplementedError("Not implemented %s" % token)


def get_divmod_code(right_token=None):
    # given that the current pointer points to a, and the cell after a contains b,
    # (i.e the cells look like: --> a, b, ?, ?, ?, ?, ...)
    # returns a code that calculates divmod, and the cells look like this:
    # --> 0, b-a%b, a%b, a/b, 0, 0
    # and the pointer points to the first 0 (which is in the same cell as a used to be)
    ADD_DIVISION_BY_ZERO_CHECK = True

    if right_token is not None and right_token.type == Token.NUM:
        if get_NUM_token_value(right_token) == 0:
            raise BFSemanticError("Dividing by Zero, at %s" % right_token)

        ADD_DIVISION_BY_ZERO_CHECK = False

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

        code_inside_if = get_print_string_code("Error - Division by zero\n")
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


def get_bitwise_code(code_logic):
    # a, b, c, w, x, y, z, bit1, bitcounter, res
    # code_logic uses the cells y, z, and bit1. Where y is res and z and bit1 are the bits.
    # y is zero. z and bit1 should be zero after code_logic.

    code = ">" * 7  # point to bit1
    code += "[-]"  # zero bit1
    code += ">"  # point to bitcounter
    code += ">[-]<"  # zero res

    code += "[-]--------[++++++++"  # while bitcounter != 8:
    code += "<"
    code += "<[-]" * 5  # clear c, w, x, y, z
    code += "++"  # c = 2
    code += "<<"  # point to a

    code += "["  # while a != 0:
    code +=     "-"  # a -= 1
    code +=     ">>-"  # c -= 1
    code +=     "[>+>>+<<<-]>[<+>-]"  # copy c to y (using w)
    code +=     ">>"  # point to y
    code +=     ">>+<<"  # bit1 += 1

    code +=     "-["  # if y != 1:
    code +=         "<+"  # x += 1
    code +=         "<<++"  # c += 2 (c was 0)
    code +=         ">" * 5  # point to bit1
    code +=         "--"  # bit1 -= 2 (bit1 was 2)
    code +=         "<<"  # point to y
    code +=         "+"  # set y to 0
    code +=     "]"  # end if

    code +=     "<<<<<"  # point to a
    code += "]"  # end while

    code += ">>>>[<<<<+>>>>-]"  # move x to a (x is a/2)
    code += "<<[-]++"  # c = 2
    code += "<"  # point to b

    code += "["  # while b != 0:
    code +=     "-"  # b -= 1
    code +=     ">-"  # c -= 1
    code +=     "[>+>>+<<<-]>[<+>-]"  # copy c to y (using w)
    code +=     ">>"  # point to y
    code +=     ">+<"  # z += 1

    code +=     "-["  # if y != 1:
    code +=         ">--<"  # z -= 2 (z was 2)
    code +=         "<+"  # x += 1
    code +=         "<<++"  # c += 2 (c was 0)
    code +=         ">>>"  # point to y
    code +=         "+"  # set y to 0
    code +=     "]"

    code +=     "<<<<"  # point to b
    code += "]"  # end while

    # w is a % 2
    # x is a / 2

    code += ">>>[<<<+>>>-]"  # move x to b

    code += ">>"  # point to z
    code += code_logic  # pointer ends at bit1, z and bit1 should be 0 after code

    code += ">[<+<+>>-]<[>+<-]"  # copy bit to z (using bit1)

    # y = y << z
    code += "<"
    code += "["  # while z != 0:
    code += "<"  # point to y
    code += "[<+>-]"  # copy y to x
    code += "<[>++<-]"  # copy x to y * 2
    code += ">>-"  # z -= 1
    code += "]"

    code += "<"  # point to y
    code += "[>>>>+<<<<-]"  # res += y

    code += ">>>"  # point to bitcounter
    code += "-" * 7  # loop if bitcounter != 7

    code += "]"  # end while

    code += ">[<<<<<<<<<+>>>>>>>>>-]"  # move res to a
    code += "<<<<<<<<"  # point to b

    return code


def get_unary_prefix_op_code(token, offset_to_variable=None):
    # returns code that:
    # performs op on an operand that is at the current pointer
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
        # returns code that copies the value from the variable's cell at the given offset, and adds 1 to both the copied and the original cell
        assert offset_to_variable is not None
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "+"  # increase destination by 1
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * (offset + 1)  # point to temp
        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    elif token.type == Token.DECREMENT:
        # returns code that copies the value from the variable's cell at the given offset, and subtracts 1 from both the copied and the original cell
        assert offset_to_variable is not None
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "-"  # decrease destination by 1
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * (offset + 1)  # point to temp
        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    elif token.type == Token.UNARY_MULTIPLICATIVE:
        # returns code that copies the value from the variable's cell at the given offset, modifies both the copied and the original cell depending on the op
        assert offset_to_variable is not None
        offset = offset_to_variable

        if token.data in ["**", "//"]:
            code = "[-]"  # res = 0
            code += ">[-]"  # temp (next pointer) = 0
            code += "<" * (offset + 1)  # point to destination cell
            code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
            code += ">" * offset  # point to res
            code += ">"  # point to temp (**x, //x keep x the same)
            code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
            # at this point we point to the next available cell

            return code

        elif token.data == "%%":
            code = "[-]"  # res = 0
            code += "<" * offset  # point to destination cell
            code += "[-]"  # zero destination
            code += ">" * offset  # point to res
            code += ">"  # point the next available cell
            # at this point we point to the next available cell

            return code

        else:
            raise BFSyntaxError("Unexpected unary prefix %s" % str(token))

    elif token.type == Token.BITWISE_NOT:
        # a temp
        code = "[>+<-]"  # move a into temp
        code += ">"  # point to temp
        code += "+[<->-]"  # invert temp into a

        return code

    raise NotImplementedError


def get_unary_postfix_op_code(token, offset_to_variable):
    # returns code that:
    # performs op on operand that is at the current pointer
    # the result is placed in the cell of the operand
    # and the pointer points to the cell right after it (which becomes the next available cell)

    if token.type == Token.INCREMENT:
        # returns code that copies the value from the variable's cell at the given offset, and adds 1 to the original cell
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
        # returns code that copies the value from the variable's cell at the given offset, and subtracts 1 from the original cell
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
        # returns code that copies the value from the variable's cell at the given offset, and modifies the original cell depending on the operation
        offset = offset_to_variable

        code = "[-]"  # res = 0
        code += ">[-]"  # temp (next pointer) = 0
        code += "<" * (offset + 1)  # point to destination cell
        code += "[" + ">" * offset + "+>+" + "<" * (offset + 1) + "-]"  # increase res and temp, zero destination
        code += ">" * (offset + 1)  # point to temp

        if token.data in ["**", "//"]:
            pass  # x**, x// keeps x the same
        elif token.data == "%%":
            # at this point we zeroed x and we point to temp (next available cell)
            return code  # no need to copy anything back to destination - x%% modifies x to 0
        else:
            raise BFSyntaxError("Unexpected unary postfix %s" % str(token))

        code += "[" + "<" * (offset + 1) + "+" + ">" * (offset + 1) + "-]"  # copy temp back to destination
        # at this point we point to the next available cell, which is temp, which is now zero

        return code

    raise NotImplementedError


def get_op_between_literals_code(op_token, right_token=None):
    # returns code that:
    # performs op on 2 operands
    # the first operand is at current pointer, and the second operand is at current pointer + 1
    # the code can destroy second operand, and everything after it

    # the result is placed in the cell of the first operand
    # and the pointer points to the cell right after it (which becomes the next available cell)

    op = op_token.data
    if op == "+" or op == "-":
        code = ">[<" + op + ">-]"  # increase/decrease the first operand and decrease the second operand
        # the pointer now points to the next available cell, which is the second operand, which is 0

        return code

    elif op == "*":
        # a, b, temp1, temp2
        code = ">>[-]"  # temp1 = 0
        code += ">[-]"  # temp2 = 0
        code += "<<<"  # point to first operand
        code += "[>>>+<<<-]"  # move first operand to temp2
        code += ">>>"  # point to temp2

        # do in a loop: as long as temp2 != 0
        code += "["

        code += "<<"  # point to second operand
        code += "[<+>>+<-]"  # add it to first operand and temp1
        code += ">"  # point to temp1
        code += "[<+>-]"  # move it to second operand

        # end loop
        code += ">"  # point back to temp2
        code += "-"  # decrease temp2
        code += "]"

        code += "<<"  # point back to next available cell (second operand)
        return code

    elif op == "/":
        code = get_divmod_code(right_token)
        code += ">>>"  # point to a/b
        code += "[<<<+>>>-]"  # copy a/b to current cell
        code += "<<"  # point to next available cell

        return code

    elif op == "%":
        code = get_divmod_code(right_token)
        code += ">>"  # point to a%b
        code += "[<<+>>-]"  # copy a%b to current cell
        code += "<"  # point to next available cell

        return code

    # relops
    elif op == "==":
        # a, b
        code = "[->-<]"  # a = 0, b = b - a
        code += "+"  # a = 1. will hold the result. if a!=b, this is unchanged
        code += ">"  # point to b
        code += "["  # if b == 0, enter the following code
        code += "<->[-]"  # a = 0, b=0
        code += "]"  # end of "loop"

        return code

    elif op == "!=":
        # a, b
        code = "[->-<]"  # a = 0, b = b - a
        # a will hold the result. if a != b, this is unchanged
        code += ">"  # point to b
        code += "["  # if b == 0, enter the following code
        code += "<+>[-]"  # a = 1, b=0
        code += "]"  # end of "loop"

        return code

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

    elif op == "<<":
        # a, b, temp

        code = ">>[-]"  # zero temp
        code += "<"  # point to b

        code += "["  # while b != 0
        code += "<"  # point to a
        code += "[>>+<<-]"  # copy a to temp
        code += ">>"  # point to temp
        code += "[<<++>>-]"  # multiply temp by 2 and store result in a
        code += "<-"  # point to b and b -= 1
        code += "]"  # end while

        return code

    elif op == ">>":
        # a, b, c, x, y, z

        code = ">"  # point to b
        code += ">[-]" * 4  # clear 4 cells
        code += "<" * 4  # point to b

        code += "["  # while b != 0
        code += ">++"  # set c to 2
        code += "<<"  # point to a

        code += "["  # while a != 0
        code += "-"  # a -= 1
        code += ">>-"  # c -= 1
        code += "[>>+>+<<<-]>>>[<<<+>>>-]"  # copy c to y (via z)
        code += "<"  # point to y

        code += "-["  # if y == 0
        code += "<+"  # x += 1
        code += "<++"  # set c to 2
        code += ">>"
        code += "+"  # zero y
        code += "]"  # end if

        code += "<<<<"  # point to a
        code += "]"  # end while

        code += ">>>"  # point to x
        code += "[<<<+>>>-]"  # move x to a
        code += "<[-]"  # zero c
        code += "<-"  # b -= 1
        code += "]"  # end while

        return code

    elif op_token.type == Token.BITWISE_AND:
        code = get_bitwise_code("[->[-<<+>>]<]>[-]")

        return code

    elif op_token.type == Token.BITWISE_OR:
        code = get_bitwise_code("[>+<-]>[[-]<<+>>]")

        return code

    elif op_token.type == Token.BITWISE_XOR:
        code = get_bitwise_code("[>-<-]>[[-]<<+>>]")

        return code

    raise NotImplementedError


def get_print_string_code(string):
    code = "[-]"  # zero the current cell
    code += ">[-]"  # zero the next cell (will be used for loop counts)
    code += "<"  # point to the original cell ("character" cell)

    prev_value = 0
    for i in range(len(string)):
        current_value = ord(string[i])

        code += get_set_cell_value_code(current_value, prev_value, zero_next_cell_if_necessary=False)
        code += "."

        prev_value = current_value

    return code


def get_move_right_index_cells_code(current_pointer, node_index):
    # used for arrays
    # returns a code that evaluates the index, then moves the pointer right, <index> amount of cells
    # at the end of execution, the layout is:
    # 0 index next_available_cell (point to next available cell)

    # index, steps_taken_counter
    code = node_index.get_code(current_pointer)  # index
    code += "[-]"  # counter = 0
    code += "<"  # point to index

    code += "["  # while index != 0
    code += ">>"  # point to new_counter (one after current counter)
    code += "[-]+"  # zero new_counter then add 1 to the new_counter
    code += "<"  # move to old counter
    code += "[>+<-]"  # add old counter to new counter
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


# =================
#     General
# =================

def get_NUM_token_value(token):
    if token.data.startswith("0x"):
        return int(token.data, 16)
    else:
        return int(token.data)


def get_variable_from_ID_token(ids_map_list, ID_token):
    ID = ID_token.data
    # given an id, goes through the ids map list and returns the index of the first ID it finds
    for i in range(len(ids_map_list)):
        ids_map = ids_map_list[i].IDs_dict
        if ID in ids_map:
            return ids_map[ID]
    raise BFSemanticError("'%s' does not exist" % str(ID_token))


def dimensions_to_size(dimensions):
    return reduce(lambda x, y: x * y, dimensions)


def get_variable_dimensions_from_token(ids_map_list, ID_token):
    variable = get_variable_from_ID_token(ids_map_list, ID_token)
    return variable.dimensions


def get_variable_size_from_token(ids_map_list, ID_token):
    variable = get_variable_from_ID_token(ids_map_list, ID_token)
    return variable.size


def get_id_index(ids_map_list, ID_token):
    variable = get_variable_from_ID_token(ids_map_list, ID_token)
    return variable.cell_index


def get_offset_to_variable(ids_map_list, ID_token, current_pointer):
    offset = current_pointer - get_id_index(ids_map_list, ID_token)
    return offset
