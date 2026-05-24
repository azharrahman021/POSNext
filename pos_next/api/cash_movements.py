# Copyright (c) 2026, BrainWise and contributors
# For license information, please see license.txt

"""
POS cash movement helpers.

This module provides a lightweight POS-facing entry point for:
- customer payments (Payment Entry, Receive)
- supplier payments (Payment Entry, Pay)
- expenses (Journal Entry)
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_details
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

from pos_next.api.partial_payments import _has_pos_profile_access


def _validate_pos_profile(pos_profile: str, company: str):
	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	if not company:
		frappe.throw(_("Company is required"))

	if not frappe.db.exists("POS Profile", pos_profile):
		frappe.throw(_("POS Profile {0} does not exist").format(pos_profile))

	profile_company = frappe.db.get_value("POS Profile", pos_profile, "company")
	if profile_company != company:
		frappe.throw(_("POS Profile company does not match the selected company"))

	if not _has_pos_profile_access(pos_profile):
		frappe.throw(_("You don't have access to this POS Profile"))


def _resolve_payment_account(mode_of_payment: str, company: str, payment_account: str | None = None) -> str:
	if payment_account:
		if not frappe.db.exists("Account", payment_account):
			frappe.throw(_("Payment account {0} does not exist").format(payment_account))
		return payment_account

	if not mode_of_payment:
		frappe.throw(_("Mode of Payment is required"))

	account_info = get_bank_cash_account(mode_of_payment, company)
	if not account_info or not account_info.get("account"):
		frappe.throw(
			_("Could not determine an account for {0}. Please select one explicitly.").format(
				mode_of_payment
			)
		)

	return account_info.get("account")


def _resolve_party_account(company: str, party_type: str, party: str, posting_date: str, cost_center: str | None = None):
	party_details = get_party_details(company, party_type, party, posting_date, cost_center=cost_center)
	if not party_details or not party_details.get("party_account"):
		frappe.throw(_("Could not determine the {0} account for {1}").format(party_type, party))
	return party_details


@frappe.whitelist()
def get_cash_movement_defaults(company: str):
	if not company:
		frappe.throw(_("Company is required"))

	return frappe.db.get_value(
		"Company",
		company,
		["default_expense_account", "cost_center", "default_currency"],
		as_dict=True,
	) or {}


@frappe.whitelist()
def search_expense_accounts(company: str, txt: str = "", page_length: int = 20):
	if not company:
		frappe.throw(_("Company is required"))

	conditions = {
		"company": company,
		"account_type": "Expense Account",
		"is_group": 0,
		"disabled": 0,
	}
	if txt:
		conditions["name"] = ["like", f"%{txt}%"]

	return frappe.get_all(
		"Account",
		filters=conditions,
		fields=["name", "account_name", "account_number"],
		order_by="account_name asc",
		limit_page_length=page_length,
	)


@frappe.whitelist()
def create_cash_movement(
	pos_profile: str,
	company: str,
	movement_type: str,
	amount: float,
	mode_of_payment: str | None = None,
	payment_account: str | None = None,
	party_type: str | None = None,
	party: str | None = None,
	expense_account: str | None = None,
	cost_center: str | None = None,
	reference_no: str | None = None,
	remarks: str | None = None,
	posting_date: str | None = None,
):
	_validate_pos_profile(pos_profile, company)

	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Amount must be greater than zero"))

	posting_date = posting_date or nowdate()
	if getdate(posting_date) > getdate(nowdate()):
		frappe.throw(_("Posting date cannot be in the future"))

	movement_type = (movement_type or "").strip().lower()
	if movement_type not in {"customer", "supplier", "expense"}:
		frappe.throw(_("Invalid movement type"))

	if movement_type in {"customer", "supplier"}:
		if not party_type or not party:
			frappe.throw(_("Party is required"))

		expected_party_type = "Customer" if movement_type == "customer" else "Supplier"
		if party_type != expected_party_type:
			frappe.throw(_("Party type must be {0}").format(expected_party_type))

		party_details = _resolve_party_account(company, party_type, party, posting_date, cost_center)
		bank_account = _resolve_payment_account(mode_of_payment, company, payment_account)

		payment_type = "Receive" if movement_type == "customer" else "Pay"
		pe = frappe.new_doc("Payment Entry")
		pe.company = company
		pe.payment_type = payment_type
		pe.party_type = party_type
		pe.party = party
		pe.posting_date = posting_date
		pe.reference_no = (reference_no or "")[:140] or f"POS-{pos_profile}"
		pe.remarks = (remarks or "").strip() or f"POS Next {movement_type} payment"
		pe.mode_of_payment = mode_of_payment
		pe.cost_center = cost_center
		pe.paid_amount = amount
		pe.received_amount = amount

		if payment_type == "Receive":
			pe.paid_from = party_details.get("party_account")
			pe.paid_to = bank_account
		else:
			pe.paid_from = bank_account
			pe.paid_to = party_details.get("party_account")

		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.set_exchange_rate()
		pe.flags.ignore_permissions = True
		pe.insert()
		pe.submit()

		return {
			"doctype": pe.doctype,
			"name": pe.name,
			"payment_type": pe.payment_type,
		}

	if not expense_account:
		frappe.throw(_("Expense account is required"))

	expense_account_doc = frappe.db.get_value(
		"Account",
		expense_account,
		["company", "account_type", "is_group", "disabled"],
		as_dict=True,
	)
	if not expense_account_doc or expense_account_doc.disabled:
		frappe.throw(_("Expense account {0} does not exist").format(expense_account))
	if expense_account_doc.company != company:
		frappe.throw(_("Expense account must belong to the selected company"))
	if expense_account_doc.is_group:
		frappe.throw(_("Expense account must be a ledger account"))
	if expense_account_doc.account_type != "Expense Account":
		frappe.throw(_("Selected account must be an Expense Account"))

	bank_account = _resolve_payment_account(mode_of_payment, company, payment_account)
	defaults = get_cash_movement_defaults(company) or {}
	cost_center = cost_center or defaults.get("cost_center")

	jv = frappe.new_doc("Journal Entry")
	jv.voucher_type = "Journal Entry"
	jv.company = company
	jv.posting_date = posting_date
	jv.user_remark = (remarks or "").strip() or f"POS Next expense entry - {reference_no or pos_profile}"

	debit_row = jv.append("accounts", {})
	debit_row.account = expense_account
	debit_row.debit_in_account_currency = amount
	debit_row.credit_in_account_currency = 0
	debit_row.cost_center = cost_center

	credit_row = jv.append("accounts", {})
	credit_row.account = bank_account
	credit_row.debit_in_account_currency = 0
	credit_row.credit_in_account_currency = amount
	credit_row.cost_center = cost_center

	jv.flags.ignore_permissions = True
	jv.save()
	jv.submit()

	return {
		"doctype": jv.doctype,
		"name": jv.name,
		"payment_type": "Expense",
	}
