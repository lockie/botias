from sqlalchemy import *
from migrate import *


meta = MetaData()

def upgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	limit = Column('limit', Integer())
	limit.create(users)

def downgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	users.c.limit.drop()

