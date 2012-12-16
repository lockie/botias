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
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.bootstrap import Bootstrap
from flask.ext.babel import Babel, gettext
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
	# init backend connection
	rpc = RpcClient(app.config['BACKEND_ADDRESS'])
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
	if current_user is not None and not current_user.is_anonymous:
		return current_user.locale
	# otherwise try to guess the language from the user accept
	# header the browser transmits. The best match wins.
	return request.accept_languages.best_match(['ru', 'uk', 'en'])

@babel.timezoneselector
def get_timezone():
	if current_user is not None and not current_user.is_anonymous:
		return current_user.timezone

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

class User(database.Model):
	__tablename__ = 'users'
	id = database.Column(database.Integer, primary_key=True)
	name = database.Column(database.String(25))
	surname = database.Column(database.String(35))
	corporate = database.Column(database.Boolean())
	code = database.Column(database.String(10))
	purpose = database.Column(database.SmallInteger())
	beneficiary = database.Column(database.Integer())
	email = database.Column(database.String(80), unique=True)
	password = database.Column(database.String(56))
	files = database.relationship('SourceFile',
		order_by='SourceFile.date')

	def __init__(self, name, surname, corporate, code, purpose, beneficiary, email, password):
		self.name = name
		self.surname = surname
		self.corporate = corporate
		self.code = code
		self.purpose = purpose
		self.beneficiary = int(beneficiary)
		self.email = email
		self.password = password
		self.locale = "ru"

	def is_active(self):
		return True

	def get_id(self):
		return self.id

	def is_anonymous(self):
		return False

	def is_authenticated(self):
		return True

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
		seed(code)
		password = ''.join([choice(string.letters + string.digits) for i in range(8)])
		user = User(name,
			surname,
			corporate,
			code,
			purpose,
			beneficiary,
			email,
			hashlib.sha224(password + app.secret_key).hexdigest()
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

@app.route('/prefs', methods=['GET', 'POST'])
@login_required
def preferences():
	action = request.args.get('act')
	if action == 'profile':
		flash(gettext('Profile parameters saved'), 'success')
	elif action == 'calc':
		flash(gettext('Calculation parameters saved'), 'success')
	elif action == 'actuarial':
		flash(gettext('Actuarial parameters saved'), 'success')

	profile_form = ProfileForm()
	calc_form = CalcForm()
	actuarial_form = ActuarialForm()
	profile_form.name.default = current_user.name
	profile_form.surname.default = current_user.surname
	# TODO : non-fake, actual data
	actuarial_form.discount_rates = [ [2010, "15,00%"], [2011, "14,00%"], [2012, "13,00%"] ]
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

