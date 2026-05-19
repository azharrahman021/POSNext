# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pos_next.api.pos_profile import get_sales_persons


class TestPosProfileAPI(unittest.TestCase):
	def test_get_sales_persons_returns_all_enabled_sales_people(self):
		mock_frappe = Mock()
		mock_frappe.db.get_value.return_value = "Fix & Build Margin Free Store -Karanthad"
		mock_frappe.db.has_column.return_value = False
		mock_frappe.get_all.return_value = [
			SimpleNamespace(name="Azhar", sales_person_name="Azhar", employee="HR-EMP-00001")
		]

		with patch("pos_next.api.pos_profile.frappe", new=mock_frappe):
			result = get_sales_persons.__wrapped__(pos_profile="Fix & Build Margin Free Store -Karanthad")

		self.assertEqual(len(result), 1)
		mock_frappe.get_all.assert_called_once_with(
			"Sales Person",
			filters={"enabled": 1, "is_group": 0},
			fields=["name", "sales_person_name", "commission_rate", "employee"],
			order_by="sales_person_name",
			limit_page_length=0,
		)

	def test_get_sales_persons_keeps_company_filter_if_sales_person_has_company_field(self):
		mock_frappe = Mock()
		mock_frappe.db.get_value.return_value = "Fix & Build Margin Free Store -Palakode"
		mock_frappe.db.has_column.return_value = True
		mock_frappe.get_all.return_value = []

		with patch("pos_next.api.pos_profile.frappe", new=mock_frappe):
			get_sales_persons.__wrapped__(pos_profile="Fix & Build Margin Free Store -Palakode")

		mock_frappe.get_all.assert_called_once_with(
			"Sales Person",
			filters={"enabled": 1, "is_group": 0, "company": "Fix & Build Margin Free Store -Palakode"},
			fields=["name", "sales_person_name", "commission_rate", "employee"],
			order_by="sales_person_name",
			limit_page_length=0,
		)
