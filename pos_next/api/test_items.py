from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pos_next.api.items import get_effective_selling_price_list


class TestCustomerPriceListResolution(unittest.TestCase):
	def test_uses_pos_profile_price_list_without_customer(self):
		pos_profile = SimpleNamespace(selling_price_list="Standard Selling")

		self.assertEqual(
			get_effective_selling_price_list(pos_profile),
			"Standard Selling",
		)

	def test_uses_customer_default_price_list_when_enabled_for_selling(self):
		pos_profile = SimpleNamespace(selling_price_list="Standard Selling")

		def get_value(doctype, name, fields=None, as_dict=False):
			if doctype == "Customer":
				return "Retail Price List"
			if doctype == "Price List":
				return SimpleNamespace(name=name, enabled=1, selling=1)
			return None

		with patch("pos_next.api.items.frappe.db.get_value", side_effect=get_value):
			self.assertEqual(
				get_effective_selling_price_list(
					pos_profile,
					{"name": "Test Customer"},
				),
				"Retail Price List",
			)

	def test_falls_back_when_customer_price_list_is_not_selling(self):
		pos_profile = SimpleNamespace(selling_price_list="Standard Selling")

		def get_value(doctype, name, fields=None, as_dict=False):
			if doctype == "Customer":
				return "Buying Price List"
			if doctype == "Price List":
				return SimpleNamespace(name=name, enabled=1, selling=0)
			return None

		with patch("pos_next.api.items.frappe.db.get_value", side_effect=get_value):
			self.assertEqual(
				get_effective_selling_price_list(pos_profile, "Test Customer"),
				"Standard Selling",
			)
