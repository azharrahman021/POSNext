# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import Mock, patch

from pos_next.api.invoices import update_invoice


class TestInvoicesAPI(unittest.TestCase):
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
