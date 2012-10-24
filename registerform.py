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
	individual = BooleanField(_('Individual'),
		description=_('Are you individual or corporate user'))
	code = TextField('Code',
		[validators.Required(_('This field is required.')),
		validators.Length(min=8, max=10, message=_('Wrong length.'))]
	)
	purpose = SelectField(_('Purpose of calculation'), choices=[
		('edu', _('educational purposes')),
		('aud', _('annual audit')),
		('lst', _('introduction of the issuer in exchange listing')),
		('ipo', _('IPO entry'))
	])
	beneficiary = IntegerField(_('Approx. beneficiary count'),
		[validators.Required(_('This field is required.'))]
	)
	email = TextField(_('E-mail'),
		[validators.Required(_('This field is required.')),
		validators.Length(max=80, message=_('Wrong length.')),
		validators.Email(_('Invalid email address.'))],
		description=_('We will send you your password to this email.')
	)


	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)

