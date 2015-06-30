"""
Parser
------

Top-down recursive descent parser.
"""

from collections import namedtuple
from abrvalg import ast
from abrvalg.errors import AbrvalgSyntaxError


MatchPattern = namedtuple('Match', ['pattern', 'body'])
ConditionElif = namedtuple('ConditionElif', ['test', 'body'])


class ParserError(AbrvalgSyntaxError):

    def __init__(self, message, token):
        super(ParserError, self).__init__(message, token.line, token.column)


def enter_scope(parser, name):
    class State(object):
        def __enter__(self):
            parser.scope.append(name)

        def __exit__(self, exc_type, exc_val, exc_tb):
            parser.scope.pop()

    return State()


class Subparser(object):

    PRECEDENCE = {
        'call': 10,
        'subscript': 10,

        'unary': 9,

        '*': 7,
        '/': 7,
        '%': 7,

        '+': 6,
        '-': 6,

        '>': 5,
        '>=': 5,
        '<': 5,
        '<=': 5,

        '==': 4,
        '!=': 4,

        '&&': 3,

        '||': 2,

        '..': 1,
        '...': 1,
    }

    def get_subparser(self, token, subparsers, default=None):
        cls = subparsers.get(token.name, default)
        if cls is not None:
            return cls()


class PrefixSubparser(Subparser):

    def parse(self, parser, tokens):
        raise NotImplementedError()


class InfixSubparser(Subparser):

    def parse(self, parser, tokens, left):
        raise NotImplementedError()

    def get_precedence(self, token):
        raise NotImplementedError()


# number_expr: NUMBER
class NumberExpression(PrefixSubparser):

    def parse(self, parser, tokens):
        token = tokens.consume_expected('NUMBER')
        return ast.Number(token.value)


# str_expr: STRING
class StringExpression(PrefixSubparser):

    def parse(self, parser, tokens):
        token = tokens.consume_expected('STRING')
        return ast.String(token.value)


# name_expr: NAME
class NameExpression(PrefixSubparser):

    def parse(self, parser, tokens):
        token = tokens.consume_expected('NAME')
        return ast.Identifier(token.value)


# prefix_expr: OPERATOR expr
class UnaryOperatorExpression(PrefixSubparser):

    SUPPORTED_OPERATORS = ['-', '!']

    def parse(self, parser, tokens):
        token = tokens.consume_expected('OPERATOR')
        if token.value not in self.SUPPORTED_OPERATORS:
            raise ParserError('Unary operator {} is not supported'.format(token.value), token)
        right = Expression().parse(parser, tokens, self.get_precedence(token))
        if right is None:
            raise ParserError('Expected expression'.format(token.value), tokens.consume())
        return ast.UnaryOperator(token.value, right)

    def get_precedence(self, token):
        return self.PRECEDENCE['unary']


# group_expr: LPAREN expr RPAREN
class GroupExpression(PrefixSubparser):

    def parse(self, parser, tokens):
        tokens.consume_expected('LPAREN')
        right = Expression().parse(parser, tokens)
        tokens.consume_expected('RPAREN')
        return right


# array_expr: LBRACK list_of_expr? RBRACK
class ArrayExpression(PrefixSubparser):

    def parse(self, parser, tokens):
        tokens.consume_expected('LBRACK')
        items = ListOfExpressions().parse(parser, tokens)
        tokens.consume_expected('RBRACK')
        return ast.Array(items)


# dict_expr: LCBRACK (expr COLON expr COMMA)* RCBRACK
class DictionaryExpression(PrefixSubparser):

    def _parse_keyvals(self, parser, tokens):
        items = []
        while not tokens.is_end():
            key = Expression().parse(parser, tokens)
            if key is not None:
                tokens.consume_expected('COLON')
                value = Expression().parse(parser, tokens)
                if value is None:
                    raise ParserError('Dictionary value expected', tokens.consume())
                items.append((key, value))
            else:
                break
            if tokens.current().name == 'COMMA':
                tokens.consume_expected('COMMA')
            else:
                break
        return items

    def parse(self, parser, tokens):
        tokens.consume_expected('LCBRACK')
        items = self._parse_keyvals(parser, tokens)
        tokens.consume_expected('RCBRACK')
        return ast.Dictionary(items)


# infix_expr: expr OPERATOR expr
class BinaryOperatorExpression(InfixSubparser):

    def parse(self, parser, tokens, left):
        token = tokens.consume_expected('OPERATOR')
        right = Expression().parse(parser, tokens, self.get_precedence(token))
        if right is None:
            raise ParserError('Expected expression'.format(token.value), tokens.consume())
        return ast.BinaryOperator(token.value, left, right)

    def get_precedence(self, token):
        return self.PRECEDENCE[token.value]


# call_expr: NAME LPAREN list_of_expr? RPAREN
class CallExpression(InfixSubparser):

    def parse(self, parser, tokens, left):
        tokens.consume_expected('LPAREN')
        arguments = ListOfExpressions().parse(parser, tokens)
        tokens.consume_expected('RPAREN')
        return ast.Call(left, arguments)

    def get_precedence(self, token):
        return self.PRECEDENCE['call']


# subscript_expr: NAME LBRACK expr RBRACK
class SubscriptOperatorExpression(InfixSubparser):

    def parse(self, parser, tokens, left):
        tokens.consume_expected('LBRACK')
        key = Expression().parse(parser, tokens)
        if key is None:
            raise ParserError('Subscript operator key is required', tokens.current())
        tokens.consume_expected('RBRACK')
        return ast.SubscriptOperator(left, key)

    def get_precedence(self, token):
        return self.PRECEDENCE['subscript']


# expr: number_expr | str_expr | name_expr | group_expr | array_expr | dict_expr | prefix_expr | infix_expr | call_expr
#     | subscript_expr
class Expression(Subparser):

    def get_prefix_subparser(self, token):
        return self.get_subparser(token, {
            'NUMBER': NumberExpression,
            'STRING': StringExpression,
            'NAME': NameExpression,
            'LPAREN': GroupExpression,
            'LBRACK': ArrayExpression,
            'LCBRACK': DictionaryExpression,
            'OPERATOR': UnaryOperatorExpression,
        })

    def get_infix_subparser(self, token):
        return self.get_subparser(token, {
            'OPERATOR': BinaryOperatorExpression,
            'LPAREN': CallExpression,
            'LBRACK': SubscriptOperatorExpression,
        })

    def get_next_precedence(self, tokens):
        if not tokens.is_end():
            token = tokens.current()
            parser = self.get_infix_subparser(token)
            if parser is not None:
                return parser.get_precedence(token)
        return 0

    def parse(self, parser, tokens, precedence=0):
        subparser = self.get_prefix_subparser(tokens.current())
        if subparser is not None:
            left = subparser.parse(parser, tokens)
            if left is not None:
                while precedence < self.get_next_precedence(tokens):
                    op = self.get_infix_subparser(tokens.current()).parse(parser, tokens, left)
                    if op is not None:
                        left = op
                return left


# list_of_expr: (expr COMMA)*
class ListOfExpressions(Subparser):

    def parse(self, parser, tokens):
        items = []
        while not tokens.is_end():
            exp = Expression().parse(parser, tokens)
            if exp is not None:
                items.append(exp)
            else:
                break
            if tokens.current().name == 'COMMA':
                tokens.consume_expected('COMMA')
            else:
                break
        return items


# block: NEWLINE INDENT stmnts DEDENT
class Block(Subparser):

    def parse(self, parser, tokens):
        tokens.consume_expected('NEWLINE', 'INDENT')
        statements = Statements().parse(parser, tokens)
        tokens.consume_expected('DEDENT')
        return statements


# func_stmnt: FUNCTION NAME LPAREN func_params? RPAREN COLON block
class FunctionStatement(Subparser):

    # func_params: (NAME COMMA)*
    def _parse_params(self, tokens):
        params = []
        if tokens.current().name == 'NAME':
            while not tokens.is_end():
                id_token = tokens.consume_expected('NAME')
                params.append(id_token.value)
                if tokens.current().name == 'COMMA':
                    tokens.consume_expected('COMMA')
                else:
                    break
        return params

    def parse(self, parser, tokens):
        tokens.consume_expected('FUNCTION')
        id_token = tokens.consume_expected('NAME')
        tokens.consume_expected('LPAREN')
        arguments = self._parse_params(tokens)
        tokens.consume_expected('RPAREN', 'COLON')
        with enter_scope(parser, 'function'):
            block = Block().parse(parser, tokens)
        if block is None:
            raise ParserError('Expected function body', tokens.current())
        return ast.Function(id_token.value, arguments, block)


# cond_stmnt: IF expr COLON block (ELIF COLON block)* (ELSE COLON block)?
class ConditionalStatement(Subparser):

    def _parse_elif_conditions(self, parser, tokens):
        conditions = []
        while not tokens.is_end() and tokens.current().name == 'ELIF':
            tokens.consume_expected('ELIF')
            test = Expression().parse(parser, tokens)
            if test is None:
                raise ParserError('Expected `elif` condition', tokens.current())
            tokens.consume_expected('COLON')
            block = Block().parse(parser, tokens)
            if block is None:
                raise ParserError('Expected `elif` body', tokens.current())
            conditions.append(ConditionElif(test, block))
        return conditions

    def _parse_else(self, parser, tokens):
        else_block = None
        if not tokens.is_end() and tokens.current().name == 'ELSE':
            tokens.consume_expected('ELSE', 'COLON')
            else_block = Block().parse(parser, tokens)
            if else_block is None:
                raise ParserError('Expected `else` body', tokens.current())
        return else_block

    def parse(self, parser, tokens):
        tokens.consume_expected('IF')
        test = Expression().parse(parser, tokens)
        if test is None:
            raise ParserError('Expected `if` condition', tokens.current())
        tokens.consume_expected('COLON')
        if_block = Block().parse(parser, tokens)
        if if_block is None:
            raise ParserError('Expected if body', tokens.current())
        elif_conditions = self._parse_elif_conditions(parser, tokens)
        else_block = self._parse_else(parser, tokens)
        return ast.Condition(test, if_block, elif_conditions, else_block)


# match_stmnt: MATCH expr COLON NEWLINE INDENT match_when+ (ELSE COLON block)? DEDENT
class MatchStatement(Subparser):

    # match_when: WHEN expr COLON block
    def _parse_when(self, parser, tokens):
        tokens.consume_expected('WHEN')
        pattern = Expression().parse(parser, tokens)
        if pattern is None:
            raise ParserError('Pattern expression expected', tokens.current())
        tokens.consume_expected('COLON')
        block = Block().parse(parser, tokens)
        return MatchPattern(pattern, block)

    def parse(self, parser, tokens):
        tokens.consume_expected('MATCH')
        test = Expression().parse(parser, tokens)
        tokens.consume_expected('COLON', 'NEWLINE', 'INDENT')
        patterns = []
        while not tokens.is_end() and tokens.current().name == 'WHEN':
            patterns.append(self._parse_when(parser, tokens))
        if not patterns:
            raise ParserError('One or more `when` pattern excepted', tokens.current())
        else_block = None
        if not tokens.is_end() and tokens.current().name == 'ELSE':
            tokens.consume_expected('ELSE', 'COLON')
            else_block = Block().parse(parser, tokens)
            if else_block is None:
                raise ParserError('Expected `else` body', tokens.current())
        tokens.consume_expected('DEDENT')
        return ast.Match(test, patterns, else_block)


# loop_while_stmnt: WHILE expr COLON block
class WhileLoopStatement(Subparser):

    def parse(self, parser, tokens):
        tokens.consume_expected('WHILE')
        test = Expression().parse(parser, tokens)
        if test is None:
            raise ParserError('While condition expected', tokens.current())
        tokens.consume_expected('COLON')
        with enter_scope(parser, 'loop'):
            block = Block().parse(parser, tokens)
        if block is None:
            raise ParserError('Expected loop body', tokens.current())
        return ast.WhileLoop(test, block)


# loop_for_stmnt: FOR NAME expr COLON block
class ForLoopStatement(Subparser):

    def parse(self, parser, tokens):
        tokens.consume_expected('FOR')
        id_token = tokens.consume_expected('NAME')
        tokens.consume_expected('IN')
        collection = Expression().parse(parser, tokens)
        tokens.consume_expected('COLON')
        with enter_scope(parser, 'loop'):
            block = Block().parse(parser, tokens)
        if block is None:
            raise ParserError('Expected loop body', tokens.current())
        return ast.ForLoop(id_token.value, collection, block)


# return_stmnt: RETURN expr?
class ReturnStatement(Subparser):

    def parse(self, parser, tokens):
        if not parser.scope or 'function' not in parser.scope:
            raise ParserError('Return outside of function', tokens.current())
        tokens.consume_expected('RETURN')
        value = Expression().parse(parser, tokens)
        tokens.consume_expected('NEWLINE')
        return ast.Return(value)


# break_stmnt: BREAK
class BreakStatement(Subparser):

    def parse(self, parser, tokens):
        if not parser.scope or parser.scope[-1] != 'loop':
            raise ParserError('Break outside of loop', tokens.current())
        tokens.consume_expected('BREAK', 'NEWLINE')
        return ast.Break()


# cont_stmnt: CONTINUE
class ContinueStatement(Subparser):

    def parse(self, parser, tokens):
        if not parser.scope or parser.scope[-1] != 'loop':
            raise ParserError('Continue outside of loop', tokens.current())
        tokens.consume_expected('CONTINUE', 'NEWLINE')
        return ast.Continue()


# assing_stmnt: expr ASSIGN expr NEWLINE
class AssignmentStatement(Subparser):

    def parse(self, parser, tokens, left):
        tokens.consume_expected('ASSIGN')
        right = Expression().parse(parser, tokens)
        tokens.consume_expected('NEWLINE')
        return ast.Assignment(left, right)


# expr_stmnt: assing_stmnt
#           | expr NEWLINE
class ExpressionStatement(Subparser):

    def parse(self, parser, tokens):
        exp = Expression().parse(parser, tokens)
        if exp is not None:
            if tokens.current().name == 'ASSIGN':
                return AssignmentStatement().parse(parser, tokens, exp)
            else:
                tokens.consume_expected('NEWLINE')
                return exp


# stmnts: stmnt*
class Statements(Subparser):

    def get_statement_subparser(self, token):
        return self.get_subparser(token, {
            'FUNCTION': FunctionStatement,
            'IF': ConditionalStatement,
            'MATCH': MatchStatement,
            'WHILE': WhileLoopStatement,
            'FOR': ForLoopStatement,
            'RETURN': ReturnStatement,
            'BREAK': BreakStatement,
            'CONTINUE': ContinueStatement,
        }, ExpressionStatement)

    def parse(self, parser, tokens):
        statements = []
        while not tokens.is_end():
            statement = self.get_statement_subparser(tokens.current()).parse(parser, tokens)
            if statement is not None:
                statements.append(statement)
            else:
                break
        return statements


# prog: stmnts
class Program(Subparser):

    def parse(self, parser, tokens):
        statements = Statements().parse(parser, tokens)
        tokens.expect_end()
        return ast.Program(statements)


class Parser(object):

    def __init__(self):
        self.scope = None

    def parse(self, tokens):
        self.scope = []
        return Program().parse(self, tokens)
