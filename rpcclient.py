#!/usr/bin/env python

from pika import BasicProperties
from time import time
import uuid


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
		print header.correlation_id, body
		self.responses[header.correlation_id] = body

	def wait_response(self, corr_id):
		# wait till we get response with correct correlation id
		begin = time()
		while corr_id not in self.responses:
			# TODO : have to return to IO loop here
			if time() - begin > self.timeout:
				return None
		return self.responses.pop(corr_id)

	def call(self, user, data):
		# generate unique correlation id for each request
		corr_id = user + '-' + str(uuid.uuid4())
		self.channel.basic_publish(
			exchange='',
			routing_key='rpc_queue',
			properties=BasicProperties(
				reply_to=self.callback_queue,
				correlation_id=corr_id,
				delivery_mode=2,  # make message persistent
			),
			body=data)
		return self.wait_response(corr_id)

