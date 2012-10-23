#!/usr/bin/env python

from flask_wtf import Form, TextField, PasswordField, BooleanField, SelectField, IntegerField, validators
from flask.ext.babel import gettext, ngettext


class RegisterForm(Form):
	name = TextField(gettext('Name'),
		[validators.Required(gettext('This field is required.')),
		validators.Length(min=2, max=25, message=gettext('Wrong length.'))]
	)
	surname = TextField(gettext('Surname'),
		[validators.Required(gettext('This field is required.')),
		validators.Length(min=2, max=35, message=gettext('Wrong length.'))]
	)
	individual = BooleanField(gettext('Individual'),
		description=gettext('Are you individual or corporate user'))
	code = TextField('Code',
		[validators.Required(gettext('This field is required.')),
		validators.Length(min=8, max=10, message=gettext('Wrong length.'))]
	)
	purpose = SelectField(gettext('Purpose of calculation'), choices=[
		('edu', gettext('educational purposes')),
		('aud', gettext('annual audit')),
		('lst', gettext('introduction of the issuer in exchange listing')),
		('ipo', gettext('IPO entry'))
	])
	beneficiary = IntegerField(gettext('Approx. beneficiary count'),
		[validators.Required(gettext('This field is required.'))]
	)
	email = TextField(gettext('E-mail'),
		[validators.Required(gettext('This field is required.')),
		validators.Length(max=80, message=gettext('Wrong length.')),
		validators.Email(gettext('Invalid email address.'))],
		description=gettext('We will send you your password to this email.')
	)


	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)

