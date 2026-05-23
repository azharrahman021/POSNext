import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt


class POSItemRequest(Document):
	def autoname(self):
		series = (getattr(self, "naming_series", None) or "PIR-.YYYY.-").strip()
		if series.endswith(".#####"):
			series = series[: -len(".#####")].rstrip(".")

		self.name = make_autoname(f"{series}.#####", "", self)

	def validate(self):
		self.requested_item_name = (self.requested_item_name or "").strip()
		if not self.requested_item_name:
			frappe.throw(_("Requested item name is required"))

		self.availability_type = (self.availability_type or "unknown").strip()
		if self.availability_type not in {"out_of_stock", "not_in_inventory", "unknown"}:
			self.availability_type = "unknown"

		self.qty = flt(self.qty or 1)
		if self.qty <= 0:
			self.qty = 1

		if not self.status:
			self.status = "new"
