# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	frappe.reload_doc("website", "doctype", "website_sitemap")
	frappe.reload_doc("website", "doctype", "website_sitemap_permission")
	frappe.reload_doc("website", "doctype", "website_group")
	frappe.reload_doc("website", "doctype", "post")
	frappe.reload_doc("website", "doctype", "user_vote")
	
	frappe.conn.sql("""update `tabWebsite Sitemap` ws set ref_doctype=(select wsc.ref_doctype
		from `tabWebsite Sitemap Config` wsc where wsc.name=ws.website_sitemap_config)
		where ifnull(page_or_generator, '')!='Page'""")
	
	home_page = frappe.conn.get_value("Website Settings", "Website Settings", "home_page")
	home_page = frappe.conn.get_value("Website Sitemap", {"docname": home_page}) or home_page
	frappe.conn.set_value("Website Settings", "Website Settings", "home_page",
		home_page)
