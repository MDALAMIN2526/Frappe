# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt 

from __future__ import unicode_literals
import frappe, os
import frappe.utils
from frappe.modules import get_doc_path

standard_format = "templates/print_formats/standard.html"

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d,dl

	def validate(self):
		if self.doc.standard=="Yes" and frappe.session.user != "Administrator":
			frappe.msgprint("Standard Print Format cannot be updated.", raise_exception=1)
		
		# old_doc_type is required for clearing item cache
		self.old_doc_type = frappe.conn.get_value('Print Format',
				self.doc.name, 'doc_type')

	def on_update(self):
		if hasattr(self, 'old_doc_type') and self.old_doc_type:
			frappe.clear_cache(doctype=self.old_doc_type)		
		if self.doc.doc_type:
			frappe.clear_cache(doctype=self.doc.doc_type)

		self.export_doc()
	
	def export_doc(self):
		# export
		if self.doc.standard == 'Yes' and (frappe.conf.get('developer_mode') or 0) == 1:
			from frappe.modules.export_file import export_to_files
			export_to_files(record_list=[['Print Format', self.doc.name]], 
				record_module=self.doc.module)	
	
	def on_trash(self):
		if self.doc.doc_type:
			frappe.clear_cache(doctype=self.doc.doc_type)

def get_args():
	if not frappe.form_dict.format:
		frappe.form_dict.format = standard_format
	if not frappe.form_dict.doctype or not frappe.form_dict.name:
		return {
			"body": """<h1>Error</h1>
				<p>Parameters doctype, name and format required</p>
				<pre>%s</pre>""" % repr(frappe.form_dict)
		}
		
	bean = frappe.bean(frappe.form_dict.doctype, frappe.form_dict.name)
	for ptype in ("read", "print"):
		if not frappe.has_permission(bean.doc.doctype, ptype, bean.doc):
			return {
				"body": """<h1>Error</h1>
					<p>No {ptype} permission</p>""".format(ptype=ptype)
			}
		
	return {
		"body": get_html(bean.doc, bean.doclist),
		"css": get_print_style(frappe.form_dict.style),
		"comment": frappe.session.user
	}

def get_html(doc, doclist, print_format=None):
	from jinja2 import Environment
	
	if isinstance(doc, basestring) and isinstance(doclist, basestring):
		bean = frappe.bean(doc, doclist)
		doc = bean.doc
		doclist = bean.doclist

	template = Environment().from_string(get_print_format_name(doc.doctype, 
		print_format or frappe.form_dict.format))
	doctype = frappe.get_doctype(doc.doctype)
	
	args = {
		"doc": doc,
		"doclist": doclist,
		"doctype": doctype,
		"frappe": frappe,
		"utils": frappe.utils
	}
	html = template.render(args)
	return html

def get_print_format_name(doctype, format_name):
	if format_name==standard_format:
		return format_name
		
	# server, find template
	path = os.path.join(get_doc_path(frappe.conn.get_value("DocType", doctype, "module"), 
		"Print Format", format_name), format_name + ".html")
	if os.path.exists(path):
		with open(path, "r") as pffile:
			return pffile.read()
	else:
		html = frappe.conn.get_value("Print Format", format_name, "html")
		if html:
			return html
		else:
			return "No template found.\npath: " + path

def get_print_style(style=None):
	if not style:
		style = frappe.conn.get_default("print_style") or "Standard"
	path = os.path.join(get_doc_path("Core", "DocType", "Print Format"), "styles", 
		style.lower() + ".css")
	if not os.path.exists(path):
		if style!="Standard":
			return get_print_style("Standard")
		else:
			return "/* Standard Style Missing ?? */"
	else:
		with open(path, 'r') as sfile:
			return sfile.read()
	