#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import xlrd
from flask.ext.babel import lazy_gettext as _


MIN_YEAR = 1990
MIN_BIRTH_YEAR = 1900
MAX_BIRTH_YEAR = 1994

class Dict(dict):
	__getattr__= dict.__getitem__
	__setattr__= dict.__setitem__
	__delattr__= dict.__delitem__

def parse_employee(workbook, id):
	# regexp for experience
	import re
	exp = re.compile(ur'(?P<years>\d+).*?[р|Р|л|Л|г|Г]{1}(.*?(?P<months>\d+).*?[м|М]{1})?(.*?(?P<days>\d+).*?[д|Д]{1})?')

	data = []
	for sheet in workbook.sheets():
		d = Dict()

		# Year
		#
		if not sheet.name.isdigit():
			raise RuntimeError(_(u'Invalid year in sheet name: "%(name)s"', name=sheet.name))
		year = int(sheet.name)
		from datetime import datetime
		if year < MIN_YEAR or year > datetime.now().year:
			raise RuntimeError(_(u'Invalid year: %(year)s',year=str(year)))
		d.year = year

		# get row with corresp. id
		row = None
		for i in range(sheet.nrows):
			r = sheet.row_values(i)
			if type(r[0]) is float and int(r[0]) == id:
				row = r

		if row is None:
			raise RuntimeError(_(u'No record with id %(id)d for year %(year)d', id=id, year=year))

		# Gender
		#
		if row[1] == u'М' or row[1] == u'м':
			d.gender = 1
		elif row[1] == u'Ж' or row[1] == u'ж':
			d.gender = 0
		else:
			raise RuntimeError(_(u'Invalid gender: %(gender)s', gender=str(row[1])))

		# Birth date
		#
		(year, month, day, hr, mn, sc) = xlrd.xldate_as_tuple(row[2], workbook.datemode)
		if year < MIN_BIRTH_YEAR or year > MAX_BIRTH_YEAR:
			raise RuntimeError(_(u'Invalid birth date: %(day)d.%(month)d.%(year)d',
				day=day, month=month, year=year))
		d.birth = dict(year=year, month=month, day=day)

		# Salary
		#
		if type(row[3]) is not float:
			raise RuntimeError(_(u'Invalid salary: %(salary)s', salary=str(row[3])))
		d.salary = row[3]

		# Overall experience
		#
		if type(row[4]) is unicode:
			e = exp.search(row[4])
			if e:
				x = e.groupdict()
				d.experience = dict(zip([str(v) for v in x.keys()], [int(v or 0) for v in x.values()]))
		if not 'experience' in d:
			if type(row[4]) is unicode:
				raise RuntimeError(_(u'Invalid overall experience: "%(exp)s"', exp=row[4]))
			else:
				raise RuntimeError(_(u'Invalid overall experience: "%(exp)s"', exp=str(row[4])))

		# Experience in company
		#
		if type(row[5]) is unicode:
			e = exp.search(row[5])
			if e:
				x = e.groupdict()
				d.experience_company = dict(zip([str(v) for v in x.keys()], [int(v or 0) for v in x.values()]))
		if not 'experience_company' in d:
			if type(row[5]) is unicode:
				raise RuntimeError(_(u'Invalid company experience: "%(exp)s"', exp=row[5]))
			else:
				raise RuntimeError(_(u'Invalid company experience: "%(exp)s"', exp=str(row[5])))

		# List 1 begin
		#
		if type(row[6]) is float:
			(year, month, day, hr, mn, sc) = xlrd.xldate_as_tuple(row[6], workbook.datemode)
			d.list1_begin = dict(year=year, month=month, day=day)
		else:
			d.list1_begin = dict(year=0, month=0, day=0)

		# List 1 end
		#
		if type(row[7]) is float:
			(year, month, day, hr, mn, sc) = xlrd.xldate_as_tuple(row[7], workbook.datemode)
			d.list1_end = dict(year=year, month=month, day=day)
		else:
			d.list1_end = dict(year=0, month=0, day=0)

		# List 1 place
		#
		d.list1_place = row[8]

		# List 2 begin
		#
		if type(row[9]) is float:
			(year, month, day, hr, mn, sc) = xlrd.xldate_as_tuple(row[9], workbook.datemode)
			d.list2_begin = dict(year=year, month=month, day=day)
		else:
			d.list2_begin = dict(year=0, month=0, day=0)

		# List 2 end
		#
		if type(row[10]) is float:
			(year, month, day, hr, mn, sc) = xlrd.xldate_as_tuple(row[10], workbook.datemode)
			d.list2_end = dict(year=year, month=month, day=day)
		else:
			d.list2_end = dict(year=0, month=0, day=0)

		# List 2 place
		#
		d.list2_place = row[11]

		# Date of dismissal
		#
		if type(row[12]) is float:
			(year, month, day, hr, mn, sc) = xlrd.xldate_as_tuple(row[12], workbook.datemode)
			d.date_end = dict(year=year, month=month, day=day)
		else:
			d.date_end = dict(year=0, month=0, day=0)

		if type(row[13]) is float:
			d.end_cause = int(row[13])
		else:
			d.end_cause = 0

		if type(row[14]) is float:
			d.chernobyl = int(row[14])
		else:
			d.chernobyl = 0

		data.append(d)
	return data

def parse_file(file, id):
	workbook = xlrd.open_workbook(file_contents=file)
	if workbook.nsheets != 4:
		raise RuntimeError(_(u'Invalid sheets count (%(count)d), must be 4', count=workbook.nsheets))

	if id == 0:
		# TODO : this is pathetic Shlemiel the painter's algorithm. Rewrite.
		rows = []
		ids = []
		sheet1 = workbook.sheets()[0]
		for i in range(sheet1.nrows):
			r = sheet1.row_values(i)
			if type(r[0]) is float:
				ids.append(int(r[0]))
		for id in ids:
			try:
				data = parse_employee(workbook, id)
				rows.append({'id': id, 'data': data})
			except Exception:
				pass
		return {'type': 0, 'rows': rows}
	else:
		return {'type': 1, 'rows': [{'id': id, 'data': parse_employee(workbook, id)}]}

def main():
	import sys
	if len(sys.argv) != 3:
		print "Usage:", sys.argv[0], "<filename> <id>"
		return 0

	data = parse(sys.argv[1], sys.argv[2])

	import json
	j = json.dumps(data)
	print "JSON: ", j
	print len(j), "bytes long."

	import bson
	b = bson.dumps(data)
	print "\nBSON: ", repr(b)
	print len(b), "bytes long."


if __name__ == "__main__":
	main()

