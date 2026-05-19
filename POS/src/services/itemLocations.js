import { call } from "@/utils/apiWrapper"

const METHOD_PREFIX = "invoice_manager.api.item_locations"

export async function getItemLocationsBulk(itemCodes, company) {
	if (!company || !Array.isArray(itemCodes) || itemCodes.length === 0) {
		return {}
	}

	const response = await call(`${METHOD_PREFIX}.get_item_locations_bulk`, {
		item_codes: JSON.stringify(itemCodes),
		company,
	})
	return response?.message || response || {}
}

export async function resolvePosItemWarehouse(itemCode, company, qty = 1) {
	if (!itemCode || !company) {
		return null
	}

	const response = await call(`${METHOD_PREFIX}.resolve_pos_item_warehouse`, {
		item_code: itemCode,
		company,
		qty,
	})
	return response?.message || response || null
}
