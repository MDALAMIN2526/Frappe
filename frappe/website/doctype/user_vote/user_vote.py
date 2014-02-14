# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.permissions import get_access

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def validate(self):
		# if new
		if self.doc.fields.get("__islocal"):
			if frappe.conn.get_value("User Vote", {"ref_doctype": self.doc.ref_doctype, 
				"ref_name": self.doc.ref_name, "owner": frappe.session.user}):
				
				raise frappe.DuplicateEntryError
			
	def on_update(self):
		self.update_ref_count()

	def on_trash(self):
		self.update_ref_count(-1)

	def update_ref_count(self, cnt=0):
		count = frappe.conn.sql("""select count(*) from `tabUser Vote` where ref_doctype=%s and ref_name=%s""",
			(self.doc.ref_doctype, self.doc.ref_name))[0][0]
		frappe.conn.set_value(self.doc.ref_doctype, self.doc.ref_name, "upvotes", count + cnt)
		
def on_doctype_update():
	frappe.conn.add_index("User Vote", ["ref_doctype", "ref_name"])

# don't allow guest to give vote
@frappe.whitelist()
def set_vote(ref_doctype, ref_name):
	website_group = frappe.conn.get_value(ref_doctype, ref_name, "website_group")
	pathname = frappe.conn.get_value("Website Sitemap", {"ref_doctype": "Website Group",
		"docname": website_group})
	
	if not get_access(pathname).get("read"):
		raise frappe.PermissionError
	
	try:
		user_vote = frappe.bean({
			"doctype": "User Vote",
			"ref_doctype": ref_doctype,
			"ref_name": ref_name
		})
		user_vote.ignore_permissions = True
		user_vote.insert()
		return "ok"
	except frappe.DuplicateEntryError:
		return "duplicate"
