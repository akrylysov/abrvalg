import unittest
import os
from abrvalg.interpreter import evaluate

TESTS_DIR = os.path.dirname(__file__)


class InterpreterTest(unittest.TestCase):

    def _evaluate(self, s):
        return evaluate(s, verbose=True)

    def _evaluate_file(self, path):
        with open(os.path.join(TESTS_DIR, path)) as f:
            return self._evaluate(f.read())

    def test_big(self):
        self.assertEqual(self._evaluate_file('factorial.abr'), 3628800)
        self.assertEqual(self._evaluate_file('merge_sort.abr'), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self._evaluate_file('big.abr')
