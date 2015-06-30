import unittest
from abrvalg.lexer import Lexer


class LexerTest(unittest.TestCase):

    def _token_names(self, src):
        return [token[0] for token in Lexer().tokenize(src)]

    def _assertTokensEq(self, src, expected):
        return self.assertEqual(self._token_names(src), expected.split())

    def test_simple(self):
        self._assertTokensEq(
            'if x > 0: continue',
            'IF NAME OPERATOR NUMBER COLON CONTINUE NEWLINE'
        )

    def test_keyword(self):
        self._assertTokensEq(
            'xbreak x break breakx',
            'NAME NAME BREAK NAME NEWLINE'
        )

    def test_indent(self):
        src = '''1
    1
1
        1'''
        expected = 'NUMBER NEWLINE INDENT NUMBER NEWLINE DEDENT NUMBER NEWLINE INDENT INDENT NUMBER NEWLINE DEDENT ' \
                   'DEDENT'
        self._assertTokensEq(src, expected)

    def test_comments(self):
        self._assertTokensEq('#comment', '')

        self._assertTokensEq('"#not comment"', 'STRING NEWLINE')

        src1 = '''# continue
continue'''
        self._assertTokensEq(src1, 'CONTINUE NEWLINE')

        src2 = '''break
    # continue'''
        self._assertTokensEq(src2, 'BREAK NEWLINE')
