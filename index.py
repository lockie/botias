#!/usr/bin/python

from application import app

#def app(environ, start_response): # simple test; works always
#	start_response('200 OK', [('Content-Type', 'text/plain')])
#	return ['Hello, world!']

if __name__ == '__main__':
	from flup.server.fcgi import WSGIServer
	from werkzeug.contrib.fixers import LighttpdCGIRootFix
	WSGIServer(LighttpdCGIRootFix(app)).run()

