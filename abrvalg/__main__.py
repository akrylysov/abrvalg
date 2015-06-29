"""
Main
----

Command line interface.
"""
import argparse
from abrvalg import __version__ as version, interpreter


try:
    input = raw_input
except NameError:
    pass


def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-v', '--verbose', action='store_true')
    argparser.add_argument('file', nargs='?')
    return argparser.parse_args()


def interpret_file(path, verbose=False):
    with open(path) as f:
        print(interpreter.evaluate(f.read(), verbose=verbose))


def repl():
    print('Abrvalg {}. Press Ctrl+C to exit.'.format(version))
    env = interpreter.create_global_env()
    buf = ''
    try:
        while True:
            inp = input('>>> ' if not buf else '')
            if inp == '':
                print(interpreter.evaluate_env(buf, env))
                buf = ''
            else:
                buf += '\n' + inp
    except KeyboardInterrupt:
        pass


def main():
    args = parse_args()
    if args.file:
        interpret_file(args.file, args.verbose)
    else:
        repl()

if __name__ == '__main__':
    main()
