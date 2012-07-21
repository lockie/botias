#!/usr/bin/env python

import pika
import uuid
from time import time


class RpcClient(object):
	def __init__(self, host, timeout=5):
		# TODO : handle RabbitMQ non-availability
		self.connection = pika.BlockingConnection(pika.ConnectionParameters(
			host=host))
		self.channel = self.connection.channel()
		result = self.channel.queue_declare(exclusive=True,
			durable=True) # dont loose messages when RabbitMQ restarts or otherwise dies
		self.callback_queue = result.method.queue
		self.channel.basic_consume(self.on_response, no_ack=True,
			queue=self.callback_queue)
		self.responses = { }
		self.timeout = timeout

	def on_response(self, ch, method, props, body):
		self.responses[props.correlation_id] = body

	def wait_response(self, corr_id):
		# wait till we get response with correct correlation id
		begin = time()
		while corr_id not in self.responses:
			self.connection.process_data_events()
			if time() - begin > self.timeout:
				return 'Connection to server timed out. Try again later.'
		return self.responses.pop(corr_id)

	def call(self, username, data):
		# generate unique correlation id for each request
		corr_id = username + '-' + str(uuid.uuid4())
		self.channel.basic_publish(
			exchange='',
			routing_key='rpc_queue',
			properties=pika.BasicProperties(
				reply_to=self.callback_queue,
				correlation_id=corr_id,
				delivery_mode=2,  # make message persistent
			),
			body=str(data)  # TODO : proper serialization
		)
		return self.wait_response(corr_id)

