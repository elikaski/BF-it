from collections import namedtuple
from .Structs import get_struct_object
from .Token import Token
from .General import dimensions_to_size

"""
This file holds the program's functions and global variables
(as global variables, hehe)
And related functions
"""

global_variables = list()  # Global list of global variables

data_sizes = {
    Token.INT: 1,
    Token.VOID: 0
}


# variables
def get_global_variables():
    return global_variables


def insert_global_variable(variable):
    get_global_variables().append(variable)


def get_global_variables_size():
    return sum(get_variable_size(variable) for variable in get_global_variables())


def create_variable(name, type, dimensions, size=1, extra=None):
    # return variable named tuple
    variable = namedtuple("variable", ["name", "type", "size", "dimensions", "cell_index", "extra"])

    variable.name = name
    variable.type = type
    variable.size = size
    variable.dimensions = dimensions  # list of array dimensions sizes (for non-arrays it will be [1])
    variable.cell_index = None  # will be updated when we insert this variable into an ids map
    variable.extra = extra

    return variable


def get_variable_size(variable):
    # return total variable size
    return dimensions_to_size(variable.dimensions) * variable.size


def get_variable_dimensions(variable):
    return variable.dimensions


def is_variable_array(variable):
    return variable.dimensions != [1]


def get_data_type_size(data_type):
    return data_sizes[data_type]


def create_variable_from_definition(parser, index=None, advance_tokens=False):
    """
    processes the variable definition at index, and returns the variable named tuple
    if index is None, then assumes we start at the current_token_index
    if advance_tokens is True, then modifies current_token_index accordingly using parser.advance_token()
    """
    from Compiler.General import get_NUM_token_value
    if index is None:
        index = parser.current_token_index

    variable_type = parser.tokens[index].type

    assert variable_type in [Token.INT, Token.STRUCT]

    offset = 0
    extra = None
    size = 1

    if variable_type == Token.STRUCT:
        parser.check_next_tokens_are([Token.ID, Token.ID], starting_index=index)
        struct_id = parser.tokens[index + 1].data
        ID = parser.tokens[index + 2].data

        struct_object = get_struct_object(struct_id)
        size = struct_object.size
        extra = struct_object

        offset += 2
    else:
        parser.check_next_tokens_are([Token.ID], starting_index=index)
        ID = parser.tokens[index + 1].data

        offset += 1

    if advance_tokens:
        parser.advance_token(amount=offset + 1)  # skip (INT ID | STRUCT ID ID)

    if parser.tokens[index + offset + 1].type == Token.LBRACK:  # array (support multi-dimensional arrays)
        dimensions = []  # element[i] holds the size of dimension[i]
        while parser.tokens[index + offset + 1].type == Token.LBRACK:
            parser.check_next_tokens_are([Token.LBRACK, Token.NUM, Token.RBRACK], starting_index=index + offset)
            dimensions.append(get_NUM_token_value(parser.tokens[index + offset + 2]))

            if advance_tokens:
                parser.advance_token(amount=3)  # skip LBRACK NUM RBRACK
            index += 3
    else:
        dimensions = [1]

    return create_variable(ID, variable_type, dimensions, size, extra)
