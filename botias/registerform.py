#!/usr/bin/env python

from flask_wtf import Form, TextField, PasswordField, BooleanField, SelectField, IntegerField, validators
from flask.ext.babel import lazy_gettext as _


class RegisterForm(Form):
	name = TextField(_('Name'),
		[validators.Required(_('This field is required.')),
		validators.Length(min=2, max=25, message=_('Wrong length.'))]
	)
	surname = TextField(_('Surname'),
		[validators.Required(_('This field is required.')),
		validators.Length(min=2, max=35, message=_('Wrong length.'))]
	)
	corporate = BooleanField(_('Corporate'),
		description=_('Are you corporate user'))
	code = TextField('Code',
		[validators.Required(_('This field is required.')),
		validators.Length(min=8, max=10, message=_('Wrong length.'))]
	)
	purpose = SelectField(_('Purpose'), choices=[
		('edu', _('educational')),
		('aud', _('annual audit')),
		('lst', _('introduction of the issuer in exchange listing')),
		('ipo', _('IPO'))
	])
	beneficiary = IntegerField(_('Approximate number of beneficiaries'),
		[validators.Required(_('This field is required.'))]
	)
	email = TextField(_('E-mail'),
		[validators.Required(_('This field is required.')),
		validators.Length(max=80, message=_('Wrong length.')),
		validators.Email(_('Invalid email address.'))],
		description=_('Your password will be sent to this address.')
	)


	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)

