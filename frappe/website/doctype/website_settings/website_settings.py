# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import get_request_site_address, encode
from frappe.model.controller import DocListController
from urllib import quote

class DocType(DocListController):
	def validate(self):
		self.validate_top_bar_items()
		self.validate_footer_items()
		self.validate_home_page()
	
	def validate_home_page(self):
		if self.doc.home_page and \
			not frappe.conn.get_value("Website Sitemap", {"name": self.doc.home_page}):
			frappe.throw(_("Invalid Home Page") + " (Standard pages - index, login, products, blog, about, contact)")
	
	def validate_top_bar_items(self):
		"""validate url in top bar items"""
		for top_bar_item in self.doclist.get({"parentfield": "top_bar_items"}):
			if top_bar_item.parent_label:
				parent_label_item = self.doclist.get({"parentfield": "top_bar_items", 
					"label": top_bar_item.parent_label})
				
				if not parent_label_item:
					# invalid item
					msgprint(_(self.meta.get_label("parent_label", parentfield="top_bar_items")) +
						(" \"%s\": " % top_bar_item.parent_label) + _("does not exist"), raise_exception=True)
				
				elif not parent_label_item[0] or parent_label_item[0].url:
					# parent cannot have url
					msgprint(_("Top Bar Item") + (" \"%s\": " % top_bar_item.parent_label) +
						_("cannot have a URL, because it has child item(s)"), raise_exception=True)
	
	def validate_footer_items(self):
		"""clear parent label in footer"""
		for footer_item in self.doclist.get({"parentfield": "footer_items"}):
			footer_item.parent_label = None

	def on_update(self):
		# make js and css
		# clear web cache (for menus!)

		from frappe.website.render import clear_cache
		clear_cache()

def get_website_settings():
	hooks = frappe.get_hooks()
	
	all_top_items = frappe.conn.sql("""\
		select * from `tabTop Bar Item`
		where parent='Website Settings' and parentfield='top_bar_items'
		order by idx asc""", as_dict=1)
	
	top_items = [d for d in all_top_items if not d['parent_label']]
	
	# attach child items to top bar
	for d in all_top_items:
		if d['parent_label']:
			for t in top_items:
				if t['label']==d['parent_label']:
					if not 'child_items' in t:
						t['child_items'] = []
					t['child_items'].append(d)
					break
					
	context = frappe._dict({
		'top_bar_items': top_items,
		'footer_items': frappe.conn.sql("""\
			select * from `tabTop Bar Item`
			where parent='Website Settings' and parentfield='footer_items'
			order by idx asc""", as_dict=1),
		"post_login": [
			{"label": "Reset Password", "url": "update-password", "icon": "icon-key"},
			{"label": "Logout", "url": "?cmd=web_logout", "icon": "icon-signout"}
		]
	})
		
	settings = frappe.doc("Website Settings", "Website Settings")
	for k in ["banner_html", "brand_html", "copyright", "twitter_share_via",
		"favicon", "facebook_share", "google_plus_one", "twitter_share", "linked_in_share",
		"disable_signup"]:
		if k in settings.fields:
			context[k] = settings.fields.get(k)
			
	if settings.address:
		context["footer_address"] = settings.address

	for k in ["facebook_share", "google_plus_one", "twitter_share", "linked_in_share",
		"disable_signup"]:
		context[k] = int(context.get(k) or 0)
	
	context.url = quote(str(get_request_site_address(full_address=True)), safe="/:")
	context.encoded_title = quote(encode(context.title or ""), str(""))
	
	for update_website_context in hooks.update_website_context or []:
		frappe.get_attr(update_website_context)(context)
		
	context.web_include_js = hooks.web_include_js or []
	context.web_include_css = hooks.web_include_css or []
	
	return context
