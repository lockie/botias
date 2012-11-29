#!/usr/bin/env python

from flask_wtf import Form, TextField, DecimalField, PasswordField, validators
from flask.ext.babel import lazy_gettext as _


class ProfileForm(Form):
	name = TextField(_('Name'),
		[validators.Required(),
		validators.Length(min=2, max=25, message=_('Wrong length.'))]
	)
	surname = TextField(_('Surname'),
		[validators.Required(_('This field is required.')),
		validators.Length(min=2, max=35, message=_('Wrong length.'))]
	)

#	password = PasswordField('Password', [validators.Required()])

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)


class CalcForm(Form):
	income = DecimalField(_('Annual income growth rate'),
		[validators.Required()])
	pension = DecimalField(_('Annual pension indexation rate'),
		[validators.Required()])

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)


class ActuarialForm(Form):

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)

