#!/usr/bin/env python

from application import app

#def app(environ, start_response): # simple test; works always
#	start_response('200 OK', [('Content-Type', 'text/plain')])
#	return ['Hello, world!']

if __name__ == '__main__':
	from tornado.wsgi import WSGIContainer
	from tornado.httpserver import HTTPServer
	from tornado.ioloop import IOLoop
	http_server = HTTPServer(WSGIContainer(app))
	http_server.listen(80)
	IOLoop.instance().start()

