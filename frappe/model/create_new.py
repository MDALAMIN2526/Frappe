# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
"""
Create a new document with defaults set
"""

import frappe
from frappe.utils import nowdate, nowtime, cint, flt
import frappe.defaults

def get_new_doc(doctype, parent_doc = None, parentfield = None):
	doc = frappe.doc({
		"doctype": doctype,
		"__islocal": 1,
		"owner": frappe.session.user,
		"docstatus": 0
	})
	
	meta = frappe.get_doctype(doctype)
	
	restrictions = frappe.defaults.get_restrictions()
	
	if parent_doc:
		doc.parent = parent_doc.name
		doc.parenttype = parent_doc.doctype
	
	if parentfield:
		doc.parentfield = parentfield
	
	for d in meta.get({"doctype":"DocField", "parent": doctype}):
		default = frappe.defaults.get_user_default(d.fieldname)
		
		if (d.fieldtype=="Link") and d.ignore_restrictions != 1 and (d.options in restrictions)\
			and len(restrictions[d.options])==1:
			doc.fields[d.fieldname] = restrictions[d.options][0]
		elif default:
			doc.fields[d.fieldname] = default
		elif d.fields.get("default"):
			if d.default == "__user":
				doc.fields[d.fieldname] = frappe.session.user
			elif d.default == "Today":
				doc.fields[d.fieldname] = nowdate()

			elif d.default.startswith(":"):
				ref_fieldname = d.default[1:].lower().replace(" ", "_")
				if parent_doc:
					ref_docname = parent_doc.fields[ref_fieldname]
				else:
					ref_docname = frappe.conn.get_default(ref_fieldname)
				doc.fields[d.fieldname] = frappe.conn.get_value(d.default[1:], 
					ref_docname, d.fieldname)

			else:
				doc.fields[d.fieldname] = d.default
			
			# convert type of default
			if d.fieldtype in ("Int", "Check"):
				doc.fields[d.fieldname] = cint(doc.fields[d.fieldname])
			elif d.fieldtype in ("Float", "Currency"):
				doc.fields[d.fieldname] = flt(doc.fields[d.fieldname])
				
		elif d.fieldtype == "Time":
			doc.fields[d.fieldname] = nowtime()
			
	return doc
