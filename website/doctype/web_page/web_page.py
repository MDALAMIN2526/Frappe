# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# MIT License. See license.txt

from __future__ import unicode_literals
import webnotes

class DocType():
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def autoname(self):
		from webnotes.webutils import page_name
		self.doc.name = page_name(self.doc.title)

	def on_update(self):
		from webnotes.webutils import update_page_name
		update_page_name(self.doc, self.doc.title)
		self.if_home_clear_cache()

	def if_home_clear_cache(self):
		"""if home page, clear cache"""
		if webnotes.conn.get_value("Website Settings", None, "home_page")==self.doc.name:
			from webnotes.sessions import clear_cache
			clear_cache('Guest')
			
			from webnotes.webutils import clear_cache
			clear_cache(self.doc.page_name)
			clear_cache('index')
			
	def get_context(self):
		if self.doc.slideshow:
			from website.doctype.website_slideshow.website_slideshow import get_slideshow
			get_slideshow(self)
			
		self.doc.meta_description = self.doc.description
