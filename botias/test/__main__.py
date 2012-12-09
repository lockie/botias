#!/usr/bin/env python

from tornado import testing
import unittest


def all():
	import tests
	return unittest.defaultTestLoader.loadTestsFromModule(tests)

if __name__ == '__main__':
	testing.main()

