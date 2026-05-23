import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pos_next.pos_next.doctype.pos_item_request.pos_item_request import POSItemRequest


class TestPOSItemRequest(unittest.TestCase):
	def test_autoname_strips_literal_series_placeholder(self):
		doc = SimpleNamespace(naming_series="PIR-.YYYY.-.#####", name=None)

		with patch(
			"pos_next.pos_next.doctype.pos_item_request.pos_item_request.make_autoname",
			return_value="PIR-.2026.-.00001",
		) as mocked_make_autoname:
			POSItemRequest.autoname(doc)

		mocked_make_autoname.assert_called_once_with("PIR-.YYYY.-.#####", "", doc)
		self.assertEqual(doc.name, "PIR-.2026.-.00001")

	def test_autoname_uses_default_series_when_missing(self):
		doc = SimpleNamespace(name=None)

		with patch(
			"pos_next.pos_next.doctype.pos_item_request.pos_item_request.make_autoname",
			return_value="PIR-.2026.-.00002",
		) as mocked_make_autoname:
			POSItemRequest.autoname(doc)

		mocked_make_autoname.assert_called_once_with("PIR-.YYYY.-.#####", "", doc)
		self.assertEqual(doc.name, "PIR-.2026.-.00002")
