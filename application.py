#!/usr/bin/env python

import os
import hashlib
from werkzeug import secure_filename
from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from loginform import LoginForm
import zmq


# some application parameters
DEBUG = True
SECRET_KEY = 'rawr!'
SESSION_PROTECTION = 'strong'
SQLALCHEMY_DATABASE_URI = 'sqlite:////var/www/localhost/htdocs/db/users.db'
ALLOWED_EXTENSIONS = set(['txt', 'csv', 'xls', 'xlsx'])
MAX_CONTENT_LENGTH = 64 * 1024 * 1024 # 64M
UPLOAD_FOLDER = "/tmp" # TODO : deletion?

# construct application
app = Flask(__name__)
app.config.from_object(__name__)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = 'login'


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
		content="""This is unique service for <abbr style="cursor: help;" title="averagin ur data since 2012!">calculating average</abbr>!
You may <a href="/submit">submit</a> ur data to expirience fury unleashed.""")


def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/result')
@login_required
def result():
	return 'kay'

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
	if request.method == 'POST' and 'data' in request.files:
		filename = request.files['data'].filename
		if(allowed_file(filename)):
			fn = str(current_user.get_id()) + '_' + secure_filename(filename)
			request.files['data'].save(os.path.join(
				app.config['UPLOAD_FOLDER'], fn))
			flash('submit OK')
			return redirect(url_for('result'))
	return render_template('submit.html')

	context = zmq.Context()
	socket = context.socket(zmq.REQ)
	socket.setsockopt(zmq.LINGER, 0)
	socket.connect('tcp://server:5555')
	socket.send('Hello')
	# use poll for timeout
	poller = zmq.Poller()
	poller.register(socket, zmq.POLLIN)
	if poller.poll(5*1000): # 5s timeout in milliseconds
		message = socket.recv()
	else:
		message = 'TIMEOUT'
	socket.close()
	context.term()
	return render_template('main.html', title='Results', content='Hello, %s!!1' % message)



@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated():
		flash('Already authenticated')
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
			flash('Logged OK')
			return redirect(next_url or url_for('index'))
		else:
			flash('Authentication failed')
	return render_template('login.html',
		form=form, next=next_url, username=username)

@app.route('/logout')
@login_required
def logout():
	logout_user()
	session.pop('logged_in', None)
	flash('You have logged out')
	return redirect(request.args.get('next') or url_for('index'))


if __name__ == '__main__':
	app.run()

