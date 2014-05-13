# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
"""
	Execute Patch Files

	To run directly

	python lib/wnf.py patch patch1, patch2 etc
	python lib/wnf.py patch -f patch1, patch2 etc

	where patch1, patch2 is module name
"""
import frappe, os

class PatchError(Exception): pass

def run_all():
	"""run all pending patches"""
	executed = [p[0] for p in frappe.db.sql("""select patch from `tabPatch Log`""")]

	for patch in get_all_patches():
		if patch and (patch not in executed):
			if not run_single(patchmodule = patch):
				log(patch + ': failed: STOPPED')
				raise PatchError(patch)

def get_all_patches():
	patches = []
	for app in frappe.get_installed_apps():
		# 3-to-4 fix
		if app=="webnotes":
			app="frappe"
		patches.extend(frappe.get_file_items(frappe.get_pymodule_path(app, "patches.txt")))

	return patches

def reload_doc(args):
	import frappe.modules
	run_single(method = frappe.modules.reload_doc, methodargs = args)

def run_single(patchmodule=None, method=None, methodargs=None, force=False):
	from frappe import conf

	# don't write txt files
	conf.developer_mode = 0

	if force or method or not executed(patchmodule):
		return execute_patch(patchmodule, method, methodargs)
	else:
		return True

def execute_patch(patchmodule, method=None, methodargs=None):
	"""execute the patch"""
	success = False
	block_user(True)
	frappe.db.begin()
	try:
		log('Executing %s in %s' % (patchmodule or str(methodargs), frappe.db.cur_db_name))
		if patchmodule:
			if patchmodule.startswith("execute:"):
				exec patchmodule.split("execute:")[1] in globals()
			else:
				frappe.get_attr(patchmodule + ".execute")()
			update_patch_log(patchmodule)
		elif method:
			method(**methodargs)

		frappe.db.commit()
		success = True
	except Exception, e:
		frappe.db.rollback()
		tb = frappe.get_traceback()
		log(tb)

	block_user(False)
	if success:
		log('Success')
	return success

def update_patch_log(patchmodule):
	"""update patch_file in patch log"""
	frappe.get_doc({"doctype": "Patch Log", "patch": patchmodule}).insert()

def executed(patchmodule):
	"""return True if is executed"""
	done = frappe.db.get_value("Patch Log", {"patch": patchmodule})
	# if done:
	# 	print "Patch %s already executed in %s" % (patchmodule, frappe.db.cur_db_name)
	return done

def block_user(block):
	"""stop/start execution till patch is run"""
	frappe.db.begin()
	msg = "Patches are being executed in the system. Please try again in a few moments."
	frappe.db.set_global('__session_status', block and 'stop' or None)
	frappe.db.set_global('__session_status_message', block and msg or None)
	frappe.db.commit()

def check_session_stopped():
	if frappe.db.get_global("__session_status")=='stop':
		frappe.msgprint(frappe.db.get_global("__session_status_message"))
		raise frappe.SessionStopped('Session Stopped')

def log(msg):
	if getattr(frappe.local, "patch_log_list", None) is None:
		frappe.local.patch_log_list = []

	frappe.local.patch_log_list.append(msg)
