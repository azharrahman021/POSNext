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
from erpnext.accounts.utils import get_account_currency, get_balance_on

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
def get_party_balance_summary(
	company: str,
	party_type: str,
	party: str,
	posting_date: str | None = None,
	cost_center: str | None = None,
):
	if not company:
		frappe.throw(_("Company is required"))
	if party_type not in {"Customer", "Supplier"}:
		frappe.throw(_("Party type must be Customer or Supplier"))
	if not party:
		frappe.throw(_("Party is required"))

	posting_date = posting_date or nowdate()
	party_details = _resolve_party_account(company, party_type, party, posting_date, cost_center)

	company_balance = flt(
		get_balance_on(
			party_type=party_type,
			party=party,
			company=company,
			date=posting_date,
			cost_center=cost_center,
			ignore_account_permission=True,
		)
	)
	all_company_balance = flt(
		get_balance_on(
			party_type=party_type,
			party=party,
			date=posting_date,
			cost_center=cost_center,
			ignore_account_permission=True,
		)
	)

	return {
		"party": party,
		"party_name": party_details.get("party_name") or party,
		"party_account": party_details.get("party_account"),
		"party_account_currency": party_details.get("party_account_currency"),
		"company_balance": company_balance,
		"all_company_balance": all_company_balance,
		"posting_date": posting_date,
	}


def _resolve_account_details(account: str, posting_date: str, cost_center: str | None = None) -> dict:
	account_details = frappe.db.get_value(
		"Account",
		account,
		["account_currency", "account_type"],
		as_dict=True,
	)
	if not account_details:
		frappe.throw(_("Account {0} does not exist").format(account))

	balance = flt(
		get_balance_on(account, posting_date, cost_center=cost_center, ignore_account_permission=True)
	)
	if not balance:
		# Payment Entry.set_missing_values() treats a zero balance as "missing" and
		# falls back to a permission-checked account lookup. Use a tiny sentinel so
		# POS users can submit payments without needing direct Payment Entry access.
		balance = 0.000001

	return {
		"currency": account_details.account_currency or get_account_currency(account),
		"balance": balance,
		"account_type": account_details.account_type,
	}


def _resolve_write_off_details(
	pos_profile: str,
	write_off_account: str | None = None,
	write_off_cost_center: str | None = None,
) -> dict:
	details = frappe.db.get_value(
		"POS Profile",
		pos_profile,
		["write_off_account", "write_off_cost_center", "write_off_limit"],
		as_dict=True,
	) or {}

	return {
		"write_off_account": write_off_account or details.get("write_off_account"),
		"write_off_cost_center": write_off_cost_center or details.get("write_off_cost_center"),
		"write_off_limit": flt(details.get("write_off_limit") or 0),
	}


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


def _normalize_search_text(value: str) -> str:
	if not value:
		return ""
	return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _score_expense_account(query: str, account: dict) -> int:
	query_norm = _normalize_search_text(query)
	if not query_norm:
		return 0

	name = _normalize_search_text(account.get("name") or "")
	account_name = _normalize_search_text(account.get("account_name") or "")
	account_number = _normalize_search_text(account.get("account_number") or "")
	text = " ".join(part for part in [account_name, name, account_number] if part)
	tokens = [token for token in query_norm.split(" ") if token]

	score = 0

	if query_norm == account_name or query_norm == name:
		score += 120
	elif account_name.startswith(query_norm) or name.startswith(query_norm):
		score += 110
	elif query_norm in text:
		score += 90

	if tokens:
		matched_tokens = 0
		for token in tokens:
			if token in text:
				matched_tokens += 1
				score += 25
				if account_name.startswith(token) or name.startswith(token):
					score += 10
		if matched_tokens == len(tokens):
			score += 20

	# Prefer cleaner display names when scores are tied.
	score += max(0, 10 - min(len(account_name), 10))
	return score


@frappe.whitelist()
def search_expense_accounts(company: str, txt: str = "", page_length: int = 20):
	if not company:
		frappe.throw(_("Company is required"))

	accounts = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"root_type": "Expense",
			"is_group": 0,
			"disabled": 0,
		},
		fields=["name", "account_name", "account_number"],
		order_by="account_name asc",
		limit_page_length=0,
	)

	if not txt:
		return accounts[:page_length]

	scored_accounts = []
	for account in accounts:
		score = _score_expense_account(txt, account)
		if score > 0:
			account = dict(account)
			account["score"] = score
			scored_accounts.append(account)

	scored_accounts.sort(
		key=lambda row: (
			-row.get("score", 0),
			(row.get("account_name") or row.get("name") or "").lower(),
		)
	)
	return scored_accounts[:page_length]


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
	write_off_amount: float = 0,
	write_off_account: str | None = None,
	write_off_cost_center: str | None = None,
	reference_no: str | None = None,
	reference_date: str | None = None,
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
		party_account = party_details.get("party_account")
		party_account_details = _resolve_account_details(party_account, posting_date, cost_center)
		bank_account_details = _resolve_account_details(bank_account, posting_date, cost_center)

		payment_type = "Receive" if movement_type == "customer" else "Pay"
		pe = frappe.new_doc("Payment Entry")
		pe.company = company
		pe.payment_type = payment_type
		pe.party_type = party_type
		pe.party = party
		pe.party_balance = party_details.get("party_balance") or pe.party_balance
		pe.posting_date = posting_date
		pe.reference_no = (reference_no or "")[:140] or f"POS-{pos_profile}"
		pe.reference_date = reference_date or posting_date
		pe.remarks = (remarks or "").strip() or f"POS Next {movement_type} payment"
		pe.mode_of_payment = mode_of_payment
		pe.cost_center = cost_center
		pe.paid_amount = amount
		pe.received_amount = amount

		if payment_type == "Receive":
			pe.paid_from = party_account
			pe.paid_to = bank_account
			pe.paid_from_account_currency = party_account_details.get("currency")
			pe.paid_from_account_balance = party_account_details.get("balance")
			pe.paid_from_account_type = party_account_details.get("account_type")
			pe.paid_to_account_currency = bank_account_details.get("currency")
			pe.paid_to_account_balance = bank_account_details.get("balance")
			pe.paid_to_account_type = bank_account_details.get("account_type")
		else:
			pe.paid_from = bank_account
			pe.paid_to = party_account
			pe.paid_from_account_currency = bank_account_details.get("currency")
			pe.paid_from_account_balance = bank_account_details.get("balance")
			pe.paid_from_account_type = bank_account_details.get("account_type")
			pe.paid_to_account_currency = party_account_details.get("currency")
			pe.paid_to_account_balance = party_account_details.get("balance")
			pe.paid_to_account_type = party_account_details.get("account_type")

		write_off_amount = flt(write_off_amount)
		if write_off_amount > 0:
			write_off_details = _resolve_write_off_details(
				pos_profile,
				write_off_account=write_off_account,
				write_off_cost_center=write_off_cost_center,
			)
			if write_off_details.get("write_off_limit") > 0 and write_off_amount > write_off_details.get("write_off_limit"):
				frappe.throw(
					_("Write-off amount cannot exceed {0}").format(write_off_details.get("write_off_limit"))
				)
			if not write_off_details.get("write_off_account"):
				frappe.throw(_("Write-off account is required"))
			pe.write_off_difference_amount = write_off_amount
			pe.append(
				"deductions",
				{
					"account": write_off_details.get("write_off_account"),
					"cost_center": write_off_details.get("write_off_cost_center") or cost_center,
					"amount": write_off_amount,
				},
			)

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
		["company", "root_type", "account_type", "is_group", "disabled"],
		as_dict=True,
	)
	if not expense_account_doc or expense_account_doc.disabled:
		frappe.throw(_("Expense account {0} does not exist").format(expense_account))
	if expense_account_doc.company != company:
		frappe.throw(_("Expense account must belong to the selected company"))
	if expense_account_doc.is_group:
		frappe.throw(_("Expense account must be a ledger account"))
	if expense_account_doc.root_type != "Expense":
		frappe.throw(_("Selected account must belong to Expense"))

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
