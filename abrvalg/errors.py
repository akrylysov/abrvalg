"""
Errors
------

Exceptions and exception helpers.
"""


class AbrvalgSyntaxError(Exception):

    def __init__(self, message, line, column):
        super(AbrvalgSyntaxError, self).__init__(message)
        self.message = message
        self.line = line
        self.column = column


def report_syntax_error(lexer, error):
    line = error.line
    column = error.column
    source_line = lexer.source_lines[line - 1]
    print('Syntax error: {} at line {}, column {}'.format(error.message, line, column))
    print('{}\n{}^'.format(source_line, ' ' * (column - 1)))
