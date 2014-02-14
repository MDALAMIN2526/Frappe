# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt 

from __future__ import unicode_literals
import frappe, json
import frappe.model.doc
import frappe.utils

@frappe.whitelist()
def getdoc(doctype, name, user=None):
	"""
	Loads a doclist for a given document. This method is called directly from the client.
	Requries "doctype", "name" as form variables.
	Will also call the "onload" method on the document.
	"""

	import frappe
	
	if not (doctype and name):
		raise Exception, 'doctype and name required!'
	
	if not name: 
		name = doctype

	if not frappe.conn.exists(doctype, name):
		return []

	try:
		bean = frappe.bean(doctype, name)
		bean.run_method("onload")
		
		if not bean.has_read_perm():
			raise frappe.PermissionError

		doclist = bean.doclist

		# add file list
		get_docinfo(doctype, name)
		
	except Exception, e:
		frappe.errprint(frappe.utils.get_traceback())
		frappe.msgprint('Did not load.')
		raise

	if bean and not name.startswith('_'):
		frappe.user.update_recent(doctype, name)
	
	frappe.response['docs'] = doclist

@frappe.whitelist()
def getdoctype(doctype, with_parent=False, cached_timestamp=None):
	"""load doctype"""
	import frappe.model.doctype
	import frappe.model.meta
	
	doclist = []
	
	# with parent (called from report builder)
	if with_parent:
		parent_dt = frappe.model.meta.get_parent_dt(doctype)
		if parent_dt:
			doclist = frappe.model.doctype.get(parent_dt, processed=True)
			frappe.response['parent_dt'] = parent_dt
	
	if not doclist:
		doclist = frappe.model.doctype.get(doctype, processed=True)
	
	frappe.response['restrictions'] = get_restrictions(doclist)
	
	if cached_timestamp and doclist[0].modified==cached_timestamp:
		return "use_cache"
	
	frappe.response['docs'] = doclist

def get_docinfo(doctype, name):
	frappe.response["docinfo"] = {
		"attachments": add_attachments(doctype, name),
		"comments": add_comments(doctype, name),
		"assignments": add_assignments(doctype, name)
	}
	
def get_restrictions(meta):
	out = {}
	all_restrictions = frappe.defaults.get_restrictions()
	for df in meta.get_restricted_fields(all_restrictions):
		out[df.options] = all_restrictions[df.options]
	return out

def add_attachments(dt, dn):
	attachments = {}
	for f in frappe.conn.sql("""select name, file_name, file_url from
		`tabFile Data` where attached_to_name=%s and attached_to_doctype=%s""", 
			(dn, dt), as_dict=True):
		attachments[f.file_url or f.file_name] = f.name

	return attachments
		
def add_comments(dt, dn, limit=20):
	cl = frappe.conn.sql("""select name, comment, comment_by, creation from `tabComment` 
		where comment_doctype=%s and comment_docname=%s 
		order by creation desc limit %s""" % ('%s','%s', limit), (dt, dn), as_dict=1)
		
	return cl
	
def add_assignments(dt, dn):
	cl = frappe.conn.sql_list("""select owner from `tabToDo`
		where reference_type=%(doctype)s and reference_name=%(name)s and status="Open"
		order by modified desc limit 5""", {
			"doctype": dt,
			"name": dn
		})
		
	return cl

@frappe.whitelist()
def get_badge_info(doctypes, filters):
	filters = json.loads(filters)
	doctypes = json.loads(doctypes)
	filters["docstatus"] = ["!=", 2]
	out = {}
	for doctype in doctypes:
		out[doctype] = frappe.conn.get_value(doctype, filters, "count(*)")

	return out