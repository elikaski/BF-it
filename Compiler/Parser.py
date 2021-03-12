from .Exceptions import BFSyntaxError, BFSemanticError
from .Token import Token


class Parser:
    """
    Used to easily iterate tokens
    """
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0

    # parsing tokens
    def current_token(self):
        if self.current_token_index >= len(self.tokens):
            return None
        else:
            return self.token_at_index(self.current_token_index)

    def advance_token(self, amount=1):
        self.current_token_index += amount

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
        elif token_to_match.type == Token.LPAREN:
            inc = Token.LPAREN
            dec = Token.RPAREN
        else:
            raise BFSemanticError("no support for matching %s" % str(token_to_match))

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

        raise BFSyntaxError("did not find matching %s for %s" % (dec, str(token_to_match)))

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
