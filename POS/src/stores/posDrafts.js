import { deleteDraft, saveDraft, getAllDrafts, updateDraft } from "@/utils/draftManager"
import { useToast } from "@/composables/useToast"
import { usePOSShiftStore } from "@/stores/posShift"
import { call } from "@/utils/apiWrapper"
import { isOffline } from "@/utils/offline"
import { defineStore } from "pinia"
import { ref } from "vue"

export const usePOSDraftsStore = defineStore("posDrafts", () => {
	// Use custom toast
	const { showSuccess, showError, showWarning } = useToast()
	const shiftStore = usePOSShiftStore()

	// State
	const draftsCount = ref(0)
	const drafts = ref([])

	function isLocalDraftId(draftId) {
		return String(draftId || "").startsWith("DRAFT-")
	}

	function normalizeDraftItem(item) {
		const quantity = Number.parseFloat(item.quantity ?? item.qty ?? 1) || 1
		const rate = Number.parseFloat(item.rate ?? item.net_rate ?? item.price_list_rate ?? 0) || 0

		return {
			...item,
			quantity,
			rate,
			price_list_rate: Number.parseFloat(item.price_list_rate ?? rate) || rate,
			amount: Number.parseFloat(item.amount ?? item.net_amount ?? quantity * rate) || 0,
			uom: item.uom || item.stock_uom,
			conversion_factor: item.conversion_factor || 1,
			discount_percentage: Number.parseFloat(item.discount_percentage || 0) || 0,
			discount_amount: Number.parseFloat(item.discount_amount || 0) || 0,
		}
	}

	function formatDraftItemForSubmission(item) {
		const quantity = Number.parseFloat(item.quantity ?? item.qty ?? 1) || 1
		const rate = Number.parseFloat(item.rate ?? item.net_rate ?? item.price_list_rate ?? 0) || 0
		const priceListRate = Number.parseFloat(item.price_list_rate ?? rate) || rate

		return {
			item_code: item.item_code,
			item_name: item.item_name,
			qty: quantity,
			rate: item.is_free_item ? 0 : rate,
			price_list_rate: item.is_free_item ? 0 : priceListRate,
			uom: item.uom || item.stock_uom,
			warehouse: item.warehouse,
			batch_no: item.batch_no,
			serial_no: item.serial_no,
			use_serial_batch_fields: item.batch_no || item.serial_no ? 1 : 0,
			conversion_factor: item.conversion_factor || 1,
			discount_percentage: Number.parseFloat(item.discount_percentage || 0) || 0,
			discount_amount: Number.parseFloat(item.discount_amount || 0) || 0,
			pricing_rules: Array.isArray(item.pricing_rules)
				? item.pricing_rules.join("\n")
				: item.pricing_rules || "",
			is_rate_manually_edited: item.is_rate_manually_edited || 0,
			original_rate: item.original_rate || null,
			is_free_item: item.is_free_item || 0,
		}
	}

	function formatDraftItemsForSubmission(items) {
		const out = []
		for (const item of items) {
			out.push(formatDraftItemForSubmission(item))
			const freeQty = Number.parseFloat(item.free_qty) || 0
			if (!item.is_free_item && freeQty > 0) {
				const uom = item.uom || item.stock_uom
				const hasDedicatedFree = items.some(
					(i) =>
						i.is_free_item &&
						i.item_code === item.item_code &&
						(i.uom || i.stock_uom) === uom,
				)
				if (!hasDedicatedFree) {
					out.push(
						formatDraftItemForSubmission({
							...item,
							quantity: freeQty,
							qty: freeQty,
							rate: 0,
							price_list_rate: 0,
							discount_percentage: 0,
							discount_amount: 0,
							is_rate_manually_edited: 0,
							original_rate: null,
							is_free_item: 1,
						}),
					)
				}
			}
		}
		return out
	}

	function getCustomerDisplayTitle(customer) {
		if (!customer) {
			return null
		}

		if (typeof customer === "object") {
			return customer.customer_name || customer.name || null
		}

		return customer
	}

	function resolveDraftDocumentTitle(invoiceTitle, customer) {
		const customTitle =
			typeof invoiceTitle === "string" ? invoiceTitle.trim() : ""

		return customTitle || getCustomerDisplayTitle(customer) || null
	}

	function extractCustomInvoiceTitle(title, customer) {
		const resolvedTitle = typeof title === "string" ? title.trim() : ""
		if (!resolvedTitle) {
			return ""
		}

		const customerTitle = getCustomerDisplayTitle(customer)
		if (customerTitle && resolvedTitle === customerTitle) {
			return ""
		}

		return resolvedTitle
	}

	function normalizeServerDraft(draft) {
		const invoice = draft?.doc || draft
		const customer = invoice.customer
			? {
				name: invoice.customer,
				customer_name: invoice.customer_name || invoice.customer,
			}
			: null

		return {
			...invoice,
			draft_id: invoice.name,
			erp_invoice_name: invoice.name,
			server_backed: true,
			created_at: invoice.creation || invoice.posting_date || invoice.modified,
			updated_at: invoice.modified,
			customer,
			invoice_title: extractCustomInvoiceTitle(invoice.title, customer),
			items: (invoice.items || []).map(normalizeDraftItem),
		}
	}

	async function getServerDrafts() {
		const posOpeningShift = shiftStore.currentShift?.name || null
		const posProfile = shiftStore.currentProfile?.name || shiftStore.profileName || null
		if (!posOpeningShift && !posProfile) {
			return []
		}

		const response = await call("pos_next.api.invoices.get_draft_invoices", {
			pos_opening_shift: posOpeningShift,
			pos_profile: posProfile,
		})
		const rows = response?.message || response || []
		return Array.isArray(rows) ? rows.map(normalizeServerDraft) : []
	}

	// Actions
	async function updateDraftsCount() {
		try {
			await loadDrafts()
		} catch (error) {
			console.error("Error getting drafts count:", error)
		}
	}

	async function loadDrafts() {
		try {
			if (isOffline()) {
				drafts.value = await getAllDrafts()
			} else {
				drafts.value = await getServerDrafts()
			}
			draftsCount.value = drafts.value.length
		} catch (error) {
			console.error("Error loading drafts:", error)
			drafts.value = await getAllDrafts()
			draftsCount.value = drafts.value.length
		}
	}

	async function saveDraftInvoice(
		invoiceItems,
		customer,
		invoiceTitle = "",
		posProfile,
		appliedOffers = [],
		draftId = null,
	) {
		if (invoiceItems.length === 0) {
			showWarning(__("Cannot save an empty cart as draft"))
			return null
		}

		try {
			let savedDraft
			if (isOffline()) {
				const draftData = {
					pos_profile: posProfile,
					customer: customer,
					invoice_title: invoiceTitle,
					items: invoiceItems,
					applied_offers: appliedOffers, // Save applied offers
				}
				if (draftId) {
					savedDraft = await updateDraft(draftId, draftData)
				} else {
					savedDraft = await saveDraft(draftData)
				}
			} else {
				const payload = {
					doctype: "Sales Invoice",
					pos_profile: posProfile,
					posa_pos_opening_shift: shiftStore.currentShift?.name || null,
					customer: customer?.name || customer,
					title: resolveDraftDocumentTitle(invoiceTitle, customer),
					items: formatDraftItemsForSubmission(invoiceItems),
					is_pos: 1,
					update_stock: 1,
				}

				if (draftId && !isLocalDraftId(draftId)) {
					payload.name = draftId
				}

				const response = await call("pos_next.api.invoices.update_invoice", {
					data: JSON.stringify(payload),
				})
				savedDraft = normalizeServerDraft(response?.message || response)
			}

			await loadDrafts() // Refresh drafts list and count

			showSuccess(__("Invoice saved as draft successfully"))

			return savedDraft
		} catch (error) {
			console.error("Error saving draft:", error)
			showError(__("Failed to save draft"))
			return null
		}
	}

	async function loadDraft(draft) {
		try {
			showSuccess(__("Draft invoice loaded successfully"))

			return {
				items: (draft.items || []).map(normalizeDraftItem),
				customer: draft.customer,
				invoice_title:
					draft.invoice_title ||
					extractCustomInvoiceTitle(draft.title, draft.customer),
				applied_offers: draft.applied_offers || [], // Restore applied offers
			}
		} catch (error) {
			console.error("Error loading draft:", error)
			showError(__("Failed to load draft"))
			throw error
		}
	}

	async function deleteDraftById(draftId) {
		try {
			if (!isOffline() && !isLocalDraftId(draftId)) {
				await call("pos_next.api.invoices.delete_invoice", { invoice: draftId })
			} else {
				await deleteDraft(draftId)
			}
			await loadDrafts() // Refresh drafts list and count
			showSuccess(__("Draft deleted successfully"))
		} catch (error) {
			console.error("Error deleting draft:", error)
			showError(__("Failed to delete draft"))
		}
	}

	return {
		// State
		draftsCount,
		drafts,

		// Actions
		updateDraftsCount,
		loadDrafts,
		saveDraftInvoice,
		loadDraft,
		deleteDraft: deleteDraftById,
	}
})
