class Token:

    INT = "INT"
    VOID = "VOID"
    TRUE = "TRUE"
    FALSE = "FALSE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    RETURN = "RETURN"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    FOR = "FOR"
    DO = "DO"
    BREAK = "BREAK"
    CONTINUE = "CONTINUE"
    SWITCH = "SWITCH"
    CASE = "CASE"
    DEFAULT = "DEFAULT"
    COLON = "COLON"
    SEMICOLON = "SEMICOLON"
    COMMA = "COMMA"

    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LBRACK = "LBRACK"
    RBRACK = "RBRACK"

    ASSIGN = "ASSIGN"
    RELOP = "RELOP"
    BINOP = "BINOP"
    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"
    UNARY_MULTIPLICATIVE = "UNARY_MULTIPLICATIVE"

    BITWISE_SHIFT = "BITWISE_SHIFT"
    BITWISE_NOT = "BITWISE_NOT"
    BITWISE_AND = "BITWISE_AND"
    BITWISE_OR = "BITWISE_OR"
    BITWISE_XOR = "BITWISE_XOR"

    WHITESPACE = "WHITESPACE"
    ID = "ID"
    NUM = "NUM"
    STRING = "STRING"
    CHAR = "CHAR"

    PRINT = "PRINT"
    COMMENT = "COMMENT"
    UNIDENTIFIED = "UNIDENTIFIED"

    def __init__(self, type, line, column, data=None):
        self.type = type
        self.line = line
        self.column = column
        self.data = data

    def __str__(self):
        return self.type + ((" " + self.data) if self.data is not None else "") + \
               " (line %s column %s)" % (self.line, self.column)
