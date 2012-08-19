#!/usr/bin/env python

import os
import time
import hashlib
from werkzeug import secure_filename
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.bootstrap import Bootstrap
import bson
from loginform import LoginForm
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
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = 'login'
rpc = RpcClient('server')


# define User object

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True)
	password = db.Column(db.String(80))

	def __init__(self, id, username, password):
		self.id = id
		self.username = username
		self.password = password

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
	return render_template('main.html',
		title='Super averaging application',
		content="""<div class="hero-unit">This is unique service for <abbr style="cursor: help;" title="averagin ur data since 2012!">calculating average</abbr>!
To expirience fury unleashed, you may<br /><br /><a href="/submit" class="btn btn-primary">Submit ur data now!</a></div>""")


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
				'Error: no file submitted! <a href="/submit">Submit</a> one.')

		data = {}
		try:
			import xlrd
			workbook = xlrd.open_workbook(file_path)
			for sheet in workbook.sheets():
				for rown in range(sheet.nrows):
					row = sheet.row_values(rown)
					data[row[0]] = row[1]
		except Exception as e:
			return jsonify(result='Error: %s. Try fixing your file.' % str(e))
		finally:
			if os.path.exists(file_path) and os.path.isfile(file_path):
				os.remove(file_path)

		resp = rpc.call(current_user.username, bson.dumps(data))
		return jsonify(result=resp)
	except Exception as e:
		return jsonify(result='Error: %s. Contact administration.' % str(e))

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
			fn = str(current_user.get_id()) + '_' + str(time.time()) + '_' + secure_filename(filename)
			path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
			session['current_file'] = path
			request.files['data'].save(path)
			flash('Submit OK', 'success')
			return redirect(url_for('result'))
		else:
			flash('Files of this type are not allowed to upload', 'error')
	return render_template('submit.html', title='Submit data')


@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated():
		flash('Already authenticated', 'warning')
		return redirect(request.referrer or url_for('index'))

	# TODO : https
	form = LoginForm()
	username = ''
	next_url = request.args.get('next')
	if form.validate_on_submit():
		username = request.form['username']
		password = request.form['password']
		user = User.query.filter_by(username=username,
			# sha224(password + salt)
			password=hashlib.sha224(password + app.secret_key).hexdigest()).first()
		if user and login_user(user, remember=True):
			session['logged_in'] = True
			flash('Logged OK', 'success')
			return redirect(next_url or url_for('index'))
		else:
			flash('Authentication failed', 'error')
	return render_template('login.html', title='Login',
		form=form, next=next_url, username=username)

@app.route('/logout')
@login_required
def logout():
	logout_user()
	session.pop('logged_in', None)
	flash('You have logged out', 'information')
	return redirect(request.args.get('next') or url_for('index'))

@login_manager.unauthorized_handler
def unauthorized():
	flash('Please authorize to access this page', 'warning')
	return redirect(url_for('login', next=request.url))

if __name__ == '__main__':
	app.run()

