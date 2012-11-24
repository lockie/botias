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
	define("port", default=80, help="run on the given port", type=int)
	parse_config_file("app.conf")
	parse_command_line()

	http_server = HTTPServer(WSGIContainer(app))
	http_server.listen(options.port)
	ioloop = IOLoop().instance()
	autoreload.start(ioloop)
	ioloop.start()

