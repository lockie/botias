#!/usr/bin/env python

from flask import Flask
import zmq


# some application parameters
DEBUG = True

# construct application
app = Flask(__name__)
app.config.from_object(__name__)


@app.route('/')
def hello_world():
	context = zmq.Context()
	socket = context.socket(zmq.REQ)
	socket.setsockopt(zmq.LINGER, 0)
	socket.connect('tcp://server:5555')
	socket.send('Hello')
	# use poll for timeout
	poller = zmq.Poller()
	poller.register(socket, zmq.POLLIN)
	if poller.poll(5*1000): # 5s timeout in milliseconds
		message = socket.recv()
	else:
		message = 'TIMEOUT'
	socket.close()
	context.term()
	return 'Hello, %s!!1' % message

if __name__ == '__main__':
	app.run()

