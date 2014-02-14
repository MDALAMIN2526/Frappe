# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
"""build query for doclistview and return results"""

import frappe, json
import frappe.defaults
import frappe.permissions

@frappe.whitelist()
def get():
	return compress(execute(**get_form_params()))

def get_form_params():
	data = frappe._dict(frappe.local.form_dict)

	del data["cmd"]

	if isinstance(data.get("filters"), basestring):
		data["filters"] = json.loads(data["filters"])
	if isinstance(data.get("fields"), basestring):
		data["fields"] = json.loads(data["fields"])
	if isinstance(data.get("docstatus"), basestring):
		data["docstatus"] = json.loads(data["docstatus"])
		
	return data
	
def execute(doctype, query=None, filters=None, fields=None, docstatus=None, 
		group_by=None, order_by=None, limit_start=0, limit_page_length=20, 
		as_list=False, with_childnames=False, debug=False):
		
	"""
	fields as list ["name", "owner"] or ["tabTask.name", "tabTask.owner"]
	filters as list of list [["Task", "name", "=", "TASK00001"]]
	"""

	if query:
		return run_custom_query(query)
				
	if not filters: 
		filters = []
	if isinstance(filters, basestring):
		filters = json.loads(filters)
	if not docstatus: 
		docstatus = []
	if not fields: 
		fields = ["name"]
	if isinstance(fields, basestring):
		filters = json.loads(fields)

	args = prepare_args(doctype, filters, fields, docstatus, group_by, order_by, with_childnames)
	args.limit = add_limit(limit_start, limit_page_length)
	
	query = """select %(fields)s from %(tables)s where %(conditions)s
		%(group_by)s order by %(order_by)s %(limit)s""" % args
		
	return frappe.conn.sql(query, as_dict=not as_list, debug=debug)
	
def prepare_args(doctype, filters, fields, docstatus, group_by, order_by, with_childnames):
	frappe.local.reportview_tables = get_tables(doctype, fields)
	load_doctypes()
	remove_user_tags(doctype, fields)
	conditions = build_conditions(doctype, fields, filters, docstatus)
	
	args = frappe._dict()
	
	if with_childnames:
		for t in frappe.local.reportview_tables:
			if t != "`tab" + doctype + "`":
				fields.append(t + ".name as '%s:name'" % t[4:-1])
	
	# query dict
	args.tables = ', '.join(frappe.local.reportview_tables)
	args.conditions = ' and '.join(conditions)
	args.fields = ', '.join(fields)
	
	args.order_by = order_by or frappe.local.reportview_tables[0] + '.modified desc'
	args.group_by = group_by and (" group by " + group_by) or ""

	check_sort_by_table(args.order_by)
		
	return args

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
	
def check_sort_by_table(sort_by):
	"""check atleast 1 column selected from the sort by table """
	if "." in sort_by:
		tbl = sort_by.split('.')[0]
		if tbl not in frappe.local.reportview_tables:
			if tbl.startswith('`'):
				tbl = tbl[4:-1]
			frappe.msgprint("Please select atleast 1 column from '%s' to sort"\
				% tbl, raise_exception=1)

def run_custom_query(query):
	"""run custom query"""
	if '%(key)s' in query:
		query = query.replace('%(key)s', 'name')
	return frappe.conn.sql(query, as_dict=1)

def load_doctypes():
	"""load all doctypes and roles"""
	import frappe.model.doctype

	if not getattr(frappe.local, "reportview_doctypes", None):
		frappe.local.reportview_doctypes = {}

	for t in frappe.local.reportview_tables:
		if t.startswith('`'):
			doctype = t[4:-1]
			if frappe.local.reportview_doctypes.get(doctype):
				continue
			
			if not frappe.has_permission(doctype):
				raise frappe.PermissionError, doctype
			frappe.local.reportview_doctypes[doctype] = frappe.model.doctype.get(doctype)
	
def remove_user_tags(doctype, fields):
	"""remove column _user_tags if not in table"""
	columns = get_table_columns(doctype)
	del_user_tags = False
	del_comments = False
	for fld in fields:
		if '_user_tags' in fld and not "_user_tags" in columns:
			del_user_tags = fld
		if '_comments' in fld and not "_comments" in columns:
			del_comments = fld

	if del_user_tags: del fields[fields.index(del_user_tags)]
	if del_comments: del fields[fields.index(del_comments)]

def add_limit(limit_start, limit_page_length):
	if limit_page_length:
		return 'limit %s, %s' % (limit_start, limit_page_length)
	else:
		return ''
		
def build_conditions(doctype, fields, filters, docstatus):
	"""build conditions"""	
	if docstatus:
		conditions = [frappe.local.reportview_tables[0] + '.docstatus in (' + ','.join(docstatus) + ')']
	else:
		# default condition
		conditions = [frappe.local.reportview_tables[0] + '.docstatus < 2']
	
	# make conditions from filters
	build_filter_conditions(filters, conditions)
	
	# join parent, child tables
	for tname in frappe.local.reportview_tables[1:]:
		conditions.append(tname + '.parent = ' + frappe.local.reportview_tables[0] + '.name')

	# match conditions
	match_conditions = build_match_conditions(doctype, fields)
	if match_conditions:
		conditions.append(match_conditions)
	
	return conditions
		
def build_filter_conditions(filters, conditions):
	"""build conditions from user filters"""
	from frappe.utils import cstr, flt
	if not getattr(frappe.local, "reportview_tables", None):
		frappe.local.reportview_tables = []
		
	doclist = {}
	for f in filters:
		if isinstance(f, basestring):
			conditions.append(f)
		else:
			if not isinstance(f, (list, tuple)):
				frappe.throw("Filter must be a tuple or list (in a list)")

			if len(f) != 4:
				frappe.throw("Filter must have 4 values (doctype, fieldname, condition, value): " + str(f))
				
			tname = ('`tab' + f[0] + '`')
			if not tname in frappe.local.reportview_tables:
				frappe.local.reportview_tables.append(tname)
				
			if not hasattr(frappe.local, "reportview_doctypes") \
				or not frappe.local.reportview_doctypes.has_key(tname):
					load_doctypes()
		
			# prepare in condition
			if f[2] in ['in', 'not in']:
				opts = ["'" + t.strip().replace("'", "\\'") + "'" for t in f[3].split(',')]
				f[3] = "(" + ', '.join(opts) + ")"
				conditions.append('ifnull(' + tname + '.' + f[1] + ", '') " + f[2] + " " + f[3])
			else:
				df = frappe.local.reportview_doctypes[f[0]].get({"doctype": "DocField", 
					"fieldname": f[1]})
					
				if f[2] == "like" or (isinstance(f[3], basestring) and 
					(not df or df[0].fieldtype not in ["Float", "Int", "Currency", "Percent"])):
						value, default_val = ("'" + f[3].replace("'", "\\'") + "'"), '""'
				else:
					value, default_val = flt(f[3]), 0

				conditions.append('ifnull({tname}.{fname}, {default_val}) {operator} {value}'.format(
					tname=tname, fname=f[1], default_val=default_val, operator=f[2],
					value=value))
					
def build_match_conditions(doctype, fields=None, as_condition=True):
	"""add match conditions if applicable"""
	import frappe.permissions
	match_filters = {}
	match_conditions = []
	or_conditions = []

	if not getattr(frappe.local, "reportview_tables", None):
		frappe.local.reportview_tables = get_tables(doctype, fields)
	
	load_doctypes()
	
	# is restricted
	restricted = frappe.permissions.get_user_perms(frappe.local.reportview_doctypes[doctype]).restricted
	
	# get restrictions
	restrictions = frappe.defaults.get_restrictions()
	
	if restricted:
		or_conditions.append('`tab{doctype}`.`owner`="{user}"'.format(doctype=doctype, 
			user=frappe.local.session.user))
		match_filters["owner"] = frappe.session.user
	
	if restrictions:
		fields_to_check = frappe.local.reportview_doctypes[doctype].get_restricted_fields(restrictions.keys())
		if doctype in restrictions:
			fields_to_check.append(frappe._dict({"fieldname":"name", "options":doctype}))
		
		# check in links
		for df in fields_to_check:
			if as_condition:
				match_conditions.append('`tab{doctype}`.{fieldname} in ({values})'.format(doctype=doctype,
					fieldname=df.fieldname, 
					values=", ".join([('"'+v.replace('"', '\"')+'"') \
						for v in restrictions[df.options]])))
			else:
				match_filters.setdefault(df.fieldname, [])
				match_filters[df.fieldname]= restrictions[df.options]
										
	if as_condition:
		conditions = " and ".join(match_conditions)
		doctype_conditions = get_permission_query_conditions(doctype)
		if doctype_conditions:
			conditions += ' and ' + doctype_conditions if conditions else doctype_conditions
			
		if or_conditions:
			if conditions:
				conditions = '({conditions}) or {or_conditions}'.format(conditions=conditions, 
					or_conditions = ' or '.join(or_conditions))
			else:
				conditions = " or ".join(or_conditions)
				
		return conditions
	else:
		return match_filters
		
def get_permission_query_conditions(doctype):
	condition_methods = frappe.get_hooks("permission_query_conditions:" + doctype)
	if condition_methods:
		conditions = []
		for method in condition_methods:
			c = frappe.get_attr(method)()
			if c:
				conditions.append(c)
				
		return " and ".join(conditions) if conditions else None
		
def get_tables(doctype, fields):
	"""extract tables from fields"""
	tables = ['`tab' + doctype + '`']

	# add tables from fields
	if fields:
		for f in fields:
			if "." not in f: continue
		
			table_name = f.split('.')[0]
			if table_name.lower().startswith('group_concat('):
				table_name = table_name[13:]
			if table_name.lower().startswith('ifnull('):
				table_name = table_name[7:]
			if not table_name[0]=='`':
				table_name = '`' + table_name + '`'
			if not table_name in tables:
				tables.append(table_name)	

	return tables

@frappe.whitelist()
def save_report():
	"""save report"""
	from frappe.model.doc import Document
	
	data = frappe.local.form_dict
	if frappe.conn.exists('Report', data['name']):
		d = Document('Report', data['name'])
	else:
		d = Document('Report')
		d.report_name = data['name']
		d.ref_doctype = data['doctype']
	
	d.report_type = "Report Builder"
	d.json = data['json']
	frappe.bean([d]).save()
	frappe.msgprint("%s saved." % d.name)
	return d.name

@frappe.whitelist()
def export_query():
	"""export from report builder"""
	form_params = get_form_params()
	
	frappe.permissions.can_export(form_params.doctype, raise_exception=True)
	
	ret = execute(**form_params)

	columns = [x[0] for x in frappe.conn.get_description()]
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
	for r in data:
		# encode only unicode type strings and not int, floats etc.
		writer.writerow(map(lambda v: isinstance(v, unicode) and v.encode('utf-8') or v, r))

	f.seek(0)
	frappe.response['result'] = unicode(f.read(), 'utf-8')
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = [t[4:-1] for t in frappe.local.reportview_tables][0]

def get_labels(columns):
	"""get column labels based on column names"""
	label_dict = {}
	for doctype in frappe.local.reportview_doctypes:
		for d in frappe.local.reportview_doctypes[doctype]:
			if d.doctype=='DocField' and d.fieldname:
				label_dict[d.fieldname] = d.label
	
	return map(lambda x: label_dict.get(x, x.title()), columns)

@frappe.whitelist()
def delete_items():
	"""delete selected items"""
	import json
	from frappe.model.code import get_obj

	il = json.loads(frappe.form_dict.get('items'))
	doctype = frappe.form_dict.get('doctype')
	
	for d in il:
		try:
			dt_obj = get_obj(doctype, d)
			if hasattr(dt_obj, 'on_trash'):
				dt_obj.on_trash()
			frappe.delete_doc(doctype, d)
		except Exception, e:
			frappe.errprint(frappe.get_traceback())
			pass
		
@frappe.whitelist()
def get_stats(stats, doctype):
	"""get tag info"""
	import json
	tags = json.loads(stats)
	stats = {}
	
	columns = get_table_columns(doctype)
	for tag in tags:
		if not tag in columns: continue
		tagcount = execute(doctype, fields=[tag, "count(*)"], 
			filters=["ifnull(%s,'')!=''" % tag], group_by=tag, as_list=True)
			
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
	res = frappe.conn.sql("DESC `tab%s`" % table, as_dict=1)
	if res: return [r['Field'] for r in res]

# used in building query in queries.py
def get_match_cond(doctype, searchfield = 'name'):
	cond = build_match_conditions(doctype)

	if cond:
		cond = ' and ' + cond
	else:
		cond = ''
	return cond
