# Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
# 
# MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals
"""build query for doclistview and return results"""

import webnotes, json

tables = None
doctypes = {}
roles = []

@webnotes.whitelist()
def get(arg=None):
	query = build_query(arg)
	return compress(webnotes.conn.sql(query, as_dict=1))
	
def build_query(arg=None):
	"""
	build query
	
	gets doctype, subject, filters
	limit_start, limit_page_length
	"""
	data = prepare_data(arg)
	
	if 'query' in data:
		return run_custom_query(data)
	
	query = """select %(fields)s from %(tables)s where %(conditions)s
		%(group_by)s order by %(order_by)s %(limit)s""" % data
		
	return query
	
def prepare_data(arg=None):
	global tables
	
	if arg:
		data = webnotes._dict(arg)
	else:
		data = webnotes._dict(webnotes.form_dict)
		
	if 'query' in data:
		return data
	
	if isinstance(data.get("filters"), basestring):
		data["filters"] = json.loads(data["filters"])
	if isinstance(data.get("fields"), basestring):
		data["fields"] = json.loads(data["fields"])
		
	tables = get_tables(data)
	load_doctypes()
	remove_user_tags(data)
	conditions = build_conditions(data)
	
	# query dict
	data['tables'] = ', '.join(tables)
	data['conditions'] = ' and '.join(conditions)
	data['fields'] = ', '.join(data.fields)
	
	if not data.get('order_by'):
		data['order_by'] = tables[0] + '.modified desc'

	if data.get('group_by'):
		data['group_by'] = "group by " + data.get('group_by')
	else:
		data['group_by'] = ''

	check_sort_by_table(data.get('order_by'), tables)
	
	add_limit(data)
	
	return data

def compress(data):
	"""separate keys and values"""
	if not data: return data
	values = []
	keys = data[0].keys()
	for row in data:
		new_row = []
		for key in keys:
			new_row.append(row[key])
		values.append(new_row)
		
	return {
		"keys": keys,
		"values": values
	}
	
def check_sort_by_table(sort_by, tables):
	"""check atleast 1 column selected from the sort by table """
	tbl = sort_by.split('.')[0]
	if tbl not in tables:
		if tbl.startswith('`'):
			tbl = tbl[4:-1]
		webnotes.msgprint("Please select atleast 1 column from '%s' to sort"\
			% tbl, raise_exception=1)

def run_custom_query(data):
	"""run custom query"""
	query = data['query']
	if '%(key)s' in query:
		query = query.replace('%(key)s', 'name')
	return webnotes.conn.sql(query, as_dict=1)

def load_doctypes():
	"""load all doctypes and roles"""
	global doctypes, roles
	import webnotes.model.doctype

	roles = webnotes.get_roles()
		
	for t in tables:
		if t.startswith('`'):
			doctype = t[4:-1]
			if not webnotes.has_permission(doctype):
				webnotes.response['403'] = 1
				raise webnotes.PermissionError, doctype
			doctypes[doctype] = webnotes.model.doctype.get(doctype)
	
def remove_user_tags(data):
	"""remove column _user_tags if not in table"""
	for fld in data.fields:
		if '_user_tags' in fld:
			if not '_user_tags' in get_table_columns(data.doctype):
				del data.fields[data.fields.index(fld)]
				break

def add_limit(data):
	if 'limit_page_length' in data:
		data['limit'] = 'limit %(limit_start)s, %(limit_page_length)s' % data
	else:
		data['limit'] = ''
		
def build_conditions(data):
	"""build conditions"""
	# docstatus condition
	if isinstance(data.docstatus, basestring):
		data.docstatus = json.loads(data.docstatus)
	
	if data.docstatus:
		conditions = [tables[0] + '.docstatus in (' + ','.join(data.docstatus) + ')']
	else:
		# default condition
		conditions = [tables[0] + '.docstatus < 2']
	
	# make conditions from filters
	build_filter_conditions(data, conditions)

	# join parent, child tables
	for tname in tables[1:]:
		conditions.append(tname + '.parent = ' + tables[0] + '.name')

	# match conditions
	match_conditions = build_match_conditions(data)
	if match_conditions:
		conditions.append(match_conditions)

	return conditions
		
def build_filter_conditions(data, conditions):
	"""build conditions from user filters"""
	from webnotes.utils import cstr
	
	for f in data.filters:
		tname = ('`tab' + f[0] + '`')
		if not tname in tables:
			tables.append(tname)
		
		# prepare in condition
		if f[2]=='in':
			opts = ["'" + t.strip().replace("'", "\'") + "'" for t in f[3].split(',')]
			f[3] = "(" + ', '.join(opts) + ")"
			conditions.append(tname + '.' + f[1] + " " + f[2] + " " + f[3])	
		else:
			if isinstance(f[3], basestring):
				f[3] = "'" + f[3].replace("'", "\'") + "'"	
				conditions.append(tname + '.' + f[1] + " " + f[2] + " " + f[3])	
			else:
				conditions.append('ifnull(' + tname + '.' + f[1] + ",0) " + f[2] \
					+ " " + cstr(f[3]))
					
def build_match_conditions(data):
	"""add match conditions if applicable"""
	match_conditions = []
	match = True
	
	if not tables or not doctypes:
		global tables
		tables = get_tables(data)
		load_doctypes()
	
	for d in doctypes[data['doctype']]:
		if d.doctype == 'DocPerm' and d.parent == data['doctype']:
			if d.role in roles:
				if d.match: # role applicable
					if ':' in d.match:
						document_key, default_key = d.match.split(":")
					else:
						default_key = document_key = d.match
				
					for v in webnotes.user.get_defaults().get(default_key, ['**No Match**']):
						match_conditions.append('`tab%s`.%s="%s"' % (data['doctype'],
							document_key, v))
							
				elif d.read == 1 and d.permlevel == 0:
					# don't restrict if another read permission at level 0 
					# exists without a match restriction
					match = False
		
	if match_conditions and match:
		return '('+ ' or '.join(match_conditions) +')'

def get_tables(data):
	"""extract tables from fields"""
	tables = ['`tab' + data['doctype'] + '`']

	# add tables from fields
	for f in data.get('fields') or []:
		if "." not in f: continue
		
		table_name = f.split('.')[0]
		if table_name.lower().startswith('group_concat('):
			table_name = table_name[13:]
		# check if ifnull function is used
		if table_name.lower().startswith('ifnull('):
			table_name = table_name[7:]
		if not table_name[0]=='`':
			table_name = '`' + table_name + '`'
		if not table_name in tables:
			tables.append(table_name)	
	return tables

@webnotes.whitelist()
def save_report():
	"""save report"""
	from webnotes.model.doc import Document
	
	data = webnotes.form_dict
	if webnotes.conn.exists('Report', data['name'].title()):
		d = Document('Report', data['name'].title())
	else:
		d = Document('Report')
		d.name = data['name']
		d.ref_doctype = data['doctype']
		
	d.json = data['json']
	webnotes.model_wrapper([d]).save()
	webnotes.msgprint("%s saved." % d.name)
	return d.name

@webnotes.whitelist()
def export_query():
	"""export from report builder"""
	
	# TODO: validate use is allowed to export
	verify_export_allowed()
	ret = webnotes.conn.sql(build_query(), as_dict=1)

	columns = [x[0] for x in webnotes.conn.get_description()]
	data = [['Sr'] + get_labels(columns),]

	# flatten dict
	cnt = 1
	for row in ret:
		flat = [cnt,]
		for c in columns:
			flat.append(row.get(c))
		data.append(flat)
		cnt += 1

	# convert to csv
	from cStringIO import StringIO
	import csv

	f = StringIO()
	writer = csv.writer(f)
	from webnotes.utils import cstr
	for r in data:
		# encode only unicode type strings and not int, floats etc.
		writer.writerow(map(lambda v: isinstance(v, unicode) and v.encode('utf-8') or v, r))

	f.seek(0)
	webnotes.response['result'] = unicode(f.read(), 'utf-8')
	webnotes.response['type'] = 'csv'
	webnotes.response['doctype'] = [t[4:-1] for t in tables][0]

def verify_export_allowed():
	"""throw exception if user is not allowed to export"""
	global roles
	roles = webnotes.get_roles()
	if not ('Administrator' in roles or 'System Manager' in roles or 'Report Manager' in roles):
		raise webnotes.PermissionError

def get_labels(columns):
	"""get column labels based on column names"""
	label_dict = {}
	for doctype in doctypes:
		for d in doctypes[doctype]:
			if d.doctype=='DocField' and d.fieldname:
				label_dict[d.fieldname] = d.label
	
	return map(lambda x: label_dict.get(x, x.title()), columns)

@webnotes.whitelist()
def delete_items():
	"""delete selected items"""
	import json
	from webnotes.model import delete_doc
	from webnotes.model.code import get_obj

	il = json.loads(webnotes.form_dict.get('items'))
	doctype = webnotes.form_dict.get('doctype')
	
	for d in il:
		try:
			dt_obj = get_obj(doctype, d)
			if hasattr(dt_obj, 'on_trash'):
				dt_obj.on_trash()
			delete_doc(doctype, d)
		except Exception, e:
			webnotes.errprint(webnotes.getTraceback())
			pass
		
@webnotes.whitelist()
def get_stats():
	"""get tag info"""
	import json
	tags = json.loads(webnotes.form_dict.get('stats'))
	doctype = webnotes.form_dict['doctype']
	stats = {}
	
	columns = get_table_columns(doctype)
	for tag in tags:
		if not tag in columns: continue
		tagcount = webnotes.conn.sql("""select %(tag)s, count(*) 
			from `tab%(doctype)s` 
			where ifnull(%(tag)s, '')!=''
			group by %(tag)s;""" % locals(), as_list=1)
			
		if tag=='_user_tags':
			stats[tag] = scrub_user_tags(tagcount)
		else:
			stats[tag] = tagcount
			
	return stats

def scrub_user_tags(tagcount):
	"""rebuild tag list for tags"""
	rdict = {}
	tagdict = dict(tagcount)
	for t in tagdict:
		alltags = t.split(',')
		for tag in alltags:
			if tag:
				if not tag in rdict:
					rdict[tag] = 0
			
				rdict[tag] += tagdict[t]
	
	rlist = []
	for tag in rdict:
		rlist.append([tag, rdict[tag]])
	
	return rlist

def get_table_columns(table):
	res = webnotes.conn.sql("DESC `tab%s`" % table, as_dict=1)
	if res: return [r['Field'] for r in res]
