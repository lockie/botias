#!/usr/bin/env python

from pika import BasicProperties
from time import time
from flask.ext.babel import lazy_gettext as _


class RpcClient(object):
	def __init__(self, host, timeout=5):
		# TODO : handle RabbitMQ non-availability
		from pika import ConnectionParameters
		from pika.adapters.tornado_connection import TornadoConnection
		self.connection = TornadoConnection(
			ConnectionParameters(host=host),
			on_open_callback=self.on_connected,
			stop_ioloop_on_close=False)
		self.timeout = timeout
		self.responses = {}
		self.timeouts  = {}

	def on_connected(self, connection):
		self.channel = self.connection.channel(self.on_channel_open)

	def on_channel_open(self, new_channel):
		# recall when channel was created
		from time import gmtime, strftime
		self.callback_queue = 'rpc_queue' + strftime("%d%m%Y-%H.%M.%S", gmtime())
		self.channel.queue_declare(queue=self.callback_queue,
			callback=self.on_queue_declared,
			durable=True, exclusive=True, auto_delete=True)

	def on_queue_declared(self, frame):
		self.channel.basic_consume(self.on_response, queue=self.callback_queue)

	def on_response(self, channel, method, header, body):
		if header.correlation_id in self.timeouts:
			self.responses[header.correlation_id] = body
			self.timeouts.pop(header.correlation_id)

	def call(self, user, data):
		# generate unique correlation id for each request
		corr_id = user
		if corr_id in self.timeouts:
			return _('Server still processes your previous request. Try again a bit later.')
		if corr_id in self.responses:
			self.responses.pop(corr_id) # cleanup
		self.channel.basic_publish(
			exchange='',
			routing_key='rpc_queue',
			properties=BasicProperties(
				reply_to=self.callback_queue,
				correlation_id=corr_id,
				delivery_mode=2,  # make message persistent
			),
			body=data)
		self.timeouts[corr_id] = time()

	def result(self, user):
		corr_id = user
		if corr_id in self.responses:
			return {'result': self.responses.pop(corr_id)}
		if corr_id in self.timeouts:
			if time() - self.timeouts[corr_id] > self.timeout:
				self.timeouts.pop(corr_id)
				return {'error': _('Connection to server timed out. Try again later.')}
			else:
				return None
		else:
			return {'error': _('No request has been sent to server. Try again.')}

