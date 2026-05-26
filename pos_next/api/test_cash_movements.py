# Copyright (c) 2026, BrainWise and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import Mock, patch

from pos_next.api.cash_movements import (
	create_cash_movement,
	get_party_balance_summary,
	_resolve_account_details,
	_score_expense_account,
)


class TestCashMovementsAPI(unittest.TestCase):
	def test_score_expense_account_prefers_rent_related_accounts(self):
		rent_account = {
			"name": "Rent Expense - THS",
			"account_name": "Rent Expense",
			"account_number": "",
		}
		misc_account = {
			"name": "Printing Charges - THS",
			"account_name": "Printing Charges",
			"account_number": "",
		}

		self.assertGreater(_score_expense_account("rent", rent_account), _score_expense_account("rent", misc_account))

	@patch("pos_next.api.cash_movements.get_balance_on", side_effect=[1250.0, 1875.0])
	@patch("pos_next.api.cash_movements._resolve_party_account")
	def test_get_party_balance_summary_returns_company_and_all_company_balances(
		self,
		mock_resolve_party_account,
		mock_get_balance_on,
	):
		mock_resolve_party_account.return_value = {
			"party_account": "Debtors - THS",
			"party_account_currency": "INR",
			"party_name": "Test Customer",
		}

		get_party_balance_summary_fn = getattr(get_party_balance_summary, "__wrapped__", get_party_balance_summary)
		summary = get_party_balance_summary_fn(
			company="Fix & Build Margin Free Store -Palakode",
			party_type="Customer",
			party="CUST-0001",
			posting_date="2026-05-26",
		)

		self.assertEqual(summary["company_balance"], 1250.0)
		self.assertEqual(summary["all_company_balance"], 1875.0)
		self.assertEqual(summary["party_name"], "Test Customer")

	@patch("pos_next.api.cash_movements.frappe.new_doc")
	@patch("pos_next.api.cash_movements._resolve_account_details")
	@patch("pos_next.api.cash_movements._resolve_payment_account")
	@patch("pos_next.api.cash_movements._resolve_party_account")
	@patch("pos_next.api.cash_movements._validate_pos_profile")
	@patch("pos_next.api.cash_movements.nowdate", return_value="2026-05-26")
	def test_customer_payment_prefills_account_details_before_validation(
		self,
		mock_nowdate,
		mock_validate_pos_profile,
		mock_resolve_party_account,
		mock_resolve_payment_account,
		mock_resolve_account_details,
		mock_new_doc,
	):
		mock_resolve_party_account.return_value = {"party_account": "Debtors - THS"}
		mock_resolve_payment_account.return_value = "Cash - THS"
		mock_resolve_account_details.side_effect = [
			{"currency": "INR", "balance": 1.0, "account_type": "Receivable"},
			{"currency": "INR", "balance": 2.0, "account_type": "Cash"},
		]

		pe = Mock()
		pe.doctype = "Payment Entry"
		pe.name = "PE-TEST"
		pe.insert.return_value = None
		pe.submit.return_value = None
		mock_new_doc.return_value = pe

		create_cash_movement_fn = getattr(create_cash_movement, "__wrapped__", create_cash_movement)
		result = create_cash_movement_fn(
			pos_profile="POS-1",
			company="Fix & Build Margin Free Store -Palakode",
			movement_type="customer",
			amount=100,
			mode_of_payment="Cash",
			party_type="Customer",
			party="CUST-0001",
			posting_date="2026-05-26",
		)

		self.assertEqual(result["name"], "PE-TEST")
		self.assertEqual(pe.paid_from, "Debtors - THS")
		self.assertEqual(pe.paid_to, "Cash - THS")
		self.assertEqual(pe.paid_from_account_currency, "INR")
		self.assertEqual(pe.paid_to_account_currency, "INR")
		self.assertEqual(pe.paid_from_account_type, "Receivable")
		self.assertEqual(pe.paid_to_account_type, "Cash")
		pe.setup_party_account_field.assert_called_once()
		pe.set_missing_values.assert_called_once()
		pe.set_exchange_rate.assert_called_once()
		pe.insert.assert_called_once()
		pe.submit.assert_called_once()

	@patch("pos_next.api.cash_movements.frappe.new_doc")
	@patch("pos_next.api.cash_movements._resolve_account_details")
	@patch("pos_next.api.cash_movements._resolve_payment_account")
	@patch("pos_next.api.cash_movements._resolve_party_account")
	@patch("pos_next.api.cash_movements._validate_pos_profile")
	@patch("pos_next.api.cash_movements.nowdate", return_value="2026-05-26")
	def test_supplier_payment_prefills_account_details_before_validation(
		self,
		mock_nowdate,
		mock_validate_pos_profile,
		mock_resolve_party_account,
		mock_resolve_payment_account,
		mock_resolve_account_details,
		mock_new_doc,
	):
		mock_resolve_party_account.return_value = {"party_account": "Creditors - THS"}
		mock_resolve_payment_account.return_value = "Cash - THS"
		mock_resolve_account_details.side_effect = [
			{"currency": "INR", "balance": 1.0, "account_type": "Payable"},
			{"currency": "INR", "balance": 2.0, "account_type": "Cash"},
		]

		pe = Mock()
		pe.doctype = "Payment Entry"
		pe.name = "PE-TEST-2"
		pe.insert.return_value = None
		pe.submit.return_value = None
		mock_new_doc.return_value = pe

		create_cash_movement_fn = getattr(create_cash_movement, "__wrapped__", create_cash_movement)
		result = create_cash_movement_fn(
			pos_profile="POS-1",
			company="Fix & Build Margin Free Store -Palakode",
			movement_type="supplier",
			amount=100,
			mode_of_payment="Cash",
			party_type="Supplier",
			party="SUP-0001",
			posting_date="2026-05-26",
		)

		self.assertEqual(result["name"], "PE-TEST-2")
		self.assertEqual(pe.paid_from, "Cash - THS")
		self.assertEqual(pe.paid_to, "Creditors - THS")
		self.assertEqual(pe.paid_from_account_currency, "INR")
		self.assertEqual(pe.paid_to_account_currency, "INR")
		self.assertEqual(pe.paid_from_account_type, "Cash")
		self.assertEqual(pe.paid_to_account_type, "Payable")
		pe.setup_party_account_field.assert_called_once()
		pe.set_missing_values.assert_called_once()
		pe.set_exchange_rate.assert_called_once()
		pe.insert.assert_called_once()
		pe.submit.assert_called_once()

	@patch("pos_next.api.cash_movements.frappe.new_doc")
	@patch("pos_next.api.cash_movements._resolve_account_details")
	@patch("pos_next.api.cash_movements._resolve_payment_account")
	@patch("pos_next.api.cash_movements._resolve_write_off_details")
	@patch("pos_next.api.cash_movements._resolve_party_account")
	@patch("pos_next.api.cash_movements._validate_pos_profile")
	@patch("pos_next.api.cash_movements.nowdate", return_value="2026-05-26")
	def test_customer_payment_adds_write_off_deduction(
		self,
		mock_nowdate,
		mock_validate_pos_profile,
		mock_resolve_party_account,
		mock_resolve_write_off_details,
		mock_resolve_payment_account,
		mock_resolve_account_details,
		mock_new_doc,
	):
		mock_resolve_party_account.return_value = {"party_account": "Debtors - THS"}
		mock_resolve_payment_account.return_value = "Cash - THS"
		mock_resolve_write_off_details.return_value = {
			"write_off_account": "Write Off - THS",
			"write_off_cost_center": "Main - THS",
			"write_off_limit": 5000,
		}
		mock_resolve_account_details.side_effect = [
			{"currency": "INR", "balance": 1.0, "account_type": "Receivable"},
			{"currency": "INR", "balance": 2.0, "account_type": "Cash"},
		]

		pe = Mock()
		pe.doctype = "Payment Entry"
		pe.name = "PE-WOFF"
		pe.append = Mock(return_value=Mock())
		pe.insert.return_value = None
		pe.submit.return_value = None
		mock_new_doc.return_value = pe

		create_cash_movement_fn = getattr(create_cash_movement, "__wrapped__", create_cash_movement)
		result = create_cash_movement_fn(
			pos_profile="POS-1",
			company="Fix & Build Margin Free Store -Palakode",
			movement_type="customer",
			amount=450,
			mode_of_payment="Cash",
			party_type="Customer",
			party="CUST-0001",
			write_off_amount=50,
			write_off_account="Write Off - THS",
			write_off_cost_center="Main - THS",
			posting_date="2026-05-26",
		)

		self.assertEqual(result["name"], "PE-WOFF")
		self.assertEqual(pe.write_off_difference_amount, 50)
		pe.append.assert_called_once()
		mock_resolve_write_off_details.assert_called_once()
		self.assertEqual(pe.append.call_args[0][0], "deductions")
		self.assertEqual(pe.append.call_args[0][1]["account"], "Write Off - THS")
		self.assertEqual(pe.append.call_args[0][1]["cost_center"], "Main - THS")
		self.assertEqual(pe.append.call_args[0][1]["amount"], 50)
		pe.setup_party_account_field.assert_called_once()
		pe.set_missing_values.assert_called_once()
		pe.set_exchange_rate.assert_called_once()
		pe.insert.assert_called_once()
		pe.submit.assert_called_once()
