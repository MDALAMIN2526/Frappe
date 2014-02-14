# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt 

from __future__ import unicode_literals

import urllib
import frappe
from frappe.utils import get_request_site_address

no_cache = 1
no_sitemap = 1
base_template_path = "templates/pages/sitemap.xml"

def get_context(context):
	"""generate the sitemap XML"""
	host = get_request_site_address()
	links = []
	for l in frappe.conn.sql("""select `tabWebsite Sitemap`.page_name, `tabWebsite Sitemap`.lastmod 
		from `tabWebsite Sitemap`, `tabWebsite Sitemap Config` 
		where 
			`tabWebsite Sitemap`.website_sitemap_config = `tabWebsite Sitemap Config`.name
			and ifnull(`tabWebsite Sitemap Config`.no_sitemap, 0)=0""", 
		as_dict=True):
		links.append({
			"loc": urllib.basejoin(host, urllib.quote(l.page_name.encode("utf-8"))),
			"lastmod": l.lastmod
		})
	
	return {"links":links}
	