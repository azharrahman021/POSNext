import json

import frappe
from frappe import _
from frappe.utils import cint


RULE_DOCTYPE = "POS Item Location Rule"


def _rule_doctype_available():
	return bool(frappe.db.exists("DocType", RULE_DOCTYPE))


def _parse_alternate_locations(value):
	if not value:
		return []

	if isinstance(value, str):
		value = json.loads(value)

	if not isinstance(value, list):
		frappe.throw(_("Alternate locations must be a list."))

	rows = []
	seen = set()
	for index, row in enumerate(value):
		if not isinstance(row, dict):
			continue

		warehouse = (row.get("warehouse") or "").strip()
		if not warehouse or warehouse in seen:
			continue

		seen.add(warehouse)
		rows.append(
			{
				"warehouse": warehouse,
				"display_label": (row.get("display_label") or "").strip(),
				"priority": cint(row.get("priority") or ((index + 1) * 100)),
			}
		)

	return rows


def _get_rule(item_code, company):
	if not item_code or not company:
		return None

	return frappe.db.get_value(
		RULE_DOCTYPE,
		{"item_code": item_code, "company": company},
		"name",
	)


def _get_rule_payload(rule_name):
	if not rule_name:
		return None

	rule = frappe.get_doc(RULE_DOCTYPE, rule_name)
	return {
		"name": rule.name,
		"enabled": cint(rule.enabled),
		"company": rule.company,
		"item_code": rule.item_code,
		"default_warehouse": rule.default_warehouse,
		"display_label": rule.display_label or "",
		"alternate_locations": [
			{
				"warehouse": row.warehouse,
				"display_label": row.display_label or "",
				"priority": cint(row.priority),
			}
			for row in (rule.alternate_locations or [])
		],
	}


def _get_leaf_warehouse_options(company):
	if not company:
		return []

	rows = frappe.get_all(
		"Warehouse",
		filters={"company": company, "is_group": 0},
		fields=["name", "warehouse_name"],
		order_by="warehouse_name asc, name asc",
	)
	return [
		{
			"value": row.name,
			"label": row.warehouse_name or row.name,
		}
		for row in rows
	]


def _get_status_payload(company=None):
	available = _rule_doctype_available()
	can_read = available and frappe.has_permission(RULE_DOCTYPE, "read")
	can_manage = available and (
		frappe.has_permission(RULE_DOCTYPE, "write") or frappe.has_permission(RULE_DOCTYPE, "create")
	)

	return {
		"integration_available": available,
		"can_read": can_read,
		"can_manage": can_manage,
		"company": company,
		"message": ""
		if available
		else _("Rack location management requires the POS Item Location Rule doctype."),
	}


def _ensure_rule_available():
	if not _rule_doctype_available():
		frappe.throw(_("Rack location management is not available on this site."))


def _ensure_read_permission():
	if not frappe.has_permission(RULE_DOCTYPE, "read"):
		frappe.throw(_("You do not have permission to read rack locations."))


def _ensure_manage_permission():
	if frappe.has_permission(RULE_DOCTYPE, "write") or frappe.has_permission(RULE_DOCTYPE, "create"):
		return

	frappe.throw(_("You do not have permission to manage rack locations."))


@frappe.whitelist()
def get_rack_location_facility_status(company=None):
	"""Return whether the POS rack-location editor can be used on this site."""
	return _get_status_payload(company=company)


@frappe.whitelist()
def get_item_rack_location_config(item_code, company):
	"""Return the existing rack-location rule and selectable shelf warehouses."""
	_ensure_rule_available()
	_ensure_read_permission()

	if not item_code or not company:
		frappe.throw(_("Item and company are required."))

	rule_name = _get_rule(item_code, company)
	return {
		**_get_status_payload(company=company),
		"item_code": item_code,
		"rule": _get_rule_payload(rule_name),
		"warehouse_options": _get_leaf_warehouse_options(company),
	}


@frappe.whitelist()
def upsert_item_rack_location_config(
	item_code,
	company,
	default_warehouse,
	display_label=None,
	alternate_locations=None,
	enabled=1,
):
	"""Create or update the rack-location rule used by POS item cards and picking."""
	_ensure_rule_available()
	_ensure_manage_permission()

	item_code = (item_code or "").strip()
	company = (company or "").strip()
	default_warehouse = (default_warehouse or "").strip()
	display_label = (display_label or "").strip()

	if not item_code or not company or not default_warehouse:
		frappe.throw(_("Item, company, and default warehouse are required."))

	alternate_rows = [
		row for row in _parse_alternate_locations(alternate_locations) if row["warehouse"] != default_warehouse
	]
	rule_name = _get_rule(item_code, company)

	if rule_name:
		rule = frappe.get_doc(RULE_DOCTYPE, rule_name)
	else:
		rule = frappe.get_doc(
			{
				"doctype": RULE_DOCTYPE,
				"item_code": item_code,
				"company": company,
			}
		)

	rule.enabled = cint(enabled)
	rule.default_warehouse = default_warehouse
	rule.display_label = display_label
	rule.set("alternate_locations", [])
	for row in alternate_rows:
		rule.append("alternate_locations", row)

	rule.save()

	return {
		"message": _("Rack location updated for item {0}.").format(item_code),
		"rule": _get_rule_payload(rule.name),
	}
