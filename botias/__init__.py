#!/usr/bin/env python

import os
import os.path
import ntpath
import time
from datetime import datetime
import string
from random import seed, choice
import hashlib
import uuid
from werkzeug import secure_filename
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, send_file, abort
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.types import TypeDecorator, String
from sqlalchemy.orm.exc import NoResultFound
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.bootstrap import Bootstrap
from flask.ext.babel import Babel, gettext, lazy_gettext as _
from flask.ext.admin import Admin, BaseView, AdminIndexView, expose
from flask.ext.admin.contrib.sqlamodel import ModelView
from flask_debugtoolbar import DebugToolbarExtension
import bson
import json
from loginform import LoginForm
from registerform import RegisterForm
from preferencesform import ProfileForm, CalcForm, ActuarialForm
from rpcclient import RpcClient
from parse import parse_file


# some application parameters
SESSION_PROTECTION = 'strong'
ALLOWED_EXTENSIONS = set(['txt', 'csv', 'xls', 'xlsx'])
BOOTSTRAP_JQUERY_VERSION = None

# construct application
app = Flask(__name__)
app.config.from_object(__name__)
babel = Babel(app)
Bootstrap(app)
database = SQLAlchemy()
login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = 'login'
rpc = None

# administration
class AdminView(AdminIndexView):
	def __init__(self, name):
		AdminIndexView.__init__(self, name=name)

	def is_accessible(self):
		return not current_user.is_anonymous() and current_user.is_admin()

	def _handle_view(self, name, **kwargs):
		if not self.is_accessible():
			return abort(403)

	@expose()
	def index(self):
		from sqlalchemy.exc import OperationalError
		try:
			dbversion = database.session.connection().execute(
				'select version from migrate_version;').fetchone()[0]
		except OperationalError:
			dbversion = _('unknown')
		return self.render('admin.html',
			version=get_version(''),
			dbversion=dbversion,
			rpc=rpc.connection)

# user administration
class UsersView(ModelView):
	list_template = 'admin_list.html'
	edit_template = 'admin_edit.html'
	can_create = False
	searchable_columns = ['name', 'surname', 'code', 'email']
	list_columns = ('name', 'surname', 'corporate', 'code',
		'purpose', 'beneficiary', 'email', 'limit', 'admin', 'blocked')
	rename_columns = dict(name=_('Name'),
		surname=_('Surname'),
		corporate=_('Corporate'),
		code=_('Code'),
		purpose=_('Purpose'),
		beneficiary=_('Beneficiary cnt.'),
		email=_('E-mail'),
		limit=_('Limit'),
		admin=_('Admin'),
		blocked=_('Blocked')
	)
	form_columns = ('name', 'surname', 'code', 'email', 'limit', 'admin', 'blocked')

	def __init__(self, session, name):
		ModelView.__init__(self, User, session, name=name, endpoint='users')

	def is_accessible(self):
		return not current_user.is_anonymous() and current_user.is_admin()

	def _handle_view(self, name, **kwargs):
		if not self.is_accessible():
			return abort(403)

	def edit_form(self, obj=None):
		# patch WTForms to disable certain fields
		form = ModelView.edit_form(self, obj)
		from flask_wtf import TextInput, HTMLString
		class DisabledTextInput(TextInput):
			def __call__(self, field, **kwargs):
				kwargs.setdefault('id', field.id)
				kwargs.setdefault('type', self.input_type)
				if 'value' not in kwargs:
					kwargs['value'] = field._value()
				return HTMLString('<input disabled="disabled" %s>'
					% self.html_params(name=field.name, **kwargs))
		form.name.widget = DisabledTextInput()
		form.surname.widget = DisabledTextInput()
		form.code.widget = DisabledTextInput()
		form.email.widget = DisabledTextInput()
		return form

	def update_model(self, form, model):
		del form.name
		del form.surname
		del form.code
		del form.email
		return ModelView.update_model(self, form, model)

# defaults administration
class DefaultDiscountRatesView(ModelView):
	list_template = 'admin_list.html'
	edit_template = 'admin_edit.html'
	rename_columns = dict(year=_('Year'),
		rate=_('Rate'))

	def __init__(self, session, name):
		ModelView.__init__(self, DefaultDiscountRates, session, name=name, endpoint='discount_rates')

	def is_accessible(self):
		return not current_user.is_anonymous() and current_user.is_admin()

	def _handle_view(self, name, **kwargs):
		if not self.is_accessible():
			return abort(403)

admin = Admin(name=_('Botias'),
	index_view=AdminView(_('Administration')))

def init_app(**kwargs):
	global app, database, rpc
	app.config.update(kwargs)
	# init debug toolbar
	app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
	toolbar = DebugToolbarExtension(app)
	# init db
	if database.app is None:
		database.init_app(app)
		database.app = app
	# are we running sqlite?
	if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
		database.create_all()
		database.session.commit()
	# init administration
	if admin.app is None:
		admin.init_app(app)
		admin.locale_selector(get_locale)
		admin.add_view(UsersView(database.session, name=_('Users')))
		admin.add_view(DefaultDiscountRatesView(database.session, name=_('Default discount rates')))
		if database.session.query(User).filter_by(
				email=app.config['DEFAULT_ADMIN']).count() == 0:
			default_admin = User(app.config['DEFAULT_ADMIN'],
				# TODO : "your password is autogenerated" notification
				hashlib.sha224(app.config['DEFAULT_ADMIN']+app.secret_key).hexdigest(),
				'Administrator',
				admin=True)
			database.session.add(default_admin)
			database.session.commit()
	# init backend connection
	rpc = RpcClient(app.config['BACKEND_ADDRESS'], app.config['BACKEND_TIMEOUT'])
	return app

# version
@app.template_filter('version')
def get_version(s):
	import pkg_resources
	return s + pkg_resources.require("Botias")[0].version

# l10n
@babel.localeselector
def get_locale():
	# if a user is logged in, use the locale from the user settings
	if current_user is not None and not current_user.is_anonymous():
		return current_user.locale
	# otherwise try to guess the language from the user accept
	# header the browser transmits. The best match wins.
	return request.accept_languages.best_match(['ru', 'uk', 'en'])

@babel.timezoneselector
def get_timezone():
	if current_user is not None and not current_user.is_anonymous():
		return current_user.timezone

class DefaultDiscountRates(database.Model):
	__tablename__ = 'default_discount_rates'
	id = database.Column(database.Integer(), primary_key=True)
	year = database.Column(database.Integer(), unique=True)
	rate = database.Column(database.Float())

	@staticmethod
	def value():
		res = []
		for disrate in DefaultDiscountRates.query.all():
			res.append([disrate.year, disrate.rate])
		if not res:
			res = [[None, None]]
		return res

class SourceFile(database.Model):
	__tablename__ = 'files'
	id = database.Column(database.Integer, primary_key=True)
	name = database.Column(database.String(255))
	user_id = database.Column(database.Integer, database.ForeignKey('users.id'))
	# TODO : account for timezone
	date = database.Column(database.DateTime(timezone=True))
	data = database.Column(database.LargeBinary())

	def __init__(self, name, user_id, date, data):
		self.name = name
		self.user_id = user_id
		self.date = date
		self.data = data

class JSONData(TypeDecorator):
	impl = String

	def process_bind_param(self, value, dialect):
		if value is not None:
			value = json.dumps(value)
		return value

	def process_result_value(self, value, dialect):
		if value is not None:
			value = json.loads(value)
		return value

class User(database.Model):
	__tablename__ = 'users'
	id = database.Column(database.Integer, primary_key=True)
	blocked = database.Column(database.Boolean())
	admin = database.Column(database.Boolean())
	name = database.Column(database.String(25))
	surname = database.Column(database.String(35))
	corporate = database.Column(database.Boolean())
	code = database.Column(database.String(10))
	purpose = database.Column(database.SmallInteger())
	limit = database.Column(database.Integer())
	beneficiary = database.Column(database.Integer())
	email = database.Column(database.String(80), unique=True)
	password = database.Column(database.String(56))
	files = database.relationship('SourceFile',
		order_by='SourceFile.date')
	income_growth = database.Column(database.Float())
	pension_index = database.Column(database.Float())
	discount_rates = database.Column(JSONData())
	locale = database.Column(database.String(2))

	def __init__(self, email, password, name, surname='', locale='ru',
			corporate=False, code='', purpose=0, beneficiary=0,
			income=0, pension=0, disrates=[[None, None]], admin=False):
		self.blocked = False
		self.admin = admin
		self.name = name
		self.surname = surname
		self.corporate = corporate
		self.code = code
		self.purpose = purpose
		self.limit = 2
		self.beneficiary = int(beneficiary)
		self.email = email
		self.password = password
		self.income_growth = income
		self.pension_index = pension
		self.discount_rates = disrates
		self.locale = locale

	def is_active(self):
		return not self.blocked

	def get_id(self):
		return self.id

	def is_anonymous(self):
		return False

	def is_authenticated(self):
		return True

	def is_admin(self):
		return self.admin

	def __repr__(self):
		return '<User %r %r, id %d>' % (self.name, self.surname, self.id)

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(user_id)


# define URL mappings

@app.route('/')
def index():
	if current_user.is_authenticated():
		return redirect(url_for('office'))
	else:
		return redirect(url_for('about'))

def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/_process', methods=['GET', 'POST'])
@login_required
def process(): # to be called from AJAX
	try:
		if request.method == 'POST':
			if 'id' not in request.form:
				return jsonify(error=gettext('Error: no employee id given.'))
			ident = request.form['id']
			if 'file' not in request.form:
				return jsonify(error=gettext('Error: no file id given'))
			file_id = request.form['file']
			filedata = SourceFile.query.filter_by(id=file_id,
				user_id=current_user.get_id()).one().data

			data = {}
			try:
				data = parse_file(filedata, int(ident))
				if not data['rows']:
					raise Exception(gettext('No actual data'))
			except Exception as e:
				return jsonify(error=gettext(u'Error: %(error)s. Try fixing your file.', error=unicode(e.args[0])))
			if not current_user.is_admin() and \
					len(data['rows']) > current_user.limit:
				return jsonify(error=gettext(
					'Error: number of worker records in file (%(num)d) exceeds '
					'the permitted limit (%(limit)d).',
					num=len(data['rows']), limit=current_user.limit))
			data['discount_rates'] = current_user.discount_rates
			data['income_growth']  = current_user.income_growth
			data['pension_index'] = current_user.pension_index

			# TODO : find bug in mongodb BSON parser (or write our own)
			# & pass BSON instead of JSON
			resp = rpc.call(current_user.email, json.dumps(data))
			if resp is not None:
				return jsonify(error=unicode(resp))
			return jsonify(result=None)
		elif request.method == 'GET':
			resp = rpc.result(current_user.email)
			if resp is None:
				return jsonify(result=None)
			if 'error' in resp:
				return jsonify(error=unicode(resp['error']))
			r = bson.loads(resp['result'])
			result = dict(zip([str(x) for x in r.keys()], r.values()))
			if 'tab1' not in r:
				result['tX'] = [["-", "-", "-", "-"]] * 3
			return jsonify(result=result)
	except Exception, e:
		import sys
		e = str(sys.exc_info()[0].__name__)
		return jsonify(error=gettext('Error: %(error)s. Contact administration.', error=e))

@app.route('/result')
@login_required
def result():
	if 'id' not in request.args:
		flash(gettext('Error: no employee id given'), 'error')
		return redirect(request.referrer or url_for('office'))
	if 'file' not in request.args:
		flash(gettext('Error: no file id given'), 'error')
		return redirect(request.referrer or url_for('office'))
	return render_template('result.html', id=request.args['id'],
		file=request.args['file'], title=gettext('Results'))

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
	if request.method == 'POST' and 'data' in request.files:
		filename = request.files['data'].filename
		if(allowed_file(filename)):
			try:
				file = SourceFile(ntpath.basename(secure_filename(filename)),
					current_user.get_id(),
					datetime.now(),
					request.files['data'].read())
				database.session.add(file)
				database.session.commit()
				flash(gettext('File uploaded successfully'), 'success')
			except Exception, e:
				flash(gettext('Error uploading file: %(error)s.',
					error=e.args[0]), 'error')
		else:
			flash(gettext('Files of this type are not allowed to upload'), 'error')
	return redirect(url_for('office'))


@app.route('/register', methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated():
		flash(gettext('Already authenticated'), 'warning')
		return redirect(request.referrer or url_for('index'))

	form = RegisterForm()
	if form.validate_on_submit():
		name = request.form['name']
		surname = request.form['surname']
		corporate = 'corporate' in request.form and request.form['corporate'] == u'y'
		code = request.form['code']
		purpose = ['edu', 'aud', 'lst', 'ipo'].index(request.form['purpose'])
		beneficiary = request.form['beneficiary']
		email = request.form['email']
		valid = True
		if corporate and len(code) != 8:
			form.code.errors = [gettext('Corporate code length should be 8')]
			valid = False
		if not corporate and len(code) != 10:
			form.code.errors = [gettext('Individual code length should be 10')]
			valid = False
		if len(database.session.query(User).filter_by(email=email).all()) != 0:
			form.email.errors = [gettext('The user with email %(email)s already exists', email=email)]
			valid = False
		if not valid:
			return render_template('register.html', title=gettext('Register'),
				form=form, name=name, surname=surname, corporate=corporate,
				code=code, purpose=purpose, beneficiary=beneficiary, email=email)
		seed(app.secret_key+code+email+str(datetime.now()))
		password = ''.join([choice(string.letters + string.digits) for i in range(8)])
		user = User(name=name,
			surname=surname,
			corporate=corporate,
			code=code,
			purpose=purpose,
			beneficiary=beneficiary,
			email=email,
			password=hashlib.sha224(password + app.secret_key).hexdigest(),
			income=0.15, # TODO : editable defaults for income & pension
			pension=0.15,
			disrates=DefaultDiscountRates.value()
		)
		# TODO : send email
		database.session.add(user)
		database.session.commit()
		return render_template('registered.html', title=gettext('Registration successeful'), name=name, email=email, password=password)
#		return render_template('registered.html', title=gettext('Registration successeful'), name=name, email=email)
	return render_template('register.html', title=gettext('Register'), form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated():
		flash(gettext('Already authenticated'), 'warning')
		if request.referrer and 'login' in request.referrer:
			return redirect(url_for('index'))
		return redirect(request.referrer or url_for('index'))

	# TODO : https
	form = LoginForm()
	email = ''
	next_url = request.args.get('next')
	if form.validate_on_submit():
		email = request.form['email']
		password = request.form['password']
		user = User.query.filter_by(email=email,
			# sha224(password + salt)
			password=hashlib.sha224(password + app.secret_key).hexdigest()).first()
		if user and not user.is_active():
			flash(gettext('Your account have been blocked by administrator.'), 'warning')
			return redirect(next_url or url_for('index'))
		if user and login_user(user, remember=True):
			session['logged_in'] = True
			flash(gettext('Authentication successeful'), 'success')
			if next_url and 'logout' in next_url:
				return redirect(url_for('index'))
			return redirect(next_url or url_for('index'))
		else:
			flash(gettext('Authentication failed. Check login and password.'), 'error')
	return render_template('login.html', title=gettext('Login'),
		form=form, next=next_url, email=email)

@app.route('/logout')
@login_required
def logout():
	logout_user()
	session.pop('logged_in', None)
	flash(gettext('You have logged out'), 'information')
	return redirect(request.args.get('next') or url_for('index'))

@login_manager.unauthorized_handler
def unauthorized():
	flash(gettext('Please authorize to access this page'), 'warning')
	return redirect(url_for('login', next=request.url))

@app.route('/office')
@login_required
def office():
	files = []
	for f in SourceFile.query.filter_by(user_id=current_user.get_id()):
		files.append({'id': f.id, 'name': f.name})
	return render_template('office.html', title=gettext('My office'), files=files)

@app.route('/_errors')
@login_required
def errors():
	if 'id' not in request.args:
		return jsonify(error=gettext('Error: no file id given'))
	file_id = request.args['id']
	try:
		filedata = SourceFile.query.filter_by(id=file_id,
			user_id=current_user.get_id()).one().data
	except NoResultFound:
		return jsonify(error=gettext('Error: file not found'))
	try:
		data = parse_file(filedata, 0)
		if not data['rows']:
			raise Exception(gettext('Error: file is empty'))
	except Exception as e:
		return jsonify(error=gettext(u'Error: %(error)s. ',
			error=unicode(e.args[0])))
	result=[]
	for row in data['rows']:
		if 'data' in row:
			res = 'OK'
		else:
			res = row['error']
		result.append([row['id'], res])
	result.sort(key=lambda x: int(x[0]))
	return jsonify(result=result)

@app.route('/remove') # TODO : it should be POST request (like many others)
@login_required
def remove():
	if 'id' not in request.args:
		flash(gettext('Error: no file id given'), 'error')
		return redirect(request.referrer or url_for('office'))
	file_id = request.args['id']
	try:
		f = SourceFile.query.filter_by(id=file_id,
			user_id=current_user.get_id()).one()
	except NoResultFound:
		flash(gettext('Error: file not found'), 'error')
		return redirect(request.referrer or url_for('office'))
	name = f.name
	database.session.delete(f)
	database.session.commit()
	flash(gettext('File "%(name)s" was successefully removed.', name=name),
		'information')
	return redirect(request.referrer or url_for('office'))

@app.route('/download')
@login_required
def download():
	if 'id' not in request.args:
		flash(gettext('Error: no file id given'), 'error')
		return redirect(request.referrer or url_for('office'))
	file_id = request.args['id']
	try:
		f = SourceFile.query.filter_by(id=file_id,
			user_id=current_user.get_id()).one()
		filedata = f.data
		filename = f.name
	except NoResultFound:
		flash(gettext('Error: file not found'), 'error')
		return redirect(request.referrer or url_for('office'))
	from StringIO import StringIO
	return send_file(StringIO(filedata), mimetype='application/vnd.ms-excel',
		as_attachment=True, attachment_filename=filename)

def validate_discount_rates(rates):
	result = []
	if type(rates) is not list:
		raise RuntimeError(gettext('Incorrect data')) # being paranoid today
	years = set()
	for rate in rates:
		if type(rate) is not list or len(rate) != 2:
			raise RuntimeError(gettext('Incorrect data'))
		if rate[0] is None and rate[1] is None:
			continue
		if rate[0] is None:
			raise RuntimeError(gettext(u'No year given for percentage %(per)s',
				per=str(rate[1])))
		if rate[1] is None:
			raise RuntimeError(gettext(u'No percentage for year %(year)s',
				year=str(rate[0])))
		try:
			year = int(rate[0])
		except ValueError:
			raise RuntimeError(gettext(u'Invalid year: %(year)s',
				year=str(rate[0])))
		percentage = str(rate[1]).replace('%', '')
		from parse import MIN_YEAR
		from datetime import datetime
		if year < MIN_YEAR or year > datetime.now().year+2:
			raise RuntimeError(gettext(u'Invalid year: %(year)s',
				year=str(year)))
		if year in years:
			raise RuntimeError(gettext('Duplicate year %(year)d',
				year=year))
		years.add(year)
		try:
			percentage = float(percentage)
		except ValueError:
			raise RuntimeError(gettext(
				u'Invalid discount rate: %(rate)s. '
				u'Use dot to separate the fractional part.',
				rate=rate[1]))
		result.append([year, percentage])
	return result

@app.route('/prefs', methods=['GET', 'POST'])
@login_required
def preferences():
	profile_form = ProfileForm(name=current_user.name,
		surname=current_user.surname, formdata=None)
	calc_form = CalcForm(income=current_user.income_growth,
		pension=current_user.pension_index, formdata=None)
	actuarial_form = ActuarialForm(
		discount_rates=current_user.discount_rates or [[None, None]],
		formdata=None)
	if request.method == 'POST':
		action = request.args.get('act')
		if action == 'profile':
			profile_form = ProfileForm(request.form)
			if profile_form.validate():
				current_user.name = request.form['name']
				current_user.surname = request.form['surname']
				database.session.commit()
				flash(gettext('Profile parameters saved'), 'success')
		elif action == 'calc':
			calc_form = CalcForm(request.form)
			if calc_form.validate():
				current_user.income_growth = request.form['income']
				current_user.pension_index = request.form['pension']
				database.session.commit()
				flash(gettext('Calculation parameters saved'), 'success')
		elif action == 'actuarial':
			actuarial_form = ActuarialForm(request.form)
			if actuarial_form.validate():
				try:
					actuarial_form.discount_rates.data = json.loads(
						request.form['discount_rates'])
					current_user.discount_rates = validate_discount_rates(
						actuarial_form.discount_rates.data)
					database.session.commit()
					flash(gettext('Actuarial parameters saved'), 'success')
				except Exception, e:
					actuarial_form.discount_rates.errors = [e.args[0]]
	return render_template('preferences.html', title=gettext('Preferences'),
		profile_form=profile_form, calc_form=calc_form, actuarial_form=actuarial_form)

# static pages
@app.route('/tos')
def tos():
	return render_template('tos.html', title=gettext('Terms of service'))

@app.route('/about')
def about():
	return render_template('about.html', title=gettext('About service'))

@app.route('/docs')
def docs():
	# TODO : get document desciption & other info from DB,
	# allow admins to upload/edit them.
	return render_template('docs.html', title=gettext('Documentation'))

@app.route('/faq')
def faq():
	return render_template('faq.html', title=gettext('Frequently asked questions'))

