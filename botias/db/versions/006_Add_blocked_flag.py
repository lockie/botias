from sqlalchemy import *
from migrate import *


meta = MetaData()

def upgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	blocked = Column('blocked', Boolean())
	blocked.create(users)

def downgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	# workaround for sqlite
	# see http://code.google.com/p/sqlalchemy-migrate/issues/detail?id=143
	# and http://sqlalchemy-migrate.readthedocs.org/en/v0.7.2/#id10
	if migrate_engine.url.drivername != 'sqlite':
		users.c.blocked.drop()

