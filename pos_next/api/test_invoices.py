# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import Mock, patch

from pos_next.api.invoices import cleanup_old_drafts, get_draft_invoices, update_invoice


class TestInvoicesAPI(unittest.TestCase):
    def test_get_draft_invoices_filters_to_logged_in_user(self):
        with patch("pos_next.api.invoices.frappe") as mock_frappe:
            mock_frappe.session.user = "cashier@example.com"
            mock_frappe.db.has_column.return_value = True
            mock_frappe.get_all.return_value = [{"name": "SINV-0001"}]
            mock_frappe.get_cached_doc.return_value = Mock(name="SINV-0001")

            result = get_draft_invoices.__wrapped__(
                pos_opening_shift="POS-OS-0001",
                pos_profile="POS Profile - Test",
            )

        mock_frappe.get_all.assert_called_once()
        filters = mock_frappe.get_all.call_args.kwargs["filters"]
        self.assertEqual(filters["docstatus"], 0)
        self.assertEqual(filters["owner"], "cashier@example.com")
        self.assertEqual(filters["posa_pos_opening_shift"], "POS-OS-0001")
        self.assertEqual(len(result), 1)

    def test_cleanup_old_drafts_is_non_destructive(self):
        with patch("pos_next.api.invoices.frappe") as mock_frappe:
            mock_frappe.get_all.return_value = [
                {"name": "SINV-OLD-0001", "modified": "2026-06-04 10:00:00"}
            ]

            result = cleanup_old_drafts.__wrapped__(
                pos_profile="POS Profile - Test",
                max_age_hours=1,
            )

        mock_frappe.delete_doc.assert_not_called()
        self.assertEqual(result["deleted"], 0)
        self.assertEqual(result["skipped"], 1)
        filters = mock_frappe.get_all.call_args.kwargs["filters"]
        self.assertEqual(filters["docstatus"], 0)
        self.assertEqual(filters["is_pos"], 1)
        self.assertEqual(filters["pos_profile"], "POS Profile - Test")

    @patch("pos_next.api.invoices.frappe.local", new=Mock(flags=Mock(in_test=True)))
    @patch("pos_next.api.invoices.frappe.log_error")
    @patch("pos_next.api.invoices.standardize_pricing_rules")
    @patch("pos_next.api.invoices.frappe.get_doc")
    def test_update_invoice_clears_stale_address_fields_when_customer_changes(
        self,
        mock_get_doc,
        mock_standardize_pricing_rules,
        mock_log_error,
    ):
        invoice_doc = Mock()
        invoice_doc.get.side_effect = lambda key, default=None: {
            "customer": "Cash Sale",
            "payments": [],
        }.get(key, default)
        invoice_doc.meta.has_field.return_value = True
        invoice_doc.as_dict.return_value = {"name": "ACC-SINV-0001"}
        invoice_doc.update.side_effect = RuntimeError("stop after update")

        mock_get_doc.return_value = invoice_doc

        with self.assertRaisesRegex(RuntimeError, "stop after update"):
            update_invoice(
                {
                    "doctype": "Sales Invoice",
                    "name": "ACC-SINV-0001",
                    "customer": "T1 Cash Sales",
                }
            )

        cleared_fields = [
            "customer_address",
            "shipping_address_name",
            "contact_person",
            "address_display",
            "shipping_address",
            "billing_address",
            "billing_address_display",
        ]
        self.assertEqual(
            [call.args for call in invoice_doc.set.call_args_list],
            [(field, None) for field in cleared_fields],
        )
        invoice_doc.update.assert_called_once_with(
            {
                "doctype": "Sales Invoice",
                "name": "ACC-SINV-0001",
                "customer": "T1 Cash Sales",
            }
        )
        mock_standardize_pricing_rules.assert_called_once_with(None)
        mock_log_error.assert_called_once()
