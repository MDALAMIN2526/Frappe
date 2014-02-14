# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def update(ml):
	"""update modules"""
	frappe.conn.set_global('hidden_modules', ml)
	frappe.msgprint('Updated')
	frappe.clear_cache()