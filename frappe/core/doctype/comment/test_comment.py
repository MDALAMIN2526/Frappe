# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe, unittest, json

# commented due to commits -- only run when comments are modified

# class TestComment(unittest.TestCase):
# 	def setUp(self):
# 		self.cleanup()
# 		self.test_rec = frappe.bean({
# 			"doctype":"Event",
# 			"subject":"__Comment Test Event",
# 			"event_type": "Private",
# 			"starts_on": "2011-01-01 10:00:00",
# 			"ends_on": "2011-01-01 10:00:00",
# 		}).insert()
# 		
# 	def tearDown(self):
# 		self.cleanup()
# 	
# 	def cleanup(self):
# 		frappe.conn.sql("""delete from tabEvent where subject='__Comment Test Event'""")
# 		frappe.conn.sql("""delete from tabComment where comment='__Test Comment'""")
# 		frappe.conn.commit()
# 		if "_comments" in frappe.conn.get_table_columns("Event"):
# 			frappe.conn.commit()
# 			frappe.conn.sql("""alter table `tabEvent` drop column `_comments`""")
# 	
# 	def test_add_comment(self):
# 		self.comment = frappe.bean({
# 			"doctype":"Comment",
# 			"comment_doctype": self.test_rec.doc.doctype,
# 			"comment_docname": self.test_rec.doc.name,
# 			"comment": "__Test Comment"
# 		}).insert()
# 		
# 		test_rec = frappe.doc(self.test_rec.doc.doctype, self.test_rec.doc.name)
# 		_comments = json.loads(test_rec.get("_comments"))
# 		self.assertTrue(_comments[0].get("comment")=="__Test Comment")
# 		
# 	def test_remove_comment(self):
# 		self.test_add_comment()
# 		frappe.delete_doc("Comment", self.comment.doc.name)
# 		test_rec = frappe.doc(self.test_rec.doc.doctype, self.test_rec.doc.name)
# 		_comments = json.loads(test_rec.get("_comments"))
# 		self.assertEqual(len(_comments), 0)
# 		
# 		
# if __name__=="__main__":
# 	unittest.main()