#!/usr/bin/env python

from setuptools import setup
from version import get_git_version


setup(
	name='Botias',
	version=get_git_version(),
	author="Andrew Kravchuk",
	author_email="awkravchuk@gmail.com",
	url="http://www.axiomlogic.ru",
	license='commercial',
	long_description=open('README.txt').read(),
	packages=['botias',],
	scripts=['bin/botias-frontend.py',],
	include_package_data=True,
	install_requires=[
		"Babel==0.9.6",
		"Flask==0.9",
		"Flask-Babel==0.8",
		"Flask-Bootstrap==2.0.4-3",
		"Flask-Login==0.1.3",
		"Flask-SQLAlchemy==0.16",
		"Flask-WTF==0.8",
		"Jinja2==2.6",
		"SQLAlchemy==0.7.9",
		"WTForms==1.0.2",
		"Werkzeug==0.8.3",
		"bson==0.3.3",
		"pika==0.9.8",
		"pysqlite==2.6.3",
		"pytz==2012h",
		"speaklater==1.3",
		"tornado==2.4.1",
		"wsgiref==0.1.2",
		"xlrd==0.8.0",
	],

)

