#!/usr/bin/env python

from flask_wtf import Form, TextField, PasswordField, validators

class LoginForm(Form):
	email = TextField('E-mail', [validators.Required()])
	password = PasswordField('Password', [validators.Required()])

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)

