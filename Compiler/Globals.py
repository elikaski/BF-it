from collections import namedtuple
from functools import reduce
from copy import deepcopy
from Compiler.Token import Token

"""
This file holds the program's functions and global variables
(as global variables, hehe)
And related functions
"""

global_variables = list()  # Global list of global variables
functions = dict()  # Global dictionary of function_name --> FunctionCompiler objects


# General Error classes


class BFSyntaxError(Exception):
    pass


class BFSemanticError(Exception):
    pass


# functions
def insert_function_object(function):
    functions[function.name] = function


def get_function_object(name):
    """
    must return a copy of the function
    because we might need to compile function recursively
    and if we dont work on different copies then we will interfere with the current token pointer etc

    for example:
        int increase(int n) { return n+1;}
        int main() {int x = increase(increase(1));}

    while compiling the first call, we start a compilation of the same function object in the second call
    """
    return deepcopy(functions[name])


def insert_library_functions():
    from Compiler.General import get_readint_code, get_printint_code, get_readchar_code, get_printchar_code
    from Compiler.FunctionCompiler import LibraryFunctionCompiler

    readint = LibraryFunctionCompiler("readint", Token.INT, list(), get_readint_code())
    insert_function_object(readint)

    printint = LibraryFunctionCompiler("printint", Token.VOID, [Token.INT], get_printint_code())
    insert_function_object(printint)

    readchar = LibraryFunctionCompiler("readchar", Token.INT, list(), get_readchar_code())
    insert_function_object(readchar)

    printchar = LibraryFunctionCompiler("printchar", Token.VOID, [Token.INT], get_printchar_code())
    insert_function_object(printchar)


def check_function_exists(function_token, parameters_amount):
    function_name = function_token.data
    if function_name not in functions:
        raise BFSemanticError("Function '%s' is undefined" % str(function_token))

    function = functions[function_name]
    if len(function.parameters) != parameters_amount:
        raise BFSemanticError("Function '%s' has %s parameters (called it with %s parameters)" % (str(function_token), len(function.parameters), parameters_amount))


# variables
def get_global_variables():
    return global_variables


def insert_global_variable(variable):
    get_global_variables().append(variable)


def get_global_variables_size():
    return sum(get_variable_size(variable) for variable in get_global_variables())


def create_variable(name, type, dimensions):
    # return variable named tuple
    variable = namedtuple("variable", ["name", "type", "size", "cell_index"])

    variable.name = name
    variable.type = type
    variable.dimensions = dimensions  # list of array dimensions sizes (for non-arrays it will be [1])
    variable.cell_index = None  # will be updated when we insert this variable into an ids map

    return variable


def get_variable_size(variable):
    # return total variable size
    return reduce(lambda x, y: x*y, variable.dimensions)


def create_variable_from_definition(parser, index=None, advance_tokens=False):
    """
    processes the variable definition at index, and returns the variable named tuple
    if index is None, then assumes we start at the current_token_index
    if advance_tokens is True, then modifies current_token_index accordingly using parser.advance_token()
    """
    from Compiler.General import get_NUM_token_value
    if index is None:
        index = parser.current_token_index

    assert parser.tokens[index].type == Token.INT

    parser.check_next_tokens_are([Token.ID], starting_index=index)
    ID = parser.tokens[index + 1].data

    if advance_tokens:
        parser.advance_token(amount=2)  # skip INT ID

    if parser.tokens[index + 2].type == Token.LBRACK:  # array (support multi-dimensional arrays)
        dimensions = []  # element[i] holds the size of dimension[i]
        while parser.tokens[index + 2].type == Token.LBRACK:
            parser.check_next_tokens_are([Token.LBRACK, Token.NUM, Token.RBRACK], starting_index=index + 1)
            dimensions.append(get_NUM_token_value(parser.tokens[index + 3]))

            if advance_tokens:
                parser.advance_token(amount=3)  # skip LBRACK NUM RBRACK
            index += 3
    else:
        dimensions = [1]

    return create_variable(ID, Token.INT, dimensions)
