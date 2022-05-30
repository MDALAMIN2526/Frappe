# Copyright (c) 2021, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DocumentShareKey(Document):
	def before_insert(self):
		self.key = frappe.generate_hash(length=32)
		if not self.expires_on and not self.flags.no_expiry:
			self.expires_on = frappe.utils.add_days(None, days=frappe.get_system_settings("document_share_key_expiry") or 90)

	def is_expired(self):
		return self.expires_on and self.expires_on < frappe.utils.getdate()
