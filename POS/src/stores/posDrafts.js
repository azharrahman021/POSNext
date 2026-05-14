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

	function normalizeServerDraft(draft) {
		const invoice = draft?.doc || draft
		return {
			...invoice,
			draft_id: invoice.name,
			erp_invoice_name: invoice.name,
			server_backed: true,
			created_at: invoice.creation || invoice.posting_date || invoice.modified,
			updated_at: invoice.modified,
			customer: invoice.customer
				? {
					name: invoice.customer,
					customer_name: invoice.customer_name || invoice.customer,
				}
				: null,
			items: (invoice.items || []).map(normalizeDraftItem),
		}
	}

	async function getServerDrafts() {
		const posOpeningShift = shiftStore.currentShift?.name || null
		const posProfile = shiftStore.currentProfile?.name || null
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
		posProfile,
		appliedOffers = [],
		draftId = null,
	) {
		if (invoiceItems.length === 0) {
			showWarning(__("Cannot save an empty cart as draft"))
			return null
		}

		try {
			const draftData = {
				pos_profile: posProfile,
				customer: customer,
				items: invoiceItems,
				applied_offers: appliedOffers, // Save applied offers
			}

			let savedDraft
			if (draftId) {
				savedDraft = await updateDraft(draftId, draftData)
			} else {
				savedDraft = await saveDraft(draftData)
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
