"""
Installation and Migration hooks for POS Next

This module relies on Frappe's fixture system for:
- Custom fields (custom_field.json)
- Roles (role.json)
- Custom DocPerm (custom_docperm.json)

This module also creates app-managed print formats during install/migrate so
the live site gets the same receipt templates as the repository source.
"""
import json
import os

import frappe
import logging

# Configure logger
logger = logging.getLogger(__name__)


def after_install():
	"""Hook that runs after app installation"""
	try:
		log_message("POS Next: Running post-install setup", level="info")

		# Setup default print format for POS Profiles
		setup_default_print_format()
		setup_payment_entry_print_format()

		# Clear cache to ensure changes take effect
		frappe.clear_cache()
		frappe.db.commit()

		log_message("POS Next: Installation completed successfully", level="success")
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			title="POS Next Installation Error",
			message=frappe.get_traceback()
		)
		log_message(f"POS Next: Installation error - {str(e)}", level="error")
		raise


def after_migrate():
	"""Hook that runs after bench migrate"""
	try:
		# Setup default print format
		setup_default_print_format(quiet=True)
		setup_payment_entry_print_format(quiet=True)

		# Clear cache
		frappe.clear_cache()
		frappe.db.commit()

		log_message("POS Next: Migration completed successfully", level="success")
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			title="POS Next Migration Error",
			message=frappe.get_traceback()
		)
		log_message(f"POS Next: Migration error - {str(e)}", level="error")
		raise


def setup_default_print_format(quiet=False):
	"""
	Set POS Next Receipt as default print format for POS Profiles if not already set.

	Args:
		quiet (bool): If True, suppress detailed logs
	"""
	try:
		# Check if the print format exists
		if not frappe.db.exists("Print Format", "POS Next Receipt"):
			if not quiet:
				log_message("POS Next Receipt print format not found, skipping default setup", level="warning")
			return

		# Get all POS Profiles without a print format
		pos_profiles = frappe.get_all(
			"POS Profile",
			filters={"print_format": ["in", ["", None]]},
			fields=["name"]
		)

		if pos_profiles:
			updated_count = 0
			for profile in pos_profiles:
				try:
					frappe.db.set_value(
						"POS Profile",
						profile.name,
						"print_format",
						"POS Next Receipt",
						update_modified=False
					)
					if not quiet:
						log_message(f"Set default print format for: {profile.name}", level="info", indent=1)
					updated_count += 1
				except Exception as e:
					log_message(f"Error updating POS Profile {profile.name}: {str(e)}", level="error", indent=1)

			if updated_count > 0 and not quiet:
				log_message(f"Updated {updated_count} POS Profile(s) with default print format", level="success")

	except Exception as e:
		log_message(f"Error setting up default print format: {str(e)}", level="error")
		frappe.log_error(
			title="Default Print Format Setup Error",
			message=frappe.get_traceback()
		)


def setup_payment_entry_print_format(quiet=False):
	"""Create the POS Next Payment Receipt print format if it does not exist."""
	format_name = "POS Next Payment Receipt"
	if frappe.db.exists("Print Format", format_name):
		return

	template_path = os.path.join(
		os.path.dirname(__file__),
		"pos_next",
		"print_format",
		"payment_entry_receipt",
		"payment_entry_receipt.html",
	)

	try:
		with open(template_path, "r", encoding="utf-8") as handle:
			html = handle.read()

		doc = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": format_name,
				"module": "POS Next",
				"doc_type": "Payment Entry",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"disabled": 0,
				"standard": "No",
				"default_print_language": "en",
				"font_size": 12,
				"raw_printing": 0,
				"show_section_headings": 0,
				"html": html,
			}
		)
		doc.insert(ignore_permissions=True)
		if not quiet:
			log_message(f"Created print format: {format_name}", level="success")
	except Exception as e:
		log_message(f"Error setting up payment entry print format: {str(e)}", level="error")
		frappe.log_error(
			title="Payment Entry Print Format Setup Error",
			message=frappe.get_traceback()
		)


def log_message(message, level="info", indent=0):
	"""
	Standardized logging function with consistent formatting.

	Args:
		message (str): The message to log
		level (str): Log level - info, success, warning, error
		indent (int): Indentation level (0, 1, 2, etc.)
	"""
	indent_str = "  " * indent

	prefixes = {
		"info": "[INFO]",
		"success": "[SUCCESS]",
		"warning": "[WARNING]",
		"error": "[ERROR]",
	}

	prefix = prefixes.get(level, "[INFO]")
	formatted_message = f"{indent_str}{prefix} {message}"

	# Print to console
	print(formatted_message)

	# Also log to frappe logger
	if level == "error":
		logger.error(message)
	elif level == "warning":
		logger.warning(message)
	else:
		logger.info(message)
