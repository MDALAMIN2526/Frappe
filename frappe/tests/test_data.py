# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import guess_date_format

test_date_obj = datetime.datetime.now()
test_datetime = test_date_obj.strftime("%Y-%m-%d %H:%M:%S.%f")
test_date_formats = {
	"%Y-%m-%d": test_date_obj.strftime("%Y-%m-%d"),
	"%d-%m-%Y": test_date_obj.strftime("%d-%m-%Y"),
	"%d/%m/%Y": test_date_obj.strftime("%d/%m/%Y"),
	"%d.%m.%Y": test_date_obj.strftime("%d.%m.%Y"),
	"%m/%d/%Y": test_date_obj.strftime("%m/%d/%Y"),
	"%m-%d-%Y": test_date_obj.strftime("%m-%d-%Y"),
	"%Y.%m.%d.": test_date_obj.strftime("%Y.%m.%d."),
}
test_time_formats = {
	"%H:%M:%S": test_date_obj.strftime("%H:%M:%S"),
	"%H:%M": test_date_obj.strftime("%H:%M"),
}


class TestData(FrappeTestCase):
	"""Tests date, time and datetime formatters and some associated
	utility functions. These rely on the system-wide date and time
	formats.
	"""

	def test_guess_format(self):
		# Test formatdate with various default date formats set
		for valid_format, date_str in test_date_formats.items():
			frappe.db.set_default("date_format", valid_format)
			self.assertEqual(guess_date_format(date_str), valid_format)
