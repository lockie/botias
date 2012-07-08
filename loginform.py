#!/usr/bin/env python

import sys
import os

sys.path += [os.path.dirname(__file__) + "/contrib/flask-wtf"]
from flask_wtf import Form, TextField, PasswordField, validators

class LoginForm(Form):
	username = TextField('Username', [validators.Required()])
	password = PasswordField('Password', [validators.Required()])

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)
		self.user = None

