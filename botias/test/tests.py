#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

from tornado.testing import AsyncTestCase, LogTrapTestCase
try:
	from webtest import TestApp
except ImportError:
	print 'Please install WebTest'
	exit(1)
try:
	from mock import MagicMock
except ImportError:
	print 'Please install mock'
	exit(1)
try:
	import BeautifulSoup
except ImportError:
	print 'Please install BeautifulSoup'
	exit(1)
from botias import init_app


SECRET_KEY='testing'
TEST_MAIL='test@axiomlogic.ru'
TEST_PASSWORD='test'

class BaseTestCase(AsyncTestCase, LogTrapTestCase):
	""" Base class for all test cases.
	We need to derive from AsyncTestCase for it creates tornado IOLoop
	impicitly.
	"""
	def __init__(self, *args, **kwargs):
		AsyncTestCase.__init__(self, *args, **kwargs)

	def setUp(self):
		AsyncTestCase.setUp(self)
		app = init_app(TESTING=True,
			SECRET_KEY=SECRET_KEY,
			SQLALCHEMY_DATABASE_URI='sqlite://',
			UPLOAD_FOLDER='/tmp',
			BACKEND_ADDRESS=''
		)
		from botias import database as db, User, rpc
		if User.query.count() != 0:
			User.query.delete()
		import hashlib
		db.session.add(User('Test', 'Test', True, '12345678', 'edu', 10,
			TEST_MAIL, hashlib.sha224(TEST_PASSWORD+SECRET_KEY).hexdigest()))
		db.session.commit()
		if rpc.connection is None:
			rpc.call = MagicMock(return_value=None)
			rpc.result = MagicMock(return_value={'error': 'Just testing.'})
		#self.app = flaskr.app.test_client()
		self.app = TestApp(app)

	def get_csrf_token(self, url):
		resp = self.app.get(url)
		csrf_token = resp.html.form.find('input', {'id': 'csrf_token'})['value']
		return {'csrf_token': csrf_token}

	def login(self, email=TEST_MAIL, password=TEST_PASSWORD):
		self.app.post('/login',
			dict({'email': email, 'password': password},
				**self.get_csrf_token('/login')))
		resp = self.app.get('/office')
		self.assertIn('success', resp.body, 'Login broken')

	def tearDown(self):
		AsyncTestCase.tearDown(self)


class LayoutCase(BaseTestCase):
	def __init__(self, *args, **kwargs):
		BaseTestCase.__init__(self, *args, **kwargs)

	def test_mainpage(self):
		resp = self.app.get('/')
		self.assertEqual(resp.status, '302 FOUND', 'Main page didnt redirect')
		self.assertEqual(resp.headers['Location'].split('/')[-1], 'about',
			'Wrong redirect for anonymous')
		resp = resp.follow()
		self.assertIn('hero-unit', resp.body, 'No hero unit in main page')

	def test_mainpaige_logged(self):
		self.login()
		resp = self.app.get('/')
		self.assertEqual(resp.headers['Location'].split('/')[-1], 'office',
			'Wrong redirect for logged user')

	def test_office(self):
		self.login()
		resp = self.app.get('/office')
		self.assertIn('static/test.xls', resp.body, 'No link to test file')

	def test_header(self):
		resp = self.app.get('/').follow()
		self.assertIn('navbar-fixed-top', resp.body, msg='No naviagtion bar')

	def test_footer(self):
		resp = self.app.get('/').follow()
		self.assertIn('<footer', resp.body, msg='No footer tag')

	def test_menu(self):
		resp = self.app.get('/').follow()
		links = []
		for ul in resp.html.findAll('ul', 'dropdown-menu'):
			links += [li.a['href'] for li in ul.findAll('li')]
		self.assertIn(u'/faq', links, msg='No FAQ link in menu')
		self.assertIn(u'/docs', links, msg='No docs link in menu')
		self.assertIn(u'/tos', links, msg='No TOS link in menu')
		self.assertIn(u'/login', links, msg='No login link in menu')
		self.assertIn(u'/register', links, msg='No register link in menu')

	def test_menu_logged(self):
		self.login()
		resp = self.app.get('/').follow()
		links = []
		for ul in resp.html.findAll('ul', 'dropdown-menu'):
			links += [li.a['href'] for li in ul.findAll('li') if len(li) > 0]
		self.assertIn(u'/office', links, msg='No office link in menu')
		self.assertIn(u'/prefs', links, msg='No preferences link in menu')
		self.assertIn(u'/logout', links, msg='No logout link in menu')

	def test_l10n(self):
		resp = self.app.get('/').follow()
		self.assertIn('About service', resp.body,
			'No english heading in main page')
		resp = self.app.get('/').follow(
			headers={'Accept-Language': 'ru-ru,ru;q=0.8;en;q=0.1'})
		self.assertIn('О сервисе', resp.body,
			'No russian heading in main page')


class RegisterCase(BaseTestCase):
	""" Addresses #24 passingly.
	"""
	def __init__(self, *args, **kwargs):
		BaseTestCase.__init__(self, *args, **kwargs)

	def register(self, email, name=u'Иван', surname=u'Иванов',
			code='1234567890', purpose='edu', beneficiary='10'):
		resp = self.app.post('/register', dict({
			'name': name,
			'surname': surname,
			'code': code,
			'purpose': purpose,
			'beneficiary': beneficiary,
			'email': email},
			**self.get_csrf_token('/register')))
		self.assertIn('Registration successeful', resp.body,
			'Registration failed')
		passw = resp.html.find('p', {'class': 'lead text-success'}
			).contents[2].split(' ')[6][:-1]
		return passw

	def test_register(self):
		email = 'test2@axiomlogic.ru'
		self.login(email, self.register(email))

	def test_double_register(self):
		""" Ensure user e-mail addresses are unique (addresses #27)
		"""
		email = 'test2@axiomlogic.ru'
		self.register(email)
		resp = self.app.post('/register', dict({
			'name': 'Ivan',
			'surname': 'Ivanov',
			'code': '1234567890',
			'purpose': 'edu',
			'beneficiary': '10',
			'email': email},
			**self.get_csrf_token('/register')))
		self.assertIn('already exists', resp, 'User e-mails are not unique')


class DoubleLoginCase(BaseTestCase):
	""" Check bug #15
	"""
	def __init__(self, *args, **kwargs):
		BaseTestCase.__init__(self, *args, **kwargs)

	def test_double_login(self):
		form1 = self.app.get('/login').form
		form2 = self.app.get('/login').form
		form1['email'] = TEST_MAIL
		form1['password'] = TEST_PASSWORD
		form1.submit()
		form2['email'] = TEST_MAIL
		form2['password'] = TEST_PASSWORD
		resp = form2.submit(headers={'Referer': 'http://localhost:80/login'})
		self.assertNotIn('login', resp, 'Infinite redirect at login')

	def test_double_logout(self):
		""" Not a bug really, but looks strange to user
		"""
		params = dict({'email': TEST_MAIL, 'password': TEST_PASSWORD})
		params.update(**self.get_csrf_token('/login'))
		params.update({'next': 'http://localhost:80/logout'})
		resp = self.app.post('/login?next=/logout', params)
		self.assertNotIn('logout', resp, 'Infinite redirect at logout')


from os.path import dirname, realpath, join

class SubmitCase(BaseTestCase):
	def __init__(self, *args, **kwargs):
		BaseTestCase.__init__(self, *args, **kwargs)

	def test_submit(self):
		""" Check file submission and whole protocol
		"""
		self.login()
		form = self.app.get('/office').form
		fn = join(dirname(realpath(__file__)), 'file1.xls')
		file = open(fn)
		data = file.read()
		file.close()
		self.assertIn('success',
			form.submit('/submit', upload_files=[('data', fn, data)]).follow(),
			'File upload broken')
		self.app.get('/result?id=0&file=2')
		self.assertIs(self.app.post('/_process', {'id': '0', 'file': '2'}).json[u'result'],
				None, 'POST _process URL handler broken')
		self.assertEqual(self.app.get('/_process').json[u'error'],
				'Just testing.', 'GET _process URL handler broken')
		# TODO : test some actual BSON got from mock?

	def test_submit_single(self):
		self.login()
		form = self.app.get('/office').form
		fn = join(dirname(realpath(__file__)), 'file2.xls')
		file = open(fn)
		data = file.read()
		file.close()
		self.assertIn('success',
			form.submit('/submit', upload_files=[('data', fn, data)]).follow(),
			'File upload broken')
		self.app.get('/result?id=2&file=3')
		self.assertIs(self.app.post('/_process', {'id': '0', 'file': '3'}).json[u'result'],
				None, 'POST _process URL handler broken')
		self.assertEquals(self.app.get('/_process').json[u'error'],
				'Just testing.', 'GET _process URL handler broken')

	def test_broken_file(self):
		self.login()
		form = self.app.get('/office').form
		fn = realpath(__file__)
		file = open(fn)
		data = file.read()
		file.close()
		self.assertIn('success',
			form.submit('/submit',
				upload_files=[('data', '/test.xls', data)]).follow(),
				'File upload broken')
		self.app.get('/result?id=10&file=1')
		self.assertIn('Try fixing your file',
			self.app.post('/_process', {'id': '0', 'file': '1'}),
			'Corrupted file slipped validation')


class DbMigrationCase(BaseTestCase):
	def __init__(self, *args, **kwargs):
		BaseTestCase.__init__(self, *args, **kwargs)

	db = '/tmp/test.db'

	def cleanup(self):
		import os, os.path
		if os.path.exists(self.db):
			os.remove(self.db)

	def setUp(self):
		BaseTestCase.setUp(self)
		self.cleanup()

	def test_migration_is_actual(self):
		# create DB with latest migration
		from migrate.versioning.api import version_control, upgrade
		from botias.db import REPOSITORY
		dbname = 'sqlite:///'+self.db
		version_control(dbname, REPOSITORY)
		upgrade(dbname, REPOSITORY)
		from sqlalchemy import create_engine, MetaData
		engine = create_engine(dbname)
		metadata = MetaData(bind=engine)
		metadata.reflect(engine)
		# compare it with actual DB schema
		from botias import database
		from migrate.versioning.schemadiff import SchemaDiff
		diff = SchemaDiff(database.metadata, metadata,
			labelA='application', labelB='migration',
			excludeTables=['migrate_version'])
		self.assertFalse(diff, str(diff))

	def test_migration(self):
		from migrate.versioning.api import version_control, version, upgrade, test
		from botias.db import REPOSITORY
		dbname = 'sqlite:///'+self.db
		version_control(dbname, REPOSITORY)
		upgrade(dbname, REPOSITORY, version=version(REPOSITORY)-1)
		test(dbname, REPOSITORY)

	def tearDown(self):
		BaseTestCase.tearDown(self)
		self.cleanup()

