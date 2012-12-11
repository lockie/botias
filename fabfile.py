#!/usr/bin/env python

import os.path
import fabric
from fabric.api import *
from fabric.utils import abort
from fabric.colors import *


PACKAGE_NAME='botias'
VENV_PATH='/var/www/'+PACKAGE_NAME
fabric.state.output['stdout'] = False
if env.user == env.local_user:
	env.user = 'administrator'

def bootstrap():
	""" Prepare bare installation for running the server """
	print blue('NB: user %s should be able to use sudo.\n\
Its unnecessary for deploy though.' % env.user)
	# detect OS
	OS = {'debian': False}
	with settings(warn_only=True):
		fabric.state.output['warnings'] = False
		result = run('uname -a | grep Debian')
		if result.return_code == 0:
			OS['debian'] = True
		fabric.state.output['warnings'] = True
	if not True in OS.values():
		abort('Unsupported OS in remote server')
	if len(OS.values()) != 1:
		abort('Unknown OS in remote server')
	# install required packages. update first
	if OS['debian']:
		sudo('apt-get update')
		run('yes | sudo apt-get install task-database-server python-dev\
			python-virtualenv libsqlite3-dev libpq-dev supervisor')
	# setup virtualenv
	sudo('mkdir -p %s' % VENV_PATH)
	sudo('chown %s %s' % (env.user, VENV_PATH))
	with cd(os.path.dirname(VENV_PATH)):
		app_dir = os.path.basename(VENV_PATH)
		sudo('rm -fr %s/*' % app_dir) # just in case
		run('virtualenv %s' % app_dir)
	# create configs
	with open('/tmp/app.conf', 'w') as f:
		f.write("""port=80
secret="CHANGE ME TO SOMETHING SECURE PLEASE"
db="sqlite://"
backend="amqp://backend"
logging="warning"
""")
	put('/tmp/app.conf', '%s/app.conf' % VENV_PATH, mode=0600)
	local('rm /tmp/app.conf')
	f = open('/tmp/%s.conf' % PACKAGE_NAME, 'w')
	f.write("""# -*- conf -*-
[program:%(package)s]
command=%(venv)s/bin/python -m %(package)s
startsecs=10
autorestart=true
stopasgroup=true
redirect_stderr=true
directory=%(venv)s
environment=PATH="%(venv)s/bin"
""" % {'package': PACKAGE_NAME, 'venv': VENV_PATH})
	f.close()
	put('/tmp/%s.conf' % PACKAGE_NAME, '/etc/supervisor/conf.d/', use_sudo=True)
	local('rm /tmp/%s.conf' % PACKAGE_NAME)
	# fix supervisord.conf (add appropriate chown)
	get('/etc/supervisor/supervisord.conf', '/tmp/supervisord.conf')
	f = open('/tmp/supervisord.conf', 'r')
	oldconf = f.readlines()
	f.close()
	local('rm /tmp/supervisord.conf')
	conf = []
	fixed = False
	for l in oldconf:
		if not 'chown' in l or not fixed:
			conf.append(l)
		if 'chmod' in l and not fixed:
			conf.append('chown=%s\n' % env.user)
			fixed = True
	f = open('/tmp/supervisord.fixed.conf', 'w')
	f.writelines(conf)
	f.close()
	put('/tmp/supervisord.fixed.conf', '/etc/supervisor/supervisord.conf', use_sudo=True)
	local('rm /tmp/supervisord.fixed.conf')
	# restart supervisor in idle mode
	sudo('kill -HUP `cat /var/run/supervisord.pid`')
	print green('Ready to deploy!')

def deploy():
	""" Create a python egg, install it on remote host & restart server"""
	# ensure everything is in place
	have_virtualenv = os.path.exists('../bin/python') and os.path.exists('../bin/pybabel')
	local('ls .git &> /dev/null && git submodule update --init --recursive ; true')
	if have_virtualenv:
		local('../bin/pybabel compile -d %s/translations' % PACKAGE_NAME)
	else:
		local('which pybabel &> /dev/null && pybabel compile -d %s/translations ; true' % PACKAGE_NAME)
	# run tests
	if have_virtualenv:
		local('../bin/python -m %s.test' % PACKAGE_NAME)
	else:
		print red('Virtualenv not found, skipping tests')
	# create a new source distribution as tarball
	local('python setup.py sdist --formats=gztar', capture=False)
	# figure out the release name and version
	dist = local('python setup.py --fullname', capture=True).strip()
	# upload the source tarball to the temporary folder on the server
	try:
		put('dist/%s.tar.gz' % dist, '/tmp/%s.tar.gz' % PACKAGE_NAME)
		run('mkdir -p /tmp/%s' % PACKAGE_NAME)
		with cd('/tmp/%s' % PACKAGE_NAME):
			run('tar xzf /tmp/%s.tar.gz' % PACKAGE_NAME)
			# uninstall previous version, if needed
			with settings(warn_only=True):
				fabric.state.output['warnings'] = False
				result = run('%s/bin/python -c "import %s"' % (VENV_PATH, PACKAGE_NAME))
				if result.return_code == 0:
					run('yes | %s/bin/pip uninstall %s' % (VENV_PATH, PACKAGE_NAME))
				fabric.state.output['warnings'] = True
			# now setup the package with our virtual environment's
			# python interpreter
			with cd('/tmp/%s/%s' % (PACKAGE_NAME, dist)):
				run('%s/bin/python setup.py install' % VENV_PATH)
		# and finally reload of the application
		run('supervisorctl restart %s' % PACKAGE_NAME)
	finally:
		# now that all is set up, delete the folder again
		run('rm -rf /tmp/%s /tmp/%s.tar.gz' % (PACKAGE_NAME, PACKAGE_NAME))

