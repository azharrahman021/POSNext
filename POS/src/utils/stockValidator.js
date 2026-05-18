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
 * Check if the requested quantity exceeds available stock.
 *
 * @param {Object}  item       - Item with actual_qty / stock_qty
 * @param {number}  requestedQty - Total quantity to validate against
 * @param {string}  [warehouse]  - Warehouse name (for error message)
 * @returns {{ available: boolean, actualQty: number, error: string|null }}
 */
export function checkStockAvailability(item, requestedQty, warehouse) {
	const actualQty = item.original_stock ?? item.actual_qty ?? item.stock_qty ?? 0
	const conversionFactor = Number.parseFloat(item.conversion_factor) || 1
	const requestedStockQty = Number.parseFloat(requestedQty || 0) * conversionFactor
	const wh = warehouse || item.warehouse || ''

	if (actualQty >= requestedStockQty) {
		return { available: true, actualQty, error: null }
	}

	return {
		available: false,
		actualQty,
		requestedStockQty,
		error: formatStockError(item.item_name, requestedQty, actualQty, wh, item),
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
 * @returns {string} - Formatted error message
 */
export function formatStockError(itemName, requested, available, warehouse, item = {}) {
	const requestedQty = Number.parseFloat(requested || 0)
	const availableQty = Number.parseFloat(available || 0)
	const conversionFactor = Number.parseFloat(item.conversion_factor) || 1
	const requestedStockQty = requestedQty * conversionFactor
	const requestedUom = item.uom || item.stock_uom || (requestedQty === 1 ? "unit" : "units")
	const stockUom = item.stock_uom || requestedUom

	if (available <= 0) {
		return `"${itemName}" is out of stock in warehouse "${warehouse}".`
	}

	const requestedLabel = requestedUom === stockUom
		? `${requestedQty} ${requestedUom}`
		: `${requestedQty} ${requestedUom} (${requestedStockQty} ${stockUom})`
	return `Not enough stock for "${itemName}".\n\nYou requested ${requestedLabel}, but only ${availableQty} ${stockUom} available in "${warehouse}".`
}
