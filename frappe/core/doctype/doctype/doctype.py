# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt 

from __future__ import unicode_literals

import frappe
from frappe import msgprint, _
import os

from frappe.utils import now, cint
from frappe.model import no_value_fields

class DocType:
	def __init__(self, doc=None, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		if not frappe.conf.get("developer_mode"):
			frappe.throw("Not in Developer Mode! Set in site_config.json")
		for c in [".", "/", "#", "&", "=", ":", "'", '"']:
			if c in self.doc.name:
				frappe.msgprint(c + " not allowed in name", raise_exception=1)
		self.validate_series()
		self.scrub_field_names()
		self.validate_title_field()
		validate_fields(self.doclist.get({"doctype":"DocField"}))
		validate_permissions(self.doclist.get({"doctype":"DocPerm"}))
		self.make_amendable()
		self.check_link_replacement_error()

	def change_modified_of_parent(self):
		if frappe.flags.in_import:
			return
		parent_list = frappe.conn.sql("""SELECT parent 
			from tabDocField where fieldtype="Table" and options="%s" """ % self.doc.name)
		for p in parent_list:
			frappe.conn.sql('''UPDATE tabDocType SET modified="%s" 
				WHERE `name`="%s"''' % (now(), p[0]))

	def scrub_field_names(self):
		restricted = ('name','parent','idx','owner','creation','modified','modified_by',
			'parentfield','parenttype',"file_list")
		for d in self.doclist:
			if d.parent and d.fieldtype:
				if (not d.fieldname):
					if d.label:
						d.fieldname = d.label.strip().lower().replace(' ','_')
						if d.fieldname in restricted:
							d.fieldname = d.fieldname + '1'
					else:
						d.fieldname = d.fieldtype.lower().replace(" ","_") + "_" + str(d.idx)
						
	
	def validate_title_field(self):
		if self.doc.title_field and \
			self.doc.title_field not in [d.fieldname for d in self.doclist.get({"doctype":"DocField"})]:
			frappe.throw(_("Title field must be a valid fieldname"))
			
	def validate_series(self, autoname=None, name=None):
		if not autoname: autoname = self.doc.autoname
		if not name: name = self.doc.name
		
		if not autoname and self.doclist.get({"fieldname":"naming_series"}):
			self.doc.autoname = "naming_series:"
		
		if autoname and (not autoname.startswith('field:')) and (not autoname.startswith('eval:')) \
			and (not autoname=='Prompt') and (not autoname.startswith('naming_series:')):
			prefix = autoname.split('.')[0]
			used_in = frappe.conn.sql('select name from tabDocType where substring_index(autoname, ".", 1) = %s and name!=%s', (prefix, name))
			if used_in:
				msgprint('<b>Series already in use:</b> The series "%s" is already used in "%s"' % (prefix, used_in[0][0]), raise_exception=1)

	def on_update(self):
		from frappe.model.db_schema import updatedb
		updatedb(self.doc.name)

		self.change_modified_of_parent()
		make_module_and_roles(self.doclist)
		
		from frappe import conf
		if (not frappe.flags.in_import) and conf.get('developer_mode') or 0:
			self.export_doc()
			self.make_controller_template()
		
		# update index
		if not self.doc.custom:
			from frappe.model.code import load_doctype_module
			module = load_doctype_module( self.doc.name, self.doc.module)
			if hasattr(module, "on_doctype_update"):
				module.on_doctype_update()
		frappe.clear_cache(doctype=self.doc.name)

	def check_link_replacement_error(self):
		for d in self.doclist.get({"doctype":"DocField", "fieldtype":"Select"}):
			if (frappe.conn.get_value("DocField", d.name, "options") or "").startswith("link:") \
				and not d.options.startswith("link:"):
				frappe.msgprint("link: type Select fields are getting replaced. Please check for %s" % d.label,
					raise_exception=True)

	def on_trash(self):
		frappe.conn.sql("delete from `tabCustom Field` where dt = %s", self.doc.name)
		frappe.conn.sql("delete from `tabCustom Script` where dt = %s", self.doc.name)
		frappe.conn.sql("delete from `tabProperty Setter` where doc_type = %s", self.doc.name)
		frappe.conn.sql("delete from `tabReport` where ref_doctype=%s", self.doc.name)
	
	def before_rename(self, old, new, merge=False):
		if merge:
			frappe.throw(_("DocType can not be merged"))
			
	def after_rename(self, old, new, merge=False):
		if self.doc.issingle:
			frappe.conn.sql("""update tabSingles set doctype=%s where doctype=%s""", (new, old))
		else:
			frappe.conn.sql("rename table `tab%s` to `tab%s`" % (old, new))
	
	def export_doc(self):
		from frappe.modules.export_file import export_to_files
		export_to_files(record_list=[['DocType', self.doc.name]])
		
	def import_doc(self):
		from frappe.modules.import_module import import_from_files
		import_from_files(record_list=[[self.doc.module, 'doctype', self.doc.name]])		

	def make_controller_template(self):
		from frappe.modules import get_doc_path, get_module_path, scrub
		
		pypath = os.path.join(get_doc_path(self.doc.module, 
			self.doc.doctype, self.doc.name), scrub(self.doc.name) + '.py')

		if not os.path.exists(pypath):
			with open(pypath, 'w') as pyfile:
				with open(os.path.join(get_module_path("core"), "doctype", "doctype", 
					"doctype_template.py"), 'r') as srcfile:
					pyfile.write(srcfile.read())
	
	def make_amendable(self):
		"""
			if is_submittable is set, add amended_from docfields
		"""
		if self.doc.is_submittable:
			if not frappe.conn.sql("""select name from tabDocField 
				where fieldname = 'amended_from' and parent = %s""", self.doc.name):
					new = self.doc.addchild('fields', 'DocField', self.doclist)
					new.label = 'Amended From'
					new.fieldtype = 'Link'
					new.fieldname = 'amended_from'
					new.options = self.doc.name
					new.permlevel = 0
					new.read_only = 1
					new.print_hide = 1
					new.no_copy = 1
					new.idx = self.get_max_idx() + 1
				
	def get_max_idx(self):
		max_idx = frappe.conn.sql("""select max(idx) from `tabDocField` where parent = %s""", 
			self.doc.name)
		return max_idx and max_idx[0][0] or 0

def validate_fields_for_doctype(doctype):
	from frappe.model.doctype import get
	validate_fields(get(doctype, cached=False).get({"parent":doctype, 
		"doctype":"DocField"}))
		
def validate_fields(fields):
	def check_illegal_characters(fieldname):
		for c in ['.', ',', ' ', '-', '&', '%', '=', '"', "'", '*', '$', 
			'(', ')', '[', ']', '/']:
			if c in fieldname:
				frappe.msgprint("'%s' not allowed in fieldname (%s)" % (c, fieldname))
	
	def check_unique_fieldname(fieldname):
		duplicates = filter(None, map(lambda df: df.fieldname==fieldname and str(df.idx) or None, fields))
		if len(duplicates) > 1:
			frappe.msgprint('Fieldname <b>%s</b> appears more than once in rows (%s). Please rectify' \
			 	% (fieldname, ', '.join(duplicates)), raise_exception=1)
	
	def check_illegal_mandatory(d):
		if d.fieldtype in ('HTML', 'Button', 'Section Break', 'Column Break') and d.reqd:
			frappe.msgprint('%(label)s [%(fieldtype)s] cannot be mandatory' % d.fields, 
				raise_exception=1)
	
	def check_link_table_options(d):
		if d.fieldtype in ("Link", "Table"):
			if not d.options:
				frappe.msgprint("""#%(idx)s %(label)s: Options must be specified for Link and Table type fields""" % d.fields, 
					raise_exception=1)
			if d.options=="[Select]":
				return
			if d.options != d.parent and not frappe.conn.exists("DocType", d.options):
				frappe.msgprint("""#%(idx)s %(label)s: Options %(options)s must be a valid "DocType" for Link and Table type fields""" % d.fields, 
					raise_exception=1)

	def check_hidden_and_mandatory(d):
		if d.hidden and d.reqd and not d.default:
			frappe.msgprint("""#%(idx)s %(label)s: Cannot be hidden and mandatory (reqd) without default""" % d.fields,
				raise_exception=True)

	def check_max_items_in_list(fields):
		count = 0
		for d in fields:
			if d.in_list_view: count+=1
		if count > 5:
			frappe.msgprint("""Max 5 Fields can be set as 'In List View', please unselect a field before selecting a new one.""")
				
	def check_width(d):
		if d.fieldtype == "Currency" and cint(d.width) < 100:
			frappe.msgprint("Minimum width for FieldType 'Currency' is 100px", raise_exception=1)

	def check_in_list_view(d):
		if d.in_list_view and d.fieldtype!="Image" and (d.fieldtype in no_value_fields):
			frappe.msgprint("'In List View' not allowed for field of type '%s'" % d.fieldtype, raise_exception=1)

	for d in fields:
		if not d.permlevel: d.permlevel = 0
		if not d.fieldname:
			frappe.msgprint("Fieldname is mandatory in row %s" % d.idx, raise_exception=1)
		check_illegal_characters(d.fieldname)
		check_unique_fieldname(d.fieldname)
		check_illegal_mandatory(d)
		check_link_table_options(d)
		check_hidden_and_mandatory(d)
		check_in_list_view(d)

def validate_permissions_for_doctype(doctype, for_remove=False):
	from frappe.model.doctype import get
	validate_permissions(get(doctype, cached=False).get({"parent":doctype, 
		"doctype":"DocPerm"}), for_remove)

def validate_permissions(permissions, for_remove=False):
	doctype = permissions and permissions[0].parent
	issingle = issubmittable = isimportable = False
	if doctype and not doctype.startswith("New DocType"):
		values = frappe.conn.get_value("DocType", doctype, 
			["issingle", "is_submittable", "allow_import"], as_dict=True)
		issingle = cint(values.issingle)
		issubmittable = cint(values.is_submittable)
		isimportable = cint(values.allow_import)

	def get_txt(d):
		return "For %s (level %s) in %s, row #%s:" % (d.role, d.permlevel, d.parent, d.idx)
		
	def check_atleast_one_set(d):
		if not d.read and not d.write and not d.submit and not d.cancel and not d.create:
			frappe.msgprint(get_txt(d) + " Atleast one of Read, Write, Create, Submit, Cancel must be set.",
			 	raise_exception=True)
		
	def check_double(d):
		similar = permissions.get({
			"role":d.role,
			"permlevel":d.permlevel,
			"match": d.match
		})
		
		if len(similar) > 1:
			frappe.msgprint(get_txt(d) + " Only one rule allowed for a particular Role and Level.", 
				raise_exception=True)
	
	def check_level_zero_is_set(d):
		if cint(d.permlevel) > 0 and d.role != 'All':
			if not permissions.get({"role": d.role, "permlevel": 0}):
				frappe.msgprint(get_txt(d) + " Higher level permissions are meaningless if level 0 permission is not set.",
					raise_exception=True)
					
			if d.create or d.submit or d.cancel or d.amend or d.match: 
				frappe.msgprint("Create, Submit, Cancel, Amend, Match has no meaning at level " + d.permlevel,
					raise_exception=True)
	
	def check_permission_dependency(d):
		if d.write and not d.read:
			frappe.msgprint(get_txt(d) + " Cannot set Write permission if Read is not set.",
				raise_exception=True)
		if d.cancel and not d.submit:
			frappe.msgprint(get_txt(d) + " Cannot set Cancel permission if Submit is not set.",
				raise_exception=True)
		if (d.submit or d.cancel or d.amend) and not d.write:
			frappe.msgprint(get_txt(d) + " Cannot set Submit, Cancel, Amend permission if Write is not set.",
				raise_exception=True)
		if d.amend and not d.write:
			frappe.msgprint(get_txt(d) + " Cannot set Amend if Cancel is not set.",
				raise_exception=True)
		if (d.fields.get("import") or d.export) and not d.report:
			frappe.msgprint(get_txt(d) + " Cannot set Import or Export permission if Report is not set.",
				raise_exception=True)
		if d.fields.get("import") and not d.create:
			frappe.msgprint(get_txt(d) + " Cannot set Import if Create is not set.",
				raise_exception=True)
	
	def remove_rights_for_single(d):
		if not issingle:
			return
		
		if d.report:
			frappe.msgprint("{doctype} {meaningless}".format(doctype=doctype,
				meaningless=_("is a single DocType, permission of type Report is meaningless.")))
			d.report = 0
			d.fields["import"] = 0
			d.fields["export"] = 0
			
		if d.restrict:
			frappe.msgprint("{doctype} {meaningless}".format(doctype=doctype,
				meaningless=_("is a single DocType, permission of type Restrict is meaningless.")))
			d.restrict = 0
	
	def check_if_submittable(d):
		if d.submit and not issubmittable:
			frappe.msgprint(doctype + " is not Submittable, cannot assign submit rights.",
				raise_exception=True)
		elif d.amend and not issubmittable:
			frappe.msgprint(doctype + " is not Submittable, cannot assign amend rights.",
				raise_exception=True)
	
	def check_if_importable(d):
		if d.fields.get("import") and not isimportable:
			frappe.throw("{doctype}: {not_importable}".format(doctype=doctype,
				not_importable=_("is not allowed to be imported, cannot assign import rights.")))
	
	for d in permissions:
		if not d.permlevel: 
			d.permlevel=0
		check_atleast_one_set(d)
		if not for_remove:
			check_double(d)
			check_permission_dependency(d)
			check_if_submittable(d)
			check_if_importable(d)
		check_level_zero_is_set(d)
		remove_rights_for_single(d)

def make_module_and_roles(doclist, perm_doctype="DocPerm"):
	try:
		if not frappe.conn.exists("Module Def", doclist[0].module):
			m = frappe.bean({"doctype": "Module Def", "module_name": doclist[0].module})
			m.insert()
		
		default_roles = ["Administrator", "Guest", "All"]
		roles = [p.role for p in doclist.get({"doctype": perm_doctype})] + default_roles
		
		for role in list(set(roles)):
			if not frappe.conn.exists("Role", role):
				r = frappe.bean({"doctype": "Role", "role_name": role})
				r.doc.role_name = role
				r.insert()
	except frappe.DoesNotExistError, e:
		pass
	except frappe.SQLError, e:
		if e.args[0]==1146:
			pass
		else:
			raise
