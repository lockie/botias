from sqlalchemy import *
from migrate import *


meta = MetaData()

def upgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	locale = Column('locale', String(2))
	locale.create(users)

def downgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	users.c.locale.drop()

