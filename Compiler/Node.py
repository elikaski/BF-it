from .Exceptions import BFSemanticError
from .General import get_copy_from_variable_code, get_copy_to_variable_code
from .General import get_move_left_index_cell_code, get_move_right_index_cells_code
from .General import get_offset_to_variable, get_variable_dimensions_from_token
from .General import get_op_between_literals_code, get_literal_token_code, get_token_ID_code
from .General import get_unary_prefix_op_code, get_unary_postfix_op_code
from .General import unpack_literal_tokens_to_array_dimensions
from .Structs import get_offset_to_field, get_struct_from_id_token
from .Token import Token

"""
This file holds classes that are used to create the parse tree of expressions
Each class implements a get_code() function that receives a "stack pointer" and returns code that evaluates the expression
"""


class Node:
    def __init__(self, ids_map_list):
        # holds a copy of ids_map_list as it was when we parsed the expression
        self.ids_map_list = ids_map_list

    def assign_token_to_op_token(self, assign_token):
        assert assign_token.data in ["+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="]

        assignment_map = {
            "+=": Token(Token.BINOP, assign_token.line, assign_token.column, data="+"),
            "-=": Token(Token.BINOP, assign_token.line, assign_token.column, data="-"),
            "*=": Token(Token.BINOP, assign_token.line, assign_token.column, data="*"),
            "/=": Token(Token.BINOP, assign_token.line, assign_token.column, data="/"),
            "%=": Token(Token.BINOP, assign_token.line, assign_token.column, data="%"),
            "<<=": Token(Token.BITWISE_SHIFT, assign_token.line, assign_token.column, data="<<"),
            ">>=": Token(Token.BITWISE_SHIFT, assign_token.line, assign_token.column, data=">>"),
            "&=": Token(Token.BITWISE_AND, assign_token.line, assign_token.column),
            "|=": Token(Token.BITWISE_OR, assign_token.line, assign_token.column),
            "^=": Token(Token.BITWISE_XOR, assign_token.line, assign_token.column),
        }

        op_token = assignment_map[assign_token.data]
        op_node = NodeToken(self.ids_map_list, token=op_token)
        return op_node

    def get_code(self, *args, **kwargs):
        pass


class NodeToken(Node):
    def __init__(self, ids_map_list, left=None, token=None, right=None):
        Node.__init__(self, ids_map_list)
        self.left = left
        self.right = right
        self.token = token

    def get_code(self, current_pointer, *args, **kwargs):
        # returns the code that evaluates the parse tree

        if self.token.type in [Token.NUM, Token.CHAR, Token.ID, Token.TRUE, Token.FALSE]:
            # its a literal (leaf)
            assert self.left is None and self.right is None
            if self.token.type == Token.ID:
                return get_token_ID_code(self.ids_map_list, self.token, current_pointer)
            else:
                return get_literal_token_code(self.token)

        elif self.token.type in [Token.BINOP, Token.RELOP, Token.AND, Token.OR, Token.BITWISE_SHIFT, Token.BITWISE_AND, Token.BITWISE_OR, Token.BITWISE_XOR]:
            code = self.left.get_code(current_pointer)
            code += self.right.get_code(current_pointer + 1)
            code += "<<"  # point to the first operand

            right_token = None
            if isinstance(self.right, NodeToken):
                right_token = self.right.token

            code += get_op_between_literals_code(self.token, right_token)
            return code

        elif self.token.type == Token.ASSIGN:
            assert self.left.token.type == Token.ID

            if self.token.data == '=':
                # id = expression
                code = self.right.get_code(current_pointer)

                offset = 0
                if isinstance(self.left, NodeStructGetField):
                    offset = self.left.get_offset()

                # create code to copy from evaluated expression to ID's cell
                code += "<"  # point to evaluated expression cell
                code += get_copy_to_variable_code(self.ids_map_list, self.left.token, current_pointer - offset)
                code += ">"  # point to next available cell

                return code

            else:
                assert self.token.data in ["+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="]
                # id += expression
                # create a node for id + expression

                op_node = self.assign_token_to_op_token(self.token)
                op_node.left = self.left
                op_node.right = self.right

                # create a node for id = id + expression
                assign_token = Token(Token.ASSIGN, self.token.line, self.token.column, data="=")
                assignment_node = NodeToken(self.ids_map_list, left=self.left, token=assign_token, right=op_node)

                return assignment_node.get_code(current_pointer)


class NodeUnaryPrefix(Node):
    def __init__(self, ids_map_list, operation, literal):
        Node.__init__(self, ids_map_list)
        self.token_operation = operation
        self.node_literal = literal

    def get_code(self, current_pointer, *args, **kwargs):
        # unary prefix (!x or ++x or ~x)
        assert self.token_operation.type in [Token.NOT, Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE, Token.BITWISE_NOT]

        if self.token_operation.type in [Token.NOT, Token.BITWISE_NOT]:
            code = self.node_literal.get_code(current_pointer)
            code += "<"  # point to operand
            code += get_unary_prefix_op_code(self.token_operation)

            return code
        else:
            # its INCREMENT or DECREMENT
            if isinstance(self.node_literal, NodeArrayGetElement):
                token_id, index_node = self.node_literal.token_id, self.node_literal.node_expression
                code = get_move_right_index_cells_code(current_pointer, index_node)

                offset = self.node_literal.get_offset() + 2
                # it is offset by 2 because in "get_move_right_index_cells_code", we moved 2 extra cells to the right, for retrieving the value
                offset_to_array = get_offset_to_variable(self.ids_map_list, token_id, current_pointer + offset)

                code += get_unary_prefix_op_code(self.token_operation, offset_to_array)

                code += "<"  # point to res
                code += "[<<+>>-]"  # move res to old "index cell"
                code += "<"  # point to new index cell

                code += get_move_left_index_cell_code()
                return code
            elif isinstance(self.node_literal, NodeStructGetField):
                offset = self.node_literal.get_offset()
                offset_to_ID = get_offset_to_variable(self.ids_map_list, self.node_literal.token, current_pointer - offset)
                return get_unary_prefix_op_code(self.token_operation, offset_to_ID)

            # the token to apply on must be an ID
            if isinstance(self.node_literal, NodeToken) is False:
                raise BFSemanticError("Prefix operator %s can only be applied to a variable" % str(self.token_operation))

            if self.node_literal.token.type != Token.ID:
                raise BFSemanticError("Prefix operator %s cannot be applied to %s, but only to a variable" % (str(self.token_operation), str(self.node_literal.token)))

            offset_to_ID = get_offset_to_variable(self.ids_map_list, self.node_literal.token, current_pointer)
            return get_unary_prefix_op_code(self.token_operation, offset_to_ID)


class NodeUnaryPostfix(Node):
    def __init__(self, ids_map_list, operation, literal):
        Node.__init__(self, ids_map_list)
        self.token_operation = operation
        self.node_literal = literal

    def get_code(self, current_pointer, *args, **kwargs):
        # its an unary postfix operation (x++)
        assert self.token_operation.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]

        if isinstance(self.node_literal, NodeArrayGetElement):
            token_id, index_node = self.node_literal.token_id, self.node_literal.node_expression
            code = get_move_right_index_cells_code(current_pointer, index_node)

            offset = self.node_literal.get_offset() + 2
            # it is offset by 2 because in "get_move_right_index_cells_code", we moved 2 extra cells to the right, for retrieving the value
            offset_to_array = get_offset_to_variable(self.ids_map_list, token_id, current_pointer + offset)

            code += get_unary_postfix_op_code(self.token_operation, offset_to_array)

            code += "<"  # point to res
            code += "[<<+>>-]"  # move res to old "index cell"
            code += "<"  # point to new index cell

            code += get_move_left_index_cell_code()
            return code
        elif isinstance(self.node_literal, NodeStructGetField):
            offset = self.node_literal.get_offset()
            offset_to_ID = get_offset_to_variable(self.ids_map_list, self.node_literal.token, current_pointer - offset)
            return get_unary_postfix_op_code(self.token_operation, offset_to_ID)

        # the token to apply on must be an ID
        if isinstance(self.node_literal, NodeToken) is False:
            raise BFSemanticError("Postfix operator %s can only be applied to a variable" % str(self.token_operation))

        if self.node_literal.token.type != Token.ID:
            raise BFSemanticError("Postfix operator %s cannot be applied to %s, but only to a variable" % (str(self.token_operation), str(self.node_literal.token)))

        offset_to_ID = get_offset_to_variable(self.ids_map_list, self.node_literal.token, current_pointer)
        return get_unary_postfix_op_code(self.token_operation, offset_to_ID)


class NodeFunctionCall(Node):
    def __init__(self, ids_map_list, function_to_call, parameters):
        """
            receives a FunctionCompiler object
                that implements get_code() which gets a stack pointer and returns code
            receives a list of parameters - Node objects
                each one gets a stack pointer and returns code that evaluates the parameter
        """
        Node.__init__(self, ids_map_list)
        self.function_to_call = function_to_call
        self.parameters = parameters

    def get_code(self, current_pointer, *args, **kwargs):
        code = '[-]>'  # return_value_cell=0

        # evaluate parameters from left to right, and put them on the "stack" in that order
        # after each parameter code, the pointer points to the next available cell (one after the parameter)
        for i, parameter in enumerate(self.parameters):
            code += parameter.get_code(current_pointer+1+i)  # evaluate each parameter at its cell offset (starting at one after return_value_cell)

        # at this point we point to one after the last parameter
        code += "<" * len(self.parameters)  # point back to first parameter
        code += "<"  # point to return_value_cell
        code += self.function_to_call.get_code(current_stack_pointer=current_pointer)  # after this we point to return value cell
        code += ">"  # point to next available cell (one after return value)
        return code


class NodeArrayElement(Node):
    def __init__(self, ids_map_list, token_id, struct_field):
        Node.__init__(self, ids_map_list)

        self.struct_field = struct_field
        self.struct_object = None
        if struct_field is not None:
            self.struct_object = get_struct_from_id_token(ids_map_list, token_id)

    def get_offset(self, offset=0):
        if self.struct_field is not None:
            offset -= get_offset_to_field(self.struct_object, self.struct_field)

        return offset

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
    """
    class for getting element of a one-dimensional array
    it receives an expression, indicating the required index
    and returns a code that gets that element
    """

    def __init__(self, ids_map_list, token_id, node_expression, struct_field=None):
        NodeArrayElement.__init__(self, ids_map_list, token_id, struct_field)
        self.token_id = token_id
        self.node_expression = node_expression

    def get_code(self, current_pointer, *args, **kwargs):
        offset = self.get_offset() + 2  # it is +2 because that is where the value is

        code = get_move_right_index_cells_code(current_pointer, self.node_expression)
        code += get_copy_from_variable_code(self.ids_map_list, self.token_id, current_pointer + offset)

        code += "<"  # point to res
        code += "[<<+>>-]"  # move res to old "index cell"
        code += "<"  # point to new index cell

        code += get_move_left_index_cell_code()
        return code


class NodeArraySetElement(NodeArrayElement):
    """
    class for setting element of a one-dimensional array
    it receives:
    1. an expression, indicating the required index
    2. assignment operator (=|+=|-=|*=|/=|%=|<<=|>>=|&=|(|=)|^=)
    3. an expression, indicating the value to be used for the assignment
    and returns a code that gets that element
    """

    def __init__(self, ids_map_list, token_id, node_expression_index, assign_token, node_expression_value, struct_field=None):
        NodeArrayElement.__init__(self, ids_map_list, token_id, struct_field)
        self.token_id = token_id
        self.node_expression_index = node_expression_index

        if assign_token.data == "=":
            # id[exp] = expression

            self.assign_token = assign_token
            self.node_expression_value = node_expression_value

        else:
            # id[exp] += expression
            assert assign_token.data in ["+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="]

            self.assign_token = Token(Token.ASSIGN, assign_token.line, assign_token.column, data="=")

            # create a node for id[exp] + expression
            op_node = self.assign_token_to_op_token(assign_token)
            op_node.left = NodeArrayGetElement(self.ids_map_list[:], token_id, node_expression_index, struct_field=self.struct_field)
            op_node.right = node_expression_value

            self.node_expression_value = op_node

    def get_code(self, current_pointer, *args, **kwargs):
        # index, steps_taken_counter, value

        offset = self.get_offset() + 2  # it is +2 because that is where the value is

        code = self.node_expression_index.get_code(current_pointer)
        code += "[-]"  # counter = 0
        code += ">"  # point to value cell
        code += self.node_expression_value.get_code(current_pointer + offset)
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
        code += get_copy_to_variable_code(self.ids_map_list, self.token_id, current_pointer + offset)
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


class NodeArrayAssignment(NodeArrayElement):
    """
        Used for array assignment
        E.g arr = = { 1, 2, 3... }
    """
    def __init__(self, ids_map_list, token_id, literal_tokens_list, struct_field=None):
        NodeArrayElement.__init__(self, ids_map_list, token_id, struct_field)
        self.token_id = token_id
        self.literal_tokens_list = literal_tokens_list

    def get_code(self, current_pointer, *args, **kwargs):
        if self.struct_field is not None:
            array_dimensions = self.struct_object.get_field_dimensions(self.struct_field)
        else:
            array_dimensions = get_variable_dimensions_from_token(self.ids_map_list, self.token_id)
        unpacked_literals_list = unpack_literal_tokens_to_array_dimensions(self.token_id, array_dimensions, self.literal_tokens_list)

        field_offset = self.get_offset()
        offset = get_offset_to_variable(self.ids_map_list, self.token_id, current_pointer + field_offset)
        code = "<" * offset  # point to first array element
        for literal in unpacked_literals_list:
            code += get_literal_token_code(literal)  # evaluate this literal and point to next array element
        code += ">" * (offset - len(unpacked_literals_list))  # move back to the original position
        code += ">"  # point to the next cell
        return code


class NodeStruct(Node):
    def __init__(self, ids_map_list, token_id):
        Node.__init__(self, ids_map_list)
        self.struct_object = get_struct_from_id_token(ids_map_list, token_id)


class NodeStructGetField(NodeStruct):
    def __init__(self, ids_map_list, token, field_name):
        NodeStruct.__init__(self, ids_map_list, token)
        self.token = token
        self.field_name = field_name

    def get_offset(self):
        field_offset = get_offset_to_field(self.struct_object, self.field_name)
        return field_offset

    def get_code(self, current_pointer, *args, **kwargs):
        return get_copy_from_variable_code(self.ids_map_list, self.token, current_pointer - self.get_offset())


class NodeStructSetField(NodeStruct):
    def __init__(self, ids_map_list, token, field_name, assign_token, node_expression_value):
        NodeStruct.__init__(self, ids_map_list, token)
        self.token = token
        self.field_name = field_name
        self.left = NodeStructGetField(self.ids_map_list[:], token, field_name)

        self.assign_token = assign_token
        self.node_expression_value = node_expression_value

    def get_code(self, current_pointer, *args, **kwargs):
        cell_field_offset = self.left.get_offset()

        if self.assign_token.data == "=":
            # id.id = expression
            code = self.node_expression_value.get_code(current_pointer)

            # create code to copy from evaluated expression to the field
            code += "<"  # point to evaluated expression cell
            code += get_copy_to_variable_code(self.ids_map_list, self.token, current_pointer - cell_field_offset)
            code += ">"  # point to next available cell

            return code
        else:
            assert self.assign_token.data in ["+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="]
            # id.id += expression
            # create a node for id.id + expression

            op_node = self.assign_token_to_op_token(self.assign_token)
            op_node.left = self.left
            op_node.right = self.node_expression_value

            # create a node for id.id = id.id + expression
            assign_token = Token(Token.ASSIGN, self.token.line, self.token.column, data="=")
            assignment_node = NodeToken(self.ids_map_list, left=self.left, token=assign_token, right=op_node)

            return assignment_node.get_code(current_pointer)
