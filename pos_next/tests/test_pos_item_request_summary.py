import unittest
from unittest.mock import patch

from pos_next.tasks.pos_item_request_summary import _get_requests


class TestPOSItemRequestSummary(unittest.TestCase):
	def test_get_requests_excludes_closed_statuses(self):
		with patch("pos_next.tasks.pos_item_request_summary.frappe.get_all") as mocked_get_all:
			_get_requests("2026-05-28 00:00:00")

		mocked_get_all.assert_called_once()
		_, kwargs = mocked_get_all.call_args
		self.assertEqual(kwargs["filters"], [["creation", "<", "2026-05-28 00:00:00"], ["status", "in", ("new", "ordered")]])
