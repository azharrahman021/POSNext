<template>
	<Dialog
		v-model="show"
		:options="{ title: __('Payments & Expenses'), size: 'xl' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<CashMovementTabs
					:tabs="tabs"
					:movement-type="movementType"
					@select="movementType = $event"
				/>
				<div class="grid gap-4 lg:grid-cols-2">
					<div class="space-y-4">
						<div class="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-4">
							<div>
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ __('Posting Date') }}
								</label>
								<input
									v-model="postingDate"
									type="date"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								/>
							</div>

							<div>
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ __('Mode of Payment') }}
								</label>
								<select
									v-model="modeOfPayment"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								>
									<option v-for="method in paymentMethods" :key="method.mode_of_payment" :value="method.mode_of_payment">
										{{ method.mode_of_payment }}
									</option>
								</select>
							</div>

							<div>
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ __('Amount') }}
								</label>
								<input
									v-model.number="amount"
									type="number"
									min="0"
									step="0.01"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								/>
							</div>

							<CashMovementLookupCard
								:movement-type="movementType"
								:party-search="partySearch"
								:party-results="partyResults"
								:party-dropdown-open="partyDropdownOpen"
								:selected-party="selectedParty"
								:party-balance-loading="partyBalanceLoading"
								:party-balance-summary="partyBalanceSummary"
								:expense-search="expenseSearch"
								:expense-results="expenseResults"
								:expense-dropdown-open="expenseDropdownOpen"
								:selected-expense-account="selectedExpenseAccount"
								:expense-loading="expenseLoading"
								:expense-placeholder="defaults.default_expense_account || __('Search expense account...')"
								:format-currency="formatCurrency"
								@update:party-search="partySearch = $event"
								@focus-party="partyDropdownOpen = true"
								@blur-party="handlePartyBlur"
								@select-party="selectParty"
								@update:expense-search="expenseSearch = $event"
								@focus-expense="expenseDropdownOpen = true"
								@blur-expense="handleExpenseBlur"
								@select-expense="selectExpenseAccount"
								@search-expense="searchExpenseAccounts"
							/>

							<CashMovementWriteOffCard
								:movement-type="movementType"
								:apply-write-off="applyWriteOff"
								:selected-party="selectedParty"
								:write-off-amount="writeOffAmount"
								:format-currency="formatCurrency"
								@toggle="toggleWriteOff"
							/>
						</div>
					</div>

					<div class="space-y-4">
						<CashMovementDetailsCard
							:reference-no="referenceNo"
							:reference-date="referenceDate"
							:remarks="remarks"
							:movement-label="movementLabel"
							:amount="amount"
							:mode-of-payment="modeOfPayment"
							:error-message="errorMessage"
							:format-currency="formatCurrency"
							@update:reference-no="referenceNo = $event"
							@update:reference-date="referenceDate = $event"
							@update:remarks="remarks = $event"
						/>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex w-full gap-2">
				<Button variant="subtle" class="flex-1" @click="show = false">
					{{ __('Close') }}
				</Button>
				<Button
					variant="solid"
					theme="blue"
					class="flex-1"
					:loading="submitting"
					:disabled="!canSubmit"
					@click="submitMovement"
				>
					{{ submitLabel }}
				</Button>
			</div>
		</template>
	</Dialog>

</template>

<script setup>
import { Button, call } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useToast } from "@/composables/useToast"
import { parseError } from "@/utils/errorHandler"
import { formatCurrency as formatCurrencyUtil } from "@/utils/currency"
import CashMovementTabs from "@/components/cash-movement/CashMovementTabs.vue"
import CashMovementLookupCard from "@/components/cash-movement/CashMovementLookupCard.vue"
import CashMovementWriteOffCard from "@/components/cash-movement/CashMovementWriteOffCard.vue"
import CashMovementDetailsCard from "@/components/cash-movement/CashMovementDetailsCard.vue"

const props = defineProps({
	modelValue: Boolean,
	posProfile: {
		type: String,
		default: "",
	},
	company: {
		type: String,
		default: "",
	},
	currency: {
		type: String,
		default: "USD",
	},
	writeOffAccount: {
		type: String,
		default: "",
	},
	writeOffCostCenter: {
		type: String,
		default: "",
	},
	writeOffLimit: {
		type: Number,
		default: 0,
	},
})

const emit = defineEmits(["update:modelValue", "saved"])

const { showSuccess, showError, showWarning } = useToast()

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
})

const tabs = [
	{ key: "customer", label: "Customer Payment", activeClass: "bg-blue-50 border-blue-500 text-blue-700 shadow-sm" },
	{ key: "supplier", label: "Supplier Payment", activeClass: "bg-orange-50 border-orange-500 text-orange-700 shadow-sm" },
	{ key: "expense", label: "Expense", activeClass: "bg-emerald-50 border-emerald-500 text-emerald-700 shadow-sm" },
]

const movementType = ref("customer")
const postingDate = ref(new Date().toISOString().slice(0, 10))
const amount = ref(0)
const modeOfPayment = ref("")
const referenceNo = ref("")
const referenceDate = ref(new Date().toISOString().slice(0, 10))
const remarks = ref("")
const submitting = ref(false)
const errorMessage = ref("")

const paymentMethods = ref([])
const defaults = ref({})

const partySearch = ref("")
const partyResults = ref([])
const partyDropdownOpen = ref(false)
const selectedParty = ref("")
const partyBalanceSummary = ref(null)
const partyBalanceLoading = ref(false)

const expenseSearch = ref("")
const expenseResults = ref([])
const expenseDropdownOpen = ref(false)
const selectedExpenseAccount = ref("")
const expenseLoading = ref(false)
const applyWriteOff = ref(false)

let partyTimer = null
let expenseTimer = null

const movementLabel = computed(() => {
	if (movementType.value === "supplier") return __("Supplier Payment")
	if (movementType.value === "expense") return __("Expense")
	return __("Customer Payment")
})

const partyCompanyBalance = computed(() => {
	return Number(partyBalanceSummary.value?.company_balance || 0)
})

const partyOutstanding = computed(() => {
	return Math.abs(partyCompanyBalance.value)
})

const writeOffAmount = computed(() => {
	if (movementType.value === "expense" || !applyWriteOff.value) return 0
	return Math.max(partyOutstanding.value - Number(amount.value || 0), 0)
})

const submitLabel = computed(() => {
	if (movementType.value === "expense") return __("Submit")
	return __("Submit")
})

const canSubmit = computed(() => {
	if (!props.posProfile || !props.company) return false
	if (!modeOfPayment.value || Number(amount.value) <= 0) return false
	if (movementType.value === "expense") {
		return Boolean(selectedExpenseAccount.value || expenseSearch.value.trim())
	}
	return Boolean(selectedParty.value || partySearch.value.trim())
})

function formatCurrency(amountValue) {
	return formatCurrencyUtil(Number(amountValue || 0), props.currency)
}

function resetForm() {
	postingDate.value = new Date().toISOString().slice(0, 10)
	amount.value = 0
	referenceNo.value = ""
	referenceDate.value = new Date().toISOString().slice(0, 10)
	remarks.value = ""
	errorMessage.value = ""
	partySearch.value = ""
	partyResults.value = []
	selectedParty.value = ""
	partyBalanceSummary.value = null
	partyBalanceLoading.value = false
	expenseSearch.value = ""
	expenseResults.value = []
	selectedExpenseAccount.value = ""
	expenseDropdownOpen.value = false
	expenseLoading.value = false
	applyWriteOff.value = false
	movementType.value = "customer"
	if (paymentMethods.value.length > 0) {
		const defaultMethod = paymentMethods.value.find((method) => method.default)
		modeOfPayment.value = defaultMethod?.mode_of_payment || paymentMethods.value[0].mode_of_payment
	}
}

function resetWriteOffSlider() {
	applyWriteOff.value = false
}

function canToggleWriteOff() {
	if (!selectedParty.value) {
		showWarning(__("Select a party first"))
		return false
	}
	if (partyBalanceLoading.value) {
		showWarning(__("Party balance is still loading"))
		return false
	}
	if (!props.writeOffAccount) {
		showWarning(__("Write off account is not configured for this POS profile"))
		return false
	}
	if (partyOutstanding.value <= 0) {
		showWarning(__("No party balance available to write off"))
		return false
	}
	if (props.writeOffLimit > 0 && writeOffAmount.value > props.writeOffLimit) {
		showWarning(
			__("Write off amount cannot exceed {0}", [
				formatCurrency(props.writeOffLimit),
			]),
		)
		return false
	}
	return true
}

function toggleWriteOff() {
	if (!applyWriteOff.value) {
		if (!canToggleWriteOff()) return
		applyWriteOff.value = true
		return
	}
	applyWriteOff.value = false
}

async function loadDefaults() {
	if (!props.company) return

	try {
		const result = await call("pos_next.api.cash_movements.get_cash_movement_defaults", {
			company: props.company,
		})
		defaults.value = result?.message || result || {}
		expenseSearch.value = defaults.value.default_expense_account || ""
		selectedExpenseAccount.value = defaults.value.default_expense_account || ""
	} catch (error) {
		defaults.value = {}
	}
}

async function loadPaymentMethods() {
	if (!props.posProfile) return

	try {
		const result = await call("pos_next.api.pos_profile.get_payment_methods", {
			pos_profile: props.posProfile,
		})
		paymentMethods.value = result?.message || result || []
		if (paymentMethods.value.length > 0 && !modeOfPayment.value) {
			const defaultMethod = paymentMethods.value.find((method) => method.default)
			modeOfPayment.value = defaultMethod?.mode_of_payment || paymentMethods.value[0].mode_of_payment
		}
	} catch (error) {
		paymentMethods.value = []
	}
}

async function searchParties(query) {
	if (!query.trim()) {
		partyResults.value = []
		return
	}

	const doctype = movementType.value === "supplier" ? "Supplier" : "Customer"
	const result = await call("frappe.desk.search.search_link", {
		doctype,
		txt: query,
		page_length: 10,
	})
	const rows = result?.message || result || []
	partyResults.value = rows.map((row) => ({
		value: row.value || row.name || row,
		description: row.description || row.extra || "",
	}))
}

async function loadPartyBalance(partyName) {
	if (!partyName || movementType.value === "expense") {
		partyBalanceSummary.value = null
		return
	}

	partyBalanceLoading.value = true
	try {
		const result = await call("pos_next.api.cash_movements.get_party_balance_summary", {
			company: props.company,
			party_type: movementType.value === "supplier" ? "Supplier" : "Customer",
			party: partyName,
			posting_date: postingDate.value,
			cost_center: defaults.value.cost_center || "",
		})
		partyBalanceSummary.value = result?.message || result || null
	} catch (error) {
		partyBalanceSummary.value = null
	} finally {
		partyBalanceLoading.value = false
	}
}

async function searchExpenseAccounts(query) {
	expenseLoading.value = true
	try {
		const result = await call("pos_next.api.cash_movements.search_expense_accounts", {
			company: props.company,
			txt: query || "",
			page_length: 10,
		})
		const rows = result?.message || result || []
		expenseResults.value = rows.map((row) => ({
			name: row.name,
			account_name: row.account_name,
			score: row.score || 0,
		}))
		expenseDropdownOpen.value = true
	} finally {
		expenseLoading.value = false
	}
}

function selectParty(item) {
	selectedParty.value = item.value
	partySearch.value = item.value
	partyDropdownOpen.value = false
	partyResults.value = []
	applyWriteOff.value = false
	loadPartyBalance(item.value).catch(() => {})
}

function selectExpenseAccount(item) {
	selectedExpenseAccount.value = item.name
	expenseSearch.value = item.name
	expenseDropdownOpen.value = false
	expenseResults.value = []
}

function handlePartyBlur() {
	setTimeout(() => {
		partyDropdownOpen.value = false
	}, 150)
}

function handleExpenseBlur() {
	setTimeout(() => {
		expenseDropdownOpen.value = false
	}, 150)
}

watch(
	() => show.value,
	async (open) => {
		errorMessage.value = ""
		if (!open) {
			resetForm()
			return
		}

		await Promise.all([loadDefaults(), loadPaymentMethods()])
		resetForm()
	},
)

watch(movementType, () => {
	errorMessage.value = ""
	partySearch.value = ""
	partyResults.value = []
	selectedParty.value = ""
	partyBalanceSummary.value = null
	partyBalanceLoading.value = false
	expenseSearch.value = defaults.value.default_expense_account || ""
	selectedExpenseAccount.value = defaults.value.default_expense_account || ""
	expenseResults.value = []
	expenseDropdownOpen.value = false
	expenseLoading.value = false
	resetWriteOffSlider()
})

watch(partySearch, (value) => {
	if (value !== selectedParty.value) {
		selectedParty.value = ""
		partyBalanceSummary.value = null
		resetWriteOffSlider()
	}
	clearTimeout(partyTimer)
	partyTimer = setTimeout(() => {
		partyDropdownOpen.value = true
		searchParties(value).catch(() => {
			partyResults.value = []
		})
	}, 250)
})

watch(expenseSearch, (value) => {
	if (movementType.value !== "expense") return
	if (value !== selectedExpenseAccount.value) {
		selectedExpenseAccount.value = ""
	}
	clearTimeout(expenseTimer)
	expenseTimer = setTimeout(() => {
		if (!value.trim()) {
			expenseResults.value = []
			expenseDropdownOpen.value = false
			return
		}
		searchExpenseAccounts(value).catch(() => {
			expenseResults.value = []
		})
	}, 250)
})

watch(postingDate, () => {
	if (selectedParty.value) {
		loadPartyBalance(selectedParty.value).catch(() => {})
	}
})

watch([amount, selectedParty, movementType], () => {
	if (movementType.value === "expense") {
		applyWriteOff.value = false
		return
	}
	if (!selectedParty.value) {
		applyWriteOff.value = false
		return
	}
})

async function submitMovement() {
	errorMessage.value = ""
	submitting.value = true

	try {
		const payload = {
			pos_profile: props.posProfile,
			company: props.company,
			movement_type: movementType.value,
			amount: Number(amount.value),
			mode_of_payment: modeOfPayment.value,
			posting_date: postingDate.value,
			reference_no: referenceNo.value.trim(),
			reference_date: referenceDate.value || postingDate.value,
			remarks: remarks.value.trim(),
			party_type: movementType.value === "customer" ? "Customer" : movementType.value === "supplier" ? "Supplier" : null,
			party: movementType.value === "expense" ? null : (selectedParty.value || partySearch.value.trim()),
			expense_account: movementType.value === "expense" ? (selectedExpenseAccount.value || expenseSearch.value.trim()) : null,
			cost_center: defaults.value.cost_center || "",
			write_off_amount: movementType.value !== "expense" && applyWriteOff.value ? Number(writeOffAmount.value || 0) : 0,
			write_off_account: movementType.value !== "expense" && applyWriteOff.value ? props.writeOffAccount : "",
			write_off_cost_center: movementType.value !== "expense" && applyWriteOff.value ? (props.writeOffCostCenter || defaults.value.cost_center || "") : "",
		}

		const result = await call("pos_next.api.cash_movements.create_cash_movement", payload)
		const data = result?.message || result || {}
		showSuccess(__("{0} created: {1}", [movementLabel.value, data.name || ""]))
		emit("saved", data)
		show.value = false
	} catch (error) {
		const parsed = parseError(error)
		errorMessage.value = parsed.message || error.message || __("Failed to save movement")
		showError(__("Unable to save movement"), errorMessage.value)
	} finally {
		submitting.value = false
	}
}
</script>
