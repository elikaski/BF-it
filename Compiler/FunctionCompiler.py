from Compiler.Parser import Parser
from Compiler.Node import *
from Compiler.General import *
from Compiler.Globals import *

"""
This file implements the FunctionCompiler object
It is where we actually compile code - statements, assignments, calculations, etc
The syntax of the language is defined here as compilation rules

A function is position dependent - it needs to know where on the tape it runs
So that it can access global variables, which are at the beginning of the stack, correctly
Because of that, the function's code is dependent on when/where we call it
The idea is that we compile the function on demand - every time it is called
And on every time we compile it - we pass it the current stack pointer
This is implemented in the get_code() function

FunctionCompiler object holds tokens correspond to the function so that we can compile it on demand
"""


class LibraryFunctionCompiler:
    def __init__(self, name, type, parameters, code):
        self.name = name
        self.type = type
        self.parameters = parameters
        self.code = code

    def get_code(self, current_stack_pointer):
        return self.code


class FunctionCompiler:

    def __init__(self, name, tokens):
        self.name = name
        self.tokens = tokens
        self.parser = Parser(self.tokens)
        self.ids_map_list = list()
        self.type = None
        self.parameters = None
        self.process_function_definition()  # sets type and parameters
        self.return_value_cell = None  # will be set on every call to this function

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
    """

    def process_function_definition(self):
        # sets function type and parameters, advances parser

        function_return_type = self.parser.current_token()
        self.parser.advance_token()  # skip return type
        function_name = self.parser.current_token().data
        assert function_name == self.name
        self.parser.advance_token()  # skip ID
        parameters = self.get_function_parameters_declaration()
        # parser now points to LBRACE = beginning of function scope

        self.type = function_return_type
        self.parameters = parameters

    def get_code(self, current_stack_pointer):
        """
        layout:
                    current_stack_pointer -------
                                                |
                                                v
        global1 global2 unknown1 unknown2 my_return_value param1 param2 local1 local2

        current_stack_pointer is current next available cell
        which is the value of the caller's current_stack_pointer plus this function's parameters
        create ids map for global variables
        make room for return_value
        """
        self.insert_global_variables_to_function_scope()

        # self.current_stack_pointer is now equal to the size of the global variables plus 1 (next_available_cell)
        # new stack pointer should be at least that size
        assert self.current_stack_pointer() <= current_stack_pointer
        self.return_value_cell = current_stack_pointer
        self.set_stack_pointer(current_stack_pointer+1) #  make room for return_value cell. next available cell is the next one after it.
        function_code = self.compile_function_scope(self.parameters)
        self.remove_ids_map()  # Global variables
        return function_code

    # =================
    # helper functions
    # =================
    def insert_global_variables_to_function_scope(self):
        self.add_ids_map()
        for variable in global_variables:
            self.insert_to_ids_map(variable)

    def get_array_index_expression(self):
        """
        the idea - address the multi-dimensional array as a one-dimensional array
        calculate the appropriate index in the one-dimensional array
        by multiplying the index in each dimension by its size (i.e the multiplication of all sizes of the following dimensions)
        and then using the NodeArrayGetElement/NodeArraySetElement class which gets an element in a one-dimensional array

        in order to do that, we need to create our own sub-tree of multiplications,
        and pass it as the "index expression"

        e.g if the array is: arr[10][5][2] and we want to get arr[4][3][1]
        then we want to calculate index = (4*(5*2) + 3*(2) + 1)
        """
        ID_token = self.parser.current_token()
        self.parser.advance_token(2)  # skip ID, LBRACK
        first_index_expression = index_expression = self.expression()  # first dimension
        self.parser.check_current_tokens_are([Token.RBRACK])
        self.parser.advance_token()  # skip RBRACK

        # now handle the next dimensions (if multi-dimensional array)
        dimensions = get_variable_dimensions(self.ids_map_list, ID_token)
        if len(dimensions) > 1:
            multiply_token = Token(Token.BINOP, ID_token.line, ID_token.column, data="*")
            add_token = Token(Token.BINOP, ID_token.line, ID_token.column, data="+")

            # multiply by next dimensions sizes
            multiply_amount = reduce(lambda x, y: x * y, dimensions[1:])  # size of the following dimensions
            node_token_multiply_amount = NodeToken(self.ids_map_list[:], token=Token(Token.NUM, ID_token.line, ID_token.column, data=str(multiply_amount)))
            index_expression = NodeToken(self.ids_map_list[:], token=multiply_token, left=first_index_expression, right=node_token_multiply_amount)

            # handle next dimensions
            dimension = 1
            while dimension < len(dimensions):
                if self.parser.current_token().type != Token.LBRACK:  # too few indexes given...
                    if dimension == 1:
                        return first_index_expression  # allow use of only one dimension for multi-dimensional array
                    raise BFSemanticError("%s is a %s-dimensional array, but only %s dimension(s) given as index" %
                                          (str(ID_token), len(dimensions), dimension))
                self.parser.check_current_tokens_are([Token.LBRACK])
                self.parser.advance_token()  # skip LBRACK
                exp = self.expression()

                self.parser.check_current_tokens_are([Token.RBRACK])
                self.parser.advance_token()  # skip RBRACK

                # current_dimension_index *= size_of_following_dimensions
                if dimension + 1 < len(dimensions):  # not last dimension - need to multiply and add
                    multiply_amount = reduce(lambda x, y: x * y, dimensions[dimension + 1:])  # size of the following dimensions
                    node_token_multiply_amount = NodeToken(self.ids_map_list[:], token=Token(Token.NUM, ID_token.line, ID_token.column, data=str(multiply_amount)))
                    multiply_node = NodeToken(self.ids_map_list[:], token=multiply_token, left=exp, right=node_token_multiply_amount)

                    # prev_dimensions_index += current_dimension_index
                    index_expression = NodeToken(self.ids_map_list[:], token=add_token, left=index_expression, right=multiply_node)
                else:  # last dimension - no need to multiply, just add
                    index_expression = NodeToken(self.ids_map_list[:], token=add_token, left=index_expression, right=exp)
                dimension += 1

        if self.parser.current_token().type == Token.LBRACK:  # too many indexes given...
            raise BFSemanticError("%s is a %s-dimensional array. Unexpected %s" %
                                  (str(ID_token), len(dimensions), self.parser.current_token()))
        return index_expression

    def get_token_after_array_access(self):
        # in case we have: "ID[a][b][c]...[z] next_token", return "next_token"
        self.parser.check_current_tokens_are([Token.ID, Token.LBRACK])
        idx = self.parser.current_token_index + 1  # point to LBRACK
        while self.parser.token_at_index(idx).type == Token.LBRACK:
            idx = self.parser.find_matching(idx)  # point to RBRACK
            idx += 1  # advance to one after the RBRACK

        return self.parser.token_at_index(idx)

    def add_ids_map(self):
        """
        first cells are global variable cells (index 0 to n)
        the next cell (index n+1) is the return_value cell
        every function assumes that these cell exist
        """

        next_available_cell = 0 if len(self.ids_map_list) == 0 else self.ids_map_list[0].next_available_cell

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
        ids_map.next_available_cell += get_variable_size(variable)
        ids_map.IDs_dict[variable.name] = variable

    def reserve_cell_in_ids_map(self):
        """
        reserve cell by increasing the "pointer" of the next available cell
        this is used for making room for return_value cell
        """
        ids_map = self.ids_map_list[0]
        ids_map.next_available_cell += 1

    def variables_dict_size(self, variables_dict_index):
        variables_dict = self.ids_map_list[variables_dict_index].IDs_dict

        size = 0
        for variable in variables_dict.values():
            size += get_variable_size(variable)

        return size

    def size_of_variables_current_scope(self):
        return self.variables_dict_size(0)

    def size_of_global_variables(self):
        return self.variables_dict_size(-1)

    def increase_stack_pointer(self, amount=1):
        # sometimes it is needed to increase the stack pointer
        # for example, when compiling "if ... else ...", we need 2 temporary cells before the inner scope code of both the if and the else
        # another example - when evaluating expression list in function call, each expression is evaluated while pointing to a different cell
        # therefore, it is needed to "update" the stack pointer to represent the new pointer
        self.ids_map_list[0].next_available_cell += amount

    def decrease_stack_pointer(self, amount=1):
        self.ids_map_list[0].next_available_cell -= amount

    def set_stack_pointer(self, new_value):
        assert new_value >= self.ids_map_list[0].next_available_cell
        self.ids_map_list[0].next_available_cell = new_value

    def current_stack_pointer(self):
        return self.ids_map_list[0].next_available_cell

    def insert_scope_variables_into_ids_map(self):
        # go through all the variable definitions in this scope (not including sub-scopes), and add them to the ids map
        # move the pointer to the next available cell (the one after the last variable declared in this scope)

        assert self.parser.current_token().type == Token.LBRACE
        self.parser.advance_token()

        i = self.parser.current_token_index
        while i < len(self.tokens):
            token = self.tokens[i]

            if token.type == Token.INT:
                if self.tokens[i-2].type != Token.FOR:  # if it is not a definition inside a FOR statement (for (int i = 0...))
                    variable = create_variable_from_definition(self.parser, index=i)
                    self.insert_to_ids_map(variable)

            elif token.type == Token.LBRACE:
                i = self.parser.find_matching(starting_index=i)

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

    def check_id_doesnt_exist(self, ID):
        # make sure that the id does not exist in the current scope
        # used when defining a variable
        if ID in self.ids_map_list[0].IDs_dict:
            raise BFSemanticError("ID %s is already defined" % ID)

    # =================
    # compilation rules
    # =================

    # expression
    def function_call(self):
        # function_call: ID LPAREN expression_list RPAREN
        # returns NodeFunctionCall
        assert self.parser.current_token().type == Token.ID

        function_token = self.parser.current_token()
        function_name = function_token.data
        self.parser.advance_token()  # skip ID

        if function_name == self.name:
            raise BFSemanticError("No support for recursion yet :(.... in function call '%s'" % str(function_token))

        parameters = self.compile_expression_list()

        check_function_exists(function_token, len(parameters))
        function_to_call = get_function_object(function_name)

        return NodeFunctionCall(self.ids_map_list[:], function_to_call, parameters)

    def literal(self):
        # literal: NUM | CHAR | ID | ID (LBRACK expression RBRACK)+ | TRUE | FALSE | function_call | ( expression )
        token = self.parser.current_token()

        if token.type == Token.ID and self.parser.next_token().type == Token.LPAREN:
            return self.function_call()

        if token.type == Token.ID and self.parser.next_token().type == Token.LBRACK:  # array - ID(LBRACK expression RBRACK)+
            index_expression = self.get_array_index_expression()
            return NodeArrayGetElement(self.ids_map_list[:], token, index_expression)

        if token.type in [Token.NUM, Token.CHAR, Token.ID, Token.TRUE, Token.FALSE]:
            self.parser.advance_token()
            return NodeToken(self.ids_map_list[:], token=token)

        if token.type != Token.LPAREN:
            raise BFSyntaxError("Unexpected '%s'. expected literal (NUM | ID | ID(LBRACK expression RBRACK)+ | TRUE | FALSE | function_call | ( expression ))" % str(token))

        # ( expression )
        self.parser.check_current_tokens_are([Token.LPAREN])
        self.parser.advance_token()  # skip LPAREN
        exp = self.expression()
        self.parser.check_current_tokens_are([Token.RPAREN])
        self.parser.advance_token()  # skip RPAREN

        return exp

    def unary_postfix(self):
        # unary_postfix: literal ( ++ | -- | UNARY_MULTIPLICATIVE)?

        literal = self.literal()
        token = self.parser.current_token()

        if token.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:
            self.parser.advance_token()
            new_node = NodeUnaryPostfix(self.ids_map_list[:], operation=token, literal=literal)
            return new_node
        else:
            return literal

    def unary_prefix(self):
        # unary_prefix:  ( (!)* unary_prefix ) | ( ( ++ | -- | UNARY_MULTIPLICATIVE | ~ ) literal ) | unary_postfix

        token = self.parser.current_token()

        if token.type in [Token.NOT, Token.BITWISE_NOT]:
            self.parser.advance_token()
            unary_prefix = self.unary_prefix()

            new_node = NodeUnaryPrefix(self.ids_map_list[:], operation=token, literal=unary_prefix)
            return new_node

        elif token.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:
            self.parser.advance_token()
            literal = self.literal()

            new_node = NodeUnaryPrefix(self.ids_map_list[:], operation=token, literal=literal)
            return new_node

        else:
            return self.unary_postfix()

    def multiplicative(self):
        # multiplicative: unary_prefix ((MUL|DIV|MOD) unary_prefix)*

        n = self.unary_prefix()

        token = self.parser.current_token()
        while token is not None and token.type == Token.BINOP and token.data in ["*", "/", "%"]:
            self.parser.advance_token()
            next_factor = self.unary_prefix()

            new_node = NodeToken(self.ids_map_list[:], token=token, left=n, right=next_factor)
            n = new_node

            token = self.parser.current_token()

        return n

    def additive(self):
        # additive: multiplicative ((PLUS|MINUS) multiplicative)*
        n = self.multiplicative()

        token = self.parser.current_token()
        while token is not None and token.type == Token.BINOP and token.data in ["+", "-"]:
            self.parser.advance_token()
            next_term = self.multiplicative()

            new_node = NodeToken(self.ids_map_list[:], token=token, left=n, right=next_term)
            n = new_node

            token = self.parser.current_token()

        return n

    def shift(self):
        # shift: additive (<<|>> additive)*
        n = self.additive()

        token = self.parser.current_token()
        while token is not None and token.type == Token.BITWISE_SHIFT:
            self.parser.advance_token()
            next_additive = self.additive()

            new_node = NodeToken(self.ids_map_list[:], token=token, left=n, right=next_additive)
            n = new_node

            token = self.parser.current_token()

        return n

    def relational(self):
        # relational: shift (==|!=|<|>|<=|>= shift)?
        a = self.shift()

        token = self.parser.current_token()
        if token.type != Token.RELOP:  # just an arithmetic expression
            return a

        self.parser.advance_token()
        b = self.shift()

        new_node = NodeToken(self.ids_map_list[:], token=token, left=a, right=b)
        return new_node

    def bitwise_and(self):
        # bitwise_and: relational (& relational)*

        n = self.relational()

        token = self.parser.current_token()
        while token is not None and token.type == Token.BITWISE_AND:
            self.parser.advance_token()
            next_relational = self.relational()

            new_node = NodeToken(self.ids_map_list[:], token=token, left=n, right=next_relational)
            n = new_node

            token = self.parser.current_token()

        return n

    def bitwise_or(self):
        # bitwise_or: bitwise_and (| bitwise_and)*

        n = self.bitwise_and()

        token = self.parser.current_token()
        while token is not None and token.type == Token.BITWISE_OR:
            self.parser.advance_token()
            next_bitwise_and = self.bitwise_and()

            new_node = NodeToken(self.ids_map_list[:], token=token, left=n, right=next_bitwise_and)
            n = new_node

            token = self.parser.current_token()

        return n

    def logical_and(self):
        # logical_and: bitwise_or (&& bitwise_or)*

        n = self.bitwise_or()

        token = self.parser.current_token()
        while token is not None and token.type == Token.AND:
            self.parser.advance_token()
            next_bitwise_or = self.bitwise_or()

            new_node = NodeToken(self.ids_map_list[:], token=token, left=n, right=next_bitwise_or)
            n = new_node

            token = self.parser.current_token()

        return n

    def logical_or(self):
        # logical_or: logical_and (|| logical_and)*

        n = self.logical_and()

        token = self.parser.current_token()
        while token is not None and token.type == Token.OR:
            self.parser.advance_token()
            next_and = self.logical_and()

            new_node = NodeToken(self.ids_map_list[:], token=token, left=n, right=next_and)
            n = new_node

            token = self.parser.current_token()

        return n

    def assignment(self):
        # assignment: ID ASSIGN expression | ID (LBRACK expression RBRACK)+ ASSIGN expression | logical_or

        if self.parser.current_token().type == Token.ID and self.parser.next_token().type == Token.ASSIGN:
            # ID ASSIGN expression

            id_token = self.parser.current_token()
            assign_token = self.parser.next_token()
            self.parser.advance_token(amount=2)  # skip ID ASSIGN

            expression_node = self.expression()

            new_node = NodeToken(self.ids_map_list[:], left=NodeToken(self.ids_map_list[:], token=id_token), token=assign_token, right=expression_node)
            return new_node

        elif self.parser.current_token().type == Token.ID and self.parser.next_token().type == Token.LBRACK and \
                self.get_token_after_array_access().type == Token.ASSIGN:
            # ID (LBRACK expression RBRACK)+ ASSIGN value_expression
            id_token = self.parser.current_token()
            index_expression = self.get_array_index_expression()
            self.parser.check_current_tokens_are([Token.ASSIGN])
            assign_token = self.parser.current_token()
            self.parser.advance_token()  # skip ASSIGN
            value_expression = self.expression()

            return NodeArraySetElement(self.ids_map_list[:], id_token, index_expression, assign_token, value_expression)
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
        # logical operations (!, &&, ||, ~)
        # assignment (=, +=, -=, *=, /=, %=, <<=, >>=, &=, |=)
        # this is implemented using a Node class that represents a parse tree

        """
        (used reference: https://introcs.cs.princeton.edu/java/11precedence/)
        order of operations (lowest precedence to highest precedence)
            assignment (=, +=, -=, *=, /=, %=, <<=, >>=, &=, |=)
            logical_or (||)
            logical_and (&&)
            bitwise_or (|)
            bitwise_and (&)
            relational (==|!=|<|>|<=|>=)
            shift (<<|>>)
            additive (+-)
            multiplicative (*/%)
            unary_prefix (!, ++, --, ~)
            unary_postfix (++, --)

        expression: assignment
        assignment: ID (=|+=|-=|*=|/=|%=|<<=|>>=|&=|(|=)) expression | logical_or
        logical_or: logical_and (|| logical_and)*
        logical_and: bitwise_or (&& bitwise_or)*
        bitwise_or: bitwise_and (| bitwise_and)*
        bitwise_and: relational (& relational)*
        relational: shift (==|!=|<|>|<=|>= shift)?
        shift: additive ((<<|>>) additive)*
        additive: multiplicative ((PLUS|MINUS) multiplicative)*
        multiplicative: unary_prefix ((MUL|DIV|MOD) unary_prefix)*
        unary_prefix:  ( (!)* unary_prefix ) | ( ( ++ | -- | ~ ) literal ) | unary_postfix
        unary_postfix: literal ( ++ | -- )?
        literal: NUM | CHAR | ID | ID[expression] | TRUE | FALSE | function_call | ( expression )
        """

        parse_tree = self.expression()
        expression_code = parse_tree.get_code(self.current_stack_pointer())
        return expression_code

    # functions-related
    def get_function_parameters_declaration(self):
        # parameters declaration: LPAREN (int ID (LBRACK NUM RBRACK)? (COMMA int ID)*)? RPAREN
        # return list of parameters (named tuples (type, ID)) at the same order as declared

        assert self.parser.current_token().type == Token.LPAREN
        self.parser.advance_token()

        res = list()

        token = self.parser.current_token()
        while token.type != Token.RPAREN:
            if token.type != Token.INT:
                raise BFSemanticError("Only int type is supported as a function parameter, and not '%s'" % str(token))

            parameter = create_variable_from_definition(self.parser, advance_tokens=True)
            res.append(parameter)

            if self.parser.current_token().type == Token.COMMA:
                self.parser.advance_token()
            else:
                self.parser.check_current_tokens_are([Token.RPAREN])

            token = self.parser.current_token()

        self.parser.advance_token()  # skip RPAREN
        return res

    def compile_expression_list(self):
        # expression_list: ( expression (COMMA expression)* )?
        # returns a list of Nodes - one node for each expression
        assert self.parser.current_token().type == Token.LPAREN
        self.parser.advance_token()

        expressions = list()

        token = self.parser.current_token()
        while token.type != Token.RPAREN:
            expressions.append(self.expression())

            if self.parser.current_token().type == Token.COMMA:
                self.parser.advance_token()
            else:
                self.parser.check_current_tokens_are([Token.RPAREN])
            token = self.parser.current_token()

        self.parser.advance_token()  # skip RPAREN
        return expressions

    def compile_return(self):
        # this assumes that the return is the last statement in the function

        self.parser.advance_token()  # skip return
        if self.parser.current_token().type == Token.SEMICOLON:
            # return;
            self.parser.advance_token()  # skip ;
            return ''  # nothing to do

        # return exp;
        expression_code = self.compile_expression()
        self.parser.check_current_tokens_are([Token.SEMICOLON])

        self.parser.advance_token()  # skip ;

        code = expression_code  # after this, we point to next available cell
        code += "<"  # point to value to return
        code += get_move_to_return_value_cell_code(self.return_value_cell, self.current_stack_pointer())

        return code

    # statements
    def compile_expression_as_statement(self):
        # this expression can be used as a statement.
        # e.g: x+=5;  or  x++ or ++x;

        assert self.parser.current_token().type in [Token.ID, Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]

        code = self.compile_expression()
        self.parser.check_current_tokens_are([Token.SEMICOLON])
        self.parser.advance_token()  # skip ;

        code += "<"  # discard the expression's value

        return code

    def compile_print_string(self):
        self.parser.check_next_tokens_are([Token.LPAREN, Token.STRING, Token.RPAREN, Token.SEMICOLON])
        self.parser.advance_token(amount=2)  # skip print (
        string_to_print = self.parser.current_token().data
        self.parser.advance_token(amount=3)  # skip string ) ;

        code = get_print_string_code(string_to_print)
        return code

    def compile_function_call_statement(self):
        # compile statement: function_call SEMICOLON
        function_call_node = self.function_call()
        function_call_code = function_call_node.get_code(current_pointer=self.current_stack_pointer())

        self.parser.check_current_tokens_are([Token.SEMICOLON])
        self.parser.advance_token()  # skip ;

        code = function_call_code  # at this point, we point to one after the return value
        code += "<"  # discard return value
        return code

    def compile_if(self):
        self.parser.check_next_tokens_are([Token.LPAREN])
        self.parser.advance_token(amount=2)  # skip to after LPAREN

        expression_code = self.compile_expression()
        self.parser.check_current_tokens_are([Token.RPAREN, Token.LBRACE])
        self.parser.advance_token()  # point to LBRACE

        token_after_RBRACE = self.parser.token_at_index(self.parser.find_matching() + 1)
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

        self.parser.check_current_tokens_are([Token.ELSE, Token.LBRACE])
        self.parser.advance_token()  # skip the 'else'
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
        self.parser.check_next_tokens_are([Token.LPAREN])
        self.parser.advance_token(amount=2)  # skip to after LPAREN

        expression_code = self.compile_expression()

        self.parser.check_current_tokens_are([Token.RPAREN, Token.LBRACE])
        self.parser.advance_token()  # i points to LBRACE

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

        self.parser.check_current_tokens_are([Token.FOR, Token.LPAREN])
        self.parser.advance_token(amount=2)  # skip for (

        manually_inserted_variable_in_for_definition = False
        code = ''

        # =============== enter FOR scope ===============
        self.add_ids_map()
        # ===============================================

        if self.parser.current_token().type == Token.INT:
            # we are defining a variable inside the for statement definition (for (int i = 0....))
            variable = create_variable_from_definition(self.parser, advance_tokens=False)
            self.insert_to_ids_map(variable)
            manually_inserted_variable_in_for_definition = True
            code += ">" * get_variable_size(variable)

        initial_statement = self.compile_statement()

        condition_expression = self.compile_expression()
        self.parser.check_current_tokens_are([Token.SEMICOLON])
        self.parser.advance_token()  # skip ;

        if self.parser.current_token().type == Token.RPAREN:
            modification_expression = ""  # no modification expression
        else:
            modification_expression = self.compile_expression()
            modification_expression += "<"  # discard expression value
        self.parser.check_current_tokens_are([Token.RPAREN])
        self.parser.advance_token()  # skip )

        # compiling <for> scope inside { }:
        self.parser.check_current_tokens_are([Token.LBRACE])
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

        token = self.parser.current_token()

        if token.type == Token.INT:  # INT ID ([NUM])? (= EXPRESSION)? ;
            self.parser.check_next_tokens_are([Token.ID])
            self.parser.advance_token()  # skip "INT" (now points to ID)
            assert self.parser.current_token().type == Token.ID

            if self.parser.next_token().type == Token.SEMICOLON:  # INT ID SEMICOLON
                self.parser.advance_token(2)  # skip ID SEMICOLON
                return ''  # no code is generated here. code was generated for defining this variable when we entered the scope

            elif self.parser.next_token().type == Token.LBRACK:  # INT ID (LBRACK NUM RBRACK)+ SEMICOLON
                self.parser.advance_token(1)  # skip ID
                while self.parser.current_token().type == Token.LBRACK:
                    self.parser.check_current_tokens_are([Token.LBRACK, Token.NUM, Token.RBRACK])
                    self.parser.advance_token(3)  # skip LBRACK, NUM, RBRACK
                self.parser.check_current_tokens_are([Token.SEMICOLON])
                self.parser.advance_token(1)  # skip SEMICOLON
                return ''  # no code is generated here. code was generated for defining this variable when we entered the scope

            else:
                return self.compile_expression_as_statement()

        elif token.type in [Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:  # ++ID;
            return self.compile_expression_as_statement()

        elif token.type == Token.ID:
            if self.parser.next_token().type in [Token.ASSIGN, Token.LBRACK, Token.INCREMENT, Token.DECREMENT, Token.UNARY_MULTIPLICATIVE]:
                # ID ASSIGN expression; or ID([expression])+ ASSIGN expression; or ID++;
                return self.compile_expression_as_statement()
            elif self.parser.next_token().type == Token.LPAREN:  # ID(...);  (function call)
                return self.compile_function_call_statement()
            raise BFSyntaxError("Unexpected '%s' after '%s'. Expected '=|+=|-=|*=|/=|%%=|<<=|>>=|&=|(|=)' (assignment), '++|--' (modification) or '(' (function call)" % (str(self.parser.next_token()), str(token)))

        elif token.type == Token.PRINT:  # print(string);
            return self.compile_print_string()

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
            self.parser.advance_token()  # skip ;
            return ""

        raise NotImplementedError(token)

    def compile_scope_statements(self):
        tokens = self.tokens

        code = ''
        while self.parser.current_token() is not None:

            if self.parser.current_token().type == Token.RBRACE:
                # we reached the end of our scope
                self.parser.advance_token()  # skip RBRACE
                return code
            else:
                code += self.compile_statement()

        # should never get here
        raise BFSyntaxError("expected } after the last token in scope " + str(tokens[-1]))

    def compile_scope(self):
        assert self.parser.current_token().type == Token.LBRACE

        code = self.enter_scope()
        code += self.compile_scope_statements()
        code += self.exit_scope()

        return code

    def compile_function_scope(self, parameters):
        #  returns code for the current function
        #  parameters is a list of parameters, in the order of their declaration
        #  will be inserted to the new scope prior to the scope's compilation

        """
            example layout:
                int global_var1;
                int global_var2;
                int foo(int a, int b) {
                    int x;
                    int y;
                    return 5;
                }

                int main() {
                    int n;
                    foo(1, 2);
                }

                global_var1 global_var2 main_return_value n foo_return_value a=1 b=2 x y

                calling convention:
                caller responsibility: make room for return_value (and zero its cell), place parameters, point to return_value cell
                callee responsibility: put return value in return_value cell and point to it (thus "cleaning" parameters)
                    can assume that there is a zerod cell at current_stack_pointer (return_value_cell) (therefore ids_map starts at index current_stack_pointer+1)
                    can assume that the next cells match your parameters
                    assumes that initially, the pointer points to the first cell (return_value_cell).
                    therefore begin with '>' * (1 + parameters + scope variables)
        """

        assert self.parser.current_token().type == Token.LBRACE

        code = self.enter_function_scope(parameters)
        code += self.compile_scope_statements()
        code += self.exit_scope()
        code += "<"  # point to return_value_cell

        return code

