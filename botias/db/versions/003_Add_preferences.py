from sqlalchemy import *
from sqlalchemy.types import TypeDecorator, String
from migrate import *


meta = MetaData()

class JSONData(TypeDecorator):
	impl = String
	def process_bind_param(self, value, dialect):
		if value is not None:
			value = json.dumps(value)
		return value
	def process_result_value(self, value, dialect):
		if value is not None:
			value = json.loads(value)
		return value

def upgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	income_growth = Column('income_growth', Float())
	income_growth.create(users)
	pension_index = Column('pension_index', Float())
	pension_index.create(users)
	discount_rates = Column('discount_rates', JSONData())
	discount_rates.create(users)

def downgrade(migrate_engine):
	meta.bind = migrate_engine
	users = Table('users', meta, autoload=True)
	users.c.income_growth.drop()
	users.c.pension_index.drop()
	users.c.discount_rates.drop()

