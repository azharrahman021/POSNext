# -*- coding: utf-8 -*-
# Copyright (c) 2020, Youssef Restom and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pos_next.pos_next.doctype.pos_closing_shift.pos_closing_shift import POSClosingShift


class TestPOSClosingShift(unittest.TestCase):
	def test_ensure_no_draft_invoices_blocks_close_when_drafts_exist(self):
		mock_frappe = Mock()
		mock_frappe.db.has_column.return_value = True
		mock_frappe.get_all.side_effect = [["SINV-0001"], []]
		mock_frappe.throw.side_effect = RuntimeError("blocked")

		with patch("pos_next.pos_next.doctype.pos_closing_shift.pos_closing_shift.frappe", new=mock_frappe):
			with patch("pos_next.pos_next.doctype.pos_closing_shift.pos_closing_shift._", side_effect=lambda text, *args, **kwargs: text):
				with self.assertRaises(RuntimeError):
					POSClosingShift.ensure_no_draft_invoices(
						SimpleNamespace(
							pos_profile="POS Profile - Test",
							pos_opening_shift="POS-OS-0001",
							user="cashier@example.com",
						)
					)

		mock_frappe.throw.assert_called_once()

	def test_ensure_no_draft_invoices_ignores_other_users_drafts(self):
		mock_frappe = Mock()
		mock_frappe.db.has_column.return_value = True
		mock_frappe.get_all.side_effect = [[], []]
		mock_frappe.throw.side_effect = RuntimeError("blocked")

		with patch("pos_next.pos_next.doctype.pos_closing_shift.pos_closing_shift.frappe", new=mock_frappe):
			POSClosingShift.ensure_no_draft_invoices(
				SimpleNamespace(
					pos_profile="POS Profile - Test",
					pos_opening_shift="POS-OS-0001",
					user="cashier@example.com",
				)
			)

		first_call = mock_frappe.get_all.call_args_list[0]
		self.assertEqual(first_call.kwargs["filters"]["owner"], "cashier@example.com")
		self.assertEqual(len(mock_frappe.get_all.call_args_list), 2)

	def test_on_submit_does_not_delete_drafts(self):
		opening_entry = SimpleNamespace(pos_closing_shift=None, set_status=Mock(), save=Mock())
		mock_frappe = Mock()
		mock_frappe.get_doc.return_value = opening_entry

		fake_shift = SimpleNamespace(
			pos_opening_shift="POS-OS-0001",
			name="POS-CS-0001",
			_set_closing_entry_invoices=Mock(),
			delete_draft_invoices=Mock(side_effect=AssertionError("should not delete drafts on submit")),
		)

		with patch("pos_next.pos_next.doctype.pos_closing_shift.pos_closing_shift.frappe", new=mock_frappe):
			POSClosingShift.on_submit(fake_shift)

		fake_shift.delete_draft_invoices.assert_not_called()
		fake_shift._set_closing_entry_invoices.assert_called_once()
		opening_entry.set_status.assert_called_once()
		opening_entry.save.assert_called_once()
