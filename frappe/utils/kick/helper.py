from __future__ import unicode_literals
import frappe, re


def get_user_info(email):
	return frappe.get_list('User', ["email", "full_name", "last_active"],
			filters={"email":email})[0] or None

def get_all_mail(email):
	return frappe.get_list('Communication', 
		["name", "subject", "creation", "content", "sender", "recipients", 
		"reference_name", "reference_doctype", "reference_owner", "status", 
		"sent_or_received"], 
		{"user": email, "communication_type" :"Communication"})

