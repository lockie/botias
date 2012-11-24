#!/usr/bin/env python

from application import app

#def app(environ, start_response): # simple test; works always
#	start_response('200 OK', [('Content-Type', 'text/plain')])
#	return ['Hello, world!']

if __name__ == '__main__':
	from tornado.options import parse_config_file, parse_command_line, options, define
	from tornado.wsgi import WSGIContainer
	from tornado.httpserver import HTTPServer
	from tornado.ioloop import IOLoop
	from tornado import autoreload

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
		default="sqlite:///db/users.db",
		help="Database URI (SQLAlchemy format); defaults to sqlite:///db/users.db",
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
	parse_config_file("app.conf")
	parse_command_line()

	http_server = HTTPServer(WSGIContainer(app))
	app.config.update(
		DEBUG=options.debug,
		SECRET_KEY=options.secret,
		SQLALCHEMY_DATABASE_URI=options.db,
		UPLOAD_FOLDER=options.upload,
		MAX_CONTENT_LENGTH=options.maxsize
	)
	http_server.listen(options.port)
	if options.debug:
		autoreload.start()
	IOLoop().instance().start()

