from types import SimpleNamespace
import unittest
from unittest.mock import patch

import frappe
import pos_next.api.item_locations as item_locations_module


class TestRackLocationConfig(unittest.TestCase):
	def setUp(self):
		frappe.local.flags = SimpleNamespace(in_test=True)
		self.translation_patcher = patch.object(item_locations_module, "_", lambda message: message)
		self.translation_patcher.start()

	def tearDown(self):
		self.translation_patcher.stop()

	def test_status_reports_missing_integration(self):
		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(exists=lambda doctype, name: False),
		)

		with patch.object(item_locations_module, "frappe", fake_frappe):
			result = item_locations_module.get_rack_location_facility_status(company="Test Co")

		self.assertFalse(result["integration_available"])
		self.assertFalse(result["can_manage"])

	def test_get_item_config_returns_rule_and_warehouse_options(self):
		def fake_exists(doctype, name):
			if doctype == "DocType":
				return True
			return False

		def fake_has_permission(doctype, perm_type):
			return doctype == item_locations_module.RULE_DOCTYPE and perm_type == "read"

		def fake_get_value(doctype, filters, fieldname):
			if doctype == item_locations_module.RULE_DOCTYPE:
				return "RULE-0001"
			return None

		def fake_get_all(doctype, filters=None, fields=None, order_by=None):
			if doctype == "Warehouse":
				return [
					SimpleNamespace(name="KD-A1", warehouse_name="A1"),
					SimpleNamespace(name="KD-A2", warehouse_name="A2"),
				]
			return []

		fake_rule = SimpleNamespace(
			name="RULE-0001",
			enabled=1,
			company="Test Co",
			item_code="ITEM-001",
			default_warehouse="KD-A1",
			display_label="A1",
			alternate_locations=[
				SimpleNamespace(warehouse="KD-A2", display_label="A2", priority=100),
			],
		)

		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(exists=fake_exists, get_value=fake_get_value),
			has_permission=fake_has_permission,
			get_doc=lambda doctype, name: fake_rule,
			get_all=fake_get_all,
			throw=lambda msg: (_ for _ in ()).throw(RuntimeError(msg)),
		)

		with patch.object(item_locations_module, "frappe", fake_frappe):
			result = item_locations_module.get_item_rack_location_config("ITEM-001", "Test Co")

		self.assertEqual(result["rule"]["default_warehouse"], "KD-A1")
		self.assertEqual(result["rule"]["alternate_locations"][0]["warehouse"], "KD-A2")
		self.assertEqual(result["warehouse_options"][0]["value"], "KD-A1")

	def test_upsert_updates_existing_rule_and_drops_default_from_alternates(self):
		def fake_exists(doctype, name):
			if doctype == "DocType":
				return True
			return False

		def fake_has_permission(doctype, perm_type):
			return doctype == item_locations_module.RULE_DOCTYPE and perm_type in {"create", "write"}

		def fake_get_value(doctype, filters, fieldname):
			if doctype == item_locations_module.RULE_DOCTYPE:
				return "RULE-0001"
			return None

		class FakeRule:
			def __init__(self):
				self.name = "RULE-0001"
				self.enabled = 0
				self.company = "Test Co"
				self.item_code = "ITEM-001"
				self.default_warehouse = "OLD"
				self.display_label = ""
				self.alternate_locations = []
				self.saved = False

			def set(self, fieldname, value):
				setattr(self, fieldname, value)

			def append(self, fieldname, value):
				getattr(self, fieldname).append(SimpleNamespace(**value))

			def save(self):
				self.saved = True

		fake_rule = FakeRule()
		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(exists=fake_exists, get_value=fake_get_value),
			has_permission=fake_has_permission,
			get_doc=lambda doctype, name: fake_rule,
			throw=lambda msg: (_ for _ in ()).throw(RuntimeError(msg)),
		)

		with patch.object(item_locations_module, "frappe", fake_frappe):
			result = item_locations_module.upsert_item_rack_location_config(
				item_code="ITEM-001",
				company="Test Co",
				default_warehouse="KD-A1",
				display_label="A1",
				alternate_locations=[
					{"warehouse": "KD-A1", "display_label": "A1", "priority": 10},
					{"warehouse": "KD-A2", "display_label": "A2", "priority": 20},
				],
				enabled=1,
			)

		self.assertTrue(fake_rule.saved)
		self.assertEqual(fake_rule.default_warehouse, "KD-A1")
		self.assertEqual(len(fake_rule.alternate_locations), 1)
		self.assertEqual(fake_rule.alternate_locations[0].warehouse, "KD-A2")
		self.assertEqual(result["rule"]["display_label"], "A1")
