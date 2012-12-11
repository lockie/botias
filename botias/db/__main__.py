#!/usr/bin/env python

import sys
import os.path
from tornado.options import parse_config_file, options, define
from migrate.versioning.shell import main
from botias.db import REPOSITORY


if __name__ == '__main__':
	define('db')
	define('debug', type=bool)

	if os.path.exists("app.conf"):
		parse_config_file("app.conf")
	else:
		print 'Config file app.conf not found, bailing out.'
		exit(1)

	if options.db is None:
		print 'Database URI not found in config, bailing out.'
		exit(1)

	debug = options.debug or False
	uri  = options.db
	main(debug=debug, disable_logging=not debug, repository=REPOSITORY, url=uri)

