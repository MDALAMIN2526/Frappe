# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# MIT License. See license.txt

from __future__ import unicode_literals

import webnotes
import webnotes.webutils
from webnotes import _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def autoname(self):
		from webnotes.webutils import page_name
		self.doc.name = page_name(self.doc.title)

	def validate(self):
		if self.doc.blog_intro:
			self.doc.blog_intro = self.doc.blog_intro[:140]

		# update posts
		webnotes.conn.sql("""update tabBlogger set posts=(select count(*) from `tabBlog Post` 
			where ifnull(blogger,'')=tabBlogger.name)
			where name=%s""", self.doc.blogger)

	def on_update(self):
		webnotes.webutils.update_page_name(self.doc, self.doc.title)
		webnotes.webutils.delete_page_cache("writers")

	def get_context(self):
		import webnotes.utils
		import markdown2
		
		# this is for double precaution. usually it wont reach this code if not published
		if not webnotes.utils.cint(self.doc.published):
			raise Exception, "This blog has not been published yet!"
		
		# temp fields
		from webnotes.utils import global_date_format, get_fullname
		self.doc.full_name = get_fullname(self.doc.owner)
		self.doc.updated = global_date_format(self.doc.published_on)
		self.doc.content_html = self.doc.content
		
		if self.doc.blogger:
			self.doc.blogger_info = webnotes.doc("Blogger", self.doc.blogger).fields
		
		self.doc.description = self.doc.blog_intro or self.doc.content[:140]
		self.doc.meta_description = self.doc.description
		
		self.doc.categories = webnotes.conn.sql_list("select name from `tabBlog Category` order by name")
		
		self.doc.texts = {
			"comments": _("Comments"),
			"first_comment": _("Be the first one to comment"),
			"add_comment": _("Add Comment"),
			"submit": _("Submit"),
			"all_posts_by": _("All posts by"),
		}

		comment_list = webnotes.conn.sql("""\
			select comment, comment_by_fullname, creation
			from `tabComment` where comment_doctype="Blog Post"
			and comment_docname=%s order by creation""", self.doc.name, as_dict=1)
		
		self.doc.comment_list = comment_list or []
		for comment in self.doc.comment_list:
			comment['comment_date'] = webnotes.utils.global_date_format(comment['creation'])
			comment['comment'] = markdown2.markdown(comment['comment'])
			
def clear_blog_cache():
	for blog in webnotes.conn.sql_list("""select page_name from 
		`tabBlog Post` where ifnull(published,0)=1"""):
		webnotes.webutils.delete_page_cache(blog)
	
	webnotes.webutils.delete_page_cache("writers")

@webnotes.whitelist(allow_guest=True)
def get_blog_list(start=0, by=None, category=None):
	import webnotes
	condition = ""
	if by:
		condition = " and t1.blogger='%s'" % by.replace("'", "\'")
	if category:
		condition += " and t1.blog_category='%s'" % category.replace("'", "\'")
	query = """\
		select
			t1.title, t1.name, t1.page_name, t1.published_on as creation, 
				ifnull(t1.blog_intro, t1.content) as content, 
				t2.full_name, t2.avatar, t1.blogger,
				(select count(name) from `tabComment` where
					comment_doctype='Blog Post' and comment_docname=t1.name) as comments
		from `tabBlog Post` t1, `tabBlogger` t2
		where ifnull(t1.published,0)=1
		and t1.blogger = t2.name
		%(condition)s
		order by published_on desc, name asc
		limit %(start)s, 20""" % {"start": start, "condition": condition}
		
	result = webnotes.conn.sql(query, as_dict=1)

	# strip html tags from content
	import webnotes.utils
	
	for res in result:
		from webnotes.utils import global_date_format
		res['published'] = global_date_format(res['creation'])
		if not res['content']:
			res['content'] = webnotes.webutils.get_html(res['page_name'])
		res['content'] = res['content'][:140]
		
	return result

@webnotes.whitelist(allow_guest=True)
def add_comment(args=None):
	"""
		args = {
			'comment': '',
			'comment_by': '',
			'comment_by_fullname': '',
			'comment_doctype': '',
			'comment_docname': '',
			'page_name': '',
		}
	"""
	import webnotes
	import webnotes.utils, markdown2
	
	if not args: args = webnotes.form_dict
	args['comment'] = unicode(markdown2.markdown(args.get('comment') or ''))
	args['doctype'] = "Comment"
	
	page_name = args.get("page_name")
	if "page_name" in args:
		del args["page_name"]
	if "cmd" in args:
		del args["cmd"]
		
	comment = webnotes.bean(args)
	comment.ignore_permissions = True
	comment.insert()
	
	# since comments are embedded in the page, clear the web cache
	webnotes.webutils.clear_cache(page_name)
	
	args['comment_date'] = webnotes.utils.global_date_format(comment.doc.creation)
	template_args = { 'comment_list': [args]}
	
	# get html of comment row
	from jinja2 import Environment, FileSystemLoader
	jenv = Environment(loader = FileSystemLoader(webnotes.utils.get_base_path()))
	template = jenv.get_template("lib/website/doctype/blog_post/templates/includes/comment.html")
	
	comment_html = template.render(template_args)
	
	# notify commentors 
	commentors = [d[0] for d in webnotes.conn.sql("""select comment_by from tabComment where
		comment_doctype='Blog Post' and comment_docname=%s and
		ifnull(unsubscribed, 0)=0""", args.get('comment_docname'))]
	
	blog = webnotes.doc("Blog Post", args.get("comment_docname"))
	blogger_profile = webnotes.conn.get_value("Blogger", blog.blogger, "profile")
	blogger_email = webnotes.conn.get_value("Profile", blogger_profile, "email")
	
	from webnotes.utils.email_lib.bulk import send
	send(recipients=list(set(commentors + [blogger_email])), 
		doctype='Comment', 
		email_field='comment_by', 
		subject='New Comment on Blog: ' + blog.title, 
		message='%(comment)s<p>By %(comment_by_fullname)s</p>' % args,
		ref_doctype='Blog Post', ref_docname=blog.name)
	
	return comment_html.replace("\n", "")