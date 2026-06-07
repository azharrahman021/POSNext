# Copyright (c) 2026, BrainWise and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate, nowtime

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	make_inter_company_purchase_invoice,
)
from pos_next.api.cash_movements import _validate_pos_profile


STOCK_CORRECTOR_ROLE = "POSNext Stock Corrector"

SOURCE_COMPANY = "Fix & Build Margin Free Store -Palakode"
TARGET_COMPANY = "Fix & Build Margin Free Store -Karanthad"
SOURCE_WAREHOUSE = "Stores - THS"
TARGET_WAREHOUSE = "Store2026 - FB-KD"
TARGET_CUSTOMER = "Fix & Build Margin Free Store -Karanthad"
SOURCE_SUPPLIER = "Fix & Build Margin Free Store -Palakode"


def _require_stock_corrector():
	if STOCK_CORRECTOR_ROLE not in frappe.get_roles():
		frappe.throw(_("You are not allowed to create POS stock corrections"), frappe.PermissionError)


def _validate_stock_correction_access(pos_profile: str):
	_require_stock_corrector()

	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	company = frappe.db.get_value("POS Profile", pos_profile, "company")
	_validate_pos_profile(pos_profile, company)

	if company != TARGET_COMPANY:
		frappe.throw(_("Stock correction is only available for {0}").format(TARGET_COMPANY))


def _normalize_search_text(value: str) -> str:
	if not value:
		return ""
	return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _score_item(query: str, item: dict) -> int:
	query_norm = _normalize_search_text(query)
	if not query_norm:
		return 0

	item_code = _normalize_search_text(item.get("item_code") or "")
	item_name = _normalize_search_text(item.get("item_name") or "")
	item_group = _normalize_search_text(item.get("item_group") or "")
	description = _normalize_search_text(item.get("description") or "")
	text = " ".join(part for part in [item_code, item_name, item_group, description] if part)
	tokens = [token for token in query_norm.split(" ") if token]

	score = 0
	if query_norm == item_code or query_norm == item_name:
		score += 140
	elif item_code.startswith(query_norm) or item_name.startswith(query_norm):
		score += 120
	elif query_norm in text:
		score += 90

	if tokens:
		matched_tokens = 0
		for token in tokens:
			if token in text:
				matched_tokens += 1
				score += 25
				if item_code.startswith(token) or item_name.startswith(token):
					score += 10
		if matched_tokens == len(tokens):
			score += 30

	return score


def _get_bin_qty(item_code: str, warehouse: str) -> float:
	qty = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty")
	return flt(qty)


def _get_item_uoms(item_code: str, stock_uom: str) -> list[dict]:
	uoms = [{"uom": stock_uom, "conversion_factor": 1}]
	seen = {stock_uom}
	for row in frappe.get_all(
		"UOM Conversion Detail",
		filters={"parent": item_code},
		fields=["uom", "conversion_factor"],
		order_by="idx asc",
	):
		if not row.uom or row.uom in seen:
			continue
		uoms.append({"uom": row.uom, "conversion_factor": flt(row.conversion_factor) or 1})
		seen.add(row.uom)
	return uoms


def _decorate_item_stock(item: dict) -> dict:
	item = dict(item)
	item["target_warehouse"] = TARGET_WAREHOUSE
	item["target_qty"] = _get_bin_qty(item["item_code"], TARGET_WAREHOUSE)
	item["source_warehouse"] = SOURCE_WAREHOUSE
	item["source_qty"] = _get_bin_qty(item["item_code"], SOURCE_WAREHOUSE)
	item["item_uoms"] = _get_item_uoms(item["item_code"], item.get("stock_uom"))
	return item


@frappe.whitelist()
def search_stock_correction_items(pos_profile: str, txt: str = "", page_length: int = 20):
	_validate_stock_correction_access(pos_profile)

	page_length = min(max(cint(page_length) or 20, 1), 50)
	query = (txt or "").strip()

	filters = {
		"disabled": 0,
		"is_stock_item": 1,
		"has_serial_no": 0,
		"has_batch_no": 0,
	}
	or_filters = None
	if query:
		like_query = "%{0}%".format(query)
		or_filters = [
			["item_code", "like", like_query],
			["item_name", "like", like_query],
			["item_group", "like", like_query],
			["description", "like", like_query],
		]

	items = frappe.get_all(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["item_code", "item_name", "item_group", "description", "stock_uom"],
		order_by="modified desc",
		limit_page_length=200 if query else page_length,
	)

	if query:
		scored_items = []
		for item in items:
			score = _score_item(query, item)
			if score > 0:
				row = dict(item)
				row["score"] = score
				scored_items.append(row)
		scored_items.sort(
			key=lambda row: (
				-row.get("score", 0),
				(row.get("item_name") or row.get("item_code") or "").lower(),
			)
		)
		items = scored_items[:page_length]

	return [_decorate_item_stock(item) for item in items[:page_length]]


def _get_internal_party(doctype: str, company: str, fallback_name: str) -> str:
	name = frappe.db.get_value(doctype, {"represents_company": company}, "name")
	if name:
		return name
	if frappe.db.exists(doctype, fallback_name):
		return fallback_name
	frappe.throw(_("{0} for company {1} was not found").format(doctype, company))


def _is_intercompany_price_list(price_list: str | None) -> bool:
	if not price_list:
		return False

	return bool(
		frappe.db.exists(
			"Price List",
			{
				"name": price_list,
				"enabled": 1,
				"selling": 1,
				"buying": 1,
			},
		)
	)


def _get_intercompany_price_list() -> str:
	pos_price_list = frappe.db.get_value(
		"POS Profile",
		{"company": SOURCE_COMPANY, "disabled": 0},
		"selling_price_list",
		order_by="modified desc",
	)
	if _is_intercompany_price_list(pos_price_list):
		return pos_price_list

	if _is_intercompany_price_list("Standard Buying"):
		return "Standard Buying"

	price_list = frappe.db.get_value(
		"Price List",
		{"enabled": 1, "selling": 1, "buying": 1},
		"name",
		order_by="name asc",
	)
	if price_list:
		return price_list

	frappe.throw(_("No enabled Price List has both buying and selling checked"))


def _get_item_rate(item_code: str, price_list: str, uom: str, stock_uom: str, conversion_factor: float) -> float:
	price = frappe.db.get_value(
		"Item Price",
		{
			"item_code": item_code,
			"price_list": price_list,
			"selling": 1,
			"uom": uom,
		},
		"price_list_rate",
		order_by="valid_from desc, modified desc",
	)
	if price is not None:
		return flt(price)

	if uom != stock_uom:
		stock_uom_price = frappe.db.get_value(
			"Item Price",
			{
				"item_code": item_code,
				"price_list": price_list,
				"selling": 1,
				"uom": stock_uom,
			},
			"price_list_rate",
			order_by="valid_from desc, modified desc",
		)
		if stock_uom_price is not None:
			return flt(stock_uom_price) * conversion_factor

	valuation_rate = frappe.db.get_value(
		"Bin",
		{"item_code": item_code, "warehouse": SOURCE_WAREHOUSE},
		"valuation_rate",
	)
	if valuation_rate is not None:
		return flt(valuation_rate) * conversion_factor

	return flt(frappe.db.get_value("Item", item_code, "valuation_rate")) * conversion_factor


def _validate_item(item_code: str) -> dict:
	item = frappe.db.get_value(
		"Item",
		item_code,
		["item_code", "item_name", "stock_uom", "is_stock_item", "disabled", "has_serial_no", "has_batch_no"],
		as_dict=True,
	)
	if not item:
		frappe.throw(_("Item {0} was not found").format(item_code))
	if item.disabled:
		frappe.throw(_("Item {0} is disabled").format(item_code))
	if not item.is_stock_item:
		frappe.throw(_("Item {0} is not a stock item").format(item_code))
	if item.has_serial_no or item.has_batch_no:
		frappe.throw(_("Serialized or batched items cannot be corrected from POS"))
	return item


def _get_conversion_factor(item_code: str, stock_uom: str, uom: str | None) -> float:
	uom = uom or stock_uom
	if uom == stock_uom:
		return 1

	conversion_factor = frappe.db.get_value(
		"UOM Conversion Detail",
		{"parent": item_code, "uom": uom},
		"conversion_factor",
	)
	if not conversion_factor:
		frappe.throw(_("UOM {0} is not configured for item {1}").format(uom, item_code))

	return flt(conversion_factor)


def _clear_purchase_invoice_party_links(purchase_invoice):
	for fieldname in (
		"supplier_address",
		"address_display",
		"contact_person",
		"contact_display",
		"contact_mobile",
		"contact_email",
		"dispatch_address",
		"dispatch_address_display",
		"shipping_address",
		"shipping_address_display",
		"billing_address",
		"billing_address_display",
	):
		if purchase_invoice.meta.has_field(fieldname):
			purchase_invoice.set(fieldname, None)


def _clear_transaction_taxes(doc):
	if doc.meta.has_field("taxes_and_charges"):
		doc.taxes_and_charges = None
	doc.set("taxes", [])


@frappe.whitelist()
def create_stock_increase_transfer(
	pos_profile: str,
	item_code: str,
	qty,
	uom: str | None = None,
	remarks: str | None = None,
):
	_validate_stock_correction_access(pos_profile)

	qty = flt(qty)
	if qty <= 0:
		frappe.throw(_("Increase quantity must be greater than zero"))

	item = _validate_item(item_code)
	uom = uom or item.stock_uom
	conversion_factor = _get_conversion_factor(item_code, item.stock_uom, uom)
	stock_qty = qty * conversion_factor
	target_customer = _get_internal_party("Customer", TARGET_COMPANY, TARGET_CUSTOMER)
	source_supplier = _get_internal_party("Supplier", SOURCE_COMPANY, SOURCE_SUPPLIER)
	price_list = _get_intercompany_price_list()
	rate = _get_item_rate(item_code, price_list, uom, item.stock_uom, conversion_factor)
	posting_date = nowdate()
	posting_time = nowtime()

	if _get_bin_qty(item_code, SOURCE_WAREHOUSE) < stock_qty:
		frappe.throw(
			_("Only {0} {1} is available in {2}").format(
				_get_bin_qty(item_code, SOURCE_WAREHOUSE),
				item.stock_uom,
				SOURCE_WAREHOUSE,
			)
		)

	note = remarks or _("POSNext stock increase for {0}").format(TARGET_COMPANY)

	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.company = SOURCE_COMPANY
	sales_invoice.customer = target_customer
	sales_invoice.is_internal_customer = 1
	sales_invoice.update_stock = 1
	sales_invoice.set_posting_time = 1
	sales_invoice.posting_date = posting_date
	sales_invoice.posting_time = posting_time
	sales_invoice.due_date = posting_date
	sales_invoice.selling_price_list = price_list
	sales_invoice.remarks = note
	sales_invoice.append(
		"items",
		{
			"item_code": item_code,
			"item_name": item.item_name,
			"qty": qty,
			"uom": uom,
			"stock_uom": item.stock_uom,
			"conversion_factor": conversion_factor,
			"warehouse": SOURCE_WAREHOUSE,
			"target_warehouse": TARGET_WAREHOUSE,
			"rate": rate,
			"allow_zero_valuation_rate": 1,
		},
	)
	sales_invoice.set_missing_values()
	_clear_transaction_taxes(sales_invoice)
	sales_invoice.calculate_taxes_and_totals()
	sales_invoice.flags.ignore_permissions = True
	sales_invoice.insert(ignore_permissions=True)
	sales_invoice.submit()

	purchase_invoice = None
	try:
		purchase_invoice = make_inter_company_purchase_invoice(sales_invoice.name)
		purchase_invoice.company = TARGET_COMPANY
		purchase_invoice.supplier = source_supplier
		purchase_invoice.is_internal_supplier = 1
		purchase_invoice.update_stock = 1
		purchase_invoice.set_posting_time = 1
		purchase_invoice.posting_date = posting_date
		purchase_invoice.posting_time = posting_time
		purchase_invoice.due_date = posting_date
		purchase_invoice.remarks = note
		_clear_purchase_invoice_party_links(purchase_invoice)
		_clear_transaction_taxes(purchase_invoice)
		for row in purchase_invoice.items:
			row.warehouse = TARGET_WAREHOUSE
		purchase_invoice.calculate_taxes_and_totals()
		purchase_invoice.flags.ignore_permissions = True
		purchase_invoice.insert(ignore_permissions=True)
		purchase_invoice.submit()
	except Exception:
		if purchase_invoice and purchase_invoice.name and purchase_invoice.docstatus == 1:
			purchase_invoice.flags.ignore_permissions = True
			purchase_invoice.cancel()
		if sales_invoice.docstatus == 1:
			sales_invoice.flags.ignore_permissions = True
			sales_invoice.cancel()
		raise

	return {
		"success": True,
		"item_code": item_code,
		"item_name": item.item_name,
		"qty": qty,
		"uom": uom,
		"stock_qty": stock_qty,
		"stock_uom": item.stock_uom,
		"target_qty": _get_bin_qty(item_code, TARGET_WAREHOUSE),
		"source_qty": _get_bin_qty(item_code, SOURCE_WAREHOUSE),
		"sales_invoice": sales_invoice.name,
		"purchase_invoice": purchase_invoice.name,
	}
