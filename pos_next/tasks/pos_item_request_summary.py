# Copyright (c) 2026, POS Next and contributors
# For license information, please see license.txt

"""Daily POS item request Telegram summary."""

from __future__ import unicode_literals

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import formatdate, nowdate


def _get_recipients():
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT daily_item_request_telegram_user AS telegram_user
		FROM `tabPOS Settings`
		WHERE enabled = 1
			AND IFNULL(daily_item_request_telegram_user, '') != ''
		""",
		as_dict=True,
	)
	return [row.telegram_user for row in rows if row.telegram_user]


def _get_requests(before_ts):
	return frappe.get_all(
		"POS Item Request",
		fields=[
			"name",
			"creation",
			"requested_item_name",
			"availability_type",
			"matched_item",
			"customer",
			"mobile_no",
			"qty",
			"uom",
			"staff_user",
			"company",
			"pos_profile",
			"warehouse",
			"status",
			"notes",
		],
		filters=[
			["creation", "<", before_ts],
			["status", "in", ("new", "ordered")],
		],
		order_by="creation asc",
	)


def _format_summary(requests, request_date):
	by_item = OrderedDict()
	for req in requests:
		key = req.get("requested_item_name") or _("Unknown item")
		by_item.setdefault(key, None)

	lines = []
	lines.append(_("Daily POS Item Requests"))
	lines.append(_("Date: {0}").format(formatdate(request_date)))
	lines.append("")
	lines.append(_("Item names"))
	for item_name in by_item.keys():
		lines.append("- {0}".format(item_name))

	return "\n".join(lines)


def _chunk_message(message, limit=3500):
	lines = message.splitlines()
	chunks = []
	current = []
	current_len = 0

	for line in lines:
		line_len = len(line) + 1
		if current and current_len + line_len > limit:
			chunks.append("\n".join(current))
			current = [line]
			current_len = len(line)
		else:
			current.append(line)
			current_len += line_len

	if current:
		chunks.append("\n".join(current))

	return chunks


def _send_to_recipients(recipients, message):
	try:
		from erpnext_telegram_integration.erpnext_telegram_integration.doctype.telegram_settings.telegram_settings import (
			send_to_telegram,
		)
	except Exception:
		frappe.log_error(
			title="POS Item Request Telegram Summary Error",
			message="Telegram integration app is not installed or could not be imported.",
		)
		return

	for recipient in recipients:
		for chunk in _chunk_message(message):
			send_to_telegram(telegram_user=recipient, message=chunk)


def send_daily_pos_item_request_summary():
	"""Send all POS item requests created before today to configured Telegram groups."""
	try:
		recipients = _get_recipients()
		if not recipients:
			frappe.logger().info("No Telegram recipients configured for POS item request summary")
			return

		request_date = nowdate()
		requests = _get_requests(f"{request_date} 00:00:00")

		if not requests:
			message = _(
				"No POS item requests were created before {0}."
			).format(formatdate(request_date))
		else:
			message = _format_summary(requests, request_date)

		_send_to_recipients(recipients, message)
		frappe.logger().info(
			"Sent POS item request summary to {0} Telegram recipient(s)".format(len(recipients))
		)
	except Exception:
		frappe.log_error(
			title="POS Item Request Telegram Summary Error",
			message=frappe.get_traceback(),
		)
