import sublime
from unittest import TestCase

version = sublime.version()

# https://github.com/SublimeText/UnitTesting

class TestSoftwareOffline(TestCase):

    def test_getCodeTimeSummary(self):
        codeTimeSummary = 1
        self.assertEqual(codeTimeSummary, 1)