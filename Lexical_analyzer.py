import re
from Token import Token


class LexicalErrorException(Exception):
    pass


def analyze(text, original_text=None):
    """
    :returns list of tokens in the text
    raises exception in case of lexical error
    """

    if original_text is None:
        original_text = text

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
        ('=|\+=|-=|\*=|/=|%=', Token.ASSIGN),

        ('<=|>=|==|!=|<|>', Token.RELOP),
        ('\+\+', Token.INCREMENT),
        ('--', Token.DECREMENT),
        ('\+|-|\*|/|%', Token.BINOP),
        ('\*\*|//|%%', Token.UNARY_MULTIPLICATIVE),

        ('([a-zA-Z_][a-zA-Z0-9_]*)',    Token.ID),
        ('(\d+)',     Token.NUM),
        ('(0x[A-Fa-f\d]+)',     Token.NUM),  # hexadecimal number
        ('\"([^\"])*\"',   Token.STRING),
        ('\'[^\']\'', Token.CHAR),
        ('//.*\\n', Token.COMMENT),
        ('.',       Token.UNIDENTIFIED)
    ]

    rules = [(re.compile(r), t) for r, t in rules]

    tokens = []

    end = re.compile(r'.*\n')
    lines = [0]
    for m in re.finditer(end, original_text):
        lines.append(m.end())

    i = 0
    while i < len(text):

        current_matches = []
        for regex, token_type in rules:
            m = regex.match(text, i)
            if m:
                current_matches.append((m, token_type, m.span()))

        # pick the token that fits the longest match
        # if tie - pick the one defined first in the rules list
        longest_match = None
        max_i = i
        matched_token = None
        match_span = None
        for match, token_type, span in current_matches:
            if match.end() > max_i:
                longest_match = match
                max_i = match.end()
                matched_token = token_type
                match_span = span

        if matched_token != Token.COMMENT:
            if matched_token == Token.UNIDENTIFIED:
                line_no = len(lines)
                try:
                    for x in range(len(lines)-1):
                        item = lines[x]
                        next_item = lines[x+1]
                        if max_i in list(range(item, next_item)):
                            line_no = x+1
                except StopIteration:
                    pass

                line_col = match_span[0] - lines[line_no-1]

                raise LexicalErrorException("Unidentified Character '%s' (line %s column %s)" % (text[i], line_no, line_col))
            if matched_token != Token.WHITESPACE:
                if matched_token in [Token.STRING, Token.CHAR]:
                    tokens.append(Token(matched_token, longest_match.group()[1:-1]))  # remove quotes at beginning and end
                elif matched_token in [Token.NUM, Token.ID, Token.BINOP, Token.RELOP, Token.ASSIGN, Token.UNARY_MULTIPLICATIVE]:
                    tokens.append(Token(matched_token, longest_match.group()))
                else:
                    tokens.append(Token(matched_token))
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
