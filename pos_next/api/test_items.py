from types import SimpleNamespace
import unittest
from unittest.mock import patch

import frappe
import pos_next.api.items as items_module


class TestCustomerPriceListResolution(unittest.TestCase):
	def test_uses_pos_profile_price_list_without_customer(self):
		pos_profile = SimpleNamespace(selling_price_list="Standard Selling")

		self.assertEqual(
			items_module.get_effective_selling_price_list(pos_profile),
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

		fake_frappe = SimpleNamespace(db=SimpleNamespace(get_value=get_value))

		with patch.object(items_module, "frappe", fake_frappe):
			self.assertEqual(
				items_module.get_effective_selling_price_list(
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

		fake_frappe = SimpleNamespace(db=SimpleNamespace(get_value=get_value))

		with patch.object(items_module, "frappe", fake_frappe):
			self.assertEqual(
				items_module.get_effective_selling_price_list(pos_profile, "Test Customer"),
				"Standard Selling",
			)


class TestPOSItemRequestCreation(unittest.TestCase):
	def test_creates_request_and_uses_pos_profile_defaults(self):
		captured = {}

		class FakeDoc:
			def __init__(self, payload):
				self.__dict__.update(payload)

			def insert(self, ignore_permissions=False):
				captured["ignore_permissions"] = ignore_permissions
				self.name = "PIR-.00001"
				return self

		def fake_get_doc(payload):
			captured["payload"] = payload
			return FakeDoc(payload)

		def fake_get_value(doctype, name, fields=None, as_dict=False):
			if doctype == "POS Profile":
				return {"name": name, "company": "BrainWise", "warehouse": "Main Store"}
			return None

		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(get_value=fake_get_value),
			get_doc=fake_get_doc,
			session=SimpleNamespace(user="test.user@example.com"),
			throw=lambda msg: (_ for _ in ()).throw(RuntimeError(msg)),
			log_error=lambda *args, **kwargs: None,
			get_traceback=lambda: "traceback",
		)

		frappe.local.flags = SimpleNamespace(in_test=True)

		with patch.object(items_module, "frappe", fake_frappe):
			result = items_module.create_pos_item_request(
				requested_item_name="Steel Nail",
				availability_type="not_in_inventory",
				customer={"name": "CUST-0001"},
				mobile_no="9999999999",
				pos_profile="POS-RETAIL",
				qty=2,
				uom="Nos",
				staff_user="test.user@example.com",
				notes="Customer asked at counter 1",
			)

		self.assertEqual(result["name"], "PIR-.00001")
		self.assertTrue(captured["ignore_permissions"])
		self.assertEqual(captured["payload"]["requested_item_name"], "Steel Nail")
		self.assertEqual(captured["payload"]["company"], "BrainWise")
		self.assertEqual(captured["payload"]["warehouse"], "Main Store")
		self.assertEqual(captured["payload"]["availability_type"], "not_in_inventory")
