# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt 

from __future__ import unicode_literals
import frappe, json, os
from frappe.utils import cint, now, cstr
from frappe import throw, msgprint, _
from frappe.auth import _update_password

class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
		
	def autoname(self):
		"""set name as email id"""
		if self.doc.name not in ('Guest','Administrator'):
			self.doc.email = self.doc.email.strip()		
			self.doc.name = self.doc.email
			
			if frappe.conn.exists("Profile", self.doc.name):
				throw(_("Name Exists"))

	def validate(self):
		self.in_insert = self.doc.fields.get("__islocal")
		if self.doc.name not in ('Guest','Administrator'):
			self.validate_email_type(self.doc.email)
		self.validate_max_users()
		self.add_system_manager_role()
		self.check_enable_disable()
		if self.in_insert:
			if self.doc.name not in ("Guest", "Administrator"):
				if self.doc.new_password:
					# new password given, no email required
					_update_password(self.doc.name, self.doc.new_password)
				if not getattr(self, "no_welcome_mail", False):
					self.send_welcome_mail()
					msgprint(_("Welcome Email Sent"))
		else:
			try:
				self.email_new_password()
			except frappe.OutgoingEmailError:
				pass # email server not set, don't send email
				
		self.doc.new_password = ""
		self.update_gravatar()

	def check_enable_disable(self):
		# do not allow disabling administrator/guest
		if not cint(self.doc.enabled) and self.doc.name in ["Administrator", "Guest"]:
			throw("{msg}: {name}".format(**{
				"msg": _("Hey! You cannot disable user"), 
				"name": self.doc.name
			}))

		if not cint(self.doc.enabled):
			self.a_system_manager_should_exist()
		
		# clear sessions if disabled
		if not cint(self.doc.enabled) and getattr(frappe, "login_manager", None):
			frappe.local.login_manager.logout(user=self.doc.name)
		
	def validate_max_users(self):
		"""don't allow more than max users if set in conf"""
		from frappe import conf
		# check only when enabling a user
		if 'max_users' in conf and self.doc.enabled and \
				self.doc.name not in ["Administrator", "Guest"] and \
				cstr(self.doc.user_type).strip() in ("", "System User"):
			active_users = frappe.conn.sql("""select count(*) from tabProfile
				where ifnull(enabled, 0)=1 and docstatus<2
				and ifnull(user_type, "System User") = "System User"
				and name not in ('Administrator', 'Guest', %s)""", (self.doc.name,))[0][0]
			if active_users >= conf.max_users and conf.max_users:
				throw("""
					You already have <b>%(active_users)s</b> active users, \
					which is the maximum number that you are currently allowed to add. <br /><br /> \
					So, to add more users, you can:<br /> \
					1. <b>Upgrade to the unlimited users plan</b>, or<br /> \
					2. <b>Disable one or more of your existing users and try again</b>""" \
					% {'active_users': active_users})
						
	def add_system_manager_role(self):
		# if adding system manager, do nothing
		if not cint(self.doc.enabled) or ("System Manager" in [user_role.role for user_role in
				self.doclist.get({"parentfield": "user_roles"})]):
			return
		
		if self.doc.user_type == "System User" and not self.get_other_system_managers():
			msgprint("""Adding System Manager Role as there must 
				be atleast one 'System Manager'.""")
			self.doclist.append({
				"doctype": "UserRole",
				"parentfield": "user_roles",
				"role": "System Manager"
			})
	
	def email_new_password(self):
		if self.doc.new_password and not self.in_insert:
			_update_password(self.doc.name, self.doc.new_password)

			self.password_update_mail(self.doc.new_password)
			frappe.msgprint("New Password Emailed.")
			
	def on_update(self):
		# owner is always name
		frappe.conn.set(self.doc, 'owner', self.doc.name)
		frappe.clear_cache(user=self.doc.name)
		
	def update_gravatar(self):
		import md5
		if not self.doc.user_image:
			if self.doc.fb_username:
				self.doc.user_image = "https://graph.facebook.com/" + self.doc.fb_username + "/picture"
			else:
				self.doc.user_image = "https://secure.gravatar.com/avatar/" + md5.md5(self.doc.name).hexdigest() \
					+ "?d=retro"
	
	def reset_password(self):
		from frappe.utils import random_string, get_url

		key = random_string(32)
		frappe.conn.set_value("Profile", self.doc.name, "reset_password_key", key)
		self.password_reset_mail(get_url("/update-password?key=" + key))
	
	def get_other_system_managers(self):
		return frappe.conn.sql("""select distinct parent from tabUserRole user_role
			where role='System Manager' and docstatus<2
			and parent not in ('Administrator', %s) and exists 
				(select * from `tabProfile` profile 
				where profile.name=user_role.parent and enabled=1)""", (self.doc.name,))

	def get_fullname(self):
		"""get first_name space last_name"""
		return (self.doc.first_name or '') + \
			(self.doc.first_name and " " or '') + (self.doc.last_name or '')

	def password_reset_mail(self, link):
		self.send_login_mail("Password Reset", "templates/emails/password_reset.html", {"link": link})
	
	def password_update_mail(self, password):
		self.send_login_mail("Password Update", "templates/emails/password_update.html", {"new_password": password})

	def send_welcome_mail(self):
		from frappe.utils import random_string, get_url

		self.doc.reset_password_key = random_string(32)
		link = get_url("/update-password?key=" + self.doc.reset_password_key)

		self.send_login_mail("Verify Your Account", "templates/emails/new_user.html", {"link": link})
		
	def send_login_mail(self, subject, template, add_args):
		"""send mail with login details"""
		from frappe.profile import get_user_fullname
		from frappe.utils import get_url
		
		mail_titles = frappe.get_hooks().get("login_mail_title", [])
		title = frappe.conn.get_default('company') or (mail_titles and mail_titles[0]) or ""
		
		full_name = get_user_fullname(frappe.session['user'])
		if full_name == "Guest":
			full_name = "Administrator"
	
		args = {
			'first_name': self.doc.first_name or self.doc.last_name or "user",
			'user': self.doc.name,
			'title': title,
			'login_url': get_url(),
			'user_fullname': full_name
		}
		
		args.update(add_args)
		
		sender = frappe.session.user not in ("Administrator", "Guest") and frappe.session.user or None
		
		frappe.sendmail(recipients=self.doc.email, sender=sender, subject=subject, 
			message=frappe.get_template(template).render(args))
		
	def a_system_manager_should_exist(self):
		if not self.get_other_system_managers():
			throw(_("Hey! There should remain at least one System Manager"))
		
	def on_trash(self):
		frappe.clear_cache(user=self.doc.name)
		if self.doc.name in ["Administrator", "Guest"]:
			throw("{msg}: {name}".format(**{
				"msg": _("Hey! You cannot delete user"), 
				"name": self.doc.name
			}))
		
		self.a_system_manager_should_exist()
				
		# disable the user and log him/her out
		self.doc.enabled = 0
		if getattr(frappe.local, "login_manager", None):
			frappe.local.login_manager.logout(user=self.doc.name)
		
		# delete their password
		frappe.conn.sql("""delete from __Auth where user=%s""", (self.doc.name,))
		
		# delete todos
		frappe.conn.sql("""delete from `tabToDo` where owner=%s""", (self.doc.name,))
		frappe.conn.sql("""update tabToDo set assigned_by=null where assigned_by=%s""",
			(self.doc.name,))
		
		# delete events
		frappe.conn.sql("""delete from `tabEvent` where owner=%s
			and event_type='Private'""", (self.doc.name,))
		frappe.conn.sql("""delete from `tabEvent User` where person=%s""", (self.doc.name,))
			
		# delete messages
		frappe.conn.sql("""delete from `tabComment` where comment_doctype='Message'
			and (comment_docname=%s or owner=%s)""", (self.doc.name, self.doc.name))
			
	def before_rename(self, olddn, newdn, merge=False):
		frappe.clear_cache(user=olddn)
		self.validate_rename(olddn, newdn)
	
	def validate_rename(self, olddn, newdn):
		# do not allow renaming administrator and guest
		if olddn in ["Administrator", "Guest"]:
			throw("{msg}: {name}".format(**{
				"msg": _("Hey! You are restricted from renaming the user"), 
				"name": olddn
			}))
		
		self.validate_email_type(newdn)
	
	def validate_email_type(self, email):
		from frappe.utils import validate_email_add
	
		email = email.strip()
		if not validate_email_add(email):
			throw("{email} {msg}".format(**{
				"email": email, 
				"msg": _("is not a valid email id")
			}))
	
	def after_rename(self, olddn, newdn, merge=False):			
		tables = frappe.conn.sql("show tables")
		for tab in tables:
			desc = frappe.conn.sql("desc `%s`" % tab[0], as_dict=1)
			has_fields = []
			for d in desc:
				if d.get('Field') in ['owner', 'modified_by']:
					has_fields.append(d.get('Field'))
			for field in has_fields:
				frappe.conn.sql("""\
					update `%s` set `%s`=%s
					where `%s`=%s""" % \
					(tab[0], field, '%s', field, '%s'), (newdn, olddn))
					
		# set email
		frappe.conn.sql("""\
			update `tabProfile` set email=%s
			where name=%s""", (newdn, newdn))
		
		# update __Auth table
		if not merge:
			frappe.conn.sql("""update __Auth set user=%s where user=%s""", (newdn, olddn))
			
	def add_roles(self, *roles):
		for role in roles:
			if role in [d.role for d in self.doclist.get({"doctype":"UserRole"})]:
				continue
			self.bean.doclist.append({
				"doctype": "UserRole",
				"parentfield": "user_roles",
				"role": role
			})
			
		self.bean.save()

@frappe.whitelist()
def get_languages():
	from frappe.translate import get_lang_dict
	languages = get_lang_dict().keys()
	languages.sort()
	return [""] + languages

@frappe.whitelist()
def get_all_roles(arg=None):
	"""return all roles"""
	return [r[0] for r in frappe.conn.sql("""select name from tabRole
		where name not in ('Administrator', 'Guest', 'All') order by name""")]
		
@frappe.whitelist()
def get_user_roles(arg=None):
	"""get roles for a user"""
	return frappe.get_roles(frappe.form_dict['uid'])

@frappe.whitelist()
def get_perm_info(arg=None):
	"""get permission info"""
	return frappe.conn.sql("""select parent, permlevel, `read`, `write`, submit,
		cancel, amend from tabDocPerm where role=%s 
		and docstatus<2 order by parent, permlevel""", 
			(frappe.form_dict['role'],), as_dict=1)

@frappe.whitelist(allow_guest=True)
def update_password(new_password, key=None, old_password=None):
	# verify old password
	if key:
		user = frappe.conn.get_value("Profile", {"reset_password_key":key})
		if not user:
			return _("Cannot Update: Incorrect / Expired Link.")
	elif old_password:
		user = frappe.session.user
		if not frappe.conn.sql("""select user from __Auth where password=password(%s) 
			and user=%s""", (old_password, user)):
			return _("Cannot Update: Incorrect Password")
	
	_update_password(user, new_password)
	
	frappe.conn.set_value("Profile", user, "reset_password_key", "")
	
	frappe.local.login_manager.logout()
	
	return _("Password Updated")
	
@frappe.whitelist(allow_guest=True)
def sign_up(email, full_name):
	profile = frappe.conn.get("Profile", {"email": email})
	if profile:
		if profile.disabled:
			return _("Registered but disabled.")
		else:
			return _("Already Registered")
	else:
		if frappe.conn.sql("""select count(*) from tabProfile where 
			TIMEDIFF(%s, modified) > '1:00:00' """, now())[0][0] > 200:
			raise Exception, "Too Many New Profiles"
		from frappe.utils import random_string
		profile = frappe.bean({
			"doctype":"Profile",
			"email": email,
			"first_name": full_name,
			"enabled": 1,
			"new_password": random_string(10),
			"user_type": "Website User"
		})
		profile.ignore_permissions = True
		profile.insert()
		return _("Registration Details Emailed.")

@frappe.whitelist(allow_guest=True)
def reset_password(user):	
	user = frappe.form_dict.get('user', '')
	if user in ["demo@erpnext.com", "Administrator"]:
		return "Not allowed"
		
	if frappe.conn.sql("""select name from tabProfile where name=%s""", (user,)):
		# Hack!
		frappe.session["user"] = "Administrator"
		profile = frappe.bean("Profile", user)
		profile.get_controller().reset_password()
		return "Password reset details sent to your email."
	else:
		return "No such user (%s)" % user

@frappe.whitelist(allow_guest=True)
def facebook_login(data):
	data = json.loads(data)
	
	if not (data.get("id") and data.get("fb_access_token")):
		raise frappe.ValidationError

	user = data["email"]
		
	if not get_fb_userid(data.get("fb_access_token")):
		# garbage
		raise frappe.ValidationError
	
	if not frappe.conn.exists("Profile", user):
		if data.get("birthday"):
			b = data.get("birthday").split("/")
			data["birthday"] = b[2] + "-" + b[0] + "-" + b[1]
		
		profile = frappe.bean({
			"doctype":"Profile",
			"first_name": data["first_name"],
			"last_name": data["last_name"],
			"email": data["email"],
			"enabled": 1,
			"new_password": frappe.generate_hash(data["email"]),
			"fb_username": data["username"],
			"fb_userid": data["id"],
			"location": data.get("location", {}).get("name"),
			"birth_date":  data.get("birthday"),
			"user_type": "Website User"
		})
		profile.ignore_permissions = True
		profile.get_controller().no_welcome_mail = True
		profile.insert()
	
	frappe.local.login_manager.user = user
	frappe.local.login_manager.post_login()
	
def get_fb_userid(fb_access_token):
	import requests
	response = requests.get("https://graph.facebook.com/me?access_token=" + fb_access_token)
	if response.status_code==200:
		print response.json()
		return response.json().get("id")
	else:
		return frappe.AuthenticationError
		
def profile_query(doctype, txt, searchfield, start, page_len, filters):
	from frappe.widgets.reportview import get_match_cond
	return frappe.conn.sql("""select name, concat_ws(' ', first_name, middle_name, last_name) 
		from `tabProfile` 
		where ifnull(enabled, 0)=1 
			and docstatus < 2 
			and name not in ('Administrator', 'Guest') 
			and user_type != 'Website User'
			and (%(key)s like "%(txt)s" 
				or concat_ws(' ', first_name, middle_name, last_name) like "%(txt)s") 
			%(mcond)s
		order by 
			case when name like "%(txt)s" then 0 else 1 end, 
			case when concat_ws(' ', first_name, middle_name, last_name) like "%(txt)s" 
				then 0 else 1 end, 
			name asc 
		limit %(start)s, %(page_len)s""" % {'key': searchfield, 'txt': "%%%s%%" % txt,  
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 'page_len': page_len})

def get_total_users():
	"""Returns total no. of system users"""
	return frappe.conn.sql("""select count(*) from `tabProfile`
		where enabled = 1 and user_type != 'Website User'
		and name not in ('Administrator', 'Guest')""")[0][0]

def get_active_users():
	"""Returns No. of system users who logged in, in the last 3 days"""
	return frappe.conn.sql("""select count(*) from `tabProfile`
		where enabled = 1 and user_type != 'Website User'
		and name not in ('Administrator', 'Guest')
		and hour(timediff(now(), last_login)) < 72""")[0][0]

def get_website_users():
	"""Returns total no. of website users"""
	return frappe.conn.sql("""select count(*) from `tabProfile`
		where enabled = 1 and user_type = 'Website User'""")[0][0]
	
def get_active_website_users():
	"""Returns No. of website users who logged in, in the last 3 days"""
	return frappe.conn.sql("""select count(*) from `tabProfile`
		where enabled = 1 and user_type = 'Website User'
		and hour(timediff(now(), last_login)) < 72""")[0][0]

