"""Compatibility patches for optional invoice_manager hooks.

Some deployed sites include invoice_manager versions whose Sales Invoice
submit hook can fail POS returns by referencing a missing calculate_profit
helper, then fail again while JSON-logging date values. Keep this patch small
and defensive so POS Next does not depend on that app being installed.
"""

from __future__ import annotations

import json

import frappe
from frappe.utils import flt


def _fallback_calculate_profit(doc):
	"""Best-effort gross profit used only when invoice_manager lacks the helper."""
	total = 0
	for item in doc.get("items", []):
		income = flt(item.get("base_net_amount") or item.get("net_amount") or item.get("amount"))
		cost = flt(item.get("valuation_rate")) * abs(flt(item.get("stock_qty") or item.get("qty")))
		total += income - cost
	return total


def _safe_log_calculation_error(original):
	def wrapper(doc, error_message, context):
		try:
			return original(doc, error_message, context)
		except TypeError as exc:
			if "JSON serializable" not in str(exc):
				raise
			error_data = {
				"invoice": getattr(doc, "name", None),
				"posting_date": getattr(doc, "posting_date", None),
				"customer": getattr(doc, "customer", None),
				"error": error_message,
				"context": context,
			}
			frappe.log_error(
				title=f"{context} Error",
				message=json.dumps(error_data, indent=2, default=str),
			)

	return wrapper


def patch_invoice_manager_notification():
	try:
		from invoice_manager import notification
	except Exception:
		return

	if not hasattr(notification, "calculate_profit"):
		notification.calculate_profit = _fallback_calculate_profit

	log_error = getattr(notification, "log_calculation_error", None)
	if log_error and not getattr(log_error, "_pos_next_safe_json", False):
		wrapped = _safe_log_calculation_error(log_error)
		wrapped._pos_next_safe_json = True
		notification.log_calculation_error = wrapped
