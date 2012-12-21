#!/usr/bin/env python

from botias import init_app


if __name__ == '__main__':
	import os.path
	from tornado.options import parse_config_file, parse_command_line, options, define
	from tornado.wsgi import WSGIContainer
	from tornado.httpserver import HTTPServer
	from tornado.ioloop import IOLoop
	from tornado import autoreload
	import logging

	define("port",
		default=80,
		help="Run on the given port",
		metavar="PORT",
		type=int)
	define("debug",
		default=False,
		help="Run in debug mode")
	define("secret",
		help="Secret key used to hash passwords",
		metavar="STRING",
		type=str)
	define("db",
		default="sqlite://",
		help="Database URI (SQLAlchemy format)",
		metavar="URI",
		type=str)
	define("upload",
		default="/tmp",
		help="Upload folder for user files",
		metavar="PATH",
		type=str)
	define("maxsize",
		default=50000000,
		help="Maximum allowed upload file size, bytes",
		metavar="SIZE",
		type=int)
	define("backend",
		default="server",
		help="Backend hostname/ipaddr or AMQP URI",
		metavar="ADDR",
		type=str)
	define("admin",
		default="botias@pac.kiev.ua",
		help="Default administrator email (login and password too)",
		metavar="LOGIN",
		type=str)
	if os.path.exists("app.conf"):
		parse_config_file("app.conf")
	parse_command_line()

	app = init_app(
		DEBUG=options.debug,
		SECRET_KEY=options.secret,
		SQLALCHEMY_DATABASE_URI=options.db,
		UPLOAD_FOLDER=options.upload,
		MAX_CONTENT_LENGTH=options.maxsize,
		BACKEND_ADDRESS=options.backend,
		DEFAULT_ADMIN=options.admin
	)
	if options.debug:
		from werkzeug.debug import DebuggedApplication
		app = DebuggedApplication(app, evalex=True)
	http_server = HTTPServer(WSGIContainer(app))
	logging.info("Starting Tornado web server on port %s" % options.port)
	http_server.listen(options.port)
	if options.debug:
		logging.info("Debug mode enabled")
		autoreload.start()
	IOLoop().instance().start()

