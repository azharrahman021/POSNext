/**
 * Stock Validation Utility
 * Single source of truth for stock availability checks.
 */

import { call } from "frappe-ui"

/**
 * Determine whether an item requires stock validation.
 * Centralises the skip-logic so every call site uses the same rules.
 *
 * @param {Object} item - Item object (from search API or cart)
 * @returns {boolean} true when stock should be enforced for this item
 */
export function shouldValidateItemStock(item) {
	if (!item) return false

	// Non-stock items are never validated
	if (item.is_stock_item === 0 || item.is_stock_item === false) return false

	// Item-level allow_negative_stock bypasses validation
	if (item.allow_negative_stock === 1 || item.allow_negative_stock === true) return false

	// Batch / serial items have their own dialog-level validation
	if (item.has_serial_no || item.has_batch_no) return false

	// Must be a stock item or bundle (or have stock data)
	const hasStockData = item.actual_qty !== undefined || item.stock_qty !== undefined
	return !!(item.is_stock_item || item.is_bundle || hasStockData)
}

/**
 * Convert a sales quantity to the item's stock UOM quantity.
 *
 * @param {number} quantity - Quantity in the selected sales UOM
 * @param {Object} item - Item with conversion_factor from selected UOM to stock UOM
 * @returns {number} Quantity expressed in stock UOM
 */
export function getStockQuantity(quantity, item = {}) {
	const qty = Number.parseFloat(quantity) || 0
	const conversionFactor = Number.parseFloat(item.conversion_factor) || 1
	return qty * conversionFactor
}

/**
 * Check if the requested quantity exceeds available stock.
 *
 * @param {Object}  item       - Item with actual_qty / stock_qty
 * @param {number}  requestedQty - Total quantity to validate against
 * @param {string}  [warehouse]  - Warehouse name (for error message)
 * @param {Object}  [options]    - Optional comparison flags
 * @param {boolean} [options.quantityInStockUom=false] - requestedQty is already in stock UOM
 * @param {number}  [options.displayQty=requestedQty] - Original user-entered quantity for message
 * @returns {{ available: boolean, actualQty: number, error: string|null }}
 */
export function checkStockAvailability(item, requestedQty, warehouse, options = {}) {
	const actualQty = Number.parseFloat(item.actual_qty ?? item.stock_qty ?? 0) || 0
	const requestedStockQty = options.quantityInStockUom
		? Number.parseFloat(requestedQty) || 0
		: getStockQuantity(requestedQty, item)
	const displayQty = options.displayQty ?? requestedQty
	const wh = warehouse || item.warehouse || ''

	if (actualQty >= requestedStockQty) {
		return { available: true, actualQty, error: null }
	}

	return {
		available: false,
		actualQty,
		error: formatStockError(
			item.item_name,
			displayQty,
			actualQty,
			wh,
			requestedStockQty,
			item.stock_uom,
		),
	}
}

/**
 * Get item stock from Frappe API
 * @param {string} itemCode - Item code
 * @param {string} warehouse - Warehouse
 * @returns {Promise<number>} - Available quantity
 */
export async function getItemStock(itemCode, warehouse) {
	try {
		const result = await call("frappe.client.get_value", {
			doctype: "Bin",
			filters: {
				item_code: itemCode,
				warehouse: warehouse,
			},
			fieldname: "actual_qty",
		})

		return Number.parseFloat(result?.actual_qty || 0)
	} catch (error) {
		console.warn("Failed to fetch stock:", error)
		return 0
	}
}

/**
 * Format stock error message for user
 * @param {string} itemName - Item name
 * @param {number} requested - Requested quantity
 * @param {number} available - Available quantity
 * @param {string} warehouse - Warehouse name
 * @param {number|null} requestedStockQty - Requested quantity converted to stock UOM
 * @param {string|null} stockUom - Item stock UOM
 * @returns {string} - Formatted error message
 */
export function formatStockError(
	itemName,
	requested,
	available,
	warehouse,
	requestedStockQty = null,
	stockUom = null,
) {
	if (available <= 0) {
		return `"${itemName}" is out of stock in warehouse "${warehouse}".`
	}

	const unit = requested === 1 ? "unit" : "units"
	const availableUnit = available === 1 ? "unit" : "units"
	const convertedMessage = requestedStockQty !== null && stockUom
		? ` (${requestedStockQty} ${stockUom})`
		: ""
	return `Not enough stock for "${itemName}".\n\nYou requested ${requested} ${unit}${convertedMessage}, but only ${available} ${availableUnit} available in "${warehouse}".`
}
