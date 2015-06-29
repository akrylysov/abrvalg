"""
Lexer
-----

Regular expression based lexer.

There is plenty of room for optimizations here.
The simplest way to make lexer faster - join all regular expressions together to one big RE.
"""
import re
from collections import namedtuple
from abrvalg.errors import AbrvalgSyntaxError as LexerError


class Token(namedtuple('Token', ['name', 'value', 'line', 'column'])):

    def __repr__(self):
        return str(tuple(self))


def decode_str(s):
    regex = re.compile(r'\\(r|n|t|\\|\'|")')
    chars = {
        'r': '\r',
        'n': '\n',
        't': '\t',
        '\\': '\\',
        '"': '"',
        "'": "'",
    }

    def replace(matches):
        char = matches.group(1)[0]
        if char not in chars:
            raise Exception('Unknown escape character {}'.format(char))
        return chars[char]

    return regex.sub(replace, s)


def decode_num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)


class Lexer(object):

    rules = [
        ('COMMENT', r'#.*'),
        ('STRING', r'"((\\"|[^"])*)"'),
        ('STRING', r"'((\\'|[^'])*)'"),
        ('NUMBER', r'\d+\.\d+'),
        ('NUMBER', r'\d+'),
        ('NAME', r'[a-zA-Z_]\w*'),
        ('WHITESPACE', '[ \t]+'),
        ('NEWLINE', '\n+'),
        ('OPERATOR', r'!'),                 # unary operator
        ('OPERATOR', r'[\+\*\-\/%]'),       # arithmetic operators
        ('OPERATOR', r'<=|>=|==|!=|<|>'),   # comparison operators
        ('OPERATOR', r'\|\||&&'),           # boolean operators
        ('OPERATOR', r'\.\.\.|\.\.'),       # range operators
        ('ASSIGN', '='),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACK', r'\['),
        ('RBRACK', r'\]'),
        ('LCBRACK', r'{'),
        ('RCBRACK', r'}'),
        ('COLON', ':'),
        ('COMMA', ','),
    ]

    keywords = {
        'func': 'FUNCTION',
        'return': 'RETURN',
        'else': 'ELSE',
        'elif': 'ELIF',
        'if': 'IF',
        'while': 'WHILE',
        'break': 'BREAK',
        'continue': 'CONTINUE',
        'for': 'FOR',
        'in': 'IN',
        'match': 'MATCH',
        'when': 'WHEN',
    }

    ignore_tokens = [
        'WHITESPACE',
        'COMMENT',
    ]

    decoders = {
        'STRING': decode_str,
        'NUMBER': decode_num,
    }

    def __init__(self):
        self.source_lines = []

    def _tokenize_line(self, line, line_num):
        end_pos = 0
        while end_pos < len(line):
            matches = None
            for name, pattern in self.rules:
                regex = re.compile(pattern)
                matches = regex.match(line, end_pos)
                if matches is not None:
                    end_pos = matches.end(0)
                    if name not in self.ignore_tokens:
                        subgroups = matches.groups()
                        if subgroups:
                            value = subgroups[0]
                        else:
                            value = matches.group(0)
                        if name in self.decoders:
                            value = self.decoders[name](value)
                        elif name == 'NAME' and value in self.keywords:
                            name = self.keywords[value]
                            value = None
                        yield Token(name, value, line_num, matches.start(0) + 1)
                    break
            if matches is None:
                raise LexerError('Unexpected character {}'.format(line[end_pos]), line_num, end_pos + 1)

    def _count_leading_characters(self, line, char):
        count = 0
        for c in line:
            if c != char:
                break
            count += 1
        return count

    def _detect_indent(self, line):
        if line[0] in [' ', '\t']:
            return line[0] * self._count_leading_characters(line, line[0])

    def tokenize(self, s):
        indent_symbol = None
        tokens = []
        last_indent_level = 0
        line_num = 0
        for line_num, line in enumerate(s.splitlines()):
            line_num += 1
            line = line.rstrip()

            if not line:
                self.source_lines.append('')
                continue

            if indent_symbol is None:
                indent_symbol = self._detect_indent(line)

            if indent_symbol is not None:
                indent_level = line.count(indent_symbol)
                line = line[indent_level*len(indent_symbol):]
            else:
                indent_level = 0

            self.source_lines.append(line)

            line_tokens = list(self._tokenize_line(line, line_num))
            if line_tokens:
                if indent_level != last_indent_level:
                    if indent_level > last_indent_level:
                        tokens.extend([Token('INDENT', None, line_num, 0)] * (indent_level - last_indent_level))
                    elif indent_level < last_indent_level:
                        tokens.extend([Token('DEDENT', None, line_num, 0)] * (last_indent_level - indent_level))
                    last_indent_level = indent_level

                tokens.extend(line_tokens)
                tokens.append(Token('NEWLINE', None, line_num, len(line) + 1))

        if last_indent_level > 0:
            tokens.extend([Token('DEDENT', None, line_num, 0)] * last_indent_level)

        return tokens


class TokenStream(object):

    def __init__(self, tokens):
        self._tokens = tokens
        self._pos = 0

    def consume_expected(self, *args):
        token = None
        for expected_name in args:
            token = self.consume()
            if token.name != expected_name:
                raise LexerError('Expected {}, got {}'.format(expected_name, token.name), token.line, token.column)
        return token

    def consume(self):
        token = self.current()
        self._pos += 1
        return token

    def current(self):
        try:
            return self._tokens[self._pos]
        except:
            last_token = self._tokens[-1]
            raise LexerError('Unexpected end of input', last_token.line, last_token.column)

    def expect_end(self):
        if self._pos != len(self._tokens):
            token = self.current()
            raise LexerError('End expected', token.line, token.column)

    def is_end(self):
        return self._pos == len(self._tokens)
