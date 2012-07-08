#!/usr/bin/env python

import hashlib
from flask import Flask, render_template, request, flash, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_user, logout_user, login_required
from loginform import LoginForm
import zmq


# some application parameters
DEBUG = True
SECRET_KEY = 'rawr!'
SESSION_PROTECTION = 'strong'
SQLALCHEMY_DATABASE_URI = 'sqlite:////var/www/localhost/htdocs/db/users.db'

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
	return 'This is main page okay<br />You may <a href="/submit">submit</a> ur data.'

@app.route('/submit')
@login_required
def submit_data():
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
	return 'Hello, %s!!1' % message



@app.route('/login', methods=['GET', 'POST'])
def login():
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
	flash('You have logged out')
	return redirect(request.args.get('next') or url_for('index'))


if __name__ == '__main__':
	app.run()

