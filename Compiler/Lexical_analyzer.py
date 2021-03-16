import re
from .Token import Token


class LexicalErrorException(Exception):
    pass


def analyze(text):
    """
    :returns list of tokens in the text
    raises exception in case of lexical error
    """

    rules = [
        ('\s+', Token.WHITESPACE),
        ('void',    Token.VOID),
        ('int',     Token.INT),
        ('bool', Token.INT),  # treat bool as int
        ('char', Token.INT),  # treat char as int

        ('true', Token.TRUE),
        ('false', Token.FALSE),
        ('&&', Token.AND),
        ('\|\|', Token.OR),
        ('\!', Token.NOT),
        ('return', Token.RETURN),
        ('if', Token.IF),
        ('else', Token.ELSE),
        ('while', Token.WHILE),
        ('for', Token.FOR),
        ('do', Token.DO),
        ('print', Token.PRINT),
        ('break', Token.BREAK),  # todo
        ('continue', Token.CONTINUE),  # todo
        (';', Token.SEMICOLON),
        (',', Token.COMMA),

        ('\(', Token.LPAREN),
        ('\)', Token.RPAREN),
        ('\{', Token.LBRACE),
        ('\}', Token.RBRACE),
        ('\[', Token.LBRACK),
        ('\]', Token.RBRACK),
        ('=|\+=|-=|\*=|/=|%=|<<=|>>=|&=|\|=|\^=', Token.ASSIGN),

        ('<=|>=|==|!=|<|>', Token.RELOP),
        ('\+\+', Token.INCREMENT),
        ('--', Token.DECREMENT),
        ('\+|-|\*|/|%', Token.BINOP),
        ('\*\*|//|%%', Token.UNARY_MULTIPLICATIVE),

        ('<<|>>', Token.BITWISE_SHIFT),
        ('~', Token.BITWISE_NOT),
        ('&', Token.BITWISE_AND),
        ('\|', Token.BITWISE_OR),
        ('\^', Token.BITWISE_XOR),

        (r'#include <(.*\.code)>', Token.INCLUDE_LIB_DIRECTIVE),
        (r'#include "(.*\.code)"', Token.INCLUDE_LOCAL_DIRECTIVE),

        ('([a-zA-Z_][a-zA-Z0-9_]*)',    Token.ID),
        ('(\d+)',     Token.NUM),
        ('(0x[A-Fa-f\d]+)',     Token.NUM),  # hexadecimal number
        (r'\"(\\\"|[^"])*"',   Token.STRING),
        (r'\'(\\\'|(\\)?[^\'])\'', Token.CHAR),
        ('//.*(\\n|$)', Token.COMMENT),
        (r'/\*[\s\S]*?\*/', Token.COMMENT),  # multiline comments
        ('.',       Token.UNIDENTIFIED)
    ]

    rules = [(re.compile(r), t) for r, t in rules]

    tokens = []

    # create a mapping of [line number] to [offset of that line from the beginning of the text]
    newline = re.compile('\n')
    lines = [0] + [m.end() for m in re.finditer(newline, text)]

    i = 0
    while i < len(text):
        current_matches = []
        for regex, token_type in rules:
            m = regex.match(text, i)
            if m:
                current_matches.append((m, token_type))

        # pick the token that fits the longest match
        # if tie - pick the one defined first in the rules list
        longest_match, max_i, matched_token = None, i, None
        for match, token_type in current_matches:
            if match.end() > max_i:
                longest_match, max_i, matched_token = match, match.end(), token_type

        # calculate line and column
        line, column = None, None
        for line_idx in range(len(lines)-1):
            if lines[line_idx] <= longest_match.start() < lines[line_idx+1]:
                line, column = line_idx+1, (longest_match.start() - lines[line_idx])+1  # humans count from 1 :)
                break
        if not line:
            line, column = len(lines), (longest_match.start() - lines[-1])+1

        if matched_token != Token.COMMENT:
            if matched_token == Token.UNIDENTIFIED:
                raise LexicalErrorException("Unidentified Character '%s' (line %s column %s)" % (text[i], line, column))
            if matched_token != Token.WHITESPACE:
                if matched_token in [Token.STRING, Token.CHAR]:
                    # remove quotes at beginning and end, un-escape characters
                    tokens.append(Token(matched_token, line, column, longest_match.group()[1:-1].encode("utf8").decode("unicode_escape")))
                elif matched_token in [Token.NUM, Token.ID, Token.BINOP, Token.RELOP, Token.ASSIGN, Token.UNARY_MULTIPLICATIVE, Token.BITWISE_SHIFT, Token.INCLUDE_LIB_DIRECTIVE, Token.INCLUDE_LOCAL_DIRECTIVE]:
                    tokens.append(Token(matched_token, line, column, longest_match.group()))
                else:
                    tokens.append(Token(matched_token, line, column))
        i = longest_match.end()

    return tokens


def tests():
    def test1():
        # test token priorities: INT should not be confused with ID even if ID contains "int"
        text = "my international int ; int; pints; international;"
        res = analyze(text)

        expected = [Token.ID, Token.ID, Token.INT, Token.SEMICOLON, Token.INT, Token.SEMICOLON, Token.ID,
                    Token.SEMICOLON, Token.ID, Token.SEMICOLON]
        assert len(res) == len(expected) and all(res[i].type == expected[i] for i in range(len(res)))

    def test2():
        text = "true !||!false falsek  k||y+-a&&x"
        res = analyze(text)

        expected = [Token.TRUE, Token.NOT, Token.OR, Token.NOT, Token.FALSE, Token.ID, Token.ID, Token.OR, Token.ID,
                    Token.BINOP, Token.BINOP, Token.ID, Token.AND, Token.ID]
        assert len(res) == len(expected) and all(res[i].type == expected[i] for i in range(len(res)))

    # todo find a better way to test?
    test1()
    test2()


if __name__ == '__main__':
    tests()
