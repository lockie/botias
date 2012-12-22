from sqlalchemy import *
from migrate import *


meta = MetaData()

default_discount_rates = Table(
	'default_discount_rates', meta,
	Column('id', Integer(), primary_key=True),
	Column('year', Integer(), unique=True),
	Column('rate', Float())
)

def upgrade(migrate_engine):
	meta.bind = migrate_engine
	default_discount_rates.create()

def downgrade(migrate_engine):
	meta.bind = migrate_engine
	default_discount_rates.drop()

