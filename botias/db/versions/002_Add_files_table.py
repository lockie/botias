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

files = Table(
	'files', meta,
	Column('id', Integer, primary_key=True),
	Column('name', String(255)),
	Column('user_id', Integer, ForeignKey('users.id')),
	Column('date', DateTime(timezone=True)),
	Column('data', LargeBinary())
)

def upgrade(migrate_engine):
	meta.bind = migrate_engine
	files.create()

def downgrade(migrate_engine):
	meta.bind = migrate_engine
	files.drop()

