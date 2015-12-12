Abrvalg
=======

Abrvalg is a Python-like programming language interpreter.

The project contains:

- Regular expression based lexer
- Top-down recursive descent parser
- AST-walking interpreter
- REPL

Abrvalg doesn't require any third-party libraries.

What the language looks like:

.. code-block::

    func map(arr, fn):
        r = []
        for val in arr:
            r = r + [fn(val)]
        r

    func factorial(n):
        if n <= 1:
            1
        else:
            n * factorial(n - 1)

    print(map(1...10, factorial))


You can find more examples in ``tests`` directory.

How to try it:

.. code-block::
    
    git clone https://github.com/akrylysov/abrvalg.git
    cd abrvalg
    python -m abrvalg tests/factorial.abr
