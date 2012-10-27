#!/usr/bin/env python

import os
import time
import string
from random import choice
import hashlib
import uuid
from werkzeug import secure_filename
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.bootstrap import Bootstrap
from flask.ext.babel import Babel, gettext
import bson
from loginform import LoginForm
from registerform import RegisterForm
from preferencesform import ProfileForm, CalcForm, ActuarialForm
from rpcclient import RpcClient


# some application parameters
DEBUG = True
SECRET_KEY = 'rawr!'
SESSION_PROTECTION = 'strong'
SQLALCHEMY_DATABASE_URI = 'sqlite:////var/www/localhost/htdocs/db/users.db'
ALLOWED_EXTENSIONS = set(['txt', 'csv', 'xls', 'xlsx'])
MAX_CONTENT_LENGTH = 64 * 1024 * 1024 # 64M
UPLOAD_FOLDER = '/tmp'
BOOTSTRAP_JQUERY_VERSION = None

# construct application
app = Flask(__name__)
app.config.from_object(__name__)
babel = Babel(app)
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = 'login'
rpc = RpcClient('server')


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

# define User object

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(25))
	surname = db.Column(db.String(35))
	individual = db.Column(db.Boolean())
	code = db.Column(db.String(10))
	purpose = db.Column(db.SmallInteger())
	beneficiary = db.Column(db.Integer())
	email = db.Column(db.String(80), unique=True)
	password = db.Column(db.String(20))

	def __init__(self, name, surname, individual, code, purpose, beneficiary, email, password):
		self.name = name
		self.surname = surname
		self.individual = (individual == u'y')
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

@app.route('/_process')
@login_required
def process(): # to be called from AJAX; TODO : long polling maybe?
	try:
		file_path = session.pop('current_file', '')
		if not file_path:
	#		flash('No file submitted')
	#		return redirect(url_for('submit'))
			return jsonify(result=
				gettext('Error: no file submitted! <a href="/submit">Submit</a> one.'))

		data = {}
		try:
			import xlrd
			workbook = xlrd.open_workbook(file_path)
			for sheet in workbook.sheets():
				for rown in range(sheet.nrows):
					row = sheet.row_values(rown)
					data[row[0]] = row[1]
		except Exception as e:
			return jsonify(result=gettext('Error: %(error)s. Try fixing your file.', error=str(e)))# % { 'error': str(e)})
		finally:
			if os.path.exists(file_path) and os.path.isfile(file_path):
				os.remove(file_path)

		resp = rpc.call(current_user.email, bson.dumps(data))
		return jsonify(result=resp)
	except Exception, e:
		import sys
		e = str(sys.exc_info()[0].__name__)
		return jsonify(result=gettext('Error: %(error)s. Contact administration.', error=e))# % { 'error': e})

@app.route('/result')
@login_required
def result():
	return render_template('result.html')

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
	if request.method == 'POST' and 'data' in request.files:
		filename = request.files['data'].filename
		if(allowed_file(filename)):
			fn = str(current_user.get_id()) + '_' + str(time.time()) + '_' + str(uuid.uuid4()) + '_' + secure_filename(filename)
			path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
			session['current_file'] = path
			request.files['data'].save(path)
			flash('Submit OK', 'success')
			return redirect(url_for('result'))
		else:
			flash(gettext('Files of this type are not allowed to upload'), 'error')
	return render_template('submit.html', title='Submit data')


@app.route('/register', methods=['GET', 'POST'])
# TODO : only when anonymous
def register():
	form = RegisterForm()
	if form.validate_on_submit():
		name = request.form['name']
		surname = request.form['surname']
		individual = request.form['individual']
		code = request.form['code']
		# TODO : check code length
		purpose = ['edu', 'aud', 'lst', 'ipo'].index(request.form['purpose'])
		beneficiary = request.form['beneficiary']
		email = request.form['email']
		# TODO : check email uniqueness
		password = ''.join([choice(string.letters + string.digits) for i in range(8)])
		user = User(name,
			surname,
			individual,
			code,
			purpose,
			beneficiary,
			email,
			hashlib.sha224(password + app.secret_key).hexdigest()
		)
		# TODO : send email
		db.session.add(user)
		db.session.commit()
		return password
#		return render_template('registered.html', title=gettext('Registration successeful'), name=name, email=email)
	return render_template('register.html', title=gettext('Register'), form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated():
		flash(gettext('Already authenticated'), 'warning')
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
			flash('Logged OK', 'success')
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
	return render_template('office.html', title=gettext('My office'),
		# TODO : non-fake, actual data
		files=[{'name': '1.xls'}, {'name': '2.xls'}, {'name': '3.xls'}])

@app.route('/prefs', methods=['GET', 'POST'])
@login_required
def preferences():
	action = request.args.get('act')
	if action == 'profile':
		return 'profile parameters, like, ya know, saved'
	elif action == 'calc':
		return 'calc parameters, like, ya know, saved'
	elif action == 'actuarial':
		return 'actuarial parameters, like, ya know, saved'

	profile_form = ProfileForm()
	calc_form = CalcForm()
	actuarial_form = ActuarialForm()
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


if __name__ == '__main__':
	app.run()

