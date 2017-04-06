from __future__ import unicode_literals
import datetime
import frappe
import json
import sys
from frappe.utils.kickapp.helper import Helper
from frappe.utils.kickapp.utils import *
from frappe.utils.kickapp.query import Query


class Base(object):
	def __init__(self, obj):
		self.obj = obj
		self.bot_name = frappe._dict(obj.bot_data).bot_name
		self.query = Query(self.bot_name)
		self.helper = Helper()

	def get_message(self, msg="Something went wrong, Please try in a little bit.", bot_data = None):
		obj = self.obj
		obj.created_at = self.get_created_at()
		obj.text = msg
		obj.chat_data = None
		obj.bot_data = self.get_bot_data() if bot_data is None else bot_data
		return obj

	def get_action_by_text(self, text):
		return self.query.get_action_from_text(text)

	def get_list(self, doctype, fields, filters):
		return self.helper.get_list(doctype, fields, 0, 3, filters)

	def get_created_at(self):
		return get_date(str(datetime.datetime.now()))

	def get_bot_data(self, base_action=None, button_text=None, 
		is_interactive_chat=False, is_interactive_list=False, items=[]):
		return {
			"bot_name":self.bot_name,
			"info":{
				"base_action": base_action,
				"button_text": button_text,
				"is_interactive_chat": is_interactive_chat,
				"is_interactive_list": is_interactive_list,
				"items": items
			}
		}

class Basic_Bot(Base):
	def __init__(self, obj):
		Base.__init__(self, obj)
		self.bot_name = frappe._dict(obj.bot_data).bot_name
		self.fields = self.helper.get_doctype_fields_from_bot_name(self.bot_name)
		self.messages = self.helper.get_messages_from_bot_name(self.bot_name)
		self.doctype = self.helper.get_doctype_name_from_bot_name(self.bot_name)
		self.item_id = frappe._dict(obj.meta).item_id

	def get_results(self):
		method = self.get_method()
		if method == 'error':
			return self.get_message("Something went wrong, please try a diffrent query")
		if method == 'cancel':
			return self.get_message("Last process cancelled")
		else:
			return getattr(self, method)()
	
	def call_lower_class_methods(self, method_name, params):
		if self.doctype == "Note":
			return getattr(Note(), method_name)(params)
		elif self.doctype == "ToDo":
			return getattr(ToDo(), method_name)(params)
	
	def get_method(self):
		obj = self.obj
		bot_data = frappe._dict(obj.bot_data)
		base_action = frappe._dict(bot_data.info).base_action
		if obj.text.lower() == 'exit' or obj.text.lower() == 'cancel':
			return 'cancel'
		if base_action == 'create_':
			return 'create_'
		elif base_action is not None and self.item_id is not None:
			return base_action.lower()
		return self.get_action_by_text(obj.text).lower()

	def create(self):
		bot_data = self.get_bot_data(base_action='create_')
		return self.get_message(self.messages.get('create'), bot_data = bot_data)

	def update(self):
		items = self.get_list(self.doctype, self.fields, filters={"owner": self.obj.user_id})
		bot_data = self.get_bot_data(base_action='update_', button_text='load more', 
			is_interactive_list=True, items=self.call_lower_class_methods('map_list', items))
		return self.get_message(self.messages.get('update'), bot_data = bot_data)
		
	def delete(self):
		items = self.get_list(self.doctype, self.fields, filters={"owner": self.obj.user_id})
		bot_data = self.get_bot_data(base_action='delete_', button_text='load more', 
			is_interactive_list=True, items=self.call_lower_class_methods('map_list', items))
		return self.get_message(self.messages.get('delete'), bot_data = bot_data)

	def get(self):
		items = self.get_list(self.doctype, self.fields, filters={"owner": self.obj.user_id})
		bot_data = self.get_bot_data(button_text='load more', is_interactive_list=True, 
			items=self.call_lower_class_methods('map_list', items))
		return self.get_message(self.messages.get('get'), bot_data = bot_data)

	def create_(self):
		params = {
			"doctype":self.doctype,
			"obj":self.obj,
			"item_id" : self.item_id
		}
		
		data = self.call_lower_class_methods('create_', params)
		if data.is_success:
			items = self.get_list(self.doctype, self.fields, data.filters)
			bot_data = self.get_bot_data(button_text='view info', is_interactive_chat=True, 
				items=self.call_lower_class_methods('map_list', items))
			return self.get_message(self.messages.get('create_'), bot_data = bot_data)
		return self.get_message()

	def update_(self):
		params = {
			"doctype":self.doctype,
			"obj":self.obj,
			"item_id" : self.item_id
		}
		
		data =  self.call_lower_class_methods('update_', params)

		if data.is_success:
			items = self.get_list(self.doctype, self.fields, data.filters)
			bot_data = self.get_bot_data(button_text='view info', is_interactive_chat=True, 
				items=self.call_lower_class_methods('map_list', items))
			return self.get_message(self.messages.get('update_'), bot_data = bot_data)
		return self.get_message()

	def delete_(self):
		filters = {"name": self.item_id, "owner": self.obj.user_id}
		try:
			items = self.get_list(self.doctype, self.fields, filters)
			if len(items) > 0:
				frappe.delete_doc(self.doctype, self.item_id)
				frappe.db.commit()
				bot_data = self.get_bot_data(button_text='view info', is_interactive_chat=True, 
					items=self.call_lower_class_methods('map_list', items))
				return self.get_message(self.messages.get('delete_'), bot_data = bot_data)
			else:
				return self.get_message("Looks like item already deleted from database.")
		except Exception, e:
			print e
			return self.get_message()


class Note(object):

	def map_list(self, items):
		new_list = []
		for item in items:
			new_list.append({
				"id": item.name,
				"text": item.name if item.content is None else item.content,
				"creation": str(item.creation).split('.')[0]
			})
		return new_list

	def create_(self, params):
		doctype = params.get('doctype')
		obj = params.get('obj')
		user_id = frappe._dict(obj.meta).user_id
		filters = None
		is_success = False
		try:
			title = obj.text[0:9] if len(obj.text) > 10 else obj.text 
			note_doc = frappe.get_doc({"doctype":doctype, "title": title})
			note_doc.content = obj.text
			note_doc.owner = user_id
			note_doc.save()
			frappe.db.commit()
			filters = {"name": note_doc.name, "owner": user_id}
			is_success = True
		except Exception, e:
			print e
			filters = None
			is_success = False
		return frappe._dict({
			"is_success" : is_success,
			"filters": filters
		})

	def update_(self, params):
		doctype = params.get('doctype')
		obj = params.get('obj')
		item_id = params.get('item_id')
		user_id = frappe._dict(obj.meta).user_id
		filters = None
		is_success = False
		try:
			frappe.set_value(doctype, item_id, "content", obj.text)
			frappe.db.commit()
			filters = {"name": item_id, "owner": user_id}
			is_success = True
		except Exception, e:
			print e
			filters = None
			is_success = False
		return frappe._dict({
			"is_success" : is_success,
			"filters": filters
		})

class ToDo(object):

	def map_list(self, items):
		new_list = []
		for item in items:
			new_list.append({
				"id": item.name,
				"text": item.description,
				"creation": str(item.creation).split('.')[0]
			})
		return new_list

	def create_(self, params):
		print 'creatre--------------'
		doctype = params.get('doctype')
		obj = params.get('obj')
		user_id = frappe._dict(obj.meta).user_id
		filters = None
		is_success = False
		try:
			todo_doc = frappe.new_doc(doctype)
			todo_doc.description = obj.text
			todo_doc.owner = user_id
			todo_doc.save()
			frappe.db.commit()
			filters = {"name": todo_doc.name, "owner": user_id}
			is_success = True
		except Exception, e:
			filters = None
			is_success = False
		return frappe._dict({
			"is_success" : is_success,
			"filters": filters
		})

	def update_(self, params):
		doctype = params.get('doctype')
		obj = params.get('obj')
		user_id = frappe._dict(obj.meta).user_id
		item_id = params.get('item_id')
		filters = None
		is_success = False
		try:
			frappe.set_value(doctype, item_id, "description", obj.text)
			frappe.db.commit()
			filters = {"name": item_id, "owner": user_id}
			is_success = True
		except Exception, e:
			print e
			filters = None
			is_success = False
		return frappe._dict({
			"is_success" : is_success,
			"filters": filters
		})
