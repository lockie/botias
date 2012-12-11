from sqlalchemy import *
from migrate import *


meta = MetaData()

users = Table(
	'users', meta,
	Column('id', Integer, primary_key=True),
	Column('name', String(25)),
	Column('surname', String(35)),
	Column('corporate', Boolean()),
	Column('code', String(10)),
	Column('purpose', SmallInteger()),
	Column('beneficiary', Integer()),
	Column('email', String(80), unique=True),
	Column('password', String(56))
)

def upgrade(migrate_engine):
	meta.bind = migrate_engine
	users.create()

def downgrade(migrate_engine):
	meta.bind = migrate_engine
	users.drop()

